import re
import os
import logging
import unicodedata
import functools
from typing import Optional, List, Dict, Tuple
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

TOPIC_KEYWORDS = {
    "obras_publicas": [
        "bache", "baches", "calle", "calles", "carpeta", "asfalto", "puente",
        "parque", "obra", "obras", "cordon", "summo", "vereda", "acera",
        "drenaje", "alcantarillado", "construccion", "reparacion", "pavimento",
        "pavimentacion", "adoquin", "adoquinado", "infraestructura", "callejon",
        "bulevar", "carretera", "rotonda", "redondel", "pasarela", "anden",
        "mejoramiento vial", "vialidad", "construyendo", "reconstruccion",
        "remodelacion", "embellecimiento", "jardin", "jardines", "area verde",
        "cancha", "canchas", "deportiva", "polideportivo", "pista", "estadio",
        "gimnasio", "parque infantil", "juegos", "mirador", "turistico",
        "maquinaria", "lotificacion", "terreno", "terrenos",
        "calle principal", "rehabilitacion", "obra gris", "cimientos",
        "colado", "colada", "loseta", "baldosa", "puente peatonal",
        "paso a desnivel", "tunel", "derrumbe", "deslizamiento", "talud",
        "contencion", "muro", "muros", "pavimentar", "via principal",
        "construccion", "construyendo", "reconstruyendo",
    ],
    "seguridad": [
        "robo", "robos", "asalto", "asaltos", "delincuencia", "delincuente",
        "seguridad", "policia", "crimen", "matar", "muerte", "asesinato",
        "pandilla", "extorsion", "amenaza", "violencia",
        "camaras", "videovigilancia", "patrullaje", "seguridad ciudadana",
        "prevencion", "alumbrado publico", "denuncia",
        "proteccion", "resguardo", "militares", "ejercito", "pnc", "fgr",
        "pandilleros", "maras", "marero", "mareros", "rondas", "vigilante",
        "vigilancia", "motin", "intoxicacion", "intoxicado",
        "balacera", "disparos", "arma blanca", "arma de fuego", "portacion",
        "captura", "capturado", "detenido", "detencion", "orden de captura",
        "seguridad publica", "prevencion del delito", "carcel", "prision",
        "presidio", "reo", "reos", "ciudadano vigilante",
    ],
    "servicios_publicos": [
        "agua", "luz", "electricidad", "basura", "recoleccion", "servicio",
        "corte", "servicios", "tuberia", "alcantarillado", "desague",
        "potable", "cloro", "afectado", "sin agua", "sin luz",
        "alumbrado", "alumbrado publico", "fuga", "caneria", "tuberia rota",
        "mantenimiento", "limpieza", "aseo", "mercado", "cementerio",
        "registro", "municipal", "tramite", "permiso",
        "enlace", "link", "pagina web", "digital", "virtual",
        "ventanilla", "atencion al publico", "horario", "oficina",
        "reclamo", "queja", "solicitud", "solicitar", "buzon", "caja",
        "pago", "pagar", "recibo", "factura", "tarifa", "cobro",
        "inundacion", "calle anegada", "anega", "desbordamiento",
        "desborde", "aguas lluvias", "aguas negras", "aguas servidas",
        "tuberia tapada", "fosa", "pozo", "septico",
        "recolector", "camion de basura", "contenedor",
        "alumbrado electrico", "poste", "cableado", "transformador",
        "sin agua potable", "corte de luz", "apagon",
    ],
    "empleo": [
        "trabajo", "empleo", "desempleo", "desempleado", "negocio", "negocios",
        "empresa", "empresas", "trabajador", "patron", "formal", "informal",
        "vacante", "contratar", "feria de empleo", "oportunidad laboral",
        "emprendedor", "emprendimiento", "microempresa", "mipyme",
        "capacitacion", "taller", "curso", "formacion",
        "empleo joven", "bolsa de trabajo",
        "sueldo", "salario", "ingreso", "ingresos", "puesto",
        "contratacion", "contrataciones", "plaza",
        "jornada laboral", "jubilacion", "pension",
        "trabajadores", "trabajadora", "empleados", "empleada",
        "despido", "despidieron", "cesante", "sin trabajo", "contratado",
        "mano de obra", "oficio", "profesion",
        "emprendedores", "emprendedora", "empleo temporal",
    ],
    "salud": [
        "hospital", "clinica", "doctor", "doctora", "salud",
        "enfermedad", "enfermo", "consulta", "medico", "centro de salud",
        "emergencia", "ambulancia", "vacuna", "farmacia", "medicina",
        "campana de salud", "jornada medica", "odontologia", "optometria",
        "donacion de sangre", "papanicolaou", "ultrasonido", "rayos x",
        "consulta externa", "atencion medica", "bienestar", "nutricion",
        "operacion", "cirugia", "paciente",
        "cita medica", "examenes", "analisis",
        "analisis clinicos", "diagnostico",
        "tratamiento", "terapia", "rehabilitacion fisica",
        "covid", "covid-19", "pandemia", "virus", "sintomas",
        "fiebre", "gripe", "resfriado", "tos", "dolor",
        "jornada de salud", "feria de salud", "salud publica",
        "ambulancia municipal", "centro de salud cercano",
    ],
    "educacion": [
        "escuela", "colegio", "educacion", "maestro", "maestra",
        "estudiante", "alumno", "clase", "universidad", "becas",
        "material", "uniforme", "instituto", "paquete escolar", "entrega de",
        "kit escolar", "zapatos", "mochila", "cuaderno", "libros",
        "infraestructura educativa", "aula", "computadora", "laboratorio",
        "biblioteca", "cursos", "talleres educativos", "ninos", "jovenes",
        "estudiantes", "bachillerato", "educacion basica", "inscripcion",
        "matricula", "docente", "catedratico",
        "profesor", "profesora", "director", "directora",
        "jardin infantil", "kinder", "preescolar",
        "primaria", "secundaria", "media", "tecnico",
        "aprendizaje", "educativo", "educativa", "escolar",
        "beca", "paseo escolar", "excursion",
        "computadoras", "tablets", "clases virtuales",
    ],
    "movilidad": [
        "trafico", "transito", "transporte",
        "carro", "carros", "vehiculo", "bus", "buses", "ruta",
        "parada", "semaforo", "embotellamiento", "congestion",
        "via", "carretera", "taxi", "motocicleta", "bicicleta",
        "ciclovia", "estacionamiento", "parqueo", "peatonal",
        "peaton", "senalizacion", "senal de transito", "transporte publico",
        "mototaxi", "moto", "cuadraciclo", "pickup", "camion",
        "microbus", "colectivo", "furgon",
        "terminal", "paradero", "desvio",
        "cierre de calle", "calle cerrada", "paso cerrado",
        "accidente de transito", "choque",
        "atropellado", "vuelco", "incidente vial", "transito vehicular",
        "trafico vehicular", "circulacion",
        "transporte gratuito", "ruta escolar",
    ],
    "corrupcion": [
        "corrupto", "corrupta", "corrupcion", "robo",
        "ladron", "ladrones", "mentira", "mentiras", "fraude",
        "desvio", "malversacion", "trafico de influencias", "cohecho",
        "soborno", "nepotismo", "impunidad", "encubrimiento", "desfalco",
        "mal gobierno", "autoritarismo", "dictadura", "represion",
        "oposicion", "tirania", "abusos", "abuso de poder",
        "favoritismo", "clientelismo", "prebenda", "prebendas",
        "enriquecimiento", "ilicito", "ilegal", "ilegales",
        "malversado", "malversar", "robar", "robado",
        "politiqueria", "partidario", "partidarismo",
        "compadrazgo", "amiguismo",
        "negocio turbio", "dinero sucio", "lavado", "testaferro",
        "sobrevalorado", "inflado", "cobro indebido",
        "se robaron", "se robo", "dinero publico",
    ],
    "medio_ambiente": [
        "contaminacion", "basura", "rio", "arbol",
        "verde", "ambiente", "ecologia",
        "reserva", "bosque", "playa", "contaminante", "reciclaje",
        "reciclar", "cambio climatico", "sostenible", "sostenibilidad",
        "areas verdes", "parque nacional", "naturaleza",
        "fauna", "flora", "cuenca", "quebrada", "mangle", "ecosistema",
        "reforestacion", "jornada de limpieza",
        "desechos solidos", "separacion de basura",
        "punto limpio", "vertedero", "relleno sanitario",
        "calentamiento global", "huella ecologica",
        "energia limpia", "energia solar", "paneles solares",
        "renovable", "sustentable",
        "parque ecologico", "jardin botanico", "jard\u00edn bot\u00e1nico",
        "vivero", "aguas residuales", "tratamiento de aguas",
        "humedal", "laguna", "lago", "volcan", "cerro",
        "montana", "senderismo", "aves", "pajaro", "pajaros",
        "arboles", "plantas", "plantar", "siembra",
    ],
    "transparencia": [
        "informacion", "transparente", "donde esta",
        "gasto", "gastos", "presupuesto", "informe", "rendicion",
        "cuenta publica", "transparencia", "acceso a la informacion",
        "rendicion de cuentas", "auditoria", "ley de acceso",
        "datos abiertos", "portal de transparencia", "licitacion",
        "contratacion", "obra publica", "inversion",
        "inversiones", "ejecucion",
        "presupuestado", "ejecutado", "partida", "asignacion",
        "fondos", "financiamiento", "finanzas",
        "declaracion", "patrimonio", "bienes",
        "municipalidad", "concejo", "concejal", "concejales",
        "sesion", "acta", "actas", "acuerdo", "acuerdos",
        "reglamento", "ordenanza", "articulo", "normativa",
        "gestion municipal", "plan de trabajo",
        "plan operativo", "memoria de labores", "logros",
        "cuanto costo", "cuanto gasto", "en que se gasto",
    ],
    "cultura": [
        "cultura", "evento", "festival", "desfile", "concierto",
        "presentacion", "artistico", "artistica", "musica",
        "baile", "tradicion", "folclor", "folklore",
        "fiestas patronales", "procesion", "feria", "exposicion",
        "museo", "teatro", "danza", "pintura", "artesania",
        "patrimonio", "cultural", "turismo", "turistica",
        "turistico", "atractivo", "paseo", "convivencia", "familiar",
        "celebracion", "aniversario", "conmemoracion",
        "homenaje", "reconocimiento", "inauguracion",
        "festividad", "festejo", "festejos",
        "alborada", "polvora", "cohetes", "juegos pirotecnicos",
        "pirotecnia", "comparsa", "carroza", "reinado", "reina",
        "coronacion", "noche cultural", "velada", "recital", "muestra",
        "gastronomia", "comida tipica",
        "pupusas", "tamales", "atol", "yuca",
        "feria patronal", "dia del municipio",
    ],
    "deportes": [
        "deporte", "deportivo", "deportiva", "futbol",
        "beisbol", "baloncesto", "basquetbol", "voleibol",
        "natacion", "atletismo", "ciclismo",
        "maraton", "caminata", "competencia", "torneo",
        "campeonato", "entrenamiento", "entrenar", "ejercicio",
        "actividad fisica", "saludable", "bienestar",
        "jovenes", "ninos", "skate", "patinaje",
        "fas", "equipo fas", "once lobos", "isidro metapan",
        "liga", "partido", "ganar", "gano", "perder", "perdio",
        "gol", "goleada", "victoria", "triunfo",
        "trotar", "correr", "nadar", "montanismo", "campismo",
        "ajedrez", "boxeo", "lucha", "karate", "taekwondo", "judo",
        "academia deportiva", "escuela deportiva",
        "polideportivo", "cancha sintetica",
        "deportista", "medalla", "trofeo", "logro deportivo",
        "olimpiadas", "juegos deportivos",
    ],
}

ZONA_KEYWORDS = {
    "Centro": [
        "centro de santa ana", "santa ana centro", "casco urbano",
        "calle principal centro", "parque libertad", "parque colon",
        "parque col\u00f3n", "plaza mayor", "palacio municipal",
        "catedral", "mercado central", "mercado municipal",
        "calle libertad", "avenida independencia",
        "1\u00aa calle poniente", "2\u00aa avenida sur",
        "barrio san lorenzo", "barrio santa cruz", "barrio el calvario",
        "barrio concepcion", "barrio concepci\u00f3n",
        "colonia las magnolias", "colonia san miguelito",
        "colonia belen", "colonia bel\u00e9n",
        "colonia centroamericana", "urbanizacion centro",
        "residencial centro", "colonias del centro",
    ],
    "Norte": [
        "sector norte", "zona norte", "norte de santa ana",
        "villa jardin", "urbanizacion norte",
        "barrio norte", "la china",
        "colonia san antonio", "colonia santa rosa",
        "colonia las flores", "colonia ferrocarril",
        "colonia san jose", "colonia san jos\u00e9",
        "colonia santa rosa de lima",
        "colonia los andes", "colonia altos del norte",
        "colonia santa elena",
        "residencial los pinos", "residencial jardines",
        "residencial villas del norte",
        "urbanizacion jardines de santa ana",
        "urbanizacion los pinos",
        "caserio el rodeo", "cant\u00f3n norte",
    ],
    "Sur": [
        "sector sur", "zona sur", "sur de santa ana",
        "colonia sur", "colonia santa lucia",
        "colonia las delicias", "colonia el progreso sur",
        "colonia las palmeras sur", "colonia belen sur",
        "colonia la libertad",
        "residencial la fontana", "urbanizacion santa lucia",
        "canton el mango", "canton las delicias",
        "canton el porvenir", "canton santa lucia",
        "caserio el sunzal",
    ],
    "Este": [
        "sector este", "zona este", "este de santa ana",
        "colonia santa rita", "colonia buenos aires",
        "colonia san carlos", "colonia lourdes",
        "colonia san luis", "colonia los angeles",
        "colonia los angeles", "colonia el progreso",
        "colonia las brisas", "colonia santa lucia este",
        "colonia el palomar",
        "urbanizacion la esperanza",
        "residencial la esperanza",
        "lotificacion la esperanza", "lotificacion el progreso",
        "canton el progreso", "canton la esperanza",
    ],
    "Oeste": [
        "sector oeste", "zona oeste", "oeste de santa ana",
        "colonia san juan", "colonia san cristobal",
        "colonia san crist\u00f3bal", "colonia santa marta",
        "colonia la joya", "colonia san jeronimo",
        "colonia san jer\u00f3nimo",
        "colonia el pais", "colonia metapan",
        "colonia texistepeque", "colonia candelaria",
        "residencial san cristobal",
        "urbanizacion oeste",
        "caserio la monta\u00f1ona", "caserio la montanona",
        "canton san cristobal", "canton san juan",
        "canton el congo",
    ],
}

EMERGENCY_KEYWORDS = [
    "emergencia", "urgente", "muerte", "muerto", "asesinato", "accidente",
    "desastre", "inundacion", "tormenta", "ayuda", "socorro", "peligro",
    "grave", "critico", "alerta", "robo a mano armada", "balacera",
    "derrumbe", "deslizamiento", "incendio",
]

# \u2500\u2500\u2500 Capa 3 \u00b7 Robustez del respaldo por palabras clave \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# Palabras \"ambiguas\": aparecen a menudo en dichos, bromas o lenguaje figurado y
# por si solas NO bastan para afirmar que el comentario trata de ese tema.
# Ejemplo: \"rio\" en el dicho burlon \"panchito el rio estaba\" no habla de medio
# ambiente. Cuando la UNICA senal de un tema es ambigua, se exige una segunda
# senal para asignarlo (ver detect_topics). Una palabra fuerte/especifica
# (cualquier otra) basta por si sola, como antes.
AMBIGUOUS_KEYWORDS = {
    "rio", "rios", "arbol", "arboles", "verde", "playa",
    "cerro", "montana", "lago", "laguna", "aves", "pajaro", "pajaros",
}

# Dichos / frases hechas locales (El Salvador) que NO hablan del tema literal.
# Si el comentario contiene uno de estos dichos, el respaldo por palabras clave
# NO le asigna tema (lo deja para que la IA lo marque como no_aplica).
#
# La lista combina una semilla base (hardcodeada) con las frases idiomaticas
# multi-palabra definidas en idioms_sv_global.json (raiz del repo), cargadas por
# src.analyzer.idioms_loader. Para agregar mas dichos, edita ese archivo JSON.
_DICHOS_BASE = [
    "panchito el rio estaba",
    "al que madruga dios lo ayuda",
    "camaron que se duerme se lo lleva la corriente",
    "el que nace para tamal",
    "mas vale pajaro en mano",
    "el que con ninos se acuesta",
    "arbol que nace torcido",
    "no hay mal que dure cien anos",
    "el que mucho abarca poco aprieta",
]


def _fusionar_dichos(*listas) -> List[str]:
    """Une varias listas de dichos evitando duplicados (sin distinguir
    mayusculas) y conservando el orden de aparicion."""
    vistos = set()
    salida: List[str] = []
    for lista in listas:
        for dicho in (lista or []):
            if not dicho:
                continue
            clave = dicho.strip().lower()
            if not clave or clave in vistos:
                continue
            vistos.add(clave)
            salida.append(dicho)
    return salida


# Carga defensiva: si idioms_sv_global.json falta o esta malformado, se conserva
# unicamente la lista base y el pipeline/CI siguen funcionando con normalidad.
try:
    from src.analyzer.idioms_loader import extraer_dichos as _extraer_dichos_idioms
    _DICHOS_IDIOMS = _extraer_dichos_idioms()
except Exception as _exc:  # pragma: no cover - nunca romper por carga de dichos
    logger.warning("No se pudieron cargar dichos de idioms_sv_global.json: %r", _exc)
    _DICHOS_IDIOMS = []

DICHOS_LOCALES = _fusionar_dichos(_DICHOS_BASE, _DICHOS_IDIOMS)

# Cuantas senales (palabras clave) se exigen para asignar un tema cuando NINGUNA
# de las coincidencias es una palabra clave fuerte (especifica). Configurable.
MIN_SENALES_KEYWORD = int(os.environ.get("TOPIC_KW_MIN_SENALES", "2"))


def _normalize(s: str) -> str:
    return unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode('ascii')

@functools.lru_cache(maxsize=1)
def _norm_topic_keywords():
    return {t: [_normalize(k) for k in kws] for t, kws in TOPIC_KEYWORDS.items()}

@functools.lru_cache(maxsize=1)
def _norm_zona_keywords():
    return {z: [_normalize(k) for k in kws] for z, kws in ZONA_KEYWORDS.items()}

@functools.lru_cache(maxsize=1)
def _norm_ambiguous():
    return {_normalize(k) for k in AMBIGUOUS_KEYWORDS}

@functools.lru_cache(maxsize=1)
def _norm_dichos():
    return [_normalize(d) for d in DICHOS_LOCALES]

def _matches_dicho(text_norm: str) -> bool:
    """True si el texto (normalizado) contiene algun dicho/frase hecha local."""
    return any(d and d in text_norm for d in _norm_dichos())

def _kw_match(kw_norm: str, text_norm: str) -> bool:
    # l\u00edmite de palabra + plural espa\u00f1ol opcional (escuela \u2192 escuelas, bache \u2192 baches)
    return re.search(r'\b' + re.escape(kw_norm) + r'(?:es|s)?\b', text_norm) is not None

APOYO_GENERICO = [
    "bendiciones", "dios lo bendiga", "dios le bendiga", "felicidades",
    "felicitaciones", "gracias alcalde", "adelante alcalde", "buen trabajo",
    "excelente trabajo", "siga adelante", "lo apoyo", "apoyamos", "amen",
]

_has_spacy = False
_nlp = None


def _init_spacy():
    global _has_spacy, _nlp
    if _has_spacy or _nlp is not None:
        return
    try:
        import spacy
        _nlp = spacy.load("es_core_news_sm")
        _has_spacy = True
    except Exception:
        logger.debug("spaCy es_core_news_sm not available")
        _has_spacy = False
        _nlp = None


def detect_topics(text: str) -> List[Tuple[str, float]]:
    if not text:
        return []
    text_norm = _normalize(text)
    # Capa 3: los dichos / frases hechas no representan un tema literal.
    if _matches_dicho(text_norm):
        return []
    ambiguous = _norm_ambiguous()
    topics_found = []
    for topic, keywords in _norm_topic_keywords().items():
        matched = [kw for kw in keywords if _kw_match(kw, text_norm)]
        if not matched:
            continue
        total = len(matched)
        fuertes = sum(1 for kw in matched if kw not in ambiguous)
        # Capa 3: se asigna el tema si hay al menos UNA senal fuerte (palabra
        # especifica) o, en su defecto, al menos MIN_SENALES_KEYWORD senales
        # (aunque todas sean ambiguas). Una sola palabra ambigua suelta NO basta.
        if fuertes >= 1 or total >= MIN_SENALES_KEYWORD:
            topics_found.append((topic, min(total / 3, 1.0)))
    topics_found.sort(key=lambda x: x[1], reverse=True)
    return topics_found[:3]


def get_main_topic(text: str) -> str:
    topics = detect_topics(text)
    if topics:
        return topics[0][0]
    text_norm = _normalize(text or "")
    # Capa 3: un dicho no es apoyo generico ni ningun tema.
    if _matches_dicho(text_norm):
        return ""
    if any(_kw_match(_normalize(g), text_norm) for g in APOYO_GENERICO):
        return "apoyo_generico"
    return ""


def detect_zona(text: str) -> str:
    if not text:
        return ""
    text_norm = _normalize(text)
    for zona, keywords in _norm_zona_keywords().items():
        if any(_kw_match(kw, text_norm) for kw in keywords):
            return zona
    return ""


def detect_zona_ner(text: str) -> List[str]:
    _init_spacy()
    if not _has_spacy or not text:
        return []

    try:
        doc = _nlp(text[:2000])
        gpes = [ent.text for ent in doc.ents if ent.label_ == "GPE" or ent.label_ == "LOC"]
        return list(set(gpes))
    except Exception:
        return []


def detect_emerging_topics(texts: List[str], n_topics: int = 6) -> Dict:
    try:
        from src.analyzer.latent_topics import extract_latent_topics
        return extract_latent_topics(texts, n_topics=n_topics)
    except Exception as e:
        logger.warning(f"LDA extraction failed: {e}")
        return {"topics": [], "error": str(e)}


def is_emergency(text: str) -> bool:
    if not text:
        return False

    text_norm = unicodedata.normalize('NFKD', text.lower()).encode('ascii', 'ignore').decode('ascii')
    for kw in EMERGENCY_KEYWORDS:
        kw_norm = unicodedata.normalize('NFKD', kw.lower()).encode('ascii', 'ignore').decode('ascii')
        if kw_norm in text_norm:
            return True
    return False


def extract_problematicas(text: str, sentiment: str) -> List[Dict]:
    if not text:
        return []

    text_lower = text.lower()
    problematicas = []

    topic = get_main_topic(text)
    zona = detect_zona(text)

    if topic:
        problematicas.append({
            "topic": topic,
            "zona": zona,
            "sentiment": sentiment,
            "text_preview": text[:100]
        })

    for kw in EMERGENCY_KEYWORDS:
        if kw in text_lower:
            problematicas.append({
                "topic": "emergencia",
                "keyword": kw,
                "zona": zona,
                "sentiment": sentiment,
                "text_preview": text[:100]
            })
            break

    return problematicas


class TopicDetector:
    def __init__(self):
        self.topic_keywords = TOPIC_KEYWORDS
        self.zona_keywords = ZONA_KEYWORDS
        self.emergency_keywords = EMERGENCY_KEYWORDS

    def analyze(self, text: str) -> Dict:
        topics = detect_topics(text)
        zona = detect_zona(text)
        emergency = is_emergency(text)
        main_topic = get_main_topic(text)

        return {
            "topics": topics,
            "main_topic": main_topic,
            "zona": zona,
            "is_emergency": emergency,
            "text_length": len(text) if text else 0
        }

    def batch_analyze(self, texts: List[str]) -> List[Dict]:
        return [self.analyze(t) for t in texts]
