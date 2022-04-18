import xml.etree.ElementTree as ET
from map_tile_mgr import deg2num

class waypoint_mgr(object):

    def __init__(self, waypt_file):
        self.wptfile = waypt_file

    def read_waypoints(self, bbox=None):
        root = ET.parse(self.wptfile)
        data = {}
        for w in root.findall('.//wpt'):
            wptid = w.attrib['id']
            name = w.findall('name')[0].text
            lat = float(w.findall('lat')[0].text)
            lon = float(w.findall('lon')[0].text)
            if(bbox):
                if(lat > bbox[0]):
                    continue
                if(lat < bbox[2]):
                    continue
                if(lon < bbox[1]):
                    continue
                if(lon > bbox[3]):
                    continue
            elev = w.findall('elev_ft')[0].text
            if(elev):
                elev = int(elev)
            data[wptid] = {'name': name, 'lat': lat, 'lon': lon, 'elev_ft': elev}
        return(data)


    def get_tile_to_waypoint_map(self, zoom_factor):
        waypoints = self.read_waypoints()
        tile2wp = {}

        for wptid in waypoints.keys():
            tile = deg2num([waypoints[wptid]['lat'], waypoints[wptid]['lon']], zoom_factor)
            if(tile[0] not in tile2wp.keys()):
                tile2wp[tile[0]] = {}
            if(tile[1] not in tile2wp[tile[0]].keys()):
                tile2wp[tile[0]][tile[1]] = []
            tile2wp[tile[0]][tile[1]].append(wptid)

        return(tile2wp)

