from flask import Flask, request, jsonify
import random
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

app = Flask(__name__)

# ============================================================
#  GOOGLE SHEETS (CONFIGURACIÓN)
# ============================================================

# Cargamos credenciales desde credentials.json
with open("credentials.json", "r") as f:
    google_creds = json.load(f)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
client = gspread.authorize(creds)

# Abre las hojas "Aprender" y "Invertir" dentro del archivo
SHEET_ID = "1OPvixPXTfuYnpGYcxcyFRQzSuM3aKqDyLTZLXL-g54k"

sheet_aprender = client.open_by_key(SHEET_ID).worksheet("Aprender")
sheet_invertir = client.open_by_key(SHEET_ID).worksheet("Invertir")

def guardar_aprender(nombre, ciudad, telefono):
    sheet_aprender.append_row([nombre, ciudad, telefono, time.strftime("%Y-%m-%d %H:%M:%S")])

def guardar_invertir(nombre, ciudad, presupuesto, telefono):
    sheet_invertir.append_row([nombre, ciudad, presupuesto, telefono, time.strftime("%Y-%m-%d %H:%M:%S")])

# ============================================================
#  RESPUESTAS PARA COMENTARIOS POSITIVOS
# ============================================================

respuestas_aprender = [
    "✨ ¡Qué bueno ver tu interés por aprender sobre remates judiciales! Te enviamos información directo al DM 📩",
    "📚 Aprender el paso a paso correcto hace toda la diferencia. Mira tu DM, allí encontrarás cómo funciona nuestra mentoría. ⚖️✨",
    "✨ Gracias por tu interés en formarte con nosotros. Te escribimos por DM con toda la información 🙌"
]

respuestas_invertir = [
    "👋 Ya te enviamos un mensaje privado con todos los detalles para invertir en remates judiciales 🏡✨",
    "🏘️ Te enviamos la información para comenzar tu proceso de inversión. Revisa tu DM 📩",
    "😊 Acabamos de enviarte un mensaje con toda la información para invertir de forma segura. Revisa tu bandeja de entrada ✨"
]

# ============================================================
#  MENSAJE DM INICIAL PARA TU BOT PRINCIPAL
# ============================================================

mensaje_dm_inicial = (
    "✨ ¡Hola! Qué alegría tenerte por aquí ✨\n"
    "👋 Somos Grupo T. Vimos que tienes interés sobre nosotros.\n"
    "¿Deseas *aprender* o deseas *invertir*?\n"
    "En cualquier momento escribe *asesor* para hablar con uno."
)

# ============================================================
#  CLASIFICACIÓN DE COMENTARIOS
# ============================================================

def clasificar_comentario(texto):
    texto = texto.lower()

    positivos = ["interes", "quiero", "informacion", "info", "precio", "metodo",
                 "invertir", "aprender", "saber", "explica", "cómo funciona"]

    negativos = ["estafa", "mentira", "engaño", "falso", "basura", "robo", "no creo"]

    if any(p in texto for p in positivos):
        return "positivo"
    if any(n in texto for n in negativos):
        return "negativo"
    return "neutral"

# ============================================================
#  ANTI SPAM — Delay aleatorio entre 2.5 y 5 segundos
# ============================================================

def anti_spam_delay():
    time.sleep(random.uniform(2.5, 5.0))

# ============================================================
#  WEBHOOK MANYCHAT → PYTHON
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    comentario = data.get("comment", "")
    user_id = data.get("user_id", "")

    clasificacion = clasificar_comentario(comentario)

    # Si el comentario no es positivo → ignorar
    if clasificacion != "positivo":
        return jsonify({"accion": "ignorar"})

    # Delay antispam
    anti_spam_delay()

    # Elige una de las 6 respuestas de forma aleatoria
    respuesta_publica = random.choice(respuestas_aprender + respuestas_invertir)

    return jsonify({
        "accion": "responder",
        "comentario_publico": respuesta_publica,
        "mensaje_dm": mensaje_dm_inicial,
        "user_id": user_id
    })

# ============================================================
#  HOME PAGE - PARA PROBAR QUE ESTÁ EN LÍNEA
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return "Servidor activo ✔", 200

# ============================================================
#  EJECUCIÓN LOCAL
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
