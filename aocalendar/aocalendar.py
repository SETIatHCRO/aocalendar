# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

import json
from astropy.time import Time, TimeDelta
from datetime import datetime
from tabulate import tabulate
from copy import copy
import logging
from sys import stdout
from astropy.coordinates import EarthLocation, Angle, AltAz, SkyCoord
from astropy.time import Time
from astropy import units as u
from os import path as op
from hashlib import sha256
from numpy import floor, round
from numpy import where as npwhere
from os import getenv
from . import __version__, aoc_tools, logger_setup
try:
    from ATATools.ata_sources import check_source  # type: ignore
except ImportError:
    def check_source(src):
        return 'Not Available'


logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')  # Set to lowest

ATA = EarthLocation(lat=40.817431*u.deg, lon=-121.470736*u.deg, height=1019*u.m)
ENTRY_FIELDS = {'name': "Name", 'pid': "pid",
                'utc_start': None, 'utc_stop': None, 'lst_start': None, 'lst_stop': None,
                'observer': None, 'email': None, 'note': None, 'state': 'primary'}
PATH_ENV = 'AOCALENDAR'
AOC_PREFIX = 'aocal'
AOCLOG_FILENAME = 'aoclog'
SHORT_LIST = ['name', 'pid', 'utc_start', 'utc_stop', 'lst_start', 'lst_stop', 'observer', 'state']
DAYSEC = 24 * 3600


def aoc_entry(path='getenv', output='ERROR', **kwargs):
    """
    Simple access to AOCalendar to add entry.

    Parameters
    ----------
    path : str
        Path to use.  Default retrieves AOCALENDAR from environment
    output : str
        Logging output to use.  Default is ERROR
    kwargs : fields for entry.  Must have at least utc_start, utc_stop and one more.

    Returns
    -------
    str : if not successful then '', otherwise either 'ok' or csv-list of conflicts

    """
    msg = ''
    if 'utc_start' not in kwargs:
        logger.error("utc_start not included.")
        return msg
    cal = Calendar(kwargs['utc_start'], path=path, output=output)
    is_added = cal.add(**kwargs)
    msg = ''
    if is_added and cal.recent_event.valid:
        logger.info(cal.recent_event)
        cal.write_calendar()
        if len(cal.results['conflict']):
            msg = ','.join([str(x) for x in cal.results['conflict']])
            logger.warning(f"Entry conflicts with {msg}")
        else:
            msg = 'ok'
    logger.error(f"Entry add was unsuccessful.\n{cal.recent_event.msg}")
    return msg


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
        s = f"CALENDAR ENTRY {self.utc_start.datetime.strftime('%Y')}\n"
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
        for key in ['utc_start', 'utc_stop']:
            try:
                setattr(self, key, aoc_tools.interp_date(getattr(self, key), fmt='Time'))
            except ValueError:
                self.msg.append(f'Need valid {key} - got {getattr(self, key)}')
                self.valid = False
        if not kwctr:
            self.msg.append(f"Need at least one non-time entry.")
            self.valid = False
        self.msg = 'ok' if self.valid else '\n'.join(self.msg)
        self.modified = aoc_tools.interp_date('now', fmt='Time')
        # Always recompute LST
        self.update_lst()

    def row(self, cols='all', printable=True, include_meta=False):
        """
        Return the entry as a list.

        Parameters
        ----------
        cols : list or 'all'
            Columns to include
        printable : bool
            Flag to make the entries all str

        """
        if cols == 'all': cols = self.fields
        entry = self.todict(printable=printable, include_meta=include_meta)
        row = [entry[col] for col in cols]
        return row
    
    def hash(self, cols='all'):
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
        self.lst_start, self.lst_stop = obstimes.sidereal_time('mean', longitude=ATA)


class Calendar:
    meta_fields = ['created', 'updated']

    def __init__(self, calfile='now', path='getenv', output='INFO', file_logging=False, start_new=False):
        """
        Parameters
        ----------
        calfile : str
            interpreted by set_calfile
        path : str
            get path for location of aocal files and logs etc, interpreted by determine_path
        output : str
            Logging output level
        start_new : bool
            Flag to start empty one if file not found.

        """
        self.path = aoc_tools.determine_path(path, calfile)
        self.refdate = Time.now()
        logger_setup.setup(logger, output=output, file_logging=file_logging, log_filename=AOCLOG_FILENAME, path=self.path)
        logger.info(f"{__name__} ver. {__version__}")
        self.read_calendar_events(calfile=calfile, path=None, skip_duplicates=True, start_new=start_new)

    def set_calfile(self, calfile, path=None):
        """
        Parameters
        ----------
        calfile : str
            calfile or something interpretable by aoc_tools.interp_date
        path : str
            path or 'getenv' - if calfile has path, gets overwritten, if None use self.path

        Attributes
        ----------
        calfile : str
            Basename of calfile
        calfile_fullpath : str
            path/calfile
        refdate : Time
            reference date for calfile

        """
        if calfile == 'refresh':
            return
        if path is None: path = self.path
        if isinstance(calfile, str) and calfile.endswith('.json'):
            dn = op.dirname(calfile)
            if len(dn):
                path = dn
            calfile = op.basename(calfile)
            try:
                year = int(calfile.split('.')[0][-4:])
                self.refdate = Time(datetime(year=year, month=1, day=1))
            except ValueError:
                self.refdate = Time.now()
        else:
            self.refdate = aoc_tools.interp_date(calfile, 'Time')
            calfile = f"{AOC_PREFIX}{self.refdate.datetime.year}.json"
        self.calfile = calfile
        self.calfile_fullpath = op.join(path, calfile)

    def read_calendar_events(self, calfile, path=None, skip_duplicates=True, start_new=False):
        """
        Reads a cal json file -- it will "fix" any wrong day entries.

        Parameters
        ----------
        calfile : str
            Can be a json file, or a date all the way from YYYY to YYYY-MM-DDT...
        path : str
            Path to find the file - 'getenv' will read the environmen variable OBSCALENDAR
        skip_duplicates : bool
            Flag to not include duplicated entries

        Attributes
        ----------
        events : dict
            Contents of file
        straddle : dict
            Extra info for entries straddling a day
        all_fields : list
            List of all of the entry fields
        all_hash : list
            List of all entry hashes

        """
        self.events = {}
        self.straddle = {}
        self.all_fields =  list(ENTRY_FIELDS.keys())  # This is a cheat for now.
        self.all_hash = []
        self.set_calfile(calfile=calfile, path=path)
        try:
            with open(self.calfile_fullpath, 'r') as fp:
                inp = json.load(fp)
        except FileNotFoundError:
            if start_new:
                atime = Time.now().datetime.isoformat(timespec="seconds")
                inp = {'created': atime, 'updated': atime}
                with open(self.calfile_fullpath, 'w') as fp:
                    json.dump(inp, fp)                    
                logger.info(f"No calendar file was found at {self.calfile_fullpath} -- started new.")
            else:
                logger.warning(f"No calendar file was found at {self.calfile_fullpath}.")
                return
        logger.info(f"Reading {self.calfile_fullpath}")
        for key, entries in inp.items():
            if key in self.meta_fields:
                setattr(self, key, entries)
            else:
                keydate = Time(key)
                self.events.setdefault(key, [])
                for i, event in enumerate(entries):
                    this_event = Entry(**event)
                    this_hash = this_event.hash()
                    if this_hash in self.all_hash:
                        logger.warning(f"Entry {key}:{i} is a duplicate.")
                        if skip_duplicates:
                            logger.warning("Skipping entry")
                            continue
                    else:
                        self.all_hash.append(this_hash)
                    if not this_event.valid:
                        logger.warning(f"Entry {key}:{i} invalid")
                    if not aoc_tools.same_date(keydate, this_event.utc_start, timespec='day'):
                        keystr = this_event.utc_start.datetime.strftime("%Y-%m-%d")
                        logger.info(f"{keystr} in wrong day.")
                    else:
                        keystr = keydate.datetime.strftime("%Y-%m-%d")
                    self.events.setdefault(keystr, [])
                    self.events[keystr].append(this_event)
                    try:
                        endkeystr = this_event.utc_stop.datetime.strftime("%Y-%m-%d")
                        if endkeystr != keystr:
                            self.straddle.setdefault(endkeystr, [])
                            self.straddle[endkeystr].append(this_event)
                    except AttributeError:  # Problem with utc_stop, probably INVALID
                        continue

    def write_calendar(self, calfile=None):
        """
        Write the calendar out to a file.

        Parameter
        ---------
        calfile : str or None
            If None, use self.calfile_fullpath

        """
        if calfile is None:
            calfile = self.calfile_fullpath
        logger.info(f"Writing {calfile}")
        full_events = {}
        for md in self.meta_fields:
            if md == 'updated':
                self.updated = Time.now().datetime.isoformat(timespec='seconds')
            full_events[md] = getattr(self, md)
        for key, val in self.events.items():
            full_events[key] = []
            for event in val:
                full_events[key].append(event.todict(printable=True, include_meta=True))
            if not len(full_events[key]):
                del(full_events[key])
        with open(calfile, 'w') as fp:
           json.dump(full_events, fp, indent=2)

    def make_hash_keymap(self, cols='all'):
        """
        For purposes of checking calendars etc, make a hash-key to entry (day, #) map

        """
        self.hashmap = {}
        for day, events in self.events.items():
            for i, event in enumerate(events):
                this_hash = event.hash(cols=cols)
                if this_hash in self.hashmap:
                    oth = self.hashmap[this_hash]
                    logger.warning(f"This event ({day}:{i}) has same hash as ({oth[0]}:{oth[1]}) and will overwrite.")
                self.hashmap[this_hash] = (day, i)

    def sort_day(self, day):
        """
        Sort the events per day by utc_start,utc_stop.

        Parameter
        ---------
        day : str/Time/etc
            Date info for day

        Return
        ------
        sorted_day : list
            List of sorted events
        indmap : dict
            Index map between sorted and stored, key is sorted order.

        """
        day = aoc_tools.interp_date(day, fmt='%Y-%m-%d')
        sorted_dict = {}
        offset = 0
        if day in self.straddle:
            for i, event in enumerate(self.straddle[day]):
                key = (event.utc_start, event.utc_stop, i)
                offset += 1
                sorted_dict[key] = {'event': copy(event), 'index': -offset}
        if day in self.events:
            for i, event in enumerate(self.events[day]):
                key = (event.utc_start, event.utc_stop, i)
                sorted_dict[key] = {'event': copy(event), 'index': i}
        sorted_day = []
        indmap = {}
        for i, key in enumerate(sorted(sorted_dict)):
            if 'event' in sorted_dict[key]:
                sorted_day.append(sorted_dict[key]['event'])
                indmap[i] = sorted_dict[key]['index']
        return sorted_day, indmap

    def format_day_events(self, day='today', cols='short', return_as='table'):
        """
        Return a formatted table or array of the events on a day.

        Parameters
        ----------
        day : str/Time/etc
            Day to use.
        cols : str/list
            Columns to use or 'all' or 'short'
        return_as : str
            Return as 'table' or 'list'

        """
        if cols == 'all':
            cols = self.all_fields
        elif cols == 'short':
            cols = SHORT_LIST
        hdr = ['#'] + cols
        sorted_day, indmap = self.sort_day(day)
        if return_as == 'table':
            return(tabulate([[indmap[i]] + event.row(cols, printable=True, include_meta=False) for i, event in enumerate(sorted_day)], headers=hdr))
        else:
            return [[indmap[i]] + event.row(cols, printable=True, include_meta=False) for i, event in enumerate(sorted_day)], hdr
        
    def graph_day(self, day='today', header_col='name', tz='sys', interval_min=10.0):
        """
        Text-based graph of schedule sorted by start/stop times.

        Parameters
        ----------
        day : str/Time/etc
            Day to use
        header_col : str
            header to use
        tz : str
            timezone to use for extra line tz or 'sys'
        interval_min : float
            interval for graph in min

        """
        tz, tzoff = aoc_tools.get_tz(tz, aoc_tools.interp_date(day, fmt='Time').datetime)
        sorted_day, indmap = self.sort_day(day)
        if not len(sorted_day):
            return ' '
        cbuflt, cbufind, cbufrt = 2, 3, 2
        stroff = max([len(getattr(x, header_col)) for x in sorted_day])  # This is max name
        colhdr = [f"{cbuflt*' '}{indmap[i]:>{cbufind-1}d}-{getattr(x, header_col):{stroff}s}{cbufrt*' '}" for i, x in enumerate(sorted_day)]
        stroff += (cbuflt + cbufind + cbufrt)  # Now add the extra

        day = aoc_tools.interp_date(day, fmt='%Y-%m-%d')
        start_of_day = Time(day)
        end_of_day = start_of_day + TimeDelta(DAYSEC, format='sec')
        interval_sec = interval_min * 60.0
        numpoints = int(DAYSEC / interval_sec)
        dt = ((end_of_day - start_of_day) / (numpoints-1)).to('second').value

        current = int((Time.now() - start_of_day).to('second').value / dt)
        show_current = True if (current > -1 and current < numpoints) else False

        # Set up ticks/labels
        sm = numpoints + 5
        tickrow = [' '] * (numpoints + 1)
        trow = {'UTC': {'labels': [' ']*sm}, 'LST': {'labels': [' ']*sm}, tz: {'labels': [' ']*sm}}
        trow['UTC']['times'] = Time([start_of_day + TimeDelta(int(x)*3600.0, format='sec') for x in range(0, 25, 2)])
        trow['LST']['times'] =  trow['UTC']['times'].sidereal_time('mean', longitude=ATA)
        trow[tz]['times'] = trow['UTC']['times'] + TimeDelta(tzoff*3600, format='sec')
        for i, utc in enumerate(trow['UTC']['times']):
            toff = int(round(24.0 * (utc - start_of_day).value) * 3600.0 / dt)
            tickrow[toff] = '|'
            for tt in trow:
                if tt == 'LST':
                    t = f"{trow[tt]['times'][i].value:.1f}"
                else:
                    t = f"{trow[tt]['times'][i].datetime.hour}"
                for j in range(len(t)):
                    trow[tt]['labels'][toff+j] = t[j]
        if show_current:
            tickrow[current] = '0'
        tickrow = ' ' * stroff + ''.join(tickrow)
        for tt in trow:
            tstr = f"{tt}  "
            trow[tt]['labels'] = ' ' * (stroff - len(tstr)) + tstr + ''.join(trow[tt]['labels'])
        
        # Get table string
        if tz != 'UTC':
            ss = f"\n\n{' '*stroff}{day} at interval {interval_min:.0f}m\n{trow['UTC']['labels']}\n{trow[tz]['labels']}\n{tickrow}\n"
        else:
            ss = f"\n\n{' '*stroff}{day} at interval {interval_min:.0f}m\n{trow['UTC']['labels']}\n{tickrow}\n"
        for i, entry in enumerate(sorted_day):
            row = ['.'] * numpoints
            if entry.utc_start < start_of_day:
                starting = 0
            else:
                starting = int(floor((entry.utc_start  -  start_of_day).to('second').value / dt))
            ending = int(floor((entry.utc_stop - start_of_day).to('second').value / dt)) + 1
            for star in range(starting, ending):
                try:
                    row[star] = '*'
                except IndexError:
                    pass
            if show_current:
                row[current] = 'X' if row[current] == '*' else '|'
            ss += f"{colhdr[i]}{''.join(row)}\n"
        ss += f"{tickrow}\n{trow['LST']['labels']}"
        return ss

    def check_kwargs(self, kwargs):
        try:
            utc_start = aoc_tools.interp_date(kwargs['utc_start'], fmt='Time')
        except KeyError:
            logger.error(f"Need a utc_start.")
            return kwargs
        utc_stop = kwargs['utc_stop'] if 'utc_stop' in kwargs else None
        utc_stop = aoc_tools.interp_date(utc_stop, fmt='Time') if aoc_tools.boolcheck(utc_stop) else None
        if utc_stop is None:
            lst_start = kwargs['lst_start'] if 'lst_start' in kwargs else None
            if lst_start is None:
                logger.error("Need an lst_start if no utc_stop")
                return kwargs
            else:
                utc_start = self.get_utc_from_lst(lst_start, utc_start)
            lst_stop = kwargs['lst_stop'] if 'lst_stop' in kwargs else None
            if lst_stop is None:
                logger.error("Need an lst_stop if no utc_stop")
                return kwargs
            else:
                utc_stop = self.get_utc_from_lst(lst_stop, utc_start)
                if utc_stop < utc_start:
                    utc_stop = self.get_utc_from_lst(lst_stop, utc_start + TimeDelta(DAYSEC, format='sec'))
        kwargs['utc_start'], kwargs['utc_stop'] = utc_start, utc_stop
        return kwargs

    def add(self, **kwargs):
        """
        Parameters
        ----------
        kwargs : fields to add

        """
        kwargs = self.check_kwargs(kwargs)
        this_event = Entry(**kwargs)
        self.recent_event = this_event
        this_hash = this_event.hash()
        self.results = self.conflicts(this_event, is_new=True)
        if len(self.results['duplicate']):
            suf = 'y' if len(self.results['duplicate']) == 1 else 'ies'
            logger.warning(f"Not adding -- duplicate with entr{suf}: {', '.join([str(x) for x in self.results['duplicate']])}.")
            return False
        if len(self.results['conflict']):
            suf = 'y' if len(self.results['conflict']) == 1 else 'ies'
            logger.warning(f"Overlaps with entr{suf}: {', '.join([str(x) for x in self.results['conflict']])}.")
        day = this_event.utc_start.datetime.strftime('%Y-%m-%d')
        self.events.setdefault(day, [])
        self.events[day].append(this_event)
        self.all_hash.append(this_hash)                
        if not this_event.valid:
            logger.warning(f"Entry invalid:\n{this_event.msg}")
        return True

    def delete(self, day, nind):
        """
        Parameters
        ----------
        day : str, etc
            Day input for interp_date
        nind : int
            Index number of that day

        """
        day = aoc_tools.interp_date(day, fmt='%Y-%m-%d')
        try:
            del(self.events[day][nind])
            return True
        except (KeyError, IndexError):
            logger.warning(f"Invalid entry: {day}, {nind}")
            return False

    def update(self, day, nind, **kwargs):
        """
        Parameters
        ----------
        day : str, etc
            Day input for interp_date
        nind : int
            Index number of that day
        kwargs : fields to add

        """
        day = aoc_tools.interp_date(day, fmt='%Y-%m-%d')
        kwargs['modified'] = kwargs['modified'] if 'modified' in kwargs else 'now'
        try:
            self.events[day][nind].update(**kwargs)
            self.recent = self.events[day][nind]
        except (KeyError, IndexError):
            logger.warning(f"{day}, {nind} not found.")
            return False
        this_hash = self.events[day][nind].hash()
        if this_hash in self.all_hash:
            logger.warning(f"You made {day}, {nind} a duplicate.")
        else:
            self.all_hash.append(this_hash)
        event_day = self.events[day][nind].utc_start.datetime.strftime('%Y-%m-%d')
        if day != event_day:
            logger.info(f"Changed day from {day} to {event_day}")
            move_entry = self.events[day][nind].todict(printable=False)
            move_entry['created'] = 'now'
            self.add(**move_entry)
            del(self.events[day][nind])
        return True

    def add_from_file(self, file_name, sep='auto'):
        data = aoc_tools.read_data_file(file_name=file_name, sep=sep)
        added, rejected = 0, 0
        for entry in data:
            is_ok = self.add(**entry)
            if is_ok:
                added += 1
            else:
                rejected += 1
        logger.info(f"Added {added} and rejected {rejected}")

    def get_utc_from_lst(self, lst, day):
        from numpy import argmax
        usedec = ATA.lat - 10.0 * u.deg
        _, obs = self.get_obs(ra=lst, dec=usedec, source='lst', day=day, duration=24.0, dt=1.0)
        alt = obs.alt.value
        maxalt = argmax(alt)
        return obs.obstime[maxalt]

    def get_obs(self, ra, dec, source, day, duration, dt = 10.0):
        day = aoc_tools.interp_date(day, fmt='Time')
        if aoc_tools.boolcheck(ra) and aoc_tools.boolcheck(dec):
            pass
        else:
            src = check_source(source)
            if src == 'Not Available':
                raise RuntimeError("Sources not available.")
            ra = src['ra']
            dec = src['dec']
        if isinstance(ra, (str, float, int)):
            try:
                ra = float(ra)
                ra = ra * u.hourangle
            except (TypeError, ValueError):
                pass
        if isinstance(ra, (str, float, int)):
            try:
                dec = float(dec)
                dec = dec * u.deg
            except (TypeError, ValueError):
                pass

        ra = Angle(ra)
        dec = Angle(dec)
        source = source if source is not None else f"{ra.to_string(precision=0)},{dec.to_string(precision=0)}"

        duration = TimeDelta(duration * 3600.0, format='sec')
        start = Time(datetime(year=day.datetime.year, month=day.datetime.month, day=day.datetime.day))
        stop = start + TimeDelta(24 * 3600, format='sec')
        dt = TimeDelta(dt * 60, format='sec')  # Use 10min
        current, times = copy(start), []
        while current < stop:
            times.append(current)
            current += dt
        altazsky = SkyCoord(ra, dec).transform_to(AltAz(location=ATA, obstime=times))
        return source, altazsky

    def schedule(self, ra=None, dec=None, source=None, day='now', duration=12, el_limit=15.0, **kwargs):
        """
        Schedule an observation at a given ra/dec or source on a given day for a given duration.
        If ra AND dec are both "true", ignores source

        Parameters
        ----------
        ra : float/int/str
            RA in hours (can be a string interpretable by astropy Angles)
        dec : float/int/str
            Dec in degrees (can be a string interpretable by astropy Angles)
        source : str/None
            Source name (if ATATools.ata_sources is available)
        day : str/Time
            Day of observation (UTC).  Interpreted by aoc_tools.interp_dates
        duration : float
            Length of observation in hours
        el_limit : float
            Elevation limit to check in degrees
        **kwargs
            Other calendar Event fields

        """
        source, obs = self.get_obs(ra=ra, dec=dec, source=source, day=day, duration=duration)
        duration = obs.obstime[-1] - obs.obstime[0]

        above = npwhere(obs.alt.value > el_limit)[0]
        if not len(above):
            logger.warning(f"{source} never above the elevation limit of {el_limit}.")
            return False
        srcstart = obs.obstime[above[0]]
        srcstop = obs.obstime[above[-1]]
        time_above = srcstop - srcstart
        logger.info(f"Scheduling {source}")
        if time_above > duration:
            srcstart = obs.obstime[above[len(above) // 2]] - duration / 2.0
            srcstop = obs.obstime[above[len(above) // 2]] + duration / 2.0
            logger.info(f"Scheduling middle {duration.to(u.hour).value:.1f}h of {time_above.to(u.hour).value:.1f}h above {el_limit}d")
        else:
            logger.info(f"Scheduling {time_above.to(u.hour).value:.1f}h above {el_limit}d of desired {duration.to(u.hour).value:.1f}h")

        kwargs['utc_start'] = srcstart.datetime.isoformat(timespec='seconds')
        kwargs['utc_stop'] = srcstop.datetime.isoformat(timespec='seconds')

        if 'name' not in kwargs or kwargs['name'] is None:  kwargs['name'] = source
        if 'note' not in kwargs or kwargs['note'] is None : kwargs['note'] = source
        else: kwargs['note'] += f" -- {source}"
        self.add(**kwargs)
        logger.warning("Now should edit down the scheduled observation times!")
        return True

    def conflicts(self, check_event, is_new=False):
        """
        Check an event for conflicts.

        Parameters
        ----------
        check_event : Entry
            Entry to check
        is_new : bool
            Flag to alert that this entry is not yet in the calendar for duplicate check.

        Return
        ------
        dict : results with keys 'duplcate' and 'conflict'

        """
        day = check_event.utc_start.datetime.strftime('%Y-%m-%d')
        this_hash = check_event.hash()
        results = {'duplicate': [], 'conflict': []}
        if day not in self.events:
            return results
        for i, this_event in enumerate(self.events[day]):
            if this_event.hash() == this_hash:
                results['duplicate'].append(i)
                if is_new:
                    msg = f"Entry is duplicated with {day}:{i}"
                    logger.warning(msg)
                    check_event.msg += msg
                continue  # Skip it
            if check_event.utc_start <= this_event.utc_stop and this_event.utc_start <= check_event.utc_stop:
                results['conflict'].append(i)
        return results
