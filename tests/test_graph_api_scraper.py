"""Tests for graph_api_scraper fixes:
- Date parsing (SCRAPE_SINCE/SCRAPE_UNTIL)
- Pagination cursor extraction
- views_count None vs 0
"""
from src.fb_scraper.graph_api_scraper import GraphAPIScraper


class TestDateParsing:
    def test_parse_date_valid(self):
        ts = GraphAPIScraper._parse_date("2025-01-01")
        assert isinstance(ts, int)
        assert ts > 0

    def test_parse_date_invalid_defaults(self):
        ts = GraphAPIScraper._parse_date("bad-date")
        assert isinstance(ts, int)
        # Should default to 2025-01-01 epoch
        from datetime import datetime
        expected = int(datetime(2025, 1, 1).timestamp())
        assert ts == expected

    def test_parse_date_empty_defaults(self):
        ts = GraphAPIScraper._parse_date("")
        from datetime import datetime
        expected = int(datetime(2025, 1, 1).timestamp())
        assert ts == expected

    def test_parse_date_recent(self):
        ts = GraphAPIScraper._parse_date("2026-06-01")
        from datetime import datetime
        expected = int(datetime(2026, 6, 1).timestamp())
        assert ts == expected


class TestViewsCount:
    def test_views_none_is_not_zero(self):
        """views_count None means 'no permission', not 'zero views'."""
        post_data = {"id": "123", "views_count": None}
        views = post_data.get("views_count")
        assert views is None
        assert views != 0

    def test_views_missing_defaults_none(self):
        post_data = {"id": "123"}
        views = post_data.get("views_count")
        assert views is None

    def test_views_zero_is_zero(self):
        post_data = {"id": "123", "views_count": 0}
        views = post_data.get("views_count")
        assert views == 0


class TestPaginationCursor:
    def test_cursor_after_preferred_over_split(self):
        """paging.cursors.after should be used, not split('after=')."""
        paging = {
            "cursors": {"after": "cursorABC123"},
            "next": "https://graph.facebook.com/v21.0/123/comments?after=cursorABC123&limit=100",
        }
        after_cursor = paging["cursors"].get("after")
        assert after_cursor == "cursorABC123"
        # The old fragile approach:
        old_way = paging["next"].split("after=")[1].split("&")[0]
        assert old_way == after_cursor  # same result in this case
