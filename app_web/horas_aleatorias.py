from pymongo import MongoClient
from datetime import datetime, timedelta
import random

# Conexión
client = MongoClient("mongodb+srv://caminaseguro:bWbTAwKWxEFzgfQt@cluster0.oawj7sa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["caminaseguro"]
coleccion = db["delitos_formateados"]  # ejemplo: "incidentes"

# Filtrar documentos con hora 00:00:00
filtro = {
    "fecha_completa": {
        "$regex": r"\d{4}-\d{2}-\d{2} 00:00:00"  # string exacto
    }
}

documentos = coleccion.find(filtro)

for doc in documentos:
    fecha_str = doc["fecha_completa"]
    fecha_base = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")

    # Generar hora aleatoria
    horas = random.randint(0, 23)
    minutos = random.randint(0, 59)

    nueva_fecha = fecha_base + timedelta(hours=horas, minutes=minutos)

    # Actualizar documento
    coleccion.update_one(
        {"_id": doc["_id"]},
        {"$set": {"fecha_completa": nueva_fecha.strftime("%Y-%m-%d %H:%M:%S")}}
    )

print("Fechas actualizadas con horas aleatorias.")
