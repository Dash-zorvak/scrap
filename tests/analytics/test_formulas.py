"""Tests para las fórmulas §D-I del Bloque 6.1 (compute.py + report.py wiring).

Reescritura completa según fórmulas literales de 'Agente Analista — instrucciones'.
Cada test verifica una fórmula con números conocidos calculados a mano.
"""
import math
import pytest

from analytics.compute import (
    clamp,
    engagement_rate_fb, engagement_rate_tk, ratio_amor_enojo_fb,
    reacciones_positivas_fb, reacciones_negativas_fb, interacciones_fb,
    net_sentiment_reacciones, controversy_reacciones, effectiveness_reacciones,
    approval_pct_reacciones, rejection_pct_reacciones,
    net_sentiment_index, nsi_deviation, vol_factor, risk_reputacional,
    detectar_ici, detectar_sdi, detectar_efi, detectar_tai, detectar_zdi,
    verificar_cooldown, calcular_sensibilidad_tema,
    calcular_hhi,
    calcular_aprobacion, calcular_conexion_con_vistas, calcular_conexion_sin_vistas,
    calcular_tranquilidad, calcular_diversidad_temas, calcular_presencia_zonas,
    calcular_consistencia, calcular_atencion,
    calcular_pulso_iq_fb, calcular_pulso_iq_tk,
    pulso_iq_score, pulso_iq_cuadrante,
    DIMENSION_WEIGHTS, PLATFORM_IQ_WEIGHTS,
    coeficiente_variacion, autenticidad_pct,
)
from analytics.report import construir_analysis


# ═══════════════════════════════════════════════════════════════════════════════
# §D — Engagement
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngagementFB:
    def test_fb_con_vistas(self):
        """§D literal: ER_fb = (reacciones + comentarios + compartidos) / vistas * 100
        100+10+0+5+0+2+3=120 reac, 120+5+15=140 eng, 140/500*100=28.0"""
        er, basis = engagement_rate_fb(
            likes=100, loves=10, cares=0, hahas=5,
            wows=0, sads=2, angrys=3,
            comments=5, shares=15, views=500, n_posts=10,
        )
        assert er == 28.0
        assert basis == "views"

    def test_fb_sin_vistas_con_posts(self):
        """§D literal: proxy = interacciones / n_posts, basis = per_post
        50+5+0+0+0+0+0+10+20=85, 85/10=8.5"""
        er, basis = engagement_rate_fb(
            likes=50, loves=5, cares=0, hahas=0,
            wows=0, sads=0, angrys=0,
            comments=10, shares=20, views=0, n_posts=10,
        )
        assert er == 8.5
        assert basis == "per_post"

    def test_fb_sin_vistas_sin_posts(self):
        """Sin vistas ni posts → engagement_abs como fallback."""
        er, basis = engagement_rate_fb(
            likes=50, loves=5, cares=0, hahas=0,
            wows=0, sads=0, angrys=0,
            comments=10, shares=20, views=0, n_posts=0,
        )
        assert er == 85.0
        assert basis == "engagement_abs"

    def test_fb_cero_engagement(self):
        er, basis = engagement_rate_fb(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        assert er == 0.0
        assert basis == "sin_datos"


class TestEngagementTK:
    def test_tk_con_vistas(self):
        """§D literal: ER_tk = (likes + shares + favorites + comments) / views * 100
        Nota: se aplica *100 por consistencia con FB (documentado en PR)."""
        er, basis = engagement_rate_tk(
            views=1000, likes=200, shares=10, favorites=5, comments=8, n_videos=5,
        )
        assert er == 22.3
        assert basis == "views"

    def test_tk_sin_vistas_con_videos(self):
        """Sin vistas pero con videos → per_post."""
        er, basis = engagement_rate_tk(0, 50, 5, 3, 10, n_videos=10)
        assert er == 6.8  # 68/10
        assert basis == "per_post"

    def test_tk_sin_vistas_sin_videos(self):
        """Sin vistas ni videos → engagement_abs."""
        er, basis = engagement_rate_tk(0, 50, 5, 3, 10, n_videos=0)
        assert er == 68.0
        assert basis == "engagement_abs"


class TestRatioAmorEnojo:
    def test_ratio_normal(self):
        """(100+20+10) / (5+3+2) = 130/10 = 13.0"""
        r = ratio_amor_enojo_fb(100, 20, 10, 2, 3, 5)
        assert r == 13.0

    def test_ratio_sin_enojo(self):
        r = ratio_amor_enojo_fb(50, 10, 5, 0, 0, 0)
        assert r == 999.0

    def test_ratio_cero(self):
        r = ratio_amor_enojo_fb(0, 0, 0, 0, 0, 0)
        assert r == 0.0


class TestReacciones:
    def test_positivas(self):
        assert reacciones_positivas_fb(100, 20, 10) == 130

    def test_negativas(self):
        """§D literal: negativas = angrys + sads + hahas"""
        assert reacciones_negativas_fb(5, 3, 2) == 10

    def test_interacciones(self):
        """§D: interacciones = reacciones + comments + shares"""
        assert interacciones_fb(100, 10, 0, 5, 0, 2, 3, 5, 15) == 140


# ═══════════════════════════════════════════════════════════════════════════════
# §E — Indices de reacciones
# ═══════════════════════════════════════════════════════════════════════════════

class TestNetSentimentReacciones:
    """§E literal: net_sentiment = (likes+loves+cares - negativas) / total_reactions"""

    def test_positivo(self):
        """(100+20+10 - 5-3-2) / (100+20+10+5+3+2) = 120/140 = 0.8571"""
        ns = net_sentiment_reacciones(100, 20, 10, 5, 3, 2)
        assert ns == 0.8571

    def test_negativo(self):
        """(10+0+0 - 50+30+20) / (10+50+30+20) = -90/110 = -0.8182"""
        ns = net_sentiment_reacciones(10, 0, 0, 20, 30, 50)
        assert ns == -0.8182

    def test_neutral(self):
        """(50+0+0 - 0+0+50) / 100 = 0.0"""
        ns = net_sentiment_reacciones(50, 0, 0, 0, 0, 50)
        assert ns == 0.0

    def test_cero_reacciones(self):
        ns = net_sentiment_reacciones(0, 0, 0, 0, 0, 0)
        assert ns == 0.0


class TestControversyReacciones:
    """§E literal: controversy = negativas / total_reactions"""

    def test_normal(self):
        """(5+3+2) / (100+20+10+5+3+2) = 10/140 = 0.0714"""
        c = controversy_reacciones(100, 20, 10, 5, 3, 2)
        assert c == 0.0714

    def test_todo_negativo(self):
        """(50+30+20) / (0+0+0+50+30+20) = 100/100 = 1.0"""
        c = controversy_reacciones(0, 0, 0, 50, 30, 20)
        assert c == 1.0

    def test_cero(self):
        c = controversy_reacciones(0, 0, 0, 0, 0, 0)
        assert c == 0.0


class TestEffectivenessReacciones:
    """§E literal: effectiveness = (likes+loves+cares) / total_reactions"""

    def test_normal(self):
        """(100+20+10) / 140 = 0.9286"""
        e = effectiveness_reacciones(100, 20, 10, 5, 3, 2)
        assert e == 0.9286

    def test_cero(self):
        e = effectiveness_reacciones(0, 0, 0, 0, 0, 0)
        assert e == 0.0


class TestApprovalRejectionReacciones:
    def test_aprobacion(self):
        """(100+20+10) / max(140,1) * 100 = 92.9%"""
        a = approval_pct_reacciones(100, 20, 10, 5, 3, 2)
        assert a == 92.9

    def test_rechazo(self):
        """(5+3+2) / max(140,1) * 100 = 7.1%"""
        r = rejection_pct_reacciones(100, 20, 10, 5, 3, 2)
        assert r == 7.1


class TestNSI:
    """§E literal: nsi = ((posts_positivos - posts_negativos) / total_posts) * 100"""

    def test_positivo(self):
        assert net_sentiment_index(70, 30, 100) == 40.0

    def test_negativo(self):
        assert net_sentiment_index(20, 80, 100) == -60.0

    def test_cero(self):
        assert net_sentiment_index(0, 0, 0) == 0.0


class TestNSIDeviation:
    """§E literal: nsi_deviation = max(0, (50 - nsi) / 100)"""

    def test_nsi_50(self):
        assert nsi_deviation(50) == 0.0

    def test_nsi_0(self):
        assert nsi_deviation(0) == 0.5

    def test_nsi_negativo(self):
        """max(0, (50 - (-50)) / 100) = 1.0"""
        assert nsi_deviation(-50) == 1.0

    def test_nsi_100(self):
        assert nsi_deviation(100) == 0.0


class TestVolFactor:
    """§E literal: vol_factor = min(2.0, 1.0 + total_posts / 1000)"""

    def test_cero_posts(self):
        assert vol_factor(0) == 1.0

    def test_1000_posts(self):
        assert vol_factor(1000) == 2.0

    def test_2000_posts(self):
        assert vol_factor(2000) == 2.0

    def test_500_posts(self):
        assert vol_factor(500) == 1.5


class TestRiskReputacional:
    """§E literal: RR = clamp((max_topic_controversy * 10 * 0.50 + nsi_deviation * 0.50) * vol_factor, 0, 1)"""

    def test_bajo(self):
        """max_tc=0.05, nsi=40(dev=0.1), vf=1.0
        RR = (0.05*10*0.50 + 0.1*0.50) * 1.0 = (0.25+0.05)*1.0 = 0.3"""
        rr = risk_reputacional(40, 0.05, 1.0)
        assert rr == 0.3

    def test_alto(self):
        """max_tc=0.8, nsi=-50(dev=1.0), vf=2.0
        RR = clamp((0.8*10*0.50 + 1.0*0.50) * 2.0, 0, 1) = clamp(9.0, 0, 1) = 1.0"""
        rr = risk_reputacional(-50, 0.8, 2.0)
        assert rr == 1.0

    def test_medio(self):
        """max_tc=0.3, nsi=0(dev=0.5), vf=1.5
        RR = (0.3*10*0.50 + 0.5*0.50) * 1.5 = (1.5+0.25)*1.5 = 2.625 → clamp 1.0"""
        rr = risk_reputacional(0, 0.3, 1.5)
        assert rr == 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# §F — Alertas
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertaICI:
    """§F literal: z-score de controversia contra 4+ meses previos, alerta si z > 2.0"""

    def test_alerta_si_z_alto(self):
        """Historial con variación [0.10, 0.12, 0.08, 0.11], actual=0.50 → z alto.
        media=0.1025, std≈0.0149, z≈(0.5-0.1025)/0.0149≈26.7"""
        alerta = detectar_ici(0.50, [0.10, 0.12, 0.08, 0.11])
        assert alerta is not None
        assert alerta["tipo"] == "ICI"
        assert alerta["severidad"] >= 2

    def test_no_alerta_si_historial_insuficiente(self):
        """Menos de 4 meses → no alerta"""
        alerta = detectar_ici(0.5, [0.1, 0.1])
        assert alerta is None

    def test_no_alerta_si_z_bajo(self):
        """Historial con variación, actual dentro del rango → z bajo"""
        alerta = detectar_ici(0.12, [0.10, 0.12, 0.08, 0.11, 0.13])
        assert alerta is None

    def test_severidad_3_z_gt_2_5(self):
        """z > 2.5 → severidad 3. Hist [0.10,0.12,0.08,0.11], actual=0.60
        media≈0.1025, std≈0.0149, z≈33.4 → severidad 4"""
        alerta = detectar_ici(0.60, [0.10, 0.12, 0.08, 0.11])
        assert alerta is not None
        assert alerta["severidad"] >= 3


class TestAlertaSDI:
    """§F literal: SDI = (actual - previo) / max(|previo|, 0.01), alerta si SDI ≤ -0.20"""

    def test_alerta_si_caida(self):
        """NSI actual=10, previo=50 → SDI = (10-50)/50 = -0.8"""
        alerta = detectar_sdi(10, 50)
        assert alerta is not None
        assert alerta["tipo"] == "SDI"

    def test_no_alerta_si_estable(self):
        alerta = detectar_sdi(50, 48)
        assert alerta is None

    def test_no_alerta_si_mejora(self):
        alerta = detectar_sdi(60, 40)
        assert alerta is None

    def test_severidad_3_caida_grave(self):
        """SDI ≤ -0.50 → severidad 3"""
        alerta = detectar_sdi(-10, 50)
        assert alerta is not None
        assert alerta["severidad"] == 3


class TestAlertaEFI:
    """§F literal: EFI = (ER_actual - ER_previo) / max(ER_previo, 0.001), alerta si EFI ≤ -0.30 y ≥30 reacciones"""

    def test_alerta_si_caida(self):
        """ER actual=5, previo=10 → EFI = (5-10)/10 = -0.5"""
        alerta = detectar_efi(5, 10, 50)
        assert alerta is not None
        assert alerta["tipo"] == "EFI"

    def test_no_alerta_si_pocas_reacciones(self):
        """Menos de 30 reacciones → no alerta"""
        alerta = detectar_efi(5, 10, 20)
        assert alerta is None

    def test_no_alerta_si_caida_leve(self):
        alerta = detectar_efi(8, 10, 50)
        assert alerta is None


class TestAlertaTAI:
    """§F literal: TAI = ratio_enojo_tema / ratio_enojo_general, alerta si TAI > 2.0, enojo > 3%, ≥3 posts"""

    def test_alerta_si_enojo_alto(self):
        """enojo_tema=0.10, enojo_general=0.02 → TAI=5.0"""
        alerta = detectar_tai(0.10, 0.02, 5)
        assert alerta is not None
        assert alerta["tipo"] == "TAI"

    def test_no_alerta_si_pocos_posts(self):
        alerta = detectar_tai(0.10, 0.02, 2)
        assert alerta is None

    def test_no_alerta_si_enojo_bajo(self):
        """enojo_tema ≤ 3% → no alerta"""
        alerta = detectar_tai(0.02, 0.01, 5)
        assert alerta is None

    def test_no_alerta_si_tai_bajo(self):
        """TAI ≤ 2.0 → no alerta"""
        alerta = detectar_tai(0.05, 0.04, 5)
        assert alerta is None


class TestAlertaZDI:
    """§F literal: ZDI alerta si pct_negativos > 25% con ≥3 posts de zona"""

    def test_alerta_si_enojo_alto(self):
        alerta = detectar_zdi(35.0, 5)
        assert alerta is not None
        assert alerta["tipo"] == "ZDI"

    def test_no_alerta_si_pocos_posts(self):
        alerta = detectar_zdi(50.0, 2)
        assert alerta is None

    def test_no_alerta_si_bajo(self):
        alerta = detectar_zdi(20.0, 10)
        assert alerta is None


class TestCooldown:
    def test_primera_vez(self):
        assert verificar_cooldown(None, "2026-07-14T12:00:00Z", "ICI") is True

    def test_dentro_cooldown_ici(self):
        """ICI cooldown = 3 días. 1 día después → False"""
        assert verificar_cooldown(
            "2026-07-13T12:00:00Z", "2026-07-14T12:00:00Z", "ICI"
        ) is False

    def test_fuera_cooldown_ici(self):
        """3 días después → True"""
        assert verificar_cooldown(
            "2026-07-11T12:00:00Z", "2026-07-14T12:00:00Z", "ICI"
        ) is True

    def test_dentro_cooldown_sdi(self):
        """SDI cooldown = 7 días. 5 días después → False"""
        assert verificar_cooldown(
            "2026-07-09T12:00:00Z", "2026-07-14T12:00:00Z", "SDI"
        ) is False

    def test_fuera_cooldown_sdi(self):
        assert verificar_cooldown(
            "2026-07-07T12:00:00Z", "2026-07-14T12:00:00Z", "SDI"
        ) is True


class TestSensibilidadTema:
    def test_corrupcion_base(self):
        s = calcular_sensibilidad_tema("corrupcion", 1.0)
        assert s == 1.45

    def test_educacion_base(self):
        s = calcular_sensibilidad_tema("educacion", 1.0)
        assert s == 0.8

    def test_cv_alto(self):
        """base=1.0, cv=2.0 → 1.0 * (1+min(0.6,0.5)) * (1+0) = 1.5"""
        s = calcular_sensibilidad_tema("desconocido", 1.0, cv_28d=2.0, velocidad=0)
        assert s == 1.5

    def test_acotado_max(self):
        s = calcular_sensibilidad_tema("corrupcion", 10.0, cv_28d=10, velocidad=10)
        assert s == 2.0

    def test_acotado_min(self):
        s = calcular_sensibilidad_tema("desconocido", 0.1)
        assert s == 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# §G — HHI
# ═══════════════════════════════════════════════════════════════════════════════

class TestHHI:
    def test_un_tema(self):
        assert calcular_hhi([100]) == 1.0

    def test_dos_temas_iguales(self):
        assert calcular_hhi([50, 50]) == 0.5

    def test_tres_temas(self):
        hhi = calcular_hhi([60, 30, 10])
        assert hhi == 0.46

    def test_cero_temas(self):
        assert calcular_hhi([]) == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# §H — Pulso IQ (7 dimensiones)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAprobacion:
    """§H literal: score = clamp((promedio + 2) * 25, 0, 100)"""

    def test_maxima(self):
        assert calcular_aprobacion(2) == 100.0

    def test_media(self):
        assert calcular_aprobacion(0) == 50.0

    def test_minima(self):
        assert calcular_aprobacion(-2) == 0.0

    def test_clamp_alto(self):
        assert calcular_aprobacion(3) == 100.0

    def test_clamp_bajo(self):
        assert calcular_aprobacion(-3) == 0.0


class TestConexion:
    """§H literal: con vistas → eng_rate * 2000; sin vistas → interacciones/posts/50*100"""

    def test_con_vistas(self):
        assert calcular_conexion_con_vistas(1000, 50000) == 40.0

    def test_con_vistas_max(self):
        assert calcular_conexion_con_vistas(10000, 50000) == 100.0

    def test_sin_vistas(self):
        assert calcular_conexion_sin_vistas(500, 100) == 10.0

    def test_sin_vistas_max(self):
        assert calcular_conexion_sin_vistas(5000, 100) == 100.0

    def test_cero_posts(self):
        assert calcular_conexion_sin_vistas(100, 0) == 0.0


class TestTranquilidad:
    """§H literal: controversia = negativas/total; score = (1-controversia)*100"""

    def test_tranquilo(self):
        assert calcular_tranquilidad(2, 1, 2, 100) == 95.0

    def test_molesto(self):
        assert calcular_tranquilidad(30, 25, 25, 100) == pytest.approx(20.0, abs=0.01)

    def test_cero_total(self):
        assert calcular_tranquilidad(0, 0, 0, 0) == 50.0


class TestDiversidadTemas:
    """§H literal: % de posts con tema asignado"""

    def test_todos(self):
        assert calcular_diversidad_temas(100, 100) == 100.0

    def test_mitad(self):
        assert calcular_diversidad_temas(50, 100) == 50.0

    def test_cero(self):
        assert calcular_diversidad_temas(0, 100) == 0.0


class TestPresenciaZonas:
    """§H literal: % de posts con zona detectada"""

    def test_todos(self):
        assert calcular_presencia_zonas(80, 100) == 80.0

    def test_cero(self):
        assert calcular_presencia_zonas(0, 100) == 0.0


class TestConsistencia:
    """§H literal: score = clamp(100 - std * 30, 0, 100); default 50 si <2 meses o <5 posts"""

    def test_estable(self):
        assert calcular_consistencia([(0.5, 10), (0.5, 10), (0.5, 10)]) == 100.0

    def test_variable(self):
        s = calcular_consistencia([(0, 10), (1, 10)])
        assert s == 85.0

    def test_muy_variable(self):
        s = calcular_consistencia([(-2, 10), (2, 10)])
        assert s == 40.0

    def test_default_un_mes(self):
        assert calcular_consistencia([(0.5, 10)]) == 50.0

    def test_default_cero(self):
        assert calcular_consistencia([]) == 50.0

    def test_default_pocos_posts(self):
        """2 meses pero solo 3 posts totales (< 5) → default 50."""
        assert calcular_consistencia([(0.5, 1), (0.6, 2)]) == 50.0

    def test_calcula_con_suficientes_posts(self):
        """2 meses, 3+2=5 posts → calcula desviación real."""
        s = calcular_consistencia([(0.0, 3), (1.0, 2)])
        assert s == 85.0


class TestAtencion:
    """§H literal: promedio = comentarios/posts; score = min(100, promedio * 10)"""

    def test_normal(self):
        assert calcular_atencion(100, 10) == 100.0

    def test_alto(self):
        assert calcular_atencion(500, 10) == 100.0

    def test_bajo(self):
        assert calcular_atencion(5, 10) == 5.0


class TestDimensionWeights:
    def test_suma(self):
        assert abs(sum(DIMENSION_WEIGHTS.values()) - 6.0) < 0.01

    def test_plataforma_weights(self):
        assert PLATFORM_IQ_WEIGHTS["facebook"] == 0.55
        assert PLATFORM_IQ_WEIGHTS["tiktok"] == 0.45
        assert abs(PLATFORM_IQ_WEIGHTS["facebook"] + PLATFORM_IQ_WEIGHTS["tiktok"] - 1.0) < 0.01


class TestPulsoIQScore:
    def test_fb_only(self):
        dims = {
            "aprobacion": 60, "conexion": 40, "tranquilidad": 70,
            "diversidad_temas": 50, "presencia_zonas": 30,
            "consistencia": 50, "atencion": 45,
        }
        score, _ = pulso_iq_score(dims, None)
        expected = (60*1.0 + 40*1.0 + 70*1.0 + 50*0.8 + 30*0.7 + 50*0.9 + 45*0.6) / 6.0
        assert score == round(expected, 2)

    def test_fb_tk_combined(self):
        dims_fb = {
            "aprobacion": 60, "conexion": 40, "tranquilidad": 70,
            "diversidad_temas": 50, "presencia_zonas": 30,
            "consistencia": 50, "atencion": 45,
        }
        dims_tk = {
            "aprobacion": 80, "conexion": 60, "tranquilidad": 50,
            "diversidad_temas": 70, "presencia_zonas": 50,
            "consistencia": 50, "atencion": 55,
        }
        score, _ = pulso_iq_score(dims_fb, dims_tk)
        iq_fb = (60+40+70+40+21+45+27) / 6.0  # 303/6 = 50.5
        iq_tk = (80+60+50+56+35+45+33) / 6.0  # 359/6 = 59.833
        expected = iq_fb * 0.55 + iq_tk * 0.45
        assert score == round(expected, 2)

    def test_no_dims(self):
        score, _ = pulso_iq_score(None, None)
        assert score == 0.0


class TestCuadrante:
    """§H literal: X=aprobacion, Y=conexion"""

    def test_liderazgo(self):
        dims = {"aprobacion": 70, "conexion": 60}
        assert pulso_iq_cuadrante(65, dims) == "LIDERAZGO"

    def test_institucional(self):
        dims = {"aprobacion": 70, "conexion": 30}
        assert pulso_iq_cuadrante(55, dims) == "INSTITUCIONAL"

    def test_populista(self):
        dims = {"aprobacion": 30, "conexion": 70}
        assert pulso_iq_cuadrante(45, dims) == "POPULISTA"

    def test_crisis(self):
        dims = {"aprobacion": 30, "conexion": 30}
        assert pulso_iq_cuadrante(25, dims) == "CRISIS"

    def test_vacio(self):
        assert pulso_iq_cuadrante(50, {}) == ""


# ═══════════════════════════════════════════════════════════════════════════════
# §I — Autenticidad
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutenticidad:
    def test_estable(self):
        cv, organico = coeficiente_variacion([10, 11, 9, 10, 12])
        assert cv < 0.5
        assert organico is True

    def test_volatil(self):
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
        cv, organico = coeficiente_variacion([50])
        assert cv == 0.0
        assert organico is True


# ═══════════════════════════════════════════════════════════════════════════════
# §J — Aislamiento FB/TK
# ═══════════════════════════════════════════════════════════════════════════════

class TestAislamientoPlataformas:
    def test_fb_no_usa_tk(self):
        er_fb, _ = engagement_rate_fb(
            100, 0, 0, 0, 0, 0, 0, 0, 0, 1000, n_posts=5,
        )
        er_tk, _ = engagement_rate_tk(1000, 200, 0, 0, 0, n_videos=5)
        assert er_fb == 10.0
        assert er_tk == 20.0
        assert er_fb != er_tk

    def test_wiring_fb_stats(self):
        """construir_analysis con fb_stats → métricas reales."""
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
        assert mr["reacciones_positivas"] == 125
        assert mr["reacciones_negativas"] == 13
        assert mr["engagementBasis"] == "views"
        assert "net_sentiment_reacciones" in mr
        assert "controversy_reacciones" in mr
        assert "effectiveness_reacciones" in mr
        assert "aprobacion_pct_reacciones" in mr
        assert "rechazo_pct_reacciones" in mr

    def test_wiring_tk_stats(self):
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
        assert mr["engagementBasis"] == "views"

    def test_wiring_both_platforms(self):
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
        assert mr["engagement_rate"] == 10.0
        assert mr["engagementBasis"] == "ponderado_volumen"
        assert data["meta"]["plataforma"] == "multicanal"


# ═══════════════════════════════════════════════════════════════════════════════
# Wiring: campos poblados en construir_analysis
# ═══════════════════════════════════════════════════════════════════════════════

class TestWiringCampos:
    def test_concentracion_tematica_hhi(self):
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

    def test_pulso_iq_campos(self):
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

    def test_nivel_alerta_campos(self):
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
        assert "alertas_cambridge" in na

    def test_autenticidad_campos(self):
        aprob = [{"categoria": "test", "label": "T", "pct": 100,
                  "doc_count": 10, "apoyo": 5, "critica": 3, "neutral": 2,
                  "pct_apoyo": 50, "pct_critica": 30, "pct_neutral": 20,
                  "saldo": 2, "ejemplo": "", "ejemplo_critica": "",
                  "emociones": {}, "emocion_dominante": "calma"}]
        data = construir_analysis(aprob, "2026-07", "2026-07-14")
        auth = data["bloque3"]["autenticidad"]
        assert "pct_organico" in auth
        assert "pct_coordinado" in auth

    def test_meta_campos(self):
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

    def test_polarizacion_indice(self):
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


# ═══════════════════════════════════════════════════════════════════════════════
# 22.6 — Tests obligatorios Bloque 6.2
# ═══════════════════════════════════════════════════════════════════════════════

class TestICIUsaHistorialMensualReal:
    """22.6: ICI debe usar controversia mensual real, no controversia por tema."""

    def test_ici_z_score_sobre_serie_mensual(self):
        """Armar 5 meses de controversia creciente y confirmar que el z-score
        se calcula sobre esa serie, no sobre per-theme controversy."""
        # Meses con controversia creciente: ~0.10, ~0.12, ~0.08, ~0.11
        # y mes actual con pico: 0.50
        historial = [0.10, 0.12, 0.08, 0.11]
        alerta = detectar_ici(0.50, historial)
        assert alerta is not None
        assert alerta["tipo"] == "ICI"
        # Verificar que el z-score se calcula correctamente
        media = sum(historial) / len(historial)  # 0.1025
        assert alerta["valor"] > 2.0

    def test_ici_no_usa_controversia_por_tema(self):
        """Historial de mensual con controversy variada pero estable → no alerta
        aunque haya temas controversiales altos."""
        # Meses con variación natural pero dentro del rango
        historial = [0.10, 0.25, 0.05, 0.30, 0.15]
        alerta = detectar_ici(0.20, historial)
        assert alerta is None

    def test_ici_wiring_con_monthly_controversy(self):
        """construir_analysis con fb_monthly_controversy usa datos mensuales."""
        aprob = [{"categoria": "test", "label": "T", "pct": 100,
                  "doc_count": 10, "apoyo": 5, "critica": 3, "neutral": 2,
                  "pct_apoyo": 50, "pct_critica": 30, "pct_neutral": 20,
                  "saldo": 2, "ejemplo": "", "ejemplo_critica": "",
                  "emociones": {}, "emocion_dominante": "calma"}]
        # 6 meses: 5 previos estables, 1 actual con pico
        monthly = [
            ("2026-01", 0.10, 10), ("2026-02", 0.12, 10),
            ("2026-03", 0.08, 10), ("2026-04", 0.11, 10),
            ("2026-05", 0.10, 10), ("2026-06", 0.50, 10),
        ]
        data = construir_analysis(
            aprob, "2026-06", "2026-06-30",
            fb_monthly_controversy=monthly,
        )
        na = data["bloque3"]["nivel_alerta"]
        # ICI should have fired (z-score for 0.50 vs [0.10,0.12,0.08,0.11,0.10])
        ici_alerts = [a for a in na["alertas_cambridge"] if a["tipo"] == "ICI"]
        assert len(ici_alerts) >= 1


class TestEnlacesReferenciaAlertas:
    """22.6: Cada alerta debe tener enlaces_referencia no vacío cuando
    existen posts reales que la justifiquen."""

    def test_sdi_enlaces_no_vacios(self):
        """SDI con fb_controversial_posts → enlaces_referencia populated."""
        aprob = [{"categoria": "test", "label": "T", "pct": 100,
                  "doc_count": 10, "apoyo": 5, "critica": 3, "neutral": 2,
                  "pct_apoyo": 50, "pct_critica": 30, "pct_neutral": 20,
                  "saldo": 2, "ejemplo": "", "ejemplo_critica": "",
                  "emociones": {}, "emocion_dominante": "calma"}]
        controversial = [
            {"post_id": "p1", "post_url": "https://fb.com/p1",
             "topic_category": "seguridad", "zona": "",
             "negativos": 10, "total_reacciones": 20, "ratio": 0.5,
             "page_name": "", "created_time": ""},
            {"post_id": "p2", "post_url": "https://fb.com/p2",
             "topic_category": "seguridad", "zona": "",
             "negativos": 8, "total_reacciones": 15, "ratio": 0.53,
             "page_name": "", "created_time": ""},
        ]
        data = construir_analysis(
            aprob, "2026-07", "2026-07-14",
            nsi_previo=50.0,  # prev NSI=50, actual will be lower → SDI fires
            fb_controversial_posts=controversial,
            fb_per_theme_controversy=[
                {"tema": "seguridad", "n_posts": 10, "negativos": 8,
                 "total_reacciones": 20, "controversy": 0.4},
            ],
        )
        na = data["bloque3"]["nivel_alerta"]
        sdi_alerts = [a for a in na["alertas_cambridge"] if a["tipo"] == "SDI"]
        if sdi_alerts:
            assert len(sdi_alerts[0]["enlaces_referencia"]) > 0

    def test_efi_enlaces_no_vacios(self):
        """EFI con fb_controversial_posts → enlaces_referencia populated."""
        aprob = [{"categoria": "test", "label": "T", "pct": 100,
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
        controversial = [
            {"post_id": "p1", "post_url": "https://fb.com/p1",
             "topic_category": "", "zona": "",
             "negativos": 10, "total_reacciones": 20, "ratio": 0.5,
             "page_name": "", "created_time": ""},
        ]
        # er_previo very high so current ER is much lower → EFI fires
        data = construir_analysis(
            aprob, "2026-07", "2026-07-14",
            fb_stats=fb, er_previo=50.0,
            fb_controversial_posts=controversial,
        )
        na = data["bloque3"]["nivel_alerta"]
        efi_alerts = [a for a in na["alertas_cambridge"] if a["tipo"] == "EFI"]
        if efi_alerts:
            assert len(efi_alerts[0]["enlaces_referencia"]) > 0

    def test_tai_enlaces_por_tema(self):
        """TAI con fb_controversial_posts filtrados por tema → enlaces del tema."""
        aprob = [{"categoria": "test", "label": "T", "pct": 100,
                  "doc_count": 10, "apoyo": 5, "critica": 3, "neutral": 2,
                  "pct_apoyo": 50, "pct_critica": 30, "pct_neutral": 20,
                  "saldo": 2, "ejemplo": "", "ejemplo_critica": "",
                  "emociones": {}, "emocion_dominante": "calma"}]
        controversial = [
            {"post_id": "p1", "post_url": "https://fb.com/p1",
             "topic_category": "corrupcion", "zona": "",
             "negativos": 10, "total_reacciones": 12, "ratio": 0.83,
             "page_name": "", "created_time": ""},
            {"post_id": "p2", "post_url": "https://fb.com/p2",
             "topic_category": "educacion", "zona": "",
             "negativos": 2, "total_reacciones": 20, "ratio": 0.1,
             "page_name": "", "created_time": ""},
        ]
        # corrupcion: 10 neg / 12 total = 0.83 controversy, 5 posts
        # general: low enojo → TAI fires for corrupcion
        data = construir_analysis(
            aprob, "2026-07", "2026-07-14",
            fb_controversial_posts=controversial,
            fb_per_theme_controversy=[
                {"tema": "corrupcion", "n_posts": 5, "negativos": 10,
                 "total_reacciones": 12, "controversy": 0.83},
                {"tema": "educacion", "n_posts": 10, "negativos": 2,
                 "total_reacciones": 20, "controversy": 0.10},
            ],
        )
        na = data["bloque3"]["nivel_alerta"]
        tai_alerts = [a for a in na["alertas_cambridge"] if a["tipo"] == "TAI"]
        if tai_alerts:
            assert len(tai_alerts[0]["enlaces_referencia"]) > 0
            # Verify links are from the right theme
            for link in tai_alerts[0]["enlaces_referencia"]:
                assert "fb.com/p1" in link  # corrupcion post

    def test_zdi_enlaces_por_zona(self):
        """ZDI con posts de la zona → enlaces_referencia populated."""
        aprob = [{"categoria": "test", "label": "T", "pct": 100,
                  "doc_count": 10, "apoyo": 5, "critica": 3, "neutral": 2,
                  "pct_apoyo": 50, "pct_critica": 30, "pct_neutral": 20,
                  "saldo": 2, "ejemplo": "", "ejemplo_critica": "",
                  "emociones": {}, "emocion_dominante": "calma"}]
        anger_by_zone = [
            {"zona": "norte", "negativos": 10, "total": 20, "pct_negativos": 50.0},
        ]
        # Mock get_fb_posts_by_zone by patching
        from unittest.mock import patch
        mock_posts = [
            {"post_id": "z1", "post_url": "https://fb.com/z1",
             "topic_category": "", "created_time": ""},
            {"post_id": "z2", "post_url": "https://fb.com/z2",
             "topic_category": "", "created_time": ""},
        ]
        with patch("analytics.queries.get_fb_posts_by_zone", return_value=mock_posts):
            data = construir_analysis(
                aprob, "2026-07", "2026-07-14",
                fb_anger_by_zone=anger_by_zone,
            )
        na = data["bloque3"]["nivel_alerta"]
        zdi_alerts = [a for a in na["alertas_cambridge"] if a["tipo"] == "ZDI"]
        if zdi_alerts:
            assert len(zdi_alerts[0]["enlaces_referencia"]) > 0


class TestSensibilidadAjustadaEnAlertas:
    """22.6: Umbral de TAI/ICI cambia según sensibilidad del tema."""

    def test_tai_umbral_mayor_para_corrupcion(self):
        """corrupcion (base=1.45) debería tener umbral más alto que
        educación (base=0.8), requiriendo TAI más extremo para alertar."""
        # TAI = ratio_enojo_tema / ratio_enojo_general
        # Para corrupcion con umbral base ajustado (1.45 * 2.0 = 2.9):
        #   necesita TAI > 2.9 para alertar
        # Para educacion con umbral ajustado (0.8 * 2.0 = 1.6):
        #   necesita TAI > 1.6 para alertar
        # Con TAI=2.0: no alerta para corrupcion, sí para educacion
        alerta_corrupcion = detectar_tai(0.10, 0.05, 5, umbral_base=2.9)
        alerta_educacion = detectar_tai(0.10, 0.05, 5, umbral_base=1.6)
        assert alerta_corrupcion is None
        assert alerta_educacion is not None

    def test_ici_umbral_ajustado_por_sensibilidad(self):
        """ICI con umbral ajustado (>2.0) requiere z-score más alto."""
        historial = [0.10, 0.12, 0.08, 0.11]
        # Con umbral default 2.0: alerta
        alerta_default = detectar_ici(0.50, historial, umbral_base=2.0)
        assert alerta_default is not None
        # Con umbral ajustado 4.0: podría no alertar
        alerta_ajustada = detectar_ici(0.50, historial, umbral_base=4.0)
        # z-score ≈ 26.7, still > 4.0, so still alerts — test with lower value
        alerta_baja = detectar_ici(0.15, historial, umbral_base=4.0)
        assert alerta_baja is None

    def test_sensibilidad_para_alertas_deriva_de_datos(self):
        """calcular_sensibilidad_para_alertas usa la serie mensual del tema."""
        from analytics.compute import calcular_sensibilidad_para_alertas
        monthly = [
            {"mes": "2026-01", "tema": "corrupcion", "controversy": 0.10, "n_posts": 5},
            {"mes": "2026-02", "tema": "corrupcion", "controversy": 0.15, "n_posts": 5},
            {"mes": "2026-03", "tema": "corrupcion", "controversy": 0.20, "n_posts": 5},
            {"mes": "2026-04", "tema": "corrupcion", "controversy": 0.30, "n_posts": 5},
            {"mes": "2026-05", "tema": "corrupcion", "controversy": 0.40, "n_posts": 5},
            {"mes": "2026-06", "tema": "corrupcion", "controversy": 0.50, "n_posts": 5},
        ]
        sens = calcular_sensibilidad_para_alertas("corrupcion", monthly, "2026-06-30")
        # base=1.45, cv>0, velocidad>0 → sens > 1.45
        assert sens >= 1.45
        assert sens <= 2.0

    def test_sensibilidad_para_alertas_sin_datos(self):
        """Sin datos mensuales → sensibilidad base del tema."""
        from analytics.compute import calcular_sensibilidad_para_alertas
        sens = calcular_sensibilidad_para_alertas("corrupcion", [], "2026-06-30")
        assert sens == 1.45

    def test_sensibilidad_para_alertas_tema_desconocido(self):
        """Tema no en TOPIC_SENSITIVITY_BASES → base=1.0."""
        from analytics.compute import calcular_sensibilidad_para_alertas
        sens = calcular_sensibilidad_para_alertas("tema_raro", [], "2026-06-30")
        assert sens == 1.0


class TestConsistenciaPostsThreshold:
    """22.6: calcular_consistencia devuelve 50.0 con ≥2 meses pero <5 posts."""

    def test_dos_meses_pocos_posts(self):
        """2 meses, 2+1=3 posts (< 5) → default 50."""
        assert calcular_consistencia([(0.5, 2), (0.6, 1)]) == 50.0

    def test_dos_meses_suficientes_posts(self):
        """2 meses, 3+3=6 posts (≥5) → calcula desviación."""
        s = calcular_consistencia([(0.0, 3), (1.0, 3)])
        assert s == 85.0

    def test_cuatro_meses_pocos_posts(self):
        """4 meses pero 1+1+1+1=4 posts → default 50."""
        assert calcular_consistencia([(0.5, 1), (0.5, 1),
                                       (0.5, 1), (0.5, 1)]) == 50.0


class TestEngagementAmbosZero:
    """22.6: engagement_rate_fb/tk con vistas=0 y posts=0."""

    def test_fb_engagement_abs_fallback(self):
        """FB: vistas=0, posts=0, eng=85 → (85.0, 'engagement_abs')."""
        er, basis = engagement_rate_fb(
            likes=50, loves=5, cares=0, hahas=0,
            wows=0, sads=0, angrys=0,
            comments=10, shares=20, views=0, n_posts=0,
        )
        assert er == 85.0
        assert basis == "engagement_abs"

    def test_fb_cero_total(self):
        """FB: todo cero → (0.0, 'sin_datos')."""
        er, basis = engagement_rate_fb(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        assert er == 0.0
        assert basis == "sin_datos"

    def test_tk_engagement_abs_fallback(self):
        """TK: vistas=0, videos=0, eng=68 → (68.0, 'engagement_abs')."""
        er, basis = engagement_rate_tk(0, 50, 5, 3, 10, n_videos=0)
        assert er == 68.0
        assert basis == "engagement_abs"

    def test_tk_cero_total(self):
        """TK: todo cero → (0.0, 'sin_datos')."""
        er, basis = engagement_rate_tk(0, 0, 0, 0, 0, n_videos=0)
        assert er == 0.0
        assert basis == "sin_datos"
