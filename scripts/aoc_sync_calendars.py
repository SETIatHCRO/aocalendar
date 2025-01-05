#! /usr/bin/env python
import argparse
from aocalendar import google_calendar_sync

ap = argparse.ArgumentParser()
ap.add_argument('--output', help='Output console logging level', default='INFO')
ap.add_argument('--file_logging', help='Output file logging level (or off as default)', default=False)
ap.add_argument('--path', help='Path for cal and log file', default='getenv')
args = ap.parse_args()

gcal = google_calendar_sync.SyncCal(output=args.output, path=args.path, file_logging=args.file_logging)

gcal.get_gc_aocal()
gcal.get_aoc_aocal()
gcal.get_google_calendar()
gcal.gc_added_removed()
gcal.aoc_added_removed()
gcal.update_aoc()
gcal.udpate_gc()
gcal.shuffle_aoc_files()