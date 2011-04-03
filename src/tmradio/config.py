# vim: set fileencoding=utf-8:

import base64
import os
import sys
import yaml

class YamlConfig:
    """YAML interface."""
    def __init__(self):
        self.filename = os.path.expanduser('~/.tmradio-client.yaml')
        if os.path.exists(self.filename):
            self.data = yaml.load(open(self.filename, 'rb').read())
        else:
            self.data = {}

    def save(self):
        dump = yaml.dump(self.data)
        exists = os.path.exists(self.filename)
        f = open(self.filename, 'wb')
        f.write(dump.encode('utf-8'))
        f.close()
        if not exists:
            os.chmod(self.filename, 0600)

    def get(self, key, default=None):
        if self.data.has_key(key):
            return self.data[key]
        return default

    def get_volume(self):
        return float(self.get('volume', 0.75))

    def set_volume(self, value):
        self.data['volume'] = float(value)

    def get_log(self):
        return self.get('log', '~/tmradio-client.log')

    def get_jabber_id(self):
        return self.get('jabber_id')

    def set_jabber_id(self, value):
        self.data['jabber_id'] = value

    def get_jabber_password(self):
        return base64.b64decode(self.get('jabber_password'))

    def set_jabber_password(self, value):
        self.data['jabber_password'] = base64.b64encode(value)

    def get_debug(self):
        return self.get('debug', '--debug' in sys.argv)

    def get_jabber_bot(self):
        return self.get('jabber_bot', 'robot@tmradio.net')

    def set_jabber_bot(self, value):
        self.data['jabber_bot'] = value

    def get_jabber_chat_room(self):
        return self.get('jabber_chat_room', 'tmradio@conference.jabber.ru')

    def set_jabber_chat_room(self, value):
        self.data['jabber_chat_room'] = value

    def get_jabber_chat_nick(self, guess=False):
        nick = self.get('jabber_chat_nick')
        if not nick and guess:
            nick = self.get_jabber_id().split('@')[0]
        return nick

    def set_jabber_chat_nick(self, value):
        self.data['jabber_chat_nick'] = value

    def get_stream_uri(self):
        return self.get('stream_uri', 'http://stream.tmradio.net:8180/live.mp3')

    def set_stream_uri(self, value):
        self.data['stream_uri'] = value

    def get_twitter_search(self):
        return self.get('twitter_search', '#tmradio')

    def set_twitter_search(self, value):
        self.data['twitter_search'] = value

def Open():
    return YamlConfig()
