from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from apscheduler.schedulers.background import BackgroundScheduler
import dateparser
import datetime
import pytz

app = Flask(__name__)
scheduler = BackgroundScheduler()
scheduler.start()

recordatorios = []

def enviar_recordatorio(numero, mensaje):
    # Esta función puede luego conectarse con Twilio directamente
    print(f"Enviando recordatorio a {numero}: {mensaje}")

@app.route("/", methods=["POST"])
def whatsapp_bot():
    mensaje = request.form.get('Body').lower()
    numero = request.form.get('From')
    respuesta = MessagingResponse()

    if "recuérdame" in mensaje or "recordatorio" in mensaje:
        fecha = dateparser.parse(mensaje, settings={'PREFER_DATES_FROM': 'future'})
        
        if not fecha:
            respuesta.message("No pude entender la fecha y hora. Intenta decir algo como:\n'Reunión con Luis el viernes a las 10am, recuérdame 10 minutos antes.'")
            return str(respuesta)

        anticipacion = 0
        if "minuto" in mensaje:
            palabras = mensaje.split()
            for i, palabra in enumerate(palabras):
                if "minuto" in palabra:
                    try:
                        anticipacion = int(palabras[i - 1])
                    except:
                        anticipacion = 10
                    break

        # Hora de envío
        hora_envio = fecha - datetime.timedelta(minutes=anticipacion)

        if hora_envio < datetime.datetime.now():
            respuesta.message("La hora del recordatorio ya pasó. Intenta una hora futura.")
            return str(respuesta)

        scheduler.add_job(
            enviar_recordatorio,
            trigger='date',
            run_date=hora_envio,
            args=[numero, f"🔔 Recordatorio: {mensaje}"],
            timezone=pytz.timezone("America/Santiago")
        )

        respuesta.message(f"✅ Recordatorio agendado para el {fecha.strftime('%A %d/%m %H:%M')}.\nTe avisaré {anticipacion} minutos antes.")

    else:
        respuesta.message("Hola 👋, soy tu asistente. Puedes decirme:\n'Recuérdame reunión con Luis el viernes a las 10am, 10 minutos antes.'")

    return str(respuesta)
