# encoding=utf-8

"""Text interface for the tmradio client."""

import readline

import tmradio.audio
import tmradio.jabber


class TextClient:
    def __init__(self):
        self.jabber = tmradio.jabber.Open()
        self.audio = tmradio.audio.Open()

        self.jabber.set_handlers({
            'chat-message': self.on_chat_message,
            'chat-joined': self.on_user_joined,
            'chat-parted': self.on_user_parted,
            'track-info': self.on_track_info,
        })

    def on_chat_message(self, **kwargs):
        print kwargs

    def on_user_joined(self, nickname):
        print nickname

    def on_user_parted(self, nickname):
        print nickname

    def on_track_info(self, ti):
        print ti

    def run(self):
        tmradio.log.quiet = True
        print 'Ready.'
        while True:
            try:
                text = raw_input('> ')
            except EOFError:
                return self.exit()
            if not text:
                continue
            cmd = text.split(' ', 1)[0].lower()
            if cmd == '/exit':
                return self.exit()
            else:
                self.jabber.send_chat_message(text)

    def exit(self):
        self.jabber.shutdown()

def Run():
    TextClient().run()
