import json
import logging
import os
from datetime import datetime

from src.analyzer.trends import TrendAnalyzer

logger = logging.getLogger(__name__)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np

    HAS_MPL = True
except ImportError:
    HAS_MPL = False


class ReportGenerator:
    def __init__(self, db_session, output_dir: str):
        self.session = db_session
        self.output_dir = output_dir
        self.trends = TrendAnalyzer(db_session)
        os.makedirs(output_dir, exist_ok=True)

    def generate_full_report(self, platform: str = "facebook") -> dict:
        report = {
            "generated_at": datetime.now().isoformat(),
            "platforms": {},
            "summary": {},
        }

        pf_report = self._platform_report("facebook")
        report["platforms"]["facebook"] = pf_report

        report["summary"] = self._global_summary(report["platforms"])

        json_path = os.path.join(
            self.output_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Report saved to {json_path}")

        if HAS_MPL:
            self._generate_charts(report, ["facebook"])

        return report

    def _platform_report(self, platform: str) -> dict:
        sentiment_trend = self.trends.sentiment_over_time(platform)
        engagement = self.trends.engagement_analysis(platform)
        top_posts = self.trends.top_posts(platform)

        report = {
            "sentiment_trend": sentiment_trend,
            "engagement": engagement,
            "top_posts": top_posts,
        }

        report["reaction_breakdown"] = self.trends.reaction_breakdown()

        latest_sentiment = sentiment_trend.get("positive", [])
        recent_pos = latest_sentiment[-3:] if len(latest_sentiment) >= 3 else latest_sentiment
        report["current_mood"] = (
            "positive"
            if recent_pos and sum(recent_pos) / len(recent_pos) > 50
            else "negative" if recent_pos and sum(recent_pos) / len(recent_pos) < 30
            else "neutral"
        )

        return report

    def _global_summary(self, platform_reports: dict) -> dict:
        total_posts = 0
        total_positives = 0
        total_negatives = 0
        total_neutral = 0
        all_engagement = {}

        for pf, report in platform_reports.items():
            eng = report.get("engagement", {})
            total_posts += eng.get("total_posts", 0)

            trend = report.get("sentiment_trend", {})
            positives = trend.get("positive", [])
            negatives = trend.get("negative", [])
            neutrals = trend.get("neutral", [])

            if positives:
                total_positives += int(sum(positives) / len(positives) * eng.get("total_posts", 0) / 100)
            if negatives:
                total_negatives += int(sum(negatives) / len(negatives) * eng.get("total_posts", 0) / 100)
            if neutrals:
                total_neutral += int(sum(neutrals) / len(neutrals) * eng.get("total_posts", 0) / 100)

            all_engagement[pf] = {
                "avg_reactions": eng.get("avg_reactions_per_post", 0),
                "avg_comments": eng.get("avg_comments_per_post", 0),
            }

        grand_total = total_positives + total_negatives + total_neutral
        return {
            "total_posts_analyzed": total_posts,
            "sentiment_distribution": {
                "positive_pct": round(total_positives / grand_total * 100, 1) if grand_total else 0,
                "negative_pct": round(total_negatives / grand_total * 100, 1) if grand_total else 0,
                "neutral_pct": round(total_neutral / grand_total * 100, 1) if grand_total else 0,
            },
            "overall_sentiment": (
                "positive"
                if total_positives > total_negatives
                else "negative" if total_negatives > total_positives
                else "neutral"
            ),
            "engagement_by_platform": all_engagement,
        }

    def _generate_charts(self, report: dict, platforms: list):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for pf in platforms:
            pf_data = report.get("platforms", {}).get(pf, {})
            trend = pf_data.get("sentiment_trend", {})
            if not trend.get("labels"):
                continue

            self._plot_sentiment_trend(trend, pf, timestamp)

        summary = report.get("summary", {}).get("sentiment_distribution", {})
        if summary:
            self._plot_sentiment_pie(summary, timestamp)

        logger.info(f"Charts saved to {self.output_dir}")

    def _plot_sentiment_trend(self, trend: dict, platform: str, timestamp: str):
        labels = trend.get("labels", [])
        if not labels:
            logger.info(f"No trend data for {platform}, skipping chart")
            return
        positive = trend.get("positive", [])
        negative = trend.get("negative", [])
        neutral = trend.get("neutral", [])
        totals = trend.get("total", [])

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [3, 1]})

        x = range(len(labels))
        ax1.stackplot(
            x, positive, negative, neutral,
            labels=["Positivo", "Negativo", "Neutral"],
            colors=["#2ecc71", "#e74c3c", "#95a5a6"],
            alpha=0.8,
        )
        ax1.set_ylabel("% de posts", fontsize=12)
        ax1.set_title(f"Tendencia de Sentimiento - {platform.upper()}", fontsize=14, fontweight="bold")
        ax1.legend(loc="upper left")
        ax1.set_ylim(0, 100)
        ax1.grid(True, alpha=0.3)

        if len(labels) > 10:
            step = max(1, len(labels) // 10)
            ax1.set_xticks(x[::step])
            ax1.set_xticklabels([labels[i] for i in range(0, len(labels), step)], rotation=45, ha="right")
        else:
            ax1.set_xticks(x)
            ax1.set_xticklabels(labels, rotation=45, ha="right")

        ax2.bar(x, totals, color="#3498db", alpha=0.7)
        ax2.set_ylabel("Posts", fontsize=12)
        ax2.set_xlabel("Período", fontsize=12)
        ax2.grid(True, alpha=0.3)

        if len(labels) > 10:
            ax2.set_xticks(x[::step])
            ax2.set_xticklabels([labels[i] for i in range(0, len(labels), step)], rotation=45, ha="right")
        else:
            ax2.set_xticks(x)
            ax2.set_xticklabels(labels, rotation=45, ha="right")

        plt.tight_layout()
        path = os.path.join(self.output_dir, f"sentiment_trend_{platform}_{timestamp}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()

    def _plot_sentiment_pie(self, distribution: dict, timestamp: str):
        sizes = [
            distribution.get("positive_pct", 0) or 0,
            distribution.get("negative_pct", 0) or 0,
            distribution.get("neutral_pct", 0) or 0,
        ]
        if sum(sizes) == 0:
            logger.info("No data for pie chart, skipping")
            return

        labels = ["Positivo", "Negativo", "Neutral"]
        colors = ["#2ecc71", "#e74c3c", "#95a5a6"]

        fig, ax = plt.subplots(figsize=(8, 8))
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            colors=colors,
            textprops={"fontsize": 14, "fontweight": "bold"},
        )
        ax.set_title("Distribución General de Sentimiento", fontsize=16, fontweight="bold")

        plt.tight_layout()
        path = os.path.join(self.output_dir, f"sentiment_pie_{timestamp}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
