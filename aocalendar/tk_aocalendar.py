# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

import tkinter
from tkinter import simpledialog, messagebox
from tkcalendar import Calendar
from aocalendar import aocalendar, aoc_tools, logger_setup, __version__
import logging


logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

def frame_label_fmt(txt, n=20):
    return f"{txt:>{n}s}"


class AOCalendarApp(tkinter.Tk):
    def __init__(self, **kwargs):
        super().__init__()
        self.title("Allen Telescope Array Observing Calendar")

        # Set window size to 1200x900
        self.geometry("900x1000")

        calfile = kwargs['calfile'] if 'calfile' in kwargs else 'now'
        path = kwargs['path'] if 'path' in kwargs else 'getenv'
        output = kwargs['output'] if 'output' in kwargs else 'INFO'
        file_logging = kwargs['file_logging'] if 'file_logging' in kwargs else False
        path = aoc_tools.determine_path(path=path, fileinfo=calfile)
        logger_setup.setup(logger, output=output, file_logging=file_logging, log_filename='aoclog', path=path)
        logger.info(f"{__name__} ver. {__version__}")

        self.this_cal = aocalendar.Calendar(calfile=calfile, path=path, output=output, file_logging=file_logging)
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
                              font="Arial 18", showweeknumbers=False, foreground='grey', selectforeground='blue', firstweekday='sunday')
        self.tkcal.grid(row=0, column=0)

        for day, events in self.this_cal.events.items():
            for event in events:
                label = f"{event.name}:{event.pid}"
                self.tkcal.calevent_create(event.utc_start.datetime, label, 'obs')
        self.tkcal.tag_config('obs', foreground='red')

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
        self.this_cal.read_calendar_events(calfile='refresh')
        self.tkcal.calevent_remove('all')
        for day, events in self.this_cal.events.items():
            for event in events:
                label = f"{event.name}:{event.pid}"
                self.tkcal.calevent_create(event.utc_start.datetime, label, 'obs')

    def reset(self):
        self.aoc_action = ''
        self.aoc_field_defaults = {}
        for key in aocalendar.aocentry.ENTRY_FIELDS:
            self.aoc_field_defaults[key] = ''
        self.aoc_day = ''
        self.aoc_nind = 0
        for widget in self.frame_update.winfo_children():
            widget.destroy()

    def show_date(self, datestr=None):
        if datestr is None:
            datestr = self.tkcal.selection_get().strftime('%Y-%m-%d')
        entry = f"{self.this_cal.calfile_fullpath} SCHEDULE FOR {datestr}\n\n"
        try:
            entry += self.this_cal.format_day_events(datestr, return_as='table')
            entry += self.this_cal.graph_day(datestr, interval_min=15.0)
        except KeyError:
            entry += "No entry."
        info_text = tkinter.Text(self.frame_info, width=800)
        info_text.grid(row=0, column=0, columnspan=4)
        info_text.insert(tkinter.CURRENT, entry)

    def submit(self):
        if self.aoc_action in ['add', 'update', 'schedule']:
            kwargs = {
                'name': self.name_entry.get().strip(),
                'pid': self.pid_entry.get().strip(),
                'utc_start': self.start_entry.get().strip(),
                'utc_stop': self.stop_entry.get().strip(),
                'lst_start': self.lstart_entry.get().strip(),
                'lst_stop': self.lstop_entry.get().strip(),
                'state': self.state_entry.get().strip(),
                'note': self.note_entry.get().strip(),
                'observer': self.obs_entry.get().strip(),
                'email': self.email_entry.get().strip()
            }
        if self.aoc_action == 'add':
            self.aoc_day = aoc_tools.interp_date(kwargs['utc_start'], fmt='%Y-%m-%d')
            is_ok = self.this_cal.add(**kwargs)
        elif self.aoc_action in ['update', 'schedule']:
            is_ok = self.this_cal.update(day=self.aoc_day, nind=self.aoc_nind, **kwargs)
        elif self.aoc_action == 'delete':
            is_ok = self.this_cal.delete(day=self.aoc_day, nind=self.aoc_nind)
        if is_ok:
            self.show_date(self.aoc_day)
            yn=messagebox.askquestion('Write Calendar', 'Do you want to write calendar file with edits?')
            if yn == 'yes':
                self.this_cal.write_calendar()
            else:
                messagebox.showinfo('Return', 'Not writing new calendar.')
        else:
            print("Did not succeed.")
        for widget in self.frame_update.winfo_children():
            widget.destroy()

    def event_fields(self, gobutton):
        for widget in self.frame_update.winfo_children():
            widget.destroy()
        name_label = tkinter.Label(self.frame_update, text=frame_label_fmt('Name'))
        name_label.grid(row=0, column=0)
        self.name_entry = tkinter.Entry(self.frame_update)
        self.name_entry.grid(row=0, column=1)
        self.name_entry.insert(0, self.aoc_field_defaults['name'])
        pid_label = tkinter.Label(self.frame_update, text=frame_label_fmt('pid'))
        pid_label.grid(row=0, column=2)
        self.pid_entry = tkinter.Entry(self.frame_update)
        self.pid_entry.grid(row=0, column=3)
        self.pid_entry.insert(0, self.aoc_field_defaults['pid'])

        start_label = tkinter.Label(self.frame_update, text=frame_label_fmt('UTC start'))
        start_label.grid(row=1, column=0)
        self.start_entry = tkinter.Entry(self.frame_update)
        self.start_entry.grid(row=1, column=1)
        self.start_entry.insert(0, self.aoc_field_defaults['utc_start'].datetime.isoformat(timespec='minutes'))
        stop_label = tkinter.Label(self.frame_update, text=frame_label_fmt('UTC stop'))
        stop_label.grid(row=1, column=2)
        self.stop_entry = tkinter.Entry(self.frame_update)
        self.stop_entry.grid(row=1, column=3)
        self.stop_entry.insert(0, '')  # self.aoc_field_defaults['utc_stop'].datetime.isoformat(timespec='minutes'))

        lstart_label = tkinter.Label(self.frame_update, text=frame_label_fmt('LST start'))
        lstart_label.grid(row=2, column=0)
        self.lstart_entry = tkinter.Entry(self.frame_update)
        self.lstart_entry.grid(row=2, column=1)
        self.lstart_entry.insert(0, self.aoc_field_defaults['lst_start'])
        lstop_label = tkinter.Label(self.frame_update, text=frame_label_fmt('LST stop'))
        lstop_label.grid(row=2, column=2)
        self.lstop_entry = tkinter.Entry(self.frame_update)
        self.lstop_entry.grid(row=2, column=3)
        self.lstop_entry.insert(0, self.aoc_field_defaults['lst_stop'])

        state_label = tkinter.Label(self.frame_update, text=frame_label_fmt('State'))
        state_label.grid(row=3, column=0)
        self.state_entry = tkinter.Entry(self.frame_update)
        self.state_entry.grid(row=3, column=1)
        self.state_entry.insert(0, self.aoc_field_defaults['state'])
        note_label = tkinter.Label(self.frame_update, text=frame_label_fmt('Note'))
        note_label.grid(row=3, column=2)
        self.note_entry = tkinter.Entry(self.frame_update)
        self.note_entry.grid(row=3, column=3)
        self.note_entry.insert(0, self.aoc_field_defaults['note'])

        obs_label = tkinter.Label(self.frame_update, text=frame_label_fmt('Observer'))
        obs_label.grid(row=4, column=0)
        self.obs_entry = tkinter.Entry(self.frame_update)
        self.obs_entry.grid(row=4, column=1)
        self.obs_entry.insert(0, self.aoc_field_defaults['observer'])
        email_label = tkinter.Label(self.frame_update, text=frame_label_fmt('E-mail'))
        email_label.grid(row=4, column=2)
        self.email_entry = tkinter.Entry(self.frame_update)
        self.email_entry.grid(row=4, column=3)
        self.email_entry.insert(0, self.aoc_field_defaults['email'])

        submit_button = tkinter.Button(self.frame_update, text=f"{gobutton:^15s}", command=self.submit)
        submit_button.grid(row=5, column=1)
        cancel_button = tkinter.Button(self.frame_update, text='Cancel', command=self.reset)
        cancel_button.grid(row=5, column=3)

    def add_event(self):
        self.reset()
        self.aoc_action = 'add'
        self.aoc_field_defaults['utc_start'] = aoc_tools.interp_date(self.tkcal.selection_get().strftime('%Y-%m-%d'), fmt='Time')
        self.aoc_field_defaults['utc_stop'] = aoc_tools.interp_date(self.tkcal.selection_get().strftime('%Y-%m-%d'), fmt='Time')
        self.aoc_field_defaults['lst_start'] = ''
        self.aoc_field_defaults['lst_stop'] = ''
        self.aoc_field_defaults['state'] = 'primary'
        self.event_fields('Add')

    def del_event(self):
        self.reset()
        self.aoc_action = 'delete'
        self.aoc_day = self.tkcal.selection_get().strftime('%Y-%m-%d')
        try:
            num_events = len(self.this_cal.events[self.aoc_day])
        except KeyError:
            logger.warning(f"{self.aoc_day} does not exist")
            return
        if  num_events > 1:
            entry = simpledialog.askstring("Input", f"{self.aoc_day} entry #", parent=self)
            if entry is None:
                return
            self.aoc_nind = int(entry)
        else:
            self.aoc_nind = 0
        try:
            this_entry = self.this_cal.events[self.aoc_day][self.aoc_nind]
        except IndexError:
            logger.warning(f"Entry {self.aoc_nind} does not exist in {self.aoc_day}.")
            self.reset()
            return
        for field in this_entry.fields:
            self.aoc_field_defaults[field] = getattr(this_entry, field)
        self.aoc_field_defaults['lst_start'] = f"{self.aoc_field_defaults['lst_start'].to_string(precision=0)}"
        self.aoc_field_defaults['lst_stop'] = f"{self.aoc_field_defaults['lst_stop'].to_string(precision=0)}"
        self.event_fields('Delete')

    def upd_event(self):
        self.reset()
        self.aoc_action = 'update'
        self.aoc_day = self.tkcal.selection_get().strftime('%Y-%m-%d')
        try:
            num_events = len(self.this_cal.events[self.aoc_day])
        except KeyError:
            logger.warning(f"{self.aoc_day} does not exist")
            return
        if num_events > 1:
            entry = simpledialog.askstring("Input", f"{self.aoc_day} entry #", parent=self)
            if entry is None:
                return
            self.aoc_nind = int(entry)
        else:
            self.aoc_nind = 0
        try:
            this_entry = self.this_cal.events[self.aoc_day][self.aoc_nind]
        except IndexError:
            logger.warning(f"Entry {self.aoc_nind} does not exist in {self.aoc_day}.")
            self.reset()
            return
        for field in this_entry.fields:
            self.aoc_field_defaults[field] = getattr(this_entry, field)
        self.aoc_field_defaults['lst_start'] = f"{self.aoc_field_defaults['lst_start'].to_string(precision=0)} - can't update"
        self.aoc_field_defaults['lst_stop'] = f"{self.aoc_field_defaults['lst_stop'].to_string(precision=0)} - can't update"
        self.event_fields('Update')

    def schedule(self):
        for widget in self.frame_update.winfo_children():
            widget.destroy()
        name_label = tkinter.Label(self.frame_update, text=frame_label_fmt('Name'))
        name_label.grid(row=0, column=0)
        self.name_entry = tkinter.Entry(self.frame_update)
        self.name_entry.grid(row=0, column=1)
        pid_label = tkinter.Label(self.frame_update, text=frame_label_fmt('pid'))
        pid_label.grid(row=0, column=2)
        self.pid_entry = tkinter.Entry(self.frame_update)
        self.pid_entry.grid(row=0, column=3)

        source_label = tkinter.Label(self.frame_update, text=frame_label_fmt('RA,dec or source'))
        source_label.grid(row=1, column=0)
        self.source_entry = tkinter.Entry(self.frame_update)
        self.source_entry.grid(row=1, column=1)
        day_label = tkinter.Label(self.frame_update, text=frame_label_fmt('UTC day'))
        day_label.grid(row=1, column=2)
        self.day_entry = tkinter.Entry(self.frame_update)
        self.day_entry.grid(row=1, column=3)
        self.day_entry.insert(0, self.tkcal.selection_get().strftime('%Y-%m-%d'))

        duration_label = tkinter.Label(self.frame_update, text=frame_label_fmt('length [h]'))
        duration_label.grid(row=2, column=0)
        self.duration_entry = tkinter.Entry(self.frame_update)
        self.duration_entry.grid(row=2, column=1)
        self.duration_entry.insert(0, '6')
        note_label = tkinter.Label(self.frame_update, text=frame_label_fmt('Note'))
        note_label.grid(row=2, column=2)
        self.note_entry = tkinter.Entry(self.frame_update)
        self.note_entry.grid(row=2, column=3)

        submit_button = tkinter.Button(self.frame_update, text='Schedule', command=self.doschedule)
        submit_button.grid(row=3, column=1)
        cancel_button = tkinter.Button(self.frame_update, text='Cancel', command=self.reset)
        cancel_button.grid(row=3, column=3)

    def doschedule(self):
        name = self.name_entry.get().strip()
        if not name:
            name = None
        pid = self.pid_entry.get().strip()
        source = self.source_entry.get().strip()
        if ',' in source:
            ra, dec = source.split(',')
            source = None
        else:
            ra, dec = None, None
        day = self.day_entry.get().strip()
        duration = float(self.duration_entry.get())
        note = self.note_entry.get().strip()
        scheduled = self.this_cal.schedule(ra=ra, dec=dec, source=source, day=day, duration=duration, name=name, pid=pid, note=note)
        self.reset()
        self.show_date(day)
        if scheduled:
            self.aoc_action = 'schedule'
            self.aoc_day = day
            self.aoc_nind = -1
            this_entry = self.this_cal.events[self.aoc_day][self.aoc_nind]
            for field in this_entry.fields:
                thisef = getattr(this_entry, field)
                if thisef is None: thisef = ''
                self.aoc_field_defaults[field] = thisef
            self.event_fields('OK')
        for widget in self.frame_update.winfo_children():
            widget.destroy()


