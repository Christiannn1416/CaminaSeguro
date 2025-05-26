from flask import Flask, jsonify, request
from flask_cors import CORS
import osmnx as ox
import networkx as nx
import requests
import geopandas as gpd
from shapely.geometry import Point, LineString
import logging
from shapely.geometry import Point, LineString
from geopy.distance import geodesic

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

delitos = gpd.GeoDataFrame(delitos_json)
delitos["geometry"] = delitos["coordenadas"].apply(lambda u: Point(u["coordinates"]))
delitos.set_geometry("geometry", inplace=True)
delitos.set_crs(epsg=4326, inplace=True)
delitos = delitos.to_crs(epsg=3857)


# ------------------ CALCULAR RUTA MÁS SEGURA ------------------

def calcular_ruta_segura(G, origen_lat, origen_lon, destino_lat, destino_lon, modo):
    nodo_origen = ox.distance.nearest_nodes(G, origen_lon, origen_lat)
    nodo_destino = ox.distance.nearest_nodes(G, destino_lon, destino_lat)

    # Calcula la ruta más segura
    try:
        ruta = nx.shortest_path(G, nodo_origen, nodo_destino, weight='weight')
    except Exception as e:
        raise Exception(f"No se pudo calcular la ruta: {str(e)}")

    coordenadas = []
    distancia_total = 0

    for i in range(len(ruta) - 1):
        u, v = ruta[i], ruta[i + 1]

        # get_edge_data devuelve un diccionario con todas las aristas entre u y v
        edge_data = G.get_edge_data(u, v)
        if not edge_data:
            continue

        # Selecciona la arista con el menor peso (más segura y corta)
        edge = min(edge_data.values(), key=lambda e: e.get('weight', e.get('length', 1)))
        distancia = edge.get('length', 0)
        distancia_total += distancia

        # Geometría de la arista
        if 'geometry' in edge:
            coords = list(edge['geometry'].coords)
        else:
            coords = [(G.nodes[u]['x'], G.nodes[u]['y']), (G.nodes[v]['x'], G.nodes[v]['y'])]

        coordenadas.extend(coords)

    # Velocidades promedio por modo (m/s)
    velocidades = {"peatonal": 1.4, "bicicleta": 4.5, "vehículo": 13.8}
    velocidad = velocidades.get(modo, 1.4)
    tiempo_estimado = distancia_total / velocidad

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coordenadas
        },
        "properties": {
            "descripcion": f"Ruta más segura ({modo})",
            "distancia_m": round(distancia_total, 2),
            "tiempo_s": round(tiempo_estimado, 1)
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
