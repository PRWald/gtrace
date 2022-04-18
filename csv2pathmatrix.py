#!/usr/bin/env python3

import os
import argparse
import dateutil.parser as DP
import waypoint_mgr

# TODO: Add option to use min, max, or avg times.
# TODO: Add option to print waypoint description.

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
    ap = argparse.ArgumentParser(description='Summarize raw paths data from .csv file.')
    ap.add_argument('-p', '--waypoints-file', help='Name of waypoint .xml file')
    ap.add_argument('-b', '--path-csv-file', help='Name of path csv file')
    ap.add_argument('-c', '--course-file', help='File containing list of waypoints in course')
    args = ap.parse_args()
    return(args)

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

    total_dist_m = {}
    total_time_s = {}
    path_id_cnts = {}
    if(os.path.isfile(path_csv_file)):
        with open(path_csv_file, 'r') as f_csv:
            for line in f_csv:
                (gps_file, activity_datestamp, path_id, dist_m, time_s) = line.strip().split(',')

                if(path_id not in path_id_cnts):
                    path_id_cnts[path_id] = 0
                path_id_cnts[path_id] += 1

                if(path_id not in total_dist_m):
                    total_dist_m[path_id] = 0
                total_dist_m[path_id] += float(dist_m)

                if(path_id not in total_time_s):
                    total_time_s[path_id] = 0
                total_time_s[path_id] += float(time_s)

    avg_dist_m = {}
    avg_time_s = {}
    for path_id in total_dist_m.keys():
        avg_dist_m[path_id] = total_dist_m[path_id] / path_id_cnts[path_id]
        avg_time_s[path_id] = total_time_s[path_id] / path_id_cnts[path_id]

    max_waypt = 0
    for path_id in total_dist_m.keys():
        (wpt1, wpt2) = path_id.split(':')
        wpt1 = int(wpt1[1:].strip())
        wpt2 = int(wpt2[1:].strip())
        if(wpt1 > max_waypt):
            max_waypt = wpt1
        if(wpt2 > max_waypt):
            max_waypt = wpt2
    for wpt1 in range(1, max_waypt+1):
        print('{:5s}: '.format('w%s' % wpt1), end='')
        for wpt2 in range(1, max_waypt+1):
            path_id = 'w%s:w%s' % (wpt1, wpt2)
            if(path_id in total_dist_m.keys()):
                print('w%s %3.2f %s (%s)  ' % 
                    (wpt2, m2mi(avg_dist_m[path_id]), s2minsec(avg_time_s[path_id]), path_id_cnts[path_id]), 
                    end='')
        print('')

