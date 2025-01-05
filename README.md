# ATA Observation Calendar

ATA Observing calendar - calendar info is in json files delineated by year, e.g. cal2024.json generally located at the environment variable 'AOCALENDAR'.

## Three ways to use

- `from aocalendar import aocalendar`

    provides access to all methods (see the script `aocuser.py` for examples)
    Can use simple 'add' function `aocalendar.aoc_entry` or make the \<class\> `aocalendar.Calendar`

- command line using `aocuser.py`

- gui using `aoctkuser.py`

Events can be added by scheduling a RA/Dec or source, or by LST bounds as well as by UTC.  To specify via LST, leave UTC_stop blank and include LST_start, LST_stop.  UTC_start is needed regardless.  If LST, it only uses the day and not the time (that is the LST on that UTC day, not after the provided UTC time).

For command line:
usage: aocuser.py [-h] [--path PATH] [--output OUTPUT] [-l] [-e SHOW_ENTRY] [-g] [-a] [-u UPDATE] [-d DELETE] [-s SCHEDULE] [-q QUICK] [--duration DURATION] [-n NAME] [-p PID] [--utc_start UTC_START] [--utc_stop UTC_STOP] [--lst_start LST_START] [--lst_stop LST_STOP] [--observer OBSERVER] [--email EMAIL] [--note NOTE] [--state STATE] [calfile]

positional arguments:
  calfile               Calfile/date to use.

options:
  -h, --help            show this help message and exit
  --path PATH           Path to use
  --output OUTPUT       Logging output level
  -l, --list            List events of day
  -e SHOW_ENTRY, --show_entry SHOW_ENTRY
                        Show an entry # on date
  -g, --graph           Graph calendar day
  -a, --add             Add an entry
  -u UPDATE, --update UPDATE
                        Update an entry # on date
  -d DELETE, --delete DELETE
                        Delete an entry # on date
  -s SCHEDULE, --schedule SCHEDULE
                        Schedule ra,dec/source and set duration of observation
  -q QUICK, --quick QUICK
                        Quick add a session of #h/m/s length starting now (at least add -n...)
  --duration DURATION   Duration of scheduled observation in hours
  -n NAME, --name NAME  Event field
  -p PID, --pid PID     Event field
  --utc_start UTC_START
                        Event field
  --utc_stop UTC_STOP   Event field
  --lst_start LST_START
                        Event field
  --lst_stop LST_STOP   Event field
  --observer OBSERVER   Event field
  --email EMAIL         Event field
  --note NOTE           Event field
  --state STATE         Event field
