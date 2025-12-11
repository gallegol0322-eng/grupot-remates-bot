from flask import Flask, request, jsonify
import json
import torch
import joblib
import re
from clean_text import clean_text
from sentence_transformers import SentenceTransformer
from google_sheets import guardar_en_google_sheets  # si no usarás Sheets, comenta esta línea


app = Flask(__name__)

# ==============================================
#    CONTROL DE ESTADO POR USUARIO
# ==============================================
user_states = {}

def get_state(uid):
    if uid not in user_states:
        user_states[uid] = {
            "name": None,
            "city": None,
            "phone": None,
            "modo": None,          # lo dejamos por compatibilidad, pero siempre será "invertir"
            "last_action": None,
            "confirming": None
        }
    return user_states[uid]


# ==============================================
#  📌  EXTRACCIÓN DE DATOS DEL USUARIO
# ==============================================

def extract_name(text):
    if not text:
        return None

    # Normalización inicial
    text = text.lower().strip()
    text = re.sub(r"[^a-záéíóúñ ]", "", text)

    # Buscar expresiones comunes
    match = re.search(r"(me llamo|mi nombre es|soy)\s+(.*)", text)
    if match:
        name = match.group(2).strip()
    else:
        # si no hay patrón, usar todo el texto
        name = text

    # separo por palabras
    parts = name.split()

    # si no hay partes válidas
    if not parts:
        return None

    # tomar solo el primer nombre
    primer_nombre = parts[0]

    # capitalizar bonito
    return primer_nombre.title()


def extract_city(text):
    text = text.lower().strip()
    text = re.sub(r"(desde|soy de|estoy en|vivo en|ciudad de|de|en)\s+", "", text)
    norm = (text.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u"))

    ciudades = ["Abriaquí","Acacías","Acandí","Acevedo","Achí","Agrado",
        "Aguachica","Aguada","Aguadas","Aguazul","Agustín Codazzi",
        "Aipe","Albania","Albania (Caquetá)","Albania (Santander)","Albán",
        "Albán (Nariño)","Alcalá","Alejandría","Algarrobo","Algeciras","Almaguer",
        "Almeida","Alpujarra","Altamira","Alto Baudó","Altos del Rosario","Ambalema",
        "Anapoima","Ancuya","Andalucía","Andes","Angelópolis","Angostura","Anolaima",
        "Anorí","Anserma","Ansermanuevo","Antioquia","Antúquiz","Anzá","Apartadó",
        "Apía","Aquitania","Aracataca","Aranzazu","Aratoca","Arauca","Arauquita",
        "Arbeláez","Arboleda","Arboledas","Arboletes","Arcabuco","Arenal",
        "Argelia (Antioquia)","Argelia (Cauca)","Argelia (Valle)","Ariguaní","Arjona",
        "Armenia","Armero Guayabal","Arroyohondo","Astrea","Ataco","Atrato","Ayapel",
        "Bagadó","Bahía Solano","Bajo Baudó","Balboa (Cauca)","Balboa (Risaralda)",
        "Baranoa","Baraya","Barbacoas","Barbosa","Barbosa (Santander)","Barichara",
        "Barranca de Upía","Barrancabermeja","Barrancas","Barranco de Loba",
        "Barranquilla","Becerril","Belalcázar","Bello","Belmira","Beltrán","Belén",
        "Belén (Boyacá)","Belén de Bajirá","Belén de Umbría","Belén de los Andaquíes",
        "Berbeo","Betania","Betéitiva","Betulia (Antioquia)","Betulia (Santander)",
        "Bituima","Boavita","Bochalema","Bogotá","Bojacá","Bojayá","Bolívar (Cauca)",
        "Bolívar (Santander)","Bolívar (Valle)","Bosconia","Boyacá","Briceño (Antioquia)",
        "Briceño (Boyacá)","Briceño (Cundinamarca)","Bucaramanga","Bucarasica",
        "Buenaventura","Buenos Aires","Buenavista (Boyacá)","Buenavista (Córdoba)",
        "Buenavista (Quindío)","Buenavista (Sucre)","Bugalagrande","Burítica","Busbanzá",
        "Cabrera (Cundinamarca)","Cabrera (Santander)","Cabuyaro","Cacahual","Cachipay",
        "Caicedo","Caicedonia","Caimito","Cajamarca","Cajibío","Cajicá",
        "Calamar (Bolívar)","Calamar (Guaviare)","Calarcá",
        "Caldas (Antioquia)","Caldas (Boyacá)","Caldas (Cundinamarca)","Caldono",
        "California","Calima Darién","Caloto","Campamento","Campoalegre","Campohermoso",
        "Cali","Canalete","Candelaria (Atlántico)","Candelaria (Valle)","Cantagallo",
        "Cantón de San Pablo","Caparrapí","Capitanejo","Cáqueza","Caracolí","Caramanta",
        "Carcasí","Carepa","Carmen de Apicalá","Carmen de Carupa","Carmen de Viboral",
        "Carmen del Darién","Carolina","Cartagena de Indias","cartagena","Cartago","Carurú","Casabianca",
        "Castilla la Nueva","Caucasia","Cañasgordas","Cepitá","Cereté","Cerinza","Cerrito",
        "Cerro San Antonio","Cértegui","Chachagüí","Chaguaní","Chalán","Chaparral","Charalá",
        "Charta","Chía","Chigorodó","Chima (Santander)","Chimá (Córdoba)","Chimichagua",
        "Chinavita","Chinchiná","Chinú","Chipaque","Chipatá","Chiquinquirá","Chiriguaná",
        "Chiscas","Chita","Chitagá","Chitaraque","Chivatá","Chivolo","Choachí",
        "Chocontá","Cicuco","Ciénaga (Magdalena)","Ciénaga de Oro","Cimitarra",
        "Cúcuta","Circasia","Cisneros","Clemencia","Cocorná","Coello","Cogua",
        "Colombia","Colón (Putumayo)","Colón (Nariño)","Coloso","Cómbita",
        "Concepción (Antioquia)","Concepción (Santander)","Concordia (Antioquia)",
        "Concordia (Magdalena)","Condoto","Confines","Consacá","Contadero",
        "Contratación","Convención","Copacabana","Coper","Cordobá","Corinto",
        "Coromoro","Corozal","Corrales","Cota","Cotorra","Covarachía","Coveñas",
        "Coyaima","Cravo Norte","Cuaspud","Cubarral","Cubará","Cucaita","Cucunubá",
        "Cucutilla","Cumaral","Cumaribo","Cumbal","Cumbitara","Cunday","Curillo",
        "Curití","Curumaní","Cáceres","Dabeiba","Dagua","Dibulla","Distracción",
        "Dolores","Don Matías","Dosquebradas","Duitama","Durania","Ebéjico","El Águila",
        "El Bagre","El Banco","El Cairo","El Calvario","El Carmen (Norte de Santander)",
        "El Carmen de Atrato","El Carmen de Bolívar","El Castillo","El Cerrito","El Charco",
        "El Cocuy","El Colegio","El Copey","El Doncello","El Dorado","El Dovio",
        "El Encanto","El Espino","El Guacamayo","El Guamo","El Litoral del San Juan",
        "El Molino","El Paso","El Paujil","El Peñol","El Peñón (Bolívar)","El Peñón (Santander)",
        "El Peñón (Cundinamarca)","El Piñón","El Playón","El Retorno","El Retiro","El Roble",
        "El Rosal","El Rosario","El Tablón de Gómez","El Tambo (Cauca)","El Tambo (Nariño)",
        "El Tarra","El Yopal","El Zulia","Encino","Enciso","Entrerríos","Envigado","Espinal",
        "Facatativá","Falan","Filadelfia","Filandia","Firavitoba","Flandes","Florencia","Floresta",
        "Florida","Floridablanca","Florián","Fonseca","Fortúl","Fosca","Fómeque","Francisco Pizarro",
        "Fredonia","Fresno","Frontino","Fuente de Oro","Fundación","Funes","Funza","Fusagasugá",
        "Gachalá","Gachancipá","Gachantivá","Gachetá","Galapa","Galeras","Gama","Gamarra",
        "Garagoa","Garzón","Gigante","Ginebra","Giraldo","Girardot","Girardota","Girón",
        "Granada (Antioquia)","Granada (Meta)","Granada (Cundinamarca)","Guaca","Guacamayas",
        "Guacarí","Guachetá","Guarne","Guasca","Guatapé","Guatavita","Guayabal de Síquima",
        "Guayatá","Guepsa","Hacarí","Heliconia","Hispania","Honda","Ibagué","Icononzo",
        "Ipiales","Istmina","Itagüí","Ituango","Jamundí","Jardín","Jenésano","Jericó",
        "La Calera","La Ceja","La Cruz","La Cumbre","La Dorada","La Estrella","La Jagua de Ibirico",
        "La Macarena","La Mesa","La Palma","La Paz (Cesar)","La Plata","La Vega (Cundinamarca)",
        "La Victoria (Valle)","La Virginia","Líbano","Lloró","Lorica","Los Patios","Luruaco",
        "Madrid","Magangué","Maicao","Malambo","Manizales","Manzanares","Margarita",
        "Marinilla","Mariquita","Marsella","Medellín","Melgar","Mercaderes","Mesetas",
        "Miranda","Mocoa","Mompox","Moniquirá","Monterrey","Montería","Montenegro",
        "Morales (Bolívar)","Mosquera (Cundinamarca)","Neiva","Ocaña","Palmira","Pamplona",
        "Pasto","Pereira","Piedecuesta","Pitalito","Popayán","Quibdó","Riohacha","Santa Marta",
        "Sincelejo","Soacha","Sogamoso","Tuluá","Tunja","Valledupar","Villavicencio","Yopal",
        "Amazonas","Antioquia","Arauca","Atlántico","Bolívar","Boyacá","Caldas","Caquetá",
        "Casanare","Cauca","Cesar","Chocó","Cundinamarca","Córdoba","Guainía","Guaviare",
        "Huila","La Guajira","Magdalena","Meta","Nariño","Norte de Santander","Putumayo",
        "Quindío","Risaralda","San Andrés, Providencia y Santa Catalina","Santander",
        "Sucre","Tolima","Valle del Cauca","Vaupés","Vichada","Buga", "Alcalá", "Andersen", "Buga", "Bugalagrande", "Bolívar", 
        "Buenaventura", "Cali", "Calima", "Candelaria", "Cartago", "Dagua", "El Águila", "El Cairo", 
        "El Cerrito", "El Dovio", "Florida", "Galeras", "Ginebra", "Guacarí", "Guachené", "Jamundí", 
        "La Cumbre", "La Unión", "La Victoria", "Obando", "Palmira", "Pradera", "Restrepo", "Riofrío", "Roldanillo",
        "San Jerónimo", "San Juan del Valle", "San Pedro", "Santa Bárbara", "Santa Cruz", "Sevilla", "Toro", 
        "Tuluá", "Ulloa", "Uncía", "Versalles", "Vijes"
    ] 

    ciudades_norm = [
        c.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
        for c in ciudades
    ]
    mapa = dict(zip(ciudades_norm, ciudades))

    for w in norm.split():
        if w in mapa:
            return mapa[w]
    return mapa.get(norm)


def extract_phone(text):
    if not text:
        return None
    
    # quitar todo lo que no sea número
    phone = re.sub(r"\D", "", text)
    if not phone:
        return None
        
    # quitar prefijo +57 o 57
    if phone.startswith("57"):
        phone = phone[2:]

    # si comienza con 3 y tiene 10 dígitos (cel colombiano)
    if len(phone) == 10 and phone.startswith("3"):
        return phone

    # si tiene 7 dígitos (línea fija)
    if len(phone) == 7:
        return phone

    # aceptar números largos internacionales 7 a 15
    if 7 <= len(phone) <= 15:
        return phone

    return None


# ==============================================
# MODELLO DE INTENTOS Y SEMÁNTICA
# ==============================================
intent_model = joblib.load("models/intent_model.joblib")
vectorizer = joblib.load("models/intent_vectorizer.joblib")

emb = torch.load("semantic_embeddings.pt")
model_sem = SentenceTransformer("all-MiniLM-L6-v2")

with open("intents_v2.json","r",encoding="utf-8") as f:
    intents = json.load(f)["intents"]


def find_semantic(text):
    q = model_sem.encode(text, convert_to_tensor=True)
    scores = torch.matmul(q, emb["sentence_embeddings"].T)
    idx = torch.argmax(scores).item()
    tag = emb["mapping"][idx]
    return next((i for i in intents if i["tag"] == tag), None)


# ==============================================
# CONFIRMACIÓN DE DATOS
# ==============================================
def confirm_value(field, value, state):
    state["confirming"] = field
    return f"¿Tu {field} es {value}? (sí / no)"

def process_confirmation(msg, state):
    msg = msg.lower().strip()
    field = state.get("confirming")

    if not field:
        return "No entendí, repite por favor."

    # Respuestas afirmativas
    afirm = ["si","sí","claro","correcto","ok","sisas","s"]

    # Respuesta negativa
    neg = ["no","nop","nel","nope","ño","n"]
    
    if msg in afirm: 
        state["confirming"] = None
        
        if field == "nombre":
            state["last_action"] = "save_city"
            return f"Genial {state['name']} 😊 ¿De qué ciudad nos escribes?"

        if field == "ciudad":
            state["last_action"] = "save_phone"
            return (
                f"{state['name']} regálame por favor tu número de teléfono "
                "seguido de tu primer nombre. Ejemplo: (Juan 3141234567)"
            )

        if field == "telefono":
            # Guardar en Google Sheets
            try:
                guardar_en_google_sheets(
                    modo=state["modo"],
                    name=state["name"],
                    city=state["city"],
                    phone=state["phone"]
                )
            except:
                pass

            state["last_action"] = None
            return "Perfecto ✔️ Registro guardado.\nUn asesor te contactará pronto 💌"

        return "Listo."
        
    if msg in neg: 
        state["confirming"] = None

        if field == "nombre":
            state["last_action"] = "save_name"
            return "Vale, dime de nuevo tu nombre completo 😊"

        if field == "ciudad":
            state["last_action"] = "save_city"
            return "Listo, escribe de nuevo tu ciudad."

        if field == "telefono":
            state["last_action"] = "save_phone"
            return "Ok, escríbeme de nuevo tu número de WhatsApp."

        return f"Ok, repíteme tu {field}."

    # si responde algo raro
    return "¿Sí o no?"
  

# ==============================================
# MANEJO POR ETAPAS NOMBRE / CIUDAD / TELÉFONO
# ==============================================
def handle_action(msg, state):

    # ===============================
    #  INTELIGENCIA DE CORRECCIÓN DE RUTA
    # ===============================

    # 1. ¿El usuario escribió un nombre aunque no se lo estemos pidiendo?
    nombre = extract_name(msg)
    if nombre and nombre != state.get("name"):
        state["name"] = nombre
        state["last_action"] = "save_city"
        state["confirming"] = "nombre"
        return f"¿Tu nombre es {nombre}? (sí / no)"

    # 2. ¿El mensaje contiene una ciudad?
    ciudad = extract_city(msg)
    if ciudad and ciudad != state.get("city"):
        state["city"] = ciudad
        state["last_action"] = "save_phone"
        state["confirming"] = "ciudad"
        return f"¿Tu ciudad es {ciudad}? (sí / no)"

    # 3. ¿El usuario dio un teléfono aunque estemos en otra fase?
    telefono = extract_phone(msg)
    if telefono and telefono != state.get("phone"):
        state["phone"] = telefono
        state["confirming"] = "telefono"
        return f"¿Tu teléfono es {telefono}? (sí / no)"


    if state["confirming"]:
        return process_confirmation(msg, state)
        
    if state["last_action"] == "save_name":
        n = extract_name(msg)
        
        if n: 
            state["name"] = n 
            state["confirming"] = "nombre"
            return f"¿Tu nombre es {n}? (sí / no)"
            
        return "No entendí tu nombre 🙈"

    if state["last_action"] == "save_city":
        c = extract_city(msg)
        
        if c: 
            state["city"] = c
            state["confirming"] = "ciudad"
            return f"¿Tu ciudad es {c}? (sí / no)"
            
        return "No reconocí la ciudad 🤔 intenta escribiendo solo tu ciudad"

    if state["last_action"] == "save_phone":
        p = extract_phone(msg)

        # Si pude leer el número → confirmar
        if p:
            state["phone"] = p
            state["confirming"] = "telefono"
            return f"¿Tu teléfono es {p}? (sí / no)"

        # Si no entendí el número → pedir de nuevo
        return (
            "No logro leer tu número 📵\n"
            "Escríbelo usando *guiones, espacios o puntos*, por ej:\n\n"
            "📌 314 523 2968\n"
            "📌 314-523-2968\n"
            "📌 314.523.2968\n"
            "📌 +57 314 523 2968\n"
        )

    return None


# ==============================================
#  ⚡ CHATBOT PRINCIPAL (MODO SOLO INVERTIR)
# ==============================================
def chatbot(msg, state):
    m = msg.lower().strip()

    # Bloquear mensajes duplicados de ManyChat
    if state.get("last_msg") == msg:
       return None  # NO respondas si ya recibimos lo mismo
    state["last_msg"] = msg


    # Reset de conversación
    if m in ["cancel", "cancelar", "cance", "cancela", "reset"]:
       state.update({
         "name": None,
         "city": None,
         "phone": None,
         "modo": None,
         "last_action": None,
         "confirming": None
    })
    return "Proceso cancelado. Empecemos de nuevo 😊 ¿Cuál es tu nombre?"


    # Atajo para hablar con asesor directamente
    if "asesor" in m or "asesoría" in m or "asesoria" in m:
        return "Contacto directo 👇 https://wa.me/573160422795"

    # Protección por si ManyChat te manda "aprender" por error
    if "aprender" in m:
        return "Este canal es solo para inversión. Un asesor te apoyará con el tema de aprendizaje."

    # -----------------------
    #  MODO UNIFICADO: SOLO INVERTIR
    # -----------------------
    if state["modo"] is None:
        state["modo"] = "invertir"
        if state["last_action"] is None:   # <-- evita repetición
           state["last_action"] = "save_name"
           return "Perfecto 💼 ¿Cuál es tu nombre completo?"


    # Si está confirmando algo
    if state["confirming"]:
        return process_confirmation(msg, state)

    # Si está en alguna etapa del flujo (nombre/ciudad/teléfono)
    if state["last_action"]:
        forced = handle_action(msg, state)
        if forced:
            return forced

    # Si no está en flujo forzado, usamos intents / semántica para respuestas normales
    cleaned = clean_text(msg)
    intent = intent_model.predict(vectorizer.transform([cleaned]))[0]

    for i in intents:
        if i["tag"] == intent:
            state["last_action"] = i.get("next_action")
            r = i["responses"][0]
            return (
                r.replace("{name}", state["name"] or "")
                 .replace("{city}", state["city"] or "")
                 .replace("{phone}", state["phone"] or "")
            )

    sem = find_semantic(msg)
    if sem:
        state["last_action"] = sem.get("next_action")
        return sem["responses"][0]

    return "No logré entenderte 😅 prueba con otras palabras o escribe *asesor*."


# ==============================================
# ⚡ ENDPOINT PARA MANYCHAT / INSTAGRAM
# ==============================================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    uid = str(
        data.get("user_id") or 
        data.get("sender_id") or 
        data.get("contact_id") or 
        data.get("profile_id") or 
        "anon"
    )

    # ManyChat puede mandar triggers personalizados
    trigger = data.get("trigger")

    # Activar flujo SOLO cuando ManyChat lo indique
    if trigger == "start_invertir":
        state = get_state(uid)
        state.update({
            "name": None,
            "city": None,
            "phone": None,
            "modo": "invertir",
            "last_action": "save_name",
            "confirming": None
        })
        return jsonify({"respuesta": "Perfecto 💼 ¿Cuál es tu nombre completo?"})

    # Si no hay trigger, seguimos flujo normal
    msg = data.get("message") or data.get("text") or data.get("comment") or ""
    if not msg:
        phone_field = data.get("phone")
        msg = str(phone_field) if phone_field else ""

    state = get_state(uid)
    respuesta = chatbot(msg, state)

    return jsonify({"respuesta": respuesta}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)





