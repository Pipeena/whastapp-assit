from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import datetime
import time
import threading
import logging
import dateparser
import os
from dotenv import load_dotenv
import re
import pytz  # Importante para zona horaria

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cargar variables de entorno
load_dotenv()

# Configuración Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
USER_PHONE_NUMBER = os.getenv('USER_PHONE_NUMBER')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
app = Flask(__name__)

recordatorios = []
ZONA_CHILE = pytz.timezone("America/Santiago")

def extraer_anticipacion(mensaje):
    match = re.search(r'(\d+)\s*minutos?\s*antes', mensaje.lower())
    if match:
        return int(match.group(1))
    return 10  # Por defecto 10 minutos antes

def procesar_mensaje(mensaje):
    mensaje_lower = mensaje.lower()
    if "recuérdame" in mensaje_lower:
        logging.info(f"Procesando recordatorio: {mensaje}")

        anticipacion = extraer_anticipacion(mensaje)

        ahora_chile = datetime.datetime.now(ZONA_CHILE)

        fecha_evento = dateparser.parse(
            mensaje,
            languages=['es'],
            settings={
                'PREFER_DATES_FROM': 'future',
                'TIMEZONE': 'America/Santiago',
                'TO_TIMEZONE': 'America/Santiago',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'RELATIVE_BASE': ahora_chile
            }
        )

        logging.info(f"Fecha detectada: {fecha_evento}")

        if not fecha_evento:
            return "❌ No pude entender la fecha y hora del recordatorio. Intenta con otro formato."

        recordatorios.append({
            "mensaje": mensaje,
            "fecha_evento": fecha_evento,
            "anticipacion_segundos": anticipacion * 60,
            "enviado": False
        })
        return f"✅ Recordatorio creado para {fecha_evento.strftime('%Y-%m-%d %H:%M:%S')} con aviso {anticipacion} minutos antes."

    elif "ver recordatorios" in mensaje_lower:
        if not recordatorios:
            return "📭 No tienes recordatorios guardados."
        textos = []
        for r in recordatorios:
            hora_local = r['fecha_evento'].astimezone(ZONA_CHILE)
            textos.append(f"- {r['mensaje']} (evento: {hora_local.strftime('%Y-%m-%d %H:%M:%S')})")
        return "\n".join(textos)

    else:
        return "🤖 No entendí tu mensaje. Usa:\n- recuérdame [evento] [fecha/hora] [X minutos antes]\n- ver recordatorios"

@app.route('/sms', methods=['POST'])
def sms_reply():
    mensaje_usuario = request.form.get('Body', '')
    logging.info(f"Mensaje recibido: {mensaje_usuario}")
    respuesta_texto = procesar_mensaje(mensaje_usuario)

    resp = MessagingResponse()
    resp.message(respuesta_texto)
    return str(resp)

def revisar_recordatorios():
    while True:
        ahora = datetime.datetime.now(ZONA_CHILE)
        logging.info(f"Revisando recordatorios a las {ahora.isoformat()}")
        for r in list(recordatorios):
            if r["enviado"]:
                continue
            tiempo_aviso = r["fecha_evento"] - datetime.timedelta(seconds=r["anticipacion_segundos"])
            delta = (tiempo_aviso - ahora).total_seconds()
            logging.info(f"Tiempo para aviso de '{r['mensaje']}': {delta} segundos")

            if 0 <= delta <= 60:
                try:
                    client.messages.create(
                        body=f"⏰ Recordatorio: {r['mensaje']}",
                        from_=TWILIO_PHONE_NUMBER,
                        to=USER_PHONE_NUMBER
                    )
                    logging.info(f"Recordatorio enviado: {r['mensaje']}")
                    r["enviado"] = True
                except Exception as e:
                    logging.error(f"Error enviando recordatorio: {e}")
        time.sleep(30)

threading.Thread(target=revisar_recordatorios, daemon=True).start()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
