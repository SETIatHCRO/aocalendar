#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

import argparse
from aocalendar.tk_aocalendar import AOCalendarApp

ap = argparse.ArgumentParser()
ap.add_argument('calfile', help="Calendar file to use/find.", nargs='?', default='now')
ap.add_argument('--ods', help="Name of ODS file/url to check.", default="https://www.seti.org/sites/default/files/HCRO/ods.json")
ap.add_argument('--path', help="path to use", default='getenv')
ap.add_argument('--allow-observer', dest='allow_observer', help="Active the observe button", action='store_true')
ap.add_argument('--conlog', help="Output console logging level", default='WARNING')
ap.add_argument('--filelog', help="Output file logging level", default='WARNING')
args = ap.parse_args()

if args.ods.lower() in ['none', 'disable']:
    args.ods = None

tkobscal = AOCalendarApp(**vars(args))
tkobscal.mainloop()
