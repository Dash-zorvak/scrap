"""Regresion: cada video de TikTok debe ser una fila independiente.

Reproduce el bug de IDs colisionados: al subir varios videos de la misma cuenta
y fecha con descripcion vacia (y metricas en 0, como suele devolver el modelo de
vision), todos compartian el mismo hash -> el mismo id -> insertar_video
(INSERT OR REPLACE) sobreescribia las filas (cada nueva subida pisaba la
anterior). Aqui validamos el escenario exacto reportado: varios videos de la
Alcaldia + varios del Alcalde, sin que ninguno reemplace a otro, y que el numero
de filas coincide con el numero de videos procesados.
"""
import os
import sqlite3
import tempfile

import pytest


def _item(datos: dict, tmp_id: str) -> dict:
    return {"id_temporal": tmp_id, "estado": "revisado", "datos_revisados": datos}


def _video(account_id: int, created_at: str, description: str = "",
           views: int = 0, likes: int = 0, favorites_count: int = 0,
           shares: int = 0, comments_count: int = 0) -> dict:
    return {
        "plataforma": "tiktok",
        "account_id": account_id,
        "description": description,
        "created_at": created_at,
        "views": views,
        "likes": likes,
        "favorites_count": favorites_count,
        "shares": shares,
        "comments_count": comments_count,
        "comentarios": [],
    }


class TestTikTokIdUnico:
    @pytest.fixture(autouse=True)
    def _temp_dbs(self, monkeypatch):
        self.fb_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.fb_tmp.close()
        self.tk_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tk_tmp.close()
        self.ext_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.ext_tmp.close()
        import dashboard.config as cfg
        monkeypatch.setattr(cfg, "FACEBOOK_DB", self.fb_tmp.name)
        monkeypatch.setattr(cfg, "TIKTOK_DB", self.tk_tmp.name)
        monkeypatch.setattr(cfg, "EXTERNOS_DB", self.ext_tmp.name)
        yield
        for p in (self.fb_tmp.name, self.tk_tmp.name, self.ext_tmp.name):
            try:
                os.unlink(p)
            except OSError:
                pass

    def _count_videos(self) -> int:
        conn = sqlite3.connect(self.tk_tmp.name)
        try:
            return conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        finally:
            conn.close()

    def test_escenario_reportado_alcaldia_luego_alcalde(self):
        """4 videos Alcaldia (account 1) + 4 del Alcalde (account 3), descripcion
        vacia y metricas en 0, subidos de a uno como en la UI. Deben quedar 8
        filas y ninguna debe ser reemplazada."""
        from dashboard.guardar_lote import guardar_lote
        total = 0
        for i in range(4):
            res = guardar_lote([_item(_video(1, "2026-06-20"), f"alc-{i}")])
            assert res["tk_videos"] == 1
            assert res["errores"] == []
            total += 1
            assert self._count_videos() == total
        for i in range(4):
            res = guardar_lote([_item(_video(3, "2026-06-22"), f"alcde-{i}")])
            assert res["tk_videos"] == 1
            assert res["errores"] == []
            total += 1
            assert self._count_videos() == total
        assert self._count_videos() == 8

    def test_lote_unico_varios_videos_misma_cuenta_sin_descripcion(self):
        """Varios videos de la misma cuenta/fecha sin descripcion en un mismo
        lote: cada uno es una fila propia."""
        from dashboard.guardar_lote import guardar_lote
        lote = [_item(_video(3, "2026-06-22"), f"v-{i}") for i in range(5)]
        res = guardar_lote(lote)
        assert res["tk_videos"] == 5
        assert res["errores"] == []
        assert self._count_videos() == 5

    def test_resubir_mismo_video_con_descripcion_deduplica(self):
        """Con descripcion (identidad fiable) re-subir el mismo video reutiliza el
        id -> upsert -> 1 sola fila, igual que en Facebook."""
        from dashboard.guardar_lote import guardar_lote
        v = _video(1, "2026-06-20", description="Inauguracion del parque central")
        guardar_lote([_item(dict(v), "a")])
        guardar_lote([_item(dict(v), "b")])
        assert self._count_videos() == 1

    def test_videos_distintos_con_descripcion_no_colisionan(self):
        """Dos videos con descripciones distintas (misma cuenta/fecha) generan
        dos filas: nunca se sobrescriben."""
        from dashboard.guardar_lote import guardar_lote
        v1 = _video(1, "2026-06-20", description="Inauguracion del parque")
        v2 = _video(1, "2026-06-20", description="Reunion con vecinos del sector")
        guardar_lote([_item(v1, "a"), _item(v2, "b")])
        assert self._count_videos() == 2
