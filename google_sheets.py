from flask import Flask, request, jsonify
import os
import json
import datetime
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# =========================
# CONFIGURACIÓN
# =========================

SPREADSHEET_ID = "1OPvixPXTfuYnpGYcxcyFRQzSuM3aKqDyLTZLXL-g54k"

HOJAS = {
    "invertir": "invertir",
    "aprender": "aprender"
}

# =========================
# GOOGLE SHEETS
# =========================

def guardar_en_google_sheets(modo, name, city, phone):
    print("🟡 Entró a guardar_en_google_sheets")

    creds_raw = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    print("🟡 Variable existe:", bool(creds_raw))

    if not creds_raw:
        print("❌ ERROR: GOOGLE_SHEETS_CREDENTIALS no existe")
        return False

    try:
        creds_info = json.loads(creds_raw)
        print("🟢 JSON de credenciales cargado")
    except Exception as e:
        print("❌ ERROR JSON:", e)
        return False

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    try:
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(creds)
        sh = client.open_by_key(SPREADSHEET_ID)
        print("🟢 Conectado a Google Sheets")
    except Exception as e:
        print("❌ ERROR conexión Sheets:", e)
        return False

    hoja = HOJAS.get(modo, "invertir")

    try:
        worksheet = sh.worksheet(hoja)
    except gspread.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=hoja, rows="1000", cols="20")
        worksheet.update("A1:D1", [["nombre", "ciudad", "telefono", "fecha"]])

    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        worksheet.append_row([
            name or "",
            city or "",
            phone or "",
            fecha
        ])
        print(f"✅ Guardado en hoja {hoja}")
        return True
    except Exception as e:
        print("❌ ERROR al guardar fila:", e)
        return False


# =========================
# ENDPOINT PRINCIPAL
# =========================

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "online"})


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📩 DATA RECIBIDA:", data)

    modo = data.get("modo")
    name = data.get("name")
    city = data.get("city")
    phone = data.get("phone")

    if not modo:
        return jsonify({"error": "modo requerido"}), 400

    ok = guardar_en_google_sheets(modo, name, city, phone)

    return jsonify({"guardado": ok})


# =========================
# START
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
