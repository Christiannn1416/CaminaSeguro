from flask import Flask, jsonify, request
from flask_cors import CORS
import osmnx as ox
import networkx as nx
import requests
import geopandas as gpd
import logging
from shapely.geometry import Point, LineString

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# ------------------ CARGAR GRAFOS ------------------

print("Cargando grafos...")
G_walk = ox.load_graphml('walk_celaya.graphml')
G_drive = ox.load_graphml('drive_celaya.graphml')
G_bike = ox.load_graphml('bike_celaya.graphml')

# ------------------ CARGAR DELITOS ------------------

print("Cargando delitos y calculando peligrosidad...")
try:
    delitos_resp = requests.get("http://localhost:5000/api/calles")
    delitos_json = delitos_resp.json()["data"]
except Exception as e:
    raise RuntimeError("No se pudo cargar el JSON de delitos: " + str(e))

# Crear GeoDataFrame con los delitos
delitos = gpd.GeoDataFrame(delitos_json)
delitos["geometry"] = delitos["coordenadas"].apply(lambda u: Point(u["coordinates"]))
delitos.set_geometry("geometry", inplace=True)
delitos.set_crs(epsg=4326, inplace=True)
delitos = delitos.to_crs(epsg=3857)

# Crear diccionario de peligrosidad por nombre de calle
zonas_peligrosas_cercanas = {}
for item in delitos_json:
    calle = item.get("calle", "").strip().lower()
    nivel = item.get("nivel_peligro")
    if calle:
        zonas_peligrosas_cercanas[calle] = nivel

# ------------------ FUNCIONES ------------------

def detectar_peligros_en_ruta(linea_ruta, zonas, radio_alerta=30):
    zonas_peligrosas = []
    for zona in zonas:
        if zona["nivel_peligro"] in ["Medio", "Alto"]:
            lat, lon = zona["coordenadas"]["coordinates"][1], zona["coordenadas"]["coordinates"][0]
            punto = Point(lon, lat)
            if linea_ruta.distance(punto) * 111000 < radio_alerta:
                zonas_peligrosas.append(zona["calle"].strip().lower())
    return zonas_peligrosas

def calcular_ruta_segura(G, origen_lat, origen_lon, destino_lat, destino_lon, modo):
    nodo_origen = ox.distance.nearest_nodes(G, origen_lon, origen_lat)
    nodo_destino = ox.distance.nearest_nodes(G, destino_lon, destino_lat)
    ruta = nx.shortest_path(G, nodo_origen, nodo_destino, weight='weight')

    coordenadas = []
    distancia_total = 0
    calles_peligrosas = set()

    for i in range(len(ruta) - 1):
        u, v = ruta[i], ruta[i + 1]
        edge_data = G.get_edge_data(u, v) or G.get_edge_data(v, u)
        if not edge_data:
            continue

        edge = list(edge_data.values())[0]
        distancia = edge.get('length', 0)
        distancia_total += distancia

        # Coordenadas
        if 'geometry' in edge:
            coords = list(edge['geometry'].coords)
        else:
            coords = [(G.nodes[u]['x'], G.nodes[u]['y']), (G.nodes[v]['x'], G.nodes[v]['y'])]
        coordenadas.extend(coords)

        # Verificar nombre de calle
        name = edge.get("name")
        if isinstance(name, list):
            name = name[0]
        if name:
            name_lower = name.strip().lower()
            nivel = zonas_peligrosas_cercanas.get(name_lower)
            if nivel in ["Medio", "Alto"]:
                calles_peligrosas.add(name_lower)

    # Verificar proximidad a puntos peligrosos
    linea_ruta = LineString(coordenadas)
    calles_proximas = detectar_peligros_en_ruta(linea_ruta, delitos_json)
    calles_peligrosas.update(calles_proximas)

    velocidades = {"peatonal": 1.4, "bicicleta": 4.5, "vehículo": 13.8}
    velocidad = velocidades.get(modo, 1.4)
    tiempo_estimado = distancia_total / velocidad

    alerta_texto = ""
    if calles_peligrosas:
        alerta_texto = "Se detectaron zonas peligrosas en la ruta: " + ", ".join(sorted(calles_peligrosas))

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coordenadas
        },
        "properties": {
            "descripcion": f"Ruta más segura ({modo})",
            "distancia_m": distancia_total,
            "tiempo_s": tiempo_estimado,
            "alerta": alerta_texto
        }
    }

# ------------------ ENDPOINTS ------------------

@app.route('/ruta_segura_walk', methods=['GET'])
def ruta_walk():
    try:
        lat_o = float(request.args.get('origen_lat'))
        lon_o = float(request.args.get('origen_lon'))
        lat_d = float(request.args.get('destino_lat'))
        lon_d = float(request.args.get('destino_lon'))

        geojson = calcular_ruta_segura(G_walk, lat_o, lon_o, lat_d, lon_d, "peatonal")
        return jsonify(geojson)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ruta_segura_drive', methods=['GET'])
def ruta_drive():
    try:
        lat_o = float(request.args.get('origen_lat'))
        lon_o = float(request.args.get('origen_lon'))
        lat_d = float(request.args.get('destino_lat'))
        lon_d = float(request.args.get('destino_lon'))

        geojson = calcular_ruta_segura(G_drive, lat_o, lon_o, lat_d, lon_d, "vehículo")
        return jsonify(geojson)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ruta_segura_bike', methods=['GET'])
def ruta_bike():
    try:
        lat_o = float(request.args.get('origen_lat'))
        lon_o = float(request.args.get('origen_lon'))
        lat_d = float(request.args.get('destino_lat'))
        lon_d = float(request.args.get('destino_lon'))

        geojson = calcular_ruta_segura(G_bike, lat_o, lon_o, lat_d, lon_d, "bicicleta")
        return jsonify(geojson)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ MAIN ------------------

if __name__ == "__main__":
    app.run(port=5050, debug=True)
