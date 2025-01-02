#! /usr/bin/env python

import tkinter
from tkinter import simpledialog, messagebox
from tkcalendar import Calendar
from aocalendar import aocalendar
from . import aoc_tools


def t2iso(t):
    mdy = t.split("/")
    mn, dy, yr = [int(x) for x in mdy]
    return f"20{yr:02d}-{mn:02d}-{dy:02d}"

class AOCalendarApp(tkinter.Tk):
    def __init__(self, **kwargs):
        super().__init__()
        self.title("Allen Telescope Array Observing Calendar")

        # Set window size to 1200x900
        self.geometry("900x1000")

        calfile = kwargs['calfile'] if 'calfile' in kwargs else 'now'
        path = kwargs['path'] if 'path' in kwargs else 'getenv'
        output = kwargs['output'] if 'output' in kwargs else 'INFO'

        self.this_cal = aocalendar.Calendar(calfile=calfile, path=path, output=output)
        self.refdate = self.this_cal.refdate.datetime

        # Create all of the frames
        self.frame_calendar = tkinter.Frame(self)
        self.frame_buttons = tkinter.Frame(self)
        self.frame_info = tkinter.Frame(self)
        self.frame_update = tkinter.Frame(self)

        # Layout all of the frames 4 rows, 1 column
        self.grid_rowconfigure(0, weight=2)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=2)
        self.grid_rowconfigure(3, weight=2)
        self.grid_columnconfigure(0, weight=1)

        # Calendar
        self.frame_calendar.grid(row=0, column=0)
        self.tkcal = Calendar(self.frame_calendar, selectmode='day', year=self.refdate.year, month=self.refdate.month, day=self.refdate.day,
                              font="Arial 18", showweeknumbers=False, foreground='black', selectforeground='red')
        self.tkcal.grid(row=0, column=0)

        # Buttons
        self.frame_buttons.grid(row=1, column=0)    
        info_button = tkinter.Button(self.frame_buttons, text = "Get Day Info", command = self.show_date)
        info_button.grid(row=2, column=0)
        add_button = tkinter.Button(self.frame_buttons, text = "Add entry", command = self.add_event)
        add_button.grid(row=2, column=1)
        del_button = tkinter.Button(self.frame_buttons, text = "Delete entry", command = self.del_event)
        del_button.grid(row=2, column=2)
        upd_button = tkinter.Button(self.frame_buttons, text = "Update entry", command = self.upd_event)
        upd_button.grid(row=2, column=3)
        sch_button = tkinter.Button(self.frame_buttons, text="Schedule", command =self.schedule)
        sch_button.grid(row=2, column=4)
        rrl_button = tkinter.Button(self.frame_buttons, text = "Refresh calendar", command = self.refresh)
        rrl_button.grid(row=2, column=5)
        rst_button = tkinter.Button(self.frame_buttons, text = "Reset", command = self.reset)
        rst_button.grid(row=2, column=6)

        # Info
        self.frame_info.grid(row=2, column=0)
        info_text = tkinter.Text(self.frame_info)
        info_text.grid(row=0, column=0, columnspan=4)
        info_text.insert(tkinter.INSERT, f"CALENDAR DATE INFORMATION: {self.this_cal.calfile_fullpath}")

        # Update
        self.frame_update.grid(row=3, column=0)
        self.reset()

    def refresh(self):
        self.this_cal.read_calendar_contents(calfile='refresh')

    def reset(self):
        self.aoc_action = ''
        self.aoc_field_defaults = {}
        for key in aocalendar.ENTRY_FIELDS:
            self.aoc_field_defaults[key] = ''
        self.aoc_day = ''
        self.aoc_nind = 0

    def show_date(self, datestr=None):
        if datestr is None:
            datestr = t2iso(self.tkcal.get_date())
        entry = f"{self.this_cal.calfile_fullpath} SCHEDULE FOR {datestr}\n\n"
        try:
            entry += self.this_cal.format_day_contents(datestr, return_as='table')
            entry += self.this_cal.graph_day(datestr, interval_min=15.0)
        except KeyError:
            entry += "No entry."
        info_text = tkinter.Text(self.frame_info, width=800)
        info_text.grid(row=0, column=0, columnspan=4)
        info_text.insert(tkinter.CURRENT, entry)

    def submit(self):
        if self.aoc_action in ['add', 'update', 'schedule']:
            kwargs = {
                'name': self.name_entry.get(),
                'pid': self.pid_entry.get(),
                'utc_start': self.start_entry.get(),
                'utc_stop': self.stop_entry.get(),
                'state': self.state_entry.get(),
                'note': self.note_entry.get(),
                'observer': self.obs_entry.get(),
                'email': self.email_entry.get()
            }
        if self.aoc_action == 'add':
            self.day = aoc_tools.interp_date(kwargs['utc_start'], fmt='%Y-%m-%d')
            is_ok = self.this_cal.add(**kwargs)
        elif self.aoc_action in ['update', 'schedule']:
            is_ok = self.this_cal.update(day=self.day, nind=self.nind, **kwargs)
        elif self.aoc_action == 'delete':
            is_ok = self.this_cal.delete(day=self.day, nind=self.nind)
        if is_ok:
            self.show_date(self.day)
            yn=messagebox.askquestion('Write Calendar', 'Do you want to write calendar file with edits?')
            if yn == 'yes':
                self.this_cal.write_calendar()
            else:
                messagebox.showinfo('Return', 'Not writing new calendar.')
        else:
            print("Did not succeed.")

    def event_fields(self, gobutton):
        name_label = tkinter.Label(self.frame_update, text='Name')
        name_label.grid(row=0, column=0)
        self.name_entry = tkinter.Entry(self.frame_update)
        self.name_entry.grid(row=0, column=1)
        self.name_entry.insert(0, self.aoc_field_defaults['name'])
        pid_label = tkinter.Label(self.frame_update, text='pid')
        pid_label.grid(row=0, column=2)
        self.pid_entry = tkinter.Entry(self.frame_update)
        self.pid_entry.grid(row=0, column=3)
        self.pid_entry.insert(0, self.aoc_field_defaults['pid'])

        start_label = tkinter.Label(self.frame_update, text='UTC start')
        start_label.grid(row=1, column=0)
        self.start_entry = tkinter.Entry(self.frame_update)
        self.start_entry.grid(row=1, column=1)
        self.start_entry.insert(0, self.aoc_field_defaults['utc_start'].datetime.isoformat(timespec='minutes'))
        stop_label = tkinter.Label(self.frame_update, text='UTC stop')
        stop_label.grid(row=1, column=2)
        self.stop_entry = tkinter.Entry(self.frame_update)
        self.stop_entry.grid(row=1, column=3)
        self.stop_entry.insert(0, self.aoc_field_defaults['utc_stop'].datetime.isoformat(timespec='minutes'))

        state_label = tkinter.Label(self.frame_update, text='State')
        state_label.grid(row=2, column=0)
        self.state_entry = tkinter.Entry(self.frame_update)
        self.state_entry.grid(row=2, column=1)
        self.state_entry.insert(0, self.aoc_field_defaults['state'])
        note_label = tkinter.Label(self.frame_update, text='Note')
        note_label.grid(row=2, column=2)
        self.note_entry = tkinter.Entry(self.frame_update)
        self.note_entry.grid(row=2, column=3)
        self.note_entry.insert(0, self.aoc_field_defaults['note'])

        obs_label = tkinter.Label(self.frame_update, text='Observer')
        obs_label.grid(row=3, column=0)
        self.obs_entry = tkinter.Entry(self.frame_update)
        self.obs_entry.grid(row=3, column=1)
        self.obs_entry.insert(0, self.aoc_field_defaults['observer'])
        email_label = tkinter.Label(self.frame_update, text='E-mail')
        email_label.grid(row=3, column=2)
        self.email_entry = tkinter.Entry(self.frame_update)
        self.email_entry.grid(row=3, column=3)
        self.email_entry.insert(0, self.aoc_field_defaults['email'])

        submit_button = tkinter.Button(self.frame_update, text=gobutton, command=self.submit)
        submit_button.grid(row=4, column=1)
        cancel_button = tkinter.Button(self.frame_update, text='Cancel', command=self.reset)
        cancel_button.grid(row=4, column=3)

    def add_event(self):
        self.reset()
        self.aoc_action = 'add'
        self.aoc_field_defaults['utc_start'] = self.this_cal.refdate
        self.aoc_field_defaults['utc_stop'] = self.this_cal.refdate
        self.aoc_field_defaults['state'] = 'primary'
        self.event_fields('Add')

    def del_event(self):
        self.reset()
        self.aoc_action = 'delete'
        entry = simpledialog.askstring("Input", "YYYY-MM-DD,#", parent=self)
        if entry is None:
            return
        self.day, self.nind = entry.split(',')
        self.nind = int(self.nind)
        this_entry = self.this_cal.contents[self.day][self.nind]
        for field in this_entry.fields:
            self.aoc_field_defaults[field] = getattr(this_entry, field)
        self.event_fields('Delete')

    def upd_event(self):
        self.reset()
        self.aoc_action = 'update'
        entry = simpledialog.askstring("Input", "YYYY-MM-DD,#", parent=self)
        if entry is None:
            return
        self.day, self.nind = entry.split(',')
        self.nind = int(self.nind)
        this_entry = self.this_cal.contents[self.day][self.nind]
        for field in this_entry.fields:
            self.aoc_field_defaults[field] = getattr(this_entry, field)
        self.event_fields('Update')

    def schedule(self):
        name_label = tkinter.Label(self.frame_update, text='Name')
        name_label.grid(row=0, column=0)
        self.name_entry = tkinter.Entry(self.frame_update)
        self.name_entry.grid(row=0, column=1)
        pid_label = tkinter.Label(self.frame_update, text='pid')
        pid_label.grid(row=0, column=2)
        self.pid_entry = tkinter.Entry(self.frame_update)
        self.pid_entry.grid(row=0, column=3)

        ra_label = tkinter.Label(self.frame_update, text='RA')
        ra_label.grid(row=1, column=0)
        self.ra_entry = tkinter.Entry(self.frame_update)
        self.ra_entry.grid(row=1, column=1)
        dec_label = tkinter.Label(self.frame_update, text='Dec')
        dec_label.grid(row=1, column=2)
        self.dec_entry = tkinter.Entry(self.frame_update)
        self.dec_entry.grid(row=1, column=3)

        day_label = tkinter.Label(self.frame_update, text='UTC day')
        day_label.grid(row=2, column=0)
        self.day_entry = tkinter.Entry(self.frame_update)
        self.day_entry.grid(row=2, column=1)
        duration_label = tkinter.Label(self.frame_update, text='length [h]')
        duration_label.grid(row=2, column=2)
        self.duration_entry = tkinter.Entry(self.frame_update)
        self.duration_entry.grid(row=2, column=3)
        self.duration_entry.insert(0, '1')

        submit_button = tkinter.Button(self.frame_update, text='Schedule', command=self.doschedule)
        submit_button.grid(row=4, column=1)
        cancel_button = tkinter.Button(self.frame_update, text='Cancel', command=self.reset)
        cancel_button.grid(row=4, column=3)

    def doschedule(self):
        name = self.name_entry.get()
        pid = self.pid_entry.get()
        ra = self.ra_entry.get()
        dec = self.dec_entry.get()
        day = self.day_entry.get()
        duration = self.duration_entry.get()
        self.this_cal.schedule(ra=ra, dec=dec, day=day, duration=float(duration), name=name, pid=pid)
        self.reset()
        self.show_date(day)
        self.aoc_action = 'schedule'
        self.day = day
        self.nind = -1
        this_entry = self.this_cal.contents[self.day][self.nind]
        for field in this_entry.fields:
            thisef = getattr(this_entry, field)
            if thisef is None: thisef = ''
            self.aoc_field_defaults[field] = thisef
        self.event_fields('Check Schedule')


