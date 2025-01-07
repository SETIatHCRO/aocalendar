# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from aocalendar import aocalendar, aoc_tools
from astropy.time import TimeDelta
from copy import copy
import os, shutil
import logging
from . import __version__, logger_setup

logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')  # Set to lowest to enable handlers to setLevel


ATA_CAL_ID = 'jhutdq684fs4hq7hpr3rutcj5o@group.calendar.google.com'
ATTRIB2KEEP = {'creator': 'email', 'end': 'utc_stop', 'start': 'utc_start', 'summary': 'name',
               'event_id': 'event_id', 'updated': 'created', 'timezone': '_convert2utc'}
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

        if DEBUG_SKIP_GC:
            self.google_cal_name = 'Allen Telescope Array Observing'
            self.gc = GCDEBUG()
        else:
            self.gc = GoogleCalendar()
            ata = self.gc.get_calendar_list_entry(self.gc_cal_id)
            self.google_cal_name = ata.summary

    def sequence(self):
        """Sequence through the actions to sync the calendars."""
        self.get_gc_aocal()
        self.get_aoc_aocal()
        self.get_google_calendar()
        self.gc_added_removed()
        self.aoc_added_removed()
        self.update_aoc()
        self.udpate_gc()
        self.shuffle_aoc_files()

    def get_gc_aocal(self):
        """Read in the aocals containing the google data -- NEW should be a new one which gets populated via self.get_google_calendar"""
        gcname_old = f"{self.google_cal_name.replace(' ', '_')}_OLD.json"
        gcname_new = f"{self.google_cal_name.replace(' ', '_')}_NEW.json"

        self.gc_new_cal = aocalendar.Calendar(gcname_new, output=self.output, path=self.path, file_logging=self.file_logging, start_new=True)
        self.gc_old_cal = aocalendar.Calendar(gcname_old, path=self.path, start_new=True)
        self.gc_old_cal.make_hash_keymap(cols=self.attrib2push)

    def get_aoc_aocal(self):
        """Read in the working aocal, as well as the previous for diff."""
        self.aocal = aocalendar.Calendar(path=self.path, start_new=True)
        self.aocal.make_hash_keymap(cols=self.attrib2push)
        archive_cal_filename = self.aocal.calfile_fullpath.split('.')[0] + '_OLD.json'
        self.aoarc = aocalendar.Calendar(archive_cal_filename, path=self.path, start_new=True)
        self.aoarc.make_hash_keymap(cols=self.attrib2push)

    def get_google_calendar(self, show=False):
        """Read in the google calendar and populate the gc aocal"""
        if DEBUG_SKIP_GC:
            try:
                self.gc_new_cal.make_hash_keymap(cols=self.attrib2push)
            except AttributeError:
                logger.error("DEBUG: NEED TO READ IN AOC calendars.")
                raise RuntimeError("In DEBUG need to first read in calendar.")
            return

        for event in self.gc.get_events(calendar_id=self.gc_cal_id):
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
            self.gc_new_cal.add(**entry)
        if show:
            for day in self.gc_new_cal.events:
                logger.info(self.gc_new_cal.format_day_events(day, cols=list(aocalendar.ENTRY_FIELDS.keys())) + '\n')
        self.gc_new_cal.write_calendar()
        self.gc_new_cal.make_hash_keymap(cols=self.attrib2push)

    def __end_check_ok(self, entry_end, tbuf_min=35.0):
        """If self.future_only make sure utc_stop is more than tbuf_min in the past."""
        is_old = self.now < (entry_end - TimeDelta(tbuf_min * 60.0, format='sec'))
        if self.future_only and is_old:
            return False
        return True

    def gc_added_removed(self):
        """Get the diffs between the OLD and NEW google aocals"""
        self.gc_added = []  # hash in self.gc_new_cal that weren't in self.gc_old_cal
        self.gc_removed = []  # hash in self.gc_old_cal that aren't in self.gc_new_cal
        for hh in self.gc_new_cal.hashmap:
            d, n = self.gc_new_cal.hashmap[hh]
            if hh not in self.gc_old_cal.hashmap and self.__end_check_ok(self.gc_new_cal.events[d][n].utc_stop):
                self.gc_added.append(hh)
        for hh in self.gc_old_cal.hashmap:
            d, n = self.gc_old_cal.hashmap[hh]
            if hh not in self.gc_new_cal.hashmap and self.__end_check_ok(self.gc_old_cal.events[d][n].utc_stop):
                self.gc_removed.append(hh)

    def aoc_added_removed(self):
        """Get the diffs between the OLD and NEW aocals"""
        self.aoc_added = []
        self.aoc_removed = []
        for hh in self.aocal.hashmap:
            d, n = self.aocal.hashmap[hh]
            if hh not in self.aoarc.hashmap and self.__end_check_ok(self.aocal.events[d][n].utc_stop):
                self.aoc_added.append(hh)
        for hh in self.aoarc.hashmap:
            d, n = self.aoarc.hashmap[hh]
            if hh not in self.aocal.hashmap and self.__end_check_ok(self.aoarc.events[d][n].utc_stop):
                self.aoc_removed.append(hh)

    def update_aoc(self):
        """Update the aocal with the google calendar diffs -- aocal is now correct."""
        # Add new ones in google calendar to aocalendar
        logger.info(f"Adding {len(self.gc_added)} to {self.aocal.calfile}")
        changes_made = 0
        for hkey in self.gc_added:
            if hkey not in self.aocal.hashmap and hkey not in self.aoc_removed:
                add_entry = self.gc_new_cal.events[self.gc_new_cal.hashmap[hkey][0]][self.gc_new_cal.hashmap[hkey][1]].todict(printable=False, include_meta=True)
                self.aocal.add(**add_entry)
                changes_made += 1
        logger.info(f"Removing {len(self.gc_removed)} from {self.aocal.calfile}")
        for hkey in self.gc_removed:
            if hkey in self.aocal.hashmap and hkey not in self.aoc_added:
                self.aocal.delete(self.gc_old_cal.hashmap[hkey][0], self.gc_old_cal.hashmap[hkey][1])
                changes_made += 1
        if changes_made:
            self.aocal.write_calendar()
        else:
            logger.info(f"No changes made to {self.aocal.calfile_fullpath}")
        self.aocal.make_hash_keymap(cols=self.attrib2push)

    def udpate_gc(self):
        """Update the google aocal with the updated aocal from self.update_aoc and sync up to Google Calendar"""
        ctr = 0  # count additions to Google Calendar
        for hh, entry in self.aocal.hashmap.items():
            if hh not in self.gc_new_cal.hashmap:
                start = self.aocal.events[entry[0]][entry[1]].utc_start.datetime
                end = self.aocal.events[entry[0]][entry[1]].utc_stop.datetime
                # creator = self.aocal[entry[0]][entry[1]].email
                # description = self.aocal[entry[0]][entry[1]].pid
                summary = self.aocal.events[entry[0]][entry[1]].name
                event = Event(summary, start=start, end=end, timezone='GMT')
                try:
                    event = self.gc.add_event(event, calendar_id=self.gc_cal_id)
                except RuntimeError:  # Don't know what errors might happen...?
                    logger.error(f"Error adding {entry}")
                    continue
                ctr += 1
        logger.info(f"Adding {ctr} to Google Calendar {self.google_cal_name}")
        ctr = 0  # count removals from Google Calendar
        for hh in self.aoc_removed:
            if hh in self.gc_new_cal.hashmap:
                entry = self.gc_new_cal.hashmap[hh]
                try:
                    event_id = self.gc_new_cal.events[entry[0]][entry[1]].event_id
                except AttributeError:
                    logger.info(f"Event {entry} didn't have an event_id")
                    continue
                try:
                    self.gc.delete_event(event_id, calendar_id=self.gc_cal_id)
                except RuntimeError:  # Don't know what errors might happen...?
                    logger.error(f"Error deleting {entry}")
                    continue
                ctr += 1
        logger.info(f"Removing {ctr} from Google Calendar {self.google_cal_name}")

    def shuffle_aoc_files(self):
        """Move the NEW calendars to OLD and delete the NEW google aocal"""
        try:
            os.remove(self.gc_old_cal.calfile_fullpath)
        except OSError:
            pass
        try:
            shutil.copy2(self.gc_new_cal.calfile_fullpath, self.gc_old_cal.calfile_fullpath)
        except OSError:
            pass
        try:
            os.remove(self.gc_new_cal.calfile_fullpath)
        except OSError:
            pass
        try:
            os.remove(self.aoarc.calfile_fullpath)
        except OSError:
            pass
        try:
            shutil.copy2(self.aocal.calfile_fullpath, self.aoarc.calfile_fullpath)
        except OSError:
            pass

def show_stuff(gc):
    from tabulate import tabulate

    data = []
    for event in gc.get_events(calendar_id=ATA_CAL_ID):
        row = {}
        for col in dir(event):
            if col[0] != '_':
                entry = getattr(event, col)
                if str(entry)[0] != '<' and bool(entry):
                    row[col] = str(entry)
        data.append(row)
        # if event.summary == 'TEST':
        #     delevent = event
    hdr = sorted(data[0].keys())
    table = []
    for d in data:
        trow = []
        for key in hdr:
            try:
                trow.append(d[key][:20])
            except KeyError:
                trow.append('  ')
        table.append(trow)
    print(tabulate(table, headers=hdr))


