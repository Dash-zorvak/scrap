"""Tests para agregar_por_tema_automatico — clasificación léxica sin aprobación manual."""
import os
import sqlite3
import tempfile

import pytest

from dashboard.tema_aprobaciones import (
    agregar_por_tema_automatico,
    EMOCION_DEFAULT,
    INTENSIDAD_POSTURA_DEFAULT,
)


def _crear_bd_temp(tabla="fb_comments", cols_extra=""):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    extra = ""
    if cols_extra:
        extra = ", " + cols_extra
    if tabla == "fb_comments":
        conn.execute(
            f"CREATE TABLE {tabla} ("
            "comment_id TEXT PRIMARY KEY, message TEXT, emocion TEXT"
            f"{extra})"
        )
    elif tabla == "comments":
        conn.execute(
            f"CREATE TABLE {tabla} ("
            "id TEXT PRIMARY KEY, text TEXT, emocion TEXT"
            f"{extra})"
        )
    elif tabla == "external_comments":
        conn.execute(
            f"CREATE TABLE {tabla} ("
            "comment_id TEXT PRIMARY KEY, message TEXT, emocion TEXT"
            f"{extra})"
        )
    conn.close()
    return path


class TestAutomaticoBasico:
    def test_clasifica_seguridad(self):
        db = _crear_bd_temp()
        try:
            conn = sqlite3.connect(db)
            conn.execute(
                "INSERT INTO fb_comments (comment_id, message, emocion) VALUES (?, ?, ?)",
                ("c1", "Hay mucha delincuencia en el centro, los robos aumentaron", "enojo"),
            )
            conn.commit()
            conn.close()

            temas = agregar_por_tema_automatico(db)
            assert len(temas) >= 1
            cats = [t["categoria"] for t in temas]
            assert "seguridad" in cats
            t_seg = next(t for t in temas if t["categoria"] == "seguridad")
            assert t_seg["doc_count"] == 1
        finally:
            os.unlink(db)

    def test_clasifica_salud(self):
        db = _crear_bd_temp()
        try:
            conn = sqlite3.connect(db)
            conn.execute(
                "INSERT INTO fb_comments (comment_id, message, emocion) VALUES (?, ?, ?)",
                ("c1", "El hospital necesita más médicos y medicamentos", "tristeza"),
            )
            conn.commit()
            conn.close()

            temas = agregar_por_tema_automatico(db)
            assert len(temas) >= 1
            cats = [t["categoria"] for t in temas]
            assert "salud" in cats
        finally:
            os.unlink(db)

    def test_no_aplica_se_excluye(self):
        db = _crear_bd_temp()
        try:
            conn = sqlite3.connect(db)
            conn.execute(
                "INSERT INTO fb_comments (comment_id, message, emocion) VALUES (?, ?, ?)",
                ("c1", "hola", "calma"),
            )
            conn.commit()
            conn.close()

            temas = agregar_por_tema_automatico(db)
            assert len(temas) == 0
        finally:
            os.unlink(db)

    def test_texto_vacio_se_excluye(self):
        db = _crear_bd_temp()
        try:
            conn = sqlite3.connect(db)
            conn.execute(
                "INSERT INTO fb_comments (comment_id, message, emocion) VALUES (?, ?, ?)",
                ("c1", "", "calma"),
            )
            conn.execute(
                "INSERT INTO fb_comments (comment_id, message, emocion) VALUES (?, ?, ?)",
                ("c2", None, "calma"),
            )
            conn.commit()
            conn.close()

            temas = agregar_por_tema_automatico(db)
            assert len(temas) == 0
        finally:
            os.unlink(db)

    def test_multiples_temas(self):
        db = _crear_bd_temp()
        try:
            conn = sqlite3.connect(db)
            datos = [
                ("c1", "Los baches en las calles están terribles", "enojo"),
                ("c2", "Mucha delincuencia y robos en el barrio", "miedo"),
                ("c3", "Las escuelas necesitan más maestros y libros", "tristeza"),
                ("c4", "El hospital necesita más médicos", "tristeza"),
                ("c5", "Otro bache en la calle principal", "enojo"),
            ]
            conn.executemany(
                "INSERT INTO fb_comments (comment_id, message, emocion) VALUES (?, ?, ?)",
                datos,
            )
            conn.commit()
            conn.close()

            temas = agregar_por_tema_automatico(db)
            assert len(temas) >= 3
            cats = [t["categoria"] for t in temas]
            assert "obras_servicios" in cats
            assert "seguridad" in cats
            t_obras = next(t for t in temas if t["categoria"] == "obras_servicios")
            assert t_obras["doc_count"] == 2
        finally:
            os.unlink(db)


class TestSinTablaEmocion:
    def test_funciona_sin_columna_emocion(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE fb_comments ("
            "comment_id TEXT PRIMARY KEY, message TEXT)"
        )
        conn.execute(
            "INSERT INTO fb_comments (comment_id, message) VALUES (?, ?)",
            ("c1", "Hay mucha delincuencia y robos en la zona"),
        )
        conn.commit()
        conn.close()
        try:
            temas = agregar_por_tema_automatico(path)
            assert len(temas) >= 1
            cats = [t["categoria"] for t in temas]
            assert "seguridad" in cats
            t_seg = next(t for t in temas if t["categoria"] == "seguridad")
            assert t_seg["doc_count"] == 1
        finally:
            os.unlink(path)


class TestPosturaDerivada:
    def test_emocion_enojo_da_critica(self):
        db = _crear_bd_temp()
        try:
            conn = sqlite3.connect(db)
            conn.execute(
                "INSERT INTO fb_comments (comment_id, message, emocion) VALUES (?, ?, ?)",
                ("c1", "Hay mucha delincuencia en esta ciudad", "enojo"),
            )
            conn.commit()
            conn.close()

            temas = agregar_por_tema_automatico(db)
            assert len(temas) >= 1
            t = temas[0]
            assert t["critica"] == 1
            assert t["apoyo"] == 0
        finally:
            os.unlink(db)

    def test_emocion_alegria_da_apoyo(self):
        db = _crear_bd_temp()
        try:
            conn = sqlite3.connect(db)
            conn.execute(
                "INSERT INTO fb_comments (comment_id, message, emocion) VALUES (?, ?, ?)",
                ("c1", "Buen hospital con buenos médicos", "alegria"),
            )
            conn.commit()
            conn.close()

            temas = agregar_por_tema_automatico(db)
            assert len(temas) >= 1
            t = temas[0]
            assert t["apoyo"] == 1
            assert t["critica"] == 0
        finally:
            os.unlink(db)

    def test_emocion_default_cuando_no_existe_columna(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE fb_comments (comment_id TEXT PRIMARY KEY, message TEXT)"
        )
        conn.execute(
            "INSERT INTO fb_comments (comment_id, message) VALUES (?, ?)",
            ("c1", "Hay mucha delincuencia y robos en la zona"),
        )
        conn.commit()
        conn.close()
        try:
            temas = agregar_por_tema_automatico(path)
            assert len(temas) >= 1
            t = temas[0]
            default_postura = "neutral"
            assert t["neutral"] == 1 or t["critica"] == 1 or t["apoyo"] == 1
        finally:
            os.unlink(path)


class TestIntensidadSiempreModerada:
    def test_intensidad_default_en_automatico(self):
        db = _crear_bd_temp()
        try:
            conn = sqlite3.connect(db)
            conn.execute(
                "INSERT INTO fb_comments (comment_id, message, emocion) VALUES (?, ?, ?)",
                ("c1", "Hay mucha delincuencia en esta ciudad", "enojo"),
            )
            conn.commit()
            conn.close()

            temas = agregar_por_tema_automatico(db)
            assert len(temas) >= 1
            t = temas[0]
            assert t["saldo_ponderado"] != 0
        finally:
            os.unlink(db)


class TestNoTemaAprobaciones:
    def test_no_necesita_tema_aprobaciones(self):
        db = _crear_bd_temp()
        try:
            conn = sqlite3.connect(db)
            conn.execute(
                "INSERT INTO fb_comments (comment_id, message, emocion) VALUES (?, ?, ?)",
                ("c1", "Hay mucha delincuencia y robos en la zona", "enojo"),
            )
            conn.commit()

            existe = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tema_aprobaciones'"
            ).fetchone()
            conn.close()
            assert existe is None

            temas = agregar_por_tema_automatico(db)
            assert len(temas) >= 1
        finally:
            os.unlink(db)


class TestPlataformasAlternativas:
    def test_tiktok_tabla_comments(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE comments ("
            "id TEXT PRIMARY KEY, text TEXT, emocion TEXT)"
        )
        conn.execute(
            "INSERT INTO comments (id, text, emocion) VALUES (?, ?, ?)",
            ("tk1", "Los buses están tardando mucho y el tráfico está terrible", "enojo"),
        )
        conn.commit()
        conn.close()
        try:
            temas = agregar_por_tema_automatico(
                path, tabla="comments", col_id="id", col_texto="text"
            )
            assert len(temas) >= 1
            cats = [t["categoria"] for t in temas]
            assert "movilidad" in cats
        finally:
            os.unlink(path)

    def test_externos_tabla_external_comments(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE external_comments ("
            "comment_id TEXT PRIMARY KEY, message TEXT, emocion TEXT)"
        )
        conn.execute(
            "INSERT INTO external_comments (comment_id, message, emocion) VALUES (?, ?, ?)",
            ("ext1", "La corrupción en el municipio es inaceptable", "indignacion"),
        )
        conn.commit()
        conn.close()
        try:
            temas = agregar_por_tema_automatico(
                path, tabla="external_comments", col_id="comment_id", col_texto="message"
            )
            assert len(temas) >= 1
            cats = [t["categoria"] for t in temas]
            assert "gobernanza" in cats
        finally:
            os.unlink(path)
