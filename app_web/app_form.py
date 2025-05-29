from flask import Flask, request, render_template, jsonify
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

client = MongoClient("mongodb+srv://caminaseguro:bWbTAwKWxEFzgfQt@cluster0.oawj7sa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["caminaseguro"]
incidentes = db["delitos_prueba"]
colonias = db["colonias_con_calles"]
tipos_delito = db["tipos_delito"]
forma_accion = db["forma_accion"]

@app.route("/formulario")
def formulario():
    delitos = list(tipos_delito.find({}, {"_id": 0}))
    colonias_lista = list(colonias.find({}, {"_id": 0, "colonia": 1}))
    return render_template("formulario.html", delitos=delitos, colonias=colonias_lista)

@app.route("/get_calles/<colonia>")
def get_calles(colonia):
    doc = colonias.find_one({"colonia": colonia}, {"_id": 0, "calles": 1})
    return jsonify(doc["calles"] if doc else [])

@app.route("/reportar-incidente", methods=["POST"])
def reportar_incidente():
    datos = {
        "delito": request.form["tipo_delito"],
        "colonia": request.form["colonia"],
        "calle": request.form["calle"],
        "forma_accion": request.form["forma_accion"],
        "fecha_completa": request.form["fecha_hora"],
        "anio": int(request.form["fecha_hora"][:4]),
        "mes_nombre": datetime.strptime(request.form["fecha_hora"], "%Y-%m-%dT%H:%M").strftime("%B").upper(),
        "dia": int(request.form["fecha_hora"][8:10]),
        "municipio": "CELAYA",  # Puedes permitir que esto sea editable si lo deseas
    }
    incidentes.insert_one(datos)
    return "Incidente reportado correctamente"

