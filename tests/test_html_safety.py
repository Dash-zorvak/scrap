"""Tests for dashboard/html_safety.py — T2.1."""
from dashboard.html_safety import safe_text, safe_list


class TestSafeText:
    def test_escapes_script_tag(self):
        result = safe_text('<script>alert(1)</script>')
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_none_returns_empty(self):
        assert safe_text(None) == ""

    def test_int_coerced_to_str(self):
        assert safe_text(123) == "123"

    def test_normal_text_unchanged(self):
        assert safe_text("hola mundo") == "hola mundo"

    def test_html_entities_escaped(self):
        result = safe_text('a < b & c > "d"')
        assert "&lt;" in result
        assert "&amp;" in result
        assert "&gt;" in result
        assert "&#34;" in result or "&quot;" in result

    def test_empty_string(self):
        assert safe_text("") == ""

    def test_float(self):
        assert safe_text(3.14) == "3.14"


class TestSafeList:
    def test_escapes_all_items(self):
        items = ["<b>bold</b>", None, "normal"]
        result = safe_list(items)
        assert len(result) == 3
        assert "&lt;b&gt;" in result[0]
        assert result[1] == ""
        assert result[2] == "normal"

    def test_none_input(self):
        assert safe_list(None) == []

    def test_empty_list(self):
        assert safe_list([]) == []
