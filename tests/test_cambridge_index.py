import math
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.intelligence.cambridge_index import (
    assign_topic_sensitivity,
    quarterly_adjustment,
    TOPIC_DEFAULT_SENSITIVITY,
    TOPIC_SENSITIVITY_BASE,
    SuppressionEngine,
    detect_controversy_spike,
    detect_sentiment_dissonance,
    detect_engagement_fugue,
    detect_topic_anomaly,
    detect_zone_dissonance,
    run_all_detectors,
    AlertResult,
    prioritize_alerts,
)


def make_post(overrides=None):
    base = {
        "post_id": "p1",
        "likes_count": 10,
        "loves_count": 5,
        "cares_count": 0,
        "hahas_count": 2,
        "wows_count": 1,
        "sads_count": 1,
        "angrys_count": 2,
        "comments_count": 3,
        "shares_count": 1,
        "views_count": 100,
        "sentiment": "positive",
        "topic_category": "seguridad",
        "zona": "Centro",
        "created_time": datetime.now().isoformat(),
    }
    if overrides:
        base.update(overrides)
    return base


class TestTopicSensitivity:
    def test_subtopic_match_returns_highest(self):
        assert assign_topic_sensitivity(["malversacion", "soborno"]) == 1.6

    def test_no_subtopic_falls_back_to_topic(self):
        assert assign_topic_sensitivity([], "corrupcion") == 1.3

    def test_no_subtopic_no_topic_returns_default(self):
        assert assign_topic_sensitivity([]) == 1.0

    def test_unknown_topic_returns_default(self):
        assert assign_topic_sensitivity([], "unknown_topic") == 1.0

    def test_subtopic_without_topic_main(self):
        assert assign_topic_sensitivity(["agua"]) == 1.2

    def test_mixed_known_unknown_subtopics(self):
        assert assign_topic_sensitivity(["unknown_subtopic", "malversacion"]) == 1.6

    def test_all_subtopics_known(self):
        assert assign_topic_sensitivity(["delincuencia", "extorsion", "violencia"]) == 1.5


class TestQuarterlyAdjustment:
    def test_normal_adjustment(self):
        base = 1.0
        daily = [10, 12, 8, 11, 9, 13, 7, 10, 11, 9,
                 10, 12, 8, 11, 9, 13, 7, 10, 11, 9,
                 10, 12, 8, 11, 9, 13, 7, 10]
        result = quarterly_adjustment(base, daily, velocity_score=0.1)
        assert 0.5 <= result <= 2.0
        assert result > base

    def test_no_volatility_returns_base(self):
        daily = [10.0] * 28
        result = quarterly_adjustment(1.0, daily, velocity_score=0.0)
        assert result == 1.0

    def test_clamping_low(self):
        result = quarterly_adjustment(0.5, [0.001, 0.001], velocity_score=0.0)
        assert result >= 0.5

    def test_clamping_high(self):
        daily = [100 if i % 2 == 0 else 1 for i in range(28)]
        result = quarterly_adjustment(2.0, daily, velocity_score=1.0)
        assert result <= 2.0

    def test_single_value_list(self):
        result = quarterly_adjustment(1.0, [10.0], velocity_score=0.0)
        assert result == 1.0

    def test_empty_list(self):
        result = quarterly_adjustment(1.0, [], velocity_score=0.0)
        assert result == 1.0

    def test_velocity_applies(self):
        daily = [10.0] * 28
        no_vel = quarterly_adjustment(1.0, daily, velocity_score=0.0)
        with_vel = quarterly_adjustment(1.0, daily, velocity_score=0.5)
        assert with_vel > no_vel


class TestSuppressionEngine:
    def test_fresh_engine_no_suppression(self):
        engine = SuppressionEngine()
        assert not engine.is_suppressed("ici", 3.0)

    def test_suppression_after_record(self):
        engine = SuppressionEngine()
        engine.record("ici", "p1", 3.0)
        assert engine.is_suppressed("ici", 3.0)

    def test_different_type_not_suppressed(self):
        engine = SuppressionEngine()
        engine.record("ici", "p1", 3.0)
        assert not engine.is_suppressed("sdi", -0.5)

    def test_cooldown_expires(self):
        engine = SuppressionEngine()
        past = datetime.now() - timedelta(days=10)
        engine.record("ici", "p1", 3.0, now=past)
        assert not engine.is_suppressed("ici", 3.0)

    def test_multiple_records(self):
        engine = SuppressionEngine()
        engine.record("ici", "p1", 2.1)
        engine.record("ici", "p2", 3.5)
        assert engine.is_suppressed("ici", 4.0)


class TestControversySpike:
    def test_triggers_on_high_z_score(self):
        monthly = [0.02, 0.018, 0.022, 0.019, 0.021, 0.017, 0.023]
        engine = SuppressionEngine()
        result = detect_controversy_spike(monthly, 0.08, engine)
        assert result is not None
        assert result.alert_type == "ici"
        assert result.severity >= 2

    def test_no_trigger_below_threshold(self):
        monthly = [0.02, 0.018, 0.022, 0.019, 0.021]
        engine = SuppressionEngine()
        result = detect_controversy_spike(monthly, 0.021, engine)
        assert result is None

    def test_insufficient_data(self):
        monthly = [0.02, 0.018]
        engine = SuppressionEngine()
        result = detect_controversy_spike(monthly, 0.05, engine)
        assert result is None

    def test_zero_std_returns_none(self):
        monthly = [0.02, 0.02, 0.02, 0.02]
        engine = SuppressionEngine()
        result = detect_controversy_spike(monthly, 0.05, engine)
        assert result is None

    def test_critical_at_3_sigma(self):
        monthly = [0.02, 0.018, 0.022, 0.019, 0.021, 0.017, 0.023]
        engine = SuppressionEngine()
        result = detect_controversy_spike(monthly, 0.15, engine)
        assert result is not None
        assert result.severity == 4

    def test_suppressed_by_cooldown(self):
        monthly = [0.02, 0.018, 0.022, 0.019, 0.021]
        engine = SuppressionEngine()
        engine.record("ici", "p1", 3.0)
        result = detect_controversy_spike(monthly, 0.08, engine)
        assert result is None


class TestSentimentDissonance:
    def test_triggers_on_sharp_decline(self):
        engine = SuppressionEngine()
        result = detect_sentiment_dissonance(0.3, 0.8, engine)
        assert result is not None
        assert result.alert_type == "sdi"

    def test_no_trigger_on_stable(self):
        engine = SuppressionEngine()
        result = detect_sentiment_dissonance(0.75, 0.8, engine)
        assert result is None

    def test_no_trigger_on_improvement(self):
        engine = SuppressionEngine()
        result = detect_sentiment_dissonance(0.9, 0.7, engine)
        assert result is None

    def test_edge_case_zero_prior(self):
        engine = SuppressionEngine()
        result = detect_sentiment_dissonance(-0.5, 0.0, engine)
        assert result is not None

    def test_suppressed(self):
        engine = SuppressionEngine()
        engine.record("sdi", "p1", -0.5)
        result = detect_sentiment_dissonance(0.2, 0.8, engine)
        assert result is None

    def test_small_decline_no_trigger(self):
        engine = SuppressionEngine()
        result = detect_sentiment_dissonance(0.7, 0.75, engine)
        assert result is None


class TestEngagementFugue:
    def test_triggers_on_sharp_drop(self):
        engine = SuppressionEngine()
        result = detect_engagement_fugue(0.02, 0.05, engine)
        assert result is not None
        assert result.alert_type == "efi"

    def test_no_trigger_on_stable(self):
        engine = SuppressionEngine()
        result = detect_engagement_fugue(0.045, 0.05, engine)
        assert result is None

    def test_no_trigger_on_increase(self):
        engine = SuppressionEngine()
        result = detect_engagement_fugue(0.06, 0.04, engine)
        assert result is None

    def test_suppressed(self):
        engine = SuppressionEngine()
        engine.record("efi", "p1", -0.5)
        result = detect_engagement_fugue(0.01, 0.05, engine)
        assert result is None

    def test_edge_zero_prior(self):
        engine = SuppressionEngine()
        result = detect_engagement_fugue(0.0, 0.0, engine)
        assert result is None


class TestTopicAnomaly:
    def test_triggers_on_high_angry_ratio(self):
        engine = SuppressionEngine()
        result = detect_topic_anomaly(0.15, 0.03, "seguridad", 10, engine)
        assert result is not None
        assert result.alert_type == "tai"

    def test_no_trigger_below_ratio(self):
        engine = SuppressionEngine()
        result = detect_topic_anomaly(0.04, 0.03, "seguridad", 10, engine)
        assert result is None

    def test_no_trigger_below_min_ratio(self):
        engine = SuppressionEngine()
        result = detect_topic_anomaly(0.02, 0.01, "seguridad", 10, engine)
        assert result is None

    def test_insufficient_posts(self):
        engine = SuppressionEngine()
        result = detect_topic_anomaly(0.2, 0.03, "seguridad", 1, engine)
        assert result is None

    def test_suppressed(self):
        engine = SuppressionEngine()
        engine.record("tai", "p1", 3.0)
        result = detect_topic_anomaly(0.15, 0.03, "seguridad", 10, engine)
        assert result is None


class TestZoneDissonance:
    def test_triggers_on_high_neg_rate(self):
        engine = SuppressionEngine()
        result = detect_zone_dissonance(0.4, "Norte", 10, engine)
        assert result is not None
        assert result.alert_type == "zdi"

    def test_no_trigger_below_threshold(self):
        engine = SuppressionEngine()
        result = detect_zone_dissonance(0.2, "Centro", 10, engine)
        assert result is None

    def test_insufficient_posts(self):
        engine = SuppressionEngine()
        result = detect_zone_dissonance(0.5, "Sur", 1, engine)
        assert result is None

    def test_suppressed(self):
        engine = SuppressionEngine()
        engine.record("zdi", "p1", 2.0)
        result = detect_zone_dissonance(0.4, "Norte", 10, engine)
        assert result is None


class TestPrioritizeAlerts:
    def test_critical_first(self):
        critical = AlertResult("ici", 4, "Crisis", "desc", 5.0, "controversia")
        medium = AlertResult("efi", 2, "Fuga", "desc", -0.5, "engagement")
        high = AlertResult("sdi", 3, "Disonancia", "desc", -0.4, "sentimiento")
        sorted_alerts = prioritize_alerts([medium, high, critical])
        assert sorted_alerts[0].severity == 4
        assert sorted_alerts[1].severity == 3
        assert sorted_alerts[2].severity == 2

    def test_same_severity_sorted_by_score(self):
        a1 = AlertResult("ici", 3, "A", "desc", 3.5, "controversia")
        a2 = AlertResult("ici", 3, "B", "desc", 2.5, "controversia")
        sorted_alerts = prioritize_alerts([a2, a1])
        assert sorted_alerts[0].score == 3.5


class TestIntegration:
    def test_run_all_detectors_empty(self):
        result = run_all_detectors([])
        assert result["alerts"] == []

    def test_run_all_detectors_few_posts(self):
        posts = [make_post() for _ in range(3)]
        result = run_all_detectors(posts)
        assert result["alerts"] == []

    def test_run_all_detectors_with_data(self):
        posts = []
        for i in range(30):
            p = make_post({
                "post_id": f"p{i}",
                "angrys_count": 0 if i < 25 else 20,
                "sads_count": 0 if i < 25 else 10,
                "sentiment": "positive" if i < 25 else "negative",
                "topic_category": "seguridad" if i < 15 else "corrupcion",
                "zona": "Centro" if i < 20 else "Norte",
                "created_time": (datetime.now() - timedelta(days=i)).isoformat(),
            })
            posts.append(p)
        result = run_all_detectors(posts)
        assert "alerts" in result
        assert "indices" in result
        assert "topic_sensitivity" in result

    def test_indices_computed_correctly(self):
        posts = [make_post({"likes_count": 100, "angrys_count": 10}) for _ in range(10)]
        result = run_all_detectors(posts)
        idx = result["indices"]
        assert idx["netSentiment"] > 0.5
        assert idx["controversy"] < 0.2
        assert idx["nsi"] > 0

    def test_topic_sensitivity_returns_all_topics(self):
        posts = [make_post({"topic_category": "seguridad"}) for _ in range(5)]
        posts += [make_post({"topic_category": "salud"}) for _ in range(3)]
        result = run_all_detectors(posts)
        ts = result["topic_sensitivity"]
        assert "seguridad" in ts
        assert "salud" in ts
        assert ts["seguridad"]["base"] == 1.2
        assert ts["salud"]["base"] == 1.1
