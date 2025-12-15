import gspread
import json
import os
from google.oauth2.service_account import Credentials
import datetime

SPREADSHEET_ID = "1OPvixPXTfuYnpGYcxcyFRQzSuM3aKqDyLTZLXL-g54k"

HOJAS = {
    "invertir": "invertir",
    "aprender": "aprender"
}

def guardar_en_google_sheets(modo, name, city, phone):

    creds_raw = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not creds_raw:
        print("❌ ERROR: No se encontró GOOGLE_SHEETS_CREDENTIALS")
        return

    creds_info = json.loads(creds_raw)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)

    client = gspread.authorize(creds)
    sh = client.open_by_key(SPREADSHEET_ID)

    hoja = HOJAS.get(modo, "invertir")

    try:
        worksheet = sh.worksheet(hoja)
    except gspread.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=hoja, rows="1000", cols="20")
        worksheet.update("A1:D1", [["nombre", "ciudad", "telefono", "fecha"]])

    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    worksheet.append_row([
        name or "",
        city or "",
        phone or "",
        fecha
    ])

    print(f"✔ Guardado en Google Sheets — hoja «{hoja}»")
