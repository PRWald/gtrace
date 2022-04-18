#!/usr/bin/env python3
# $Id$

import argparse
import subprocess

# Requires ImageMagick.
imcmd = 'identify -verbose'.split()

class extract_exif_gps(object):
    def __init__(self):
        pass


    def _slash_conv(self, s):
        (nm, dv) = s.split('/')
        return(float(nm) / float(dv))


    def _hms2dec(self, s):
        (hr, mn, sd) = s.split(', ')
        dec = self._slash_conv(hr) + self._slash_conv(mn) / 60.0 + self._slash_conv(sd) / 3600.0
        return(dec)


    def get_coords(self, jpg_file):
        lat = 1.0
        lon = 1.0
        p = subprocess.Popen(imcmd + [jpg_file], stdout=subprocess.PIPE).communicate()[0]
        for line in p.decode('utf-8').split('\n'):
            val = line.split(':')
            if('exif:GPS' in line):
                if('GPSLatitude' == val[1]):
                    lat *= self._hms2dec(val[2])
                if('GPSLatitudeRef' == val[1]):
                    if(val[2].strip() == 'S'):
                        lat *= (-1)
                if('GPSLongitude' == val[1]):
                    lon = self._hms2dec(val[2])
                if('GPSLongitudeRef' == val[1]):
                    if(val[2].strip() == 'W'):
                        lon *= (-1)

        return(lat, lon)


if(__name__ == '__main__'):
    print('ERROR: This is a module.')


# vi:set ai et ts=4 sts=4 sw=4:
