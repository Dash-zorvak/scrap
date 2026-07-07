"""Tests: sugerir_candidatos y sugerir_no_traccion warn al no encontrar oficiales."""
import datetime as dt
import logging

from dashboard import medalla_seleccion as msel

INI = dt.datetime(2026, 7, 1)
FIN = dt.datetime(2026, 7, 31)

_POST_NO_OFICIAL = {
    "post_id": "p1", "page_name": "Ciudadano X",
    "message": "texto", "created_time": "2026-07-05 12:00:00",
    "likes_count": 10, "loves_count": 5, "cares_count": 0,
    "hahas_count": 0, "wows_count": 0, "sads_count": 0, "angrys_count": 0,
    "comments_count": 2, "shares_count": 1,
}
_POST_OFICIAL = {**_POST_NO_OFICIAL, "post_id": "p2", "page_name": "Alcaldía de Santa Ana"}


def _mock_posts(*posts):
    return lambda inicio, fin, db_path=None: list(posts)


class TestSugerirCandidatosWarning:

    def test_sin_oficiales_emite_warning(self, monkeypatch, caplog):
        """Hay posts pero ninguno oficial → warning y usa no oficiales."""
        monkeypatch.setattr(msel, "_leer_posts_fb", _mock_posts(_POST_NO_OFICIAL))
        caplog.set_level(logging.WARNING)
        _, _, candidatos = msel.sugerir_candidatos("2026-07", fecha_ref=FIN, db_path=":memory:")
        assert len(candidatos) == 1
        assert candidatos[0]["post_id"] == "p1"
        assert any("No se encontraron posts oficiales" in r.message for r in caplog.records)

    def test_con_oficiales_no_emite_warning(self, monkeypatch, caplog):
        """Hay posts oficiales → no warning."""
        monkeypatch.setattr(msel, "_leer_posts_fb", _mock_posts(_POST_OFICIAL))
        caplog.set_level(logging.WARNING)
        _, _, candidatos = msel.sugerir_candidatos("2026-07", fecha_ref=FIN, db_path=":memory:")
        assert len(candidatos) == 1
        assert candidatos[0]["post_id"] == "p2"
        assert len(caplog.records) == 0

    def test_sin_posts_no_rompe_ni_emite_warning(self, monkeypatch, caplog):
        """No hay posts en absoluto → sin warning, sin crash."""
        monkeypatch.setattr(msel, "_leer_posts_fb", _mock_posts())
        caplog.set_level(logging.WARNING)
        _, _, candidatos = msel.sugerir_candidatos("2026-07", fecha_ref=FIN, db_path=":memory:")
        assert candidatos == []
        assert len(caplog.records) == 0


class TestSugerirNoTraccionWarning:

    def test_sin_oficiales_emite_warning(self, monkeypatch, caplog):
        monkeypatch.setattr(msel, "_leer_posts_fb", _mock_posts(_POST_NO_OFICIAL))
        caplog.set_level(logging.WARNING)
        candidatos = msel.sugerir_no_traccion(INI, FIN, db_path=":memory:")
        assert len(candidatos) == 1
        assert candidatos[0]["post_id"] == "p1"
        assert any("No se encontraron posts oficiales" in r.message for r in caplog.records)

    def test_con_oficiales_no_emite_warning(self, monkeypatch, caplog):
        monkeypatch.setattr(msel, "_leer_posts_fb", _mock_posts(_POST_OFICIAL))
        caplog.set_level(logging.WARNING)
        candidatos = msel.sugerir_no_traccion(INI, FIN, db_path=":memory:")
        assert len(candidatos) == 1
        assert candidatos[0]["post_id"] == "p2"
        assert len(caplog.records) == 0

    def test_sin_posts_no_rompe_ni_emite_warning(self, monkeypatch, caplog):
        monkeypatch.setattr(msel, "_leer_posts_fb", _mock_posts())
        caplog.set_level(logging.WARNING)
        candidatos = msel.sugerir_no_traccion(INI, FIN, db_path=":memory:")
        assert candidatos == []
        assert len(caplog.records) == 0
