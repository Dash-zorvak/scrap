import re
import logging
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)

TOPIC_KEYWORDS = {
    "obras_publicas": [
        "bache", "baches", "calle", "calles", "carpeta", "asfalto", "puente",
        "parque", "obra", "obras", "cordón", "summo", "vereda", "acera",
        "drenaje", "alcantarillado", "construcción", "reparación"
    ],
    "seguridad": [
        "robo", "robos", "asalto", "asaltos", "delincuencia", "delincuente",
        "seguridad", "policía", "crimen", "matar", "muerte", "asesinato",
        "pandilla", "extorsión", "amenaza", "violencia", "asociación"
    ],
    "servicios_publicos": [
        "agua", "luz", "electricidad", "basura", "recolección", "servicio",
        "corte", "servicios", "tubería", "alcantarillado", "desague",
        "potable", "cloro", "afectado", "sin agua", "sin luz"
    ],
    "empleo": [
        "trabajo", "empleo", "desempleo", "desempleado", "negocio", "negocios",
        "empresa", "empresas", "trabajador", "patrón", "formal", "informal",
        "empleo", "vacante", "contratar"
    ],
    "salud": [
        "hospital", "hospital", "clínica", "doctor", "doctora", "salud",
        "enfermedad", "enfermo", "consulta", "médico", "clínica", "centro de salud",
        "emergencia", "ambulancia", "vacuna"
    ],
    "educacion": [
        "escuela", "colegio", "educación", "educacion", "maestro", "maestra",
        "estudiante", "alumno", "clase", "colegio", "universidad", "becas",
        "material", "uniforme"
    ],
    "movilidad": [
        "tráfico", "trafico", "transito", "tránsito", "carro", "carros",
        "vehículo", "bus", "buses", "ruta", "parada", "semáforo", "semaforo",
        "embotellamiento", "congestion", "vía", "carretera"
    ],
    "corrupcion": [
        "corrupto", "corrupta", "corrupción", "robo", "ladrón", "ladrones",
        "mentira", "mentiras", "fraude", "desvío", "malversación", "pego",
        "tráfico de influencia", "cohecho"
    ],
    "medio_ambiente": [
        "contaminación", "basura", "río", "arbol", "árbol", "verde",
        "contaminacion", "ambiente", "ecología", "ecologia", "reserva",
        "bosque", "playa", "contaminante"
    ],
    "transparencia": [
        "información", "informacion", "transparente", "donde está", "gasto",
        "gastos", "presupuesto", "informe", "rendición", "cuenta", " pública"
    ],
}

ZONA_KEYWORDS = {
    "Norte": [
        "norte", "norte de santa ana", "villa jardín", "villa jardin",
        "urbanización norte", "barrio norte", "sector norte", "la china",
        "san antonio", "san josé", "santa rosa", "el rodeo", "la rivera"
    ],
    "Sur": [
        "sur", "sur de santa ana", "colonia sur", "sector sur", "la libertad",
        "el mango", "san marcos", "concepción", "el sunzal"
    ],
    "Centro": [
        "centro", "city center", "downtown", "casco urbano", "paracentral",
        "calle principal", "avenida central", "mercado", "plaza"
    ],
    "Este": [
        "este de santa ana", "sector este", "zona este", "al este",
        "el palomar", "santa lucia", "san rafael", "las brisas"
    ],
    "Oeste": [
        "oeste", "west", "sector oeste", "la costa", "el puerto", "punta",
        "santa mariña", "san juan", "los cobanos"
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