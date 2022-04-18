#!/usr/bin/env python3

# TODO: Determine closest waypoint to starting point of each trace.

import argparse
import garmin
import waypoint_mgr

def parse_cmd_line():
    ap = argparse.ArgumentParser(description='Show various stats about traces.')
    ap.add_argument('-f', '--gps-files', help='Name of Garmin .tcx file(s) to process', required=True, nargs='+')
    ap.add_argument('-w', '--waypoint', help='Waypoint ID')
    args = ap.parse_args()
    return(args)

if(__name__ == '__main__'):
    args = parse_cmd_line()

    w = waypoint_mgr.waypoint_mgr('/home/common/paulw/hobbies/running/garmin-traces/waypoints.xml')
    waypoints = w.read_waypoints()

    for gps_file in args.gps_files:
#        print('INFO: Processing file {} ...'.format(gps_file))
        gt = garmin.garmin(gps_file)
        starting_pt = gt.get_starting_coord()
        min_dist = None
        min_dist_wptid = None
        for wptid in waypoints.keys():
            wp_coord = (waypoints[wptid]['lat'], waypoints[wptid]['lon'])
            dist = gt.calc_dist_m(starting_pt, wp_coord)
            if((min_dist is None) or (dist < min_dist)):
                min_dist = dist
                min_dist_wptid = wptid
        if((args.waypoint) and (args.waypoint == min_dist_wptid)):
            print('INFO: {} min_dist = {} at waypoint {}'.format(gps_file, min_dist, min_dist_wptid))
        else:
            print('INFO: {} min_dist = {} at waypoint {}'.format(gps_file, min_dist, min_dist_wptid))


