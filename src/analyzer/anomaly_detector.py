import logging
from collections import defaultdict
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def detect_anomalies(posts_df, monthly_df=None) -> List[Dict[str, Any]]:
    alerts = []

    if posts_df.empty or len(posts_df) < 10:
        return alerts

    if monthly_df is not None and not monthly_df.empty and len(monthly_df) > 2:
        if 'controversy' in monthly_df.columns:
            mean_cont = monthly_df['controversy'].mean()
            std_cont = monthly_df['controversy'].std()
            for _, row in monthly_df.iterrows():
                if std_cont > 0:
                    z = (row['controversy'] - mean_cont) / std_cont
                    if z > 2:
                        alerts.append({
                            "type": "crisis",
                            "title": f"Pico de controversia: {row['month']}",
                            "desc": f"Controversia de {row['controversy']:.1%} está {z:.1f}σ sobre la media.",
                            "severity": "alta",
                            "category": "controversia",
                            "metric": round(z, 2),
                        })

        if 'engagement_rate' in monthly_df.columns and len(monthly_df) > 3:
            for i in range(1, len(monthly_df)):
                prev = monthly_df.iloc[i-1]['engagement_rate']
                curr = monthly_df.iloc[i]['engagement_rate']
                if prev > 0:
                    drop = (prev - curr) / prev
                    if drop > 0.4:
                        alerts.append({
                            "type": "warning",
                            "title": f"Caída de engagement: {monthly_df.iloc[i]['month']}",
                            "desc": f"Engagement cayó {drop:.0%} vs mes anterior. Señal de desconexión.",
                            "severity": "media",
                            "category": "engagement",
                            "metric": round(drop, 2),
                        })

    topic_agg = posts_df.groupby('topic_category').agg(
        angrys=('angrys_count', 'sum'),
        cares=('cares_count', 'sum'),
        likes=('likes_count', 'sum'),
        loves=('loves_count', 'sum'),
        count=('post_id', 'count'),
    ).reset_index()
    topic_agg['angry_ratio'] = topic_agg['angrys'] / (topic_agg['likes'] + topic_agg['loves'] + topic_agg['cares'] + topic_agg['angrys'] + 1)
    overall_angry_ratio = topic_agg['angrys'].sum() / (topic_agg['likes'].sum() + topic_agg['loves'].sum() + topic_agg['cares'].sum() + topic_agg['angrys'].sum() + 1)
    for _, row in topic_agg.iterrows():
        if row['count'] > 2 and row['angry_ratio'] > overall_angry_ratio * 2 and row['angry_ratio'] > 0.03:
            alerts.append({
                "type": "warning",
                "title": f"Tópico con rechazo inusual: {row['topic_category']}",
                "desc": f"Ratio angry/likes de {row['angry_ratio']:.1%} vs promedio de {overall_angry_ratio:.1%}. {int(row['angrys'])} reacciones de enojo.",
                "severity": "media",
                "category": "topic_anomaly",
                "metric": round(row['angry_ratio'], 3),
            })

    if 'zona' in posts_df.columns and 'sentiment' in posts_df.columns:
        for zona in posts_df['zona'].unique():
            if not zona or zona == 'unknown':
                continue
            zona_posts = posts_df[posts_df['zona'] == zona]
            if len(zona_posts) > 3:
                neg_count = len(zona_posts[zona_posts['sentiment'] == 'negative'])
                neg_rate = neg_count / len(zona_posts)
                if neg_rate > 0.25:
                    alerts.append({
                        "type": "warning",
                        "title": f"Disonancia en zona: {zona}",
                        "desc": f"{neg_rate:.0%} de posts negativos en zona {zona}. Posible problema de ejecución.",
                        "severity": "alta",
                        "category": "zona_dissonance",
                        "metric": round(neg_rate, 2),
                    })

    alerts.sort(key=lambda a: 0 if a['severity'] == 'alta' else 1)
    return alerts
