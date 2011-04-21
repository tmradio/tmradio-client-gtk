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

        self.ctl = factory(self)
        self.ctl.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        self.scrollbar = tk.Scrollbar(self, command=self.ctl.yview)
        self.ctl['yscrollcommand'] = self.scrollbar.set
        self.scrollbar.pack(side=tk.LEFT, fill=tk.Y)


class NickList(VScrollControl):
    """The list of nicknames.

    Supports vertical scrolling, clicking and double clicking (which should add
    nicknames to the entry box, using callbacks).
    """
    def __init__(self, master):
        """Initializes with no data."""
        VScrollControl.__init__(self, master, lambda p: tk.Listbox(p, bd=2))

        #self.ctl.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)
        #self.ctl.bind('<ButtonRelease-1>', self.on_click)
        #self.ctl.bind('<Double-Button-1>', self.on_double_click)

        self.data = []

    def add(self, nickname):
        """Adds a nickname to the end of the list.

        TODO: sort alphabetically.
        """
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
        self.on_skip = None
        self.on_rocks = None
        self.on_sucks = None

        self.btn_play = tk.Button(self, text=">", command=self.on_play)
        self.btn_play.pack(side=tk.LEFT, padx=2, pady=2)

        self.btn_next = tk.Button(self, text=u">>", command=self.update_buttons)
        self.btn_next.pack(side=tk.LEFT, padx=2, pady=2)

        b = tk.Button(self, text=u"rocks", command=lambda: self.on_click('on_rocks'))
        b.pack(side=tk.LEFT, padx=2, pady=2)

        b = tk.Button(self, text=u"sucks", command=lambda: self.on_click('on_sucks'))
        b.pack(side=tk.LEFT, padx=2, pady=2)

        self.update_buttons()
        self.pack(side=tk.TOP, fill=tk.X)

    def update_buttons(self):
        """Updates button states.

        Changes the play/pause button text, enables/disables the skip button
        when not playing.
        """
        if self.audio.is_playing():
            self.btn_play.config(text='||')
            self.btn_next.config(state=tk.NORMAL)
        else:
            self.btn_play.config(text='>')
            self.btn_next.config(state=tk.DISABLED)

    def on_click(self, cmd, *args, **kwargs):
        callback = getattr(self, cmd)
        if not callback:
            print 'WARNING: toolbar.%s not set.' % cmd
        else:
            callback()

    def on_play(self):
        if self.audio.can_play():
            if self.audio.is_playing():
                self.audio.stop()
            else:
                self.audio.play()
            self.update_buttons()


class ChatEntry(tk.Entry):
    """A basic text entry with a callback to process the entered message.
    
    The messages is passed to the callback function which should be put in the
    on_message instance property, e.g.:

        entry = ChatEntry(self)
        entry.on_message = lambda txt: xyz(txt)
    """
    def __init__(self, master):
        """Initializes the control."""
        tk.Entry.__init__(self)
        self.bind('<Return>', self.on_enter)
        self.on_message = None

    def on_enter(self, event):
        if self.on_message:
            self.on_message(self.get())
        self.delete(0, tk.END)


class MainWindow(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)

        self.jabber = None
        self.audio = tmradio.audio.Open()

        self.toolbar = Toolbar(self, audio=self.audio)

        self.chat = tk.Frame(self)
        self.chat.pack(expand=tk.YES)

        self.chat_view = ChatView(self.chat)
        self.chat_view.pack(expand=tk.YES, fill=tk.BOTH, side=tk.LEFT)

        self.nick_list = NickList(self.chat)
        self.nick_list.pack(expand=tk.YES, fill=tk.Y, side=tk.RIGHT, anchor=tk.E, ipady=4)

        self.entry = ChatEntry(self)
        self.entry.pack(side=tk.BOTTOM, fill=tk.X)

        self.after(100, self.on_idle)
        self.title('TMRadio Client')
        self.setup_real()

    def setup_real(self):
        self.jabber = tmradio.jabber.Open()
        self.jabber.on_chat_message = self.on_chat_message
        self.jabber.on_disconnected = self.on_disconnected
        self.jabber.on_self_joined = self.on_self_joined
        self.jabber.on_self_parted = self.on_self_parted
        self.jabber.on_user_joined = self.on_user_joined
        self.jabber.on_user_parted = self.on_user_parted
        self.jabber.connect()

        self.entry.on_message = self.jabber.send_chat_message

        #self.jabber.add_event('chat-join', self.on_user_joined) # somebody came in
        #self.jabber.add_event('chat-part', self.on_chat_part) # somebody left

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
        pass

    def on_self_parted(self):
        pass

    def on_chat_message(self, text, nick):
        self.chat_view.add_message(text, nick)

    def on_disconnected(self):
        pass

    def show(self):
        tk.mainloop()

def Run(version):
    MainWindow().show()
