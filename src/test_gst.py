#!/usr/bin/env python
# encoding=utf-8

"""GStreamer test script.

This script starts playing tmradio.net using GStreamer.

The main purpose of this script is to test GStreamer availability on a system.
Might be helpful for porting to Windows."""

import pygst
pygst.require("0.10")
import gst
import gtk
import time


def get_pipeline(uri):
    pl = gst.Pipeline("pipeline")
    tmp = gst.parse_launch("souphttpsrc location=\"%s\" user-agent=\"test_gst.py\" ! decodebin ! autoaudiosink" % uri)
    pl.add(tmp)
    return pl


def on_bus_message(bus, msg):
    if msg.type == gst.MESSAGE_TAG:
        tags = msg.parse_tag()
        for k in tags.keys():
            print "tag: %s = %s" % (k, tags[k])
    elif msg.type == gst.MESSAGE_STATE_CHANGED:
        old, new, pending = msg.parse_state_changed()
        print "new state:", new.value_name
    elif msg.type == gst.MESSAGE_STREAM_STATUS:
        st = msg.parse_stream_status()
        print "stream status:", st[0].value_name
    elif msg.type == gst.MESSAGE_ERROR:
        tmp = msg.parse_error()
        print "error:", tmp[0].message
        gtk.main_quit()
    elif msg.type == gst.MESSAGE_DURATION:
        tmp = msg.parse_duration()
        print "duration:", tmp[0].value_name, tmp[1]
    elif msg.type == gst.MESSAGE_ASYNC_DONE:
        pass
    else:
        pass  # print "Unknown message of type", msg.type, msg


def play(uri):
    pl = get_pipeline(uri)

    bus = pl.get_bus()
    bus.add_signal_watch()
    bus.connect("message", on_bus_message)

    print "Playing %s" % uri
    pl.set_state(gst.STATE_PLAYING)

    try:
        gtk.main()
    except KeyboardInterrupt:
        print "Stopped."
    finally:
        pl.set_state(gst.STATE_NULL)


if __name__ == "__main__":
    play("http://stream.tmradio.net:8180/music.mp3")
