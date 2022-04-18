#!/usr/bin/env python3
# $Id: plot-gps-traces.py,v 1.2 2017/01/16 06:06:44 paulw Exp paulw $
# Paul R. Woods, Corvallis, Oregon

# TODO: Add pool to process layers in parallel.
# TODO: Add options for plotting dist tics, time tics, stops, min/max elev, etc.
# TODO: Add option for accepting a list of photos, extract GPS info, and plot location of photos on map.

import os
import time
import math
import argparse
import colorsys
import requests
import subprocess
import extract_exif_gps
import garmin
import map_tile_mgr
import waypoint_mgr
from map_tile_mgr import deg2num, num2deg
from garmin import ns

alpha = 0.6
rc_file = '{}/.trace.rc'.format(os.environ['HOME'])

def parse_cmd_line():
    ap = argparse.ArgumentParser(description='Trace gps trace(s) onto base map.')
    ap.add_argument('-f', '--gps-file',
            help='Name of Garmin .tcx file(s) to process. Can also be .zip containing .tcx of same base name.',
            nargs='*', default=[])
    ap.add_argument('-i', '--images', help='List of geo-tagged jpg images', nargs='*')
    ap.add_argument('-z', '--zoom-factor', help='Zoom factor', type=int, default=16)
    ap.add_argument('-t', '--tiles-url', help='URL to tile server',
            default='https://tile.thunderforest.com/cycle')
    ap.add_argument('-c', '--tile-cache', help='Directory where downloaded tiles are stored locally.',
            default='tile-cache/')
    ap.add_argument('-j', '--ignore-cache', help='Download tiles, ignoring any in cache', action='store_true')
    ap.add_argument('-s', '--stroke-width', help='Width of drawn trace', type=int, default=5)
    ap.add_argument('-l', '--legend', help='Add legend', action='store_true')
    ap.add_argument('-b', '--buffer', help='Add small buffer to map extent', action='store_true')
    ap.add_argument('-o', '--output-file', help='Output filename', default='output.png')
    ap.add_argument('-p', '--waypoints-file', help='Name of waypoints .xml file')
    ap.add_argument('-x', '--tiles-per-frame', help='Tiles per frame')
    ap.add_argument('-w', '--waypoint-extents', help='Use waypoints for map extent', nargs='*', default=[])
    args = ap.parse_args()
    return(args)

def trace_color(hue):
    (r, g, b) = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    ret_val = 'rgba({},{},{},{})'.format(170 * r, 170 * g, 170 * b, alpha)
    return (ret_val)

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

def generate_map(rc, args, nw_tile, se_tile, frm_x=None, frm_y=None):
    # Create map tile manager object.
    mtm = map_tile_mgr.map_tile_mgr(args.tiles_url, args.tile_cache, rc['map_api_key'], args.ignore_cache)

    if(args.waypoints_file):
        waypoints_file = args.waypoints_file
    else:
        if('waypoints_file' in rc.keys()):
            waypoints_file = rc['waypoints_file']
    w_mgr = waypoint_mgr.waypoint_mgr(waypoints_file)
    waypoints = w_mgr.read_waypoints()
    tile2wp = w_mgr.get_tile_to_waypoint_map(args.zoom_factor)

    tiles_x = se_tile[0] - nw_tile[0] + 1
    tiles_y = se_tile[1] - nw_tile[1] + 1
    base_map_filename = args.tile_cache+'{}-{}-{}-{}-{}.png'.format(args.zoom_factor,
            nw_tile[0], se_tile[0], nw_tile[1], se_tile[1])

    # Sanity check number of tiles to be used.  If too many, assume it's an error.
    num_tiles = tiles_x * tiles_y
    if(num_tiles > 2500):
        raise Exception ('ERROR: Too many tiles ({}) required (z={}).'.format(num_tiles, args.zoom_factor))

    # Download the tiles, if necessary.
    tiles_list = []
    tiles_obtained = 0
    newest_tile_mod_time = None
    for y in range(nw_tile[1], se_tile[1]+1):
        for x in range(nw_tile[0], se_tile[0]+1):
            tile_name = args.tile_cache+'{}-{}-{}.png'.format(args.zoom_factor, x, y)
            tiles_list.append(tile_name)
            mtm.get_tile(args.zoom_factor, x, y)
            tiles_obtained += 1
            print('INFO: {} % of tiles obtained'.format(int(100 * tiles_obtained / num_tiles)))

            # Find latest timestamp of all tiles.
            tile_timestamp = mtm.get_tile_timestamp(args.zoom_factor, x, y)
            if((newest_tile_mod_time is None) or (tile_timestamp > newest_tile_mod_time)):
                newest_tile_mod_time = tile_timestamp
                print('  Latest tile timestamp = %s' % newest_tile_mod_time)


    # Create base map if we're ignoring the cache of tiles, or there isn't
    # already a base map, or if the existing base map is older than the
    # newest tile in it.
    if(os.path.isfile(base_map_filename)):
        base_map_mod_time = os.path.getmtime(base_map_filename)
        print('  Timestamp = %s' % base_map_mod_time)

    if((not os.path.isfile(base_map_filename)) or args.ignore_cache or (base_map_mod_time < newest_tile_mod_time)):
        # Concatenate tiles to form whole map.
        print('INFO: Concat\'ing {} tiles to form base map ...'.format(tiles_x * tiles_y))
        cmd = 'montage -mode concatenate -tile %sx%s' % (tiles_x, tiles_y)
        for tile in tiles_list:
            cmd += ' %s' % tile
        cmd += ' %s' % base_map_filename
        subprocess.call(cmd.split())
    else:
        print('INFO: Base map already exists: {}'.format(base_map_filename))

    image_width = tiles_x * 256
    image_height = tiles_y * 256

    # Create IM run strings to create trace overlay images.
    overlay_files = []
    cc = 0
    prev_x_in_img = None
    prev_y_in_img = None
    num_traces = len(args.gps_file)
    if(num_traces == 0):
        num_traces = 1;
    for gps_file in args.gps_file:
        print('INFO: Building trace layer from file {} ...'.format(gps_file))
        gt = garmin.garmin(gps_file)

        cmd = 'convert -size {}x{}'.format(image_width, image_height)
        cmd += ' xc:transparent -fill transparent -stroke "{}"'.format(trace_color(cc / num_traces))
        cmd += ' -strokewidth {} -draw "polyline '.format(args.stroke_width)
        cc += 1

        for tp in gt.iter_position():
            try:
                lat = float(tp.find('.//garmin:LatitudeDegrees', ns).text)
                lon = float(tp.find('.//garmin:LongitudeDegrees', ns).text)
            except AttributeError:
                continue

            # Calculate the tile number that it's found on.
            tile = deg2num([lat, lon], args.zoom_factor)

            # Calculate the lat/lon of the corners of the tile.
            (tile_N, tile_W) = num2deg(tile[0], tile[1], args.zoom_factor)
            (tile_S, tile_E) = num2deg(tile[0]+1, tile[1]+1, args.zoom_factor)

            # Calculate the x,y pixel within that tile.
            x_in_tile = int(256.0 * (lon - tile_W) / (tile_E - tile_W))
            y_in_tile = int(256.0 * (lat - tile_N) / (tile_S - tile_N))

            # Add the offsets from edge of bounding box.
            offset_x = 256.0 * (tile[0] - nw_tile[0])
            offset_y = 256.0 * (tile[1] - nw_tile[1])

            x_in_img = int(offset_x + x_in_tile)
            y_in_img = int(offset_y + y_in_tile)
            if(prev_x_in_img is None):
                cmd += ' {},{}'.format(x_in_img, y_in_img)
                prev_x_in_img = x_in_img
                prev_y_in_img = y_in_img
            else:
                dist_to_new = math.sqrt((x_in_img - prev_x_in_img)**2 +
                        (y_in_img - prev_y_in_img)**2)
                # IM freaks out when x coords are same between adjacent points.
                if((x_in_img != prev_x_in_img) and (dist_to_new > args.stroke_width+1)):
                    cmd += ' {},{}'.format(x_in_img, y_in_img)
                    prev_x_in_img = x_in_img
                    prev_y_in_img = y_in_img

        overlay_filename = gps_file.replace('.tcx', '.png')
        overlay_filename = overlay_filename.replace('.zip', '.png')
        overlay_files.append(overlay_filename)
        cmd += '" {}'.format(overlay_filename)
        subprocess.call(cmd, shell=True)

    # Create overlay of points showing location of geo-coded jpg images.
    if(args.images is not None):
        for jpg_file in args.images:
            (lat, lon) = jpg_gps_ex.get_coords(jpg_file)
            print('DEBUG: Photo {} taken at ({}, {})'.format(jpg_file, lat, lon))
            # TODO: <prw>: Create mark on overlay layer.

    # Create layer of waypoints.
    circle_parms = ' -stroke "rgba(0,255,0,0.6)" -strokewidth 5 -fill "rgba(200,0,0,0.6)"'
    text_parms = ' -stroke "rgba(15,10,15,0.6)" -strokewidth 1 -fill "rgba(15,10,15,0.6)" -pointsize 26'
    cmd = 'convert -size {}x{} xc:transparent'.format(image_width, image_height)
    for y in range(nw_tile[1], se_tile[1]+1):
        offset_y = 256.0 * (y - nw_tile[1])
        for x in range(nw_tile[0], se_tile[0]+1):
            offset_x = 256.0 * (x - nw_tile[0])
            if(x in tile2wp.keys()):
                if(y in tile2wp[x].keys()):
                    for wptid in tile2wp[x][y]:
                        wp_lat = waypoints[wptid]['lat']
                        wp_lon = waypoints[wptid]['lon']

                        # Calculate the lat/lon of the corners of the tile.
                        (tile_N, tile_W) = num2deg(x, y, args.zoom_factor)
                        (tile_S, tile_E) = num2deg(x+1, y+1, args.zoom_factor)

                        # Calculate the x,y pixel within that tile.
                        x_in_tile = int(256.0 * (wp_lon - tile_W) / (tile_E - tile_W))
                        y_in_tile = int(256.0 * (wp_lat - tile_N) / (tile_S - tile_N))

                        # Add the offsets from edge of bounding box.
                        x_in_img = int(offset_x + x_in_tile)
                        y_in_img = int(offset_y + y_in_tile)

                        cmd += circle_parms + ' -draw "circle %d,%d %d,%d"' % (x_in_img, y_in_img, x_in_img+5, y_in_img)
                        cmd += text_parms + ' -annotate +%d+%d "%s"' % (x_in_img+10, y_in_img+5, wptid)

    waypoints_overlay_filename = 'temp_waypoints_overlay.png'
    overlay_files.append(waypoints_overlay_filename)
    cmd += ' ' + waypoints_overlay_filename
    subprocess.call(cmd, shell=True)

    # Generate output file name.
    (out_file_name, out_file_ext) = args.output_file.split('.')
    if(args.tiles_per_frame is not None):
        out_file_name += '-%dx%d' % (frm_x, frm_y)
    out_file_name += '.%s' % out_file_ext

    # Create composite map with overlay file(s) over base map.
    # To save resources, applies overlays one at a time.
    print('INFO: Compositing map and layers into one ...')
    os.rename(base_map_filename, out_file_name)
    for overlay_filename in overlay_files:
        print('INFO: Applying overlay "%s".' % overlay_filename)
        cmd = 'convert -page +0+0 {}'.format(out_file_name)
        cmd += ' -page +0+0 {}'.format(overlay_filename)
        cmd += ' -layers flatten {}'.format(out_file_name)
        subprocess.call(cmd, shell=True)

    # Add per-trace labels to bottom of composite image.
    if(args.legend):
        cc = 0
        for gps_file in args.gps_file:
            print('INFO: Appending legend to image for trace {}'.format(gps_file))
            gt = garmin.garmin(gps_file)
            start_time = gt.get_activity_start_datestamp()
            elev_gain_ft = gt.calc_elev_gain() * 3.28084
            # TODO: <prw>: Add more info to annot string.
            annotation_str = '{} {} {}'.format(gps_file, start_time, elev_gain_ft) 
            temp_output_file = 'foobarfiletmp' # TODO: Use temp file module.
            # TODO: <prw>: Fix transparent bkgnd of annotation lines.
            cmd = 'convert {} -gravity South -background "{}"'.format(args.output_file, trace_color(cc / num_traces))
            cmd += ' -splice 0x18 -annotate +0+2 \'{}\' {}'.format(annotation_str, temp_output_file)
            subprocess.call(cmd, shell=True)
            os.rename(temp_output_file, args.output_file)
            cc += 1

    # Clean up overlay files.
    for overlay_filename in overlay_files:
        os.remove(overlay_filename)

    print('INFO: Completed file "{}" is ready.'.format(out_file_name))


def main():
    args = parse_cmd_line()
    rc = read_rc_file()
    jpg_gps_ex = extract_exif_gps.extract_exif_gps()
    buf = 0

    # Ensure tile cache name ends with '/'.
    if (not args.tile_cache.endswith('/')):
        args.tile_cache += '/'

    # Create tile cache, if it's not already there.
    if (not os.path.isdir(args.tile_cache)):
        os.mkdir(args.tile_cache)

    # Get all waypoints and figure out which tile each will appear on.
    if(args.waypoints_file):
        waypoints_file = args.waypoints_file
    else:
        if('waypoints_file' in rc.keys()):
            waypoints_file = rc['waypoints_file']

    w_mgr = waypoint_mgr.waypoint_mgr(waypoints_file)
    waypoints = w_mgr.read_waypoints()
    tile2wp = w_mgr.get_tile_to_waypoint_map(args.zoom_factor)

    # Compute bounding box.
    gps_lat_N = None
    gps_lat_S = None
    gps_lon_W = None
    gps_lon_E = None

    # If waypoints are given, then use those waypoints to determine the
    # extent of the final map. Otherwise, use the extents as found in any
    # given trace files.

    # Use just the waypoints given on command line.
    extents = args.waypoint_extents

    if(len(extents) > 0):
        for w in extents:
            wp_lat = waypoints[w]['lat']
            wp_lon = waypoints[w]['lon']
            if((gps_lat_N is None) or (wp_lat > gps_lat_N)):
                gps_lat_N = wp_lat
            if((gps_lat_S is None) or (wp_lat < gps_lat_S)):
                gps_lat_S = wp_lat
            if((gps_lon_W is None) or (wp_lon < gps_lon_W)):
                gps_lon_W = wp_lon
            if((gps_lon_E is None) or (wp_lon > gps_lon_E)):
                gps_lon_E = wp_lon

    else:
        # No waypoints given, so look at traces for map extent.
        files_by_start_tile = {}
        for gps_file in args.gps_file:
            print('INFO: Processing file {} ...'.format(gps_file))
            gt = garmin.garmin(gps_file)

            # Get tile of starting coord.
            try:
                start_coord = gt.get_starting_coord()
                start_tile = deg2num(start_coord, args.zoom_factor)
                start_tile_name = '{}-{}-{}.png'.format(args.zoom_factor, start_tile[0], start_tile[1])
                print('INFO: start coord {} {} on tile {}'.format(start_coord[0], start_coord[1], start_tile_name))

                # Sort files by starting tile name.
                if (start_tile_name not in files_by_start_tile):
                    files_by_start_tile[start_tile_name] = []
                files_by_start_tile[start_tile_name].append(gps_file)
            except IndexError:
                pass

            # Scan through all coords to get bounding box of trace.
            (bb_n, bb_w, bb_s, bb_e) = gt.get_bbox()
            if((gps_lat_N is None) or (bb_n > gps_lat_N)):
                gps_lat_N = bb_n
            if((gps_lat_S is None) or (bb_s < gps_lat_S)):
                gps_lat_S = bb_s
            if((gps_lon_W is None) or (bb_w < gps_lon_W)):
                gps_lon_W = bb_w
            if((gps_lon_E is None) or (bb_e > gps_lon_E)):
                gps_lon_E = bb_e

            # TODO: Get stats about run such as start time, elapsed time, distance, etc. for annotation.
            start_time = gt.get_activity_start_datestamp()
            print('INFO: start time = {}'.format(start_time))

        # Print list of files that start on same tiles.
        for tile_name in files_by_start_tile.keys():
            print('{}:'.format(tile_name), end='')
            for filename in sorted(files_by_start_tile[tile_name]):
                print(' {}'.format(filename), end='')
            print()

    # Identify tiles needed.
    nw_coord = [gps_lat_N, gps_lon_W]
    se_coord = [gps_lat_S, gps_lon_E]

    # Calculate NW and SE tile numbers. Add a buffer, if specified.
    if(args.buffer):
        buf = 1
    nw_tile = deg2num(nw_coord, args.zoom_factor)
    nw_tile[0] -= buf
    nw_tile[1] -= buf
    se_tile = deg2num(se_coord, args.zoom_factor)
    se_tile[0] += buf
    se_tile[1] += buf

    if(args.tiles_per_frame is not None):
        # Expand map size to fit into whole number of frames (x and y).
        tiles_x = se_tile[0] - nw_tile[0] + 1
        tiles_y = se_tile[1] - nw_tile[1] + 1
        print('DEBUG: tiles_per_frame = %s' % args.tiles_per_frame)
        tiles_per_frame = [int(x) for x in args.tiles_per_frame.split('x')]
        num_frames_x = int(tiles_x / tiles_per_frame[0])
        r = tiles_x % tiles_per_frame[0]
        if(r > 0):
            num_frames_x += 1
            nw_tile[0] -= int(r/2)
            se_tile[0] += int(r/2)
            if(r & 1):
                se_tile[0] += 1
        num_frames_y = int(tiles_y / tiles_per_frame[1])
        r = tiles_y % tiles_per_frame[1]
        if(r > 0):
            num_frames_y += 1
            nw_tile[1] -= int(r/2)
            se_tile[1] += int(r/2)
            if(r & 1):
                se_tile[1] += 1
        frm_nw_tile = [0, 0]
        frm_se_tile = [0, 0]
        for frm_y in range(num_frames_y):
            for frm_x in range(num_frames_x):
                print('DEBUG: frm_x, frm_y = %d, %d' % (frm_x, frm_y))
                frm_nw_tile[0] = nw_tile[0] + frm_x * tiles_per_frame[0]
                frm_nw_tile[1] = nw_tile[1] + frm_y * tiles_per_frame[1]
                frm_se_tile[0] = nw_tile[0] + (frm_x + 1) * tiles_per_frame[0] - 1
                frm_se_tile[1] = nw_tile[1] + (frm_y + 1) * tiles_per_frame[1] - 1
                generate_map(rc, args, frm_nw_tile, frm_se_tile, frm_x, frm_y)
    else:
        generate_map(rc, args, nw_tile, se_tile)

if(__name__ == '__main__'):
    main()

# vi:set ts=4 et sw=4:
