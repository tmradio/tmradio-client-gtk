import time
import datetime
import re
import webbrowser

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

import tmradio.config


class Toolbar(gtk.HBox):
    def __init__(self):
        gtk.HBox.__init__(self, False, 0)

        self.btn_play = gtk.Button('Play')
        self.pack_start(self.btn_play, expand=False)

        self.btn_rocks = gtk.Button('Rocks')
        self.pack_start(self.btn_rocks, expand=False)

        self.btn_sucks = gtk.Button('Sucks')
        self.pack_start(self.btn_sucks, expand=False)

        self.progress_bar = gtk.ProgressBar()
        self.pack_start(self.progress_bar, expand=True, fill=True)

        self.btn_info = gtk.Button('Last.fm')
        self.pack_start(self.btn_info, expand=False)

        self.btn_volume = gtk.VolumeButton()
        self.pack_start(self.btn_volume, expand=False)


class NickListControl(gtk.TreeView):
    def __init__(self):
        gtk.TreeView.__init__(self)

        self.nl_store = gtk.ListStore(gobject.TYPE_STRING)
        self.set_model(self.nl_store)

        self.nl_column = gtk.TreeViewColumn('Nickname')
        self.nl_column.set_sort_column_id(0)
        self.append_column(self.nl_column)

        self.nl_cell = gtk.CellRendererText()
        self.nl_column.pack_start(self.nl_cell, True)
        self.nl_column.add_attribute(self.nl_cell, 'text', 0)

        self.add_nick('hello')
        self.add_nick('world')

    def add_nick(self, nickname):
        self.nl_store.append([ nickname ])


class MessageTextView(gtk.TextView):
    def __init__(self, scroll_window=None, collapse_nicknames=False, **kwargs):
        gtk.TextView.__init__(self)
       
        self.highlight_re = self.get_highlight_re()
        
        self.url_tags = []
        self.set_property('pixels-above-lines', 4)
        self.set_property('wrap-mode', gtk.WRAP_WORD)
        self.set_property('indent', -20)
        self.set_property('can-focus', False)
        self.set_property('editable', False)
        self.connect('motion_notify_event', self.on_mouse_motion)

        # Scroll to last line.
        # http://www.daa.com.au/pipermail/pygtk/2009-January/016507.html
        if scroll_window:
            scroll_window.get_vadjustment().connect('value-changed', self.on_va_changed)
            scroll_window.get_vadjustment().connect("changed", self.on_va_changed2)
            scroll_window.add_with_viewport(self)

        self.setup_tags()

    def get_highlight_re(self):
        config = tmradio.config.Open()

        expr = config.get('highlight_re')
        if expr is None:
            try: expr = config.get_jabber_id() + u'|' + config.get_jabber_chat_nick()
            except: return None

        return re.compile(expr)

    def on_va_changed(self, vadjust):
        vadjust.need_scroll = abs(vadjust.value + vadjust.page_size - vadjust.upper) < vadjust.step_increment

    def on_va_changed2(self, vadjust):
        if not hasattr(vadjust, "need_scroll") or vadjust.need_scroll:
            vadjust.set_value(vadjust.upper-vadjust.page_size)
            vadjust.need_scroll = True

    def setup_tags(self):
        tt = self.get_buffer().get_tag_table()

        tag = gtk.TextTag('time')
        tag.set_property('foreground', 'gray')
        tt.add(tag)

        tag = gtk.TextTag('nick')
        tag.set_property('foreground', 'black')
        tag.set_property('weight', 800)
        tt.add(tag)

    def on_mouse_motion(self, widget, event, data=None):
        """Track mouse movement to change the cursor.
        
        http://www.daa.com.au/pipermail/pygtk/2004-December/009352.html
        """
        pointer = self.window.get_pointer()
        x, y, spam = self.window.get_pointer()
        x, y = self.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, x, y)
        tags = self.get_iter_at_location(x, y).get_tags()

        cursor = None
        for tag in tags:
            if tag in self.url_tags:
                cursor = gtk.gdk.Cursor(gtk.gdk.HAND2)
        self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(cursor)

        return False

    def on_link_event(self, tag, tv, event, iterator, link):
        link = link.rstrip(',.!?)')
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            menu = gtk.Menu()
            item = gtk.MenuItem('Open link')
            item.connect('activate', lambda item: webbrowser.open(link))
            menu.append(item)
            menu.show_all()
            menu.popup(None, None, None, event.button, event.time)
            return True
        elif event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
            webbrowser.open(link)
            return True
        return False

    def add_message(self, **_kwargs):
        kwargs = {'time': datetime.datetime.now(), 'nick': None, 'nicklink': None, 'message': '' }
        kwargs.update(_kwargs)

        ts = kwargs['time']
        nick = kwargs['nick']
        nicklink = kwargs['nicklink']
        text = kwargs['message'].strip()

        tb = self.get_buffer()
        sob, eob = tb.get_bounds()

        if tb.get_char_count():
            tb.insert(eob, '\n')

        tb.insert_with_tags_by_name(eob, time.strftime('%d.%m %H:%M ', time.localtime(ts)), 'time')
        self._add_nickname(tb, eob, kwargs)
        tb.insert(eob, ':')
        notifyUser = False
        for word in text.split(' '):
            tb.insert(eob, ' ')
            if self.is_url(word):
                # http://www.mail-archive.com/pygtk@daa.com.au/msg18007.html
                t = tb.create_tag()
                t.set_property('foreground', 'blue')
                t.set_property('underline', pango.UNDERLINE_SINGLE)
                t.connect('event', self.on_link_event, word)
                tb.insert_with_tags(eob, word, t)
                self.url_tags.append(t)
            elif self.highlight_re is not None and self.highlight_re.search(word) is not None:
                t = tb.create_tag()
                config = tmradio.config.Open()
                t.set_property('foreground', config.get('highlight_color', 'red'))
                bg = config.get('highlight_bgcolor', None)
                if bg is not None:
                    t.set_property('background', bg)
                tb.insert_with_tags(eob, word, t)
                notifyUser = True
            else:
                tb.insert(eob, word)

        if not notifyUser and self.highlight_re is not None and self.highlight_re.search(text):
            notifyUser = True

        if notifyUser:
            notify(u'You were mentioned in the chat!')

    def is_url(self, text):
        return False
            
    def _add_nickname(self, tb, eob, kwargs):
        t = tb.create_tag()
        t.set_property('weight', 800)
        if kwargs['nicklink']:
            t.set_property('underline', pango.UNDERLINE_SINGLE)
            t.connect('event', self.on_link_event, kwargs['nicklink'])
            self.url_tags.append(t)
        tb.insert_with_tags(eob, kwargs['nick'], t)

    def clear(self):
        self.url_tags = []
        tb = self.get_buffer()
        sob, eob = tb.get_bounds()
        tb.delete(sob, eob)


class ChatView(gtk.HPaned):
    def __init__(self):
        gtk.HPaned.__init__(self)

        self.text_scroll = gtk.ScrolledWindow()
        self.text_scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.text_pane = MessageTextView(scrolled_window=self.text_scroll)
        self.text_scroll.add(self.text_pane)
        self.add1(self.text_scroll)

        self.nick_list = NickListControl()
        self.add2(self.nick_list)

        self.connect('show', self.update_size)

    def update_size(self, *args, **kwargs):
        self.props.position = 600

    def add_message(self, **kwargs):
        self.text_pane.add_message(**kwargs)


class MainMenu(gtk.MenuBar):
    def __init__(self, on_exit=None):
        gtk.MenuBar.__init__(self)

        submenu = gtk.Menu()

        item = gtk.MenuItem('Preferences')
        item.connect('activate', self.on_preferences)
        submenu.append(item)

        item = gtk.MenuItem('Open Chat Log')
        item.connect('activate', self.on_chat_log)
        submenu.append(item)

        item = gtk.SeparatorMenuItem()
        submenu.append(item)

        item = gtk.MenuItem('Exit')
        if on_exit:
            item.connect('activate', on_exit)
        submenu.append(item)

        menu = gtk.MenuItem('Root Menu')
        menu.set_submenu(submenu)
        self.append(menu)

        submenu = gtk.Menu()

        item = gtk.MenuItem('Visit web site')
        submenu.append(item)

        item = gtk.MenuItem('Report bugs')
        submenu.append(item)

        item = gtk.MenuItem('About')
        submenu.append(item)

        menu = gtk.MenuItem('Help')
        menu.set_submenu(submenu)
        self.append(menu)

    def on_preferences(self, *args):
        pass

    def on_chat_log(self, *args):
        pass


class MainWindow:
    def __init__(self):
        self.setup_window()

    def setup_window(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title('TMRadio Client')
        self.window.connect('delete_event', self.on_quit)

        self.vbox = gtk.VBox(False, 2)
        self.window.add(self.vbox)

        self.vbox.pack_start(self.setup_menu(), expand=False, fill=True)
        self.vbox.pack_start(self.setup_toolbar(), expand=False, fill=True)
        self.vbox.pack_start(self.setup_chat_pane(), expand=True, fill=True)
        self.vbox.pack_start(self.setup_chat_entry(), expand=False, fill=True)

        self.window.resize(800, 380)

    def setup_chat_pane(self):
        self.chat_view = ChatView()
        for x in range(100):
            self.chat_view.add_message(nick='umonkey', message='hello, world. ' * 20, nicklink='http://www.example.com/', time=time.time())
        return self.chat_view

    def setup_chat_entry(self):
        self.msg = gtk.Entry()
        return self.msg

    def setup_menu(self):
        self.menu_bar = MainMenu(on_exit=lambda x: self.on_quit(None, None))
        return self.menu_bar

    def setup_toolbar(self):
        self.toolbar = Toolbar()
        return self.toolbar

    def run(self):
        self.window.show_all()
        gtk.main()

    def on_quit(self, widget, event, data=None):
        gtk.main_quit()
        return False

if __name__ == '__main__':
    MainWindow().run()
