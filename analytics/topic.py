"""Clasificación de tema por reglas léxicas (10 categorías fijas).

Sin modelos entrenados, sin llamadas a APIs. Cada categoría tiene un léxico
de palabras/frases semilla. Clasifica por conteo de coincidencias; mayor
conteo gana; sin coincidencias y texto vacío → "no_aplica". Texto con
señal pero sin match → propuesta abierta en taxonomias_pendientes.json.
"""
import re
import unicodedata

from analytics._propuestas import _registrar_propuesta


# ── Normalización ──

_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def _normalize(text: str) -> str:
    text = text.lower()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(_normalize(text))


def _raw_lower(text: str) -> str:
    return (text or "").lower().strip()


# ── Léxico por tema (10 categorías fijas) ──

TOPIC_LEXICON: dict[str, set[str]] = {
    # ── Obras y servicios públicos ──
    "obras_servicios": {
        "obra", "obras", "bache", "baches", "pavimento", "pavimentar",
        "calles", "calle", "parque", "parques", "puente", "puentes",
        "construccion", "construir", "agua", "agua potable", "luz",
        "alumbrado", "basura", "reciclaje", "basurero", "alcantarillado",
        "alcantarilla", "drenaje", "cloaca", "mantenimiento", "reparacion",
        "reparar", "baldosa", "acera", "banqueta", "andador",
        "infraestructura", "semilla", "arbol", "arboles", "jardin",
        "plaza", "escalinata", "techo", "techar", "coladera",
        "tapa", "tapa de drenaje", "luminaria", "poste de luz",
        "trámite", "tramite", "predial", "agua y luz",
    },
    # ── Seguridad ──
    "seguridad": {
        "seguridad", "delincuencia", "robo", "robos", "asalto", "asaltos",
        "hurto", "hurtos", "pandilla", "pandillas", "marero", "maras",
        "violencia", "violento", "violenta", "policia", "policía",
        "guardia", "patrulla", "vigilancia", "denuncia", "denuncias",
        "femicidio", "extorsion", "extorsión", "sicariato", "narcotrafico",
        "droga", "drogas", "arma", "armas", "escopeta", "pistola",
        "navaja", "cuchillo", "inseguridad", "inseguro", "insegura",
        "asesinato", "asesino", "muerte", "secuestro", "hostigamiento",
        "acoso", "amenaza", "amenazas", "crimen", "crimenes",
        "redada", "allanamiento", "captura", "detenido", "detenidos",
    },
    # ── Movilidad ──
    "movilidad": {
        "movilidad", "transporte", "tráfico", "trafico", "semáforo",
        "semaforo", "bus", "buses", "camion", "camión", "ruta", "rutas",
        "microbús", "microbus", "colectivo", "taxi", "uber", "didi",
        "accidente", "accidentes", "choque", "choques", "atropello",
        "estacionamiento", "estacionar", "vehículo", "vehiculo", "carro",
        "carros", "transito", "carril", "carriles", "vía", "via",
        "autopista", "intersección", "interseccion", "retorno",
        "glorieta", "bache de tránsito", "velocidad", "exceso de velocidad",
        "pico", "hora pico", "embotellamiento", "congestión", "congestion",
    },
    # ── Empleo ──
    "empleo": {
        "empleo", "trabajo", "trabajar", "empleo formal", "empleo decente",
        "salario", "sueldo", "nómina", "nomina", "contrato",
        "contratación", "contratacion", "vacante", "vacantes",
        "emprendimiento", "emprender", "negocio", "negocios", "empresa",
        "empresas", "microempresa", "pyme", "comercio", "comerciar",
        "economía", "economia", "ingreso", "ingresos", "oportunidad",
        "oportunidades", "capacitación", "capacitacion", "curso",
        "puestos", "puesto", "chamba", "jale", "fachero",
    },
    # ── Salud ──
    "salud": {
        "salud", "hospital", "hospitales", "clínica", "clinica",
        "médico", "medico", "médica", "medica", "doctor", "doctores",
        "enfermera", "enfermero", "medicina", "medicamentos",
        "medicamento", "pastilla", "pastillas", "insumo", "insumos",
        "jornada médica", "cirugía", "cirugia", "emergencia",
        "emergencias", "ambulancia", "ambulancia", "consulta",
        "cita médica", "laboratorio", "análisis", "analisis",
        "EPS", "IGSS", "seguro social", "enfermedad", "enfermo",
        "enferma", "dengue", "covid", "gripe", "fiebre",
        "desnutrición", "desnutricion", "vacuna", "vacunación",
    },
    # ── Educación ──
    "educacion": {
        "educación", "educacion", "escuela", "escuelas", "colegio",
        "colegios", "instituto", "maestro", "maestros", "profesor",
        "profesores", "beca", "becas", "estudiante", "estudiantes",
        "alumno", "alumnos", "escolar", "escolares", "matrícula",
        "matricula", "aula", "aulas", "material", "materiales",
        "libro", "libros", "uniforme", "uniformes", "desayuno escolar",
        "UTEB", "universidad", "facultad", "título", "titulo",
        "graduación", "graduacion", "enseñanza", "enseñar", "aprender",
        "clase", "clases", "tarea", "tareas", "calificación",
    },
    # ── Medio ambiente ──
    "medio_ambiente": {
        "medio ambiente", "medioambiente", "contaminación", "contaminacion",
        "contaminado", "contaminada", "rio", "ríos", "agua contaminada",
        "arbol", "árboles", "reforestación", "reforestacion", "sembrar",
        "siembra", "desechos", "basura", "reciclaje", "reciclar",
        "área verde", "area verde", "parque", "bosque", "fauna",
        "flora", "naturaleza", "ecología", "ecologia", "sustentable",
        "cambio climático", "cambio climatico", "sequía", "sequia",
        "inundación", "inundacion", "deforestación", "tala",
        "residuos", "vertedero", "recolección", "limpieza ambiental",
    },
    # ── Gobernanza / Transparencia ──
    "gobernanza": {
        "corrupción", "corrupcion", "corrupto", "corrupta", "fraude",
        "mal gobierno", "mal uso", "malversación", "malversacion",
        "desfalco", "soborno", "cohecho", "transparencia",
        "rendición de cuentas", "rendicion de cuentas", "presupuesto",
        "gasto público", "gasto publico", "licitación", "licitacion",
        "contratación directa", "concusion", "prevaricato",
        "abuso de poder", "abuso", "autoridad", "alcalde",
        "alcaldía", "alcaldia", "municipio", "gestión municipal",
        "gestion municipal", "funcionario", "funcionarios",
        "político", "politico", "partido", "elecciones",
        "confianza institucional", "desconfianza", "impunidad",
        "doble filo", "compadrazgo", "nepotismo",
    },
    # ── Cultura y deportes ──
    "cultura_deportes": {
        "cultura", "cultural", "evento", "eventos", "fiesta", "fiestas",
        "festiva", "festival", "festivales", "tradición", "tradicion",
        "tradiciones", "concierto", "conciertos", "música", "musica",
        "baile", "danza", "teatro", "pintura", "arte",
        "deporte", "deportes", "cancha", "canchas", "estadio",
        "torneo", "torneos", "futbol", "fútbol", "basketball",
        "atletismo", "natación", "deportista", "atleta",
        "olímpico", "olimpico", "maratón", "maraton",
        "velódromo", "polideportivo", "gimnasio",
    },
    # ── Apoyo genérico ──
    "apoyo_generico": {
        "buen trabajo", "bien hecho", "sigue asi", "sigue así",
        "felicidades", "éxitos", "exitos", "bendiciones",
        "gracias por todo", "te apoyo", "te apoyamos",
        "adelante", "fuerza", "animo", "ánimo",
        "te deseamos lo mejor", "mi apoyo",
    },
}

# Todas las categorías válidas (incluye no_aplica)
CATEGORIAS_TEMA = set(TOPIC_LEXICON.keys()) | {"no_aplica"}


# ── Remapeo de categorías legacy ──


# ── Result type ──

from dataclasses import dataclass, field as dc_field


@dataclass
class TopicResult:
    tema: str = "no_aplica"
    scores: dict = dc_field(default_factory=dict)
    evidence: list[str] = dc_field(default_factory=list)
    n_coincidencias: int = 0


# ── Core classifier ──

def classify_topic(text: str) -> TopicResult:
    """Clasifica el tema de un texto usando léxico semilla.

    El resultado pasa por remapear() del catálogo abierto.
    Si no hay coincidencias pero el texto tiene contenido real (no vacío
    ni saludo de una palabra), se registra como propuesta abierta.

    Retorna TopicResult con la categoría de mayor conteo, o "no_aplica"
    solo para texto vacío o genuinamente sin señal.
    """
    if not text or not text.strip():
        return TopicResult(tema="no_aplica")

    tokens = set(_tokenize(text))
    low = _raw_lower(text)

    scores: dict[str, int] = {}
    evidence_map: dict[str, list[str]] = {}

    for tema, lexicon in TOPIC_LEXICON.items():
        hits = 0
        evi = []
        for seed in lexicon:
            seed_norm = _normalize(seed)
            if " " in seed_norm:
                if seed_norm in low:
                    hits += 1
                    evi.append(seed)
            else:
                if seed_norm in tokens:
                    hits += 1
                    evi.append(seed)
        if hits > 0:
            scores[tema] = hits
            evidence_map[tema] = evi

    if not scores:
        # Texto vacío, saludo o muy corto (≤5 tokens) → no_aplica (sin propuesta).
        # Texto con contenido real pero sin match → propuesta abierta.
        if len(tokens) <= 5:
            return TopicResult(tema="no_aplica", scores=scores)

        # Texto con contenido real pero sin match → propuesta abierta.
        # La propuesta se devuelve como clave, no se fuerza a 'no_aplica'.
        # Clave determinista: sorted(tokens)[0] no depende del orden de iteración del set.
        from analytics._propuestas import _registrar_propuesta
        palabra_rep = sorted(tokens)[0] if tokens else "desconocido"
        propuesta_key = f"tema_nuevo_{palabra_rep}"
        _registrar_propuesta(
            clave_propuesta=propuesta_key,
            ejemplo_texto=text[:200],
            tipo="tema",
            familia_mas_cercana="",
        )
        return TopicResult(tema=propuesta_key, scores=scores)

    best_tema = max(scores, key=lambda k: scores[k])

    # Remapear con el catálogo abierto
    from dashboard.tema_taxonomia import remapear
    best_tema = remapear(best_tema)

    return TopicResult(
        tema=best_tema,
        scores=scores,
        evidence=evidence_map.get(best_tema, []),
        n_coincidencias=scores.get(best_tema, 0),
    )


# ── Agregación batch ──

def aggregate_topics(texts: list[str]) -> dict:
    """Clasifica una lista de textos y retorna conteos por tema.

    Returns dict con:
        - total: total de textos
        - conteo: {tema: count} para cada categoría
        - pct: {tema: pct} para cada categoría
        - dominante: tema con mayor frecuencia
        - n_sin_tema: textos que cayeron en no_aplica
    """
    if not texts:
        return {"total": 0, "conteo": {}, "pct": {}, "dominante": "no_aplica", "n_sin_tema": 0}

    conteo: dict[str, int] = {t: 0 for t in CATEGORIAS_TEMA}

    for text in texts:
        result = classify_topic(text)
        # Contar también claves no-canónicas (propuestas)
        if result.tema not in conteo:
            conteo[result.tema] = 0
        conteo[result.tema] += 1

    total = len(texts)
    pct = {
        tema: round(count / total * 100, 1)
        for tema, count in conteo.items()
        if count > 0
    }

    dominante = max(conteo, key=lambda k: (conteo[k], k))
    if conteo.get(dominante, 0) == 0:
        dominante = "no_aplica"

    return {
        "total": total,
        "conteo": conteo,
        "pct": pct,
        "dominante": dominante,
        "n_sin_tema": conteo.get("no_aplica", 0),
    }
