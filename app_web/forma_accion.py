from pymongo import MongoClient

# Conexión a tu base de datos (ajusta con tu URI de MongoDB Atlas o local)
client = MongoClient("mongodb+srv://caminaseguro:bWbTAwKWxEFzgfQt@cluster0.oawj7sa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# Selecciona base de datos y colecciones
db = client["caminaseguro"]
coleccion_origen = db["delitos"]  # Colección original con los incidentes
coleccion_tipos = db["forma_accion"]  # Nueva colección para tipos de delito

# Obtener todos los tipos de delito únicos usando aggregate
registros = coleccion_origen.aggregate([
    {
        "$group": {
            "_id": { "forma_accion": "$forma_accion" }
        }
    }
])

# Construir documentos
documentos = []
for r in registros:
    forma_accion = r["_id"]["forma_accion"]
    if forma_accion:  # Filtrar valores vacíos o nulos
        documentos.append({ "forma_accion": forma_accion })

# Eliminar colección destino antes de insertar (opcional)
coleccion_tipos.delete_many({})

# Insertar documentos si hay datos válidos
if documentos:
    coleccion_tipos.insert_many(documentos)
    print(f"Se insertaron {len(documentos)} forma_accion.")
else:
    print("No se encontraron forma_accion.")

# Cerrar conexión
client.close()