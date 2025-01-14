# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.


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
