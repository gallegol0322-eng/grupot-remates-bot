from flask import Flask, request, jsonify
import json
import torch
import joblib
import re
from clean_text import clean_text
from sentence_transformers import SentenceTransformer
from google_sheets import guardar_en_google_sheets
import os

app = Flask(__name__)



# ============================================================
# ESTADO DEL USUARIO (versión igual a chat_console)
# ============================================================

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


# ============================================================
# EXTRACCIÓN DE NOMBRE (igual que tu chat_console)
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
# EXTRACCIÓN DE CIUDAD (ELIMINADO → ahora devuelve siempre texto)
# ============================================================

def extract_city(text):
    text = text.strip().title()
    return text if len(text) > 1 else None


# ============================================================
# EXTRACCIÓN DE PRESUPUESTO
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
# EXTRACCIÓN DE TELÉFONO
# ============================================================

def extract_phone(text):
    phone = re.sub(r"\D", "", text)
    return phone if 7 <= len(phone) <= 12 else None


# ============================================================
# CARGA DE MODELOS
# ============================================================

intent_model = joblib.load("models/intent_model.joblib")
vectorizer = joblib.load("models/intent_vectorizer.joblib")

emb = torch.load("semantic_embeddings.pt")
model_sem = SentenceTransformer("all-MiniLM-L6-v2")

with open("intents_v2.json", "r", encoding="utf-8") as f:
    intents = json.load(f)["intents"]


# ============================================================
# SEMÁNTICA
# ============================================================

def find_semantic(text):
    q = model_sem.encode(text, convert_to_tensor=True)
    scores = torch.matmul(q, emb["sentence_embeddings"].T)
    idx = torch.argmax(scores).item()
    tag = emb["mapping"][idx]

    for intent in intents:
        if intent["tag"] == tag:
            return intent
    return None


# ============================================================
# CONFIRMACIONES
# ============================================================

def confirm_value(state, key, value):
    state["confirming"] = key
    return f"¿Tu {key.title()} es {value}? (sí / no)"

def process_confirmation(state, msg):
    msg = msg.lower().strip()

    if msg in ["si", "sí", "claro", "correcto", "ok"]:
        field = state["confirming"]
        state["confirming"] = None

        if field == "nombre":
            state["last_action"] = "save_city"
            return f"Listo {state['name']} 😊 ¿De qué ciudad nos escribes?"

        if field == "ciudad":
            if state["modo"] == "invertir":
                state["last_action"] = "save_budget"
                return f"{state['name']}, ¿cuál es tu presupuesto?"
            else:
                state["last_action"] = "save_phone"
                return f"{state['name']}, ¿cuál es tu número de teléfono?"

        if field == "presupuesto":
            state["last_action"] = "save_phone"
            return "Perfecto. ¿Cuál es tu número?"

        if field == "teléfono":
            guardar_en_google_sheets(
                modo=state["modo"],
                name=state["name"],
                city=state["city"],
                budget=state["budget"],
                phone=state["phone"]
            )
            return (
                f"Perfecto {state['name']} 😊\n"
                f"Te registramos correctamente.\n"
                f"Un asesor te contactará al {state['phone']} 📩"
            )

    field = state["confirming"]
    state[field] = None
    state["confirming"] = None
    return f"Entendido, repíteme tu {field} por favor."


# ============================================================
# ACCIONES
# ============================================================

def handle_action(state, action, msg):

    if state["confirming"]:
        return process_confirmation(state, msg)

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
        return "No entendí la ciudad, escríbela de nuevo."

    if action == "save_budget":
        b = extract_budget(msg)
        if b:
            state["budget"] = b
            return confirm_value(state, "presupuesto", f"${b:,}")
        return "No entendí tu presupuesto."

    if action == "save_phone":
        p = extract_phone(msg)
        if p:
            state["phone"] = p
            return confirm_value(state, "teléfono", p)
        return "Ese número no es válido."

    return None


# ============================================================
# CHATBOT PRINCIPAL (idéntico estilo a tu chat_console)
# ============================================================

def chatbot_answer(uid, msg):
    state = get_state(uid)
    m = msg.lower().strip()

    if m == "reset":
        reset_state(uid)
        return "Listo, empecemos de cero 😊"

    if state["modo"] is None:
        if "aprender" in m:
            state["modo"] = "aprender"
            state["last_action"] = "save_name"
            return "Perfecto 🤓 ¿Cuál es tu nombre completo?"

        if "invertir" in m:
            state["modo"] = "invertir"
            state["last_action"] = "save_name"
            return "Excelente 💼 ¿Cuál es tu nombre completo?"

        return "¿Deseas aprender o invertir? 🙌"

    if "asesor" in m:
        return "Aquí tienes contacto directo 👇\nhttps://wa.me/573160422795"

    if state["confirming"]:
        return process_confirmation(state, msg)

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

            # placeholders
            if "{name}" in resp and state["name"]:
                resp = resp.replace("{name}", state["name"])
            if "{city}" in resp and state["city"]:
                resp = resp.replace("{city}", state["city"])
            if "{budget}" in resp and state["budget"]:
                resp = resp.replace("{budget}", f"${state['budget']:,}")
            if "{phone}" in resp and state["phone"]:
                resp = resp.replace("{phone}", state["phone"])

            return resp

    sem = find_semantic(msg)
    if sem:
        state["last_action"] = sem.get("next_action")
        return sem["responses"][0]

    return "No entendí muy bien, ¿podrías repetirlo?"


# ============================================================
# FLASK ROUTES
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online"}), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    uid = str(data.get("user_id") or data.get("sender_id") or data.get("id") or "anon")
    msg = data.get("message") or data.get("text") or data.get("comment") or ""

    respuesta = chatbot_answer(uid, msg)

    return jsonify({"respuesta": respuesta}), 200


# ============================================================
# MODO CONSOLA LOCAL
# ============================================================

if __name__ == "__main__":
    print("Bot local:")
    while True:
        t = input("Tú: ")
        print("Bot:", chatbot_answer("console", t))




