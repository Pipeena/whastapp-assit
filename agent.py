from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import datetime
import time
import threading
import logging
import dateparser
from dateparser.search import search_dates
import os
from dotenv import load_dotenv
import re
import pytz
import google.generativeai as genai  # <- NUEVO

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
USER_PHONE_NUMBER = os.getenv('USER_PHONE_NUMBER')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # <- NUEVO

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
app = Flask(__name__)
recordatorios = []
tz_chile = pytz.timezone("America/Santiago")

def extraer_anticipacion(mensaje):
    match = re.search(r'(\d+)\s*minutos?\s*antes', mensaje.lower())
    if match:
        return int(match.group(1))
    return 10

def consultar_gemini(texto_usuario):
    try:
        modelo = genai.GenerativeModel('gemini-pro')
        prompt = f"""Extrae la fecha y hora futura del siguiente mensaje:
'{texto_usuario}'
Devuélvela en formato ISO 8601 y en horario de Chile.
Si no hay fecha, responde exactamente: NO_FECHA"""
        respuesta = modelo.generate_content(prompt)
        contenido = respuesta.text.strip()
        logging.info(f"Gemini respondió: {contenido}")
        if "NO_FECHA" in contenido:
            return None
        return dateparser.parse(contenido, settings={'TIMEZONE': 'America/Santiago', 'RETURN_AS_TIMEZONE_AWARE': True})
    except Exception as e:
        logging.error(f"Error con Gemini: {e}")
        return None

def procesar_mensaje(mensaje):
    mensaje_lower = mensaje.lower()
    if "recuérdame" in mensaje_lower:
        logging.info(f"Procesando recordatorio: {mensaje}")
        anticipacion = extraer_anticipacion(mensaje)

        mensaje_limpio = re.sub(r"recuérdame", "", mensaje_lower, flags=re.IGNORECASE)
        mensaje_limpio = re.sub(r"\d+\s*minutos?\s*antes", "", mensaje_limpio, flags=re.IGNORECASE).strip()
        logging.info(f"Texto para detectar fecha: {mensaje_limpio}")

        resultado = search_dates(
            mensaje_limpio,
            languages=['es'],
            settings={
                'PREFER_DATES_FROM': 'future',
                'TIMEZONE': 'America/Santiago',
                'RETURN_AS_TIMEZONE_AWARE': True,
            }
        )

        fecha_evento = resultado[0][1] if resultado else None
        logging.info(f"Fecha detectada con dateparser: {fecha_evento}")

        # Usa Gemini si dateparser no encuentra fecha
        if not fecha_evento:
            logging.info("Dateparser no encontró fecha. Probando con Gemini...")
            fecha_evento = consultar_gemini(mensaje_limpio)

        if not fecha_evento:
            return "❌ No pude entender la fecha y hora del recordatorio, intenta de nuevo."

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
        textos = [f"- {r['mensaje']} (evento: {r['fecha_evento']})" for r in recordatorios]
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
        ahora = datetime.datetime.now(tz_chile)
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
