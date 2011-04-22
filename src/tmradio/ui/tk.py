# encoding=utf-8

"""Tk interface for the tmradio client.

TODO:
- Set width of the nick list.
- Put images on buttons.
"""

import time

import tkFont
import Tkinter as tk

import tmradio.audio
import tmradio.jabber


class VScrollControl(tk.Frame):
    """Vertical scroller.

    Adds a vertical scroll bar to any control.  The control is created by
    calling the `factory' function, which receives a parent as the only
    parameter.  The rest is done automatically.
    """
    def __init__(self, master, factory, **kwargs):
        tk.Frame.__init__(self, master, **kwargs)

        self.scrollbar = tk.Scrollbar(self)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.ctl = factory(self)
        self.ctl.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        self.scrollbar.config(command=self.ctl.yview)
        self.ctl['yscrollcommand'] = self.scrollbar.set


class NickList(VScrollControl):
    """The list of nicknames.

    Supports vertical scrolling, clicking and double clicking (which should add
    nicknames to the entry box, using callbacks).
    """
    def __init__(self, master):
        """Initializes with no data."""
        VScrollControl.__init__(self, master, lambda p: tk.Listbox(p, highlightthickness=0, bd=2))

        #self.ctl.bind('<ButtonRelease-1>', self.on_click)
        #self.ctl.bind('<Double-Button-1>', self.on_double_click)

        self.data = []

    def add(self, nickname):
        """Adds a nickname to the end of the list.

        TODO: sort alphabetically.
        """
        if not nickname in self.data:
            self.data.append(nickname)
            self.ctl.insert(tk.END, nickname)

    def remove(self, nickname):
        pass # FIXME


class ChatView(VScrollControl):
    """A text based chat window.

    Shows timestamped messages with sources (nicknames, bold).  Supports
    hyperlinks in the messages (blue, underlined).  The nicknames can also be
    hyperlinked.
    """
    def __init__(self, master):
        VScrollControl.__init__(self, master, lambda p: tk.Text(p, bd=2, highlightthickness=0, state=tk.DISABLED))

        font_family = 'Ubuntu'
        font_size = 9

        font = tkFont.Font(family=font_family, weight='normal', size=font_size)
        self.ctl.config(font=font)

        font = tkFont.Font(family=font_family, size=font_size)
        self.ctl.tag_config('ts', font=font, foreground='gray')

        font = tkFont.Font(family=font_family, weight='bold', size=font_size)
        self.ctl.tag_config('nick', font=font)

    def add_message(self, message, nickname, ts=None):
        ts = ts or int(time.time())
        ts_text = time.strftime('%d.%m %H:%M', time.localtime(ts))

        self.ctl.config(state=tk.NORMAL)

        self.ctl.insert(tk.END, ts_text + ' ', 'ts')
        self.ctl.insert(tk.END, nickname, 'nick')
        self.ctl.insert(tk.END, u': ' + message.rstrip() + u'\n')


class Toolbar(tk.Frame):
    """The main toolbar.

    Contains buttons that send commands to the jabber when clicked.

    Arguments:
    master -- the parent frame
    audio -- the player, must conform to tmradio.audio
    """
    def __init__(self, master, audio):
        tk.Frame.__init__(self, master)

        self.audio = audio
        self.jabber = None
        self.track_info = {}

        self.btn_play = tk.Button(self, text=">", command=self.on_play_clicked)
        self.btn_play.pack(side=tk.LEFT, padx=2, pady=2)

        self.btn_skip = tk.Button(self, text=u">>", command=self.on_skip_clicked)
        self.btn_skip.pack(side=tk.LEFT, padx=2, pady=2)

        self.btn_rocks = tk.Button(self, text=u"rocks", command=self.on_rocks_clicked)
        self.btn_rocks.pack(side=tk.LEFT, padx=2, pady=2)

        self.btn_sucks = tk.Button(self, text=u"sucks", command=self.on_sucks_clicked)
        self.btn_sucks.pack(side=tk.LEFT, padx=2, pady=2)

        self.name = tk.Label(self, text='Updating, please wait...')
        self.name.pack(side=tk.LEFT, padx=2, pady=2)

        self.update_buttons()
        self.pack(side=tk.TOP, fill=tk.X)

    def update_buttons(self):
        """Updates button states.

        Changes the play/pause button text, enables/disables the skip button
        when not playing.
        """
        if self.audio.is_playing():
            self.btn_play.config(text='||')
            self.btn_skip.config(state=tk.NORMAL)
        else:
            self.btn_play.config(text='>')
            self.btn_skip.config(state=tk.DISABLED)

        jabber_state = tk.DISABLED
        if self.jabber is not None:
            jabber_state = tk.NORMAL
        self.btn_rocks.config(state=jabber_state)
        self.btn_sucks.config(state=jabber_state)

        vote = self.track_info.get('vote')
        if vote == 1:
            self.btn_rocks.config(default=tk.ACTIVE)
            self.btn_sucks.config(default=tk.NORMAL)
        elif vote == -1:
            self.btn_rocks.config(default=tk.NORMAL)
            self.btn_sucks.config(default=tk.ACTIVE)

        if self.jabber is not None and self.track_info.get('editable'):
            self.btn_skip.config(state=tk.NORMAL)
        else:
            self.btn_skip.config(state=tk.DISABLED)

    def set_track_info(self, ti):
        text = u'%s — %s ♺%u ⚖%.2f' % (ti.get('artist', 'unknown artist'), ti.get('title', 'untitled'), ti.get('count', 0), ti.get('weight', 1))
        self.name.config(text=text)
        print 'New track info:', self.track_info
        self.track_info = ti
        self.update_buttons()

    def on_click(self, cmd, *args, **kwargs):
        callback = getattr(self, cmd)
        if not callback:
            print 'WARNING: toolbar.%s not set.' % cmd
        else:
            callback()

    def on_play_clicked(self):
        if self.audio.can_play():
            if self.audio.is_playing():
                self.audio.stop()
            else:
                self.audio.play()
            self.update_buttons()

    def on_skip_clicked(self):
        self.jabber.skip_track(self.track_info.get('id'))

    def on_rocks_clicked(self):
        self.jabber.send_rocks(self.track_info.get('id'))

    def on_sucks_clicked(self):
        self.jabber.send_sucks(self.track_info.get('id'))


class ChatEntry(tk.Entry):
    """A basic text entry with a callback to process the entered message.
    
    The messages is passed to the callback function which should be put in the
    on_message instance property, e.g.:

        entry = ChatEntry(self)
        entry.on_message = lambda txt: xyz(txt)
    """
    def __init__(self, master, **kwargs):
        """Initializes the control."""
        tk.Entry.__init__(self, state='readonly', highlightthickness=0, **kwargs)
        self.bind('<Return>', self.on_enter)
        self.on_message = None

    def on_enter(self, event):
        if self.on_message:
            self.on_message(self.get())
        self.delete(0, tk.END)

    def enable(self):
        self.config(state=tk.NORMAL)

    def disable(self):
        self.config(state='readonly')


class MainWindow(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)

        self.jabber = None
        self.audio = tmradio.audio.Open()

        self.toolbar = Toolbar(self, audio=self.audio)

        self.entry = ChatEntry(self)
        self.entry.pack(side=tk.BOTTOM, fill=tk.X)

        self.panes = tk.PanedWindow(self, orient=tk.HORIZONTAL, bd=4)
        self.panes.pack(fill=tk.BOTH, expand=tk.YES)

        self.chat_view = ChatView(self.panes)
        self.chat_view.pack(expand=tk.YES, fill=tk.BOTH, side=tk.LEFT)
        self.panes.add(self.chat_view)

        self.nick_list = NickList(self.panes)
        self.nick_list.pack(expand=tk.YES, fill=tk.BOTH, side=tk.RIGHT, anchor=tk.E, ipady=4)
        self.panes.add(self.nick_list)

        """
        self.status = tk.Label(self, text='This is a status bar.', bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        """

        self.after(100, self.on_idle)
        self.title('TMRadio Client')
        self.setup_real()

    def setup_real(self):
        """Connects the UI to the jabber client."""
        self.jabber = tmradio.jabber.Open()
        self.toolbar.jabber = self.jabber

        self.jabber.on_chat_message = self.on_chat_message
        self.jabber.on_disconnected = self.on_disconnected
        self.jabber.on_self_joined = self.on_self_joined
        self.jabber.on_self_parted = self.on_self_parted
        self.jabber.on_user_joined = self.on_user_joined
        self.jabber.on_user_parted = self.on_user_parted
        self.jabber.on_track_info = self.on_track_info

        self.entry.on_message = self.jabber.send_chat_message

    def setup_test(self):
        """Fills the windows with test data.  Can be used for safe debugging
        without bothering real users in the chat room."""
        for nick in ('hakimovis', 'dugwin', u'Хасан Атаман', 'umonkey'):
            self.on_user_joined(nick)

        self.chat_view.add_message(u'и пока не нашел как сделать обновление рейтинга песни после голосования', 'hakimovis (1983)')
        self.chat_view.add_message(u'привет, кстати, кого не видел)', 'hakimovis (1983)')
        self.chat_view.add_message(u'ура ага', 'dugwin')
        self.chat_view.add_message(u'кто первый придумал "доброе утро, страна"?', 'hakimovis (1983)')
        self.chat_view.add_message(u'мне кажется цекало', 'dugwin')
        self.chat_view.add_message(u'раскручивал по крайней мере', 'dugwin')

    def on_idle(self):
        """Runs backgound tasks, such as polling the Jabber, restarting the
        audio, updating toolbar buttons etc."""
        self.toolbar.update_buttons()
        if self.jabber:
            self.jabber.on_idle()
        self.audio.on_idle()
        self.after(100, self.on_idle)

    def on_user_joined(self, nickname):
        self.nick_list.add(nickname)

    def on_user_parted(self, nickname):
        self.nick_list.remove(nickname)

    def on_self_joined(self):
        self.entry.enable()

    def on_self_parted(self):
        self.entry.disable()

    def on_chat_message(self, text, nick):
        self.chat_view.add_message(text, nick)

    def on_disconnected(self):
        pass

    def on_track_info(self, ti):
        self.title('TMRadio Client (%u listeners)' % ti.get('listeners', 0))
        self.toolbar.set_track_info(ti)

    def show(self):
        tk.mainloop()

def Run():
    MainWindow().show()
