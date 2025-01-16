# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

import tkinter
from tkinter import simpledialog  #, messagebox
from tkcalendar import Calendar
from aocalendar import aocalendar, times, tools, logger_setup, __version__
import logging
from datetime import datetime


logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')


class AOCalendarApp(tkinter.Tk):
    def __init__(self, **kwargs):
        super().__init__()
        self.title("Allen Telescope Array Observing Calendar")

        # Set window size to 1200x900
        self.geometry("900x820")
        self.resizable(0, 0)

        calfile = kwargs['calfile'] if 'calfile' in kwargs else 'now'
        path = kwargs['path'] if 'path' in kwargs else 'getenv'
        output = kwargs['output'] if 'output' in kwargs else 'INFO'
        file_logging = kwargs['file_logging'] if 'file_logging' in kwargs else False
        path = tools.determine_path(path=path, fileinfo=calfile)
        logger_setup.setup(logger, output=output, file_logging=file_logging, log_filename='aoclog', path=path)
        logger.info(f"{__name__} ver. {__version__}")

        self.this_cal = aocalendar.Calendar(calfile=calfile, path=path, output=output, file_logging=file_logging)
        self.aoc_day = times.truncate_to_day(self.this_cal.refdate)
        self.schedule_by = 'utc'

        # Create all of the frames
        self.frame_calendar = tkinter.Frame(self, height=50)
        self.frame_calendar.grid(row=0, column=0)
        self.frame_buttons = tkinter.Frame(self, height=50)
        self.frame_buttons.grid(row=0, column=1)   
        self.frame_info = tkinter.Frame(self, height=50, borderwidth=2, relief='groove')
        self.frame_info.grid(row=1, column=0, columnspan=2)
        self.frame_update = tkinter.Frame(self, height=50)
        self.frame_update.grid(row=2, column=0, columnspan=2)

        # Layout all of the frames 4 rows, 1 column
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        #self.grid_rowconfigure(3, weight=2)
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)

        # Calendar
        self.tkcal = Calendar(self.frame_calendar, selectmode='day', year=self.aoc_day.year, month=self.aoc_day.month, day=self.aoc_day.day,
                              font="Arial 18", showweeknumbers=False, foreground='grey', selectforeground='blue', firstweekday='sunday',
                              showothermonthdays=False)
        self.tkcal.grid(row=0, column=0)
        self.refresh_flag = False

        for day, events in self.this_cal.events.items():
            for event in events:
                label = f"{event.name}:{event.pid}"
                self.tkcal.calevent_create(event.utc_start.datetime, label, 'obs')
        self.tkcal.tag_config('obs', foreground='red')
        self.tkcal.bind("<<CalendarSelected>>", self.show_date)

        # Buttons
        add_button = tkinter.Button(self.frame_buttons, text = "New", width=12, command = self.add_event)
        add_button.grid(row=0, column=0)
        del_button = tkinter.Button(self.frame_buttons, text = "Delete", width=12, command = self.del_event)
        del_button.grid(row=1, column=0)
        upd_button = tkinter.Button(self.frame_buttons, text = "Edit", width=12, command = self.upd_event)
        upd_button.grid(row=2, column=0)
        rst_button = tkinter.Button(self.frame_buttons, text = "Reset", width=12, command = self.reset)
        rst_button.grid(row=4, column=0, pady=13)

        # Info
        info_text = tkinter.Text(self.frame_info, borderwidth=2, relief='groove', width=130, yscrollcommand=True)
        info_text.insert(tkinter.INSERT, f"CALENDAR DATE INFORMATION: {self.this_cal.calfile_fullpath}")
        info_text.grid(row=0, column=0)
        self.show_date(self.aoc_day)        

    def refresh(self):
        self.this_cal.read_calendar_events(calfile='refresh')
        self.tkcal.calevent_remove('all')
        for day, events in self.this_cal.events.items():
            for event in events:
                label = f"{event.name}:{event.pid}"
                self.tkcal.calevent_create(event.utc_start.datetime, label, 'obs')

    def reset(self):
        if self.refresh_flag:
            self.refresh()
            self.refresh_flag = False
        self.aoc_action = ''
        self.aoc_field_defaults = {}
        for key in aocalendar.aocentry.ENTRY_FIELDS:
            self.aoc_field_defaults[key] = ''
        self.aoc_nind = 0
        for widget in self.frame_update.winfo_children():
            widget.destroy()

    def show_date(self, dateinp=None):
        """Show date in frame_info."""
        for widget in self.frame_info.winfo_children():
            widget.destroy()
        if str(dateinp)[0] == '<' or dateinp is None:
            mdy = self.tkcal.get_date()
            m,d,y = mdy.split('/')
            self.aoc_day = datetime(year=2000+int(y), month=int(m), day=int(d))
        else:
            self.aoc_day = times.truncate_to_day(dateinp)
        entry_title = f"{self.this_cal.calfile_fullpath} SCHEDULE FOR {self.aoc_day.strftime('%Y-%m-%d')}" + '\n\n'
        try:
            entry_list = self.this_cal.list_day_events(self.aoc_day, return_as='table') + '\n\n'
            entry_graph = self.this_cal.graph_day_events(self.aoc_day, tz='US/Pacific', interval_min=15.0)
        except KeyError:
            entry_list = "No entry."
            entry_graph = ''
        info_text = tkinter.Text(self.frame_info, borderwidth=2, relief='groove', width=130, yscrollcommand=True)
        info_text.grid(row=0, column=0)
        info_text.insert(tkinter.INSERT, entry_title)
        info_text.grid(row=1, column=0)
        info_text.insert(tkinter.INSERT, entry_list)
        info_text.grid(row=2, column=0, pady=6)
        info_text.insert(tkinter.INSERT, entry_graph)

    def submit(self):
        if self.aoc_action != 'delete':
            kwargs = {
                'name': self.name_entry.get().strip(),
                'pid': self.pid_entry.get().strip(),
                'utc_start': self.start_entry.get().strip(),
                'state': self.state_entry.get().strip(),
                'note': self.note_entry.get().strip(),
                'observer': self.obs_entry.get().strip(),
                'email': self.email_entry.get().strip()
            }
            if self.schedule_by == 'utc' or self.aoc_action == 'update':
                kwargs.update({
                    'utc_stop': self.stop_entry.get().strip(),
                })
            elif self.schedule_by == 'lst':
                kwargs.update({
                    'utc_start': self.start_entry.get().strip(),
                    'lst_start': self.lstart_entry.get().strip(),
                    'lst_stop': self.lstop_entry.get().strip()
                })
            elif self.schedule_by == 'source':
                raise ValueError('notyet')
                kwargs.update({
                    'utc_start': self.start_entry.get().strip(),
                    'utc_stop': self.stop_entry.get().strip(),
                    'lst_start': self.lstart_entry.get().strip(),
                    'lst_stop': self.lstop_entry.get().strip()
                })
        if self.aoc_action == 'add':
            aoc_day = times.truncate_to_day(kwargs['utc_start'])
            is_ok = self.this_cal.add(**kwargs)
        elif self.aoc_action == 'update':
            aoc_day = self.aoc_day
            is_ok = self.this_cal.update(day=aoc_day, nind=self.aoc_nind, **kwargs)
        elif self.aoc_action == 'delete':
            aoc_day = self.aoc_day
            is_ok = self.this_cal.delete(day=aoc_day, nind=self.aoc_nind)
        elif self.aoc_action == 'schedule':
            aoc_day = self.aoc_day
            is_ok = self.is_scheduled
        if is_ok:
            self.show_date(aoc_day)
            # yn=messagebox.askquestion('Write Calendar', 'Do you want to write calendar file with edits?')
            # if yn == 'yes':
            self.this_cal.write_calendar()
            self.refresh_flag = True
            # else:
            #     messagebox.showinfo('Return', 'Not writing new calendar.')
        else:
            print("Did not succeed.")
        self.reset()

    def event_fields(self, gobutton):
        # Row 0 -- name/pid
        r, c = 0, 0
        name_label = tkinter.Label(self.frame_update, text='Name', width=10)
        name_label.grid(row=r, column=c)
        self.name_entry = tkinter.Entry(self.frame_update)
        self.name_entry.grid(row=r, column=c+1)
        self.name_entry.insert(1, self.aoc_field_defaults['name'])
        pid_label = tkinter.Label(self.frame_update, text='pid', width=10)
        pid_label.grid(row=r, column=c+2)
        self.pid_entry = tkinter.Entry(self.frame_update)
        self.pid_entry.grid(row=r, column=c+3)
        self.pid_entry.insert(1, self.aoc_field_defaults['pid'])
        # Row 1 -- utc_start/utc_stop
        r, c = 1, 0
        if self.aoc_action == 'add':
            addon = 'T00:00' if self.schedule_by == 'utc' else ''
            utcstart = self.aoc_field_defaults['utc_start'] + addon
            utcstop = self.aoc_field_defaults['utc_start'] + addon
        elif self.aoc_action == 'update':
            utcstart = self.aoc_field_defaults['utc_start'].datetime.isoformat(timespec='minutes')
            utcstop = self.aoc_field_defaults['utc_stop'].datetime.isoformat(timespec='minutes')
        start_label = tkinter.Label(self.frame_update, text='UTC start', width=10)
        start_label.grid(row=r, column=c)
        self.start_entry = tkinter.Entry(self.frame_update)
        self.start_entry.grid(row=r, column=c+1)
        self.start_entry.insert(0, utcstart)
        if self.schedule_by == 'utc' or self.aoc_action == 'update':
            stop_label = tkinter.Label(self.frame_update, text='UTC stop', width=10)
            stop_label.grid(row=r, column=c+2)
            self.stop_entry = tkinter.Entry(self.frame_update)
            self.stop_entry.grid(row=r, column=c+3)
            self.stop_entry.insert(0, utcstop)
        else:
            stop_label = tkinter.Label(self.frame_update, text='  ')
            stop_label.grid(row=r, column=c+2, columnspan=2)
         # Row 2 -- lst_start/lst_stop or radec/source
        r, c = 2, 0
        if self.schedule_by == 'utc' or self.aoc_action == 'update':
            lstart_label = tkinter.Label(self.frame_update, text='  ')
            lstart_label.grid(row=r, column=c, columnspan=3)
        elif self.schedule_by == 'lst':
            lstart_label = tkinter.Label(self.frame_update, text='LST start', width=10)
            lstart_label.grid(row=r, column=c)
            self.lstart_entry = tkinter.Entry(self.frame_update)
            self.lstart_entry.grid(row=r, column=c+1)
            self.lstart_entry.insert(0, self.aoc_field_defaults['lst_start'])
            lstop_label = tkinter.Label(self.frame_update, text='LST stop', width=10)
            lstop_label.grid(row=r, column=c+2)
            self.lstop_entry = tkinter.Entry(self.frame_update)
            self.lstop_entry.grid(row=r, column=c+3)
            self.lstop_entry.insert(0, self.aoc_field_defaults['lst_stop'])
        elif self.schedule_by == 'source':
            lstart_label = tkinter.Label(self.frame_update, text='RA,Dec', width=10)
            lstart_label.grid(row=r, column=c)
            self.lstart_entry = tkinter.Entry(self.frame_update)
            self.lstart_entry.grid(row=r, column=c+1)
            self.lstart_entry.insert(0, self.aoc_field_defaults['lst_start'])
            lstop_label = tkinter.Label(self.frame_update, text='Source', width=10)
            lstop_label.grid(row=r, column=c+2)
            self.lstop_entry = tkinter.Entry(self.frame_update)
            self.lstop_entry.grid(row=r, column=c+3)
            self.lstop_entry.insert(0, self.aoc_field_defaults['lst_stop'])
        # Row 3
        r, c = 3, 0
        state_label = tkinter.Label(self.frame_update, text='State', width=10)
        state_label.grid(row=r, column=c)
        self.state_entry = tkinter.Entry(self.frame_update)
        self.state_entry.grid(row=r, column=c+1)
        self.state_entry.insert(0, self.aoc_field_defaults['state'])
        note_label = tkinter.Label(self.frame_update, text='Note', width=10)
        note_label.grid(row=r, column=c+2)
        self.note_entry = tkinter.Entry(self.frame_update)
        self.note_entry.grid(row=r, column=c+3)
        self.note_entry.insert(0, self.aoc_field_defaults['note'])
        # Row 4
        r, c = 4, 0
        obs_label = tkinter.Label(self.frame_update, text='Observer', width=10)
        obs_label.grid(row=r, column=c)
        self.obs_entry = tkinter.Entry(self.frame_update)
        self.obs_entry.grid(row=r, column=c+1)
        self.obs_entry.insert(0, self.aoc_field_defaults['observer'])
        email_label = tkinter.Label(self.frame_update, text='E-mail', width=10)
        email_label.grid(row=r, column=c+2)
        self.email_entry = tkinter.Entry(self.frame_update)
        self.email_entry.grid(row=r, column=c+3)
        self.email_entry.insert(0, self.aoc_field_defaults['email'])
        # Row 5
        submit_button = tkinter.Button(self.frame_update, text=gobutton, width=10, justify=tkinter.CENTER, command=self.submit)
        submit_button.grid(row=5, column=1)
        cancel_button = tkinter.Button(self.frame_update, text='Cancel', width=10, justify=tkinter.CENTER, command=self.reset)
        cancel_button.grid(row=5, column=3)

    def schedule_by_utc(self):
        self.reset()
        self.aoc_action = 'add'
        self.aoc_field_defaults['utc_start'] = times.interp_date(self.aoc_day, fmt='%Y-%m-%d')
        self.aoc_field_defaults['utc_stop'] = times.interp_date(self.aoc_day, fmt='%Y-%m-%d')
        self.schedule_by = 'utc'
        self.event_fields('Add')
    def schedule_by_lst(self):
        self.reset()
        self.aoc_action = 'add'
        self.aoc_field_defaults['utc_start'] = times.interp_date(self.aoc_day, fmt='%Y-%m-%d')
        self.aoc_field_defaults['utc_stop'] = times.interp_date(self.aoc_day, fmt='%Y-%m-%d')
        self.schedule_by = 'lst'
        self.event_fields('Add')
    def schedule_by_src(self):
        self.reset()
        self.aoc_action = 'add'
        self.aoc_field_defaults['utc_start'] = times.interp_date(self.aoc_day, fmt='%Y-%m-%d')
        self.aoc_field_defaults['utc_stop'] = times.interp_date(self.aoc_day, fmt='%Y-%m-%d')
        self.schedule_by = 'source'
        self.event_fields('Add')

    def add_event(self):
        self.reset()
        # self.aoc_action = 'add'
        # self.aoc_field_defaults['utc_start'] = times.interp_date(self.aoc_day, fmt='%Y-%m-%d')
        # self.aoc_field_defaults['utc_stop'] = times.interp_date(self.aoc_day, fmt='%Y-%m-%d')
        sched_label = tkinter.Label(self.frame_update, text='Schedule by:')
        sched_label.grid(row=0, column=0, padx=5)
        # fgclr = 'lightgray' if self.schedule_by == 'utc' else 'black'
        fgclr = 'black'
        utc_button = tkinter.Button(self.frame_update, text="UTC", fg=fgclr, width=10, command=self.schedule_by_utc)
        utc_button.grid(row=1, column=0, padx=5)
        # fgclr = 'lightgray' if self.schedule_by == 'lst' else 'black'
        lst_button = tkinter.Button(self.frame_update, text="LST", fg=fgclr, width=10, command=self.schedule_by_lst)
        lst_button.grid(row=2, column=0, padx=5)
        # fgclr = 'lightgray' if self.schedule_by == 'source' else 'black'
        src_button = tkinter.Button(self.frame_update, text="Source", fg=fgclr, width=10, command=self.schedule_by_src)
        src_button.grid(row=3, column=0, padx=5)
        # self.event_fields('Add')

    def del_event(self):
        self.reset()
        self.aoc_action = 'delete'
        daykey = self.aoc_day.strftime('%Y-%m-%d')
        try:
            num_events = len(self.this_cal.events[daykey])
        except KeyError:
            logger.warning(f"{daykey} does not exist")
            return
        if  num_events > 1:
            entry = simpledialog.askstring("Input", f"{daykey} entry #", parent=self)
            if entry is None:
                return
            self.aoc_nind = int(entry)
        else:
            self.aoc_nind = 0
        try:
            this_entry = self.this_cal.events[daykey][self.aoc_nind]
        except IndexError:
            logger.warning(f"Entry {self.aoc_nind} does not exist in {daykey}.")
            self.reset()
            return
        info = f"{self.aoc_nind} - {this_entry.name}: {this_entry.utc_start.datetime.isoformat(timespec='seconds')}"
        info += f" - {this_entry.utc_stop.datetime.isoformat(timespec='seconds')}"
        verify = tkinter.Label(self.frame_update, text=info)
        verify.grid_rowconfigure(0, weight=1)
        verify.grid(row=0, column=0, columnspan=2, sticky="NS")
        submit_button = tkinter.Button(self.frame_update, text="Delete", width=10, command=self.submit)
        submit_button.grid(row=1, column=0, sticky="NS")
        cancel_button = tkinter.Button(self.frame_update, text='Cancel', width=10, command=self.reset)
        cancel_button.grid(row=1, column=1, sticky="NS")

    def upd_event(self):
        self.reset()
        daykey = self.aoc_day.strftime('%Y-%m-%d')
        self.aoc_action = 'update'
        try:
            num_events = len(self.this_cal.events[daykey])
        except KeyError:
            logger.warning(f"{daykey} does not exist")
            return
        if num_events > 1:
            entry = simpledialog.askstring("Input", f"{daykey} entry #", parent=self)
            if entry is None:
                return
            self.aoc_nind = int(entry)
        else:
            self.aoc_nind = 0
        try:
            this_entry = self.this_cal.events[daykey][self.aoc_nind]
        except IndexError:
            logger.warning(f"Entry {self.aoc_nind} does not exist in {daykey}.")
            self.reset(refresh=False)
            return
        for field in this_entry.fields:
            self.aoc_field_defaults[field] = getattr(this_entry, field)
        self.aoc_field_defaults['lst_start'] = f"{self.aoc_field_defaults['lst_start'].to_string(precision=0)} - can't update"
        self.aoc_field_defaults['lst_stop'] = f"{self.aoc_field_defaults['lst_stop'].to_string(precision=0)} - can't update"
        self.event_fields('Update')

    def schedule(self):
        self.reset()
        name_label = tkinter.Label(self.frame_update, text='Name')
        name_label.grid(row=0, column=0)
        self.name_entry = tkinter.Entry(self.frame_update)
        self.name_entry.grid(row=0, column=1)
        pid_label = tkinter.Label(self.frame_update, text='pid')
        pid_label.grid(row=0, column=2)
        self.pid_entry = tkinter.Entry(self.frame_update)
        self.pid_entry.grid(row=0, column=3)

        source_label = tkinter.Label(self.frame_update, text='RA,dec or source')
        source_label.grid(row=1, column=0)
        self.source_entry = tkinter.Entry(self.frame_update)
        self.source_entry.grid(row=1, column=1)
        day_label = tkinter.Label(self.frame_update, text='UTC day')
        day_label.grid(row=1, column=2)
        self.day_entry = tkinter.Entry(self.frame_update)
        self.day_entry.grid(row=1, column=3)
        self.day_entry.insert(0, self.tkcal.selection_get().strftime('%Y-%m-%d'))

        duration_label = tkinter.Label(self.frame_update, text='length [h]')
        duration_label.grid(row=2, column=0)
        self.duration_entry = tkinter.Entry(self.frame_update)
        self.duration_entry.grid(row=2, column=1)
        self.duration_entry.insert(0, '6')
        note_label = tkinter.Label(self.frame_update, text='Note')
        note_label.grid(row=2, column=2)
        self.note_entry = tkinter.Entry(self.frame_update)
        self.note_entry.grid(row=2, column=3)

        submit_button = tkinter.Button(self.frame_update, text='Schedule', width=10, command=self.doschedule)
        submit_button.grid(row=3, column=1)
        cancel_button = tkinter.Button(self.frame_update, text='Cancel', width=10, command=self.reset)
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
        self.is_scheduled = self.this_cal.schedule(ra=ra, dec=dec, source=source, day=day, duration=duration, name=name, pid=pid, note=note)
        self.aoc_action = 'schedule'
        self.aoc_day = times.truncate_to_day(day)
        self.aoc_nind = -1
        self.submit()


