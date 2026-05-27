import re
import logging
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)

TOPIC_KEYWORDS = {
    "obras_publicas": [
        "bache", "baches", "calle", "calles", "carpeta", "asfalto", "puente",
        "parque", "obra", "obras", "cordón", "summo", "vereda", "acera",
        "drenaje", "alcantarillado", "construcción", "reparación", "pavimento",
        "pavimentación", "adoquín", "adoquinado", "infraestructura", "callejón",
        "bulevar", "carretera", "rotonda", "redondel", "pasarela", "andén",
        "mejoramiento vial", "vialidad", "construyendo", "reconstrucción",
        "remodelación", "embellecimiento", "jardín", "jardines", "área verde",
        "cancha", "canchas", "deportiva", "polideportivo", "pista", "estadio",
        "gimnasio", "parque infantil", "juegos", "mirador", "turístico"
    ],
    "seguridad": [
        "robo", "robos", "asalto", "asaltos", "delincuencia", "delincuente",
        "seguridad", "policía", "policia", "crimen", "matar", "muerte", "asesinato",
        "pandilla", "extorsión", "amenaza", "violencia", "asociación",
        "cámaras", "videovigilancia", "patrullaje", "seguridad ciudadana",
        "prevención", "iluminación", "alumbrado público", "denuncia",
        "protección", "resguardo", "militares", "ejército", "pnc", "fgr"
    ],
    "servicios_publicos": [
        "agua", "luz", "electricidad", "basura", "recolección", "servicio",
        "corte", "servicios", "tubería", "alcantarillado", "desague",
        "potable", "cloro", "afectado", "sin agua", "sin luz",
        "alumbrado", "alumbrado público", "fuga", "cañería", "tubería rota",
        "mantenimiento", "limpieza", "aseo", "mercado", "cementerio",
        "registro", "municipal", "tramite", "trámite", "permiso"
    ],
    "empleo": [
        "trabajo", "empleo", "desempleo", "desempleado", "negocio", "negocios",
        "empresa", "empresas", "trabajador", "patrón", "formal", "informal",
        "vacante", "contratar", "feria de empleo", "oportunidad laboral",
        "emprendedor", "emprendimiento", "microempresa", "mipyme",
        "capacitación", "capacitacion", "taller", "curso", "formación",
        "empleo joven", "bolsa de trabajo"
    ],
    "salud": [
        "hospital", "clínica", "clinica", "doctor", "doctora", "salud",
        "enfermedad", "enfermo", "consulta", "médico", "medico", "centro de salud",
        "emergencia", "ambulancia", "vacuna", "farmacia", "medicina",
        "campaña de salud", "jornada médica", "odontología", "optometría",
        "donación de sangre", "papanicolaou", "ultrasonido", "rayos x",
        "consulta externa", "atención médica", "bienestar", "nutrición"
    ],
    "educacion": [
        "escuela", "colegio", "educación", "educacion", "maestro", "maestra",
        "estudiante", "alumno", "clase", "universidad", "becas",
        "material", "uniforme", "instituto", "paquete escolar", "entrega de",
        "kit escolar", "zapatos", "mochila", "cuaderno", "libros",
        "infraestructura educativa", "aula", "computadora", "laboratorio",
        "biblioteca", "cursos", "talleres educativos", "niños", "jóvenes",
        "estudiantes", "bachillerato", "educación básica", "inscripción"
    ],
    "movilidad": [
        "tráfico", "trafico", "transito", "tránsito", "transporte",
        "carro", "carros", "vehículo", "vehiculo", "bus", "buses", "ruta",
        "parada", "semáforo", "semaforo", "embotellamiento", "congestión",
        "congestion", "vía", "carretera", "taxi", "motocicleta", "bicicleta",
        "ciclovía", "ciclovia", "estacionamiento", "parqueo", "peatonal",
        "peatón", "peaton", "señalización", "señal de tránsito", "transporte público"
    ],
    "corrupcion": [
        "corrupto", "corrupta", "corrupción", "corrupcion", "robo",
        "ladrón", "ladrones", "ladrona", "mentira", "mentiras", "fraude",
        "desvío", "malversación", "tráfico de influencias", "cohecho",
        "soborno", "nepotismo", "impunidad", "encubrimiento", "desfalco",
        "mal gobierno", "autoritarismo", "dictadura", "represión", "represivo",
        "oposición", "tiranía", "abusos", "abuso de poder"
    ],
    "medio_ambiente": [
        "contaminación", "contaminacion", "basura", "río", "rio",
        "árbol", "arbol", "verde", "ambiente", "ecología", "ecologia",
        "reserva", "bosque", "playa", "contaminante", "reciclaje",
        "reciclar", "cambio climático", "sostenible", "sostenibilidad",
        "áreas verdes", "areas verdes", "parque nacional", "naturaleza",
        "fauna", "flora", "cuenca", "quebrada", "mangle", "ecosistema",
        "reforestación", "reforestacion", "jornada de limpieza",
        "desechos sólidos", "desechos solidos", "separación de basura",
        "punto limpio", "vertedero", "relleno sanitario"
    ],
    "transparencia": [
        "información", "informacion", "transparente", "donde está",
        "gasto", "gastos", "presupuesto", "informe", "rendición",
        "rendicion", "cuenta pública", "transparencia", "acceso a la información",
        "rendición de cuentas", "auditoría", "auditoria", "ley de acceso",
        "datos abiertos", "portal de transparencia", "licitación",
        "contratación", "contratacion", "obra pública", "inversión"
    ],
    "cultura": [
        "cultura", "evento", "festival", "desfile", "concierto",
        "presentación", "artístico", "artistica", "música", "musica",
        "baile", "tradición", "tradicion", "folclor", "folklore",
        "fiestas patronales", "procesión", "feria", "exposición",
        "exposicion", "museo", "teatro", "danza", "pintura", "artesanía",
        "artesania", "patrimonio", "cultural", "turismo", "turística",
        "turístico", "atractivo", "paseo", "convivencia", "familiar"
    ],
    "deportes": [
        "deporte", "deportivo", "deportiva", "fútbol", "futbol",
        "béisbol", "beisbol", "baloncesto", "basquetbol", "voleybol",
        "voleibol", "natación", "natacion", "atletismo", "ciclismo",
        "maratón", "maraton", "caminata", "competencia", "torneo",
        "campeonato", "entrenamiento", "entrenar", "ejercicio",
        "actividad física", "actividad fisica", "saludable", "bienestar",
        "jóvenes", "jovenes", "niños", "skate", "patinaje"
    ],
}

ZONA_KEYWORDS = {
    "Centro": [
        "centro", "centro de santa ana", "casco urbano", "paracentral",
        "calle principal", "avenida central", "mercado", "plaza",
        "plaza mayor", "palacio municipal", "catedral", "parque libertad",
        "parque colón", "colonia centro", "barrio el centro",
        "calle libertad", "avenida independencia", "1ª calle poniente",
        "2ª avenida sur", "zona 1"
    ],
    "Norte": [
        "norte", "norte de santa ana", "villa jardín", "villa jardin",
        "urbanización norte", "barrio norte", "sector norte", "la china",
        "san antonio", "san josé", "santa rosa", "el rodeo", "la rivera",
        "colonia norte", "residencial norte", "las flores", "santa rosa",
        "cantón norte", "caserío norte", "santa ana norte",
        "san sebastián", "san rafael norte", "ciudad real", "villa sol",
        "los pinos", "altos del norte"
    ],
    "Sur": [
        "sur", "sur de santa ana", "colonia sur", "sector sur", "la libertad",
        "el mango", "san marcos", "concepción", "el sunzal",
        "residencial sur", "colonia santa lucía", "colonia santa ana sur",
        "cantón sur", "el porvenir", "san isidro", "san miguel",
        "santa ana sur", "villa maría", "la playa", "playa", "costa",
        "cantón el mango", "san antonio sur", "las palmeras"
    ],
    "Este": [
        "este de santa ana", "sector este", "zona este", "al este",
        "el palomar", "santa lucia", "san rafael", "las brisas",
        "colonia este", "cantón este", "san josé este",
        "residencial este", "villa del este", "santa ana este",
        "los ángeles", "el progreso", "san luis", "la esperanza",
        "san carlos", "lourdes", "santa rita", "buenos aires"
    ],
    "Oeste": [
        "oeste", "oeste de santa ana", "sector oeste", "zona oeste",
        "la costa", "san juan", "los cobanos",
        "colonia oeste", "cantón oeste", "residencial oeste",
        "villa oeste", "santa ana oeste", "san cristóbal",
        "santa marta", "el congo", "san jerónimo", "la montañona",
        "metapán", "texistepeque", "candelaria", "coatepeque",
        "el país", "san isidro oeste", "la joya"
    ],
}

EMERGENCY_KEYWORDS = [
    "emergencia", "urgente", "muerte", "muerto", "asesinato", "accidente",
    "desastre", "inundación", "tormenta", "ayuda", "socorro", "peligro",
    "grave", "crítico", "alerta", "robo a mano armada", "balacera"
]


def detect_topics(text: str) -> List[Tuple[str, float]]:
    if not text:
        return []
    
    text_lower = text.lower()
    topics_found = []
    
    for topic, keywords in TOPIC_KEYWORDS.items():
        matches = 0
        for kw in keywords:
            if kw in text_lower:
                matches += 1
        
        if matches > 0:
            confidence = min(matches / 3, 1.0)
            topics_found.append((topic, confidence))
    
    topics_found.sort(key=lambda x: x[1], reverse=True)
    return topics_found[:3]


def get_main_topic(text: str) -> str:
    topics = detect_topics(text)
    if topics:
        return topics[0][0]
    return ""


def detect_zona(text: str) -> str:
    if not text:
        return ""
    
    text_lower = text.lower()
    
    for zona, keywords in ZONA_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return zona
    
    return ""


def is_emergency(text: str) -> bool:
    if not text:
        return False
    
    text_lower = text.lower()
    for kw in EMERGENCY_KEYWORDS:
        if kw in text_lower:
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