"""Reproduce the offline, time-split evaluation of the four feed strategies."""

from __future__ import annotations

import argparse
import base64
import csv
from datetime import datetime
from contextlib import closing
from io import BytesIO
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile

import numpy as np

from app.db import database
from app.feed.learned import LikeModel
from app.repositories.feed import FeedRepository
from app.services.feed import FeedService


STRATEGIES = ("chronological", "popularity", "for_you", "learned")
BASELINES = STRATEGIES[:3]
COLORS = {
    "chronological": "#9AA6BD",
    "popularity": "#F7A30F",
    "for_you": "#10ADB6",
    "learned": "#0B2F63",
}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def format_time(value: datetime) -> str:
    return value.isoformat(sep=" ")


def ndcg_at_10(ranked_ids: list[int], relevant_ids: set[int]) -> float:
    if not relevant_ids:
        return 0.0
    dcg = sum(
        1.0 / np.log2(index + 2)
        for index, post_id in enumerate(ranked_ids[:10])
        if post_id in relevant_ids
    )
    ideal_count = min(10, len(relevant_ids))
    ideal = sum(1.0 / np.log2(index + 2) for index in range(ideal_count))
    return float(dcg / ideal) if ideal else 0.0


def bootstrap_interval(
    values: np.ndarray, seed: int, repetitions: int = 2000
) -> tuple[float, float, float]:
    if len(values) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, len(values), size=(repetitions, len(values)))
    means = values[samples].mean(axis=1)
    return (
        float(values.mean()),
        float(np.quantile(means, 0.025)),
        float(np.quantile(means, 0.975)),
    )


def paired_interval(
    values: np.ndarray, seed: int, repetitions: int = 2000
) -> tuple[float, float, float]:
    return bootstrap_interval(values, seed, repetitions)


def user_group(pre_like_count: int) -> str:
    if pre_like_count < 10:
        return "new (<10 likes)"
    if pre_like_count < 50:
        return "casual (10-49)"
    if pre_like_count < 200:
        return "regular (50-199)"
    return "power (200+)"


def database_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def choose_cutoff(path: Path) -> datetime:
    with closing(sqlite3.connect(path)) as connection:
        values = [
            parse_time(row[0])
            for row in connection.execute(
                "SELECT created_at FROM like ORDER BY created_at, user_id, post_id"
            )
        ]
    if not values:
        raise ValueError("the database has no likes")
    return values[max(0, int(np.ceil(len(values) * 0.8)) - 1)]


def make_snapshot(source: Path, cutoff: datetime, destination: Path) -> None:
    shutil.copy2(source, destination)
    cutoff_text = format_time(cutoff)
    with closing(sqlite3.connect(destination)) as connection:
        connection.execute("DELETE FROM like WHERE created_at >= ?", (cutoff_text,))
        connection.execute("DELETE FROM post WHERE created_at >= ?", (cutoff_text,))
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(follow)")
        }
        if "created_at" in columns:
            connection.execute(
                "DELETE FROM follow WHERE created_at >= ?", (cutoff_text,)
            )
        connection.commit()


def load_replay_data(
    source: Path, cutoff: datetime
) -> tuple[dict[int, int], dict[int, set[int]]]:
    cutoff_text = format_time(cutoff)
    with closing(sqlite3.connect(source)) as connection:
        posts = {
            row[0]
            for row in connection.execute(
                "SELECT id FROM post WHERE created_at < ?", (cutoff_text,)
            )
        }
        pre_counts = dict(
            connection.execute(
                "SELECT user_id, COUNT(*) FROM like WHERE created_at < ? "
                "GROUP BY user_id",
                (cutoff_text,),
            ).fetchall()
        )
        after = connection.execute(
            "SELECT user_id, post_id FROM like WHERE created_at >= ? "
            "ORDER BY created_at, user_id, post_id",
            (cutoff_text,),
        ).fetchall()
    relevant: dict[int, set[int]] = {}
    for user_id, post_id in after:
        if post_id in posts:
            relevant.setdefault(user_id, set()).add(post_id)
    return pre_counts, relevant


def popularity_ids(repository: FeedRepository, user_id: int, limit: int) -> list[int]:
    rows = repository.list_candidates(user_id)
    return [
        row.post_id
        for row in sorted(rows, key=lambda row: (-row.like_count, row.post_id))[:limit]
    ]


def evaluate_database(
    source_path: Path,
    cutoff: datetime,
    seed: int,
    model_path: Path,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    pre_counts, relevant = load_replay_data(source_path, cutoff)
    eligible = sorted(
        user_id
        for user_id, count in pre_counts.items()
        if count >= 3 and relevant.get(user_id)
    )
    with tempfile.TemporaryDirectory() as directory:
        snapshot = Path(directory) / "snapshot.db"
        make_snapshot(source_path, cutoff, snapshot)
        previous_path = database.DB_PATH
        database.DB_PATH = snapshot
        try:
            service = FeedService(
                FeedRepository(),
                now_factory=lambda: cutoff,
                learned_model=LikeModel.load(model_path),
            )
            repository = FeedRepository()
            rows: list[dict[str, object]] = []
            for user_id in eligible:
                group = user_group(pre_counts[user_id])
                for strategy in STRATEGIES:
                    if strategy == "popularity":
                        ids = popularity_ids(repository, user_id, 10)
                    else:
                        result = service.get_feed(user_id, strategy, 10)
                        ids = [item.post_id for item in result]
                    rows.append(
                        {
                            "user_id": user_id,
                            "strategy": strategy,
                            "ndcg_at_10": ndcg_at_10(ids, relevant[user_id]),
                            "n_relevant": len(relevant[user_id]),
                            "user_group": group,
                        }
                    )
        finally:
            database.DB_PATH = previous_path
    metadata = {
        "cutoff": format_time(cutoff),
        "seed": seed,
        "n_users": len(eligible),
        "fingerprint": database_fingerprint(source_path),
        "git_commit": git_commit(),
    }
    return rows, metadata


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "log", "-1", "--format=%H", "--", "scripts/evaluate.py"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def grouped_values(
    rows: list[dict[str, object]], strategy: str, group: str | None = None
) -> np.ndarray:
    return np.asarray(
        [
            float(row["ndcg_at_10"])
            for row in rows
            if row["strategy"] == strategy
            and (group is None or row["user_group"] == group)
        ],
        dtype=float,
    )


def verdict(interval: tuple[float, float, float]) -> str:
    if interval[1] > 0:
        return "wins"
    if interval[2] < 0:
        return "loses"
    return "unclear"


def best_baseline(rows: list[dict[str, object]], group: str | None = None) -> str:
    means = {
        strategy: grouped_values(rows, strategy, group).mean()
        for strategy in BASELINES
        if len(grouped_values(rows, strategy, group))
    }
    return max(means, key=means.get)


def markdown_report(
    rows: list[dict[str, object]], metadata: dict[str, object], seed: int
) -> str:
    lines = [
        "# Offline feed evaluation",
        "",
        "## Run metadata",
        "",
        f"- Cut-off: `{metadata['cutoff']}`",
        f"- Bootstrap seed: `{seed}`",
        f"- Eligible users: `{metadata['n_users']}`",
        f"- Database SHA-256: `{metadata['fingerprint']}`",
        f"- Git commit: `{metadata['git_commit']}`",
        "",
        "## Strategy comparison",
        "",
        "| Strategy | Mean NDCG@10 | 95% interval | Users |",
        "|---|---:|---:|---:|",
    ]
    for strategy in STRATEGIES:
        interval = bootstrap_interval(grouped_values(rows, strategy), seed)
        lines.append(
            f"| {strategy} | {interval[0]:.4f} | "
            f"[{interval[1]:.4f}, {interval[2]:.4f}] | "
            f"{len(grouped_values(rows, strategy))} |"
        )
    overall = best_baseline(rows)
    diff = paired_interval(
        grouped_values(rows, "learned") - grouped_values(rows, overall), seed + 100
    )
    lines += [
        "",
        f"Learned minus best baseline overall (`{overall}`): "
        f"{diff[0]:+.4f} [{diff[1]:+.4f}, {diff[2]:+.4f}] — {verdict(diff)}.",
        "",
        "## Learned minus best baseline by user slice",
        "",
        "| Slice | Best baseline | Difference | 95% interval | Verdict | Users |",
        "|---|---|---:|---:|---|---:|",
    ]
    groups = sorted({str(row["user_group"]) for row in rows})
    for index, group in enumerate(groups):
        baseline = best_baseline(rows, group)
        learned = grouped_values(rows, "learned", group)
        difference = paired_interval(
            learned - grouped_values(rows, baseline, group), seed + 200 + index
        )
        lines.append(
            f"| {group} | {baseline} | {difference[0]:+.4f} | "
            f"[{difference[1]:+.4f}, {difference[2]:+.4f}] | "
            f"{verdict(difference)} | {len(learned)} |"
        )
    return "\n".join(lines) + "\n"


def chart_png(fig) -> str:
    output = BytesIO()
    fig.savefig(output, format="png", dpi=130, bbox_inches="tight")
    import matplotlib.pyplot as plt

    plt.close(fig)
    return base64.b64encode(output.getvalue()).decode("ascii")


def dashboard(rows: list[dict[str, object]], metadata: dict[str, object], seed: int) -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    charts: list[tuple[str, str]] = []
    means = []
    lows = []
    highs = []
    for strategy in STRATEGIES:
        interval = bootstrap_interval(grouped_values(rows, strategy), seed)
        means.append(interval[0])
        lows.append(interval[0] - interval[1])
        highs.append(interval[2] - interval[0])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    positions = np.arange(len(STRATEGIES))
    ax.bar(positions, means, yerr=[lows, highs], color=[COLORS[s] for s in STRATEGIES], capsize=5)
    ax.set_title("A · Which strategy puts future likes in the top 10?")
    ax.set_ylabel("Mean NDCG@10 (95% bootstrap interval)")
    ax.set_xticks(positions, STRATEGIES)
    ax.set_ylim(0, max(1.0, max(highs[i] + means[i] for i in range(len(means))) * 1.15))
    ax.grid(axis="y", alpha=0.25)
    charts.append(("Overall strategy comparison", chart_png(fig)))

    groups = sorted({str(row["user_group"]) for row in rows})
    diffs, d_lows, d_highs = [], [], []
    for index, group in enumerate(groups):
        baseline = best_baseline(rows, group)
        interval = paired_interval(
            grouped_values(rows, "learned", group)
            - grouped_values(rows, baseline, group),
            seed + 200 + index,
        )
        diffs.append(interval[0])
        d_lows.append(interval[0] - interval[1])
        d_highs.append(interval[2] - interval[0])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    positions = np.arange(len(groups))
    ax.errorbar(
        diffs,
        positions,
        xerr=[d_lows, d_highs],
        fmt="o",
        color=COLORS["learned"],
        capsize=5,
    )
    ax.axvline(0, color="black", linewidth=1)
    ax.set_title("B · Where does learned beat the best baseline?")
    ax.set_xlabel("NDCG@10 learned minus best baseline")
    ax.set_yticks(positions, groups)
    ax.grid(axis="x", alpha=0.25)
    charts.append(("Slice comparison", chart_png(fig)))

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for strategy in STRATEGIES:
        values = [grouped_values(rows, strategy, group).mean() for group in groups]
        ax.plot(groups, values, marker="o", label=strategy, color=COLORS[strategy])
    ax.set_title("C · Does the winning strategy change by user activity?")
    ax.set_ylabel("Mean NDCG@10")
    ax.set_xlabel("User activity before cut-off")
    ax.set_ylim(0, 1)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    charts.append(("Strategy means by slice", chart_png(fig)))

    table = markdown_report(rows, metadata, seed)
    images = "\n".join(
        f'<section><h2>{title}</h2><img alt="{title}" src="data:image/png;base64,{image}"></section>'
        for title, image in charts
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>InstaKill feed evaluation</title>
<style>body{{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;color:#12182b}}
section{{margin:2rem 0;padding:1rem;border:1px solid #d7e1eb;border-radius:12px}}
img{{max-width:100%;height:auto}}pre{{white-space:pre-wrap;background:#f7f7f7;padding:1rem}}
table{{border-collapse:collapse;width:100%}}th,td{{padding:.45rem;border-bottom:1px solid #d7e1eb;text-align:left}}
.interactive{{background:#f7f7f7}}input{{width:100%}}.bar{{height:1.2rem;margin:.35rem 0;background:#d7e1eb}}
.fill{{height:100%;color:white;padding-left:.35rem;font-size:.8rem;background:#0B2F63}}</style>
</head><body><h1>InstaKill offline feed evaluation</h1>
<p>Static dashboard generated by <code>scripts/evaluate.py</code>. It opens
directly from disk; the small inline JavaScript only updates the precomputed
cutoff views.</p>
<section class="interactive"><h2>Interactive cutoff replay</h2>
<p>Adjust <b>T</b> to inspect precomputed evaluations. The slider changes the
results without a server; it does not invent new data between cutoffs.</p>
<input id="cutoff" type="range"><output id="cutoff-label"></output>
<div id="interactive-results"></div></section>
<pre>{table}</pre>{images}
<script>
const RUNS = {json.dumps(getattr(dashboard, "_runs", []), separators=(",", ":"))};
const STRATEGIES = ["chronological","popularity","for_you","learned"];
const slider = document.getElementById("cutoff");
const label = document.getElementById("cutoff-label");
const target = document.getElementById("interactive-results");
function render() {{
  const run = RUNS[Number(slider.value)];
  label.textContent = " " + run.cutoff + " (" + run.users + " users)";
  const bars = run.means.map(row => `<div><b>${{row.strategy}}</b>: ${{row.mean.toFixed(4)}}
    <div class="bar"><div class="fill" style="width:${{Math.max(0,row.mean)*100}}%">${{(row.mean*100).toFixed(1)}}%</div></div>
    95% CI [${{row.low.toFixed(4)}}, ${{row.high.toFixed(4)}}]</div>`).join("");
  const slices = run.slices.map(row => `<tr><td>${{row.group}}</td><td>${{row.baseline}}</td>
    <td>${{row.diff >= 0 ? "+" : ""}}${{row.diff.toFixed(4)}}</td>
    <td>[${{row.low.toFixed(4)}}, ${{row.high.toFixed(4)}}]</td><td>${{row.verdict}}</td></tr>`).join("");
  target.innerHTML = `<h3>Which strategy wins at this T?</h3>${{bars}}
    <h3>Where does learned differ from the best baseline?</h3>
    <table><tr><th>Slice</th><th>Baseline</th><th>Difference</th><th>95% CI</th><th>Verdict</th></tr>${{slices}}</table>`;
}}
slider.min = 0; slider.max = Math.max(0, RUNS.length - 1); slider.value = RUNS.length - 1;
slider.addEventListener("input", render); render();
</script></body></html>"""


def interactive_runs(
    source: Path, cutoffs: list[datetime], seed: int, model_path: Path
) -> list[dict[str, object]]:
    runs = []
    for cutoff in cutoffs:
        rows, _ = evaluate_database(source, cutoff, seed, model_path)
        if not rows:
            continue
        means = []
        for strategy in STRATEGIES:
            mean, low, high = bootstrap_interval(
                grouped_values(rows, strategy), seed
            )
            means.append(
                {"strategy": strategy, "mean": mean, "low": low, "high": high}
            )
        slices = []
        for index, group in enumerate(sorted({str(r["user_group"]) for r in rows})):
            baseline = best_baseline(rows, group)
            interval = paired_interval(
                grouped_values(rows, "learned", group)
                - grouped_values(rows, baseline, group),
                seed + 200 + index,
            )
            slices.append(
                {
                    "group": group,
                    "baseline": baseline,
                    "diff": interval[0],
                    "low": interval[1],
                    "high": interval[2],
                    "verdict": verdict(interval),
                }
            )
        runs.append(
            {
                "cutoff": format_time(cutoff),
                "users": len({r["user_id"] for r in rows}),
                "means": means,
                "slices": slices,
            }
        )
    return runs


def write_reports(
    rows: list[dict[str, object]],
    metadata: dict[str, object],
    output: Path,
    seed: int,
    runs: list[dict[str, object]],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with (output / "eval_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["user_id", "strategy", "ndcg_at_10", "n_relevant", "user_group"],
        )
        writer.writeheader()
        writer.writerows(rows)
    (output / "baseline_table.md").write_text(
        markdown_report(rows, metadata, seed), encoding="utf-8"
    )
    dashboard._runs = runs
    (output / "dashboard.html").write_text(
        dashboard(rows, metadata, seed), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("instakill.db"))
    parser.add_argument("--cutoff")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("reports"))
    args = parser.parse_args()
    cutoff = parse_time(args.cutoff) if args.cutoff else choose_cutoff(args.db)
    model_path = Path(__file__).resolve().parents[1] / "like_model.npz"
    rows, metadata = evaluate_database(args.db, cutoff, args.seed, model_path)
    with closing(sqlite3.connect(args.db)) as connection:
        cutoff_values = sorted(
            {
                parse_time(row[0])
                for row in connection.execute(
                    "SELECT DISTINCT created_at FROM like ORDER BY created_at"
                )
            }
        )
    cutoffs = [value for value in cutoff_values if value > min(cutoff_values)]
    if cutoff not in cutoffs:
        cutoffs.append(cutoff)
    cutoffs = sorted(set(cutoffs))
    runs = interactive_runs(args.db, cutoffs, args.seed, model_path)
    write_reports(rows, metadata, args.out, args.seed, runs)
    print(f"Evaluated {metadata['n_users']} users at {metadata['cutoff']}.")
    print(f"Reports written to {args.out}.")


if __name__ == "__main__":
    main()
