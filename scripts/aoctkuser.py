#! /usr/bin/env python

import argparse
from aocalendar.tk_aocalendar import AOCalendarApp

ap = argparse.ArgumentParser()
ap.add_argument('calfile', help="Calendar file to use/find.", nargs='?', default='now')
ap.add_argument('--path', help="path to use", default='getenv')
ap.add_argument('--output', help="Output logging level", default='INFO')
args = ap.parse_args()

tkobscal = AOCalendarApp(**vars(args))
tkobscal.mainloop()
