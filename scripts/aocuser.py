#! /usr/bin/env python
import argparse
from obscalendar import obscalendar

ap = argparse.ArgumentParser()
ap.add_argument('calfile', help="Calfile/date to use.", nargs='?', default='now')
ap.add_argument('--path', help="Path to use", default='getenv')
ap.add_argument('--output', help="Logging output level", default='INFO')
# Actions
ap.add_argument('--show', help="Show contents of day", action='store_true')
ap.add_argument('--entry', help="Show an entry # on date", default=False)
ap.add_argument('--graph', help="Graph calendar day", action='store_true')
ap.add_argument('--add', help="Add an entry", action='store_true')
ap.add_argument('--update', help="Update an entry # on date", default=False)
ap.add_argument('--delete', help="Delete an entry # on date", default=False)
ap.add_argument('--schedule', help="Schedule ra,dec observation", default=False)
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

if args.add:
    args.calfile = args.utc_start

aoc = obscalendar.Calendar(calfile=args.calfile, path=args.path, output=args.output)

if args.show:
    print(aoc.format_day_contents(day=args.calfile, cols='all', return_as='table'))
if args.entry:
    print(aoc.contents[args.calfile][int(args.entry)])
if args.graph:
    print(aoc.graph_day(day=args.calfile))
    print("\n\n")
if args.add:
    aoc.edit('add', **vars(args))
    aoc.write_calendar()
if args.update:
    entry_num = f"{args.calfile}:{args.update}"
    aoc.edit('update', entry=entry_num, **vars(args))
    aoc.write_calendar()
if args.delete:
    entry_num = f"{args.calfile}:{args.delete}"
    aoc.edit('delete', entry=entry_num)
    aoc.write_calendar()
if args.schedule:
    ra, dec = args.schedule.split(',')
    aoc.schedule(ra=ra, dec=dec, day=args.calfile)
    aoc.write_calendar()