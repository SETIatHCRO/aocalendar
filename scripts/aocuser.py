#! /usr/bin/env python
import argparse
from obscalendar import obscalendar

ap = argparse.ArgumentParser()
ap.add_argument('calfile', help="Calfile to use.", nargs='?', default='now')
ap.add_argument('--path', help="Path to use", default='getenv')
ap.add_argument('--output', help="Logging output level", default='INFO')
# Actions
ap.add_argument('--show', help="Show contents of day", default=False)
ap.add_argument('--entry', help="Show an entry YYYY-MM-DD:#", default=False)
ap.add_argument('--graph', help="Graph calendar day", default=False)
# Event fields
ap.add_argument('--name', help="Event field", default='name')
ap.add_argument('--id', help="Event field", default='ID')
ap.add_argument('--utc_start', help="Event field", default=None)
ap.add_argument('--utc_stop', help="Event field", default=None)
ap.add_argument('--observer', help="Event field", default=None)
ap.add_argument('--email', help="Event field", default=None)
ap.add_argument('--note', help="Event field", default=None)
ap.add_argument('--state', help="Event field", default='primary')

args = ap.parse_args()

if args.show:
    args.calfile=args.show
if args.entry:
    args.calfile = args.entry.split(':')[0]
if args.graph:
    args.calfile = args.graph

aoc = obscalendar.Calendar(calfile=args.calfile, path=args.path, output=args.output)

if args.show:
    print(aoc.format_day_contents(day=args.show, cols='all', return_as='table'))
if args.entry:
    this_entry_key, num = obscalendar.split_entry(args.entry)
    print(aoc.contents[this_entry_key][num])
if args.graph:
    print(aoc.graph_day(day=args.graph))
    print("\n\n")