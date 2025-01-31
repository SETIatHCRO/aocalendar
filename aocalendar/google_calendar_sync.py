# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.
# Acknowledge gcsa from https://google-calendar-simple-api.readthedocs.io/en/latest/

from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from googleapiclient.errors import HttpError
from aocalendar import aocalendar, tools
from copy import copy
import os
import logging
from odsutils import ods_timetools as ttools
from . import __version__, logger_setup

logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')  # Set to lowest to enable handlers to setLevel


ATA_CAL_ID = 'jhutdq684fs4hq7hpr3rutcj5o@group.calendar.google.com'
ATTRIB2KEEP = {'creator': 'email', 'end': 'utc_stop', 'start': 'utc_start', 'summary': 'program',
               'event_id': 'event_id', 'updated': 'created', 'timezone': '_convert2utc', 'description': '_test'}
##SHOULD BE COMPATIBLE WITH AOCENTRY.WEB_COMPARE_HASH_LIST -v
ATTRIB2PUSH = {'utc_stop': 'end', 'utc_start': 'start', 'program': 'summary'}

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
    def __init__(self, cal_id=ATA_CAL_ID, attrib2keep=ATTRIB2KEEP, attrib2push=ATTRIB2PUSH, path='getenv', conlog='INFO', filelog=False):
        self.gc_cal_id = cal_id
        self.attrib2keep = attrib2keep
        self.attrib2push = list(attrib2push.keys())
        self.path = tools.determine_path(path, None)
        self.now = ttools.interpret_date('now', fmt='Time')
        self.logset = logger_setup.Logger(logger, conlog=conlog, filelog=filelog, log_filename='aoclog', path=self.path)
        logger.info(f"{__name__} ver. {__version__}")

        if DEBUG_SKIP_GC:
            self.google_cal_name = 'Allen Telescope Array Observing'
            self.gc = GCDEBUG()
        else:
            self.gc = GoogleCalendar(save_token=True)
            ata = self.gc.get_calendar_list_entry(self.gc_cal_id)
            self.google_cal_name = ata.summary

    def sequence(self, update_google_calendar=False):
        """Sequence through the actions to sync the calendars."""
        self.get_aocal()
        self.get_google_calendar()
        self.gc_added_removed()
        self.update_aoc()
        self.update_gc(update_google_calendar=update_google_calendar)
        self.rewrite_files()

    def get_aocal(self, calfile='now', path=None, conlog=None, filelog=None, start_new=True):
        """Read in the working aocal, as well as the previous for diff."""
        path = self.path if path is None else path
        self.aocal = aocalendar.Calendar(calfile=calfile, path=path, conlog=self.logset.conlog, filelog=self.logset.filelog, start_new=start_new)
        self.aocal.make_hash_keymap(cols='web')
        self.aoc_added = copy(self.aocal.added)
        self.aoc_removed = copy(self.aocal.removed)

    def refresh_aocal(self):
        self.aocal.read_calendar_events(calfile='refresh')
        self.aocal.make_hash_keymap(cols='web')
        self.aoc_added = copy(self.aocal.added)
        self.aoc_removed = copy(self.aocal.removed)

    def get_google_calendar(self):
        """Read in the google calendar and populate the gc local calendar"""
        logger.info("Reading Google Calendar into local calendar.")
        gcname = os.path.join(self.path, f"{self.google_cal_name.replace(' ', '_')}.json")
        self.gc_local = aocalendar.Calendar(gcname, conlog=self.logset.conlog, path=self.path, filelog=self.logset.filelog, start_new=True)
        self.gc_local.make_hash_keymap(cols='web')
        if DEBUG_SKIP_GC:
            logger.warning("DEBUG - NOT READING LIVE GOOGLE CALENDAR")
            self.gc_web = self.gc_local
            return
        self.gc_web = aocalendar.Calendar("WEB", conlog=self.logset.conlog, path=self.path, filelog=self.logset.filelog, start_new=False)
        tmin = ttools.interpret_date(self.now.datetime.strftime('%Y'), fmt='Time')  # Start of year
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

    def gc_added_removed(self):
        """Get the diffs between the OLD and NEW google aocals"""
        self.gc_added = []  # hash in self.gc_new_cal that weren't in self.gc_old_cal
        self.gc_removed = []  # hash in self.gc_old_cal that aren't in self.gc_new_cal
        for hh in self.gc_web.hashmap:
            d, n = self.gc_web.hashmap[hh]
            if hh not in self.gc_local.hashmap:
                self.gc_added.append(hh)
        for hh in self.gc_local.hashmap:
            d, n = self.gc_local.hashmap[hh]
            if hh not in self.gc_web.hashmap:
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

    def add_event_to_google_calendar(self, event2add):
        start = copy(event2add.utc_start.datetime)
        end = copy(event2add.utc_stop.datetime)
        # creator = copy(event2add.email)
        # description = copy(event2add.pid)
        summary = copy(event2add.program)
        event2add = Event(summary, start=start, end=end, timezone='GMT')
        try:
            event = self.gc.add_event(event2add, calendar_id=self.gc_cal_id)
        except HttpError:
            logger.error(f"Error adding Google Calendar event {event2add.summary}")

    def update_event_on_google_calendar(self, event2update):
        try:
            event = self.gc.get_event(event2update.event_id, calendar_id=self.gc_cal_id)
            event = Event(event2update.program, start=event2update.utc_start, end=event2update.utc_stop, timezone='GMT')
            event = self.gc.update_event(event)
        except HttpError:
            logger.error(f"Error updating Google Calendar event {event2update.event_id}")

    def delete_event_from_google_calendar(self, event2delete):
        if isinstance(event2delete, str):
            event_id = event2delete
        else:
            event_id = event2delete.event_id
        try:
            self.gc.delete_event(event_id, calendar_id=self.gc_cal_id)
        except HttpError:
            logger.error(f"Error updating Google Calendar event {event_id}")

    def update_gc(self, update_google_calendar=False):
        """Update the google aocal with the updated aocal from self.update_aoc and sync up to Google Calendar"""
        changes_add = 0
        for hh in self.aoc_added:
            if hh not in self.gc_web.hashmap and hh not in self.gc_removed:
                try:
                    d, n = self.aocal.hashmap[hh]
                except KeyError:
                    continue
                changes_add += 1
                entry2add = self.aocal.events[d][n].todict(printable=False, include_meta=True)
                self.gc_web.add(**entry2add)
                if update_google_calendar:
                    d, n = self.aocal.hashmap[hh]
                    self.add_event_to_google_calendar(self.aocal.events[d][n])
        action = 'Added to local+GoogleCalendar' if update_google_calendar else "Added to local"
        logger.info(f"{action} {changes_add}")

        changes_del = 0
        for hh in self.aoc_removed:
            if hh in self.gc_web.hashmap and hh not in self.gc_added:
                try:
                    d, n = self.gc_web.hashmap[hh]
                except KeyError:
                    continue
                self.gc_web.delete(d, n)
                changes_del += 1
                if update_google_calendar:
                    self.delete_event_from_google_calendar(self.gc_web.events[d][n].event_id)
        action = 'Removed from local+GoogleCalendar' if update_google_calendar else "Removed from local"
        logger.info(f"{action} {changes_del}")

    def rewrite_files(self):
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