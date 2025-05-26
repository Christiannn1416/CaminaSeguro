from pymongo import MongoClient

# Conexión a tu base de datos (ajusta con tu URI de MongoDB Atlas o local)
client = MongoClient("mongodb+srv://caminaseguro:bWbTAwKWxEFzgfQt@cluster0.oawj7sa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# Selecciona base de datos y colecciones
db = client["caminaseguro"]
coleccion_origen = db["delitos_formateados"]  # Colección original con los incidentes
coleccion_tipos = db["tipos_delitos"]  # Nueva colección para tipos de delito

# Obtener todos los tipos de delito únicos usando aggregate
registros = coleccion_origen.aggregate([
    {
        "$group": {
            "_id": { "tipo_delito": "$delito" }
        }
    }
])

# Construir documentos
documentos = []
for r in registros:
    tipo_delito = r["_id"]["tipo_delito"]
    if tipo_delito:  # Filtrar valores vacíos o nulos
        documentos.append({ "tipo_delito": tipo_delito })

# Eliminar colección destino antes de insertar (opcional)
coleccion_tipos.delete_many({})

# Insertar documentos si hay datos válidos
if documentos:
    coleccion_tipos.insert_many(documentos)
    print(f"Se insertaron {len(documentos)} tipos de delito.")
else:
    print("No se encontraron tipos de delito.")

# Cerrar conexión
client.close()