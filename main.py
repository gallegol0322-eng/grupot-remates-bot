from flask import Flask, request, jsonify
import json
import torch
import joblib
import re
from clean_text import clean_text
from sentence_transformers import SentenceTransformer
from google_sheets import guardar_en_google_sheets  # <- usa tu módulo de Sheets

app = Flask(__name__)

# -----------------------------
# ESTADO ÚNICO DEL USUARIO
# (para pruebas; en producción idealmente por user_id)
# -----------------------------
user_states = {}

def get_state(uid):
    if uid not in user_states:
        user_states[uid] = {
            "name": None,
            "city": None,
            "budget": None,
            "phone": None,
            "modo": None,
            "last_action": None,
            "confirming": None
        }
    return user_states[uid]

def reset_state(uid):
    if uid in user_states:
        del user_states[uid]


# -----------------------------
# EXTRACCIÓN DE NOMBRE
# -----------------------------
def extract_name(text: str):
    text = text.lower().strip()
    text = re.sub(r"[^a-zA-Záéíóúñ ]", "", text)

    # Frases como "me llamo", "mi nombre es", "soy"
    match = re.search(r"(me llamo|mi nombre es|soy)\s+([a-zA-Záéíóúñ ]+)", text)
    if match:
        name = match.group(2).strip()
        if 1 <= len(name.split()) <= 3:
            return name.title()

    # Si solo manda 1 a 3 palabras, asumimos que es el nombre
    if 1 <= len(text.split()) <= 3:
        return text.title()

    return None

# -----------------------------
# EXTRACCIÓN DE CIUDAD
# (usa tu lista tal cual, pero si no la encuentra devuelve None)
# -----------------------------
def extract_city(text: str):
    text = text.lower().strip()
    text = re.sub(r"(desde|soy de|estoy en|vivo en|ciudad de|de|en)\s+", "", text)

    norm = (
        text.replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
    )

    ciudades = [
        "Abriaquí","Acacías","Acandí","Acevedo","Achí","Agrado",
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
        "Carmen del Darién","Carolina","Cartagena de Indias","Cartago","Carurú","Casabianca",
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
        "Sucre","Tolima","Valle del Cauca","Vaupés","Vichada"
    ]

    ciudades_norm = [
        c.lower()
         .replace("á", "a")
         .replace("é", "e")
         .replace("í", "i")
         .replace("ó", "o")
         .replace("ú", "u")
        for c in ciudades
    ]
    mapa = dict(zip(ciudades_norm, ciudades))

    # Primero probamos palabra por palabra
    for w in norm.split():
        if w in mapa:
            return mapa[w]

    # Luego probamos la frase completa
    return mapa.get(norm)

# -----------------------------
# EXTRACCIÓN PRESUPUESTO
# -----------------------------
def extract_budget(text: str):
    text = text.lower().replace(".", "").replace(",", "").strip()

    # "5 millones" -> 5000000
    match = re.search(r"(\d+)\s*millones?", text)
    if match:
        return int(match.group(1)) * 1_000_000

    # Si solo manda números largos
    nums = re.sub(r"\D", "", text)
    if nums.isdigit() and len(nums) >= 4:
        return int(nums)

    return None

# -----------------------------
# EXTRACCIÓN TELÉFONO
# -----------------------------
def extract_phone(text: str):
    phone = re.sub(r"\D", "", text)
    if 7 <= len(phone) <= 12:
        return phone
    return None

# -----------------------------
# MODELOS
# -----------------------------
intent_model = joblib.load("models/intent_model.joblib")
vectorizer = joblib.load("models/intent_vectorizer.joblib")

emb = torch.load("semantic_embeddings.pt")
model_sem = SentenceTransformer("all-MiniLM-L6-v2")

with open("intents_v2.json", "r", encoding="utf-8") as f:
    intents = json.load(f)["intents"]

# -----------------------------
# BÚSQUEDA SEMÁNTICA
# -----------------------------
def find_semantic(text: str):
    q = model_sem.encode(text, convert_to_tensor=True)
    scores = torch.matmul(q, emb["sentence_embeddings"].T)
    idx = torch.argmax(scores).item()
    tag = emb["mapping"][idx]
    for intent in intents:
        if intent["tag"] == tag:
            return intent
    return None

# -----------------------------
# CONFIRMACIONES
# -----------------------------
def confirm_value(field: str, value):
    # field: "nombre", "ciudad", "presupuesto", "teléfono"
    user_state["confirming"] = field
    return f"¿Tu {field} es {value}? (sí / no)"

def process_confirmation(msg: str):
    msg = msg.lower().strip()
    field = user_state.get("confirming")

    # Si por alguna razón no hay campo en confirmación
    if not field:
        return "No entendí, repíteme por favor."

    # Respuesta afirmativa
    if msg in ["si", "sí", "claro", "correcto", "ok"]:
        user_state["confirming"] = None

        if field == "nombre":
            user_state["last_action"] = "save_city"
            return f"Listo {user_state['name']} 😊 ¿De qué ciudad nos escribes?"

        if field == "ciudad":
            if user_state["modo"] == "invertir":
                user_state["last_action"] = "save_budget"
                return (
                    f"{user_state['name']}, ¿cuál es tu presupuesto para invertir?\n"
                    "Ejemplos: *5 millones* o *5000000*"
                )
            else:
                user_state["last_action"] = "save_phone"
                return f"{user_state['name']}, ¿tu número de teléfono?"

        if field == "presupuesto":
            user_state["last_action"] = "save_phone"
            return (
                f"Excelente {user_state['name']} 💰\n"
                "Ahora dime tu número de WhatsApp para contactarte."
            )

        if field == "teléfono":
            # Guardar en Google Sheets
            guardar_en_google_sheets(
                modo=user_state["modo"],
                name=user_state["name"],
                city=user_state["city"],
                budget=user_state["budget"],
                phone=user_state["phone"],
            )
            return (
                f"Perfecto {user_state['name']} 😊\n"
                f"Registro completado.\n"
                f"Un asesor te contactará al {user_state['phone']} 📩"
            )

    # Respuesta negativa → volver a pedir el dato
    user_state[field] = None
    user_state["confirming"] = None
    return f"Ok, repíteme tu {field} por favor."

# -----------------------------
# MANEJO DE ETAPAS (name/city/budget/phone)
# -----------------------------
def handle_action(msg: str):
    # Si estamos confirmando un dato, se maneja ahí
    if user_state["confirming"]:
        return process_confirmation(msg)

    # NOMBRE
    if user_state["last_action"] == "save_name":
        n = extract_name(msg)
        if n:
            user_state["name"] = n
            return confirm_value("nombre", n)
        return "No entendí tu nombre 🙈 intentemos otra vez. Ej: *Me llamo Juan Pérez*"

    # CIUDAD
    if user_state["last_action"] == "save_city":
        c = extract_city(msg)
        if c:
            user_state["city"] = c
            return confirm_value("ciudad", c)
        return "No pude identificar la ciudad 🤔 escribe solo el nombre, por ejemplo: *Cali*"

    # PRESUPUESTO
    if user_state["last_action"] == "save_budget":
        b = extract_budget(msg)
        if b:
            user_state["budget"] = b
            return confirm_value("presupuesto", f"${b:,}")
        return "No entendí tu presupuesto. Ejemplos: *5 millones* o *5000000*"

    # TELÉFONO
    if user_state["last_action"] == "save_phone":
        p = extract_phone(msg)

        # Intento extra: por si IG esconde caracteres
        if not p:
            cleaned = re.sub(r"\D", "", msg)
            if cleaned.isdigit() and 7 <= len(cleaned) <= 12:
                p = cleaned

        if p:
            user_state["phone"] = p
            return confirm_value("teléfono", p)

        return "No pude leer tu número 📵 escríbelo así: *3141234567*"

    return None

# -----------------------------
# CHATBOT PRINCIPAL
# -----------------------------
def chatbot(msg: str):
    m = msg.lower().strip()

    # 💬 palabras mágicas para contactar asesor directo
    if "asesor" in m:
        return "Contacto directo 👇 https://wa.me/573160422795"

    # PRIMER PASO: aprender o invertir
    if user_state["modo"] is None:
        if "aprender" in m:
            user_state["modo"] = "aprender"
            user_state["last_action"] = "save_name"
            return "Perfecto 🤓 empecemos. ¿Cuál es tu nombre completo?"
        if "invertir" in m:
            user_state["modo"] = "invertir"
            user_state["last_action"] = "save_name"
            return "Excelente 💼 ¿Cuál es tu nombre completo?"
        return "¿Deseas *aprender* o *invertir*? 🤔"



    # Si estamos confirmando algo
    if user_state["confirming"]:
        return process_confirmation(msg)

    # Si tenemos una acción pendiente (nombre, ciudad, presupuesto, teléfono)
    if user_state["last_action"]:
        forced = handle_action(msg)
        if forced:
            return forced

    # CLASIFICACIÓN POR INTENTS
    cleaned = clean_text(msg)
    intent = intent_model.predict(vectorizer.transform([cleaned]))[0]

    for i in intents:
        if i["tag"] == intent:
            user_state["last_action"] = i.get("next_action")
            r = i["responses"][0]

            if "{name}" in r:
                r = r.replace("{name}", user_state["name"] or "")
            if "{city}" in r:
                r = r.replace("{city}", user_state["city"] or "")
            if "{budget}" in r:
                r = r.replace(
                    "{budget}",
                    f"${user_state['budget']:,}" if user_state["budget"] else "",
                )
            if "{phone}" in r:
                r = r.replace("{phone}", user_state["phone"] or "")

            return r

    # BÚSQUEDA SEMÁNTICA
    sem = find_semantic(msg)
    if sem:
        user_state["last_action"] = sem.get("next_action")
        return sem["responses"][0]

    return "No logré entenderte 😅 prueba con otras palabras o escribe *asesor*."

# -----------------------------
# ENDPOINTS FLASK
# -----------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    uid = str(data.get("user_id") or data.get("sender_id") or data.get("contact_id") or "unknown")
    msg = data.get("message") or data.get("text") or data.get("comment") or ""

    state = get_state(uid)  # <-- recupera o crea sesión del usuario

    respuesta = chatbot(msg, state)  # <-- ahora chatbot usa ese estado

    return jsonify({"respuesta": respuesta}), 200





if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


