"""Tests de regresión para D3: Correlación Contenido-Reacción (Contagio Emocional)."""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# Setup path like other dashboard tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

from dashboard.dash_metrics import calcular_contagio_emocional
from dashboard.dash_bloque4 import render_bloque4_inteligencia


class TestCalcularContagioEmocional:
    """Tests para calcular_contagio_emocional con filtro de período."""

    def test_con_ini_fin_filtra_antes_de_umbrales(self):
        """
        Verifica que al pasar un df_fb ya filtrado por período, el umbral se calcula
        SOLO con posts del período. Un outlier FUERA del período no debe afectar
        la clasificación dentro del período.
        """
        # Período de prueba: 15-21 ene 2024
        # Posts DENTRO del período: scores bajos (umbral 0.75 será bajo)
        posts_dentro = pd.DataFrame({
            'post_id': ['p1', 'p2', 'p3', 'p4'],
            'created_time': [
                '2024-01-15 10:00', '2024-01-16 10:00',
                '2024-01-17 10:00', '2024-01-18 10:00'
            ],
            'score_emocional': [0.1, 0.2, 0.3, 0.4],  # q75 = 0.325, q25 = 0.175
            'score_sentimiento': [0.1, 0.2, 0.3, 0.4],
            'message': ['msg1', 'msg2', 'msg3', 'msg4'],
            'categoria_nombre': ['cat1'] * 4,
            'indice_amor': [0]*4, 'indice_humor': [0]*4,
            'indice_tristeza': [0]*4, 'total_reacciones': [10]*4,
            'pct_positivo': [50]*4, 'pct_negativo': [10]*4,
        })

        # Outlier FUERA del período: score muy alto (debería subir el q75 si no se filtra)
        posts_fuera = pd.DataFrame({
            'post_id': ['outlier1', 'outlier2'],
            'created_time': [
                '2024-01-01 10:00', '2024-01-02 10:00'
            ],
            'score_emocional': [0.9, 0.95],  # Muy alto - outlier
            'score_sentimiento': [0.9, 0.95],
            'message': ['outlier_msg1', 'outlier_msg2'],
            'categoria_nombre': ['cat1'] * 2,
            'indice_amor': [0]*2, 'indice_humor': [0]*2,
            'indice_tristeza': [0]*2, 'total_reacciones': [100]*2,
            'pct_positivo': [90]*2, 'pct_negativo': [0]*2,
        })

        df_all = pd.concat([posts_dentro, posts_fuera], ignore_index=True)

        # Simular que cargar_engagement_periodo ya filtró por fecha
        # (es decir, solo pasa los posts del período)
        df_filtrado_manual = posts_dentro.copy()

        # Llamar con df_fb ya filtrado - debe usar solo esos 4 posts para quantiles
        df_posts, conteo, _, _ = calcular_contagio_emocional(df_fb=df_filtrado_manual)
        
        # Verificar que solo quedaron los 4 posts del período
        assert len(df_posts) == 4, f"Esperaba 4 posts en el período, got {len(df_posts)}"
        
        # El umbral q75 de [0.1, 0.2, 0.3, 0.4] = 0.325
        # El umbral q25 = 0.175
        # Posts con score_emocional >= 0.325 y sent >= 0.325 -> resonancia_positiva
        # Solo p4 (0.4) >= 0.325 -> resonancia_positiva
        resonancia_pos = df_posts[df_posts['tipo_contagio'] == 'resonancia_positiva']
        assert len(resonancia_pos) >= 1, "Debería haber al menos 1 resonancia_positiva con umbrales del período"

    def test_sin_filtro_previo_comportamiento_historico(self):
        """
        Si se pasa un df_fb con todos los posts históricos, debe usar todos para umbrales.
        """
        # Posts con variación (simula todo el histórico sin filtro previo)
        posts = pd.DataFrame({
            'post_id': ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8'],
            'created_time': [
                '2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04',
                '2024-01-05', '2024-01-06', '2024-01-07', '2024-01-08'
            ],
            'score_emocional': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
            'score_sentimiento': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
            'message': [f'msg{i}' for i in range(1, 9)],
            'categoria_nombre': ['cat1'] * 8,
            'indice_amor': [0]*8, 'indice_humor': [0]*8,
            'indice_tristeza': [0]*8, 'total_reacciones': [10]*8,
            'pct_positivo': [50]*8, 'pct_negativo': [10]*8,
        })

        # Llamar con df_fb completo (sin filtrar)
        df_posts, conteo, _, _ = calcular_contagio_emocional(df_fb=posts)
        
        # Debe usar todos los 8 posts
        assert len(df_posts) == 8, f"Sin filtro previo debería usar todos los posts, got {len(df_posts)}"
        
        # q75 de [0.1..0.8] = 0.575, q25 = 0.275
        # Verificar que las clasificaciones existen
        assert 'tipo_contagio' in df_posts.columns
        assert len(conteo) > 0

    def test_outlier_fuera_no_afecta_clasificacion_interna(self):
        """
        Al pasar solo posts del período (simulando filtro previo por cargar_engagement_periodo),
        los outliers fuera del período NO afectan umbrales/clasificación.
        """
        # 5 posts DENTRO del período (valores moderados)
        posts_dentro = pd.DataFrame({
            'post_id': [f'p{i}' for i in range(1, 6)],
            'created_time': pd.date_range('2024-01-01', periods=5, freq='D'),
            'score_emocional': [0.1, 0.2, 0.3, 0.4, 0.5],
            'score_sentimiento': [0.1, 0.2, 0.3, 0.4, 0.5],
            'message': [f'msg{i}' for i in range(1, 6)],
            'categoria_nombre': ['cat1'] * 5,
            'indice_amor': [0]*5, 'indice_humor': [0]*5,
            'indice_tristeza': [0]*5, 'total_reacciones': [100]*5,
            'pct_positivo': [50]*5, 'pct_negativo': [10]*5,
        })
        
        # Outliers extremos ANTES del período - si no se filtran, subirían q75 drásticamente
        posts_outliers = pd.DataFrame({
            'post_id': ['out1', 'out2', 'out3', 'out4'],
            'created_time': pd.date_range('2023-12-01', periods=4, freq='D'),
            'score_emocional': [0.99, 0.98, 0.97, 0.96],
            'score_sentimiento': [0.99, 0.98, 0.97, 0.96],
            'message': [f'out{i}' for i in range(4)],
            'categoria_nombre': ['cat1'] * 4,
            'indice_amor': [0]*4, 'indice_humor': [0]*4,
            'indice_tristeza': [0]*4, 'total_reacciones': [1000]*4,
            'pct_positivo': [99]*4, 'pct_negativo': [0]*4,
        })
        
        df_all = pd.concat([posts_dentro, posts_outliers], ignore_index=True)
        
        # CON filtro previo (simulado): solo 5 posts, q75≈0.4
        df_filtrado, conteo_f, _, _ = calcular_contagio_emocional(df_fb=posts_dentro)
        assert len(df_filtrado) == 5, f"Esperado 5 posts con filtro, got {len(df_filtrado)}"
        
        # Verificar que los umbrales NO fueron afectados por outliers (q75 debería ser ~0.4, no ~0.97)
        # Con 5 posts: score_emocional = [0.1, 0.2, 0.3, 0.4, 0.5], q75 = 0.4, q25 = 0.2
        # Los 5 posts deberían clasificarse según estos umbrales moderados
        
        # Verificar que la clasificación tiene sentido con umbrales moderados
        # Post con score 0.5 > q75(0.4) y sent 0.5 > q75(0.4) -> resonancia_positiva
        # Post con score 0.1 < q25(0.2) y sent 0.1 < q25(0.2) -> resonancia_negativa
        tipos = df_filtrado['tipo_contagio'].tolist()
        assert 'resonancia_positiva' in tipos
        assert 'resonancia_negativa' in tipos
        
        # SIN filtro previo (usando todo): 9 posts, q75 sería ~0.96 (dominado por outliers)
        df_sin_filtro, conteo_sf, _, _ = calcular_contagio_emocional(df_fb=df_all)
        # Con outliers, los umbrales cambian drásticamente
        assert len(df_sin_filtro) == 9

    def test_esquema_real_cargar_engagement_periodo_pasa_validacion(self):
        """
        Verifica que calcular_contagio_emocional acepta un DataFrame con el
        esquema real que produce cargar_engagement_periodo para Facebook
        (columna score_sentimiento, NO sent_comentarios).
        Debe fallar con el código anterior al fix (que exigía sent_comentarios)
        y pasar con la corrección a score_sentimiento.
        """
        df_real = pd.DataFrame({
            'post_id': ['r1', 'r2', 'r3'],
            'created_time': pd.date_range('2024-06-01', periods=3, freq='D'),
            'score_emocional': [0.3, 0.6, 0.1],
            'message': ['post real 1', 'post real 2', 'post real 3'],
            'categoria_nombre': ['cat_a', 'cat_b', 'cat_a'],
            'score_sentimiento': [0.2, 0.5, 0.05],
            'pct_positivo': [60.0, 75.0, 30.0],
            'pct_negativo': [10.0, 5.0, 40.0],
            'sent_total_comentarios': [100, 200, 50],
            'indice_amor': [0.3, 0.5, 0.1],
            'indice_humor': [0.2, 0.3, 0.05],
            'indice_tristeza': [0.1, 0.05, 0.3],
            'total_reacciones': [150, 300, 80],
        })

        df_posts, conteo, _, _ = calcular_contagio_emocional(df_fb=df_real)

        assert len(df_posts) > 0, (
            "El DataFrame con esquema real NO debería estar vacío. "
            "Si falla, revisa que la validación de columnas use score_sentimiento "
            "en lugar de sent_comentarios."
        )
        assert 'tipo_contagio' in df_posts.columns
        assert len(conteo) > 0


class TestSeccion07ListasPublicaciones:
    """Tests para verificar que la sección 07 expone listas para las 3 categorías."""

    def test_render_tiene_listas_tres_categorias(self):
        """
        Verifica que el código de sección 07 incluye bloques para:
        - conectaron bien (resonancia_positiva)
        - resonancia negativa (resonancia_negativa)
        - no conectaron (rechazo_a_positivo)
        """
        import inspect
        source = inspect.getsource(render_bloque4_inteligencia)
        
        # Verificar que existen los tres bloques de listas
        assert 'PUBLICACIONES QUE CONECTARON BIEN' in source, "Falta lista 'conectaron bien'"
        assert 'PUBLICACIONES CON RESONANCIA NEGATIVA' in source, "Falta lista 'resonancia negativa'"
        assert 'PUBLICACIONES QUE NO CONECTARON' in source, "Falta lista 'no conectaron' (rechazo_a_positivo)"
        
        # Verificar que se usan los tipos de contagio correctos
        assert 'resonancia_positiva' in source
        assert 'resonancia_negativa' in source
        assert 'rechazo_a_positivo' in source
        
        # Verificar ordenamiento correcto
        assert 'nlargest(3, "score_emocional")' in source, "conectaron bien debe ordenar por score_emocional descendente"
        assert 'nsmallest(3, "score_emocional")' in source, "resonancia negativa debe ordenar por score_emocional ascendente"
        assert 'nlargest(3, "distorsion")' in source, "no conectaron debe ordenar por distorsion descendente"
        
        # Verificar estilos CSS correctos
        assert 'memo-item-positivo' in source
        assert 'memo-item-negativo' in source

    def test_nota_aclaratoria_periodo(self):
        """Verifica que existe la nota aclaratoria sobre cálculo dentro del período."""
        import inspect
        source = inspect.getsource(render_bloque4_inteligencia)
        
        assert 'DENTRO del período seleccionado entre sí' in source or \
               'dentro del período seleccionado entre sí' in source, \
               "Falta nota aclaratoria sobre cálculo relativo al período"


class TestCacheInvalidaPorPeriodo:
    """Verifica que el cache distingue por df_fb (ya filtrado)."""

    def test_cache_key_incluye_df_fb(self):
        """El decorador @st.cache_data debe distinguir llamadas con diferentes df_fb."""
        import dashboard.dash_metrics as dm
        import inspect
        
        source = inspect.getsource(dm.calcular_contagio_emocional)
        
        # Verificar que el decorador tiene ttl y parámetro df_fb
        assert '@st.cache_data' in source or 'st.cache_data' in source
        assert 'ttl=3600' in source
        assert 'df_fb' in source
        # Streamlit cache_data usa los argumentos de la función como clave de cache
        # así que df_fb distintos = cache keys distintas automáticamente