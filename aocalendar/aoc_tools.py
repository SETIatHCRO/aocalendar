from astropy.time import Time, TimeDelta


INTERPRETABLE_DATES = ['now', 'current', 'today', 'yesterday', 'tomorrow']
TIMEZONE = {'PST': -8, 'PDT': -7, 'EST': -5, 'EDT': -4, 'UTC': 0}


def same_date(e1, e2, timespec='day'):
    """Can clearly be done better."""
    if e1.datetime.year != e2.datetime.year:
        return False
    if timespec == 'year':
        return True
    if e1.datetime.month != e2.datetime.month:
        return False
    if timespec == 'month':
        return True
    if e1.datetime.day != e2.datetime.day:
        return False
    if timespec == 'day':
        return True
    if e1.datetime.hour != e2.datetime.hour:
        return False
    if timespec == 'hour':
        return True
    if e1.datetime.minute != e2.datetime.minute:
        return False
    if timespec == 'minute':
        return True
    if e1.datetime.second != e2.datetime.second:
        return False
    if timespec == 'second':
        return True
    raise ValueError(f"Invalid timespec: {timespec}")


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


def interp_date(day, fmt='%Y-%m-%d'):
    if '/' in day:  # date +/- offset
        mult = {'d': 24.0*3600.0, 'h': 3600.0, 'm': 60.0, 's': 1.0}
        day, offs = day.split('/')
        day = interp_date(day, fmt='Time')
        try:
            dt = mult[offs[-1]] * float(offs[:-1])
        except KeyError:
            dt = 60.0 * float(offs)  # default to minutes
        day += TimeDelta(dt, format='sec')
    if day == 'today' or day == 'now' or day == 'current':
        day = Time.now()
    elif day == 'yesterday':
        day = Time.now() - TimeDelta(24.0*3600.0, format='sec')
    elif day == 'tomorrow':
        day = Time.now() + TimeDelta(24.0*3600.0, format='sec')
    elif len(str(day)) == 4:  # assume just a year
        day = Time(f"{day}-01-01")
    elif len(str(day)) == 7:  # assume YYYY-MM
        day = Time(f"{day}-01")
    else:
        day = Time(day)
    if fmt[0] == '%':
        day = day.datetime.strftime(fmt)
    return day


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
