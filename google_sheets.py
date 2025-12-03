import gspread
import json
import os
from google.oauth2.service_account import Credentials

# ID del libro clientes_bot
SPREADSHEET_ID = "1OPvixPXTfuYnpGYcxcyFRQzSuM3aKqDyLTZLXL-g54k"

# Nombre de cada hoja
HOJAS = {
    "invertir": "invertir",
    "aprender": "aprender"
}

def guardar_en_google_sheets(modo, name, city, phone):
    """
    Guarda un registro en Google Sheets según el modo (invertir/aprender).
    """

    # cargar credenciales del ENV
    creds_raw = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_raw:
        print("❌ ERROR: No se encontró GOOGLE_CREDENTIALS en variables de entorno")
        return

    creds_info = json.loads(creds_raw)

    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    # conectar
    client = gspread.authorize(creds)
    sh = client.open_by_key(SPREADSHEET_ID)

    # seleccionar hoja
    hoja = HOJAS.get(modo, "invertir")

    try:
        worksheet = sh.worksheet(hoja)
    except gspread.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=hoja, rows="1000", cols="20")
        # escribir encabezados si la creamos
        worksheet.update("A1:E1", [["nombre", "ciudad", "telefono", "fecha"]])

    # convertir valores para evitar None
    name = name or ""
    city = city or ""
    budget = budget or ""
    phone = phone or ""

    # insertar fila
    import datetime
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    worksheet.append_row([name, city, phone, fecha])


    print(f"✔ Guardado en Google Sheets — hoja «{hoja}»")



