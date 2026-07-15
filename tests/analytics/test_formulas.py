"""Tests para las fórmulas §D-I del Bloque 6 (compute.py + report.py wiring).

Cada test verifica una fórmula con números conocidos verificados a mano.
Incluye test de aislamiento cruzado FB/TK (§J).
"""
import math
import pytest

from analytics.compute import (
    engagement_rate_fb, engagement_rate_tk, ratio_amor_enojo_fb,
    reacciones_positivas_fb, reacciones_negativas_fb,
    net_sentiment_index, controversy_index, effectiveness_index,
    approval_pct, rejection_pct, vol_factor, risk_reputacional,
    _detectar_alertas, calcular_hhi,
    calcular_pulso_iq_fb, calcular_pulso_iq_tk,
    pulso_iq_score, pulso_iq_cuadrante,
    coeficiente_variacion, autenticidad_pct,
)
from analytics.report import construir_analysis


# ═══════════════════════════════════════════════════════════════════════════════
# §D — Engagement
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngagementFB:
    def test_fb_con_vistas(self):
        """100 likes, 10 loves, 5 hahas, 2 sads, 3 angrys, 5 comments, 15 shares, 500 vistas
        reacciones=120, engagement=120+5+15=140, ER=140/500*100=28.0%"""
        er, basis = engagement_rate_fb(
            likes=100, loves=10, cares=0, hahas=5,
            wows=0, sads=2, angrys=3,
            comments=5, shares=15, views=500,
        )
        assert er == 28.0
        assert basis == "vistas"

    def test_fb_sin_vistas(self):
        """Sin vistas → engagement absoluto como proxy."""
        er, basis = engagement_rate_fb(
            likes=50, loves=5, cares=0, hahas=0,
            wows=0, sads=0, angrys=0,
            comments=10, shares=20, views=0,
        )
        assert er == 85.0  # 50+5+0+0+0+0+0 + 10 + 20 = 85
        assert basis == "engagement_abs"

    def test_fb_cero_engagement(self):
        er, basis = engagement_rate_fb(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        assert er == 0.0
        assert basis == "sin_datos"


class TestEngagementTK:
    def test_tk_con_vistas(self):
        """200 likes, 10 shares, 5 favorites, 8 comments, 1000 vistas
        ER = (200+10+5+8)/1000*100 = 22.3%"""
        er, basis = engagement_rate_tk(
            views=1000, likes=200, shares=10, favorites=5, comments=8,
        )
        assert er == 22.3
        assert basis == "vistas"

    def test_tk_sin_vistas(self):
        er, basis = engagement_rate_tk(0, 50, 5, 3, 10)
        assert er == 68.0  # 50+5+3+10
        assert basis == "engagement_abs"


class TestRatioAmorEnojo:
    def test_ratio_normal(self):
        """(100 likes + 20 loves + 10 cares) / (5 angrys + 3 sads + 2 hahas)
        = 130 / 10 = 13.0"""
        r = ratio_amor_enojo_fb(100, 20, 10, 2, 3, 5)
        assert r == 13.0

    def test_ratio_sin_enojo(self):
        """Sin enojo pero con amor → 999.0"""
        r = ratio_amor_enojo_fb(50, 10, 5, 0, 0, 0)
        assert r == 999.0

    def test_ratio_cero(self):
        """Sin amor ni enojo → 0.0"""
        r = ratio_amor_enojo_fb(0, 0, 0, 0, 0, 0)
        assert r == 0.0


class TestReacciones:
    def test_positivas(self):
        assert reacciones_positivas_fb(100, 20, 10) == 130

    def test_negativas(self):
        assert reacciones_negativas_fb(5, 3, 2) == 10


# ═══════════════════════════════════════════════════════════════════════════════
# §E — Indices
# ═══════════════════════════════════════════════════════════════════════════════

class TestNetSentimentIndex:
    def test_nsi_positivo(self):
        """(70-30)/100*100 = 40.0"""
        assert net_sentiment_index(70, 30, 100) == 40.0

    def test_nsi_negativo(self):
        """(20-80)/100*100 = -60.0"""
        assert net_sentiment_index(20, 80, 100) == -60.0

    def test_nsi_cero(self):
        assert net_sentiment_index(0, 0, 0) == 0.0

    def test_nsi_neutral(self):
        """(50-50)/100*100 = 0.0"""
        assert net_sentiment_index(50, 50, 100) == 0.0


class TestControversyIndex:
    def test_normal(self):
        """min(60,40)/max(60,40) = 40/60 = 0.667"""
        assert controversy_index(60, 40) == 0.667

    def test_sin_controversia(self):
        assert controversy_index(100, 0) == 0.0

    def test_maxima(self):
        assert controversy_index(50, 50) == 1.0

    def test_cero_ambos(self):
        assert controversy_index(0, 0) == 0.0


class TestEffectivenessIndex:
    def test_normal(self):
        """tono_score=20, n_comentarios=100, n_posts=10
        EI = 20 * log(101)/log(11) ≈ 20 * 4.615/2.398 ≈ 20 * 1.925 = 38.5"""
        ei = effectiveness_index(20, 100, 10)
        assert 38.0 <= ei <= 39.0

    def test_cero_posts(self):
        assert effectiveness_index(10, 50, 0) == 0.0


class TestApprovalRejection:
    def test_approval(self):
        """60% favorable + 0.5*20% neutral = 70.0"""
        assert approval_pct(60, 20) == 70.0

    def test_rejection(self):
        """40% crítico + 0.5*20% neutral = 50.0"""
        assert rejection_pct(40, 20) == 50.0


class TestVolFactor:
    def test_spike(self):
        assert vol_factor(150, 100) == 1.5

    def test_promedio_cero(self):
        assert vol_factor(100, 0) == 1.0


class TestRiskReputacional:
    def test_bajo(self):
        """10% crítico, 5% angrys, HHI bajo (0.1)
        RR = (0.1*0.4 + 0.05*0.3 + 0.1*0.3)*100 = (0.04+0.015+0.03)*100 = 8.5"""
        rr = risk_reputacional(10, 0.05, 0.1)
        assert rr == 8.5

    def test_alto(self):
        """80% crítico, 40% angrys, HHI alto (0.8)
        RR = (0.8*0.4 + 0.4*0.3 + 0.8*0.3)*100 = (0.32+0.12+0.24)*100 = 68.0"""
        rr = risk_reputacional(80, 0.4, 0.8)
        assert rr == 68.0


# ═══════════════════════════════════════════════════════════════════════════════
# §F — Alertas
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertas:
    def test_alerta_ici(self):
        """35% crítico > umbral 30% → ICI activada"""
        alertas = _detectar_alertas(35, 0.05, 0.1)
        tipos = [a["tipo"] for a in alertas]
        assert "ICI" in tipos

    def test_alerta_sdi(self):
        """55% crítico > umbral 50% → SDI activada"""
        alertas = _detectar_alertas(55, 0.05, 0.1)
        tipos = [a["tipo"] for a in alertas]
        assert "SDI" in tipos

    def test_alerta_efi(self):
        """20% angrys > umbral 15% → EFI activada"""
        alertas = _detectar_alertas(20, 0.20, 0.1)
        tipos = [a["tipo"] for a in alertas]
        assert "EFI" in tipos

    def test_alerta_tai(self):
        """controversy 0.5 > umbral 0.4 → TAI activada"""
        alertas = _detectar_alertas(20, 0.05, 0.5)
        tipos = [a["tipo"] for a in alertas]
        assert "TAI" in tipos

    def test_sin_alertas(self):
        """Valores bajos → sin alertas"""
        alertas = _detectar_alertas(5, 0.01, 0.05)
        assert len(alertas) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# §G — HHI
# ═══════════════════════════════════════════════════════════════════════════════

class TestHHI:
    def test_un_tema(self):
        """100% en un tema → HHI = 1.0"""
        assert calcular_hhi([100]) == 1.0

    def test_dos_temas_iguales(self):
        """50/50 → (0.5² + 0.5²) = 0.5"""
        assert calcular_hhi([50, 50]) == 0.5

    def test_tres_temas(self):
        """60/30/10 → 0.36+0.09+0.01 = 0.46"""
        hhi = calcular_hhi([60, 30, 10])
        assert hhi == 0.46

    def test_cero_temas(self):
        assert calcular_hhi([]) == 0.0

    def test_suma_100(self):
        """Shares que suman 100 → verificación básica."""
        hhi = calcular_hhi([40, 30, 20, 10])
        assert 0.0 < hhi < 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# §H — Pulso IQ
# ═══════════════════════════════════════════════════════════════════════════════

class TestPulsoIQ:
    def test_fb_dimensions(self):
        dims = calcular_pulso_iq_fb(
            pct_favorable=60, pct_critico=20, n_comentarios=100,
            n_posts=10, shares=[40, 30, 20, 10], tono_score=40,
        )
        assert isinstance(dims, dict)
        assert len(dims) == 7
        for d in dims:
            assert 0 <= dims[d] <= 100

    def test_tk_dimensions(self):
        dims = calcular_pulso_iq_tk(
            pct_favorable=50, pct_critico=30, n_comentarios=50,
            n_videos=5, shares=[60, 40], tono_score=20,
        )
        assert len(dims) == 7

    def test_score_fb_only(self):
        """Solo FB → score usa 100% FB."""
        dims_fb = {
            "aprobacion": 60, "conexion": 40, "tranquilidad": 70,
            "diversidad": 50, "presencia": 30, "consistencia": 50,
            "atencion": 45,
        }
        score, combined = pulso_iq_score(dims_fb, None)
        assert 0 < score < 100
        assert combined == dims_fb

    def test_score_ponderado(self):
        """FB + TK → ponderado por volumen."""
        dims_fb = {
            "aprobacion": 60, "conexion": 40, "tranquilidad": 70,
            "diversidad": 50, "presencia": 30, "consistencia": 50,
            "atencion": 45,
        }
        dims_tk = {
            "aprobacion": 80, "conexion": 60, "tranquilidad": 50,
            "diversidad": 70, "presencia": 50, "consistencia": 50,
            "atencion": 55,
        }
        score, combined = pulso_iq_score(dims_fb, dims_tk)
        assert 0 < score < 100
        # aprobacion: 60*0.6 + 80*0.4 = 36+32 = 68
        assert combined["aprobacion"] == 68.0

    def test_cuadrante_liderazgo(self):
        dims = {
            "aprobacion": 70, "conexion": 60, "presencia": 50,
            "tranquilidad": 60, "consistencia": 55,
        }
        assert pulso_iq_cuadrante(65, dims) == "LIDERAZGO"

    def test_cuadrante_crisis(self):
        dims = {
            "aprobacion": 30, "conexion": 20, "presencia": 30,
            "tranquilidad": 30, "consistencia": 40,
        }
        assert pulso_iq_cuadrante(25, dims) == "CRISIS"

    def test_cuadrante_vacio(self):
        assert pulso_iq_cuadrante(50, {}) == ""


# ═══════════════════════════════════════════════════════════════════════════════
# §I — Autenticidad
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutenticidad:
    def test_estable(self):
        """Volumen estable (CV bajo) → orgánico 100%."""
        cv, organico = coeficiente_variacion([10, 11, 9, 10, 12])
        assert cv < 0.5
        assert organico is True

    def test_volatil(self):
        """Volumen muy volátil (CV alto) → coordinado."""
        cv, organico = coeficiente_variacion([1, 100, 2, 90, 1])
        assert cv > 0.5
        assert organico is False

    def test_autenticidad_pct_estable(self):
        org, coord = autenticidad_pct([10, 11, 9, 10, 12])
        assert org == 100.0
        assert coord == 0.0

    def test_autenticidad_pct_volatil(self):
        org, coord = autenticidad_pct([1, 100, 2, 90, 1])
        assert org < 100.0
        assert coord > 0.0

    def test_un_solo_dia(self):
        """Un solo día → no hay variación → orgánico."""
        cv, organico = coeficiente_variacion([50])
        assert cv == 0.0
        assert organico is True


# ═══════════════════════════════════════════════════════════════════════════════
# §J — Aislamiento FB/TK (no mezclar fórmulas de plataformas distintas)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAislamientoPlataformas:
    def test_fb_no_usa_tk_engagement_rate(self):
        """ER Facebook no debe considerar likes de TikTok."""
        er_fb, _ = engagement_rate_fb(
            likes=100, loves=0, cares=0, hahas=0,
            wows=0, sads=0, angrys=0,
            comments=0, shares=0, views=1000,
        )
        er_tk, _ = engagement_rate_tk(
            views=1000, likes=200, shares=0, favorites=0, comments=0,
        )
        # FB: (100+0)/1000*100 = 10.0
        # TK: (200+0)/1000*100 = 20.0
        # Son independientes
        assert er_fb == 10.0
        assert er_tk == 20.0
        assert er_fb != er_tk

    def test_ratio_amor_enojo_fb_no_usa_tk(self):
        """Ratio amor/enojo solo usa reacciones FB, no TK."""
        r_fb = ratio_amor_enojo_fb(100, 0, 0, 0, 0, 10)
        r_fb2 = ratio_amor_enojo_fb(100, 0, 0, 0, 0, 10)
        # Misma fórmula, mismos datos → mismo resultado
        assert r_fb == r_fb2 == 10.0

    def test_wiring_fb_stats(self):
        """construir_analysis con fb_stats → métricas reales, no zeros."""
        aprob = [{"categoria": "test", "label": "Test", "pct": 100,
                  "doc_count": 10, "apoyo": 5, "critica": 3, "neutral": 2,
                  "pct_apoyo": 50, "pct_critica": 30, "pct_neutral": 20,
                  "saldo": 2, "ejemplo": "", "ejemplo_critica": "",
                  "emociones": {}, "emocion_dominante": "calma"}]
        fb = {
            "posts": 5, "likes": 100, "loves": 20, "cares": 5,
            "hahas": 10, "wows": 3, "sads": 2, "angrys": 1,
            "comments": 30, "shares": 50, "views": 2000,
            "total_reacciones": 141, "engagement": 221,
        }
        data = construir_analysis(aprob, "2026-07", "2026-07-14", fb_stats=fb)
        mr = data["bloque1"]["metricas_rendimiento"]
        assert mr["engagement_rate"] > 0
        assert mr["reacciones_positivas"] == 125  # 100+20+5
        assert mr["reacciones_negativas"] == 13   # 1+2+10
        assert mr["ratio_amor_enojo"] == round(125 / 13, 2)
        assert mr["engagementBasis"] == "vistas"

    def test_wiring_tk_stats(self):
        """construir_analysis con tk_stats → métricas TikTok."""
        aprob = [{"categoria": "test", "label": "Test", "pct": 100,
                  "doc_count": 10, "apoyo": 5, "critica": 3, "neutral": 2,
                  "pct_apoyo": 50, "pct_critica": 30, "pct_neutral": 20,
                  "saldo": 2, "ejemplo": "", "ejemplo_critica": "",
                  "emociones": {}, "emocion_dominante": "calma"}]
        tk = {
            "videos": 3, "views": 5000, "likes": 300,
            "shares": 20, "favorites": 10, "comments": 40,
            "engagement": 370,
        }
        data = construir_analysis(aprob, "2026-07", "2026-07-14", tk_stats=tk)
        mr = data["bloque1"]["metricas_rendimiento"]
        assert mr["engagement_rate"] > 0
        assert mr["engagementBasis"] == "vistas"

    def test_wiring_both_platforms_ponderado(self):
        """FB + TK → ER ponderado por volumen real (§J)."""
        aprob = [{"categoria": "test", "label": "Test", "pct": 100,
                  "doc_count": 10, "apoyo": 5, "critica": 3, "neutral": 2,
                  "pct_apoyo": 50, "pct_critica": 30, "pct_neutral": 20,
                  "saldo": 2, "ejemplo": "", "ejemplo_critica": "",
                  "emociones": {}, "emocion_dominante": "calma"}]
        fb = {
            "posts": 5, "likes": 100, "loves": 0, "cares": 0,
            "hahas": 0, "wows": 0, "sads": 0, "angrys": 0,
            "comments": 0, "shares": 0, "views": 1000,
            "total_reacciones": 100, "engagement": 100,
        }
        tk = {
            "videos": 3, "views": 2000, "likes": 200,
            "shares": 0, "favorites": 0, "comments": 0,
            "engagement": 200,
        }
        data = construir_analysis(
            aprob, "2026-07", "2026-07-14", fb_stats=fb, tk_stats=tk,
        )
        mr = data["bloque1"]["metricas_rendimiento"]
        # ER_fb = 100/1000*100 = 10.0
        # ER_tk = 200/2000*100 = 10.0
        # Ponderado: 10.0*(100/300) + 10.0*(200/300) = 10.0
        assert mr["engagement_rate"] == 10.0
        assert mr["engagementBasis"] == "ponderado_volumen"
        assert data["meta"]["plataforma"] == "multicanal"


# ═══════════════════════════════════════════════════════════════════════════════
# Wiring: campos poblados en construir_analysis
# ═══════════════════════════════════════════════════════════════════════════════

class TestWiringCampos:
    def test_concentracion_tematica_hhi(self):
        """concentracion_tematica debe tener hhi, top_tema, n_temas."""
        aprob = [
            {"categoria": "seg", "label": "Seg", "pct": 60, "doc_count": 60,
             "apoyo": 30, "critica": 20, "neutral": 10, "pct_apoyo": 50,
             "pct_critica": 33.3, "pct_neutral": 16.7, "saldo": 10,
             "ejemplo": "", "ejemplo_critica": "", "emociones": {},
             "emocion_dominante": "calma"},
            {"categoria": "mov", "label": "Mov", "pct": 40, "doc_count": 40,
             "apoyo": 20, "critica": 10, "neutral": 10, "pct_apoyo": 50,
             "pct_critica": 25, "pct_neutral": 25, "saldo": 10,
             "ejemplo": "", "ejemplo_critica": "", "emociones": {},
             "emocion_dominante": "calma"},
        ]
        data = construir_analysis(aprob, "2026-07", "2026-07-14")
        ct = data["bloque1"]["concentracion_tematica"]
        assert "hhi" in ct
        assert ct["hhi"] > 0
        assert ct["top_tema"] == "seg"
        assert ct["n_temas"] == 2
        assert "formula_usada" in ct

    def test_pulso_iq_campos(self):
        """pulso_iq debe tener valor, cuadrante, componentes."""
        aprob = [{"categoria": "test", "label": "T", "pct": 100,
                  "doc_count": 10, "apoyo": 5, "critica": 3, "neutral": 2,
                  "pct_apoyo": 50, "pct_critica": 30, "pct_neutral": 20,
                  "saldo": 2, "ejemplo": "", "ejemplo_critica": "",
                  "emociones": {}, "emocion_dominante": "calma"}]
        data = construir_analysis(aprob, "2026-07", "2026-07-14")
        iq = data["bloque1"]["pulso_iq"]
        assert "valor" in iq
        assert "cuadrante" in iq
        assert "componentes" in iq
        assert isinstance(iq["componentes"], dict)

    def test_polarizacion_indice(self):
        """polarizacion debe tener indice numérico."""
        aprob = [
            {"categoria": "a", "label": "A", "pct": 50, "doc_count": 50,
             "apoyo": 40, "critica": 10, "neutral": 0, "pct_apoyo": 80,
             "pct_critica": 20, "pct_neutral": 0, "saldo": 30,
             "ejemplo": "", "ejemplo_critica": "", "emociones": {},
             "emocion_dominante": "calma"},
            {"categoria": "b", "label": "B", "pct": 50, "doc_count": 50,
             "apoyo": 10, "critica": 40, "neutral": 0, "pct_apoyo": 20,
             "pct_critica": 80, "pct_neutral": 0, "saldo": -30,
             "ejemplo": "", "ejemplo_critica": "", "emociones": {},
             "emocion_dominante": "calma"},
        ]
        data = construir_analysis(aprob, "2026-07", "2026-07-14")
        pol = data["bloque2"]["polarizacion"]
        assert "indice" in pol
        assert pol["indice"] >= 0
        assert "formula_usada" in pol

    def test_nivel_alerta_campos(self):
        """nivel_alerta debe tener semaforo, indice_riesgo, alertas_cambridge."""
        aprob = [{"categoria": "test", "label": "T", "pct": 100,
                  "doc_count": 10, "apoyo": 5, "critica": 3, "neutral": 2,
                  "pct_apoyo": 50, "pct_critica": 30, "pct_neutral": 20,
                  "saldo": 2, "ejemplo": "", "ejemplo_critica": "",
                  "emociones": {}, "emocion_dominante": "calma"}]
        data = construir_analysis(aprob, "2026-07", "2026-07-14")
        na = data["bloque3"]["nivel_alerta"]
        assert "semaforo" in na
        assert na["semaforo"] in ("verde", "amarillo", "rojo")
        assert "indice_riesgo" in na
        assert na["indice_riesgo"] >= 0
        assert "alertas_cambridge" in na
        assert isinstance(na["alertas_cambridge"], list)
        assert "formula_riesgo" in na

    def test_autenticidad_campos(self):
        """autenticidad debe tener pct_organico, pct_coordinado."""
        aprob = [{"categoria": "test", "label": "T", "pct": 100,
                  "doc_count": 10, "apoyo": 5, "critica": 3, "neutral": 2,
                  "pct_apoyo": 50, "pct_critica": 30, "pct_neutral": 20,
                  "saldo": 2, "ejemplo": "", "ejemplo_critica": "",
                  "emociones": {}, "emocion_dominante": "calma"}]
        data = construir_analysis(aprob, "2026-07", "2026-07-14")
        auth = data["bloque3"]["autenticidad"]
        assert "pct_organico" in auth
        assert "pct_coordinado" in auth
        assert auth["pct_organico"] + auth["pct_coordinado"] <= 100.1

    def test_meta_campos(self):
        """meta debe tener plataforma, totales."""
        aprob = [{"categoria": "test", "label": "T", "pct": 100,
                  "doc_count": 10, "apoyo": 5, "critica": 3, "neutral": 2,
                  "pct_apoyo": 50, "pct_critica": 30, "pct_neutral": 20,
                  "saldo": 2, "ejemplo": "", "ejemplo_critica": "",
                  "emociones": {}, "emocion_dominante": "calma"}]
        fb = {
            "posts": 5, "likes": 100, "loves": 0, "cares": 0,
            "hahas": 0, "wows": 0, "sads": 0, "angrys": 0,
            "comments": 0, "shares": 0, "views": 1000,
            "total_reacciones": 100, "engagement": 100,
        }
        data = construir_analysis(aprob, "2026-07", "2026-07-14", fb_stats=fb)
        meta = data["meta"]
        assert meta["plataforma"] == "facebook"
        assert meta["total_posts_analizados"] == 5
        assert meta["total_reacciones_sumadas"] == 100
        assert meta["total_impresiones_vistas"] == 1000
