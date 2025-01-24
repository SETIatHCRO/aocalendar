# -*- mode: python; coding: utf-8 -*-
# Copyright 2025 David R DeBoer
# Licensed under the MIT license.

import tkinter
from tkinter import simpledialog, messagebox
from tkcalendar import Calendar
from aocalendar import aocalendar, times, tools, logger_setup, __version__, google_calendar_sync
import logging
from datetime import datetime
from copy import copy

UPDATE_TK = 300000

logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')


def etable(frame, header, data, start=0, width=10, fg='black', bg='white', font='Arial', fontsize=10):
    if isinstance(width, int) and isinstance(data, list):
        width = [width] * len(data[0])
    if len(header):
        for j, h in enumerate(header):
            entry = tkinter.Entry(frame, width=width[j], fg=fg, bg=bg, font=(font, fontsize, 'bold'))
            entry.grid(row=start, column=j)
            entry.insert(tkinter.END, h)
    for i, this_row in enumerate(data):
        for j, this_entry in enumerate(this_row):
            entry = tkinter.Entry(frame, width=width[j], fg=fg, bg=bg, font=(font, fontsize))
            entry.grid(row=i+start+1, column=j)
            entry.insert(tkinter.END, this_entry)

def egraph(frame, header, data, fg='black', font='Arial', fontsize=10):
    bgclr = {'v': 'red', '^': 'red', '@': 'red', '.': 'grey', '*': 'blue', ' ': 'white'}
    #maxline = max([len(x) for x in data.rows])
    maxline = data.N + 4
    for i in range(len(data.g_info['rows'])):
        for j in range(maxline):
            try:
                this_char = data.g_info['rows'][i][j]
                this_width = data.g_info['width'][j]
            except IndexError:
                this_char, this_width = ' ', 1
            bg = bgclr[this_char] if this_char in bgclr else 'white'
            if bg == 'red': this_char = ' '
            entry = tkinter.Entry(frame, fg=fg, bg=bg, width=this_width, font=(font, fontsize), borderwidth=0, highlightthickness=0, justify='right')
            entry.grid(row=i, column=j)
            entry.insert(tkinter.END, this_char)

class AOCalendarApp(tkinter.Tk):
    def __init__(self, **kwargs):
        super().__init__()
        self.title("Allen Telescope Array Observing Calendar")

        # Set window size to 1200x900
        #self.geometry("1000x820")
        self.resizable(0, 0)

        calfile = kwargs['calfile'] if 'calfile' in kwargs else 'now'
        path = kwargs['path'] if 'path' in kwargs else 'getenv'
        ods = kwargs['ods'] if 'ods' in kwargs else False
        conlog = kwargs['conlog'] if 'conlog' in kwargs else 'INFO'
        filelog = kwargs['filelog'] if 'filelog' in kwargs else False
        path = tools.determine_path(path=path, fileinfo=calfile)
        self.logset = logger_setup.Logger(logger, conlog=conlog, filelog=filelog, log_filename='aoclog', path=path)
        logger.info(f"{__name__} ver. {__version__}")

        self.this_cal = aocalendar.Calendar(calfile=calfile, path=path, conlog=self.logset.conlog, filelog=self.logset.filelog)
        self.aoc_day = times.truncate_to_day(self.this_cal.refdate)
        self.schedule_by = 'utc'

        # Create all of the frames
        self.frame_calendar = tkinter.Frame(self)
        self.frame_calendar.grid(row=0, column=0)
        self.frame_buttons = tkinter.Frame(self)
        self.frame_buttons.grid(row=0, column=1)   
        self.frame_table = tkinter.Frame(self, borderwidth=2, relief='groove')
        self.frame_table.grid(row=1, column=0, columnspan=2)
        self.frame_graph = tkinter.Frame(self, borderwidth=2, relief='groove')
        self.frame_graph.grid(row=2, column=0, columnspan=2)
        self.frame_update = tkinter.Frame(self)
        self.frame_update.grid(row=3, column=0, columnspan=2)

        # Layout all of the frames 4 rows, 1 column
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)

        # Calendar
        self.tkcal = Calendar(self.frame_calendar, selectmode='day', year=self.aoc_day.year, month=self.aoc_day.month, day=self.aoc_day.day,
                              font="Arial 18", showweeknumbers=False, foreground='grey', selectforeground='blue', firstweekday='sunday',
                              showothermonthdays=False)
        self.tkcal.grid(row=0, column=0)

        for _, events in self.this_cal.events.items():
            for event in events:
                label = f"{event.program}:{event.pid}"
                self.tkcal.calevent_create(event.utc_start.datetime, label, 'obs')
        self.tkcal.tag_config('obs', foreground='red')
        self.tkcal.bind("<<CalendarSelected>>", self.show_date)
        if ods is not None:
            self.ods_input = ods
            self.this_cal.start_ods()
        self.tk_update()

        # Buttons/checkbox/clock
        today_button = tkinter.Button(self.frame_buttons, text = "Today", width=12, command = self.goto_today)
        today_button.grid(row=0, column=0)
        rst_button = tkinter.Button(self.frame_buttons, text = "Reset", width=12, command = self.resetTrue)
        rst_button.grid(row=1, column=0)
        add_button = tkinter.Button(self.frame_buttons, text = "New", width=12, command = self.add_event)
        add_button.grid(row=0, column=1)
        del_button = tkinter.Button(self.frame_buttons, text = "Delete", width=12, command = self.delete_event)
        del_button.grid(row=1, column=1)
        upd_button = tkinter.Button(self.frame_buttons, text = "Edit", width=12, command = self.update_event)
        upd_button.grid(row=2, column=1)
        self.chk_var = tkinter.BooleanVar()
        checkbutton = tkinter.Checkbutton(self.frame_buttons, text="Google Calendar Link", variable=self.chk_var, 
                                          onvalue=True, offvalue=False, command=self.google_calendar_button_toggle)
        checkbutton.grid(row=5, column=0, columnspan=2, pady=15)
        self.google_calendar_linked = False
        self.google_calendar = None
        self.deleted_event_id = False

        # Info
        self.show_date(self.aoc_day)        

    def tk_update(self):
        if self.this_cal.ods is not None:
            active = self.this_cal.ods.check_active('now', read_from=self.ods_input)
            if len(active):
                bg = 'green'
                text = f"ODS active ({len(active)})"
            else:
                bg = 'red'
                text = f"ODS not active."
            self.ods_label = tkinter.Label(self.frame_calendar, text=text, bg=bg, width=20)
            self.ods_label.grid(row=1, column=0)
        self.show_date(self.aoc_day)
        self.update_idletasks()
        self.after(UPDATE_TK, self.tk_update)

    def google_calendar_button_toggle(self):
        self.google_calendar_linked = self.chk_var.get()
        logger.info(f"Google Calendar linking is {'on' if self.google_calendar_linked else 'off'}")
        self.reload_google_calendar()
        self.refresh()
    def reload_google_calendar(self):
        if self.google_calendar_linked:
            self.google_calendar = google_calendar_sync.SyncCal()
            self.google_calendar.sequence(update_google_calendar=False)

    def update_clock(self):
        lbl = tkinter.Label(self.frame_buttons, text='UTC', width=10)
        lbl.grid(row=6, column=0)
        utc_clock = tkinter.Entry(self.frame_buttons, width=10, fg='black', bg='white', font=('Arial', 11))
        utc_clock.grid(row=7, column=0)
        utc_clock.insert(tkinter.END, 'utc')

        lbl = tkinter.Label(self.frame_buttons, text='LST', width=10)
        lbl.grid(row=6, column=1)
        lst_clock = tkinter.Entry(self.frame_buttons, width=10, fg='black', bg='white', font=('Arial', 11))
        lst_clock.grid(row=7, column=1)
        lst_clock.insert(tkinter.END, 'lst')

    def goto_today(self):
        self.show_date('now')

    def refresh(self):
        self.this_cal.read_calendar_events(calfile='refresh')
        self.reload_google_calendar()
        self.tkcal.calevent_remove('all')
        for day, events in self.this_cal.events.items():
            for event in events:
                label = f"{event.program}:{event.pid}"
                self.tkcal.calevent_create(event.utc_start.datetime, label, 'obs')

    def teardown_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()
    def rebuild_frame(self, frame, row, column, columnspan=1, borderwidth=2, relief='groove'):
        frame.destroy()
        frame = tkinter.Frame(self, borderwidth=borderwidth, relief=relief)
        frame.grid(row=row, column=column, columnspan=columnspan)

    def resetFalse(self):
        self.reset(refresh_flag=False)
    def resetTrue(self):
        self.reset(refresh_flag=True)
    def reset(self, refresh_flag):
        if refresh_flag:
            self.refresh()
        self.aoc_action = ''
        self.aoc_field_defaults = {}
        for key in aocalendar.aocentry.ENTRY_FIELDS:
            self.aoc_field_defaults[key] = ''
        self.aoc_nind = 0
        self.deleted_event_id = False
        self.teardown_frame(self.frame_update)

    def show_date(self, dateinp=None):
        """Show date in frame_table/frame_graph"""
        self.update_clock()
        #self.rebuild_frame(self.frame_table, row=1, column=0, columnspan=2, borderwidth=2, relief='groove')
        #self.rebuild_frame(self.frame_graph, row=2, column=0, columnspan=2, borderwidth=2, relief='groove')
        if str(dateinp)[0] == '<' or dateinp is None:
            mdy = self.tkcal.get_date()
            m,d,y = mdy.split('/')
            self.aoc_day = datetime(year=2000+int(y), month=int(m), day=int(d))
        else:
            self.aoc_day = times.truncate_to_day(dateinp)
            self.tkcal.selection_set(self.aoc_day)
        entry_title = f"{self.this_cal.calfile_fullpath} SCHEDULE FOR {self.aoc_day.strftime('%Y-%m-%d')}"
        try:
            entry_list, header = self.this_cal.list_day_events(self.aoc_day, return_as='list')
            entry_graph = self.this_cal.graph_day_events(self.aoc_day, tz='US/Pacific', interval_min=15.0, return_anyway=True)
        except KeyError:
            entry_list = "No entry."
            entry_graph = ''
        info_text_t = tkinter.Entry(self.frame_table, width=len(entry_title), justify='center', font=('Arial', 12, 'bold'))
        info_text_t.grid(row=0, column=0, columnspan=9)
        info_text_t.insert(0, entry_title)
        width = [2, 18, 7, 18, 18, 10, 10, 15, 10]
        etable(self.frame_table, header=header, data=entry_list, width=width, start=1, fontsize=12)
        if True:
            egraph(self.frame_graph, header=[], data=self.this_cal.calgraph, font='Arial', fontsize=10)
        else:
            font = ('Courier New', 14)
            width = max([len(x) for x in entry_graph.splitlines()])
            info_text_g = tkinter.Text(self.frame_graph, borderwidth=2, relief='groove', width=width, height=12, yscrollcommand=True, font=font)
            info_text_g.grid(row=0, column=0)
            info_text_g.insert(tkinter.INSERT, entry_graph)

    def submit(self):
        if self.aoc_action == 'delete':
            aoc_day = self.aoc_day
            is_ok = self.this_cal.delete(day=aoc_day, nind=self.aoc_nind)
        else:
            kwargs = {
                'program': self.program_entry.get().strip(),
                'pid': self.pid_entry.get().strip(),
                'commensal': self.commensal_entry.get().strip(),
                'note': self.note_entry.get().strip(),
                'observer': self.obs_entry.get().strip(),
                'email': self.email_entry.get().strip()
            }
            if self.aoc_action == 'update' or self.schedule_by == 'utc':
                kwargs.update({
                    'utc_start': self.start_entry.get().strip(),
                    'utc_stop': self.stop_entry.get().strip()
                })
            elif self.schedule_by == 'lst':
                kwargs.update({
                    'utc_start': self.start_entry.get().strip(),
                    'lst_start': self.lstart_entry.get().strip(),
                    'lst_stop': self.lstop_entry.get().strip()
                })
            elif self.schedule_by == 'source':
                kwargs.update({
                    'utc_start': self.start_entry.get().strip()
                })
        if self.aoc_action == 'update':
            aoc_day = self.aoc_day
            is_ok = self.this_cal.update(day=aoc_day, nind=self.aoc_nind, **kwargs)
        elif self.aoc_action == 'add':
            if self.schedule_by == 'source':
                aoc_day = times.truncate_to_day(kwargs['utc_start'])
                source = self.program_entry.get()
                ra = self.ra_entry.get()
                dec = self.dec_entry.get()
                duration = float(self.duration_entry.get())
                is_ok = self.this_cal.schedule(ra=ra, dec=dec, source=source, day=aoc_day, duration=duration, **kwargs)
                if is_ok:
                    newhash = self.this_cal.most_recent_event.hash(cols='web')
                    self.this_cal.make_hash_keymap(cols='web')
                    self.aoc_day, self.aoc_nind = self.this_cal.hashmap[newhash]
            elif self.aoc_action == 'add':
                aoc_day = times.truncate_to_day(kwargs['utc_start'])
                is_ok = self.this_cal.add(**kwargs)
        if is_ok:
            self.show_date(aoc_day)
            self.this_cal.write_calendar()
            self.resetTrue()
            if self.google_calendar_linked:
                if messagebox.askyesno("Google Calendar", "Do you wish to update Google Calendar?"):
                    self.update_google_calendar()
        else:
            self.resetFalse()
            logger.warning("Did not succeed.")

    def update_google_calendar(self):
        if self.aoc_action == 'add':
            self.google_calendar.add_event_to_google_calendar(self.this_cal[self.aoc_day][self.aoc_nind])
        elif self.aoc_action == 'update':
            self.google_calendar.update_event_on_google_calendar(self.this_cal[self.aoc_day][self.aoc_nind])
        elif self.aoc_action == 'delete' and self.deleted_event_id:
            self.google_calendar.delete_event_from_google_calendar(self.deleted_event_id)

    def label_event(self, frame, row, col, elbl, lentry):
        lbl = tkinter.Label(frame, text=elbl, width=10, anchor='e')
        lbl.grid(row=row, column=col)
        if len(elbl.strip()):
            entry = tkinter.Entry(frame, width=20)
            entry.grid(row=row, column=col+1)
            entry.insert(0, lentry)
        return entry

    def event_fields(self, gobutton):
        # row 0 - program/pid
        pslbl = 'Source' if self.schedule_by == 'source' else 'Program'
        self.program_entry = self.label_event(self.frame_update, 0, 0, pslbl, self.aoc_field_defaults['program'])
        self.pid_entry = self.label_event(self.frame_update, 0, 2, "pid", self.aoc_field_defaults['pid'])
        # row 1 - utc_start/utc_stop
        if self.aoc_action == 'add':
            addon = 'T00:00' if self.schedule_by == 'utc' else ''
            utcstart = self.aoc_field_defaults['utc_start'] + addon
            utcstop = self.aoc_field_defaults['utc_start'] + addon
            utclabel = 'UTC start' if self.schedule_by == 'utc' else 'UTC day'
        elif self.aoc_action == 'update':
            utclabel = 'UTC start'
            utcstart = self.aoc_field_defaults['utc_start'].datetime.isoformat(timespec='minutes')
            utcstop = self.aoc_field_defaults['utc_stop'].datetime.isoformat(timespec='minutes')
        self.start_entry = self.label_event(self.frame_update, 1, 0, utclabel, utcstart)
        if self.schedule_by == 'utc' or self.aoc_action == 'update':
            self.stop_entry = self.label_event(self.frame_update, 1, 2, 'UTC stop', utcstop)
        # row 2 - lst_start/lst_stop
        if self.schedule_by == 'lst':
            self.lstart_entry = self.label_event(self.frame_update, 2, 0, 'LST start', '')
            self.lstop_entry = self.label_event(self.frame_update, 2, 2, 'LST stop', '')
        elif self.schedule_by == 'source':
            self.duration_entry = self.label_event(self.frame_update, 1, 2, 'Duration (hr)', '12')
            self.ra_entry = self.label_event(self.frame_update, 2, 0, 'RA', '')
            self.dec_entry = self.label_event(self.frame_update, 2, 2, 'Dec', '')
        # Row 3 - commensal/note
        self.commensal_entry = self.label_event(self.frame_update, 3, 0, 'State', 'primary')
        self.note_entry = self.label_event(self.frame_update, 3, 2, 'Note', '')
        # Row 4 - observer/email
        self.obs_entry = self.label_event(self.frame_update, 4, 0, 'Observer', '')
        self.email_entry = self.label_event(self.frame_update, 4, 2, 'E-mail', '')
        # Row 5
        submit_button = tkinter.Button(self.frame_update, text=gobutton, width=10, justify=tkinter.CENTER, command=self.submit)
        submit_button.grid(row=5, column=1)
        cancel_button = tkinter.Button(self.frame_update, text='Cancel', width=10, justify=tkinter.CENTER, command=self.resetFalse)
        cancel_button.grid(row=5, column=3)

    def schedule_by_utc(self):
        self.teardown_frame(self.frame_update)
        self.schedule_by = 'utc'
        self.event_fields('Add')
    def schedule_by_lst(self):
        self.teardown_frame(self.frame_update)
        self.schedule_by = 'lst'
        self.event_fields('Add')
    def schedule_by_src(self):
        self.teardown_frame(self.frame_update)
        self.schedule_by = 'source'
        self.event_fields('Add')

    def add_event(self):
        self.resetFalse()
        self.aoc_action = 'add'
        self.aoc_field_defaults['utc_start'] = times.interp_date(self.aoc_day, fmt='%Y-%m-%d')
        self.aoc_field_defaults['utc_stop'] = times.interp_date(self.aoc_day, fmt='%Y-%m-%d')
        sched_label = tkinter.Label(self.frame_update, text='Schedule by:')
        sched_label.grid(row=0, column=0, padx=5)
        fgclr = 'black'
        utc_button = tkinter.Button(self.frame_update, text="UTC", fg=fgclr, width=10, command=self.schedule_by_utc)
        utc_button.grid(row=1, column=0, padx=5)
        lst_button = tkinter.Button(self.frame_update, text="LST", fg=fgclr, width=10, command=self.schedule_by_lst)
        lst_button.grid(row=2, column=0, padx=5)
        src_button = tkinter.Button(self.frame_update, text="Source", fg=fgclr, width=10, command=self.schedule_by_src)
        src_button.grid(row=3, column=0, padx=5)
        cancel_button = tkinter.Button(self.frame_update, text='Cancel', width=10, justify=tkinter.CENTER, command=self.resetFalse)
        cancel_button.grid(row=5, column=0, pady=15)

    def get_entry_nind(self, daykey):
        try:
            num_events = len(self.this_cal.events[daykey])
        except KeyError:
            logger.warning(f"{daykey} does not exist")
            return None
        if  num_events > 1:
            entry_num = simpledialog.askstring("Get Entry", f"{daykey} entry #", parent=self)
            try:
                self.aoc_nind = int(entry_num)
            except (TypeError, ValueError):
                logger.warning(f"Invalid entry: {entry_num}")
                return None
        else:
            self.aoc_nind = 0
        try:
            return self.this_cal.events[daykey][self.aoc_nind]
        except IndexError:
            logger.warning(f"Entry {self.aoc_nind} does not exist in {daykey}.")
            return None

    def update_event(self):
        self.resetFalse()
        self.aoc_action = 'update'
        self.schedule_by = 'N/A'
        daykey = self.aoc_day.strftime('%Y-%m-%d')
        this_entry = self.get_entry_nind(daykey)
        if this_entry is None:
            self.resetFalse()
            return
        for field in this_entry.fields:
            self.aoc_field_defaults[field] = getattr(this_entry, field)
        self.event_fields('Update')

    def delete_event(self):
        self.resetFalse()
        self.aoc_action = 'delete'
        self.schedule_by = 'N/A'
        daykey = self.aoc_day.strftime('%Y-%m-%d')
        this_entry = self.get_entry_nind(daykey)
        if this_entry is None:
            self.resetFalse()
            return
        try:
            self.deleted_event_id = copy(this_entry.event_id)
        except AttributeError:
            self.deleted_event_id = False
        info = f"{self.aoc_nind} - {this_entry.program}: {this_entry.utc_start.datetime.isoformat(timespec='seconds')}"
        info += f" - {this_entry.utc_stop.datetime.isoformat(timespec='seconds')}"
        verify = tkinter.Label(self.frame_update, text=info, fg='red')
        verify.grid_rowconfigure(0, weight=1)
        verify.grid(row=0, column=0, columnspan=2, sticky="NS")
        submit_button = tkinter.Button(self.frame_update, text="Delete", width=10, command=self.submit)
        submit_button.grid(row=1, column=0, sticky="NS")
        cancel_button = tkinter.Button(self.frame_update, text='Cancel', width=10, command=self.resetFalse)
        cancel_button.grid(row=1, column=1, sticky="NS")