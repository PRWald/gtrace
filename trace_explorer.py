#!/usr/bin/env python3

import os
import math
import argparse
import tkinter as tk
import xml.etree.ElementTree as ET
from PIL import Image, ImageTk
import map_tile_mgr
import garmin
import waypoint_mgr
from garmin import ns
from map_tile_mgr import deg2num, num2deg

# Get gps coords, get tile, display tile with current gps coord highlighted.
# Have a button user can click to save the current point in a list with a name.
# These points will be used later to scan through other traces to compute average distances and times
# between them.

zm = 16
photoimage_cache = {}
rc_file = '{}/.trace.rc'.format(os.environ['HOME'])
prev_tile = [None, None]
wpts_on_disp = []

def parse_cmd_line():
    ap = argparse.ArgumentParser(description='Explore GPS trace on opencyclemap.org tiles')
    ap.add_argument('-f', '--gps-file', help='Name of Garmin .tcx file', required=True)
    ap.add_argument('-t', '--tiles-url', help='URL to tile server',
            default='https://tile.thunderforest.com/cycle')
    ap.add_argument('-c', '--tile-cache', help='Directory where downloaded tiles are stored locally.',
            default='tile-cache')
    ap.add_argument('-j', '--ignore-cache', help='Download tiles, ignoring any in cache', action='store_true')
    ap.add_argument('-w', '--waypoints-file', help='Name of waypoints .xml file')
    args = ap.parse_args()
    return(args)

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

def update_pos():
    global prev_tile
    scale_setting = dscale.get()
    tp = trackpoints[scale_setting]
    d_m = tp.findall('garmin:DistanceMeters', ns)[0].text
    lat_d = tp.findall('.//garmin:LatitudeDegrees', ns)[0].text
    lon_d = tp.findall('.//garmin:LongitudeDegrees', ns)[0].text
    alt_m = tp.findall('.//garmin:AltitudeMeters', ns)[0].text
    d_mi = round(0.005 + 0.000621371 * float(d_m), 2)
    alt_ft = int(0.5 + float(alt_m) * 3.28084)
    dist.set(d_mi)
    lat.set(lat_d)
    lon.set(lon_d)
    elev.set(alt_ft)
    tile = deg2num([float(lat_d), float(lon_d)], zm)
    if((tile[0] != prev_tile[0]) or (tile[1] != prev_tile[1])):
        tiledisp.set('{}, {}, {}'.format(zm, tile[0], tile[1]))
        tile_file = mtm.get_tile(zm, tile[0], tile[1])
        if(tile_file not in photoimage_cache.keys()):
            photoimage_cache[tile_file] = ImageTk.PhotoImage(Image.open(tile_file))
        tile_canvas.itemconfig(cnv_img, image=photoimage_cache[tile_file])
        for w in wpts_on_disp:
            tile_canvas.delete(w)
        for w in waypoints.keys():
            (x_in_tile, y_in_tile) = xy_in_tile(waypoints[w]['lat'], waypoints[w]['lon'], tile[0], tile[1], zm)
            tmp = tile_canvas.create_oval(x_in_tile - 2, y_in_tile - 2, x_in_tile + 2, y_in_tile + 2, fill='green')
            wpts_on_disp.append(tmp)
    (x_in_tile, y_in_tile) = xy_in_tile(lat_d, lon_d, tile[0], tile[1], zm)
    tile_canvas.coords(cnv_pt, x_in_tile-3, y_in_tile-3, x_in_tile+3, y_in_tile+3)
    prev_tile = tile

def xy_in_tile(lat, lon, tile_x, tile_y, zm):
    (tile_N, tile_W) = num2deg(tile_x, tile_y, zm)
    (tile_S, tile_E) = num2deg(tile_x + 1, tile_y + 1, zm)
    x_in_tile = int(256.0 * (float(lon) - tile_W) / (tile_E - tile_W))
    y_in_tile = int(256.0 * (float(lat) - tile_N) / (tile_S - tile_N))
    return((x_in_tile, y_in_tile))

def mwheel(event):
    scale_setting = dscale.get()
    if(event.num == 5):
        scale_setting -= 1
        if(scale_setting < 0):
            scale_setting = 0
    if(event.num == 4):
        scale_setting += 1
        if(scale_setting > num_trackpoints-1):
            scale_setting = num_trackpoints-1
    dscale.set(scale_setting)
    update_pos()

def slider_release(event):
    update_pos()

def save_point():
    print('{} {} {} {}'.format(dist.get(), elev.get(), lat.get(), lon.get()))
    print('  <wpt id="">')
    print('    <name></name>')
    print('    <lat>%s</lat>' % lat.get())
    print('    <lon>%s</lon>' % lon.get())
    print('    <elev_ft>%s</elev_ft>' % elev.get())
    print('  </wpt>')

if(__name__ == '__main__'):
    args = parse_cmd_line()

    rc = read_rc_file()

    if(args.tile_cache):
        tile_cache = args.tile_cache
    else:
        if('tile_cache' in rc.keys()):
            tile_cache = rc['tile_cache']
    if(args.tiles_url):
        tiles_url = args.tiles_url
    else:
        if('tiles_url' in rc.keys()):
            tiles_url = rc['tiles_url']
    if(args.waypoints_file):
        waypoints_file = args.waypoints_file
    else:
        if('waypoints_file' in rc.keys()):
            waypoints_file = rc['waypoints_file']

    w_mgr = waypoint_mgr.waypoint_mgr(waypoints_file)
    waypoints = w_mgr.read_waypoints()
    print('DEBUG: num waypoints = {}'.format(len(waypoints)))

    mtm = map_tile_mgr.map_tile_mgr(tiles_url, tile_cache, rc['map_api_key'], ignore_cache=args.ignore_cache)

    root = tk.Tk()
    root.title('Trace Explorer')

    gt = garmin.garmin(args.gps_file)
    trackpoints = gt.get_trackpoints()
    num_trackpoints = len(trackpoints)
    print('DEBUG: {} track points'.format(num_trackpoints))

    tp = trackpoints[1]
    lat_d = tp.findall('.//garmin:LatitudeDegrees', ns)[0].text
    lon_d = tp.findall('.//garmin:LongitudeDegrees', ns)[0].text
    tile = deg2num([float(lat_d), float(lon_d)], zm)
    tile_file = mtm.get_tile(zm, tile[0], tile[1])
    photoimage_cache[tile_file] = ImageTk.PhotoImage(Image.open(tile_file))

    dist = tk.StringVar()
    lat = tk.StringVar()
    lon = tk.StringVar()
    elev = tk.StringVar()
    tiledisp = tk.StringVar()

    dscale = tk.Scale(root, from_=0, to=num_trackpoints-1, orient=tk.HORIZONTAL, length=400)
    dscale.bind("<Button-4>", mwheel)
    dscale.bind("<Button-5>", mwheel)
    dscale.bind("<ButtonRelease-1>", slider_release)
    dscale.pack()

    tilelabel = tk.Label(root, textvariable=tiledisp)
    tilelabel.pack()

    tile_canvas = tk.Canvas(root, width=256, height=256)
    tile_canvas.pack()
    cnv_img = tile_canvas.create_image(0, 0, anchor=tk.NW, image=photoimage_cache[tile_file])
    cnv_pt = tile_canvas.create_oval(0,0,5,5, fill="red")

    dlabel = tk.Label(root, textvariable=dist)
    dlabel.pack()

    latlabel = tk.Label(root, textvariable=lat)
    latlabel.pack()

    lonlabel = tk.Label(root, textvariable=lon)
    lonlabel.pack()

    altlabel = tk.Label(root, textvariable=elev)
    altlabel.pack()

    store_button = tk.Button(root, text='Save Point', command=save_point)
    store_button.pack()

    root.mainloop()

