"""Create comparison charts from the saved CSV files in results."""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_csv(filename):
    with open(os.path.join("results", filename), newline="") as handle:
        return list(csv.DictReader(handle))


def make_report_chart():
    scaling = load_csv("scaling_results.csv")
    memory = load_csv("memory_results.csv")

    sizes = [int(r["n"]) / 1000.0 for r in scaling]
    p2_upd = [float(r["p2_updates_ms"]) for r in scaling]
    p3_upd = [float(r["p3_updates_ms"]) for r in scaling]
    p2_load = [float(r["p2_load_ms"]) for r in scaling]
    p3_bulk = [float(r["p3_bulk_load_ms"]) for r in scaling]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.4))

    ax1.plot(sizes, p2_upd, marker="o", linewidth=2.0, color="#b22222", label="Phase 2 Updates")
    ax1.plot(sizes, p2_load, marker="s", linewidth=1.8, linestyle="--", color="#d95f02", label="Phase 2 Load")
    ax1.plot(sizes, p3_bulk, marker="^", linewidth=2.0, linestyle="--", color="#2b5c8f", label="Phase 3 Bulk Load")
    ax1.plot(sizes, p3_upd, marker="D", linewidth=2.2, color="#1b7837", label="Phase 3 Updates")
    ax1.set_title("Load and Update Scaling", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Catalog Size (thousands of products)", fontsize=9.5)
    ax1.set_ylabel("Execution Time (ms)", fontsize=9.5)
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=8, loc="upper left")

    p2_mem = [float(memory[0]["active_50k_kib"]) / 1024.0, float(memory[0]["after_90pct_delete_kib"]) / 1024.0]
    p3_mem = [float(memory[1]["active_50k_kib"]) / 1024.0, float(memory[1]["after_90pct_delete_kib"]) / 1024.0]
    x = [0, 1]
    width = 0.34
    bars1 = ax2.bar([i - width / 2 for i in x], p2_mem, width, color="#b22222", label="Phase 2")
    bars2 = ax2.bar([i + width / 2 for i in x], p3_mem, width, color="#1b7837", label="Phase 3")
    ax2.set_title("Memory Footprint and Shrink Recovery", fontsize=11, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(["Active 50k Catalog", "After 90% Removal"], fontsize=9.5)
    ax2.set_ylabel("Tracked Memory (MiB)", fontsize=9.5)
    ax2.set_ylim(0, max(p2_mem) * 1.2)
    ax2.grid(True, axis="y", alpha=0.3)
    ax2.legend(fontsize=8.5, loc="upper right")

    for group in (bars1, bars2):
        for bar in group:
            h = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                h + 0.8,
                f"{h:.1f}",
                ha="center",
                va="bottom",
                fontsize=8.5,
            )

    fig.tight_layout()
    fig.savefig(os.path.join("results", "phase3_comparison.png"), dpi=240)
    plt.close(fig)


def make_query_chart():
    scaling = load_csv("scaling_results.csv")
    sizes = [int(r["n"]) / 1000.0 for r in scaling]
    p2_q = [float(r["p2_queries_ms"]) for r in scaling]
    p3_q = [float(r["p3_queries_ms"]) for r in scaling]

    fig, ax = plt.subplots(figsize=(6.4, 3.5))
    ax.plot(sizes, p2_q, marker="o", linewidth=2.0, color="#b22222", label="Phase 2 Uncached Queries")
    ax.plot(sizes, p3_q, marker="D", linewidth=2.0, color="#1b7837", label="Phase 3 With LRU Cache")
    ax.set_yscale("log")
    ax.set_title("Repeated Query Mix Time (Log Scale)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Catalog Size (thousands of products)", fontsize=9.5)
    ax.set_ylabel("Time for 1,200 Queries (ms, log scale)", fontsize=9.5)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join("results", "query_cache_scaling.png"), dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    make_report_chart()
    make_query_chart()
    print("Saved charts to results/")
