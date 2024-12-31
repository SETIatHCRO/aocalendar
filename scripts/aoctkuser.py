#! /usr/bin/env python

import argparse
from obscalendar.tk_obscalendar import ObservingCalendarApp

ap = argparse.ArgumentParser()
ap.add_argument('--calfile', help="Calendar file to use/find.", default='now')
ap.add_argument('--path', help="path to use", default='getenv')
ap.add_argument('--output', help="Output logging level", default='INFO')
args = ap.parse_args()

tkobscal = ObservingCalendarApp(**vars(args))
tkobscal.mainloop()
