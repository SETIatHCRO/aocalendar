import json
from astropy.time import Time
from datetime import datetime, timedelta
from tabulate import tabulate
from copy import copy
import logging
from astropy.coordinates import EarthLocation, Angle
from astropy.time import Time
from astropy import units as u
from os import path as op
from hashlib import sha256
from numpy import floor
from . import __version__, cal_tools


ata = EarthLocation(lat=40.817431*u.deg, lon=-121.470736*u.deg, height=1019*u.m)
logger = logging.getLogger(__name__)
ENTRY_FIELDS = {'name': "Name", 'ID': "ID",
                'utc_start': None, 'utc_stop': None, 'lst_start': None, 'lst_stop': None,
                'observer': None, 'email': None, 'note': None, 'state': 'primary'}


class Entry:
    def __init__(self, **kwargs):
        self.meta_fields = ['fields']
        self.fields = kwargs['fields'] if 'fields' in kwargs else ENTRY_FIELDS
        for key in self.fields:
            if isinstance(self.fields, dict):
                setattr(self, key, self.fields[key])
            else:
                setattr(self, key, None)
        if len(kwargs):
            self.update(**kwargs)

    def update(self, **kwargs):
        self.msg, kwctr, self.valid = [], 0, True
        for key, val in kwargs.items():
            if key in self.fields:
                if key not in ['utc_start', 'utc_stop']:
                    kwctr += 1
                setattr(self, key, val)
            elif key not in self.meta_fields:
                self.msg.append(f"{key} not valid field")
        for key in ['utc_start', 'utc_stop']:
            try:
                setattr(self, key, Time(getattr(self, key)))
            except ValueError:
                self.msg.append(f'Need valid {key} - got {getattr(self, key)}')
                self.valid = False
        if not kwctr:
            self.msg.append(f"Need at least one non-time entry.")
            self.valid = False
        self.msg = 'ok' if self.valid else '\n'.join(self.msg)

        has_lst = True
        for key in ['lst_start', 'lst_stop']:
            try:
                setattr(self, key, Angle(getattr(self, key)))
            except (ValueError, AttributeError, TypeError):
                has_lst = False
                break
        if not has_lst:
            self.update_lst()

    def row(self, cols='all', printable=True):
        if cols == 'all': cols = self.fields
        entry = self.todict(printable=printable)
        row = [entry[col] for col in cols]
        return row
    
    def hash(self):
        txt = ''.join(self.row(cols='all', printable=True)).encode('utf-8')
        return sha256(txt).hexdigest()[:8]
    
    def todict(self, printable=True):
        entry = {}
        for col in self.fields:
            if printable and col in ['utc_start', 'utc_stop']:
                entry[col] = getattr(self, col).datetime.isoformat(timespec='seconds')
            elif printable and col in ['lst_start', 'lst_stop']:
                hms = getattr(self, col).hms
                entry[col] = f"{int(hms.h):02d}h{int(hms.m):02d}m{int(hms.s):02d}s"
            else:
                entry[col] = str(getattr(self, col))
        return entry

    def update_lst(self):
        self.utc_start = Time(self.utc_start)
        self.utc_stop = Time(self.utc_stop)
        obstimes = Time([self.utc_start, self.utc_stop])
        self.lst_start, self.lst_stop = obstimes.sidereal_time('mean', longitude=ata)


class Calendar:
    meta_fields = ['updated']

    def __init__(self, calfile='now', location="ATA", output='INFO', path=''):
        # All this seems to be needed.
        level = getattr(logging, output.upper())
        logger.setLevel(level)
        ch = logging.StreamHandler()
        ch.setLevel(level)
        logger.addHandler(ch)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        #
        self.read_calendar_contents(calfile=calfile, path=path)
        self.location = location
        logger.info(f"{__name__} ver. {__version__}")
    
    def __get_calfile(self, calfile, path):
        if calfile.endswith('.json'):
            year = calfile.split('.')[0][4:]
            refdate = Time(datetime(year=year, month=1, day=1))
        else:
            refdate = cal_tools.interp_date(calfile, 'Time')
            calfile = f"cal{refdate.datetime.year}.json"
        return op.join(path, calfile), refdate

    def read_calendar_contents(self, calfile, path='', skip_duplicates=True):
        """
        Reads a cal json file -- it will "fix" any wrong day entries.
        """
        self.calfile, self.refdate = self.__get_calfile(calfile=calfile, path=path)
        with open(self.calfile, 'r') as fp:
            inp = json.load(fp)
        self.contents = {}
        self.straddle = {}
        self.all_fields = []
        self.all_hash = []
        for key, entries in inp.items():
            if key in self.meta_fields:
                setattr(self, key, entries)
            else:
                keydate = Time(key)
                self.contents.setdefault(key, [])
                for i, event in enumerate(entries):
                    this_event = Entry(**event)
                    if isinstance(this_event.fields, dict):
                        self.all_fields = list(this_event.fields.keys())
                    else:
                        self.all_fields = copy(this_event.fields)  # This is a bit of a cheat for now to keep order, should check/append.
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
                    if not cal_tools.same_date(keydate, this_event.utc_start, timespec='day'):
                        keystr = this_event.utc_start.datetime.strftime("%Y-%m-%d")
                        logger.info(f"{keystr} in wrong day.")
                    else:
                        keystr = keydate.datetime.strftime("%Y-%m-%d")
                    self.contents.setdefault(keystr, [])
                    self.contents[keystr].append(this_event)
                    endkeystr = this_event.utc_stop.datetime.strftime("%Y-%m-%d")
                    if endkeystr != keystr:
                        self.straddle.setdefault(endkeystr, [])
                        self.straddle[endkeystr].append(this_event)

    def write_calendar(self, calfile=None):
        if calfile is None:
            calfile = self.calfile
        logger.info(f"Writing {calfile}")
        full_contents = {}
        for md in self.meta_fields:
            if md == 'updated':
                self.updated = Time.now().datetime.isoformat(timespec='seconds')
            full_contents[md] = getattr(self, md)
        for key, val in self.contents.items():
            full_contents[key] = []
            for event in val:
                full_contents[key].append(event.todict(printable=True))
            if not len(full_contents[key]):
                del(full_contents[key])
        with open(calfile, 'w') as fp:
           json.dump(full_contents, fp, indent=2)

    def __sort_day(self, day):
        day = cal_tools.interp_date(day)
        sorted_dict = {}
        offset = 0
        if day in self.straddle:
            for event in self.straddle[day]:
                key = (event.utc_start, event.utc_stop)
                sorted_dict[key] = copy(event)
                offset += 1
        if day in self.contents:
            for i, event in enumerate(self.contents[day]):
                key = (event.utc_start, event.utc_stop)
                sorted_dict[key] = {'event': copy(event), 'index': i}
        sorted_day = []
        keymap = {}
        for i, key in enumerate(sorted(sorted(sorted_dict))):
            sorted_day.append(sorted_dict[key]['event'])
            keymap[i] = sorted_dict[key]['index']
        return sorted_day, offset, keymap

    def format_day_contents(self, day='today', cols='all', return_as='table'):
        if cols == 'all': cols = self.all_fields
        hdr = ['#'] + cols      
        sorted_day, offset, keymap = self.__sort_day(day)
        if return_as == 'table':
            return(tabulate([[keymap[i]-offset] + event.row(cols, printable=True) for i, event in enumerate(sorted_day)], headers=hdr))
        elif return_as == 'list':
            return [[keymap[i]-offset] + event.row(cols, printable=True) for i, event in enumerate(sorted_day)], hdr
        
    def graph_day(self, day='today', header_col='name'):
        """
        Text-based graph of schedule sorted by start/stop times.

        Parameters
        ----------

        """
        sorted_day, _, _ = self.__sort_day(day)
        if not len(sorted_day):
            return ' '
        lens = [len(getattr(x, header_col)) for x in sorted_day]
        stroff = 2 + max(lens)
        day = cal_tools.interp_date(day)
        start_of_day = Time(day)
        end_of_day = Time(start_of_day.datetime + timedelta(days=1))
        interval_sec = 15.0 * 60.0  # every 15min
        numpoints = int(24.0 * 3600.0 / interval_sec)
        dt = ((end_of_day - start_of_day) / (numpoints)).to('second').value

        current = int((Time.now() - start_of_day).to('second').value / dt)
        show_current = True if (current > -1 and current < numpoints) else False

        # Set up ticks/labels
        tickrow, labelrow = [' '] * (numpoints + 1), [' '] * (numpoints + 1)
        for h in range(0, 25, 2):  # Tick every 2 hours
            x = int(h * 3600.0 / dt)
            labelrow[x] = str(h)[-1]
            if h > 9.9:
                labelrow[x-1] = str(h)[0]
            tickrow[x] = '|'
        labelrow = ' ' * stroff + ''.join(labelrow)
        if show_current:
            tickrow[current] = '0'
        tickrow = ' ' * stroff + ''.join(tickrow)

        ss = f"\n\n\n{labelrow}\n{tickrow}\n"
        for entry in sorted_day:
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
            ss += f" {getattr(entry, header_col):{stroff-2}s} {''.join(row)}\n"
        ss += f"{tickrow}"
        return ss

    def edit(self, action, entry=None, **kwargs):
        """
        Parameters
        ----------
        action : str
            One of 'add', 'delete', 'update
        entry : str
            If 'delete' or 'update' then 'YYYY-MM-DD:#'

        """
        if action == 'add':
            this_event = Entry(**kwargs)
            this_hash = this_event.hash()
            if this_hash in self.all_hash:
                logger.warning(f"{entry} is a duplicate -- skipping add")
                return
            else:
                self.all_hash.append(this_hash)
            if not this_event.valid:
                logger.warning(f"Entry invalid:\n{this_event.msg}")
            day = this_event.utc_start.datetime.strftime('%Y-%m-%d')
            self.contents.setdefault(day, [])
            self.contents[day].append(this_event)
        elif action == 'delete':
            day = cal_tools.interp_date(entry.split(':')[0], fmt='%Y-%m-%d')
            entrynum = int(entry.split(':')[1])
            try:
                del(self.contents[day][entrynum])
            except (KeyError, IndexError):
                logger.warning(f"Invalid entry: {entry}")
        elif action == 'update':
            day = cal_tools.interp_date(entry.split(':')[0], fmt='%Y-%m-%d')
            entrynum = int(entry.split(':')[1])
            try:
                self.contents[day][entrynum].update(**kwargs)
            except (KeyError, IndexError):
                logger.warning(f"{entry} not found.")
            this_hash = self.contents[day][entrynum].hash()
            if this_hash in self.all_hash:
                logger.warning(f"You made {entry} a duplicate.")
            else:
                self.all_hash.append(this_hash)
        else:
            logger.warning(f"Invalid edit action: {action}")

    def add_from_file(self, file_name, sep='auto'):
        data = cal_tools.read_data_file(file_name=file_name, sep=sep)
        for entry in data:
            self.edit('add', **entry)

    def recurring(self):
        print("RECURRING")

    def schedule(self):
        print("SCHEDULE AN RA/DEC FOR GIVEN DAY")

    def conflict(self):
        print("CHECK FOR OVERLAPS")