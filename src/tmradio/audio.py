# vim: set fileencoding=utf-8:

try:
    import pygst
    pygst.require('0.10')
    import gst
    HAVE_GSTREAMER=True
except:
    HAVE_GSTREAMER=False


class DummyClient:
    def on_idle(self):
        pass

    def stop(self):
        pass

    def play(self, url, volume):
        pass

    def set_volume(self, volume):
        pass

    def can_play(self):
        return False


class GstClient(DummyClient):
    """Interaction with Gstreamer."""

    def __init__(self, on_track_change=None, config=None):
        """Initializes the player.

        on_track_change is called when stream metadata updates and receives the
        new stream title as the only parameter.
        """
        self.config = config
        self.pipeline = None
        self.stream_uri = None
        self.volume = None
        self.on_track_change = on_track_change
        self.restart_ts = None

    def on_idle(self):
        if self.restart_ts and time.time() >= self.restart_ts:
            self.restart_ts = time.time() + 5 # prevent spinning
            self.play(self.stream_uri)

    def play(self, uri, volume=None):
        print 'gst: starting %s' % uri
        self.restart_ts = None
        self.pipeline = self.get_pipeline(uri)
        if volume:
            self.volume.set_property('volume', volume)
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_bus_message)
        self.pipeline.set_state(gst.STATE_PLAYING)
        self.stream_uri = uri

    def stop(self):
        if self.pipeline:
            print 'gst: stopping %s' % self.stream_uri
            self.pipeline.set_state(gst.STATE_NULL)
            self.pipeline = None
            self.sink = None

    def get_pipeline(self, uri):
        pl = gst.Pipeline('pipeline')
        agent = 'tmradio-client/%s (%s)' % (VERSION, self.config.get_jabber_chat_nick(guess=True))
        tmp = gst.parse_launch('souphttpsrc location="%s" user-agent="%s" ! decodebin ! volume ! autoaudiosink' % (uri, agent))
        self.volume = list(tmp.elements())[1]
        pl.add(tmp)
        return pl

    def on_bus_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_TAG and self.on_track_change:
            dtags = {}
            rtags = message.parse_tag()
            for key in rtags.keys():
                dtags[key] = rtags[key]
            print 'Stream info updated:', dtags
            if dtags.has_key('title'):
                self.on_track_change(dtags['title'])
        elif t == gst.MESSAGE_BUFFERING:
            pass
        elif t == gst.MESSAGE_EOS or t == gst.MESSAGE_ERROR: # restart
            print 'gst: stream needs restarting.'
            self.stop()
            self.restart_ts = time.time() + 2
        else:
            pass # print message

    def set_volume(self, level):
        if self.volume:
            self.volume.set_property('volume', level)

    def can_play(self):
        return True


def Open(on_track_change=None, config=None):
    if HAVE_GSTREAMER:
        return GstClient(on_track_change, config)
    return DummyClient()
