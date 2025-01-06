# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

from astropy.time import Time, TimeDelta


INTERPRETABLE_DATES = ['now', 'current', 'today', 'yesterday', 'tomorrow']
TIMEZONE = {'PST': -8, 'PDT': -7, 'EST': -5, 'EDT': -4, 'UTC': 0}


def determine_path(path, fileinfo=None):
    """Determine path for calfile and logging etc."""
    from os import getenv
    import os.path as op
    from .aocalendar import PATH_ENV

    if path == 'getenv':
        path = getenv(PATH_ENV)
    elif path:  # Is some other specific pathname
        pass
    elif isinstance(fileinfo, str) and fileinfo.endswith('.json'):  # Otherwise get from calfile json filename
        dn = op.dirname(fileinfo)
        if len(dn):
            path = dn
    return '' if path is None else path

def boolcheck(x):
    try:
        return bool(x)
    except ValueError:
        return True

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

def read_data_file(file_name, sep='auto'):
    """
    Read a data file - assumes a header row.
    
    Parameters
    ----------
    file_name : str
        Name of file to read.
    sep : str
        Data separator in file, if 'auto' will check header row.
    replace : dict, list, str or None
        In the header will replace the character key with the dict value in case 'escape' characters.
        List will convert to {[0]: [1]}
        Str will convert to list, then if list above or len == 1 {[0]: ''}
    header_map : None or dict
        If dict, will rename the header columns.

    Returns
    -------
    pandas dataFrame

    """
    import pandas as pd

    if sep == 'auto':
        with open(file_name, 'r') as fp:
            header = fp.readline()
        for s in [',', '\t', ' ', ';']:
            if s in header:
                sep = s
                break

    data_inp = pd.read_csv(file_name, sep=sep, skipinitialspace=True)

    data = []
    for _, row in data_inp.iterrows():
        data.append(row.to_dict())

    return data


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
        iddate = Time(iddate)
    if fmt[0] == '%':
        iddate = iddate.datetime.strftime(fmt)
    return iddate


def listify(x, d={}, sep=','):
    """
    Convert input to list.

    Parameters
    ----------
    x : *
        Input to listify
    d : dict
        Default/other values for conversion.
    sep : str
        Separator to use if str
    
    Return
    ------
    list : converted x (or d[x])

    """
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, str) and x in d:
        return d[x]
    if isinstance(x, str):
        if sep == 'auto':
            sep = ','
        return x.split(sep)
    return [x]
