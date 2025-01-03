#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

import argparse
from aocalendar import aocalendar


ap = argparse.ArgumentParser()
ap.add_argument('calfile', help="Calfile/date to use.", nargs='?', default='now')
ap.add_argument('--path', help="Path to use", default='getenv')
ap.add_argument('--output', help="Logging output level", default='INFO')
# Actions
ap.add_argument('-l', '--list', help="List events of day", action='store_true')
ap.add_argument('-e', '--show_entry', help="Show an entry # on date", default=False)
ap.add_argument('-g', '--graph', help="Graph calendar day", action='store_true')
ap.add_argument('-a', '--add', help="Add an entry", action='store_true')
ap.add_argument('-u', '--update', help="Update an entry # on date", default=False)
ap.add_argument('-d', '--delete', help="Delete an entry # on date", default=False)
ap.add_argument('-s', '--schedule', help="Schedule ra,dec/source and set duration of observation", default=False)
ap.add_argument('-q', '--quick', help="Quick add a session of #h/m/s length starting now (at least add -n...)", default=False)
ap.add_argument('--duration', help="Duration of scheduled observation in hours", default=6.0)
# Event fields
ap.add_argument('-n', '--name', help="Event field", default=None)
ap.add_argument('-p', '--pid', help="Event field", default=None)
ap.add_argument('--utc_start', help="Event field", default=None)
ap.add_argument('--utc_stop', help="Event field", default=None)
ap.add_argument('--lst_start', help="Event field", default=None)
ap.add_argument('--lst_stop', help="Event field", default=None)
ap.add_argument('--observer', help="Event field", default=None)
ap.add_argument('--email', help="Event field", default=None)
ap.add_argument('--note', help="Event field", default=None)
ap.add_argument('--state', help="Event field", default=None)

args = ap.parse_args()

if args.add:
    args.calfile = args.utc_start

aoc = aocalendar.Calendar(calfile=args.calfile, path=args.path, output=args.output)
kwargs = aocalendar.cull_args(**vars(args))

if args.quick:
    from aocalendar import aoc_tools
    args.utc_start = aoc_tools.interp_date('now', fmt='Time').datetime.isoformat(timespec='seconds')
    args.utc_stop = aoc_tools.interp_date(f"now/{args.quick}", fmt='Time').datetime.isoformat(timespec='seconds')
    args.add = True

if args.list:
    print(aoc.format_day_events(day=args.calfile, cols='all', return_as='table'))
if args.show_entry:
    print(aoc.events[args.calfile][int(args.show_entry)])
if args.graph:
    print(aoc.graph_day(day=args.calfile, interval_min=10.0))
    print("\n\n")
if args.add:
    aoc.add(**kwargs)
    aoc.write_calendar()
if args.update:
    aoc.update(day=args.calfile, nind=int(args.update), **kwargs)
    aoc.write_calendar()
if args.delete:
    aoc.delete(day=args.calfile, nind=int(args.delete))
    aoc.write_calendar()
if args.schedule:
    if ',' in args.schedule:
        ra, dec = args.schedule.split(',')
        args.schedule = None
    else:
        ra, dec = None, None
    aoc.schedule(ra=ra, dec=dec, source=args.schedule, day=args.calfile, duration=float(args.duration), **kwargs)
    aoc.write_calendar()