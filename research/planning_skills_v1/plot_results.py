"""Standalone descriptive scientific figures from replay-validated real results."""
import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze_heldout import interval


LABELS = {"none": "No skill", "static_system": "Static / system", "static": "Static / latest user",
          "local": "Local rule", "ledger_system": "Ledger", "binding_system": "Joined facts", "unbound_system": "Unjoined facts"}
ORDER = list(LABELS)


def plot(directory):
    rows = json.loads((directory / "episode-results.json").read_text())
    models = sorted({r["model"] for r in rows})
    groups = defaultdict(list)
    for r in rows:
        groups[(r["model"], r["condition"])].append(r)
    fig, axes = plt.subplots(1, len(models), figsize=(13, 5.6), sharey=True, layout="constrained")
    colors = ["#667085", "#5572a5", "#95a6c4", "#ac79a2", "#65a69b", "#24806d", "#d4a64c"]
    for ax, model in zip(axes, models):
        conditions = [c for c in ORDER if (model, c) in groups]
        means, lower, upper = [], [], []
        for c in conditions:
            clustered = defaultdict(list)
            for r in groups[(model, c)]:
                clustered[r["cluster_id"]].append(int(r["success"]))
            estimate = interval([statistics.mean(v) for _, v in sorted(clustered.items())])
            mean = estimate["mean"]
            lo, hi = estimate["cluster_bootstrap_percentile95"]
            means.append(mean)
            lower.append(mean - lo)
            upper.append(hi - mean)
        ax.bar(range(len(conditions)), means, color=[colors[ORDER.index(c)] for c in conditions],
               yerr=[lower, upper], capsize=3, error_kw={"linewidth": 1})
        ax.set_xticks(range(len(conditions)), [LABELS[c] for c in conditions], rotation=40, ha="right")
        for x, c in enumerate(conditions):
            values = groups[(model, c)]
            ax.text(x, min(1.07, means[x] + upper[x] + .035),
                    f"{sum(r['success'] for r in values)}/{len(values)}", ha="center", fontsize=9)
        ax.set_title(model)
        ax.set_ylim(0, 1.13)
        ax.set_yticks([0, .25, .5, .75, 1])
        ax.grid(axis="y", alpha=.2)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Exact task success rate")
    fig.suptitle("Autonomous workflows: frozen synthetic stress tasks", fontsize=13)
    fig.supxlabel("Paired graph-cluster bootstrap intervals; diagnostic task distribution, not population confidence")
    for suffix in ("png", "svg"):
        fig.savefig(directory / f"task-success.{suffix}", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), layout="constrained")
    for mi, model in enumerate(models):
        values = [(c, groups[(model, c)]) for c in ORDER if (model, c) in groups]
        xs = [sum(r["prompt_tokens"] for r in group) / len(group) / 1000 for _, group in values]
        ys = [sum(r["success"] for r in group) / len(group) for _, group in values]
        for x, y, (c, group) in zip(xs, ys, values):
            axes[mi].scatter(x, y, s=65, color=colors[ORDER.index(c)], label=LABELS[c])
        axes[mi].legend(loc="upper right", frameon=False, fontsize=9)
        axes[mi].set_title(model)
        axes[mi].set_xlabel("Mean prompt tokens / attempted workflow (thousands)")
        axes[mi].set_ylim(-.04, 1.05)
        axes[mi].grid(alpha=.2)
    axes[0].set_ylabel("Exact task success rate")
    fig.suptitle("Failure-inclusive token work versus success; GPU monetary cost unknown", fontsize=12)
    for suffix in ("png", "svg"):
        fig.savefig(directory / f"token-work-success.{suffix}", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--directory", required=True, type=Path)
    plot(p.parse_args().directory)
