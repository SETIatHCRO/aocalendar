#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2024 David DeBoer
# Licensed under the 2-clause BSD license.

from setuptools import setup
import glob

setup_args = {
    'name': "aocalendar",
    'description': "ATA Observation Calendar",
    'license': "MIT",
    'author': "David DeBoer",
    'author_email': "david.r.deboer@gmail.edu",
    'version': '0.3.3',
    'scripts': glob.glob('scripts/*'),
    'packages': ['aocalendar']
}

if __name__ == '__main__':
    setup(**setup_args)
