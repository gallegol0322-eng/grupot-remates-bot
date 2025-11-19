from flask import Flask, request, jsonify
import random
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

app = Flask(__name__)

# ============================================================
#  GOOGLE SHEETS (CONFIGURACIÓN) — COMPATIBLE CON RENDER 🚀
# ============================================================

# Cargar credenciales desde VARIABLE DE ENTORNO
google_creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
client = gspread.authorize(creds)

# Abre las hojas "Aprender" y "Invertir"
SHEET_ID = "1OPvixPXTfuYnpGYcxcyFRQzSuM3aKqDyLTZLXL-g54k"

sheet_aprender = client.open_by_key(SHEET_ID).worksheet("aprender")
sheet_invertir = client.open_by_key(SHEET_ID).worksheet("invertir")

def guardar_aprender(nombre, ciudad, telefono):
    sheet_aprender.append_row([nombre, ciudad, telefono, time.strftime("%Y-%m-%d %H:%M:%S")])

def guardar_invertir(nombre, ciudad, presupuesto, telefono):
    sheet_invertir.append_row([nombre, ciudad, presupuesto, telefono, time.strftime("%Y-%m-%d %H:%M:%S")])

