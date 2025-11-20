import os
import json
import time
import re

from flask import Flask, request, jsonify

import joblib
from oauth2client.service_account import ServiceAccountCredentials
import gspread

from clean_text import clean_text  # Este sigue siendo un archivo aparte


# ============================================================
#  CONFIGURACIÓN GOOGLE SHEETS (TODO DENTRO DE main.py)
# ============================================================

SHEETS_SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# En Render debes tener la variable GOOGLE_CREDENTIALS con el JSON del service account
google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, SHEETS_SCOPE)
client = gspread.authorize(creds)

SHEET_NAME = "clientes_bot"  # Debe existir en tu Google Drive


def guardar_en_google_sheets(modo, name, city, budget, phone):
    """
    Guarda los datos del usuario en la hoja correspondiente:
      - invertir → hoja 'invertir'
      - aprender → hoja 'aprender'
    """
    try:
        sheet = client.open(SHEET_NAME).worksheet(
            "invertir" if modo == "invertir" else "aprender"
        )

        if modo == "aprender":
            row = [name, city, phone]
        else:
            row = [name, city, budget, phone]

        sheet.append_row(row)
        print("Datos guardados correctamente en Google Sheets:", row)

    except Exception as e:
        print("Error guardando en Google Sheets:", e)


# ============================================================
#  ESTADO DE USUARIOS (MULTI-USUARIO)
# ============================================================

# Diccionario: user_id -> estado
user_states = {}


def get_user_state(user_id):
    if user_id not in user_states:
        user_states[user_id] = {
            "name": None,
            "city": None,
            "budget": None,
            "phone": None,
            "modo": None,        # aprender o invertir
            "last_action": None,
            "confirming": None
        }
    return user_states[user_id]


def reset_user_state(user_id):
    if user_id in user_states:
        del user_states[user_id]


# ============================================================
#  EXTRACCIÓN DE NOMBRE
# ============================================================

def extract_name(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-zA-Záéíóúñ ]", "", text)

    match = re.search(r"(me llamo|mi nombre es|soy)\s+([a-zA-Záéíóúñ ]+)", text)
    if match:
        name = match.group(2).strip()
        parts = name.split()
        if 1 <= len(parts) <= 3:
            return name.title()
        return None

    parts = text.split()
    if 1 <= len(parts) <= 3:
        return text.title()

    return None


# ============================================================
#  EXTRACCIÓN DE CIUDAD (LISTA LARGA)
# ============================================================

def extract_city(text):
    text = text.lower()

    text = re.sub(
        r"(desde|soy de|estoy en|vivo en|la ciudad de|ciudad de|de|en)\s+",
        "",
        text,
    )

    text_norm = (
        text.replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
    )

    ciudades = [
        "Abriaquí", "Acacías", "Acandí", "Acevedo", "Achí", "Agrado",
        "Aguachica", "Aguada", "Aguadas", "Aguazul", "Agustín Codazzi",
        "Aipe", "Albania", "Albania (Caquetá)", "Albania (Santander)", "Albán",
        "Albán (Nariño)", "Alcalá", "Alejandría", "Algarrobo", "Algeciras", "Almaguer",
        "Almeida", "Alpujarra", "Altamira", "Alto Baudó", "Altos del Rosario", "Ambalema",
        "Anapoima", "Ancuya", "Andalucía", "Andes", "Angelópolis", "Angostura", "Anolaima",
        "Anorí", "Anserma", "Ansermanuevo", "Antioquia", "Antúquiz", "Anzá", "Apartadó",
        "Apía", "Aquitania", "Aracataca", "Aranzazu", "Aratoca", "Arauca", "Arauquita",
        "Arbeláez", "Arboleda", "Arboledas", "Arboletes", "Arboletes", "Arcabuco", "Arenal",
        "Argelia (Antioquia)", "Argelia (Cauca)", "Argelia (Valle)", "Ariguaní", "Arjona",
        "Armenia", "Armero Guayabal", "Arroyohondo", "Astrea", "Ataco", "Atrato", "Ayapel",
        "Bagadó", "Bahía Solano", "Bajo Baudó", "Balboa (Cauca)", "Balboa (Risaralda)",
        "Baranoa", "Baraya", "Barbacoas", "Barbosa", "Barbosa (Santander)", "Barichara",
        "Barranca de Upía", "Barrancabermeja", "Barrancas", "Barranco de Loba",
        "Barranquilla", "Becerril", "Belalcázar", "Bello", "Belmira", "Beltrán", "Belén",
        "Belén (Boyacá)", "Belén de Bajirá", "Belén de Umbría", "Belén de los Andaquíes",
        "Berbeo", "Betania", "Betéitiva", "Betulia (Antioquia)", "Betulia (Santander)",
        "Bituima", "Boavita", "Bochalema", "Bogotá", "Bojacá", "Bojayá", "Bolívar (Cauca)",
        "Bolívar (Santander)", "Bolívar (Valle)", "Bosconia", "Boyacá", "Briceño (Antioquia)",
        "Briceño (Boyacá)", "Briceño (Cundinamarca)", "Bucaramanga", "Bucarasica",
        "Buenaventura", "Buenos Aires", "Buenavista (Boyacá)", "Buenavista (Córdoba)",
        "Buenavista (Quindío)", "Buenavista (Sucre)", "Bugalagrande", "Bugalagrande",
        "Bugalagrande", "Burítica", "Busbanzá", "Cabrera (Cundinamarca)", "Cabrera (Santander)",
        "Cabuyaro", "Cacahual", "Cachipay", "Caicedo", "Caicedonia", "Caimito", "Cajamarca",
        "Cajibío", "Cajicá", "Calamar (Bolívar)", "Calamar (Guaviare)", "Calarcá",
        "Caldas (Antioquia)", "Caldas (Boyacá)", "Caldas (Cundinamarca)", "Caldono",
        "California", "Calima Darién", "Caloto", "Campamento", "Campoalegre", "Campohermoso",
        "cali", "Canalete", "Candelaria (Atlántico)", "Candelaria (Valle)", "Cantagallo",
        "Cantón de San Pablo", "Caparrapí", "Capitanejo", "Cáqueza", "Caracolí", "Caramanta",
        "Carcasí", "Carepa", "Carmen de Apicalá", "Carmen de Carupa", "Carmen de Viboral",
        "Carmen del Darién", "Carolina", "Cartagena de Indias", "Cartago", "Carurú", "Casabianca",
        "Castilla la Nueva", "Caucasia", "Cañasgordas", "Cepitá", "Cereté", "Cerinza", "Cerrito",
        "Cerro San Antonio", "Cértegui", "Chachagüí", "Chaguaní", "Chalán", "Chaparral", "Charalá",
        "Charta", "Chía", "Chigorodó", "Chima (Santander)", "Chimá (Córdoba)", "Chimichagua",
        "Chinavita", "Chinchiná", "Chinú", "Chipaque", "Chipatá", "Chiquinquirá", "Chiriguaná",
        "Chiscas", "Chita", "Chitagá", "Chitaraque", "Chivatá", "Chivolo", "Choachí",
        "Chocontá", "Cicuco", "Ciénaga (Magdalena)", "Ciénaga de Oro", "Cimitarra", "cúcuta",
        # ... aquí puedes seguir pegando toda tu lista completa ...
        "Amazonas", "Antioquia", "Arauca", "Atlántico", "Bolívar", "Boyacá", "Caldas",
        "Caquetá", "Casanare", "Cauca", "Cesar", "Chocó", "Cundinamarca",
        "Córdoba", "Guainía", "Guaviare", "Huila", "La Guajira", "Magdalena",
        "Meta", "Nariño", "Norte de Santander", "Putumayo", "Quindío",
        "Risaralda", "San Andrés, Providencia y Santa Catalina",
        "Santander", "Sucre", "Tolima", "Valle del Cauca", "Vaupés",
        "Vichada", "popayán"
    ]

    ciudades_normalizadas = [
        c.lower()
         .replace("á", "a")
         .replace("é", "e")
         .replace("í", "i")
         .replace("ó", "o")
         .replace("ú", "u")
        for c in ciudades
    ]

    ciudades_map = dict(zip(ciudades_normalizadas, ciudades))

    for w in text_norm.split():
        if w in ciudades_map:
            return ciudades_map[w]

    if text_norm in ciudades_map:
        return ciudades_map[text_norm]

    return None


# ============================================================
#  EXTRACCIÓN DE PRESUPUESTO
# ============================================================

def extract_budget(text):
    text = text.lower().strip()
    text = text.replace(".", "").replace(",", "")

    match = re.search(r"(\d+)\s*millones?", text)
    if match:
        return int(match.group(1)) * 1_000_000

    nums = re.sub(r"\D", "", text)
    if nums.isdigit() and len(nums) >= 4:
        return int(nums)

    return None


# ============================================================
#  EXTRACCIÓN DE TELÉFONO
# ============================================================

def extract_phone(text):
    phone = re.sub(r"\D", "", text)
    return phone if 7 <= len(phone) <= 12 else None


# ============================================================
#  CARGA DE MODELOS
# ============================================================

intent_model = joblib.load("models/intent_model.joblib")
vectorizer = joblib.load("models/intent_vectorizer.joblib")

print("Cargando intents y respuestas...")
with open("intents_v2.json", "r", encoding="utf-8") as f:
    intents = json.load(f)["intents"]


# ============================================================
#  CONFIRMACIÓN Y ACCIONES (VERSIÓN MULTI-USUARIO)
# ============================================================

def confirm_value(state, key, value):
    state["confirming"] = key
    return f"¿Tu {key.title()} es {value}? (sí / no)"


def process_confirmation(state, msg):
    msg = msg.lower().strip()

    if msg in ["si", "sí", "claro", "correcto", "ok"]:
        field = state["confirming"]
        state["confirming"] = None

        # CONFIRMA NOMBRE
        if field == "nombre":
            state["last_action"] = "save_city"
            return f"Listo {state['name']} 😊 ¿De qué ciudad nos escribes?"

        # CONFIRMA CIUDAD
        if field == "ciudad":
            if state["modo"] == "invertir":
                state["last_action"] = "save_budget"
                return f"{state['name']}, ¿cuál es tu presupuesto para invertir?"
            else:
                state["last_action"] = "save_phone"
                return f"{state['name']}, ¿cuál es tu número de teléfono?"

        # CONFIRMA PRESUPUESTO
        if field == "presupuesto":
            state["last_action"] = "save_phone"
            return "Perfecto. ¿Cuál es tu número de teléfono?"

        # CONFIRMA TELÉFONO → GUARDAR EN SHEETS
        if field == "teléfono":
            guardar_en_google_sheets(
                modo=state["modo"],
                name=state["name"],
                city=state["city"],
                budget=state["budget"],
                phone=state["phone"]
            )
            state["last_action"] = None
            return (
                f"Perfecto {state['name']} 😊\n"
                f"Te registramos correctamente en *{state['modo']}*.\n"
                f"Un asesor se comunicará contigo al número {state['phone']} 📩"
            )

    # Si NO confirmó
    field = state["confirming"]
    state[field] = None
    state["confirming"] = None
    return f"Entendido, repíteme tu {field} por favor."


def handle_action(state, action, msg):

    if state["confirming"]:
        resp = process_confirmation(state, msg)
        if resp:
            return resp

    if action == "save_name":
        n = extract_name(msg)
        if n:
            state["name"] = n
            return confirm_value(state, "nombre", n)
        return "No entendí tu nombre, ¿puedes repetirlo?"

    if action == "save_city":
        c = extract_city(msg)
        if c:
            state["city"] = c
            return confirm_value(state, "ciudad", c)
        return "No pude identificar la ciudad 😕 ¿Puedes escribirla de nuevo?"

    if action == "save_budget":
        b = extract_budget(msg)
        if b:
            state["budget"] = b
            return confirm_value(state, "presupuesto", f"${b:,}")
        return "No entendí tu presupuesto. Escríbelo en números o con puntos."

    if action == "save_phone":
        p = extract_phone(msg)
        if p:
            state["phone"] = p
            return confirm_value(state, "teléfono", p)
        return "Ese número no parece válido, escríbelo nuevamente."

    return None


# ============================================================
#  RESPUESTA PRINCIPAL DEL CHATBOT (multi-usuario)
# ============================================================

def chatbot_answer(user_id, msg):
    state = get_user_state(user_id)

    # DETECTAR APRENDER / INVERTIR
    m = msg.lower().strip()
    if state["modo"] is None:
        if "aprender" in m:
            state["modo"] = "aprender"
            state["last_action"] = "save_name"
            return "Perfecto 🤓 Empecemos. ¿Cuál es tu nombre completo?"

        if "invertir" in m:
            state["modo"] = "invertir"
            state["last_action"] = "save_name"
            return "Excelente 💼 Empecemos. ¿Cuál es tu nombre completo?"

        return "¿Deseas *aprender* o deseas *invertir*? 🙌"

    if "asesor" in msg.lower():
        return "Aquí tienes contacto directo 👇\nhttps://wa.me/573160422795"

    if state["confirming"]:
        resp = process_confirmation(state, msg)
        if resp:
            return resp

    if state["last_action"]:
        forced = handle_action(state, state["last_action"], msg)
        if forced:
            return forced

    cleaned = clean_text(msg)
    intent = intent_model.predict(vectorizer.transform([cleaned]))[0]

    for i in intents:
        if i["tag"] == intent:
            state["last_action"] = i.get("next_action")
            resp = i["responses"][0]

            if "{name}" in resp and state["name"]:
                resp = resp.replace("{name}", state["name"])

            if "{city}" in resp and state["city"]:
                resp = resp.replace("{city}", state["city"])

            if "{budget}" in resp and state["budget"]:
                resp = resp.replace("{budget}", f"${state['budget']:,}")

            if "{phone}" in resp and state["phone"]:
                resp = resp.replace("{phone}", state["phone"])

            return resp

    # Ya no hay semántica, si no encuentra intent:
    return "No entendí muy bien, ¿podrías repetirlo?"


# ============================================================
#  FLASK PARA RENDER / MANYCHAT / IG
# ============================================================

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "message": "Bot funcionando en Render"}), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)

        # Intentamos diferentes campos posibles
        user_id = (
            str(data.get("user_id"))
            or str(data.get("sender_id", "anon"))
        )
        msg = (
            data.get("message")
            or data.get("comment")
            or data.get("text")
            or ""
        )

        if not msg:
            return jsonify({"error": "Falta el campo message/comment/text"}), 400

        # Comando para reiniciar estado
        if msg.lower().strip() in ["reset", "reiniciar", "empezar de nuevo"]:
            reset_user_state(user_id)
            return jsonify({"respuesta": "Listo, empecemos de cero 😊"}), 200

        respuesta = chatbot_answer(user_id, msg)

        # Adapta esto a lo que ManyChat espere en el bloque External Request
        return jsonify({
            "respuesta": respuesta
        }), 200

    except Exception as e:
        print("ERROR EN WEBHOOK:", e)
        return jsonify({"error": str(e)}), 500


# ============================================================
#  MODO CONSOLA (chat_console) CUANDO LO CORRES LOCAL
# ============================================================

if __name__ == "__main__":
    print("🤖 Chatbot en modo consola. Escribe 'salir' para terminar.")
    while True:
        msg = input("Tú: ").strip()
        if msg.lower() in ["salir", "exit"]:
            print("Bot: ¡Hasta luego! 👋")
            break
        resp = chatbot_answer("console", msg)
        print("Bot:", resp)
