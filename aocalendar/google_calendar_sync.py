# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from datetime import datetime
from aocalendar import aocalendar
from copy import copy
import os, shutil

DEBUG_SKIP_GC = False


ATA_CAL_ID = 'jhutdq684fs4hq7hpr3rutcj5o@group.calendar.google.com'
ATTRIB2KEEP = {'creator': 'email', 'end': 'utc_stop', 'start': 'utc_start', 'summary': 'name',
               'event_id': 'event_id', 'updated': 'created', 'timezone': '_convert2utc'}
# Using updated for created, since the google one is "bad"
# need to get start/end to right time zone, which is ok since they use UTC also
ATTRIB2PUSH = {'email': 'creator', 'utc_stop': 'end', 'utc_start': 'start', 'name': 'summary'}

class SyncCal:
    def __init__(self, cal_id=ATA_CAL_ID, attrib2keep=ATTRIB2KEEP, attrib2push=ATTRIB2PUSH):
        self.gc_cal_id = cal_id
        self.attrib2keep = attrib2keep
        self.attrib2push = attrib2push

        if DEBUG_SKIP_GC:
            self.google_cal_name = 'Allen Telescope Array Observing'
        else:
            self.gc = GoogleCalendar()
            ata = self.gc.get_calendar_list_entry(self.gc_cal_id)
            self.google_cal_name = ata.summary

    def get_gc_aocal(self):
        gcname_old = f"{self.google_cal_name.replace(' ', '_')}_OLD.json"
        gcname_new = f"{self.google_cal_name.replace(' ', '_')}_NEW.json"

        self.gc_new_cal = aocalendar.Calendar(gcname_new, path='getenv', start_new=True)
        self.gc_old_cal = aocalendar.Calendar(gcname_old, path='getenv', start_new=True)
        self.gc_old_cal.make_hash_keymap()

    def get_aoc_aocal(self):
        self.aocal = aocalendar.Calendar(start_new=True)
        self.aocal.make_hash_keymap()
        archive_cal_filename = self.aocal.calfile_fullpath.split('.')[0] + '_OLD.json'
        self.aoarc = aocalendar.Calendar(archive_cal_filename, start_new=True)
        self.aoarc.make_hash_keymap()

    def get_google_calendar(self, show=False):
        if DEBUG_SKIP_GC:
            try:
                self.gc_new_cal.make_hash_keymap()
            except AttributeError:
                print("NEED TO READ IN AOC calendars.")
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
                print(self.gc_new_cal.format_day_events(day, cols=list(aocalendar.ENTRY_FIELDS.keys())) + '\n')
        self.gc_new_cal.write_calendar()
        self.gc_new_cal.make_hash_keymap()

    def gc_added_removed(self):
        self.gc_added = []  # hash in self.gc_new_cal that weren't in self.gc_old_cal
        self.gc_removed = []  # hash in self.gc_old_cal that aren't in self.gc_new_cal
        for hh in self.gc_new_cal.hashmap:
            if hh not in self.gc_old_cal.hashmap:
                self.gc_added.append(hh)
        for hh in self.gc_old_cal.hashmap:
            if hh not in self.gc_new_cal.hashmap:
                self.gc_removed.append(hh)

    def aoc_added_removed(self):
        self.aoc_added = []
        self.aoc_removed = []
        for hh in self.aocal.hashmap:
            if hh not in self.aoarc.hashmap:
                self.aoc_added.append(hh)
        for hh in self.aoarc.hashmap:
            if hh not in self.aocal.hashmap:
                self.aoc_removed.append(hh)

    def update_aoc(self):
        # Add new ones in google calendar to aocalendar
        print(f"Adding {len(self.gc_added)}")
        for hkey in self.gc_added:
            if hkey not in self.aocal.hashmap and hkey not in self.aoc_removed:
                add_entry = self.gc_new_cal.events[self.gc_new_cal.hashmap[hkey][0]][self.gc_new_cal.hashmap[hkey][1]].todict(printable=False, include_meta=True)
                self.aocal.add(**add_entry)
        print(f"Removing {len(self.gc_removed)}")
        for hkey in self.gc_removed:
            if hkey in self.aocal.hashmap and hkey not in self.aoc_added:
                self.aocal.delete(self.gc_old_cal.hashmap[hkey][0], self.gc_old_cal.hashmap[hkey][1])
        self.aocal.write_calendar()
        self.aocal.make_hash_keymap()

    def udpate_gc(self):
        ctr = 0
        for hh, entry in self.aocal.hashmap.items():
            if hh not in self.gc_new_cal.all_hash:
                start = self.aocal.events[entry[0]][entry[1]].utc_start.datetime
                end = self.aocal.events[entry[0]][entry[1]].utc_stop.datetime
                #creator = self.aocal[entry[0]][entry[1]].email
                summary = self.aocal.events[entry[0]][entry[1]].name
                ctr += 1
                event = Event(summary, start=start, end=end)
                print("SKIPPING ACTUAL ADD")
                # event = self.gc.add_event(event, calendar_id=self.gc_cal_id)
        print(f"Added {ctr} to Google Calendar")
        ctr = 0
        for hh in self.aoc_removed:
            if hh in self.gc_new_cal.all_hash:
                entry = self.gc_new_cal.hashmap[hh]
                try:
                    event_id = self.gc_new_cal.events[entry[0]][entry[1]].event_id
                except (KeyError, AttributeError):
                    print(f"DIDN'T FIND {entry}")
                    continue
                try:
                    print("SKIPPING ACTUAL DELETE")
                    #self.gc.delete_event(event_id, calendar_id=self.gc_cal_id)
                except AttributeError:  # Don't know what errors...
                    continue
                ctr += 1
        print(f"Removed {ctr} from Google Calendar")

    def shuffle_aoc_files(self):
        # Now move calendars to OLD etc
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


