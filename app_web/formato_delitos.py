from pymongo import MongoClient

# Conexión a MongoDB
client = MongoClient("mongodb+srv://caminaseguro:bWbTAwKWxEFzgfQt@cluster0.oawj7sa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["caminaseguro"]

# Colecciones
origen = db["delitos_prueba"]
destino = db["delitos_formateados"]

# Limpia colección destino si quieres
destino.delete_many({})

# Obtener todos los documentos
registros = origen.find()

def formatear_cadena(valor):
    if isinstance(valor, str):
        return valor.strip().title()
    return valor

# Procesar e insertar
documentos = []
for r in registros:
    nuevo = {
        "delito": formatear_cadena(r.get("delito")),
        "municipio": formatear_cadena(r.get("municipio")),
        "anio": r.get("anio"),
        "mes_nombre": formatear_cadena(r.get("mes_nombre")),
        "dia": r.get("dia"),
        "colonia": formatear_cadena(r.get("colonia")),
        "calle": formatear_cadena(r.get("calle")),
        "forma_accion": formatear_cadena(r.get("forma_accion")),
        "fecha_completa": r.get("fecha_completa"),
        "ubicacion": r.get("ubicacion")
    }
    documentos.append(nuevo)

if documentos:
    destino.insert_many(documentos)
    print(f"Insertados {len(documentos)} documentos con formato normalizado.")
else:
    print("No se encontraron documentos para insertar.")

client.close()
