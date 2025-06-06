# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.
from copy import copy
from . import tools
from tabulate import tabulate
from hashlib import sha256
from odsutils import locations
from odsutils import ods_timetools as ttools


ENTRY_FIELDS = {'program': "program",
                'pid': "pid",
                'utc_start': None, 'utc_stop': None,
                'lst_start': None, 'lst_stop': None,
                'observer': '',
                'email': '',
                'note': '',
                'commensal': 'primary', 
                'recurring': [], 
                'location': 'ata',
                'event_id': 'AOC'}
SHORT_LIST = ['program', 'pid', 'utc_start', 'utc_stop', 'lst_start', 'lst_stop', 'observer', 'commensal']
UNIQUE_HASH_LIST = ['program', 'pid', 'utc_start', 'utc_stop', 'observer', 'note', 'commensal']
WEB_COMPARE_HASH_LIST = ['program', 'utc_start', 'utc_stop']
META_FIELDS = ['created', 'modified']


class Entry:
    """AO Calendar Entry"""
    def __init__(self, **kwargs):
        """
        AOCalendar entry.

        Parameters
        ----------
        kwargs are entry fields or meta_fields

        """
        self.meta_fields = META_FIELDS
        self.fields = list(ENTRY_FIELDS.keys())
        self.update(**ENTRY_FIELDS)
        kwargs['created'] = kwargs['created'] if 'created' in kwargs else 'now'
        self.created = ttools.interpret_date(kwargs['created'], fmt='Time')
        if len(kwargs):
            self.update(**kwargs)

    def __str__(self):
        try:
            s = f"CALENDAR ENTRY {self.utc_start.datetime.strftime('%Y')}\n"
        except AttributeError:
            s = "BLANK ENTRY "
        s+= f"created: {self.created.datetime.isoformat(timespec='seconds')}"
        if self.modified != self.created:
            s+= f"  --  modified: {self.modified.datetime.isoformat(timespec='seconds')}"
        s += "\n\n"
        data = self.todict(printable=True)
        table = []
        for key, val in data.items():
            table.append([key, val])
        s += tabulate(table, headers=['Field', 'Value']) + '\n'
        return s

    def __EarthLocation(self, loc_input, to_string=False):
        """Take in a location input and make an EarthLocation or stringify EarthLocation"""
        if to_string:
            return loc_input.stringify()
        new_location = locations.Location(loc_input)
        try:
            new_location = new_location
        except AttributeError:
            new_location = "None"
        return new_location
    
    def __Time(self, time_input, key, to_string=False):
        """Take in a time input and return Time"""
        if to_string:
            return ttools.interpret_date(time_input, fmt='isoformat', NoneReturn='None')
        new_Time = ttools.interpret_date(time_input, fmt='Time', NoneReturn=None)
        if new_Time is None:
            try:
                new_Time = getattr(self, key)
            except AttributeError:
                new_Time = None
        return new_Time

    def __lst(self, lst_input, key, to_string=False):
        if to_string:
            try:
                hms = lst_input.hms
                return f"{int(hms.h):02d}h{int(hms.m):02d}m{int(hms.s):02d}s"
            except AttributeError:
                return None
        print("NOT YET", key)

    def __recurring(self, recurring_input, to_string=False):
        if to_string:
            return ','.join(recurring_input)

        if isinstance(recurring_input, list):
            return recurring_input
        if isinstance(recurring_input, str):
            new_recurring = recurring_input.split(',')
        else:
            try:
                new_recurring = getattr(self, 'recurring')
            except AttributeError:
                new_recurring = [] 
        return new_recurring

    def update(self, **kwargs):
        """Update an entry using the supplied kwargs.  This handles both 'native' as well as 'todict/printable'"""
        updated_kwargs = {}
        for key, val in kwargs.items():
            if key in self.fields:
                updated_kwargs[key] = val
            elif key in self.meta_fields:
                if key == 'modified':
                    self.modified = ttools.interpret_date(val, fmt='Time')
        if 'utc_start' in kwargs:
            updated_kwargs['utc_start'] = self.__Time(kwargs['utc_start'], 'utc_start', to_string=False)
        if 'utc_stop' in kwargs:
            updated_kwargs['utc_stop'] = self.__Time(kwargs['utc_stop'], 'utc_stop', to_string=False)
        if 'location' in kwargs:
            updated_kwargs['location'] = self.__EarthLocation(kwargs['location'], to_string=False)
        if 'recurring' in kwargs:
            updated_kwargs['recurring'] = self.__recurring(kwargs['recurring'], to_string=False)

        for key, val in updated_kwargs.items():
            setattr(self, key, val)

        self.valid, self.msg = True, []
        for key in ['utc_start', 'utc_stop']:
            if not tools.boolcheck(getattr(self, key)):
                self.valid = False
                self.msg.append(f"Invalid {key} - {getattr(self, key)}")
        is_ok = 0
        for key in ['program', 'observer', 'note', 'commensal']:
            this_attr = getattr(self, key)
            if this_attr is not None and len(this_attr):
                is_ok += 1
        if not is_ok:
            self.valid = False
            self.msg.append("Need at least one non-Time entry")

        self.msg = 'ok' if self.valid else '\n'.join(self.msg)
        self.modified = ttools.interpret_date('now', fmt='Time')
        # Always recompute LST
        self.update_lst()

    def row(self, cols='all', printable=True, include_meta=False):
        """
        Return the entry as a list.

        Parameters
        ----------
        cols : list or 'all' or 'unique'
            Columns to include
        printable : bool
            Flag to make the entries all str

        """
        if cols == 'all':
            cols = self.fields
        elif cols == 'unique':
            cols = UNIQUE_HASH_LIST
        elif cols == 'web':
            cols = WEB_COMPARE_HASH_LIST
        entry = self.todict(printable=printable, include_meta=include_meta)
        row = [entry[col] for col in cols]
        return row
    
    def hash(self, cols='unique'):
        """Return the hash of the entry"""
        txt = ''.join(self.row(cols=cols, printable=True)).encode('utf-8')
        return sha256(txt).hexdigest()[:10]
    
    def todict(self, printable=True, include_meta=False):
        """
        Return the dictionary of an event.

        Parameter
        ---------
        printable : bool
            Flag to make entries printable str

        """
        entry = {}
        for col in self.fields:
            if printable:
                if col in ['utc_start', 'utc_stop']:
                    entry[col] = self.__Time(getattr(self, col), col, to_string=True)
                elif col in ['lst_start', 'lst_stop']:
                    entry[col] = self.__lst(getattr(self, col), col, to_string=True)
                elif col == 'recurring':
                    entry[col] = self.__recurring(getattr(self, col), to_string=True)
                elif col == 'location':
                    entry[col] = self.__EarthLocation(getattr(self, col), to_string=True)
                else:
                    entry[col] = str(getattr(self, col))
            else:
                entry[col] = copy(getattr(self, col))
        if include_meta:
            if printable:
                entry['created'] = self.created.datetime.isoformat(timespec='seconds')
                entry['modified'] = self.modified.datetime.isoformat(timespec='seconds')
            else:
                entry['created'] = self.created
                entry['modified'] = self.modified

        return entry

    def update_lst(self):
        """Update the LSTs."""
        for key in ['utc_start', 'utc_stop']:
            try:
                utc = ttools.interpret_date(getattr(self, key), fmt='Time')
            except AttributeError:
                utc = None
            if utc is not None:
                lst = f"lst_{key.split('_')[1]}"
                setattr(self, lst, utc.sidereal_time('mean', longitude=self.location.loc))