import datetime
import re
import logging
import pytz
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import threading
import time

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
        dia += datetime.timedelta(days=diferencia)

    fecha_hora = datetime.datetime.combine(dia, hora_obj)
    return tz_chile.localize(fecha_hora)

def obtener_anticipacion(texto):
    match = re.search(r'(\d+)\s*minutos?\s*antes', texto)
    if match:
        return int(match.group(1))
    return 0

@app.route("/sms", methods=["POST"])
def sms_reply():
    mensaje = request.form.get("Body", "")
    logging.info(f"Mensaje recibido: {mensaje}")
    fecha_evento = parsear_fecha_hora(mensaje)
    logging.info(f"Procesando recordatorio: {mensaje}")
    logging.info(f"Fecha detectada: {fecha_evento}")

    if fecha_evento:
        anticipacion = obtener_anticipacion(mensaje)
        recordatorios.append({
            "mensaje": mensaje,
            "fecha": fecha_evento,
            "anticipacion": anticipacion,
            "avisado": False
        })
        respuesta = f"Te recordaré: '{mensaje}' a las {fecha_evento.strftime('%H:%M')} (con {anticipacion} minutos de anticipación)."
    else:
        respuesta = "No entendí bien la fecha y hora. Intenta con un formato como 'Recuérdame reunión hoy a las 14:30, 10 minutos antes'."

    resp = MessagingResponse()
    resp.message(respuesta)
    return str(resp)

def revisar_recordatorios():
    while True:
        ahora = datetime.datetime.now(tz_chile)
        logging.info(f"Revisando recordatorios a las {ahora.isoformat()}")
        for recordatorio in recordatorios:
            tiempo_evento = recordatorio["fecha"] - datetime.timedelta(minutes=recordatorio["anticipacion"])
            if tiempo_evento <= ahora and not recordatorio["avisado"]:
                logging.info(f"⏰ Recordatorio: {recordatorio['mensaje']}")
                recordatorio["avisado"] = True
        time.sleep(30)

if __name__ == "__main__":
    hilo = threading.Thread(target=revisar_recordatorios)
    hilo.daemon = True
    hilo.start()
    app.run(debug=True)
