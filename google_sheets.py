import gspread
from google.oauth2.service_account import Credentials

# 🏦 ID del libro de Sheets
SPREADSHEET_ID = "clientes_bot"

# 📄 Hojas según modo del usuario
HOJAS = {
    "invertir": "invertir",
    "aprender": "aprender"
}

def guardar_en_google_sheets(modo, name, city, budget, phone):

    creds = Credentials.from_service_account_file(
        "credentials.json",  # 🔥 asegúrate que existe en Render
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)
    worksheet = sh.worksheet(HOJAS.get(modo, "invertir"))  # fallback = invertir

    worksheet.append_row([name, city, budget, phone])

    print("✔ Registro enviado a Google Sheets")
