import gspread
import json
import os
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1OPvixPXTfuYnpGYcxcyFRQzSuM3aKqDyLTZLXL-g54k"

HOJAS = {
    "invertir": "invertir",
    "aprender": "aprender"
}

def guardar_en_google_sheets(modo, name, city, budget, phone):
    creds_info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client = gspread.authorize(creds)
    sh = client.open_by_key(SPREADSHEET_ID)

    hoja = HOJAS.get(modo, "invertir")
    try:
        worksheet = sh.worksheet(hoja)
    except gspread.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=hoja, rows="1000", cols="20")

    worksheet.append_row([name, city, budget, phone])
    print(f"✔ Guardado en Google Sheets — hoja «{hoja}»")


