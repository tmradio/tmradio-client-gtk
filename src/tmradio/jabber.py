# vim: set fileencoding=utf-8:

# Suppress hashlib warnings.
import warnings
warnings.filterwarnings("ignore")

import json
import os
import random
import re
import sys
import time
import urlparse
import xmpp
import Queue

import tmradio
import tmradio.log
import tmradio.config

class Jabber:
    """Simple jabber client.

    Understands some ardj replies and supports MUC.  All interfecence
    communication is serialized using incoming and outgoing queues, so it's
    thread safe.
    """

    PING_FREQUENCY = 60 # seconds
    PING_TIMEOUT = 5 # seconds

    def __init__(self):
        self.config = tmradio.config.Open()
        self.jid = None
        self.cli = None
        self.roster = None
        self.bot_jid = None
        self.chat_jid = None
        # Event handlers, should be reset externally.
        self.on_chat_message = None
        self.on_disconnected = None
        self.on_self_joined = None
        self.on_self_parted = None
        self.on_track_info = None
        self.on_user_joined = None
        self.on_user_parted = None
        # Outgoing commands, added via post_message().
        self.out_queue = Queue.Queue()
        # Incoming commands, accessible via get_messages().
        self.in_queue = Queue.Queue()
        # RegExp for parsing the status line
        self.np_re = re.compile(u'^«(.+)» by (.+) — #(\d+) ♺(\d+) ⚖(\S+) Σ(\d+)')
        # RegExp for parsing the SHOW command (extracts pro/con lists only).
        self.show_re = re.compile(u'.* #(\d+).*length=(\d+)s.*editable=(True|False).*last_played=(\d+).* Pro: (.+), contra: (.+)\.$')
        # Status.
        self.track_info = {}
        self.chat_active = False
        self.chat_my_name = None
        self.is_shutting_down = False
        self.reconnect_time = 0
        self.last_ping_ts = 0

        if self.config.get('use_threading', False):
            self.worker = threading.Thread()
            self.worker.run = self._thread_worker
            self.worker.start()

    def get_own_nickname(self):
        return self.chat_my_name

    def post_message(self, text, chat=False, special=False):
        """Send a message.

        The message is added to the outgoing queue and will be processed asap.
        If chat is set, the message is sent to the chat room.  If special is
        set, the message is treated as a command to the jabber client and must
        be one of: connect, disconnect, join, leave.
        """
        self.out_queue.put((text, chat, special))

    def connect(self):
        """Starts connecting to the server."""
        self.post_message('connect', special=True)

    def send_chat_message(self, message):
        """Sends a message to the chat room.  Messages prefixed with
        a slash are sent to the radio bot directly."""
        if message.startswith('/'):
            self.post_message(message[1:], False)
        else:
            self.post_message(message, True)

    def send_rocks(self, track_id):
        """Sends the bot a note that the user likes the specified track."""
        self.send_chat_message('/rocks %u' % track_id)

    def send_sucks(self, track_id):
        """Sends the bot a note that the user hates the specified track."""
        self.send_chat_message('/sucks %u' % track_id)

    def skip_track(self, track_id):
        self.send_chat_message('/skip %u' % track_id)

    def on_idle(self):
        """Delivers messages to the GUI using callbacks."""
        self.process_queue(0)

        for replies in self.fetch_replies():
            if type(replies) != list:
                replies = [replies]
            for reply in replies:
                if 'join' == reply[0] and self.on_user_joined:
                    self.on_user_joined(reply[1])
                elif 'part' == reply[0] and self.on_user_parted:
                    self.on_user_parted(reply[1])
                elif 'disconnected' == reply[0] and self.on_disconnected:
                    self.on_disconnected()
                elif 'chat' == reply[0] and self.on_chat_message:
                    self.on_chat_message(reply[1], reply[2])
                elif 'joined' == reply[0] and self.on_self_joined:
                    self.on_self_joined()
                elif 'parted' == reply[0] and self.on_self_parted:
                    self.on_self_parted()
                elif 'offline' == reply[0] and self.on_disconnected:
                    self.on_disconnected()
                elif 'track_info' == reply[0] and self.on_track_info:
                    self.on_track_info(reply[1])
                else:
                    print 'Unhandled jabber message:', str(reply)

    # --- local commands ---

    def set_track_info(self, ti):
        old_id = self.track_info.get('id')
        self.track_info.update(ti)
        if old_id != self.track_info.get('id'):
            self.send_chat_message('/dump %u' % self.track_info.get('id'))

    def post_replies(self, replies):
        self.in_queue.put(replies)

    def fetch_replies(self):
        rep = []
        while not self.in_queue.empty():
            rep.append(self.in_queue.get())
        return rep

    def is_connected(self):
        return self.cli is not None

    def _connect(self):
        """Connects to the jabber server."""
        jid = self.config.get_jabber_id()
        password = self.config.get_jabber_password()
        if not jid or not password:
            self._log('disabled: jid/password not set.')
            return False

        self.jid = xmpp.protocol.JID(jid)
        if self.config.get_debug():
            cli = xmpp.Client(self.jid.getDomain())
        else:
            cli = xmpp.Client(self.jid.getDomain(), debug=[])

        res = cli.connect(proxy=self._get_proxy_settings())
        if not res:
            self._log('could not connect to %s.' % self.jid.getDomain())
            return False

        res = cli.auth(self.jid.getNode(), password, 'tmclient/')
        if not res:
            self._log('could not authorize with the server.')
            self.post_replies(('auth-error', ))
            return False

        self._log('connected to %s.' % self.jid.getDomain())
        self.last_ping_ts = time.time()

        self.cli = cli
        self.cli.sendInitPresence()
        self.roster = self.cli.Roster.getRoster()
        self.cli.RegisterHandler('message', self._on_message)
        self.cli.RegisterHandler('presence', self._on_presence)

        self.bot_jid = self.config.get_jabber_bot()
        self._join_chat_room()
        self._check_roster()
        return True

    def _get_proxy_settings(self):
        if 'http_proxy' not in os.environ:
            return None
        url = urlparse.urlparse(os.environ['http_proxy'])
        if not url.netloc:
            return None
        return { 'host': url.hostname, 'port': url.port or 80 }

    def _check_roster(self):
        """Checks whether we have the bot on our roster."""
        know = False
        for contact in self.roster.getItems():
            if contact == self.bot_jid:
                know = True
        if not know:
            self._log('need to make friends with %s' % self.bot_jid)
            msg = xmpp.Presence(to=self.bot_jid, typ='subscribe', status=u'Hello, I\'m using tmradio-client/' + tmradio.version)
            self.cli.send(msg)

    def _join_chat_room(self, suffix=None):
        """Joins you to the chat room."""
        if self.chat_active:
            self._log('double chat join prevented.')
            return
        self.chat_jid = self.config.get_jabber_chat_room()
        nick = self.config.get_jabber_chat_nick()
        if not nick:
            nick = self.jid.getStripped().split('@')[0]
        if suffix is not None:
            nick += suffix
        nick = nick.replace('%R', str(random.randrange(1111, 9999)))
        self.cli.send(xmpp.Presence(to=u'/'.join((self.chat_jid, nick))))
        self.chat_my_name = nick

    def _leave_chat_room(self):
        """Removes you from the chat room."""
        if not self.chat_my_name or not self.chat_active:
            self._log('trying to leave chat while not there')
        else:
            self._log('leaving the chat room.')
            msg = xmpp.Presence()
            msg.setTo(u'/'.join((self.chat_jid, self.chat_my_name)))
            msg.setType('unavailable')
            self.cli.send(msg)

    def _on_message(self, conn, msg):
        """Process chat and group chat messages."""
        self.last_ping_ts = time.time()
        if msg.getType() == 'groupchat':
            parts = unicode(msg.getFrom()).split('/')
            if len(parts) < 2:
                pass # tmradio.log.debug(msg)
            else:
                nick = unicode(msg.getFrom()).split('/')[1]
                self.post_replies([
                    ('chat', msg.getBody(), nick, self._get_msg_ts(msg)),
                ])
            return

        elif msg.getFrom().getStripped() == self.bot_jid:
            text = msg.getBody()
            if not text:
                self._log('empty message received: %s' % msg)
                return
            if text.startswith('{'):
                self.set_track_info(json.loads(text))
                self.post_replies((('track_info', self.track_info)))
                return
        # self._log('unhandled message: %s' % msg.getBody())

    def _get_msg_ts(self, msg):
        delay = msg.getTag('delay')
        if not delay:
            return None
        if not 'stamp' in delay.attrs:
            return None
        return time.mktime(time.strptime(delay.attrs['stamp'][:19], '%Y-%m-%dT%H:%M:%S'))

    def _on_presence(self, conn, msg):
        """Process incoming presences."""
        self.last_ping_ts = time.time()
        sender = msg.getFrom()
        if self.bot_jid == sender.getStripped():
            self._on_bot_presence(msg)

        # Nickname taken in the chat room, append a random number.
        elif sender.getStripped() == self.config.get_jabber_chat_room():
            self._check_nickname_taken(sender, msg)

            replies = []
            myself = sender.getResource() == self.chat_my_name
            if msg.getType() == 'unavailable':
                replies.append(('part', sender.getResource()))
                if myself:
                    replies.append(('left', ))
                    self.chat_active = False
            else:
                replies.append(('join', sender.getResource()))
                if myself:
                    replies.append(('joined', ))
                    self.chat_active = True
            if len(replies):
                self.post_replies(replies)

    def _on_bot_presence(self, msg):
        if msg.getType() == 'unavailable':
            self.post_replies(('offline', ))
            return

        match = self.np_re.match(msg.getStatus() or '')
        if match:
            title, artist, track_id, count, weight, listeners = match.groups()
            self.set_track_info({
                'id': int(track_id),
                'artist': artist,
                'title': title,
                'count': int(count),
                'weight': float(weight),
                'listeners': int(listeners),
            })
            self.post_replies(('track_info', self.track_info))
        else:
            self._log('bot status not understood: %s' % msg.getStatus())

    def _check_nickname_taken(self, sender, msg):
        er = msg.getTag('error')
        if er and er.attrs['code'] == '409':
            self.post_replies([
                ('chat', er.getTag('text').getCDATA(), sender.getResource()),
            ])
            self.chat_my_name = None
            self._join_chat_room(suffix=' (%R)')

    def _thread_worker(self):
        while not self.is_shutting_down:
            self.process_queue(1)

    def process_queue(self, timeout=0):
        if self.cli:
            res = self.cli.Process(timeout)
            if res == 0 or res is None:
                self._on_disconnected()
            self.ping_server()
        elif time.time() > self.reconnect_time:
            self.reconnect_time = int(time.time()) + 5
            self.post_message('connect', special=True)
        elif timeout:
            time.sleep(timeout) # prevent spinlocks
        while not self.out_queue.empty():
            text, chat, special = self.out_queue.get()
            self._process_message(text, chat, special)

    def ping_server(self):
        """Pings the server, reconnects on timeout."""
        now = time.time()
        if now - self.last_ping_ts < self.PING_FREQUENCY:
            return False
        self._log('pinging the server')
        self.last_ping_ts = now
        ping = xmpp.Protocol('iq',typ='get',payload=[xmpp.Node('ping',attrs={'xmlns':'urn:xmpp:ping'})])
        try:
            res = self.cli.SendAndWaitForResponse(ping, self.PING_TIMEOUT)
            if res is None:
                self._log('ping timeout')
                self._on_disconnected()
        except IOError, e:
            self._log('error pinging the server:')
            self._on_disconnected()
        return True

    def _process_message(self, text, chat=False, special=False):
        self._log('processing message: text="%s" chat=%s special=%s' % (text, chat, special))

        if special:
            if text == 'connect':
                if not self.cli:
                    self._connect()
            elif text == 'leave':
                self._leave_chat_room()
            elif text == 'join':
                if not self.cli:
                    self._connect()
                if self.cli:
                    self._join_chat_room()
            elif text == 'quit':
                self.is_shutting_down = True
                gtk.main_quit() # FIXME: what if we're not connected?
            else:
                self._log('^^^ unknown command.')
        elif chat:
            msg = xmpp.protocol.Message(body=text)
            msg.setTo(self.chat_jid)
            msg.setType('groupchat')
            self.cli.send(msg)
            self._log('sent to chat: %s' % text)
        else:
            msg = xmpp.protocol.Message(body=text)
            msg.setTo(self.bot_jid)
            msg.setType('chat')
            self.cli.send(msg)
            self._log('sent to bot: %s' % text)

    def _log(self, message):
        pass # tmradio.log.error('jabber:', message) # FIXME: use a real log, this breaks Windows console (CP-866).

    def _on_disconnected(self):
        self._log('disconnected from the server, reconnecting in 5 seconds.')
        self.cli = None
        self.chat_active = False
        self.chat_my_name = None
        self.post_replies([('left', ), ('disconnected', )])
        self.reconnect_time = int(time.time()) + 5

def Open():
    return Jabber()
