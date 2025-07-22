from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import datetime
import os

app = Flask(__name__)

recordatorios = []

def procesar_mensaje(mensaje):
    mensaje = mensaje.lower()
    if "recuérdame" in mensaje:
        recordatorios.append({
            "mensaje": mensaje,
            "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return "¡Listo! Te recordaré eso."
    elif "lista" in mensaje:
        if not recordatorios:
            return "No tienes recordatorios aún."
        return "\n".join(
            f"{i+1}. {r['mensaje']} - {r['fecha']}" for i, r in enumerate(recordatorios)
        )
    else:
        return "No entendí tu mensaje. Prueba con 'Recuérdame...' o 'Lista'."

@app.route("/sms", methods=['POST'])
def sms_reply():
    mensaje = request.form.get('Body')
    respuesta = procesar_mensaje(mensaje)
    resp = MessagingResponse()
    resp.message(respuesta)
    return str(resp)

@app.route("/", methods=['GET'])
def home():
    return "El bot está corriendo correctamente."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
