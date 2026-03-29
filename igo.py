import csv
from staticmap import StaticMap, CircleMarker
import collections
import networkx as nx  # Library used to work with graphs
import osmnx as ox  # Library used to download the graph of Barcelona
import collections  # Library used to be able to create tuples
import csv  # Library used to be able to read information in CSV format
import pickle  # Library used to store/load data
import urllib  # Library usedto be able to download files from the web
import staticmap as sm  # Library used to be able to paint in maps
import os.path  # Library used to check if we already have saved files or not
import time


PLACE = 'Barcelona, Catalonia'
GRAPH_FILENAME = 'barcelona.graph'
IGRAPH_FILENAME = 'barcelona.igraph'
SIZE = 800
HIGHWAYS_URL = 'https://opendata-ajuntament.barcelona.cat/data/dataset/1090983a-1c40-4609-8620-14ad49aae3ab/resource/1d6c814c-70ef-4147-aa16-a49ddb952f72/download/transit_relacio_trams.csv'
CONGESTIONS_URL = 'https://opendata-ajuntament.barcelona.cat/data/dataset/8319c2b1-4c21-4962-9acd-6db4c5ff1148/resource/2d456eb5-4ea6-4f68-9794-2f3f1a58a933/download'

Highway = collections.namedtuple('Highway', 'description coordinates')
Congestion = collections.namedtuple('Congestion', 'current_state expected_state')


def shortest_path(org, dest, need_igraph, image_name):
    """Returns an image with the shortest path between the origen point (org) and the destination point (dest) """
    # Get the graph and download the highways and the congestions

    graph = _get_graph(GRAPH_FILENAME)  # Get the Barcelona's graph implemented in the osmnx library

    highways = download_highways(HIGHWAYS_URL)
    congestions = 0  # if 5 minutes since the last download of the congestions have not gone by,
    # We will not need to download the congestions as the igraph wil already be calculated and saved
    if need_igraph:  # If we need to calculate the congestions, do so
        congestions = download_congestions(CONGESTIONS_URL)

    # Creates the igraph: a modification of the graph, it contains a new atribute named itime (it will be explained)
    # If we can still use the calculated previousy, simply load it from the pickle
    t1 = time.time()
    igraph = get_igraph(need_igraph, graph, highways, congestions)
    t2 = time.time()
    print("get_igraph", t2-t1)

    # Given a departure point (org) and an arrival point (dest) find the nearest point in the osmnx Barcelona's graph
    org = ox.distance.nearest_nodes(graph, org[0], org[1])  # departure point: longitude and latitude (tuple)
    dest = ox.distance.nearest_nodes(graph, dest[0], dest[1])  # arrival point: longitude and latitude
    print(org, dest)

    # Find the shortest path between the departure and arrival representatives points in the osmnx graph
    ipath = nx.shortest_path(igraph, org, dest, 'itime')

    # Downloads an image with the shortest path painted on it
    _plot_path(graph, ipath, SIZE, image_name)


# ---> STORING FUNCTIONS OF THE GRAPH <--- #

def _get_graph(filename):
    """Returns the osmnx graph of Barcelona, if it's already downloaded just loaded, otherwise, download it"""
    if not _exists_graph(filename):  # Checks wether the graph is already downloaded or not
        graph = _download_graph(PLACE)  # Download the graph
        completar_graph(graph)  # Before saving the graph, we'll complete it with missing atributes,
        # so this process only needs to be done once and optimizes the time it takes to assing all the values to the graph
        _save_graph(graph, filename)  # Keep the graph
    else:
        graph = _load_graph(filename)  # We have already downloaded the graph, save time, just load it

    return graph  # Returns the graph


def _exists_graph(filename):
    """Returns if the GRAPH_FILENAME graph (barcelona.graph) already exists"""

    return os.path.exists(filename)  # Function from the OS


def _download_graph(place):
    """Downloads the multigraph of the given place and converts the multigraph into a digraph"""
    # Downloads the multigraph
    multigraph = ox.graph_from_place(place, network_type='drive', simplify=True)
    # Keep it as a digraph
    digraph = ox.utils_graph.get_digraph(multigraph, weight='length')

    return digraph  # Returns the digraph


def _save_graph(graph, filename):
    """Saves the graph into a pickle"""
    # Commad for saving the graph
    with open(filename, 'wb') as file:
        pickle.dump(graph, file)


def _load_graph(filename):
    """ Loads the graph that has already been downloaded and saved into a pickle"""
    # Commad for loading the graph
    with open(filename, 'rb') as file:
        return pickle.load(file)


# ---> STORING FUNCTIONS OF HIGHWAYS AND CONGESTIONS <--- #

# It recives a list of strings which represents the coordinates of a tram
# We'll return the same list in floats, instead of returning pairs with longitude and latitude because it will make the "_build_igraph"
# function take considerably less time to be executed, as the heavy-time function "nearest_nodes" will be calculated only once
def str_to_flt(list_str):
    """Given a list of strings: returns the same list, though in floats instead of strings"""

    list_flt = []  # Empty list, it will contain the float coordinates

    for i in list_str:
        list_flt.append(float(i))
    return list_flt


# Downloads highways and returs a map of highway
# Highway information: way_id and Highway tuple
def download_highways(url):
    """Downloads the given highways and return them in a dictionary: key - highway's id, value pair - Tuple Highway which contains it's description and a list of coordinates"""
    with urllib.request.urlopen(url) as response:
        lines = [l.decode('utf-8') for l in response.readlines()]
        reader = csv.reader(lines, delimiter=',', quotechar='"')
        next(reader)  # ignore first line with description

        highways = {}
        # map: id and highway tuple, each position represents a tram (information)

        for line in reader:
            way_id, description, coordinates = line
            # way_id: tram
            # description: name of the tram
            # coordinates: coordinates(lan, lat)
            highway = {way_id: Highway(description, str_to_flt(coordinates.split(',')))}
            # converts each coordinate of the list of string coordinates into a float and pair longitude and latitude of each point
            # reads the information of each tram and sorts each tram by its id

            highways.update(highway)

        return highways


# Downloads all the congestions and stores them into a map
# Congestion information:
def download_congestions(url):
    """Downloads all the congestions and stores them into a dictionary: key - highway's id, value pair - Tuple Congestion which contains it's current state and the expected one"""
    with urllib.request.urlopen(url) as response:
        lines = [l.decode('utf-8') for l in response.readlines()]
        reader = csv.reader(lines, delimiter='#', quoting=csv.QUOTE_NONE)

        congestions = {}
        for line in reader:
            way_id, date, current_state, expected_state = line
            congestion = {way_id: Congestion(current_state, expected_state)}
            congestions.update(congestion)

        return congestions


# ---> PLOTS <--- #

def plot_highways(highways, size):
    """Returns an image of Bcn with the trams given by the HIGHWAYS_URL painted on it"""
    m_bcn = StaticMap(size, size)

    # iterate for each tram given by the highways url
    for key in highways:

        coords = highways[key].coordinates

        # For each coordenate pair
        for i in range(2, len(coords), 2):
            # Paint the highway as a red line
            m_bcn.add_line(sm.Line(((coords[i-2], coords[i-1]), (coords[i], coords[i+1])), 'red', 3))

    image = m_bcn.render()
    image.save('highways.png')


def plot_congestions(highways, congestions, size):
    """Returns an image of Bcn with the highways given by the CONGESTIONS_URL and the colors which corresponds acording to the function define color"""
    m_bcn = StaticMap(size, size)
    for key in highways:
        # Paint the tram with the corresponding color
        color = define_color(key, congestions[key])
        # Draw the line
        line = sm.Line((highways[key].coordinates), color, 1)
        m_bcn.add_line(line)

        # generates an image with the trams painted
    image = m_bcn.render()
    image.save('congestions.png')


# Atributes a color to each congestions grade
def define_color(way_id, congestion):
    """ Atributes a color to each congestions grade"""
    if congestion.current_state == '0':
        return 'white'
    elif congestion.current_state == '1':
        return '#33ff7c'
    elif congestion.current_state == '2':
        return '#13d2bc'
    elif congestion.current_state == '3':
        return '#e9ff00'
    elif congestion.current_state == '4':
        return '#ff5500'
    elif congestion.current_state == '5':
        return '#ff0004'
    else:
        return 'black'


def _plot_path(graph, path, size, image_name):
    """ Downloads a map image with the path given painted on it"""

    # Creates the bcn map
    m_bcn = sm.StaticMap(size, size)
    first = True

    # path parameter: list of osmnx graph nodes
    for node in path:

        if first:
            # necessary for the first time, for painting a path we need the origine point and the arrival, firstly we just have one node
            first = False
        else:

            lon0 = graph.nodes[node_anterior]['x']  # Origine node
            lat0 = graph.nodes[node_anterior]['y']
            lon1 = graph.nodes[node]['x']  # Arrival node
            lat1 = graph.nodes[node]['y']

            m_bcn.add_line(sm.Line(((float(lon0), float(lat0)), (float(lon1), float(lat1))), '#0091ff', 3))

        node_anterior = node

    image = m_bcn.render()
    image.save(image_name)  # Saves the image


# ---> IGRAPH <--- #

def get_igraph(need_igraph, graph, highways, congestions):
    """Returns the igraph completed and ready to calculate the shortest path"""
    if need_igraph:  # If we need to calculkate it again, do so and save it in the pickle
        igraph = _build_igraph(graph, highways, congestions)
        with open(IGRAPH_FILENAME, 'wb') as file:
            pickle.dump(igraph, file)
    else:  # If we do not need to calculate it because the congestions have not been updated, load the previously calculated one from the pickle
        with open(IGRAPH_FILENAME, 'rb') as file:
            igraph = pickle.load(file)
    return igraph  # returns the igraph


def calculating_itime(graph, node1, node2, congestion):
    """Defines the new edge atribut (from node1 to node2) of the osmnx graph itime, it contributs to calculate the shortest path between two points of the graph"""

    speed = graph[node1][node2].get('maxspeed', None)
    length = graph[node1][node2].get('length', None)

    if type(speed) == list:  # The speed of the edge (node1-node2) we are calculating is given by a list of speeds
        speed = (float(speed[0])+float(speed[1]))/2  # We decide to use the average of speeds

    if speed is None:  # There's no maxspeed atribute
        speed = calcular_speed(node1, node2, graph)  # Calculate a logical speed for the street

    time = float(length)/float(speed)

    if congestion == str(6):  # Congestion level 6 means the tram is not accessible, we can't drive along this tram
        itime = float('inf')  # We add a infinit weight, so this tram will never be the shortest

    elif congestion == str(0):  # congestion level 0 means there's no information
        itime = time * 2.5  # 2.5 it's the average between molt fluit i dens

    else:
        itime = time * int(congestion)  # The lower it is, the fastest is the tram

    return itime  # Return the itime value


def _build_igraph(graph, highways, congestions):
    """It takes the osmnx barcelona graph and returns it with current_time speed value for its main highways"""

    for key in highways:  # We'll go over all the highways we have data on and add the "itme" value (combination od speed and congestion) to te main highways of the graph

        congestions_state = congestions[key].current_state

        lon_list = highways[key].coordinates[::2]  # Llist of longitudes
        lat_list = highways[key].coordinates[1::2]  # Llist of latitudes

        # Returns a list of every node that makes up the highway
        nodes_list = ox.distance.nearest_nodes(graph, lon_list, lat_list)

        # We'll look for te shortest path between every pair of nodes that make up the highway and add the itime value to its edge
        origin_node = nodes_list[0]
        for i in range(len(nodes_list)-1):
            destination_node = nodes_list[i+1]

            # Try will be executed if the "nx.shortest_path" function can be completed
            try:
                # This returns the list of nodes which make the shortest path from the origin to the final point of the street
                path = nx.shortest_path(graph, origin_node, destination_node)

                # We'll iterate for every pair of the nodes that make up the path
                n1 = path[0]
                for i in range(len(path)-1):

                    n2 = path[i+1]
                    # Calculates the itime of an edge
                    itime = calculating_itime(graph, n1, n2, congestions_state)
                    # The itime is added to the graphs edge
                    graph[n1][n2]['itime'] = itime

                    n1 = n2
            # If there is no path, pass
            except:
                pass

            origin_node = destination_node

    # returns the graph
    return graph


# To be able to have an itime value to all the graph, not only in the main highways, an estimated
# itime value is added tp every edge of the graph
def completar_graph(graph):
    """Returns the graph with an estimated itime value for every edge in it"""
    # Creates an itime value initialized to 0 for every edge on the graph
    nx.set_edge_attributes(graph, 0, 'itime')

    for node1, info1 in graph.nodes.items():
        # for each adjacent node and its information
        for node2, edge in graph.adj[node1].items():

            # A congestion is assigned taking into account the type of street it is
            congestion = calcular_congestio(node1, node2, graph)
            # The itime of the edge is calculated and assigned
            graph[node1][node2]['itime'] = calculating_itime(graph, node1, node2, congestion)


# ---> ESTIMATED CALCULATIONS ON SPEED AND CONGESTION <--- #

def calcular_speed(node1, node2, graph):
    """Returns a properly estimated speed value taking into account the streets features"""
    # The type of higway is acquired
    street_type = graph[node1][node2].get('highway', None)
    # Depending on the street type, we'll assign its corresponding speed
    if street_type == 'primary' or 'primary_link':
        speed = '50'
    elif street_type == 'secondary' or 'secondary_link':
        speed = '40'
    elif street_type == 'terciary' or 'terciary_link':
        speed = '35'
    elif street_type == 'residential' or 'living_street':
        speed = '30'
    elif street_type == 'trunk' or 'trunk_link':
        speed = '100'
    else:
        speed = '40'  # Average between 30 and 50

    return speed


def calcular_congestio(node1, node2, graph):
    """Returns a properly estimated congestion  value taking into account the streets features"""
    # The type of higway is acquired
    street_type = graph[node1][node2].get('_plot_one_highway', None)
    # Depending on the street type, we'll assign its corresponding congestion
    if street_type == 'primary' or 'primary_link':
        congestion = '1'
    elif street_type == 'secondary' or 'secondary_link':
        congestion = '2'
    elif street_type == 'terciary' or 'terciary_link':
        congestion = '3'
    elif street_type == 'residential' or 'living_street':
        congestion = '3'
    elif street_type == 'trunk' or 'trunk_link':
        congestion = '1'
    else:
        congestion = '2.5'  # Average between 30 and 50

    return congestion


# ---> BOT FUNCTIONS <--- #

def start_system():
    """Downloads the graph if it has not been saved yet"""
    # If the graph does not exist, download it, complete it and save it
    if not _exists_graph(GRAPH_FILENAME):
        graph = _download_graph(PLACE)
        completar_graph(graph)
        save_graph(graph)


def show_position(lon, lat, image_name):
    """Saves an image of Barcelona with a marker on top of the location provided"""

    # The map is created with its corresponding size
    m_bcn = sm.StaticMap(SIZE, SIZE)

    # The marker is added
    marker_outline = sm.CircleMarker((lon, lat), 'white', 30)
    marker = sm.CircleMarker((lon, lat), 'blue', 22)
    m_bcn.add_marker(marker_outline)
    m_bcn.add_marker(marker)

    # The image is saved with its corresponding name
    image = m_bcn.render()
    image.save(image_name)


def translate_direction(direction):
    """returns the longitude and latitude coordenates from the name of a street or place"""

    return ox.geocoder.geocode(direction)
