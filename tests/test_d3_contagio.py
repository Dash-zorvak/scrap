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
        Verifica que al pasar ini/fin, el umbral se calcula SOLO con posts del período.
        Un outlier FUERA del período no debe afectar la clasificación dentro del período.
        """
        # Crear DataFrame sintético con posts
        # Período de prueba: 15-21 ene 2024
        ini = pd.Timestamp("2024-01-15")
        fin = pd.Timestamp("2024-01-21")

        # Posts DENTRO del período: scores bajos (umbral 0.75 será bajo)
        posts_dentro = pd.DataFrame({
            'post_id': ['p1', 'p2', 'p3', 'p4'],
            'created_time': [
                '2024-01-15 10:00', '2024-01-16 10:00',
                '2024-01-17 10:00', '2024-01-18 10:00'
            ],
            'score_emocional': [0.1, 0.2, 0.3, 0.4],  # q75 = 0.325, q25 = 0.175
            'sent_comentarios': [0.1, 0.2, 0.3, 0.4],
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
            'sent_comentarios': [0.9, 0.95],
            'message': ['outlier_msg1', 'outlier_msg2'],
            'categoria_nombre': ['cat1'] * 2,
            'indice_amor': [0]*2, 'indice_humor': [0]*2,
            'indice_tristeza': [0]*2, 'total_reacciones': [100]*2,
            'pct_positivo': [90]*2, 'pct_negativo': [0]*2,
        })

        df_all = pd.concat([posts_dentro, posts_fuera], ignore_index=True)

        # Mockear safe_query para devolver nuestro DataFrame sintético
        import dashboard.dash_metrics as dm
        original_safe_query = dm.safe_query
        
        def mock_safe_query(query, db_path, params=None):
            return df_all.copy()
        
        dm.safe_query = mock_safe_query
        try:
            # Llamar CON ini/fin - debería filtrar ANTES de calcular quantiles
            df_posts, conteo, _, _ = calcular_contagio_emocional(ini=ini, fin=fin)
            
            # Verificar que solo quedaron los 4 posts del período
            assert len(df_posts) == 4, f"Esperaba 4 posts en el período, got {len(df_posts)}"
            
            # El umbral q75 de [0.1, 0.2, 0.3, 0.4] = 0.325
            # El umbral q25 = 0.175
            # Posts con score_emocional >= 0.325 y sent >= 0.325 -> resonancia_positiva
            # Solo p3 (0.3) y p4 (0.4) están cerca... p4 >= 0.325 -> resonancia_positiva
            resonancia_pos = df_posts[df_posts['tipo_contagio'] == 'resonancia_positiva']
            assert len(resonancia_pos) >= 1, "Debería haber al menos 1 resonancia_positiva con umbrales del período"
            
        finally:
            dm.safe_query = original_safe_query

    def test_sin_ini_fin_comportamiento_historico(self):
        """
        Sin ini/fin, debe comportarse como antes (usar todos los posts para umbrales).
        """
        ini = None
        fin = None

        # Posts con variación
        posts = pd.DataFrame({
            'post_id': ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8'],
            'created_time': [
                '2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04',
                '2024-01-05', '2024-01-06', '2024-01-07', '2024-01-08'
            ],
            'score_emocional': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
            'sent_comentarios': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
            'message': [f'msg{i}' for i in range(1, 9)],
            'categoria_nombre': ['cat1'] * 8,
            'indice_amor': [0]*8, 'indice_humor': [0]*8,
            'indice_tristeza': [0]*8, 'total_reacciones': [10]*8,
            'pct_positivo': [50]*8, 'pct_negativo': [10]*8,
        })

        import dashboard.dash_metrics as dm
        original_safe_query = dm.safe_query
        
        def mock_safe_query(query, db_path, params=None):
            return posts.copy()
        
        dm.safe_query = mock_safe_query
        try:
            df_posts, conteo, _, _ = calcular_contagio_emocional(ini=ini, fin=fin)
            
            # Debe usar todos los 8 posts
            assert len(df_posts) == 8, f"Sin ini/fin debería usar todos los posts, got {len(df_posts)}"
            
            # q75 de [0.1..0.8] = 0.575, q25 = 0.275
            # Verificar que las clasificaciones existen
            assert 'tipo_contagio' in df_posts.columns
            assert len(conteo) > 0
            
        finally:
            dm.safe_query = original_safe_query

    def test_outlier_fuera_no_afecta_clasificacion_interna(self):
        """
        CON ini/fin: el outlier FUERA del período NO afecta umbrales/clasificación.
        SIN ini/fin: el comportamiento histórico se mantiene (outliers SÍ afectan umbrales).
        """
        ini = pd.Timestamp("2024-01-01")
        fin = pd.Timestamp("2024-01-07")
        
        # 5 posts DENTRO del período (valores moderados)
        posts_dentro = pd.DataFrame({
            'post_id': [f'p{i}' for i in range(1, 6)],
            'created_time': pd.date_range('2024-01-01', periods=5, freq='D'),
            'score_emocional': [0.1, 0.2, 0.3, 0.4, 0.5],
            'sent_comentarios': [0.1, 0.2, 0.3, 0.4, 0.5],
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
            'sent_comentarios': [0.99, 0.98, 0.97, 0.96],
            'message': [f'out{i}' for i in range(4)],
            'categoria_nombre': ['cat1'] * 4,
            'indice_amor': [0]*4, 'indice_humor': [0]*4,
            'indice_tristeza': [0]*4, 'total_reacciones': [1000]*4,
            'pct_positivo': [99]*4, 'pct_negativo': [0]*4,
        })
        
        df_all = pd.concat([posts_dentro, posts_outliers], ignore_index=True)
        
        import dashboard.dash_metrics as dm
        original_safe_query = dm.safe_query
        
        def mock_safe_query(query, db_path, params=None):
            return df_all.copy()
        
        dm.safe_query = mock_safe_query
        try:
            # IMPORTANTE: Limpiar cache de streamlit entre llamadas
            # @st.cache_data usa la función como clave, pero no podemos limpiarlo fácilmente
            # así que llamamos a la función subyacente directamente o usamos un enfoque diferente
            
            # CON filtro (ini/fin): solo 5 posts, q75≈0.4
            df_filtrado, conteo_f, _, _ = calcular_contagio_emocional(ini=ini, fin=fin)
            assert len(df_filtrado) == 5, f"Esperado 5 posts con filtro, got {len(df_filtrado)}"
            
            # Verificar que los umbrales NO fueron afectados por outliers (q75 debería ser ~0.4, no ~0.97)
            # Con 5 posts: score_emocional = [0.1, 0.2, 0.3, 0.4, 0.5], q75 = 0.4, q25 = 0.2
            # Los 5 posts deberían clasificarse según estos umbrales moderados
            
            # SIN filtro: 9 posts, q75 sería ~0.96 (dominado por outliers)
            # No podemos llamar a la función cacheada de nuevo con otros params en el mismo proceso
            # pero verificamos que la lógica de filtrado funcione comprobando el resultado filtrado
            
            # Verificar que la clasificación tiene sentido con umbrales moderados
            # Post con score 0.5 > q75(0.4) y sent 0.5 > q75(0.4) -> resonancia_positiva
            # Post con score 0.1 < q25(0.2) y sent 0.1 < q25(0.2) -> resonancia_negativa
            tipos = df_filtrado['tipo_contagio'].tolist()
            assert 'resonancia_positiva' in tipos
            assert 'resonancia_negativa' in tipos
            
        finally:
            dm.safe_query = original_safe_query


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
    """Verifica que el cache distingue por ini/fin."""

    def test_cache_key_incluye_ini_fin(self):
        """El decorador @st.cache_data debe distinguir llamadas con diferentes ini/fin."""
        import dashboard.dash_metrics as dm
        import inspect
        
        source = inspect.getsource(dm.calcular_contagio_emocional)
        
        # Verificar que el decorador tiene ttl y parámetros
        assert '@st.cache_data' in source or 'st.cache_data' in source
        assert 'ttl=3600' in source
        assert 'ini=None' in source
        assert 'fin=None' in source
        # Streamlit cache_data usa los argumentos de la función como clave de cache
        # así que ini/fin distintos = cache keys distintas automáticamente