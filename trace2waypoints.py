#!/usr/bin/env python3

# Get a list of waypoints for each trace file given.
# Use parallelism (e.g., divide the trace file into the number of available
# CPUs or threads and allow parallel analysis).

import os
import argparse
import garmin
import waypoint_mgr
import multiprocessing as mp

ns = {'garmin': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
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
    ap = argparse.ArgumentParser(description='Get a list of waypoints for each trace file given')
    ap.add_argument('-f', '--gps-files', help='Name of Garmin .tcx file', required=True, nargs='+')
    ap.add_argument('-w', '--waypoints-file', help='Name of waypoint .xml file')
    args = ap.parse_args()
    return(args)

def extract_waypoints_from_trace(job):
    gt = job[0]
    waypoints = job[1]
    wp_chain = []
    for tp in gt.iter_position():
        try:
            lat = float(tp.findall('.//garmin:LatitudeDegrees', ns)[0].text)
            lon = float(tp.findall('.//garmin:LongitudeDegrees', ns)[0].text)
        except IndexError:
            continue
        for k in waypoints.keys():
            wp_lat = waypoints[k]['lat']
            wp_lon = waypoints[k]['lon']
            wp_id = k
            wp_name = waypoints[k]['name']
            sep_m = gt.calc_dist_m([lat, lon], [wp_lat, wp_lon])
            if(sep_m < 20.0):
                if(len(wp_chain) == 0):
                    wp_chain.append(wp_id)
                else:
                    if(wp_id != wp_chain[-1]):
                        wp_chain.append(wp_id)
    return(wp_chain)


if(__name__ == '__main__'):
    args = parse_cmd_line()

    rc = read_rc_file()

    if(args.waypoints_file):
        waypoints_file = args.waypoints_file
    else:
        if('waypoints_file' in rc.keys()):
            waypoints_file = rc['waypoints_file']

    w_mgr = waypoint_mgr.waypoint_mgr(waypoints_file)

#    jobs = []
    for gps_file in args.gps_files:
        try:
            gt = garmin.garmin(gps_file)
        except KeyError:
            continue

        waypoints = w_mgr.read_waypoints(gt.get_bbox())
        if(len(waypoints) > 0):
#            jobs.append((gt, waypoints))

            print('%s :' % gps_file)
            wp_chain = extract_waypoints_from_trace((gt, waypoints))
            for wp_id in wp_chain:
                print(wp_id)
            print()


#    print('DEBUG: Number of jobs = %d' % len(jobs))
#    with mp.Pool(8) as pool:
#        pool.map(extract_waypoints_from_trace, jobs)
