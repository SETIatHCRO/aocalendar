# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from aocalendar import aocalendar, aoc_tools
from astropy.time import TimeDelta, Time
from copy import copy
import os
import logging
from . import __version__, logger_setup

logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')  # Set to lowest to enable handlers to setLevel


ATA_CAL_ID = 'jhutdq684fs4hq7hpr3rutcj5o@group.calendar.google.com'
ATTRIB2KEEP = {'creator': 'email', 'end': 'utc_stop', 'start': 'utc_start', 'summary': 'name',
               'event_id': 'event_id', 'updated': 'created', 'timezone': '_convert2utc', 'description': '_test'}
##COMPATIBLE WITH AOCENTRY.WEB_COMPARE_HASH_LIST -v
ATTRIB2PUSH = {'utc_stop': 'end', 'utc_start': 'start', 'name': 'summary'}

DEBUG_SKIP_GC = False  # Disable access Google Calendar for debugging
if DEBUG_SKIP_GC:
    class GCDEBUG:
        def __init__(self):
            print("WARNING - YOU ARE IN DEBUG MODE!")
        def add_event(self, a, calendar_id):
            print("DEBUG: SKIP ADD!")
        def delete_event(self, a, calendar_id):
            print("DEBUG: SKIP DELETE!")


class SyncCal:
    def __init__(self, cal_id=ATA_CAL_ID, attrib2keep=ATTRIB2KEEP, attrib2push=ATTRIB2PUSH, path='getenv', output='INFO', file_logging=False, future_only=True):
        self.gc_cal_id = cal_id
        self.attrib2keep = attrib2keep
        self.attrib2push = list(attrib2push.keys())
        self.output = output.upper()
        self.file_logging = file_logging.upper() if isinstance(file_logging, str) else file_logging
        self.future_only = future_only
        self.path = aoc_tools.determine_path(path, None)
        self.now = aoc_tools.interp_date('now', fmt='Time')
        logger_setup.setup(logger, output=output, file_logging=file_logging, log_filename='aoclog', path=self.path)
        logger.info(f"{__name__} ver. {__version__}")

        if self.future_only:
            logger.info("Updating current/future entries.")
        else:
            logger.info("Updating all events (40 days past).")

        if DEBUG_SKIP_GC:
            self.google_cal_name = 'Allen Telescope Array Observing'
            self.gc = GCDEBUG()
        else:
            self.gc = GoogleCalendar(save_token=True)
            ata = self.gc.get_calendar_list_entry(self.gc_cal_id)
            self.google_cal_name = ata.summary

    def sequence(self, update_gc=False):
        """Sequence through the actions to sync the calendars."""
        self.get_aocal()
        self.get_google_calendar()
        self.gc_added_removed()
        self.update_aoc()
        self.update_gc(update=update_gc)
        self.finish()

    def get_aocal(self):
        """Read in the working aocal, as well as the previous for diff."""
        self.aocal = aocalendar.Calendar(path=self.path, start_new=True)
        self.aocal.make_hash_keymap(cols='web')
        self.aoc_added = copy(self.aocal.added)
        self.aoc_removed = copy(self.aocal.removed)

    def get_google_calendar(self):
        """Read in the google calendar and populate the gc aocal"""
        logger.info("Reading Google Calendar into local calendar.")
        gcname = os.path.join(self.path, f"{self.google_cal_name.replace(' ', '_')}.json")
        self.gc_local = aocalendar.Calendar(gcname, output=self.output, path=None, file_logging=self.file_logging, start_new=True)
        self.gc_local.make_hash_keymap(cols='web')
        if DEBUG_SKIP_GC:
            logger.warning("DEBUG - NOT READING LIVE GOOGLE CALENDAR")
            self.gc_web = self.gc_local
            return
        self.gc_web = aocalendar.Calendar("WEB", output=self.output, path=None, file_logging=self.file_logging, start_new=False)
        tmin = (self.now - TimeDelta(3600.0, format='sec')) if self.future_only else (self.now - TimeDelta(40.0, format='jd'))
        for event in self.gc.get_events(calendar_id=ATA_CAL_ID, single_events=True, time_min=tmin.datetime):
            entry = {}
            for key, val in self.attrib2keep.items():
                this_field = copy(getattr(event, key))
                if key in ['start', 'end']:
                    this_field = this_field.strftime('%Y-%m-%dT%H:%M:%S')
                elif key == 'creator':
                    this_field = this_field.email
                elif key == 'updated':
                    this_field = this_field.strftime('%Y-%m-%dT%H:%M:%S')
                else:
                    this_field = str(this_field)
                if val[0] != '_':
                    entry[val] = this_field
            self.gc_web.add(**entry)
        self.gc_web.make_hash_keymap(cols='web')

    def __end_check_ok(self, entry_end, tbuf_min=35.0):
        """If self.future_only make sure utc_stop is more than tbuf_min in the past."""
        if not isinstance(entry_end, Time):
            return True
        is_old = self.now < entry_end - TimeDelta(tbuf_min * 60.0, format='sec')
        if self.future_only and is_old:
            return False
        return True

    def gc_added_removed(self):
        """Get the diffs between the OLD and NEW google aocals"""
        self.gc_added = []  # hash in self.gc_new_cal that weren't in self.gc_old_cal
        self.gc_removed = []  # hash in self.gc_old_cal that aren't in self.gc_new_cal
        for hh in self.gc_web.hashmap:
            d, n = self.gc_web.hashmap[hh]
            if hh not in self.gc_local.hashmap and self.__end_check_ok(self.gc_web.events[d][n].utc_stop):
                self.gc_added.append(hh)
        for hh in self.gc_local.hashmap:
            d, n = self.gc_local.hashmap[hh]
            if hh not in self.gc_web.hashmap and self.__end_check_ok(self.gc_local.events[d][n].utc_stop):
                self.gc_removed.append(hh)

    def update_aoc(self):
        """Update the aocal with the google calendar diffs -- aocal is now correct."""
        changes = 0
        for hh in self.gc_added:
            if hh not in self.aocal.hashmap and hh not in self.aoc_removed:
                d, n = self.gc_web.hashmap[hh]
                entry2add = self.gc_web.events[d][n].todict(printable=False, include_meta=True)
                self.aocal.add(**entry2add)
                changes += 1
        logger.info(f"Adding {changes} to {self.aocal.calfile}")

        changes = 0
        for hh in self.gc_removed:
            if hh in self.aocal.hashmap and hh not in self.aoc_added:
                d, n = self.aocal.hashmap[hh]
                self.aocal.delete(d, n)
                changes += 1
        logger.info(f"Removing {changes} from {self.aocal.calfile}")
        self.aocal.make_hash_keymap(cols='web')

    def update_gc(self, update=False):
        """Update the google aocal with the updated aocal from self.update_aoc and sync up to Google Calendar"""
        changes_add = 0
        for hh in self.aoc_added:
            if hh not in self.gc_web.hashmap and hh not in self.gc_removed:
                d, n = self.aocal.hashmap[hh]
                changes_add += 1
                entry2add = self.aocal.events[d][n].todict(printable=False, include_meta=True)
                self.gc_web.add(**entry2add)
                if update:
                    d, n = self.aocal.hashmap[hh]
                    start = self.aocal.events[d][n].utc_start.datetime
                    end = self.aocal.events[d][n].utc_stop.datetime
                    # creator = self.aocal[d][n].email
                    # description = self.aocal[d][n].pid
                    summary = self.aocal.events[d][n].name
                    entry2add = Event(summary, start=start, end=end, timezone='GMT')
                    event = self.gc.add_event(entry2add, calendar_id=self.gc_cal_id)
        action = 'Adding' if update else "Found but not adding"
        logger.info(f"{action} {changes_add} to Google Calendar {self.google_cal_name}")

        changes_del = 0
        for hh in self.aoc_removed:
            if hh in self.gc_web.hashmap and hh not in self.gc_added:
                d, n = self.gc_web.hashmap[hh]
                self.gc_web.delete(d, n)
                changes_del += 1
                if update:
                    event_id = self.gc_web.events[d][n].event_id
                    self.gc.delete_event(event_id, calendar_id=self.gc_cal_id)
        action = 'Removing' if update else "Found but not removing"
        logger.info(f"{action} {changes_del} from Google Calendar {self.google_cal_name}")

    def finish(self):
        if os.path.exists(self.aocal.calfile_fullpath):
            os.remove(self.aocal.calfile_fullpath)
        self.aocal.init_calendar(self.aocal.created)
        self.aocal.write_calendar(calfile=self.aocal.calfile_fullpath)  # Get rid of added/removed/updated in aocal

        if os.path.exists(self.gc_local.calfile_fullpath):
            os.remove(self.gc_local.calfile_fullpath)
        self.gc_web.init_calendar(self.gc_local.created)
        self.gc_web.write_calendar(calfile=self.gc_local.calfile_fullpath)  # Move web to local


def show_stuff(show_entries=False):
    from tabulate import tabulate
    from datetime import datetime

    gcalendar_class = SyncCal()
    gc = gcalendar_class.gc

    if not show_entries:
        show_entries = []
    elif isinstance(show_entries, int):
        show_entries = [show_entries]
    elif isinstance(show_entries, str):
        show_entries = [int(xx) for xx in show_entries.split(',')]
    elif isinstance(show_entries, list):
        pass
    else:
        show_entries = []
        
    data = []
    data_uncut = []
    col_list = set()
    for event in gc.get_events(calendar_id=ATA_CAL_ID, single_events=True, time_min=datetime(year=2025, month=1, day=1)):
        row = {}
        row_uncut = {}
        print(event)
        for col in dir(event):
            col_list.add(col)
            entry = getattr(event, col)
            if col[0] != '_':
                if str(entry)[0] != '<' and bool(entry):
                    row[col] = str(entry)
            row_uncut[col] = entry
        data.append(row)
        data_uncut.append(row_uncut)

    hdr = sorted(data_uncut[0].keys())
    table = []
    for i, d in enumerate(data_uncut):
        trow = [i]
        for key in hdr:
            try:
                trow.append(str(d[key])[:20])
            except KeyError:
                trow.append('  ')
        table.append(trow)
    print(tabulate(table, headers=['#'] + hdr))

    hdr = sorted(data_uncut[0].keys())
    for i in show_entries:
        print(f"==================================Entry {i}=========================================")
        entry = []
        for j, key in enumerate(hdr):
            entry.append( [ key, str(data_uncut[i][key])[:100] ] )
            if isinstance(data_uncut[i][key], dict):
                print(key)
                for a, b in data_uncut[i][key].items():
                    print('\t', a, b)
        print(tabulate(entry))

    for cal in gc.get_calendar_list():
        print(cal.calendar_id, cal)
    print(', '.join(col_list))