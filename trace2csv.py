#!/usr/bin/env python3

# TODO:
# Do statistical analysis on segments.
# Add progress meter.
# See if parallel processing would be faster.
# See if storing results in splite3 would be better.

import os
import argparse
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
    ap = argparse.ArgumentParser(description='Create csv data from Garmin trace files')
    ap.add_argument('-f', '--gps-files', help='Name of Garmin .tcx file', required=True, nargs='+')
    ap.add_argument('-w', '--waypoints-file', help='Name of waypoint .xml file')
    ap.add_argument('-i', '--waypoints-of-intr', help='Waypoint(s) of interest', nargs='*', default=[])
    ap.add_argument('-p', '--path-csv-file', help='Name of path csv file')
    ap.add_argument('-j', '--ignore-stored', help='Ignore previously stored data', action='store_true')
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

    gps_file_in_store = []
    path = {}
    if(args.path_csv_file):
        path_csv_file = args.path_csv_file
    else:
        if('path_csv_file' in rc.keys()):
            path_csv_file = rc['path_csv_file']
    if(os.path.isfile(path_csv_file)):
        with open(path_csv_file, 'r') as f_csv:
            for line in f_csv:
                (gps_file, activity_datestamp, path_id, dist_m, time_s) = line.strip().split(',')
                if((gps_file in args.gps_files) and args.ignore_stored):
                    continue
                (path_start, path_end) = path_id.split(':')

                if(path_start not in path.keys()):
                    path[path_start] = {}
                if(path_end not in path[path_start].keys()):
                    path[path_start][path_end] = []
                path[path_start][path_end].append({'gps_file': gps_file,
                        'activity_datestamp': activity_datestamp, 'dist_m': dist_m, 'time_s': time_s})

                if(gps_file not in gps_file_in_store):
                    gps_file_in_store.append(gps_file)

    for gps_file in args.gps_files:
        if((gps_file in gps_file_in_store) and not args.ignore_stored):
            print('Skipping %s because already in stored results.' % gps_file)
            continue

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
                path_id = '%s:%s' % (prev_id, wp_visited[dist]['id'])

                dist_m = dist - prev_dist

                time_s = wp_visited[dist]['time'] - prev_time

                print('%s,%s,%s,%s,%s' %
                        (gps_file, activity_datestamp, path_id, dist_m, time_s))

                (path_start, path_end) = path_id.split(':')

                if(path_start not in path.keys()):
                    path[path_start] = {}
                if(path_end not in path[path_start].keys()):
                    path[path_start][path_end] = []
                path[path_start][path_end].append({'gps_file': gps_file,
                        'activity_datestamp': activity_datestamp, 'dist_m': dist_m, 'time_s': time_s})

                prev_id = wp_visited[dist]['id']
                prev_name = wp_visited[dist]['name']
                prev_dist = dist
                prev_time = wp_visited[dist]['time']

        print(path)

        with open(path_csv_file, 'w') as f_csv:
            for path_start in path.keys():
                for path_end in path[path_start].keys():
                    for path_inst in path[path_start][path_end]:
                        f_csv.write('%s,%s,%s,%s,%s\n' %
                            (path_inst['gps_file'],
                             path_inst['activity_datestamp'],
                             "%s:%s" % (path_start, path_end),
                             path_inst['dist_m'],
                             path_inst['time_s']))
