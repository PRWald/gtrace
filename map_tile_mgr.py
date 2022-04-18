import math
import os.path
import requests

# From <http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames>
# Given geo coordinates, return the OpenStreetMap tile X-Y numbers.
def deg2num(coords, zoom):
    lat_deg = coords[0]
    lon_deg = coords[1]
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return ([xtile, ytile])

# Returns lat/lon of NW corner of tile.
def num2deg(xtile, ytile, zoom):
  n = 2.0 ** zoom
  lon_deg = xtile / n * 360.0 - 180.0
  lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
  lat_deg = math.degrees(lat_rad)
  return ([lat_deg, lon_deg])

class map_tile_mgr(object):

    def __init__(self, url, cache, api_key, ignore_cache=False):
        self.tiles_url = url
        self.tiles_cache = cache
        self.api_key = api_key
        self.ignore_cache = ignore_cache
        print('ignore_cache = {}'.format(self.ignore_cache))

    def get_tile(self, zoom, x, y):
        tile_name = '{}-{}-{}.png'.format(zoom, x, y)
        tile_cache_full_path = '{}/{}'.format(self.tiles_cache, tile_name)

        if(self.ignore_cache or not os.path.isfile(tile_cache_full_path)):
            print('INFO: Downloading tile {} ...'.format(tile_name))
            tile_url = '{}/{}/{}/{}.png?apikey={}'.format(self.tiles_url, zoom, x, y, self.api_key)
            r = requests.get(tile_url)
            with open(tile_cache_full_path, 'wb') as f_img:
                for chunk in r.iter_content(100):
                    f_img.write(chunk)

        return(tile_cache_full_path)

    def get_tile_timestamp(self, zoom, x, y):
        tile_name = '{}-{}-{}.png'.format(zoom, x, y)
        tile_cache_full_path = '{}/{}'.format(self.tiles_cache, tile_name)
        
        tile_timestamp = None
        if(os.path.isfile(tile_cache_full_path)):
            tile_timestamp = os.path.getmtime(tile_cache_full_path)

        return(tile_timestamp)
