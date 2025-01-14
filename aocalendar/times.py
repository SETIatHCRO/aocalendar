# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

from astropy.time import Time, TimeDelta
from zoneinfo import available_timezones, ZoneInfo, ZoneInfoNotFoundError
from datetime import datetime


INTERPRETABLE_DATES = ['now', 'current', 'today', 'yesterday', 'tomorrow']


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
    if tz == 'sys':
        import time
        if dt is None:
            local_time = time.localtime()
        else:
            local_time = dt.timetuple()
            if local_time.tm_gmtoff is None:
                print("WARNING - No timezone set, using system 'now'")
                local_time = time.localtime()
        tz = time.tzname[local_time.tm_isdst]
        tzoff = local_time.tm_gmtoff / 3600.0
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

