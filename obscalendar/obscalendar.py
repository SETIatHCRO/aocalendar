import json
from astropy.time import Time, TimeDelta
from datetime import datetime
from tabulate import tabulate
from copy import copy
import logging
from astropy.coordinates import EarthLocation, Angle, AltAz, SkyCoord
from astropy.time import Time
from astropy import units as u
from os import path as op
from hashlib import sha256
from numpy import floor, round
from numpy import where as npwhere
from . import __version__, cal_tools


logger = logging.getLogger(__name__)

ATA = EarthLocation(lat=40.817431*u.deg, lon=-121.470736*u.deg, height=1019*u.m)
ENTRY_FIELDS = {'name': "Name", 'ID': "ID",
                'utc_start': None, 'utc_stop': None, 'lst_start': None, 'lst_stop': None,
                'observer': None, 'email': None, 'note': None, 'state': 'primary'}
PATH_ENV = 'OBSCALENDAR'
SHORT_LIST = ['name', 'ID', 'utc_start', 'utc_stop', 'lst_start', 'lst_stop', 'observer', 'state']
DAYSEC = 24 * 3600


def split_entry(entry):
    key, n = entry.split(':')
    return key, int(n)


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

    def __str__(self):
        s = f"CALENDAR ENTRY {self.utc_start.datetime.strftime('%Y')}\n\n"
        data = self.todict(printable=True)
        table = []
        for key, val in data.items():
            table.append([key, val])
        s += tabulate(table, headers=['Field', 'Value']) + '\n'
        return s

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
        # Always recompute LST
        self.update_lst()

    def row(self, cols='all', printable=True):
        if cols == 'all': cols = self.fields
        entry = self.todict(printable=printable)
        row = [entry[col] for col in cols]
        return row
    
    def hash(self):
        txt = ''.join(self.row(cols='all', printable=True)).encode('utf-8')
        return sha256(txt).hexdigest()[:10]
    
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
        self.lst_start, self.lst_stop = obstimes.sidereal_time('mean', longitude=ATA)


class Calendar:
    meta_fields = ['updated']

    def __init__(self, calfile='now', path='getenv', output='INFO'):
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
        self.read_calendar_contents(calfile=str(calfile), path=path)
        logger.info(f"{__name__} ver. {__version__}")
    
    def __get_calfile(self, calfile, path):
        """
        Parameters
        ----------
        calfile : str
            calfile or something interpretable by cal_tools.interp_date
        path : str
            path or 'getenv' - if calfile has path, gets overwritten

        Attributes
        ----------
        path : str
            Path to the calfile
        calfile : str
            Basename of calfile
        calfile_fullpath : str
            path/calfile
        refdate : Time
            reference date for calfile

        """
        if calfile == 'refresh':
            return
        if calfile.endswith('.json'):
            dn = op.dirname(calfile)
            if len(dn):
                path = dn
            calfile = op.basename(calfile)
            try:
                year = int(calfile.split('.')[0][-4:])
                refdate = Time(datetime(year=year, month=1, day=1))
            except ValueError:
                refdate = Time.now()
        else:
            refdate = cal_tools.interp_date(calfile, 'Time')
            calfile = f"cal{refdate.datetime.year}.json"
        if path == 'getenv':
            from os import getenv
            path = getenv(PATH_ENV)
            if path is None: path = ''
        self.path = path
        self.calfile = calfile
        self.calfile_fullpath = op.join(path, calfile)
        self.refdate = refdate

    def read_calendar_contents(self, calfile, path='getenv', skip_duplicates=True):
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
        contents : dict
            Contents of file
        straddle : dict
            Extra info for entries straddling a day
        all_fields : list
            List of all of the entry fields
        all_hash : list
            List of all entry hashes

        """
        self.contents = {}
        self.straddle = {}
        self.all_fields = []
        self.all_hash = []
        self.__get_calfile(calfile=str(calfile), path=path)
        try:
            with open(self.calfile_fullpath, 'r') as fp:
                inp = json.load(fp)
        except FileNotFoundError:
            logging.warning("No calendar file was found.")
            return
        logging.info(f"Reading {self.calfile_fullpath}")
        #print(f"Reading {self.calfile}")
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
            calfile = self.calfile_fullpath
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
            for i, event in enumerate(self.straddle[day]):
                key = (event.utc_start, event.utc_stop, i)
                sorted_dict[key] = copy(event)
                offset += 1
        if day in self.contents:
            for i, event in enumerate(self.contents[day]):
                key = (event.utc_start, event.utc_stop, i)
                sorted_dict[key] = {'event': copy(event), 'index': i}
        sorted_day = []
        keymap = {}
        for i, key in enumerate(sorted(sorted(sorted_dict))):
            sorted_day.append(sorted_dict[key]['event'])
            keymap[i] = sorted_dict[key]['index']
        return sorted_day, offset, keymap

    def format_day_contents(self, day='today', cols='short', return_as='table'):
        if cols == 'all':
            cols = self.all_fields
        elif cols == 'short':
            cols = SHORT_LIST
        hdr = ['#'] + cols
        sorted_day, offset, keymap = self.__sort_day(day)
        if return_as == 'table':
            return(tabulate([[keymap[i]-offset] + event.row(cols, printable=True) for i, event in enumerate(sorted_day)], headers=hdr))
        elif return_as == 'list':
            return [[keymap[i]-offset] + event.row(cols, printable=True) for i, event in enumerate(sorted_day)], hdr
        
    def graph_day(self, day='today', header_col='name', tz='sys', interval_min=10.0):
        """
        Text-based graph of schedule sorted by start/stop times.

        Parameters
        ----------

        """
        if tz == 'sys':
            import time
            gmt = time.gmtime()
            tz = time.tzname[gmt.tm_isdst]
        tzoff = cal_tools.TIMEZONE[tz]
        sorted_day, offset, keymap = self.__sort_day(day)
        if not len(sorted_day):
            return ' '
        cbuflt, cbufind, cbufrt = 2, 3, 2
        stroff = max([len(getattr(x, header_col)) for x in sorted_day])  # This is max name
        colhdr = [f"{cbuflt*' '}{keymap[i]+offset:>{cbufind-1}d}-{getattr(x, header_col):{stroff}s}{cbufrt*' '}" for i, x in enumerate(sorted_day)]
        stroff += (cbuflt + cbufind + cbufrt)  # Now add the extra

        day = cal_tools.interp_date(day, fmt='%Y-%m-%d')
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
            results = self.conflicts(this_event, is_new=True)
            skip = False
            if len(results['duplicate']):
                suf = 'y' if len(results['duplicate']) == 1 else 'ies'
                logger.warning(f"Not addiing -- duplicate with entr{suf}: {', '.join([str(x) for x in results['duplicate']])}.")
                skip = True
            elif len(results['conflict']):
                suf = 'y' if len(results['conflict']) == 1 else 'ies'
                logger.warning(f"Overlaps with entr{suf}: {', '.join([str(x) for x in results['conflict']])}.")
            if not skip:
                day = this_event.utc_start.datetime.strftime('%Y-%m-%d')
                self.contents.setdefault(day, [])
                self.contents[day].append(this_event)
                self.all_hash.append(this_hash)                
                if not this_event.valid:
                    logger.warning(f"Entry invalid:\n{this_event.msg}")
        elif action == 'delete':
            day, entrynum = split_entry(entry)
            day = cal_tools.interp_date(day, fmt='%Y-%m-%d')
            try:
                del(self.contents[day][entrynum])
            except (KeyError, IndexError):
                logger.warning(f"Invalid entry: {entry}")
        elif action == 'update':
            day, entrynum = split_entry(entry)
            day = cal_tools.interp_date(day, fmt='%Y-%m-%d')
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

    def schedule(self, ra, dec, day='now', duration=12, el_limit=15.0, **kwargs):
        """
        Schedule an observation at a given RA/Dec on a given day for a given duration

        Parameters
        ----------
        ra : float/int/str
            RA in hours (can be a string interpretable by astropy Angles)
        dec : float/int/str
            Dec in degrees (can be a string interpretable by astropy Angles)
        day : str/Time
            Day of observation (UTC).  Interpreted by cal_tools.interp_dates
        duration : float
            Length of observation in hours
        el_limit : float
            Elevation limit to check in degrees
        **kwargs
            Other calendar Event fields

        """
        day = cal_tools.interp_date(day, fmt='Time')
        try:
            ra = float(ra)
            ra = ra * u.hourangle
        except ValueError:
            pass
        try:
            dec = float(dec)
            dec = dec * u.deg
        except ValueError:
            pass

        ra = Angle(ra)
        dec = Angle(dec)
        duration = TimeDelta(duration * 3600.0, format='sec')
        start = Time(datetime(year=day.datetime.year, month=day.datetime.month, day=day.datetime.day))
        stop = start + TimeDelta(24 * 3600, format='sec')
        dt = TimeDelta(10 * 60, format='sec')  # Use 10min
        current, times = copy(start), []
        while current < stop:
            times.append(current)
            current += dt
        altazsky = SkyCoord(ra, dec).transform_to(AltAz(location=ATA, obstime=times))
        above = npwhere(altazsky.alt.value > el_limit)[0]
        if not len(above):
            logger.warning(f"Source never above the elevation limit of {el_limit}.")
            return
        srcstart = times[above[0]]
        srcstop = times[above[-1]]
        time_above = srcstop - srcstart
        if time_above > duration:
            srcstart = times[above[len(above) // 2]] - duration / 2.0
            srcstop = times[above[len(above) // 2]] + duration / 2.0
            logger.info(f"Scheduling middle {duration.to(u.hour).value:.1f}h of {time_above.to(u.hour).value:.1f}h above {el_limit}d")

        kwargs['utc_start'] = srcstart.datetime.isoformat(timespec='seconds')
        kwargs['utc_stop'] = srcstop.datetime.isoformat(timespec='seconds')
        rastr, decstr = f"{ra.hms.h:.0f}h{ra.hms.m:.0f}m{ra.hms.s:.0f}s", f"{dec.dms.d:.0f}d{dec.dms.m:.0f}m{dec.dms.s:.0f}s"
        radec = f"{rastr},{decstr}"
        if 'name' not in kwargs:  kwargs['name'] = radec
        if 'note' not in kwargs:
            kwargs['note'] = radec
        else:
            kwargs['note'] += f" -- {radec}"
        self.edit('add', **kwargs)
            
        logger.warning("Now should edit down the scheduled observation times!")

    def conflicts(self, check_event, is_new=False):
        day = check_event.utc_start.datetime.strftime('%Y-%m-%d')
        this_hash = check_event.hash()
        results = {'duplicate': [], 'conflict': []}
        if day not in self.contents:
            return results
        for i, this_event in enumerate(self.contents[day]):
            if this_event.hash() == this_hash:
                results['duplicate'].append(i)
                if is_new:
                    logger.warning(f"Entry is duplicated with {day}:{i}")
                continue  # Skip it
            if check_event.utc_start <= this_event.utc_stop and this_event.utc_start <= check_event.utc_stop:
                results['conflict'].append(i)
        return results
