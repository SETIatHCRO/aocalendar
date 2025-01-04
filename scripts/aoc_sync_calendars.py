#! /usr/bin/env python

from aocalendar import google_calendar_sync

gcal = google_calendar_sync.SyncCal()

gcal.get_gc_aocal()
gcal.get_aoc_aocal()
gcal.get_google_calendar()
gcal.gc_added_removed()
gcal.aoc_added_removed()
gcal.update_aoc()
gcal.udpate_gc()
gcal.shuffle_aoc_files()