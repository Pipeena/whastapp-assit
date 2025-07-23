import datetime
import re
import logging
import pytz
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import threading
import time
import os  # Importamos para leer variables de entorno

app = Flask(__name__)
recordatorios = []

logging.basicConfig(level=logging.INFO)

tz_chile = pytz.timezone("America/Santiago")

def parsear_fecha_hora(texto):
    texto = texto.lower()

    ahora = datetime.datetime.now(tz_chile)
    dia = ahora.date()
    hora = ahora.time()

    # Buscar hora con formato HH:MM
    coincidencia_hora = re.search(r'(\d{1,2}:\d{2})', texto)
    if not coincidencia_hora:
        return None

    hora_texto = coincidencia_hora.group(1)
    try:
        hora_obj = datetime.datetime.strptime(hora_texto, "%H:%M").time()
    except ValueError:
        return None

    if "mañana" in texto:
        dia += datetime.timedelta(days=1)
    elif "pasado mañana" in texto:
        dia += datetime.timedelta(days=2)
    elif "hoy" in texto:
        pass
    elif "lunes" in texto:
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        hoy_idx = ahora.weekday()
        objetivo_idx = dias.index("lunes")
        diferencia = (objetivo_idx - hoy_idx + 7) % 7
        if diferencia == 0:
            diferencia = 7
