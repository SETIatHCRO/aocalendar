#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

import argparse
from aocalendar.tk_aocalendar import AOCalendarApp

ap = argparse.ArgumentParser()
ap.add_argument('calfile', help="Calendar file to use/find.", nargs='?', default='now')
ap.add_argument('--path', help="path to use", default='getenv')
ap.add_argument('--output', help="Output console logging level", default='INFO')
ap.add_argument('--file_logging', help="Output file logging level", default='WARNING')
args = ap.parse_args()

tkobscal = AOCalendarApp(**vars(args))
tkobscal.mainloop()
