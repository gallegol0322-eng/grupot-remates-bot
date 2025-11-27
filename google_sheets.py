import gspread
import json
import os
from google.oauth2.service_account import Credentials

# 🆔 ID del libro
SPREADSHEET_ID = "clientes_bot"  # <-- si tu ID no es este, te digo ahora cómo tomarlo

HOJAS = {
    "invertir": "invertir",
    "aprender": "aprender"
}

def guardar_en_google_sheets(modo, name, city, budget, phone):

    # Lee JSON desde la env var GOOGLE_CREDENTIALS
    creds_info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    gc = gspread.authorize(creds)

    # 📄 Abrir libro
    sh = gc.open_by_key(SPREADSHEET_ID)

    hoja = HOJAS.get(modo, "invertir")

    ws = sh.worksheet(hoja)
    ws.append_row([name, city, budget, phone])  # envía fila 🔥

    print(f"✔ Guardado Google Sheets ({hoja})")
