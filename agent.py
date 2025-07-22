from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import datetime
import os
from dotenv import load_dotenv

load_dotenv()  # Carga variables desde archivo .env

app = Flask(__name__)

# Obtiene las credenciales desde variables de entorno
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

client = Client(account_sid, auth_token)

recordatorios = []

def procesar_mensaje(mensaje):
    mensaje = mensaje.lower()
    if "recuérdame" in mensaje:
        recordatorios.append({
            "mensaje": mensaje,
            "hora_creacion": datetime.datetime.now().isoformat()
        })
        return "✅ ¡Recordatorio creado!"
    elif "ver recordatorios" in mensaje:
        if not recordatorios:
            return "📭 No tienes recordatorios guardados."
        return "\n".join([f"- {r['mensaje']}" for r in recordatorios])
    else:
        return "🤖 No entendí tu mensaje. Puedes escribir:\n- recuérdame...\n- ver recordatorios"

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    mensaje_usuario = request.form.get('Body', '')
    respuesta_texto = procesar_mensaje(mensaje_usuario)

    resp = MessagingResponse()
    resp.message(respuesta_texto)
    return str(resp)

if __name__ == '__main__':
    app.run(port=5000)

