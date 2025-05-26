from pymongo import MongoClient

# Conexión
client = MongoClient("mongodb+srv://caminaseguro:bWbTAwKWxEFzgfQt@cluster0.oawj7sa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# Bases y colecciones
db = client["caminaseguro"]
coleccion_original = db["delitos_formateados"]
coleccion_colonias_calles = db["colonias_calles"]

# Limpia colección destino
coleccion_colonias_calles.delete_many({})

# Agrupa por colonia y calle, toma una coordenada por grupo
registros = coleccion_original.aggregate([
    {
        "$match": {
            "ubicacion.coordinates": {"$exists": True}
        }
    },
    {
        "$group": {
            "_id": {
                "colonia": "$colonia",
                "calle": "$calle"
            },
            "coordenada": { "$first": "$ubicacion.coordinates" }
        }
    }
])

# Construye estructura
estructura = {}

for r in registros:
    colonia = r["_id"]["colonia"]
    calle = r["_id"]["calle"]
    coord = r.get("coordenada")

    if colonia and calle and coord:
        if colonia not in estructura:
            estructura[colonia] = []
        estructura[colonia].append({
            "calle": calle,
            "ubicacion": {
                "type": "Point",
                "coordinates": coord
            }
        })

# Inserta
documentos = [{"colonia": c, "calles": v} for c, v in estructura.items()]
if documentos:
    coleccion_colonias_calles.insert_many(documentos)
    print(f"Insertadas {len(documentos)} colonias con sus calles y ubicaciones.")
else:
    print("No se encontraron registros válidos.")

client.close()
