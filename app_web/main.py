from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()  # Carga variables de entorno

app = Flask(__name__)
client = MongoClient("mongodb+srv://caminaseguro:bWbTAwKWxEFzgfQt@cluster0.oawj7sa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client.caminaseguro

incidentes = db["delitos_formateados"]
colonias = db["colonias_calles"]
tipos_delito = db["tipos_delito"]
forma_accion = db["forma_accion"]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/colonias', methods=['GET'])
def get_colonias():
    try:
        pipeline = [
            {
                "$match": {
                    "municipio": {"$exists": True},
                    "colonia": {"$exists": True}
                }
            },
            {
                "$group": {
                    "_id": "$colonia",
                    "total": {"$sum": 1},
                    "coordenadas": {
                        "$first": {
                            "$cond": [
                                {"$ifNull": ["$ubicacion.coordinates", False]},
                                "$ubicacion",
                                None
                            ]
                        }
                    },
                    "tipos_delitos": {"$addToSet": "$delito"},
                    "ultimo_incidente": {"$max": "$fecha_completa"}
                }
            },
            {
                "$project": {
                    "colonia": "$_id",
                    "total": 1,
                    "coordenadas": 1,
                    "variedad_delitos": {"$size": "$tipos_delitos"},
                    "tipos_delitos": {"$slice": ["$tipos_delitos", 5]},
                    "ultimo_incidente": 1,
                    "nivel_peligro": {
                        "$switch": {
                            "branches": [
                                {"case": {"$gte": ["$total", 100]}, "then": "Alto"},
                                {"case": {"$gte": ["$total", 50]}, "then": "Medio"},
                                {"case": {"$lt": ["$total", 49]}, "then": "Bajo"}
                            ]
                        }
                    }
                }
            },
            {"$sort": {"total": -1}},
            {"$match": {"total": {"$gt": 0}}}
        ]

        resultados = list(db.delitos.aggregate(pipeline))

        return jsonify({
            "status": "success",
            "count": len(resultados),
            "data": resultados
        })

    except Exception as e:
        app.logger.error(f"Error en /api/colonias: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error al procesar la solicitud",
            "details": str(e)
        }), 500


@app.route('/api/calles', methods=['GET'])
def get_calles():
    try:
        # Pipeline base
        match_stage = {
            "municipio": {"$regex": "^CELAYA$", "$options": "i"},
            "calle": {"$exists": True, "$ne": None, "$ne": "", "$ne": "NO CATALOGADO"}
        }

        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": {
                        "calle": "$calle",
                        "colonia": "$colonia"
                    },
                    "total": {"$sum": 1},
                    "coordenadas": {"$first": "$ubicacion"},
                    "tipos_delitos": {"$push": "$delito"}
                }
            },
            {
                "$project": {
                    "calle": "$_id.calle",
                    "colonia": "$_id.colonia",
                    "total": 1,
                    "coordenadas": 1,
                    "variedad_delitos": {"$size": "$tipos_delitos"},
                    "nivel_peligro": {
                        "$switch": {
                            "branches": [
                                {"case": {"$gte": ["$total", 100]}, "then": "Alto"},
                                {"case": {"$gte": ["$total", 50]}, "then": "Medio"},
                                {"case": {"$lt": ["$total", 50]}, "then": "Bajo"}
                            ]
                        }
                    }
                }
            },
            {"$sort": {"total": -1}}
        ]


        resultados = list(db.delitos_formateados.aggregate(pipeline))

        return jsonify({
            "status": "success",
            "count": len(resultados),
            "data": resultados
        })

    except Exception as e:
        app.logger.error(f"Error en /api/calles: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error al procesar la solicitud"
        }), 500



@app.route("/formulario")
def formulario():
    delitos = list(tipos_delito.find({}, {"_id": 0}))
    colonias_lista = list(colonias.find({}, {"_id": 0, "colonia": 1}))
    return render_template("form.html", delitos=delitos, colonias=colonias_lista)

@app.route("/api/tipos_delito")
def api_tipos_delito():
    datos = list(db.tipos_delito.find({}, {"_id": 0}))
    return jsonify(datos)

@app.route("/api/forma_accion")
def api_formas_accion():
    formas = db.delitos.distinct("forma_accion")
    return jsonify([{"forma_accion": f} for f in formas])

@app.route("/api/colonias_form")
def api_colonias():
    colonias_c = colonias.find({}, {"_id": 0, "colonia": 1})
    resultados = list(colonias_c)
    return jsonify(resultados)


@app.route("/api/calles/<colonia>")
def api_calles(colonia):
    # Buscar el documento que tenga la colonia solicitada (case sensitive, igual que en DB)
    documento = db.colonias_calles.find_one({"colonia": colonia}, {"_id": 0, "calles": 1})

    if documento and "calles" in documento:
        # Extraemos solo los nombres de calles (suponiendo que cada calle es un dict con 'calle' y 'ubicacion')
        calles = [c["calle"] for c in documento["calles"]]
        return jsonify([{"calle": calle} for calle in calles])
    else:
        return jsonify([])  # Si no hay calles o colonia no encontrada, enviamos lista vacía


from flask import request, jsonify

@app.route("/api/coordenadas", methods=["POST"])
def obtener_coordenadas():
    data = request.get_json()
    colonia = data.get("colonia")
    calle = data.get("calle")

    resultado = db["delitos_formateados"].find_one({
        "colonia": colonia,
        "calle": calle,
        "ubicacion": {"$exists": True}
    }, {"ubicacion": 1})

    if resultado and "ubicacion" in resultado:
        return jsonify(resultado["ubicacion"])
    else:
        return jsonify({"type": "Point", "coordinates": [0, 0]}), 404

def formatear_fecha(fecha):
    # Si ya es datetime, la convierte al formato deseado
    if isinstance(fecha, datetime):
        return fecha.strftime("%Y-%m-%d %H:%M:%S")
    try:
        # Si es string, lo intenta convertir a datetime primero
        fecha_dt = datetime.fromisoformat(fecha)
        return fecha_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None  # Si no es válido

@app.route("/reportar-incidente", methods=["POST"])
def reportar_incidente():
    datos = {
        "delito": request.form["tipo_delito"],
        "colonia": request.form["colonia"],
        "calle": request.form["calle"],
        "forma_accion": request.form["forma_accion"],
        "fecha_completa": formatear_fecha(request.form["fecha_hora"]),
        "municipio": "CELAYA",
        "ubicacion": {
            "type": "Point",
            "coordinates": [
                str(request.form["lng"]),
                str(request.form["lat"])
            ]
        }
    }

    incidentes.insert_one(datos)
    ultimo = incidentes.find_one(sort=[("_id", -1)])
    print(ultimo)
    return "Gracias, Incidente reportado correctamente"


if __name__ == '__main__':
    app.run(debug=True)