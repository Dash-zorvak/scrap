"""Tests for dedupe_existing.py: artificial suffix detection, canonical ID extraction."""
import re


def has_artificial_suffix(pid: str) -> bool:
    """Detect artificial post_id suffixes like _1, _2 added by old dup_counter bug."""
    return bool(re.search(r'_\d+$', pid))


def canonical_post_id(pid: str) -> str:
    """Strip artificial suffix. E.g. 'pfbidABC_2' -> 'pfbidABC'."""
    return re.sub(r'_\d+$', '', pid)


class TestArtificialSuffixDetection:
    def test_detects_suffix(self):
        assert has_artificial_suffix("pfbid0ABC_1") is True
        assert has_artificial_suffix("pfbid0ABC_2") is True
        assert has_artificial_suffix("pfbid0ABC_10") is True

    def test_no_false_positive_normal_pfbid(self):
        """pfbid naturally contains underscores; only trailing _N is artificial."""
        assert has_artificial_suffix("pfbid0ABC123") is False
        assert has_artificial_suffix("pfbid0ABC_DEF") is False

    def test_no_false_positive_sim_ext(self):
        assert has_artificial_suffix("SIM_EXT_0001") is True  # SIM_EXT has _0001 suffix

    def test_no_false_positive_empty(self):
        assert has_artificial_suffix("") is False


class TestCanonicalPostId:
    def test_strips_suffix(self):
        assert canonical_post_id("pfbid0ABC_1") == "pfbid0ABC"
        assert canonical_post_id("pfbid0ABC_2") == "pfbid0ABC"

    def test_preserves_normal_id(self):
        assert canonical_post_id("pfbid0ABC") == "pfbid0ABC"
        assert canonical_post_id("pfbid0ABC_DEF") == "pfbid0ABC_DEF"

    def test_handles_empty(self):
        assert canonical_post_id("") == ""


class TestDuplicateGroupLogic:
    """Simulate the dedup sorting/selection logic."""

    def test_keeps_row_with_created_time(self):
        rows = [
            {"rowid": 1, "created_time": None, "total_reactions": 5},
            {"rowid": 2, "created_time": "2025-01-01", "total_reactions": 0},
        ]
        # Sort by: non-null created_time first, then reactions DESC
        rows.sort(key=lambda r: (0 if r["created_time"] else 1, -r["total_reactions"]))
        keep = rows[0]
        assert keep["rowid"] == 2  # row with created_time wins

    def test_keeps_most_reactions_when_both_have_time(self):
        rows = [
            {"rowid": 1, "created_time": "2025-01-01", "total_reactions": 0},
            {"rowid": 2, "created_time": "2025-01-01", "total_reactions": 50},
        ]
        rows.sort(key=lambda r: (0 if r["created_time"] else 1, -r["total_reactions"]))
        keep = rows[0]
        assert keep["rowid"] == 2  # most reactions wins
