#!/usr/bin/env python3

import argparse

def parse_cmd_line():
    ap = argparse.ArgumentParser(description='List trace files with most segments.')
    ap.add_argument('-f', '--paths-file', help='Name of paths file.', required=True)
    args = ap.parse_args()
    return(args)

def main():
    args = parse_cmd_line()
    with open(args.paths_file, 'r') as f_path:
        segments = []
        segments_in_trace = {}
        segments_to_trace = {}
        for l in f_path:
            (trace_file, timestamp, segment, _, _) = l.split(',')

            # Sort endpoints so wA:wB == wB:wA
            end_pts = sorted(segment.split(':'))
            segment = '%s:%s' % (end_pts[0], end_pts[1])

            if(segment not in segments):
                segments.append(segment)

            if(segment not in segments_to_trace.keys()):
                segments_to_trace[segment] = []
            segments_to_trace[segment].append(trace_file)

            if(trace_file not in segments_in_trace.keys()):
                segments_in_trace[trace_file] = []
            segments_in_trace[trace_file].append(segment)

#    for segment in segments:
#        print(segment)

#    for trace_file in segments_in_trace.keys():
#        print('%s has %d segments' % (trace_file, len(segments_in_trace[trace_file])))

#    for segment in segments_to_trace.keys():
#        print('%s appears in %d tracefiles' % (segment,
#        len(segments_to_trace[segment])))

    for segment in segments:
        max_num = 0
        for trace_file in segments_to_trace[segment]:
            if(len(segments_in_trace[trace_file]) > max_num):
                trace_file_with_max = trace_file
                max_num = len(segments_in_trace[trace_file])
        print('segment %s taken from %s' % (segment, trace_file_with_max))

        # TODO: <prw>: Some how duplicates make it into the list.
        print('Removing the following segments from master list.')
        for seg in segments_in_trace[trace_file]:
            if(seg in segments):
                print('  %s' % seg, end='')
                segments.remove(seg)
        print('')

if(__name__ == '__main__'):
    main()

# vi:set ts=4 et sw=4:
