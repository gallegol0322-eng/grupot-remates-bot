import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

client = None   # <<--- AÚN NO creamos el cliente

# ======================================================
# INICIALIZACIÓN SEGURA (sin explotar si falta la variable)
# ======================================================
def init_google_client():
    global client

    if client is not None:
        return client

    creds_env = os.environ.get("GOOGLE_CREDENTIALS")

    if not creds_env:
        print("⚠️ GOOGLE_CREDENTIALS NO está configurado en Render")
        return None

    try:
        google_creds = json.loads(creds_env)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
        client = gspread.authorize(creds)
        print("✔️ Cliente de Google Sheets inicializado.")
        return client

    except Exception as e:
        print("❌ Error inicializando Google Sheets:", e)
        return None


SHEET_NAME = "clientes_bot"

def guardar_en_google_sheets(modo, name, city, budget, phone):
    gc = init_google_client()

    if not gc:
        print("⚠️ No se pudo inicializar Google Sheets. Dato NO guardado.")
        return

    try:
        sheet = gc.open(SHEET_NAME).worksheet(
            "invertir" if modo == "invertir" else "aprender"
        )

        row = [name, city, phone] if modo == "aprender" else [name, city, budget, phone]

        sheet.append_row(row)
        print("✔️ Datos guardados correctamente en Google Sheets.")

    except Exception as e:
        print("❌ Error guardando en Google Sheets:", e)
