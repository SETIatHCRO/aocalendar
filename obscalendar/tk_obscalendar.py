#! /usr/bin/env python

import tkinter
from tkinter import simpledialog, messagebox
from tkcalendar import Calendar
from obscalendar import obscalendar


def t2iso(t):
    mn, dy, yr = t.split("/")
    return f"20{yr}-{mn}-{dy}"

class ObservingCalendarApp(tkinter.Tk):
    def __init__(self, **kwargs):
        super().__init__()
        self.title("Allen Telescope Array Observing Calendar")

        # Set window size to 1200x900
        self.geometry("900x1000")

        calfile = kwargs['calfile'] if 'calfile' in kwargs else 'now'
        path = kwargs['path'] if 'path' in kwargs else 'getenv'
        output = kwargs['output'] if 'output' in kwargs else 'INFO'

        self.this_cal = obscalendar.Calendar(calfile=calfile, path=path, output=output)
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
        self.reset()
        info_text = tkinter.Text(self.frame_info)
        info_text.grid(row=0, column=0, columnspan=4)
        info_text.insert(tkinter.INSERT, f"CALENDAR DATE INFORMATION: {self.this_cal.calfile_fullpath}")

        # Update
        self.frame_update.grid(row=3, column=0)

    def refresh(self):
        self.this_cal.read_calendar_contents(calfile='refresh')

    def show_date(self):
        datestr = t2iso(self.tkcal.get_date())
        entry = f"{self.this_cal.calfile_fullpath} SCHEDULE FOR {datestr}\n\n"
        try:
            entry += self.this_cal.format_day_contents(datestr, return_as='table')
            entry += self.this_cal.graph_day(datestr)
        except KeyError:
            entry += "No entry."
        info_text = tkinter.Text(self.frame_info, width=800)
        info_text.grid(row=0, column=0, columnspan=4)
        info_text.insert(tkinter.CURRENT, entry)

    def submit(self):
        kwargs = {
            'name': self.name_entry.get(),
            'ID': self.ID_entry.get(),
            'utc_start': self.start_entry.get(),
            'utc_stop': self.stop_entry.get(),
            'state': self.state_entry.get(),
            'note': self.note_entry.get(),
            'observer': self.obs_entry.get(),
            'email': self.email_entry.get()
        }
        self.this_cal.edit(self.action, entry=self.entry, **kwargs)
        yn=messagebox.askquestion('Write Calendar', 'Do you want to write calendar file with edits?')
        if yn == 'yes' :
            self.this_cal.write_calendar()
        else :
            messagebox.showinfo('Return', 'Not writing new calendar.')
        self.reset()
    
    def reset(self):
        self.action = None
        self.upddef = {}
        self.entry = None

    def schedule(self):
        rdu = simpledialog.askstring("Input", "RA,dec,utc", parent=self)
        if rdu is None:
            return
        ra, dec, utc = rdu.split(',')
        self.this_cal.schedule(ra=ra, dec=dec, day=utc)
        # self.upddef = {}
        # this_entry = self.this_cal.contents[this_entry_key][int(num)]
        # for field in this_entry.fields:
        #     self.upddef[field] = getattr(this_entry, field)
        # self.add_event(action='update')

    def add_event(self, action='add'):
        if action == 'add':
            self.upddef = {}
            for fld in obscalendar.ENTRY_FIELDS:
                self.upddef[fld] = ''
            self.upddef['utc_start'] = self.this_cal.refdate
            self.upddef['utc_stop'] = self.this_cal.refdate
            self.upddef['state'] = 'primary'
            self.entry = None
        self.action = action

        #self.frame_update.grid(row=3, column=0, columnspan=2)
        name_label = tkinter.Label(self.frame_update, text='Name')
        name_label.grid(row=0, column=0)
        self.name_entry = tkinter.Entry(self.frame_update)
        self.name_entry.grid(row=0, column=1)
        self.name_entry.insert(0, self.upddef['name'])
        ID_label = tkinter.Label(self.frame_update, text='ID')
        ID_label.grid(row=0, column=2)
        self.ID_entry = tkinter.Entry(self.frame_update)
        self.ID_entry.grid(row=0, column=3)
        self.ID_entry.insert(0, self.upddef['ID'])

        start_label = tkinter.Label(self.frame_update, text='UTC start')
        start_label.grid(row=1, column=0)
        self.start_entry = tkinter.Entry(self.frame_update)
        self.start_entry.grid(row=1, column=1)
        self.start_entry.insert(0, self.upddef['utc_start'].datetime.isoformat(timespec='minutes'))
        stop_label = tkinter.Label(self.frame_update, text='UTC stop')
        stop_label.grid(row=1, column=2)
        self.stop_entry = tkinter.Entry(self.frame_update)
        self.stop_entry.grid(row=1, column=3)
        self.stop_entry.insert(0, self.upddef['utc_stop'].datetime.isoformat(timespec='minutes'))

        state_label = tkinter.Label(self.frame_update, text='State')
        state_label.grid(row=2, column=0)
        self.state_entry = tkinter.Entry(self.frame_update)
        self.state_entry.grid(row=2, column=1)
        self.state_entry.insert(0, self.upddef['state'])
        note_label = tkinter.Label(self.frame_update, text='Note')
        note_label.grid(row=2, column=2)
        self.note_entry = tkinter.Entry(self.frame_update)
        self.note_entry.grid(row=2, column=3)
        self.note_entry.insert(0, self.upddef['note'])

        obs_label = tkinter.Label(self.frame_update, text='Observer')
        obs_label.grid(row=3, column=0)
        self.obs_entry = tkinter.Entry(self.frame_update)
        self.obs_entry.grid(row=3, column=1)
        self.obs_entry.insert(0, self.upddef['observer'])
        email_label = tkinter.Label(self.frame_update, text='E-mail')
        email_label.grid(row=3, column=2)
        self.email_entry = tkinter.Entry(self.frame_update)
        self.email_entry.grid(row=3, column=3)
        self.email_entry.insert(0, self.upddef['email'])

        submit_button = tkinter.Button(self.frame_update, text='Submit', command=self.submit)
        submit_button.grid(row=4, column=1)
        cancel_button = tkinter.Button(self.frame_update, text='Cancel', command=self.reset)
        cancel_button.grid(row=4, column=3)

    def del_event(self):
        entry = simpledialog.askstring("Input", "YYYY-MM-DD:#", parent=self)
        if entry is None:
            return
        self.this_cal.edit('delete', entry=entry)
        self.this_cal.write_calendar()

    def upd_event(self):
        self.entry = simpledialog.askstring("Input", "YYYY-MM-DD:#", parent=self)
        if self.entry is None:
            return
        this_entry_key, num = obscalendar.split_entry(self.entry)
        self.upddef = {}
        this_entry = self.this_cal.contents[this_entry_key][int(num)]
        for field in this_entry.fields:
            self.upddef[field] = getattr(this_entry, field)
        self.add_event(action='update')






