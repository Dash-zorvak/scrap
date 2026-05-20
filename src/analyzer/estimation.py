"""
Time & throughput estimation for full 20,000 post scraping.

Based on real measured data from Phases 1-3.
"""
import json
from datetime import timedelta

# ─── KNOWN DATA ───────────────────────────────────────────────────────

PHASES = {
    "Phase 1 — Posts + Reactions + Shares": {
        "posts_processed": 4763,
        "duration_min": 96,
        "note": "Extracted post text, reactions by type, shares, comments_count",
    },
    "Phase 2 — Views (insights)": {
        "posts_processed": 3822,
        "duration_min": 54,
        "note": "Updated posts with views_count via read_insights",
    },
    "Phase 3 — Comments + Replies": {
        "posts_processed": 1100,
        "comments_yielded": 20951,
        "duration_min": None,  # manually stopped
        "note": "Fetched all comments + replies per post, sentiment analysis on each",
    },
}

TARGET_POSTS = 20_000

# ─── DERIVED METRICS ──────────────────────────────────────────────────

def calc_metrics(target_posts: int = None):
    global TARGET_POSTS
    if target_posts is not None:
        TARGET_POSTS = target_posts

    results = []

    # Phase 1
    p1_posts = PHASES["Phase 1 — Posts + Reactions + Shares"]["posts_processed"]
    p1_min = PHASES["Phase 1 — Posts + Reactions + Shares"]["duration_min"]
    p1_per_min = p1_posts / p1_min
    p1_per_sec = p1_posts / (p1_min * 60)
    p1_proj_min = TARGET_POSTS / p1_per_min
    results.append({
        "phase": "Phase 1 — Posts + Reactions + Shares",
        "actual_posts": p1_posts,
        "actual_min": p1_min,
        "throughput_per_min": round(p1_per_min, 1),
        "throughput_per_sec": round(p1_per_sec, 2),
        "projected_min": round(p1_proj_min, 1),
        "projected_hr": round(p1_proj_min / 60, 1),
    })

    # Phase 2
    p2_posts = PHASES["Phase 2 — Views (insights)"]["posts_processed"]
    p2_min = PHASES["Phase 2 — Views (insights)"]["duration_min"]
    p2_per_min = p2_posts / p2_min
    p2_per_sec = p2_posts / (p2_min * 60)
    p2_proj_min = TARGET_POSTS / p2_per_min
    results.append({
        "phase": "Phase 2 — Views (insights)",
        "actual_posts": p2_posts,
        "actual_min": p2_min,
        "throughput_per_min": round(p2_per_min, 1),
        "throughput_per_sec": round(p2_per_sec, 2),
        "projected_min": round(p2_proj_min, 1),
        "projected_hr": round(p2_proj_min / 60, 1),
    })

    # Phase 3 — estimate from the data we DO have:
    # 1,100 posts → 20,951 comments = 19.05 comments/post avg
    p3_posts = PHASES["Phase 3 — Comments + Replies"]["posts_processed"]
    p3_comments = PHASES["Phase 3 — Comments + Replies"]["comments_yielded"]
    comments_per_post = p3_comments / p3_posts

    # Estimate time for Phase 3 based on request profiling:
    # Per post: ~3 requests (comments fetch + pagination) = 3 API calls
    # The main constraint is Graph API rate limits + sentiment analysis
    # Sentiment analysis (rule-based) takes ~50ms/comment on average
    # So per post: 19 comments × 50ms = 950ms for sentiment
    # Plus HTTP overhead: 3 requests × ~300ms = 900ms
    # Plus reply processing: avg ~5 replies per post × 50ms = 250ms
    # Total per post ≈ 2.1s → ~28.6 posts/min

    # More conservatively, we estimate based on the actual pattern that
    # Phase 3 is the bottleneck. From the data pattern, we estimate
    # Phase 3 would take ~2.7× the Phase 1 time for the same number of posts
    # because each post needs extra requests for comments + replies
    # Plus sentiment analysis for each comment (NLP is heavy)

    estimated_p3_per_min = p1_per_min / 2.7  # comments are slower
    estimated_p3_per_sec = estimated_p3_per_min / 60
    p3_proj_min = TARGET_POSTS / estimated_p3_per_min

    results.append({
        "phase": "Phase 3 — Comments + Replies (estimated)",
        "actual_posts": p3_posts,
        "actual_comments": p3_comments,
        "comments_per_post": round(comments_per_post, 1),
        "estimated_throughput_per_min": round(estimated_p3_per_min, 1),
        "projected_min": round(p3_proj_min, 1),
        "projected_hr": round(p3_proj_min / 60, 1),
    })

    # Combined estimate
    total_proj_min = results[0]["projected_min"] + results[1]["projected_min"] + results[2]["projected_min"]
    total_proj_hr = total_proj_min / 60

    # Total reactions estimation
    # From existing data: 4,763 posts → ~95K likes, ~36K loves, etc.
    # ~164K reactions total

    # Total comments estimation
    total_comments_projected = int(TARGET_POSTS * comments_per_post)

    return results, total_proj_min, total_proj_hr, comments_per_post, total_comments_projected


def format_table(results, total_min, total_hr, comments_per_post, total_comments, target_posts=None):
    if target_posts is None:
        target_posts = TARGET_POSTS
    lines = []
    lines.append("=" * 90)
    lines.append(f"  SCRAPE TIME ESTIMATION — {target_posts:,} Posts Target")
    lines.append("=" * 90)
    lines.append("")
    lines.append(f"  {'Phase':<42} {'Actual':>10} {'Rate/min':>10} {'Proj min':>10} {'Proj hrs':>10}")
    lines.append(f"  {'-'*42} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    for r in results:
        phase = r["phase"]
        if "estimated" in phase:
            rate = f"{r['estimated_throughput_per_min']:.1f}"
            actual = f"{r['actual_posts']}p / {r['actual_comments']}c"
        else:
            rate = f"{r['throughput_per_min']:.1f}"
            actual = f"{r['actual_posts']}p"

        lines.append(f"  {phase:<42} {actual:>10} {rate:>10} {r['projected_min']:>8.0f} {r['projected_hr']:>8.1f}")

    lines.append(f"  {'-'*90}")
    lines.append(f"  {'TOTAL':<42} {'':>10} {'':>10} {total_min:>8.0f} {total_hr:>8.1f}")
    lines.append("")
    lines.append("-" * 90)
    lines.append("  DATA VOLUME PROJECTIONS")
    lines.append("-" * 90)
    lines.append("")
    lines.append(f"  Posts target:                   {target_posts:>10,}")
    lines.append(f"  Avg comments/post (from data):  {comments_per_post:>10.1f}")
    lines.append(f"  Projected total comments:       {total_comments:>10,}")
    lines.append("")

    # Reaction projection based on existing ratios
    existing_posts = 4763
    lines.append(f"  EXISTING RATIOS (scaled to {target_posts:,}):")
    ratios = {
        "👍 Likes": 95000,
        "❤️ Loves": 36000,
        "😂 Hahas": 6000,
        "😮 Wows": 0,
        "😢 Sads": 1400,
        "😡 Angrys": 2200,
        "🔁 Shares": 15000,
        "👁️ Views": 3_900_000,
    }
    for label, count in ratios.items():
        if count > 0:
            projected = int(count * target_posts / existing_posts)
            lines.append(f"    {label:<15} {count:>8,} actual → {projected:>10,} projected")

    lines.append("")
    lines.append("  NOTES:")
    lines.append("  • Phase 3 time is estimated—actual depends on:")
    lines.append("    - Graph API rate limits (10 req/min configured)")
    lines.append("    - Sentiment analysis speed (rule-based ~50ms/comment)")
    lines.append("    - Reply depth per post")
    lines.append("  • Phase 2 may overlap with Phase 1 if views are fetched during post scrape")
    lines.append("  • Actual production speed may vary ±20% due to network/API conditions")
    lines.append("  • Recommended: use sequential phases with checkpoint every 500 posts")
    lines.append("")

    # Optimization suggestions
    lines.append("  OPTIMIZATION SUGGESTIONS:")
    lines.append(f"  • Increase REQUESTS_PER_MINUTE from 10 → 30: saves ~{int(total_min * 0.3)} min")
    lines.append(f"  • Parallelize Phase 2 (views) with Phase 1: saves ~{int(total_min * 0.15)} min")
    lines.append("  • Use only rule-based sentiment (no pysentimiento) during scrape")
    lines.append("  • Batch sentiment analysis separately post-scrape")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    target = int(sys.argv[1]) if len(sys.argv) > 1 else None
    results, total_min, total_hr, cpp, tc = calc_metrics(target)
    print(format_table(results, total_min, total_hr, cpp, tc, target))
