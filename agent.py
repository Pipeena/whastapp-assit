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

# Configuración de logging para ver info en consola
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración Twilio desde variables de entorno
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
USER_PHONE_NUMBER = os.getenv('USER_PHONE_NUMBER')  # Tu número de WhatsApp para enviar mensajes

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = Flask(__name__)

# Lista para guardar recordatorios en memoria
recordatorios = []

def procesar_mensaje(mensaje):
    mensaje_lower = mensaje.lower()
    if "recuérdame" in mensaje_lower:
        logging.info(f"Procesando recordatorio para mensaje: {mensaje}")
        fecha_evento = dateparser.parse(mensaje, settings={'PREFER_DATES_FROM': 'future'})
        logging.info(f"Fecha detectada para recordatorio: {fecha_evento}")

        if not fecha_evento:
            return "❌ No pude entender la fecha y hora del recordatorio, intenta de nuevo con otra forma."

        # Guardar recordatorio
        recordatorios.append({
            "mensaje": mensaje,
            "fecha_evento": fecha_evento.isoformat(),
            "hora_creacion": datetime.datetime.now().isoformat()
        })
        return "✅ ¡Recordatorio creado!"
    
    elif "ver recordatorios" in mensaje_lower:
        if not recordatorios:
            return "📭 No tienes recordatorios guardados."
        textos = []
        for r in recordatorios:
            textos.append(f"- {r['mensaje']} (para {r['fecha_evento']})")
        return "\n".join(textos)
    
    else:
        return "🤖 No entendí tu mensaje. Puedes escribir:\n- recuérdame...\n- ver recordatorios"

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    mensaje_usuario = request.form.get('Body', '')
    logging.info(f"Mensaje recibido: {mensaje_usuario}")
    respuesta_texto = procesar_mensaje(mensaje_usuario)

    resp = MessagingResponse()
    resp.message(respuesta_texto)
    return str(resp)

def revisar_recordatorios():
    while True:
        ahora = datetime.datetime.now()
        logging.info(f"Revisando recordatorios a las {ahora.isoformat()}")
        for r in list(recordatorios):
            fecha_evento = datetime.datetime.fromisoformat(r["fecha_evento"])
            delta = (fecha_evento - ahora).total_seconds()
            logging.info(f"Tiempo restante para recordatorio '{r['mensaje']}': {delta} segundos")

            # Enviar recordatorio 10 minutos antes o menos
            if 0 <= delta <= 600:
                try:
                    client.messages.create(
                        body=f"⏰ Recordatorio: {r['mensaje']}",
                        from_=TWILIO_PHONE_NUMBER,
                        to=USER_PHONE_NUMBER
                    )
                    logging.info(f"Recordatorio enviado: {r['mensaje']}")
                    recordatorios.remove(r)
                except Exception as e:
                    logging.error(f"Error enviando mensaje: {e}")
        time.sleep(60)

# Iniciar el hilo para revisar recordatorios en segundo plano
threading.Thread(target=revisar_recordatorios, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
