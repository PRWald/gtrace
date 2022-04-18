#!/usr/bin/env python3

# TODO:
# Do statistical analysis on segments.
# Add a .dot output option.
# Add progress meter.

import os
import math
import argparse
import xml.etree.ElementTree as ET
import dateutil.parser as DP
import garmin
import waypoint_mgr
from garmin import ns

rc_file = '{}/.trace.rc'.format(os.environ['HOME'])

def read_rc_file():
    rc = {}
    if(os.path.exists(rc_file)):
        with open(rc_file, 'r') as f_rc:
            for l in f_rc:
                if(l[0] == '#'):
                    continue
                (a, b) = l.split('=')
                rc[a.strip()] = b.strip()
    return(rc)

def parse_cmd_line():
    ap = argparse.ArgumentParser(description='Explore GPS trace on opencyclemap.org tiles')
    ap.add_argument('-f', '--gps-files', help='Name of Garmin .tcx file', required=True, nargs='+')
    ap.add_argument('-d', '--dot-file', help='Name of .dot output file')
    ap.add_argument('-p', '--waypoints-file', help='Name of waypoint .xml file')
    ap.add_argument('-w', '--waypoints-of-intr', help='Waypoint(s) of interest', nargs='*', default=[])
    ap.add_argument('-b', '--path-csv-file', help='Name of path csv file')
    args = ap.parse_args()
    return(args)

def iso2epoch(t_iso):
    return(int(DP.parse(t_iso).strftime('%s')))

def m2mi(d):
    return(d / 1609.0)

def s2minsec(t):
    min = int(t / 60.0)
    sec = int(t - 60.0 * min)
    return('{}:{:02d}'.format(min, sec))

if(__name__ == '__main__'):
    args = parse_cmd_line()

    rc = read_rc_file()

    if(args.waypoints_file):
        waypoints_file = args.waypoints_file
    else:
        if('waypoints_file' in rc.keys()):
            waypoints_file = rc['waypoints_file']

    w_mgr = waypoint_mgr.waypoint_mgr(waypoints_file)

    if(args.path_csv_file):
        path_csv_file = args.path_csv_file
    else:
        if('path_csv_file' in rc.keys()):
            path_csv_file = rc['path_csv_file']

# TODO: repopulate paths dictionary, if path_csv_file exists.
    paths = {}

    for gps_file in args.gps_files:
        print('INFO: Working on %s ...' % gps_file)

        try:
            gt = garmin.garmin(gps_file)
        except KeyError:
            continue

        waypoints = w_mgr.read_waypoints(gt.get_bbox())
        print('DEBUG: num waypoints = {}'.format(len(waypoints)))
        if(len(waypoints) == 0):
            continue

        # Check for desired waypoints to exist in the current trace file.
        if(len(args.waypoints_of_intr) > 0):
            intr_wp_seen = False
            for woi in args.waypoints_of_intr:
                if(woi in waypoints):
                    intr_wp_seen = True
                    break
            if(not intr_wp_seen):
                continue

        num_trackpoints = gt.get_trackpoint_count()
        print('DEBUG: {} track points'.format(num_trackpoints))

        activity_datestamp = gt.get_activity_start_datestamp()
        print('DEBUG: Activity date = %s' % activity_datestamp)

        # Go through all track points and check for proximity to points in the waypoint database.
        wp_visited = {}
        for tp in gt.iter_position():
            time = iso2epoch(tp.findall('.//garmin:Time', ns)[0].text)
            try:
                lat = float(tp.findall('.//garmin:LatitudeDegrees', ns)[0].text)
                lon = float(tp.findall('.//garmin:LongitudeDegrees', ns)[0].text)
            except IndexError:
                continue
            dist = float(tp.findall('.//garmin:DistanceMeters', ns)[0].text)
            for k in waypoints.keys():
                wp_lat = waypoints[k]['lat']
                wp_lon = waypoints[k]['lon']
                wp_id = k
                wp_name = waypoints[k]['name']
                sep_m = gt.calc_dist_m([lat, lon], [wp_lat, wp_lon])
                if(sep_m < 20.0):
                    wp_visited[dist] = {'id': wp_id, 'name': wp_name, 'time': time}

        prev_name = None
        for dist in sorted(wp_visited.keys()):
            if(not prev_name):
                prev_id = wp_visited[dist]['id']
                prev_name = wp_visited[dist]['name']
                prev_dist = dist
                prev_time = wp_visited[dist]['time']
                continue
            if(wp_visited[dist]['name'] != prev_name):
                path = {}
                path_id = '%s:%s' % (prev_id, wp_visited[dist]['id'])

                delta_dist = dist - prev_dist
                path['dist'] = delta_dist

                delta_time = wp_visited[dist]['time'] - prev_time
                path['time'] = delta_time

                path['file'] = gps_file
                path['date'] = activity_datestamp

#                print('{} {:32s} -> {:32s} {:3.2f} mi {:5s} {}'.format(
#                    path_id, prev_name, wp_visited[dist]['name'], m2mi(delta_dist),
#                    s2minsec(delta_time), gps_file))
                print('%s,%s,%s,%s,%s' %
                        (gps_file, activity_datestamp, path_id, delta_dist, delta_time))

                if(path_id not in paths.keys()):
                    paths[path_id] = []
                paths[path_id].append(path)

                prev_id = wp_visited[dist]['id']
                prev_name = wp_visited[dist]['name']
                prev_dist = dist
                prev_time = wp_visited[dist]['time']

    for path_id in paths.keys():
        total_dist = 0.0
        print('path_id = %s, number of data = %d' % (path_id, len(paths[path_id])), end='')
        for path in paths[path_id]:
            total_dist += path['dist']
        avg_dist = total_dist / len(paths[path_id])
        print(' Avg dist = %f m (%3.2f miles)' % (avg_dist, avg_dist / 1609))

    if(args.dot_file is not None):
        with open(args.dot_file, 'w') as f_dot:
            f_dot.write('digraph G {\n');
            for path_id in paths.keys():
                total_dist = 0.0
                for path in paths[path_id]:
                    total_dist += path['dist']
                avg_dist = total_dist / len(paths[path_id])
                ep = path_id.split(':')
                f_dot.write('%s -> %s [label="%3.2f", len="%d"];\n' %
                        (ep[0], ep[1], avg_dist/1609, int(1+avg_dist)))
            f_dot.write('}\n');

# Do some stats on path data (dist and time) and print out.

