"""Tests: _CACHE_MAX eviction policy for dash_narrativa."""
import time

from dashboard import dash_narrativa as dn


class TestCacheMax:
    def _poblar(self, n, base_ts=1000.0):
        for i in range(n):
            dn._guardar_cache(f"k{i}", (f"v{i}", False, base_ts + i))

    def test_respeta_tope_con_mas_de_500_claves(self):
        dn._CACHE.clear()
        self._poblar(600)
        assert len(dn._CACHE) <= dn._CACHE_MAX

    def test_desaloja_la_mas_vieja_primero(self):
        dn._CACHE.clear()
        self._poblar(dn._CACHE_MAX + 10)
        # Las primeras 10 claves (k0..k9) deberian haber sido desalojadas
        for i in range(10):
            assert f"k{i}" not in dn._CACHE, f"k{i} debio ser desalojada"
        # k500+ debe estar presente
        assert f"k{dn._CACHE_MAX + 9}" in dn._CACHE

    def test_sin_cambios_con_menos_de_500_claves(self):
        dn._CACHE.clear()
        n = dn._CACHE_MAX - 10
        self._poblar(n)
        assert len(dn._CACHE) == n
        for i in range(n):
            assert f"k{i}" in dn._CACHE
