import json
import torch
import joblib
import re
from clean_text import clean_text
from sentence_transformers import SentenceTransformer
from google_sheets import guardar_en_google_sheets

# -----------------------------
# ESTADO DEL USUARIO
# -----------------------------
user_state = {
    "name": None,
    "city": None,
    "budget": None,
    "phone": None,
    "modo": None,
    "last_action": None,
    "confirming": None
}

# -----------------------------
# EXTRACCIÓN DE NOMBRE
# -----------------------------
def extract_name(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-zA-Záéíóúñ ]", "", text)

    match = re.search(r"(me llamo|mi nombre es|soy)\s+([a-zA-Záéíóúñ ]+)", text)
    if match:
        name = match.group(2).strip()
        if 1 <= len(name.split()) <= 3:
            return name.title()
        return None

    parts = text.split()
    if 1 <= len(parts) <= 3:
        return text.title()

    return None


# -----------------------------
# EXTRACCIÓN DE CIUDAD
# (SIN USAR LISTA — ACEPTA CUALQUIER CIUDAD)
# -----------------------------
def extract_city(text):
    text = text.lower().strip()

    text = re.sub(
        r"(desde|soy de|estoy en|vivo en|la ciudad de|ciudad de|de|en)\s+",
        "",
        text
    )

    text = re.sub(r"[^a-zA-Záéíóúñ ]", "", text).strip()

    # Aceptar ciudades de 1 a 4 palabras
    if 1 <= len(text.split()) <= 4:
        return text.title()

    return None


# -----------------------------
# EXTRACCIÓN DE PRESUPUESTO
# -----------------------------
def extract_budget(text):
    text = text.lower().replace(".", "").replace(",", "").strip()

    match = re.search(r"(\d+)\s*millones?", text)
    if match:
        return int(match.group(1)) * 1_000_000

    numbers = re.sub(r"\D", "", text)
    if numbers.isdigit() and len(numbers) >= 4:
        return int(numbers)

    return None


# -----------------------------
# EXTRACCIÓN DE TELÉFONO
# -----------------------------
def extract_phone(text):
    phone = re.sub(r"\D", "", text)
    return phone if 7 <= len(phone) <= 12 else None


# -----------------------------
# CARGA DE MODELOS
# -----------------------------
intent_model = joblib.load("models/intent_model.joblib")
vectorizer = joblib.load("models/intent_vectorizer.joblib")

print("Cargando modelos...")
emb = torch.load("semantic_embeddings.pt")
model_sem = SentenceTransformer("all-MiniLM-L6-v2")

with open("intents_v2.json", "r", encoding="utf-8") as f:
    intents = json.load(f)["intents"]


# -----------------------------
# SEMÁNTICA
# -----------------------------
def find_semantic(text):
    q = model_sem.encode(text, convert_to_tensor=True)
    scores = torch.matmul(q, emb["sentence_embeddings"].T)
    idx = torch.argmax(scores).item()
    tag = emb["mapping"][idx]

    for intent in intents:
        if intent["tag"] == tag:
            return intent

    return None


# -----------------------------
# CONFIRMACIÓN
# -----------------------------
def confirm_value(key, value):
    user_state["confirming"] = key
    return f"¿Tu {key.title()} es {value}? (sí / no)"


def process_confirmation(msg):
    msg = msg.lower().strip()

    if msg in ["si", "sí", "claro", "correcto", "ok"]:
        field = user_state["confirming"]
        user_state["confirming"] = None

        # CONFIRMAR NOMBRE
        if field == "nombre":
            user_state["last_action"] = "save_city"
            return f"Listo {user_state['name']} 😊 ¿De qué ciudad nos escribes?"

        # CONFIRMAR CIUDAD
        if field == "ciudad":
            if user_state["modo"] == "invertir":
                user_state["last_action"] = "save_budget"
                return f"{user_state['name']}, ¿cuál es tu presupuesto para invertir?"
            else:
                user_state["last_action"] = "save_phone"
                return f"{user_state['name']}, ¿cuál es tu número de teléfono?"

        # CONFIRMAR PRESUPUESTO
        if field == "presupuesto":
            user_state["last_action"] = "save_phone"
            return "Perfecto. ¿Cuál es tu número de teléfono?"

        # CONFIRMAR TELÉFONO — SE GUARDA EN GOOGLE SHEETS
        if field == "teléfono":
            guardar_en_google_sheets(
                modo=user_state["modo"],
                name=user_state["name"],
                city=user_state["city"],
                budget=user_state["budget"],
                phone=user_state["phone"]
            )
            user_state["last_action"] = None
            return (
                f"Perfecto {user_state['name']} 😊\n"
                f"Te registramos correctamente en *{user_state['modo']}*.\n"
                f"Un asesor te contactará al número {user_state['phone']} 📩"
            )

    # SI DICE "NO"
    field = user_state["confirming"]
    user_state[field] = None
    user_state["confirming"] = None
    return f"Entendido, repíteme tu {field} por favor."


# -----------------------------
# ACCIONES
# -----------------------------
def handle_action(action, msg):

    if user_state["confirming"]:
        return process_confirmation(msg)

    if action == "save_name":
        n = extract_name(msg)
        if n:
            user_state["name"] = n
            return confirm_value("nombre", n)
        return "No entendí tu nombre, ¿puedes repetirlo?"

    if action == "save_city":
        c = extract_city(msg)
        if c:
            user_state["city"] = c
            return confirm_value("ciudad", c)
        return "No pude identificar la ciudad 😕 ¿Puedes escribirla de nuevo?"

    if action == "save_budget":
        b = extract_budget(msg)
        if b:
            user_state["budget"] = b
            return confirm_value("presupuesto", f"${b:,}")
        return "No entendí tu presupuesto. Escríbelo en números."

    if action == "save_phone":
        p = extract_phone(msg)
        if p:
            user_state["phone"] = p
            return confirm_value("teléfono", p)
        return "Ese número no parece válido."

    return None


# -----------------------------
# RESPUESTA PRINCIPAL
# -----------------------------
def chatbot_answer(msg):

    m = msg.lower().strip()

    if user_state["modo"] is None:
        if "aprender" in m:
            user_state["modo"] = "aprender"
            user_state["last_action"] = "save_name"
            return "Perfecto 🤓 Empecemos. ¿Cuál es tu nombre completo?"

        if "invertir" in m:
            user_state["modo"] = "invertir"
            user_state["last_action"] = "save_name"
            return "Excelente 💼 Empecemos. ¿Cuál es tu nombre completo?"

        return "¿Deseas *aprender* o *invertir*? 🙌"

    if "asesor" in m:
        return "Aquí tienes contacto directo 👇\nhttps://wa.me/573160422795"

    if user_state["confirming"]:
        return process_confirmation(msg)

    if user_state["last_action"]:
        forced = handle_action(user_state["last_action"], msg)
        if forced:
            return forced

    cleaned = clean_text(msg)
    intent = intent_model.predict(vectorizer.transform([cleaned]))[0]

    for i in intents:
        if i["tag"] == intent:
            user_state["last_action"] = i.get("next_action")
            resp = i["responses"][0]

            # Placeholders dinámicos
            if "{name}" in resp and user_state["name"]:
                resp = resp.replace("{name}", user_state["name"])
            if "{city}" in resp and user_state["city"]:
                resp = resp.replace("{city}", user_state["city"])
            if "{budget}" in resp and user_state["budget"]:
                resp = resp.replace("{budget}", f"${user_state['budget']:,}")
            if "{phone}" in resp and user_state["phone"]:
                resp = resp.replace("{phone}", user_state["phone"])

            return resp

    sem = find_semantic(msg)
    if sem:
        user_state["last_action"] = sem.get("next_action")
        return sem["responses"][0]

    return "No entendí muy bien, ¿podrías repetirlo?"


# -----------------------------
# CONSOLA LOCAL
# -----------------------------
if __name__ == "__main__":

    while True:
        msg = input("Tú: ").strip()
        if msg.lower() in ["salir", "exit"]:
            print("Bot: ¡Hasta luego! 👋")
            break
        print("Bot:", chatbot_answer(msg))
