# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.
from copy import copy
from astropy.time import Time
from astropy.coordinates import EarthLocation
from astropy import units as u
from . import aoc_tools
from tabulate import tabulate
from hashlib import sha256


ENTRY_FIELDS = {'name': "Name", 'pid': "pid",
                'utc_start': None, 'utc_stop': None, 'lst_start': None, 'lst_stop': None,
                'observer': None, 'email': None, 'note': None, 'state': 'primary', 'recurring': [], 
                'location': None}
SHORT_LIST = ['name', 'pid', 'utc_start', 'utc_stop', 'lst_start', 'lst_stop', 'observer', 'state']
UNIQUE_HASH_LIST = ['name', 'pid', 'utc_start', 'utc_stop', 'observer', 'note', 'state']


def cull_args(**kwargs):
    """Remove non-Entry keys"""
    newkw = {}
    for key, val in kwargs.items():
        if key in ENTRY_FIELDS:
            newkw[key] = val
    return newkw


class Entry:
    def __init__(self, **kwargs):
        self.meta_fields = ['created', 'modifield', 'event_id']
        self.fields = kwargs['fields'] if 'fields' in kwargs else ENTRY_FIELDS
        for key in self.fields:
            if isinstance(self.fields, dict):
                setattr(self, key, self.fields[key])
            else:
                setattr(self, key, None)
        kwargs['created'] = kwargs['created'] if 'created' in kwargs else 'now'
        self.created = aoc_tools.interp_date(kwargs['created'], fmt='Time')
        self.modified = self.created
        self.event_id = copy(kwargs['event_id']) if 'event_id' in kwargs else 'AOC'
        for key in self.meta_fields:  # Handled them above
            if key in kwargs: del(kwargs[key])
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

    def update(self, **kwargs):
        """Update an entry using the supplied kwargs."""
        self.msg, kwctr, self.valid = [], 0, True
        for key, val in kwargs.items():
            if key in self.fields:
                if key not in ['utc_start', 'utc_stop']:
                    kwctr += 1
                if val is not None:
                    setattr(self, key, val)
            elif key in self.meta_fields:
                if key == 'modified':
                    self.modified = aoc_tools.interp_date(val, fmt='Time')
                elif key == 'event_id':
                    self.event_id = val
        # Deal with Time
        for key in ['utc_start', 'utc_stop']:
            try:
                setattr(self, key, aoc_tools.interp_date(getattr(self, key), fmt='Time'))
            except ValueError:
                self.msg.append(f'Need valid {key} - got {getattr(self, key)}')
                self.valid = False        
        if not kwctr:
            self.msg.append(f"Need at least one non-time entry.")
            self.valid = False
        # Deal with EarthLocation
        location = copy(getattr(self, 'location'))
        if isinstance(location, EarthLocation):
            pass
        elif isinstance(location, str):
            llh = {}
            for l in location.split(','):
                key, val = l.split('=')
                llh[key] = float(val)
            self.location = EarthLocation(lat=llh['lat']*u.deg, lon=llh['lon']*u.deg, height=llh['height']*u.m)
        else:
            self.valid = False
            self.msg.append("Invalid location.  Using Greenwich")
            self.location = EarthLocation(lat=0.0*u.deg, lon=0.0*u.deg, height=0.0*u.m)

        self.msg = 'ok' if self.valid else '\n'.join(self.msg)
        self.modified = aoc_tools.interp_date('now', fmt='Time')
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
                    try:
                        entry[col] = getattr(self, col).datetime.isoformat(timespec='seconds')
                    except AttributeError:
                        entry[col] = "INVALID"
                elif col in ['lst_start', 'lst_stop']:
                    try:
                        hms = getattr(self, col).hms
                        entry[col] = f"{int(hms.h):02d}h{int(hms.m):02d}m{int(hms.s):02d}s"
                    except AttributeError:
                        entry[col] = "INVALID"
                elif col == 'recurring':
                    pass
                elif col == 'location':
                    entry[col] = f"lat={self.location.lat.value},lon={self.location.lon.value},height={self.location.height.value}"
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
            entry['event_id'] = self.event_id

        return entry

    def update_lst(self):
        """Update the LSTs."""
        try:
            self.utc_start = Time(self.utc_start)
            self.utc_stop = Time(self.utc_stop)
        except ValueError:
            self.valid = False
            self.msg += '\nNo LST, unable to make Time'
            return
        obstimes = Time([self.utc_start, self.utc_stop])
        self.lst_start, self.lst_stop = obstimes.sidereal_time('mean', longitude=self.location)