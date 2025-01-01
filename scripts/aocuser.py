#! /usr/bin/env python
import argparse
from obscalendar import obscalendar


ap = argparse.ArgumentParser()
ap.add_argument('calfile', help="Calfile/date to use.", nargs='?', default='now')
ap.add_argument('--path', help="Path to use", default='getenv')
ap.add_argument('--output', help="Logging output level", default='INFO')
# Actions
ap.add_argument('-l', '--list', help="List contents of day", action='store_true')
ap.add_argument('-e', '--entry', help="Show an entry # on date", default=False)
ap.add_argument('-g', '--graph', help="Graph calendar day", action='store_true')
ap.add_argument('-a', '--add', help="Add an entry", action='store_true')
ap.add_argument('-u', '--update', help="Update an entry # on date", default=False)
ap.add_argument('-d', '--delete', help="Delete an entry # on date", default=False)
ap.add_argument('-s', '--schedule', help="Schedule ra,dec,duration observation", default=False)
ap.add_argument('-q', '--quick', help="Quick add a session of #h/m/s length starting now (at least add -n...)", default=False)
# Event fields
ap.add_argument('-n', '--name', help="Event field", default='name')
ap.add_argument('-i', '--id', help="Event field", default='ID')
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

if args.quick:
    from obscalendar import cal_tools
    args.utc_start = cal_tools.interp_date('now', fmt='Time').datetime.isoformat(timespec='seconds')
    args.utc_stop = cal_tools.interp_date(f"now/{args.quick}", fmt='Time').datetime.isoformat(timespec='seconds')
    args.add = True

if args.list:
    print(aoc.format_day_contents(day=args.calfile, cols='all', return_as='table'))
if args.entry:
    print(aoc.contents[args.calfile][int(args.entry)])
if args.graph:
    print(aoc.graph_day(day=args.calfile, interval_min=10.0))
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
    ra, dec, duration = args.schedule.split(',')
    aoc.schedule(ra=ra, dec=dec, day=args.calfile, duration=float(duration))
    aoc.write_calendar()