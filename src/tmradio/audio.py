# vim: set fileencoding=utf-8:

import os
import time

try:
    import pygst
    pygst.require('0.10')
    import gst
    HAVE_GSTREAMER=True
except:
    HAVE_GSTREAMER=False

import tmradio
import tmradio.config
import tmradio.log


class DummyClient:
    def __init__(self):
        pass

    def on_idle(self):
        pass

    def stop(self):
        pass

    def play(self, url=None, volume=None):
        pass

    def set_volume(self, volume):
        pass

    def get_volume(self):
        return 0.5

    def can_play(self):
        return False

    def is_playing(self):
        return False


class GstClient(DummyClient):
    """Interaction with Gstreamer."""
    volume_check_delay = 2 # seconds

    def __init__(self, on_track_change=None, on_start=None, on_stop=None):
        """Initializes the player.

        on_track_change is called when stream metadata updates and receives the
        new stream title as the only parameter.
        """
        self.config = tmradio.config.Open()
        self.pipeline = None
        self.stream_uri = None
        self.volume = self.config.get_volume()
        self.volume_ctl = None
        self.volume_check_ts = None
        self.on_track_change = on_track_change
        self.on_start = on_start
        self.on_stop = on_stop
        self.restart_ts = None

    def on_idle(self):
        if self.restart_ts and time.time() >= self.restart_ts:
            self.restart_ts = time.time() + 5 # prevent spinning
            self.play(self.stream_uri)

        if self.volume_check_ts and time.time() >= self.volume_check_ts:
            self.volume_check_ts = None
            if self.volume and not self.is_playing():
                tmradio.log.debug('Starting player: non-zero volume.')
                self.play(self.config.get_stream_uri())
            elif not self.volume and self.is_playing():
                tmradio.log.debug('Stopping player: zero volume.')
                self.stop()

    def play(self, uri=None, volume=None):
        if uri is None:
            uri = self.config.get_stream_uri()
        if volume is not None:
            self.volume = volume
        tmradio.log.debug('gst: starting %s' % uri)
        self.restart_ts = None
        self.pipeline = self.get_pipeline(uri)
        self.volume_ctl.set_property('volume', self.volume)
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_bus_message)
        self.pipeline.set_state(gst.STATE_PLAYING)
        self.stream_uri = uri
        if self.on_start:
            self.on_start()

    def stop(self):
        if self.pipeline:
            tmradio.log.debug('gst: stopping %s' % self.stream_uri)
            self.pipeline.set_state(gst.STATE_NULL)
            self.pipeline = None
            self.sink = None
            if self.on_stop:
                self.on_stop()

    def get_pipeline(self, uri):
        pl = gst.Pipeline('pipeline')
        agent = 'tmradio-client/%s; %s (%s)' % (tmradio.version, os.name, self.config.get_jabber_chat_nick(guess=True))
        tmp = gst.parse_launch('souphttpsrc location="%s" user-agent="%s" ! decodebin ! volume ! autoaudiosink' % (uri, agent))
        self.volume_ctl = list(tmp.elements())[1]
        pl.add(tmp)
        return pl

    def on_bus_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_TAG and self.on_track_change:
            dtags = {}
            rtags = message.parse_tag()
            for key in rtags.keys():
                dtags[key] = rtags[key]
            tmradio.log.debug('Stream info updated: %s' % dtags)
            if 'title' in dtags:
                self.on_track_change(dtags['title'])
        elif t == gst.MESSAGE_BUFFERING:
            pass
        elif t == gst.MESSAGE_EOS or t == gst.MESSAGE_ERROR: # restart
            tmradio.log.info('gst: stream needs restarting.')
            self.stop()
            self.restart_ts = time.time() + 2
        else:
            pass # tmradio.log.debug(message)

    def set_volume(self, level):
        tmradio.log.debug('set_volume(%s)' % level)
        old_level = self.volume
        self.volume = level
        if self.volume_ctl:
            self.volume_ctl.set_property('volume', level)

        if old_level == 0 and level > 0:
            self.volume_check_ts = time.time()
        else:
            self.volume_check_ts = time.time() + self.volume_check_delay

        config = tmradio.config.Open()
        config.set_volume(self.volume)
        config.save()

    def get_volume(self):
        return self.volume

    def can_play(self):
        return True

    def is_playing(self):
        return self.pipeline is not None


def Open(**kwargs):
    if HAVE_GSTREAMER:
        return GstClient(**kwargs)
    return DummyClient()
