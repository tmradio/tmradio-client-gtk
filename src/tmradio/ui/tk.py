# encoding=utf-8

"""Tk interface for the tmradio client.

TODO:
- Set width of the nick list.
"""

import time

import tkFont
import Tkinter as tk

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


class MainWindow():
    def __init__(self):
        self.tk = tk.Tk()

        self.chat_view = ChatView(self.tk)
        self.chat_view.pack(expand=tk.YES, fill=tk.BOTH, side=tk.LEFT)

        self.nick_list = NickList(self.tk)
        self.nick_list.pack(expand=tk.YES, fill=tk.Y, side=tk.RIGHT, anchor=tk.E, ipady=4)

        self.jabber = None
        #self.jabber.add_event('chat-join', self.on_chat_join) # somebody came in
        #self.jabber.add_event('chat-part', self.on_chat_part) # somebody left

        self.tk.title('TMRadio Client')
        self.add_test_data()

    def add_test_data(self):
        for nick in ('hakimovis', 'dugwin', u'Хасан Атаман', 'umonkey'):
            self.on_chat_join(nick)

        self.chat_view.add_message(u'и пока не нашел как сделать обновление рейтинга песни после голосования', 'hakimovis (1983)')
        self.chat_view.add_message(u'привет, кстати, кого не видел)', 'hakimovis (1983)')
        self.chat_view.add_message(u'ура ага', 'dugwin')
        self.chat_view.add_message(u'кто первый придумал "доброе утро, страна"?', 'hakimovis (1983)')
        self.chat_view.add_message(u'мне кажется цекало', 'dugwin')
        self.chat_view.add_message(u'раскручивал по крайней мере', 'dugwin')

    def on_chat_join(self, nickname):
        self.nick_list.add(nickname)

    def show(self):
        tk.mainloop()

def Run(version):
    MainWindow().show()
