from flask import Flask, request, jsonify
import random
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

app = Flask(__name__)

# ============================================================
#  GOOGLE SHEETS (CONFIGURACIÓN) — COMPATIBLE CON RENDER 🚀
# ============================================================

# Cargar credenciales desde VARIABLE DE ENTORNO
google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
client = gspread.authorize(creds)

# Abre las hojas "aprender" y "invertir"
SHEET_ID = "1OPvixPXTfuYnpGYcxcyFRQzSuM3aKqDyLTZLXL-g54k"

sheet_aprender = client.open_by_key(SHEET_ID).worksheet("aprender")
sheet_invertir = client.open_by_key(SHEET_ID).worksheet("invertir")


def guardar_aprender(nombre, ciudad, telefono):
    sheet_aprender.append_row(
        [nombre, ciudad, telefono, time.strftime("%Y-%m-%d %H:%M:%S")]
    )


def guardar_invertir(nombre, ciudad, presupuesto, telefono):
    sheet_invertir.append_row(
        [nombre, ciudad, presupuesto, telefono, time.strftime("%Y-%m-%d %H:%M:%S")]
    )


# ============================================================
#  RESPUESTAS PARA COMENTARIOS POSITIVOS
# ============================================================

respuestas_aprender = [
    "✨ ¡Qué bueno ver tu interés por aprender sobre remates judiciales! Te enviamos un DM 📩",
    "📚 Aprender el paso a paso correcto hace toda la diferencia. Revisa tu DM ✨",
    "✨ Gracias por tu interés en formarte con nosotros. Te escribimos por DM 🙌"
]

respuestas_invertir = [
    "👋 Ya te enviamos un mensaje privado con todos los detalles para invertir en remates judiciales 🏡✨",
    "🏘️ Te enviamos la información para comenzar tu proceso de inversión. Revisa tu DM 📩",
    "😊 Información enviada a tu bandeja de entrada ✨"
]


# ============================================================
#  DM INICIAL PARA MANYCHAT → CHATBOT PRINCIPAL
# ============================================================

mensaje_dm_inicial = (
    "✨ ¡Hola! Qué alegría tenerte por aquí ✨\n"
    "👋 Somos Grupo T.\n"
    "¿Deseas *aprender* o *invertir*?\n"
    "Escribe *asesor* si deseas hablar con uno."
)


# ============================================================
#  CLASIFICAR COMENTARIO
# ============================================================

def clasificar_comentario(texto):
    texto = texto.lower()

    positivos = [
        "interes", "quiero", "informacion", "info", "precio", "invertir",
        "aprender", "saber", "como funciona", "cómo funciona", "metodo"
    ]

    negativos = [
        "estafa", "mentira", "engaño", "falso", "robo", "basura", "no creo"
    ]

    if any(p in texto for p in positivos):
        return "positivo"
    if any(n in texto for n in negativos):
        return "negativo"
    return "neutral"


# ============================================================
#  ANTI SPAM
# ============================================================

def anti_spam_delay():
    time.sleep(random.uniform(2.5, 5.0))


# ============================================================
#  WEBHOOK MANYCHAT
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}

    comentario = data.get("comment", "")
    user_id = data.get("user_id", "")
    dm = data.get("message", "")

    # Si es comentario:
    if comentario:
        clasificacion = clasificar_comentario(comentario)

        if clasificacion != "positivo":
            return jsonify({"accion": "ignorar"})

        anti_spam_delay()

        respuesta_publica = random.choice(respuestas_aprender + respuestas_invertir)

        return jsonify({
            "accion": "responder",
            "comentario_publico": respuesta_publica,
            "mensaje_dm": mensaje_dm_inicial,
            "user_id": user_id
        })

    # Si es DM:
    if dm:
        return jsonify({"accion": "dm_recibido"})

    return jsonify({"status": "ok"})


# ============================================================
#  RUTA HOME (OBLIGATORIA PARA RENDER) ⭐
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return "Servidor activo ✔", 200


# ============================================================
#  RUN LOCAL
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
