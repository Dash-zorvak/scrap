"""Test de la mejora: guardar_lote reporta progreso incremental.

Verifica que guardar_lote invoca el callback de progreso una vez por cada item
revisado, de modo que la UI pueda mostrar un contador real (i/n) en vez de
quedarse congelada en 0/n hasta el final.
"""
import os
import tempfile

import pytest


_FB = {
    "plataforma": "facebook",
    "page_name": "Alcaldía de Santa Ana",
    "message": "Texto de prueba",
    "created_time": "2026-05-12T00:00:00",
    "comments_count": 0,
    "comentarios": [],
    "muestra_suficiente": True,
}


class TestProgresoGuardarLote:
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
        os.unlink(self.fb_tmp.name)
        os.unlink(self.tk_tmp.name)
        os.unlink(self.ext_tmp.name)

    def _item(self, idx):
        datos = dict(_FB, page_name=f"Página {idx}")
        return {
            "id_temporal": f"t{idx}",
            "estado": "revisado",
            "datos_revisados": datos,
        }

    def test_callback_una_vez_por_item(self):
        from dashboard.guardar_lote import guardar_lote
        lote = [self._item(i) for i in range(3)]
        eventos = []
        guardar_lote(
            lote,
            progreso_cb=lambda i, total, etq: eventos.append((i, total, etq)),
        )
        assert [e[0] for e in eventos] == [1, 2, 3]
        assert all(e[1] == 3 for e in eventos)

    def test_callback_opcional(self):
        # Sin callback no debe fallar (compatibilidad hacia atrás).
        from dashboard.guardar_lote import guardar_lote
        res = guardar_lote([self._item(0)])
        assert res["fb_posts"] == 1

    def test_callback_recibe_etiqueta(self):
        from dashboard.guardar_lote import guardar_lote
        lote = [self._item(7)]
        eventos = []
        guardar_lote(
            lote,
            progreso_cb=lambda i, total, etq: eventos.append(etq),
        )
        assert eventos == ["Página 7"]
