import os
import math
import zipfile
import xml.etree.ElementTree as ET

ns = {'garmin': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}

class garmin(object):

    def __init__(self, trace_file):
        if(trace_file.lower().endswith('.zip')):
            zip_file = zipfile.ZipFile(trace_file)
            zip_trace_file = zip_file.open(os.path.basename(trace_file.replace('.zip', '.tcx')))
            self.trace = ET.parse(zip_trace_file)
        else:
            self.trace = ET.parse(trace_file)

    def get_activity_start_datestamp(self):
        id = self.trace.findall('.//garmin:Id', ns)[0].text
        # TODO: Convert to current time zone.
        return(id)

    def get_starting_coord(self):
        first_pos = self.trace.findall('.//garmin:Position', ns)[0]
        start_lat = first_pos.findall('garmin:LatitudeDegrees', ns)[0].text
        start_lon = first_pos.findall('garmin:LongitudeDegrees', ns)[0].text
        start_coord = [float(start_lat), float(start_lon)]
        return(start_coord)

    def get_bbox(self):
        gps_lat_N = None
        gps_lat_S = None
        gps_lon_W = None
        gps_lon_E = None
        for pos in self.trace.findall('.//garmin:LatitudeDegrees', ns):
            gps_lat = float(pos.text)
            if((gps_lat_N is None) or (gps_lat > gps_lat_N)):
                gps_lat_N = gps_lat
            if((gps_lat_S is None) or (gps_lat < gps_lat_S)):
                gps_lat_S = gps_lat

        for pos in self.trace.findall('.//garmin:LongitudeDegrees', ns):
            gps_lon = float(pos.text)
            if((gps_lon_W is None) or (gps_lon < gps_lon_W)):
                gps_lon_W = gps_lon
            if((gps_lon_E is None) or (gps_lon > gps_lon_E)):
                gps_lon_E = gps_lon

        return(gps_lat_N, gps_lon_W, gps_lat_S, gps_lon_E)

    def iter_position(self):
        for tp in self.trace.findall('.//garmin:Trackpoint', ns):
            yield(tp)

    def calc_elev_gain(self):
        total_gain = 0.0
        prev_alt = None
        for alt in self.trace.findall('.//garmin:AltitudeMeters', ns):
            if (prev_alt is not None):
                gain = float(alt.text) - float(prev_alt)
                if (gain > 0):
                    total_gain += gain
            prev_alt = alt.text
        return(total_gain)

    def get_trackpoint_count(self):
        trackpoints = self.trace.findall('.//garmin:Trackpoint', ns)
        return(len(trackpoints))

    def get_trackpoints(self):
        return(self.trace.findall('.//garmin:Trackpoint', ns))

    def deg2rad(self, x):
        return(math.pi * x / 180.0)

    def calc_dist_m(self, pt0, pt1):
        R = 6371
        delta_lat = self.deg2rad(pt1[0] - pt0[0])
        delta_lon = self.deg2rad(pt1[1] - pt0[1])
        lat0 = self.deg2rad(pt0[0])
        lat1 = self.deg2rad(pt1[0])
        a = math.pow(math.sin(delta_lat/2), 2) + math.pow(math.sin(delta_lon/2), 2) * math.cos(lat0) * math.cos(lat1)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        d = 1000.0 * R * c
        return(d)
