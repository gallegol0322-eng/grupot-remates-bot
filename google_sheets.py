import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# -------------------------
# CONFIGURACIÓN GOOGLE API
# -------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "nimble-answer-478618-b4-27f05be4a639.json", scope
)
client = gspread.authorize(creds)

# -------------------------
# ID DE TU GOOGLE SHEETS
# -------------------------
SPREADSHEET_ID = "1OPvixPXTfuYnpGYcxcyFRQzSuM3aKqDyLTZLXL-g54k"


def guardar_en_google_sheets(modo, name, city, budget, phone):
    """
    modo: 'aprender' o 'invertir'
    """
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if modo == "invertir":
        datos = [name, city, budget, phone, fecha_actual]
        hoja = client.open_by_key(SPREADSHEET_ID).worksheet("invertir")

    elif modo == "aprender":
        datos = [name, city, phone, fecha_actual]
        hoja = client.open_by_key(SPREADSHEET_ID).worksheet("aprender")

    else:
        print(f"[ERROR] Modo inválido: {modo}")
        return

    hoja.append_row(datos, value_input_option="USER_ENTERED")
    print(f"✔ Datos guardados en '{modo}': {datos}")
