import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])

creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
client = gspread.authorize(creds)

SHEET_NAME = "clientes_bot"

def guardar_en_google_sheets(modo, name, city, budget, phone):
    try:
        sheet = client.open(SHEET_NAME).worksheet(
            "invertir" if modo == "invertir" else "aprender"
        )

        row = [name, city, phone] if modo == "aprender" else [name, city, budget, phone]

        sheet.append_row(row)
        print("Datos guardados correctamente en Google Sheets.")

    except Exception as e:
        print("Error guardando en Google Sheets:", e)


