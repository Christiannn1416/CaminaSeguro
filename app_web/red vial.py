import osmnx as ox

# Cargar el grafo desde un archivo .graphml existente
G = ox.load_graphml("bike_celaya.graphml")

# Visualizar la red vial
ox.plot_graph(G)
