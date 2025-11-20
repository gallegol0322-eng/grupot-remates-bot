import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Cargar credenciales desde la variable de entorno en Render
google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])

creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
client = gspread.authorize(creds)

# Nombre del archivo de Google Sheets
SHEET_NAME = "clientes_bot"

def guardar_en_google_sheets(modo, name, city, budget, phone):
    """
    Guarda los datos del usuario en la hoja correspondiente:
      - invertir → hoja 'invertir'
      - aprender → hoja 'aprender'
    """
    try:
        # Seleccionar hoja
        sheet = client.open(SHEET_NAME).worksheet(
            "invertir" if modo == "invertir" else "aprender"
        )

        # Filas diferentes según modo
        if modo == "aprender":
            row = [name, city, phone]
        else:
            row = [name, city, budget, phone]

        # Insertar fila
        sheet.append_row(row)
        print("Datos guardados correctamente en Google Sheets:", row)

    except Exception as e:
        print("Error guardando en Google Sheets:", e)
