"""Tests for dashboard/intencion_taxonomia.py — catálogo abierto de intención."""

from dashboard.intencion_taxonomia import (
    FAMILIAS_INTENCION,
    INTENCIONES,
    INTENCIONES_VALIDAS,
    etiqueta_familia_intencion,
    etiqueta_intencion,
    normalizar_intencion,
)


def test_todas_las_claves_normalizan_a_si_mismas():
    """Cada una de las 108 claves reales de INTENCIONES_VALIDAS debe ser
    devuelta exactamente tal cual por normalizar_intencion()."""
    for clave in INTENCIONES_VALIDAS:
        assert normalizar_intencion(clave) == clave, (
            f"normalizar_intencion({clave!r}) devolvió {normalizar_intencion(clave)!r}"
        )


def test_ic_mayusculas_y_minusculas_normalizan_igual():
    """normalizar_intencion('IC-0101') y normalizar_intencion('ic-0101')
    deben devolver la misma clave canónica."""
    mayus = normalizar_intencion("IC-0101")
    minus = normalizar_intencion("ic-0101")
    assert mayus == minus == "ic-0101"


def test_ic_mixto_case_normaliza():
    """Cualquier combinación de case en un código IC-XXXX debe normalizar
    a la clave canónica en minúsculas."""
    assert normalizar_intencion("Ic-0506") == "ic-0506"
    assert normalizar_intencion("iC-0810") == "ic-0810"


def test_etiqueta_intencion_para_clave_valida():
    """etiqueta_intencion() devuelve label legible para claves del catálogo."""
    assert etiqueta_intencion("ic-0101") == "Describir"
    assert etiqueta_intencion("hum-03") == "Satirizar"


def test_etiqueta_intencion_para_clave_desconocida():
    """etiqueta_intencion() devuelve el código capitalizado si no está en catálogo."""
    assert etiqueta_intencion("nueva-clave") == "Nueva-clave"
    assert etiqueta_intencion(None) == ""


def test_normalizar_intencion_none_devuelve_none():
    """None no registra propuesta y devuelve None."""
    assert normalizar_intencion(None) is None


def test_normalizar_intencion_desconocida_devuelve_clave():
    """Una intención no reconocida se devuelve tal cual (patrón abierto),
    nunca fuerza a un valor por defecto."""
    resultado = normalizar_intencion("nueva_intencion_rara")
    assert resultado == "nueva_intencion_rara"


def test_todas_las_claves_son_minusculas():
    """Todas las claves de INTENCIONES deben ser minúsculas."""
    for clave in INTENCIONES:
        assert clave == clave.lower(), f"Clave {clave!r} no es minúscula"


def test_108_semillas():
    """El catálogo debe tener exactamente 108 semillas."""
    assert len(INTENCIONES) == 108
    assert len(INTENCIONES_VALIDAS) == 108


def test_todas_las_familias_del_intencion_existen():
    """Cada familia referenciada en INTENCIONES debe existir en FAMILIAS_INTENCION."""
    for clave, meta in INTENCIONES.items():
        fam = meta["familia"]
        assert fam in FAMILIAS_INTENCION, (
            f"INTENCIONES[{clave}] referencia familia {fam!r} que no existe en FAMILIAS_INTENCION"
        )


def test_etiqueta_familia_intencion():
    """etiqueta_familia_intencion() devuelve label legible para las 12 familias."""
    assert etiqueta_familia_intencion("informacion") == "Información y Descripción"
    assert etiqueta_familia_intencion("enganoso") == "Contenido Potencialmente Engañoso"
    assert etiqueta_familia_intencion("no_existe") == "No_existe"
