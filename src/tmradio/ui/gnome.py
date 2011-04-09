# vim: set fileencoding=utf-8:

import datetime
import os
import re
import time
import urllib
import webbrowser

import gobject
import gtk
import pango
import pygtk

import tmradio.audio
import tmradio.config
import tmradio.feed
import tmradio.jabber
import tmradio.log

try:
    import pynotify
    HAVE_NOTIFY = True
except:
    HAVE_NOTIFY = False

USE_THREADING = False

# Global kill switch.
shutting_down = False

def is_url(text):
    parts = text.split(':')
    if not parts[0] in ('http', 'https', 'ftp', 'mailto'):
        return False
    if parts[0] == 'mailto':
        return '@' in parts[1]
    return parts[1].startswith('//')


class BaseWindow(object):
    """Base class for all windows.

    Loads UI definition from data/ui/CLASS_NAME.ui, finds a top-level window
    named as that class and creates an instance.
    """
    def __init__(self):
        self.builder = self._get_builder(self.__class__.__name__)
        self.window = self.builder.get_object(self.__class__.__name__)
        self.builder.connect_signals(self)

    def _get_builder(self, name):
        builder = gtk.Builder()
        dirs = [
            '/usr/share/tmradio-client',
            '/usr/local/share/tmradio-client', os.path.dirname(__file__),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data'),
            ]
        for dirname in dirs:
            test_file = os.path.join(dirname, 'MainWindow.ui')
            if os.path.exists(test_file):
                builder.add_from_file(os.path.join(dirname, name + '.ui'))
                return builder
        raise Exception('Could not locate UI files.')


class MessageTextView(gtk.TextView):
    def __init__(self, parent, collapse_nicknames=False, **kwargs):
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
        parent.get_vadjustment().connect('value-changed', self.on_va_changed)
        parent.get_vadjustment().connect("changed", self.on_va_changed2)

        self.setup_tags()
        parent.add_with_viewport(self)
        self.show_all()

    def get_highlight_re(self):
        config = tmradio.config.Open()

        expr = config.get('highlight_re')
        if expr is None:
            expr = config.get_jabber_id() + u'|' + config.get_jabber_chat_nick()

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
            if is_url(word):
                # http://www.mail-archive.com/pygtk@daa.com.au/msg18007.html
                t = tb.create_tag()
                t.set_property('foreground', 'blue')
                t.set_property('underline', pango.UNDERLINE_SINGLE)
                t.connect('event', self.on_link_event, word)
                tb.insert_with_tags(eob, word, t)
                self.url_tags.append(t)
            elif self.highlight_re.search(word) is not None:
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

        if not notifyUser and self.highlight_re.search(text):
            notifyUser = True

        if notifyUser:
            n = pynotify.Notification(u'Чат ТМ-Радио', u'You were mentioned in the chat!', 'audio-volume-medium')
            n.set_urgency(pynotify.URGENCY_LOW)
            n.show()
            
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


MessageView = MessageTextView


class PodcastView(gtk.TreeView):
    def __init__(self, parent):
        gtk.TreeView.__init__(self)
        self._parent = parent
        self.episode_links = []
        self.model = gtk.ListStore(str, str, str, str, str, str) # date, title, size, page_link, file_link, ts
        self.setup()
        self.show_all()

    def setup(self):
        self.set_model(self.model)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Time', cell, text=0, resizable=True)
        col.set_property('resizable', True)
        self.append_column(col)

        cell = gtk.CellRendererText()
        cell.props.xalign = 0.0
        cell.props.ellipsize = pango.ELLIPSIZE_END
        col = gtk.TreeViewColumn('Title', cell, text=1)
        col.set_property('expand', True)
        col.set_property('resizable', True)
        col.set_property('sizing', gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.append_column(col)

        cell = gtk.CellRendererText()
        cell.props.xalign = 1.0
        col = gtk.TreeViewColumn('Size', cell, text=2, expand=False)
        col.set_property('resizable', True)
        self.append_column(col)

        self.connect('button-press-event', self.on_row_clicked)
        self._parent.add_with_viewport(self)

        self.model.set_sort_func(0, lambda model, iter1, iter2: cmp(model.get_value(iter1, 5), model.get_value(iter2, 5)))
        self.model.set_sort_column_id(0, gtk.SORT_DESCENDING)

    def add(self, date, title, link, audio_link, audio_size):
        if link not in self.episode_links:
            date_txt = time.strftime('%d.%m %H:%M', date)
            size_txt = u'%.1fM' % (audio_size / 1048576)

            model = self.get_model()
            row_iter = model.append([date_txt, title, size_txt, link, audio_link, time.strftime('%Y%m%d%H%M%S', date)])
            self.episode_links.append(link)
            # path = model.get_path(row_iter)
            # self.scroll_to_cell(path)

    def on_row_clicked(self, tv, event):
        path, column, rx, ry = tv.get_path_at_pos(int(event.x), int(event.y)) or (None,) * 4
        if path is not None:
            selection = tv.get_selection()
            model, paths = selection.get_selected_rows()

            page_link = model.get_value(model.get_iter(path), 3)
            file_link = model.get_value(model.get_iter(path), 4)

            if event.button == 3:
                menu = gtk.Menu()

                if page_link:
                    item = gtk.MenuItem('Open episode page')
                    item.connect('activate', lambda item: webbrowser.open(page_link))
                    menu.append(item)

                if file_link:
                    item = gtk.MenuItem('Download episode')
                    item.connect('activate', lambda item: webbrowser.open(file_link))
                    menu.append(item)

                menu.show_all()
                menu.popup(None, None, None, event.button, event.time)

            elif event.type == gtk.gdk._2BUTTON_PRESS:
                webbrowser.open(page_link)

    def on_column_resize(self, *args):
        tmradio.log.debug('on_column_resize(%s)' % args)


class MainWindow(BaseWindow):
    def __init__(self, version):
        super(MainWindow, self).__init__()
        self.version = version
        self.config = tmradio.config.Open()
        self.jabber = tmradio.jabber.Open(self, use_threading=USE_THREADING, version=self.version)
        self.twitter = tmradio.feed.Twitter(self.config)
        self.podcast = tmradio.feed.Podcast(self.config)
        self.is_in_chat = False
        self.is_online = False # the bot is available
        self.is_visible = False
        # Track properties.
        self.track_id = None
        self.track_artist = None
        self.track_title = None
        self.track_labels = None
        self.track_labels_original = None # for editing
        self.track_length = None
        self.track_change_ts = None
        self.track_vote = 0
        self.track_link = None
        self.track_editable = False
        # Other windows.
        self.pref_window = None
        # Suppress duplicate nicknames in the chat window.
        self.last_chat_nick = None
        # Initialize the player.
        self.player = tmradio.audio.Open(on_track_change=self.on_stream_track_change, config=self.config, version=self.version, on_start=self.update_play_button, on_stop=self.update_play_button)
        self.builder.get_object('volume').set_value(self.player.get_volume())
        # RegExp for parsing stream title.
        self.stream_title_re = re.compile('"([^"]+)" by (.+)')

        self.window.connect('window-state-event', self.on_window_state)

        self.init_tabs()
        gobject.timeout_add(30, self.on_idle)

        settings = gtk.settings_get_default()
        settings.props.gtk_button_images = True

        self.twitter.start()
        self.podcast.start()
        self._jabber_autoconnect()

    def on_window_state(self, window, event):
        mask = gtk.gdk.WINDOW_STATE_ICONIFIED | gtk.gdk.WINDOW_STATE_WITHDRAWN
        self.is_visible = not (event.new_window_state & mask)

    def init_tabs(self):
        self.chat_tab = MessageView(self.builder.get_object('chatscroll'), collapse_nicknames=True, jid=self.config.get_jabber_id(), nick=self.config.get_jabber_chat_nick())
        self.twit_tab = MessageView(self.builder.get_object('twitscroll'))
        self.cast_tab = PodcastView(self.builder.get_object('podscroll'))
        self.init_nicklist()

    def init_nicklist(self):
        tv = self.builder.get_object('userlist')
        tm = tv.get_model()

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Nickname')
        col.pack_start(cell, True)
        col.add_attribute(cell, 'text', 0)
        col.set_sort_column_id(0)
        tv.append_column(col)

        tm.set_sort_func(0, lambda model, iter1, iter2: cmp(model.get_value(iter1, 0).lower(), model.get_value(iter2, 0).lower()))
        tm.set_sort_column_id(0, gtk.SORT_ASCENDING)

    def _jabber_autoconnect(self):
        """Connects to the jabber server if parameters are OK."""
        if self.config.get_jabber_id() and self.config.get_jabber_password():
            self.jabber.post_message('connect', special=True)
        else:
            self.on_menu_preferences_activate()

    def on_delete(self, *args):
        """Handle the main window's close button."""
        self.on_menu_quit_activate(None)

    def on_MainWindow_destroy(self, widget, data=None):
        self.jabber.post_message('quit', special=True)
        # gtk.main_quit()

    def on_play_clicked(self, widget, data=None):
        if self.player.is_playing():
            self.stop_playing()
        else:
            self.start_playing()

    def stop_playing(self):
        self.player.stop()
        self.update_play_button()

    def start_playing(self):
        volume = self.builder.get_object('volume').get_value()
        self.player.play(self.config.get_stream_uri(), volume=volume or 0.5)
        self.update_play_button()

    def set_track_info(self, artist, title, track_id, count, weight, tags, full_update):
        self.builder.get_object('track_artist').set_text(artist)
        self.builder.get_object('track_title').set_text(title)
        self.builder.get_object('track_labels').set_text(u' '.join(tags))
        if HAVE_NOTIFY and full_update and not self.is_visible:
            message = u'"%s" by %s' % (title, artist)
            if self.track_vote > 0:
                message += u'. You LOVE it.'
            elif self.track_vote < 0:
                message += u'. You HATE it.'
            tmradio.log.debug(u'Notification: ' + message)
            n = pynotify.Notification(self.window.get_title(), message, 'audio-volume-medium')
            n.set_urgency(pynotify.URGENCY_LOW)
            n.show()

    def on_stream_track_change(self, title):
        tmradio.log.debug('Stream title changed.')
        m = self.stream_title_re.search(title)
        if m:
            tmradio.log.debug('%s' % m.groups())

    def set_track_id(self, track_id):
        self.track_id = track_id

    def clear_chat(self):
        self.chat_tab.clear()

    def add_chat(self, text, nick=None, time=None, offline=False):
        if text and text.strip():
            nick = nick or u'Robot'
            if not offline:
                tmradio.log.chat(nick + u': ' + text)
            self.chat_tab.add_message(time=time, nick=nick, message=text)

    def on_idle(self):
        """Update controls, process xmpp messages.""" 
        self._process_jabber_replies()
        self._update_progress_bar()
        if not USE_THREADING:
            self.jabber.process_queue()
        self.player.on_idle()
        self._update_twitter()
        self._update_podcast()
        return True

    def _update_progress_bar(self):
        if self.track_change_ts and self.track_length:
            spent = float(min(int(time.time()) - self.track_change_ts, self.track_length))
            fraction = spent / float(self.track_length)
        else:
            fraction = 0
        pb = self.builder.get_object('progress')
        if pb.get_fraction() != fraction:
            pb.set_fraction(fraction)

    def _is_online(self):
        return self.jabber and self.jabber.is_connected() and self.is_online

    def update_controls(self):
        """Disables and enables controls on conditions."""
        connected = self.jabber.is_connected()
        self.update_buttons()

        img = self.builder.get_object('chatbtn').get_image()
        img.set_from_stock(self.is_in_chat and gtk.STOCK_DISCONNECT or gtk.STOCK_CONNECT, gtk.ICON_SIZE_BUTTON)
        self.builder.get_object('chatbtn').set_sensitive(connected)
        self.builder.get_object('chatmsg').set_sensitive(self.is_in_chat and 1 or 0)

        self.update_play_button()

        for ctl_name in ('skip', 'track_artist', 'track_title', 'track_labels', 'update'):
            self.builder.get_object(ctl_name).set_sensitive(self.track_editable and connected and self.is_online)

    def update_play_button(self):
        ctl = self.builder.get_object('play')
        ctl.get_image().set_from_stock(self.player.is_playing() and 'gtk-media-stop' or 'gtk-media-play', gtk.ICON_SIZE_BUTTON)
        ctl.set_sensitive(self.player.can_play())

        ctl = self.builder.get_object('volume')
        ctl.set_value(self.player.get_volume())

    def _process_jabber_replies(self):
        """Process the incoming jabber message queue."""
        update_track_info = False
        update_controls = False
        full_update = False
        for replies in self.jabber.fetch_replies():
            if type(replies) != list:
                replies = [replies]
            for reply in replies:
                update_controls = True
                if reply[0] == 'set':
                    self.is_online = True
                    if self._process_jabber_property(reply):
                        full_update = True
                    update_track_info = True
                elif reply[0] == 'offline':
                    self.is_online = False
                elif reply[0] == 'chat':
                    self.is_online = True
                    tmradio.log.debug(reply)
                    offline = len(reply) > 3 and reply[3]
                    timestamp = offline and reply[3] or time.time()
                    self.add_chat(reply[1], reply[2], timestamp, offline)
                elif reply[0] == 'joined':
                    self.is_online = True
                    self.is_in_chat = True
                elif reply[0] == 'left':
                    self.is_in_chat = False
                    self.chat_tab.clear()
                elif reply[0] == 'disconnected':
                    self.track_vote = 0
                elif reply[0] == 'join':
                    self.is_online = True
                    self._add_chat_user(reply[1], True)
                elif reply[0] == 'part':
                    self.is_online = True
                    self._add_chat_user(reply[1], False)
                elif reply[0] == 'auth-error':
                    self.on_menu_preferences_activate()
                else:
                    tmradio.log.info(u'Unhandled jabber reply: %s' % reply)
        if update_track_info:
            self.set_track_info(self.track_artist, self.track_title, self.track_id, 0, 0, self.track_labels, full_update)
            self.twitter.update()
            self.podcast.update()
        if update_controls:
            self.update_controls()

    def _update_twitter(self):
        items = self.twitter.get_records()
        if items:
            self.twit_tab.clear()
            for item in items:
                if '@' in item['author']:
                    author = item['author'].split(' ', 1)[1].strip('()')
                else:
                    author = item['author'].split(' ')[0]
                self.twit_tab.add_message(time=item['timestamp'], nick=author, message=item['title'], nicklink=item['link'])

    def _update_podcast(self):
        items = self.podcast.get_records()
        if items:
            # self.twit_tab.clear()
            for item in items:
                if item.has_key('enclosures'):
                    audio_link = None
                    audio_size = None
                    for enc in item['enclosures']:
                        if enc.has_key('type') and enc['type'].startswith('audio/'):
                            audio_link = enc['href']
                            audio_size = enc.has_key('length') and int(enc['length']) or 1024
                    self.cast_tab.add(item['updated_parsed'], item['title'], item['link'], audio_link, audio_size)

    def _process_jabber_property(self, reply):
        key, value = reply[1:]
        if key == 'track_id':
            new_id = int(value)
            if new_id != self.track_id:
                # We use track chage time to display the progress bar, so it
                # needs to be precise.  If it's the first track info we get, it
                # most likely is mid-play, we're not interested.
                if self.track_id is not None:
                    self.track_change_ts = int(time.time())
                self.track_id = new_id
                self.track_vote = 0
        elif key == 'track_artist':
            self.track_artist = value
        elif key == 'track_title':
            self.track_title = value
        elif key == 'track_labels':
            self.track_labels = value
            self.track_labels_original = value
        elif key == 'track_length':
            self.track_length = int(value)
        elif key == 'track_started_on':
            if not self.track_change_ts and str(value).isdigit():
                self.track_change_ts = int(value)
        elif key == 'track_vote':
            self.track_vote = value and int(value) or 0
            return True
        elif key == 'track_editable':
            self.track_editable = value
        elif key == 'track_listeners':
            title = 'tmradio.net (%u)' % value
            self.window.set_title(title)
            self.builder.get_object('tray').set_tooltip(title)
        elif key == 'track_weight':
            self.track_weight = value
        elif key == 'track_playcount':
            pass
        else:
            tmradio.log.debug(u'Unhandled property: ' + str(reply))

        if key in ('track_title', 'track_artist', 'track_length'):
            text = u'%s — %s' % (self.track_artist, self.track_title)
            if self.track_length:
                text += u' [%u:%02u]' % (self.track_length / 60, self.track_length % 60)
                text += u' ⚖%s' % self.track_weight
            self.builder.get_object('progress').set_text(text)

    def _add_chat_user(self, name, joined=True):
        model = self.builder.get_object('nicklist')
        for iter in model:
            if iter[0] == name:
                model.remove(iter.iter)
        if joined:
            model.append([name])

    def on_rocks_toggled(self, button):
        return self.change_track_vote(button, 1)

    def on_sucks_toggled(self, button):
        return self.change_track_vote(button, -1)

    def change_track_vote(self, button, vote):
        """Changes the current track vote and updates the buttons.

        The vote is only changed is the button is pressed, not unpressed (the
        TriggerButton widget reports a toggle event even when the state is
        changed programmatically, tricks are used to detect the real
        situation)."""
        if button.get_active() and self.track_id and self.is_online:
            if self.track_vote != vote:
                self.track_vote = vote
                cmd = vote > 0 and 'rocks' or 'sucks'
                self.jabber.post_message('%u %s' % (self.track_id, cmd))
        self.update_buttons()

    def update_buttons(self):
        """Updates the rocks/sucks button states according to the current vote.

        If the bot is offline, buttons are unpressed and disabled, otherwise
        they're set according to the vote."""
        rocks = self.builder.get_object('rocks')
        sucks = self.builder.get_object('sucks')

        if self.is_online and self.track_id:
            rocks.set_active(self.track_vote > 0)
            sucks.set_active(self.track_vote < 0)

            rocks.set_sensitive(self.track_vote <= 0)
            sucks.set_sensitive(self.track_vote >= 0)
        else:
            rocks.set_active(False)
            rocks.set_sensitive(False)
            sucks.set_active(False)
            sucks.set_sensitive(False)

        self.builder.get_object('play').set_sensitive(self.player.can_play())

    def on_chatmsg_activate(self, field):
        if self.jabber:
            text = field.get_text()
            chat = not text.startswith('/')
            if not chat:
                text = text[1:]
            field.set_text('')
            self.jabber.post_message(text, chat=chat)

    def on_update_clicked(self, button):
        if not self.jabber:
            return # TODO: error message or else.
        fmap = { 'track_artist': 'set artist to %s for %u', 'track_title': 'set title to %s for %u', 'track_labels': 'tags %s for %u' }
        for key in fmap.keys():
            value = self.builder.get_object(key).get_text()
            if key == 'track_labels':
                current = value.split(' ')
                value = []
                for l in [x for x in current if x not in self.track_labels_original]:
                    value.append(l)
                for l in [x for x in self.track_labels_original if x not in current]:
                    value.append(u'-' + l)
                value = u' '.join(value)
            if value:
                self.jabber.post_message(fmap[key] % (value, self.track_id))
        self.jabber.post_message('show ' + str(self.track_id))

    def on_chatbtn_clicked(self, *args):
        if self.is_in_chat:
            self.jabber.post_message('leave', special=True)
        else:
            self.jabber.post_message('join', special=True)

    def on_skip_clicked(self, button):
        self.jabber.post_message('skip')

    def on_info_clicked(self, *args):
        webbrowser.open('http://www.last.fm/music/%s' % urllib.quote(self.track_artist.encode('utf-8')))

    def on_volume_changed(self, widget, level):
        self.player.set_volume(level)
        self.update_play_button()

    def on_tray_activate(self, *args):
        if self.window.get_visible():
            self.window.hide()
        else:
            self.window.show()

    def on_tray_scroll(self, icon, event):
        delta = 0.1
        if event.direction == gtk.gdk.SCROLL_DOWN:
            delta = -0.1
        volume = self.builder.get_object('volume')
        value = min(max(volume.get_value() + delta, 0.0), 1.0)
        volume.set_value(value)

    def on_tray_menu(self, icon, *args):
        self.builder.get_object('tray_menu').popup(None, None, None, 3, 0)

    def on_tray_show(self, *args):
        self.on_tray_activate()

    def on_menu_preferences_activate(self, item=None):
        if not self.pref_window:
            self.pref_window = Preferences(self)
        self.pref_window.window.show()

    def on_menu_quit_activate(self, item):
        global shutting_down
        shutting_down = True
        self.twitter.shutting_down = True
        self.podcast.shutting_down = True
        gtk.main_quit()

    def on_menu_about_activate(self, *args):
        webbrowser.open('http://app.tmradio.net/')

    def on_menu_website_activate(self, *args):
        webbrowser.open('http://www.tmradio.net/')

    def on_menu_bugs_activate(self, *args):
        webbrowser.open('https://github.com/tmradio/tmradio-client-gtk/issues')

    def on_chat_entered(self):
        self.builder.get_object('chatmsg').grab_focus()

    def on_chat_left(self):
        self.clear_chat()


class Preferences(BaseWindow):
    def __init__(self, main):
        super(self.__class__, self).__init__()
        self.main = main
        self.config = main.config

    def on_delete(self, *args):
        self.window.hide()
        self.save()
        return True

    def on_show(self, *args):
        self.load()

    def on_close_clicked(self, *args):
        self.on_delete(*args)

    def load(self):
        """Fills form fields with config options."""
        for fn in [fn for fn in dir(self.config) if fn.startswith('get_')]:
            ctl = self.builder.get_object(fn[4:])
            if ctl:
                ctl.set_text(getattr(self.config, fn)() or '')

    def save(self):
        for fn in [fn for fn in dir(self.config) if fn.startswith('set_')]:
            ctl = self.builder.get_object(fn[4:])
            if ctl:
                getattr(self.config, fn)(ctl.get_text())
        self.config.save()
        self.main.jabber.post_message('connect', special=True)

def Run(version):
    gobject.threads_init()
    app = MainWindow(version)
    app.window.show()
    if app.pref_window:
        app.pref_window.window.present()
    gtk.main()
