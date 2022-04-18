#!/usr/bin/env python3

import os
import argparse
import statistics
import dateutil.parser as DP
import waypoint_mgr

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
    ap.add_argument('-w', '--waypoints-file', help='Name of waypoint .xml file')
    ap.add_argument('-p', '--path-csv-file', help='Name of path csv file')
    ap.add_argument('-c', '--course-file', help='File containing list of waypoints in course')
    args = ap.parse_args()
    return(args)

def m2mi(d):
    return(d / 1609.0)

def s2hms(t):
    hr = int(t / 3600.0)
    t = t - 3600.0 * hr
    min = int(t / 60.0)
    sec = int(t - 60.0 * min)
    return('{}:{:02d}:{:02d}'.format(hr, min, sec))

if(__name__ == '__main__'):
    args = parse_cmd_line()

    rc = read_rc_file()

    if(args.waypoints_file):
        waypoints_file = args.waypoints_file
    else:
        if('waypoints_file' in rc.keys()):
            waypoints_file = rc['waypoints_file']

    w_mgr = waypoint_mgr.waypoint_mgr(waypoints_file)
    wpts = w_mgr.read_waypoints()

    if(args.path_csv_file):
        path_csv_file = args.path_csv_file
    else:
        if('path_csv_file' in rc.keys()):
            path_csv_file = rc['path_csv_file']

    pop_dist_m = {}
    pop_time_s = {}
    if(os.path.isfile(path_csv_file)):
        with open(path_csv_file, 'r') as f_csv:
            for line in f_csv:
                (gps_file, activity_datestamp, path_id, dist_m, time_s) = line.strip().split(',')
                dist_m = float(dist_m)
                time_s = float(time_s)

                if(path_id not in pop_dist_m.keys()):
                    pop_dist_m[path_id] = []
                    pop_time_s[path_id] = []
                pop_dist_m[path_id].append(dist_m)
                pop_time_s[path_id].append(time_s)


    course = []
    if(args.course_file):
        with open(args.course_file, 'r') as f_c:
            for l in f_c:
                course.append(l.strip())

    median_dist_m = {}
    median_time_s = {}
    for path_id in pop_dist_m.keys():
        median_dist_m[path_id] = statistics.median_low(pop_dist_m[path_id])
        median_time_s[path_id] = statistics.median_low(pop_time_s[path_id])

        if(not args.course_file):
            print('%s %3.2f mi %s min (%s)' %
		        (path_id, m2mi(median_dist_m[path_id]), s2hms(median_time_s[path_id]), len(pop_dist_m[path_id])))

    course_dist_m = 0
    course_time_s = 0
    wpt_prev = None
    for wpt in course:
        if(wpt_prev):
            path_id = '%s:%s' % (wpt_prev, wpt)
            rev_path_id = '%s:%s' % (wpt, wpt_prev)
            if(path_id in pop_dist_m.keys()):
                course_dist_m += median_dist_m[path_id]
                course_time_s += median_time_s[path_id]
                print('[%-4s] %-40s %5.2f %s' % (wpt, wpts[wpt]['name'], m2mi(course_dist_m), s2hms(course_time_s)))
            elif(rev_path_id in pop_dist_m.keys()):
                course_dist_m += median_dist_m[rev_path_id]
                course_time_s += median_time_s[rev_path_id]
                print('[%-4s] %-40s %5.2f %s *' % (wpt, wpts[wpt]['name'], m2mi(course_dist_m), s2hms(course_time_s)))
            else:
                print('ERROR: Missing data')
        else:
            print('[%-4s] %-40s  0.00 0:00:00' % (wpt, wpts[wpt]['name']))
        wpt_prev = wpt

# TODO: Add option to print data in matrix form.
