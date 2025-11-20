import os
import json
import time
from flask import Flask, request, jsonify

# ===========================
#  IMPORTAR TU CHATBOT
# ===========================
from chatbot_logic import chatbot_answer, reset_user_state
from google_sheets import guardar_en_google_sheets

app = Flask(__name__)

# -------------------------------
# PRUEBA DE VIDA
# -------------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "message": "Bot funcionando en Render"}), 200


# -------------------------------
# WEBHOOK PRINCIPAL
# -------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)

        # Datos según ManyChat o IG Webhook
        user_id = str(data.get("user_id", "")) or str(data.get("sender_id", ""))
        msg = data.get("message") or data.get("comment") or ""

        if not user_id or not msg:
            return jsonify({"error": "user_id o message faltantes"}), 400

        # Opcional: resetear estado si dice "reiniciar"
        if msg.lower().strip() in ["reset", "reiniciar", "empezar de nuevo"]:
            reset_user_state(user_id)
            return jsonify({"reply": "Listo, empecemos de cero 😊"}), 200

        # Generar respuesta del chatbot
        respuesta = chatbot_answer(user_id, msg)

        return jsonify({
            "accion": "responder",
            "usuario": user_id,
            "respuesta": respuesta
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------
# INICIO
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
