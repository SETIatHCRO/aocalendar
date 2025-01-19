#! /usr/bin/env python
import argparse
from aocalendar import google_calendar_sync

ap = argparse.ArgumentParser()
ap.add_argument('-b', '--both_ways', help="Flag to update both AO and GC (True) or just AO (False)", action='store_true')
ap.add_argument('--conlog', help='Output console logging level', default='WARNING')
ap.add_argument('--filelog', help='Output file logging level (or off as default)', default='WARNING')
ap.add_argument('--path', help='Path for cal and log file', default='getenv')
args = ap.parse_args()

gcal = google_calendar_sync.SyncCal(conlog=args.conlog, path=args.path, filelog=args.filelog)
gcal.sequence(update_google_calendar=args.both_ways)