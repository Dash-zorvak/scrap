import os
import sqlite3
import pandas as pd
import random
from datetime import datetime, timedelta
import sys
sys.path.insert(0, "/Users/pro/Downloads/scrapeo-social/dashboard")
from config import *

# Allow test to redirect to a temp DB
EXTERNOS_DB = os.getenv("EXTERNOS_DB", EXTERNOS_DB)

# ── snippet de posts simulados ──────────────────────────────────────────────

PAGINAS_EXTERNAS = [
    "La Prensa Gráfica Santa Ana",
    "El Diario de Hoy Occidente",
    "Noticias Santa Ana",
    "Ciudadanos de Santa Ana",
    "Santa Ana Noticias",
    "Concejo Municipal Oposición",
    "Vecinos Colonia Flor Blanca",
    "Radio Santa Ana",
    "El Observador Santaneco",
    "Fiscalizando Santa Ana",
]

MENSAJES_POSITIVOS = [
    "Alcalde Acevedo inaugura nueva cancha deportiva en cantón El Paraíso",
    "Alcalde Acevedo inaugura nueva cancha deportiva en cantón Las Crucitas",
    "Alcalde Acevedo inaugura nueva cancha deportiva en cantón Chiquihuatán",
    "Alcaldía Santa Ana entrega materiales a comunidades vulnerables de la zona norte",
    "Alcaldía Santa Ana entrega materiales a comunidades vulnerables de la zona sur",
    "Obras de pavimentación benefician a colonias del norte de la ciudad",
    "Obras de pavimentación benefician a colonias del sur de la ciudad",
    "Gustavo Acevedo presenta avances en proyecto de parque central",
    "Gustavo Acevedo presenta avances en proyecto de mercado municipal",
    "Más de 500 familias beneficiadas con jornada médica municipal",
    "Feria de emprendedores santanecos supera los 300 expositores este mes",
    "Alcalde anuncia becas municipales para jóvenes destacados",
    "Nuevo sistema de alumbrado público reduce incidentes en colonias",
    "Rehabilitación de calles en casco histórico avanza según lo previsto",
    "Alcaldía habilita nuevo centro de acopio para reciclaje",
]

MENSAJES_NEGATIVOS = [
    "Vecinos denuncian abandono de obras en colonia Santa Isabel",
    "Vecinos denuncian abandono de obras en colonia San Antonio",
    "Críticas al alcalde por falta de atención en zona rural de Santa Ana",
    "Retraso en proyecto prometido genera molestia ciudadana en el municipio",
    "Opositores cuestionan transparencia en licitaciones municipales",
    "Baches sin reparar en avenida principal llevan meses de espera",
    "Falta de respuesta ante emergencias por lluvias en cantones",
    "Denuncian sobreprecio en obra de pavimentación de la alcaldía",
    "Vecinos reportan contaminación en río por desechos municipales",
    "Comerciantes del centro protestan por aumento de arbitrios",
    "Sindicato municipal denuncia incumplimiento de acuerdos laborales",
    "Colectivo ciudadano exige rendición de cuentas sobre presupuesto",
    "Filtraciones en mercado central continúan sin solución",
    "Alcalde enfrenta críticas por designación de funcionarios cuestionados",
    "Promesas de campaña incumplidas en distritos del municipio",
]

MENSAJES_NEUTRALES = [
    "Alcaldía convoca a cabildo abierto para próximo mes",
    "Sesión del concejo municipal aborda presupuesto 2026",
    "Alcalde participa en reunión de alcaldes del departamento",
    "Concejo municipal discute reforma al reglamento interno",
    "Alcaldía presenta informe trimestral de gestión",
    "Junta de protección civil realiza simulacro en zona urbana",
    "Convocatoria abierta para participar en presupuesto participativo",
    "Alcaldía publica calendario de ferias y eventos culturales",
    "Unidad de género municipal ofrece talleres gratuitos",
    "Registro civil municipal extiende horario de atención",
]


def crear_externos_db():
    conn = sqlite3.connect(EXTERNOS_DB)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS external_posts (
            post_id TEXT PRIMARY KEY,
            page_name TEXT,
            page_url TEXT,
            message TEXT,
            created_time DATETIME,
            total_reactions INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            post_url TEXT,
            source TEXT DEFAULT 'deep_scraper_externo',
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS external_comments (
            comment_id TEXT PRIMARY KEY,
            post_id TEXT,
            message TEXT,
            author_name TEXT DEFAULT 'Anonymous',
            created_time DATETIME,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS external_sentimiento (
            post_id TEXT PRIMARY KEY,
            total_comentarios INTEGER,
            pct_positivo REAL,
            pct_negativo REAL,
            pct_neutral REAL,
            score_sentimiento REAL,
            comentario_mas_negativo TEXT,
            comentario_mas_positivo TEXT
        );
    """)
    conn.commit()
    conn.close()
    print(f"✓ Base de datos creada/verificada: {EXTERNOS_DB}")


def generar_datos_simulados():
    conn = sqlite3.connect(EXTERNOS_DB)
    cur = conn.cursor()

    # limpiar solo datos simulados previos (nunca borrar posts reales)
    cur.execute("DELETE FROM external_sentimiento WHERE post_id LIKE 'SIM_EXT%'")
    cur.execute("DELETE FROM external_comments WHERE post_id LIKE 'SIM_EXT%'")
    cur.execute("DELETE FROM external_posts WHERE post_id LIKE 'SIM_EXT%'")

    start = datetime(2024, 12, 1)
    end   = datetime(2026, 5, 30)
    total_days = (end - start).days

    start_ids = []

    for i in range(1, 51):
        post_id = f"SIM_EXT_{i:04d}"
        page    = random.choice(PAGINAS_EXTERNAS)
        page_url = f"https://facebook.com/{page.lower().replace(' ', '')}"

        # escoger tono según distribución 40/35/25
        r = random.random()
        if r < 0.40:
            message = random.choice(MENSAJES_POSITIVOS)
            tono = "positivo"
        elif r < 0.75:
            message = random.choice(MENSAJES_NEGATIVOS)
            tono = "negativo"
        else:
            message = random.choice(MENSAJES_NEUTRALES)
            tono = "neutral"

        created = start + timedelta(days=random.randint(0, total_days),
                                     seconds=random.randint(0, 86399))
        reactions = random.randint(50, 5000)
        num_comments = random.randint(5, 200)

        post_url = f"https://facebook.com/{post_id}"

        cur.execute("""INSERT OR REPLACE INTO external_posts
            (post_id, page_name, page_url, message, created_time,
             total_reactions, comments_count, post_url, source)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (post_id, page, page_url, message, created.isoformat(),
             reactions, num_comments, post_url, "deep_scraper_externo"))

        start_ids.append((post_id, created, tono, message))

    # ── generar comentarios y sentimiento ────────────────────────────────
    comentarios_positivos = [
        "Excelente trabajo del alcalde, se notan los avances",
        "Me alegra ver estos progresos en nuestra ciudad",
        "Buenas noticias para Santa Ana, así da gusto",
        "Apoyo total a la gestión del alcalde",
        "Sigan así, necesitamos más obras como esta",
        "Gran labor de la alcaldía, felicidades",
        "Que buena iniciativa, ojalá llegue a más colonias",
        "Se agradece el apoyo a las comunidades más necesitadas",
        "Esto es lo que necesita nuestro municipio",
        "Por fin buenas noticias para Santa Ana",
    ]
    comentarios_negativos = [
        "Solo promesas y nada concreto, ya estamos cansados",
        "Otra vez lo mismo, pura propaganda municipal",
        "No sirve de nada si no hay mantenimiento después",
        "El alcalde no cumple ni la mitad de lo que promete",
        "Corrupción y abandono, eso es lo que hay",
        "Mientras no resuelvan los baches todo es fachada",
        "Esto es una burla para los santanecos",
        "No nos representan, fuera corruptos",
        "La ciudad sigue igual de abandonada",
        "Puro show de campaña, no resuelven nada real",
    ]
    comentarios_neutrales = [
        "Habrá que esperar a ver los resultados",
        "Veremos si esto se concreta o queda en anuncio",
        "Es un avance pero falta mucho por hacer",
        "Ojalá le den seguimiento a este proyecto",
        "Habría que escuchar a todas las partes involucradas",
        "Depende de cómo se ejecute puede ser bueno o malo",
        "El tiempo dirá si fue una buena decisión",
        "Esperemos que los fondos se usen correctamente",
        "Mejor es esperar a ver los informes finales",
        "Hay que estar atentos a la transparencia del proceso",
    ]

    autores = [
        "Carlos M.", "María L.", "José R.", "Ana G.", "Pedro S.",
        "Rosa V.", "Luis A.", "Sofía P.", "Diego H.", "Carmen T.",
        "Jorge N.", "Elena Q.", "Rafael D.", "Lucía B.", "Mario F.",
        "Andrea C.", "Roberto Z.", "Patricia K.", "Fernando J.", "Gloria W.",
    ]

    for post_id, created, tono, message in start_ids:
        num_comments = random.randint(3, 8)

        # definir rangos de sentimiento según tono
        if tono == "positivo":
            pct_pos = random.uniform(0.60, 0.80)
            pct_neg = random.uniform(0.05, 0.15)
            pool_pos = comentarios_positivos
            pool_neg = comentarios_negativos
        elif tono == "negativo":
            pct_pos = random.uniform(0.10, 0.25)
            pct_neg = random.uniform(0.40, 0.65)
            pool_pos = comentarios_negativos
            pool_neg = comentarios_positivos
        else:
            pct_pos = random.uniform(0.30, 0.45)
            pct_neg = random.uniform(0.15, 0.25)
            pool_pos = comentarios_positivos
            pool_neg = comentarios_negativos

        pct_neu = 1.0 - pct_pos - pct_neg
        score = pct_pos - pct_neg

        # generar comentarios
        comentarios_generados = []
        for j in range(num_comments):
            r2 = random.random()
            if r2 < pct_pos:
                txt = random.choice(pool_pos)
            elif r2 < pct_pos + pct_neg:
                txt = random.choice(pool_neg)
            else:
                txt = random.choice(comentarios_neutrales)

            comentarios_generados.append(txt)
            author = random.choice(autores)
            cid = f"{post_id}_C{j:02d}"
            ctime = created + timedelta(hours=random.randint(0, 72),
                                        minutes=random.randint(0, 59))
            cur.execute("""INSERT OR REPLACE INTO external_comments
                (comment_id, post_id, message, author_name, created_time)
                VALUES (?,?,?,?,?)""",
                (cid, post_id, txt, author, ctime.isoformat()))

        # comentarios extremos
        if tono == "positivo":
            mas_pos = random.choice(comentarios_positivos)
            mas_neg = random.choice(comentarios_negativos)
        else:
            mas_pos = random.choice(pool_pos)
            mas_neg = random.choice(pool_neg)

        cur.execute("""INSERT OR REPLACE INTO external_sentimiento
            (post_id, total_comentarios, pct_positivo, pct_negativo,
             pct_neutral, score_sentimiento,
             comentario_mas_negativo, comentario_mas_positivo)
            VALUES (?,?,?,?,?,?,?,?)""",
            (post_id, num_comments, round(pct_pos, 4), round(pct_neg, 4),
             round(pct_neu, 4), round(score, 4),
             mas_neg, mas_pos))

    conn.commit()
    conn.close()
    print("✓ 50 posts simulados generados con comentarios y sentimiento")


def imprimir_resumen():
    conn = sqlite3.connect(EXTERNOS_DB)

    total_posts = pd.read_sql("SELECT COUNT(*) AS n FROM external_posts", conn).iloc[0, 0]
    fuentes = pd.read_sql("SELECT DISTINCT page_name FROM external_posts", conn)["page_name"].tolist()
    min_date = pd.read_sql("SELECT MIN(created_time) AS d FROM external_posts", conn).iloc[0, 0]
    max_date = pd.read_sql("SELECT MAX(created_time) AS d FROM external_posts", conn).iloc[0, 0]

    # distribución de tono
    df_posts = pd.read_sql("SELECT post_id FROM external_posts", conn)
    df_sent = pd.read_sql("SELECT post_id, score_sentimiento FROM external_sentimiento", conn)
    merged = df_posts.merge(df_sent, on="post_id", how="left")

    # clasificar por score
    def clasificar(score):
        if score is None:
            return "neutral"
        if score > 0.15:
            return "positivo"
        elif score < -0.15:
            return "negativo"
        return "neutral"

    merged["tono"] = merged["score_sentimiento"].apply(clasificar)
    dist = merged["tono"].value_counts()

    # top 3 fuentes
    top3 = pd.read_sql("""SELECT page_name, COUNT(*) AS cnt
                           FROM external_posts
                           GROUP BY page_name
                           ORDER BY cnt DESC LIMIT 3""", conn)
    conn.close()

    print("=" * 60)
    print("  MÓDULO 5 — CONTEXTO EXTERNO (SIMULADO)")
    print("=" * 60)
    print("ADVERTENCIA: Datos simulados — reemplazar cuando lleguen URLs reales")
    print()
    print(f"  Total posts externos: {total_posts}")
    print(f"  Fuentes monitoreadas: {len(fuentes)}")
    print(f"  Rango de fechas: {min_date} a {max_date}")
    print(f"  Distribución de tono:")
    print(f"    - Positivos: {dist.get('positivo', 0)} posts")
    print(f"    - Negativos: {dist.get('negativo', 0)} posts")
    print(f"    - Neutrales: {dist.get('neutral', 0)} posts")
    print(f"  Top 3 fuentes más activas:")
    for _, row in top3.iterrows():
        print(f"    - {row['page_name']}: {row['cnt']} posts")


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Módulo 5 — datos simulados de contexto externo")
    parser.add_argument("--demo", action="store_true", help="Ejecutar seed de datos simulados")
    args = parser.parse_args()

    # ═══════════════════════════════════════════════════════════════════════
    # SAFETY LOCK: Este script genera 50 filas SIM_EXT_ en externos.db y
    # crea la tabla external_sentimiento. NO debe ejecutarse en producción
    # porque contamina la DB con datos ficticios que el dashboard muestra
    # como reales (dashboard/app.py:567 lee external_sentimiento).
    #
    # Requiere flag explícito --demo o env var ENABLE_DEMO_SEED=1.
    # ═══════════════════════════════════════════════════════════════════════

    if args.demo or os.getenv("ENABLE_DEMO_SEED", "0") == "1":
        crear_externos_db()
        generar_datos_simulados()
        imprimir_resumen()
        print()
        print("✓ Módulo 5 completo.")
        print("⚠ RECORDATORIO: Reemplazar datos simulados con URLs reales del deep scraper")
    else:
        print("⚠ Demo seed desactivado. Para ejecutar:")
        print("  python dashboard/modulo5_externos.py --demo")
        print("  ENABLE_DEMO_SEED=1 python dashboard/modulo5_externos.py")
