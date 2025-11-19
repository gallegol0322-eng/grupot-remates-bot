from flask import Flask, request, jsonify
import random
import time

app = Flask(__name__)

# ============================================================
#  RESPUESTAS PARA COMENTARIOS POSITIVOS
# ============================================================

respuestas_aprender = [
    "✨ ¡Qué bueno ver tu interés por aprender sobre remates judiciales! Te enviamos un DM 📩",
    "📚 Aprender el paso a paso correcto hace toda la diferencia. Mira tu DM, allí encontrarás cómo funciona nuestra mentoría. ⚖️✨",
    "✨ Gracias por tu interés en formarte con nosotros. Te escribimos por DM con toda la información 🙌"
]

respuestas_invertir = [
    "👋 Ya te enviamos un mensaje privado con todos los detalles para invertir en remates judiciales 🏡✨",
    "🏘️ Te enviamos la información para comenzar tu proceso de inversión. Revisa tu DM 📩",
    "😊 Acabamos de enviarte un mensaje con toda la información para invertir de forma segura. Revisa tu bandeja de entrada ✨"
]

# ============================================================
#  DM INICIAL PARA QUE MANYCHAT ACTIVE TU CHATBOT PRINCIPAL
# ============================================================

mensaje_dm_inicial = (
    "✨ ¡Hola! Qué alegría tenerte por aquí ✨\n"
    "👋 Somos Grupo T.\n"
    "Vimos que tienes interés sobre nosotros.\n"
    "¿Deseas *aprender* o deseas *invertir*?\n"
    "En cualquier momento escribe *asesor* para hablar con uno."
)

# ============================================================
#  PALABRAS POSITIVAS / NEGATIVAS
# ============================================================

def clasificar_comentario(texto):
    texto = texto.lower()

    positivos = [
        "interes", "quiero", "informacion", "info", "precio",
        "metodo", "invertir", "aprender", "saber",
        "explica", "cómo funciona", "como funciona"
    ]

    negativos = [
        "estafa", "mentira", "engaño", "falso",
        "basura", "robo", "no creo"
    ]

    if any(p in texto for p in positivos):
        return "positivo"
    if any(n in texto for n in negativos):
        return "negativo"
    return "neutral"

# ============================================================
#   ANTI SPAM (2.5 a 5 segundos)
# ============================================================

def anti_spam_delay():
    time.sleep(random.uniform(2.5, 5.0))

# ============================================================
#   WEBHOOK DE MANYCHAT (COMENTARIOS Y MENSAJES PRIVADOS)
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    comentario = data.get("comment", "")
    user_id = data.get("user_id", "")
    dm = data.get("message", "")

    # ============================================================
    # 1️⃣ SI VIENE UN COMENTARIO
    # ============================================================

    if comentario:
        clasificacion = clasificar_comentario(comentario)

        # Comentario negativo → ignorar
        if clasificacion != "positivo":
            return jsonify({"accion": "ignorar"})

        # Anti-spam
        anti_spam_delay()

        # Elige aleatoriamente una respuesta
        respuesta_publica = random.choice(
            respuestas_aprender + respuestas_invertir
        )

        return jsonify({
            "accion": "responder",
            "comentario_publico": respuesta_publica,
            "mensaje_dm": mensaje_dm_inicial,
            "user_id": user_id
        })

    # ============================================================
    # 2️⃣ SI VIENE UN MENSAJE PRIVADO (DM)
    # NO HACEMOS NADA AQUÍ — MANYCHAT LO MANDA A TU CHATBOT
    # ============================================================

    if dm:
        return jsonify({
            "accion": "dm_recibido",
            "mensaje": "DM recibido, procesado por ManyChat"
        })

    return jsonify({"status": "ok"})

# ============================================================
#  HOME PAGE
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return "Servidor activo ✔", 200

# ============================================================
#  EJECUCIÓN LOCAL
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
