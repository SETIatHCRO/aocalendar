# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

from astropy.time import Time, TimeDelta
import astropy.units as u
from astropy.coordinates import Angle
from zoneinfo import available_timezones, ZoneInfo, ZoneInfoNotFoundError
from datetime import datetime, timedelta
from numpy import argmin, round, ceil, floor


INTERPRETABLE_DATES = ['now', 'current', 'today', 'yesterday', 'tomorrow']
DAYSEC = 24 * 3600
SIDEREAL_RATE = 23.93447

class Graph:
    def __init__(self, title="Graph"):
        self.title = title

    def setup(self, start, dt_min=10.0, duration_days=1.0):
        daystart = interp_date(interp_date(start, '%Y-%m-%d'), fmt='Time')
        self.start = Time(daystart.datetime.replace(hour=daystart.datetime.hour))
        self.end = self.start + TimeDelta(duration_days * DAYSEC, format='sec')
        self.T = duration_days
        self.N = int(self.T * DAYSEC / (dt_min * 60.0)) + 1
        # self.N_calc = int(DAYSEC / 60) + 1

    def ticks_labels(self, tz, location, rowhdr, int_hr=2):
        self.rowhdr = rowhdr
        self.rows = []
        self.current = self.cursor_position_t(interp_date('now', fmt='Time'), round)
        self.show_current = self.current > -1 and self.current <= self.N
        utc_t = Time([self.start + TimeDelta(int(x)*3600.0, format='sec') for x in range(0, 26, int_hr)], scale='utc')
        self.lst = utc_t.sidereal_time('mean', longitude=location)
        lstday = argmin(self.lst[:-1])
        lsteq = datetime(year=self.start.datetime.year, month=self.start.datetime.month, day=self.start.datetime.day,
                         hour=int(self.lst[0].hms.h), minute=int(self.lst[0].hms.m), second=int(self.lst[0].hms.s))
        if lstday: lsteq = lsteq - timedelta(days=1)
        elapsed = TimeDelta(((utc_t - utc_t[0]).to('second').value) * (1.0 - SIDEREAL_RATE/24.0), format='sec')
        lst_l = Time([Time(lsteq.replace(minute=0, second=0, microsecond=0)) + TimeDelta(int(x)*3600.0, format='sec') for x in range(0, 27, int_hr)])
        lstoff = (Time(lsteq) - lst_l[0]) - elapsed
        utc_l = utc_t - TimeDelta(lstoff, format='sec')
        self.tzorder = ['UTC', 'LST']
        self.tzinfo = {'UTC': 0.0, 'LST': lstoff}
        self.ticks = {'UTC': {'utc': utc_t,
                              'times': utc_t,
                              'current': '@'},
                      'LST': {'utc': utc_l,
                              'times': lst_l,
                              'current': '@'}}
        if tz.upper() != 'UTC':
            tz, tzoff = get_tz(tz, self.start)
            self.tzorder = ['UTC', tz, 'LST']
            self.tzinfo[tz] = tzoff
            self.ticks[tz] = {'utc': utc_t,
                              'times': utc_t + TimeDelta(self.tzinfo[tz] * 3600.0, format='sec'),
                              'current': '@'}
        for this_tz in self.tzinfo:
            self.ticks[this_tz]['labels'] = [' '] * (self.N + 1)
            self.ticks[this_tz]['ticks'] =[' '] * (self.N + 1)
            for i in range(len(utc_t)):
                toff = self.cursor_position_t(self.ticks[this_tz]['utc'][i], func=round)
                if toff < 0 or toff > self.N:
                    continue
                self.ticks[this_tz]['ticks'][toff] = '|'
                self.ticks[this_tz]['labels'][toff] = f"{self.ticks[this_tz]['times'][i].datetime.hour:02d}"
            if self.show_current:
                self.ticks[this_tz]['ticks'][self.current] = self.ticks[this_tz]['current']

    def cursor_position_t(self, t, func):
        dt = (t - self.start).to('day').value
        return int(func( (dt/self.T) * self.N) )

    def row(self, estart=None, estop=None):
        row = ['.'] * (self.N + 1)
        if estart is None or estop is None:
            pass
        else:
            starting = 0 if estart < self.start else self.cursor_position_t(estart, func=floor)
            ending = self.N if estop > self.end else self.cursor_position_t(estop, func=ceil)
            for star in range(starting, ending):
                row[star] = '*'
        if self.show_current:
            row[self.current] = '@'
        self.rows.append(row)

    def make_table(self):
        import tabulate
        tabulate.PRESERVE_WHITESPACE = True
        maxrhdr = 4 if (self.rowhdr is None or self.rowhdr[0] is None) else max([len(x[1]) for x in self.rowhdr])
        self.g_info = {'width': [2, maxrhdr] + [1] * (self.N+1), 'rows': []}
        for this_tz in self.tzorder:
            if this_tz == 'LST': continue
            self.g_info['rows'].append([' ', this_tz] + self.ticks[this_tz]['labels'])
        self.g_info['rows'].append([' ', ' '] + self.ticks['UTC']['ticks'])
        for i, row in enumerate(self.rows):
            srh = ' ' if self.rowhdr[i] is None else self.rowhdr[i][1]
            enh = ' ' if self.rowhdr[i] is None else self.rowhdr[i][0]
            self.g_info['rows'].append([enh, srh] + row)
        self.g_info['rows'].append([' ', ' '] + self.ticks['LST']['ticks'])
        self.g_info['rows'].append([' ', 'LST'] + self.ticks['LST']['labels'])

        table = []
        for rowstr in self.g_info['rows']:
            d0 = [x[0] for x in rowstr[2:]] + [' ']
            d1 = [' '] + [x[1] if len(x) > 1 else ' ' for x in rowstr[2:]]
            xx = [aa if aa != ' ' else bb for aa, bb in zip(d0, d1)]
            this_row = [rowstr[0], rowstr[1], ''.join(xx)]
            table.append(this_row)
        self.tabulated = tabulate.tabulate(table, tablefmt='plain', colalign=('right', 'right', 'left'))

def all_timezones():
    """
    Return 2 dictionaries:
    1 - timezones['US/Pacific'] = ['PST', 'PDT]
    2 - tz_offsets['PST'] = [-8.0, -8.0...]  # they should all be the same...

    """
    timezones = {}
    tz_offsets = {}
    for tz_iana in available_timezones():
        try:
            this_tz = ZoneInfo(tz_iana)
            #
            t1 = datetime(year=2025, month=1, day=1, tzinfo=this_tz)
            this_tzname = t1.tzname()
            timezones[tz_iana] = [this_tzname]
            tz_offsets.setdefault(this_tzname, {'tz': [], 'offsets': []})
            tz_offsets[this_tzname]['tz'].append(tz_iana)
            tz_offsets[this_tzname]['offsets'].append(t1.utcoffset().total_seconds()/3600.0)
            #
            t2 = datetime(year=2025, month=7, day=1, tzinfo=this_tz)
            this_tzname = t2.tzname()
            timezones[tz_iana].append(this_tzname)
            tz_offsets.setdefault(this_tzname, {'tz': [], 'offsets': []})
            tz_offsets[this_tzname]['tz'].append(tz_iana)
            tz_offsets[this_tzname]['offsets'].append(t2.utcoffset().total_seconds()/3600.0)
        except ZoneInfoNotFoundError:
            continue
    return timezones, tz_offsets


def get_tz(tz='sys', dt=None):
    """
    Returns tz_name, offset_hours

    """
    if dt is None:
        dt = datetime.now()
    elif isinstance(dt, Time):
        dt = dt.datetime
    if tz == 'sys':
        tzinfo = dt.astimezone().tzinfo
        tz = tzinfo.tzname(dt)
        tzoff = tzinfo.utcoffset(dt).total_seconds()/3600.0
        return tz, tzoff
    timezones, tz_offsets = all_timezones()
    if tz in tz_offsets:
        return tz, tz_offsets[tz]['offsets'][0]
    if tz in timezones:
        this_tz = ZoneInfo(tz)
        dt = dt.replace(tzinfo=this_tz)
        return this_tz.tzname(dt), this_tz.utcoffset(dt).total_seconds() / 3600.0
    raise ValueError("Invalid timezone designation.")


def same_date(t1, t2, timespec='day'):
    """
    Return bool on equality of e1 == e2 for timespec.

    Parameters
    ----------
    t1 : interp_date
        Date to be checked
    t2 : interp_date
        Date to be checked
    timespec : str
        Precision of check
    
    """
    t1 = interp_date(t1, fmt='Time')
    t2 = interp_date(t2, fmt='Time')
    if timespec == 'exact':
        return t1 == t2
    fs = {'year': '%Y', 'month': '%Y-%m', 'day': '%Y-%m-%d',
          'hour': '%Y-%m-%dT%H', 'minute': '%Y-%m-%dT%H:%M', 'second': '%Y-%m-%dT%H:%M:%S'}
    return t1.datetime.strftime(fs[timespec]) == t2.datetime.strftime(fs[timespec])

def truncate_to_day(td):
    td = interp_date(td, fmt='Time')
    return datetime(year=td.datetime.year, month=td.datetime.month, day=td.datetime.day)

def interp_date(iddate, fmt='%Y-%m-%d'):
    """
    Interpret 'iddate' and return time or formated string.

    Parameters
    ----------
    iddate : datetime, Time, str
        Day to be interpreted
    fmt : str
        Either a datetime format string (starting with %) or 'Time'

    Return
    ------
    Time or str depending on fmt

    """
    if isinstance(iddate, str) and '/' in iddate:  # iddate +/- offset
        mult = {'d': 24.0*3600.0, 'h': 3600.0, 'm': 60.0, 's': 1.0}
        iddate, offs = iddate.split('/')
        iddate = interp_date(iddate, fmt='Time')
        try:
            dt = mult[offs[-1]] * float(offs[:-1])
        except KeyError:
            dt = 60.0 * float(offs)  # default to minutes
        iddate += TimeDelta(dt, format='sec')
    if iddate == 'today' or iddate == 'now' or iddate == 'current':
        iddate = Time.now()
    elif iddate == 'yesterday':
        iddate = Time.now() - TimeDelta(24.0*3600.0, format='sec')
    elif iddate == 'tomorrow':
        iddate = Time.now() + TimeDelta(24.0*3600.0, format='sec')
    elif len(str(iddate)) == 4:  # assume just a year
        iddate = Time(f"{iddate}-01-01")
    elif len(str(iddate)) == 7:  # assume YYYY-MM
        iddate = Time(f"{iddate}-01")
    else:
        try:
            iddate = Time(iddate)
        except ValueError:
            iddate = None
    if iddate is not None and fmt[0] == '%':
        iddate = iddate.datetime.strftime(fmt)
    return iddate