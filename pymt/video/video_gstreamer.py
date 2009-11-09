'''
VideoGStreamer: implementation of VideoBase with GStreamer
'''

try:
    import pygst
    pygst.require('0.10')
    import gst
except:
    raise

import threading
import gobject
from . import VideoBase
from ..baseobject import BaseObject
from ..graphx import get_texture_target, set_texture, drawTexturedRectangle, \
                     set_color
from ..texture import Texture
from OpenGL.GL import glTexSubImage2D, GL_UNSIGNED_BYTE, GL_RGB

# ensure that gobject have threads initialized.
gobject.threads_init()

class VideoGStreamer(VideoBase):
    '''VideoBase implementation using GStreamer (http://gstreamer.freedesktop.org/)
    '''

    __slots__ = ('_pipeline', '_decoder', '_videosink', '_colorspace',
                 '_videosize', '_buffer_lock')

    def __init__(self, **kwargs):
        self._pipeline      = None
        self._decoder       = None
        self._videosink     = None
        self._colorspace    = None
        self._buffer_lock   = threading.Lock()
        self._videosize     = (0, 0)
        super(VideoGStreamer, self).__init__(**kwargs)

    def stop(self):
        if self._pipeline is None:
            return
        self._wantplay = False
        self._pipeline.set_state(gst.STATE_PAUSED)

    def play(self):
        if self._pipeline is None:
            return
        self._wantplay = True
        self._pipeline.set_state(gst.STATE_PAUSED)

    def unload(self):
        if self._pipeline is None:
            return
        self._pipeline.set_state(gst.STATE_NULL)
        self._pipeline = None
        self._decoder = None
        self._videosink = None
        self._texture = None

    def load(self):
        # ensure that nothing is loaded before.
        self.unload()

        # create the pipeline
        self._pipeline = gst.Pipeline()

        # hardcoded to check which decoder is better
        if self._filename.split(':')[0] in ('http', 'https', 'file'):
            # network decoder
            self._decoder = gst.element_factory_make('uridecodebin', 'decoder')
            self._decoder.set_property('uri', self._filename)
            self._decoder.connect('pad-added', self._gst_new_pad)
            self._pipeline.add(self._decoder)
        else:
            # local decoder
            filesrc = gst.element_factory_make('filesrc')
            filesrc.set_property('location', self._filename)
            self._decoder = gst.element_factory_make('decodebin', 'decoder')
            self._decoder.connect('new-decoded-pad', self._gst_new_pad)
            self._pipeline.add(filesrc, self._decoder)
            gst.element_link_many(filesrc, self._decoder)

        # create colospace information
        self._colorspace = gst.element_factory_make('ffmpegcolorspace')

        # will extract video/audio
        caps_str = 'video/x-raw-rgb,red_mask=(int)0xff0000,green_mask=(int)0x00ff00,blue_mask=(int)0x0000ff'
        caps = gst.Caps(caps_str)
        self._videosink = gst.element_factory_make('appsink', 'videosink')
        self._videosink.set_property('emit-signals', True)
        self._videosink.set_property('caps', caps)
        self._videosink.connect('new-buffer', self._gst_new_buffer)

        # connect colorspace -> appsink
        self._pipeline.add(self._colorspace, self._videosink)
        gst.element_link_many(self._colorspace, self._videosink)

        # set to paused, for loading the file, and get the size information.
        self._pipeline.set_state(gst.STATE_PAUSED)

    def _gst_new_pad(self, dbin, pad, *largs):
        # a new pad from decoder ?
        # if it's a video, connect decoder -> colorspace
        c = pad.get_caps().to_string()
        if not c.startswith('video'):
            return
        try:
            dbin.link(self._colorspace)
        except:
            pass

    def _gst_new_buffer(self, appsink):
        # new buffer is comming, pull it.
        with self._buffer_lock:
            self._buffer = appsink.emit('pull-buffer')

    def _get_position(self):
        if self._videosink is None:
            return 0
        try:
            return self._videosink.query_position(gst.FORMAT_TIME)[0] / 1000000000.
        except:
            return 0

    def _get_duration(self):
        if self._videosink is None:
            return 0
        try:
            return self._videosink.query_duration(gst.FORMAT_TIME)[0] / 1000000000.
        except:
            return 0

    def draw(self):
        # no video sink ?
        if self._videosink is None:
            return

        # get size information first to create the texture
        if self._texture is None:
            for i in self._decoder.src_pads():
                cap = i.get_caps()[0]
                structure_name = cap.get_name()
                if structure_name.startswith('video') and cap.has_key('width'):
                    self._videosize = self.size = (cap['width'], cap['height'])
                    self._texture = Texture.create(
                        self._videosize[0], self._videosize[1], format=GL_RGB)
                    self._texture.flip_vertical()

        # no texture again ?
        if self._texture is None:
            return

        # ok, we got a texture, user want play ?
        if self._wantplay:
            self._pipeline.set_state(gst.STATE_PLAYING)
            self._wantplay = False

        # update needed ?
        with self._buffer_lock:
            if self._buffer is not None:
                target = get_texture_target(self._texture)
                set_texture(self._texture)
                glTexSubImage2D(target, 0, 0, 0,
                                self._videosize[0], self._videosize[1], GL_RGB,
                                GL_UNSIGNED_BYTE, self._buffer.data)
        # draw the texture
        set_color(*self.color)
        drawTexturedRectangle(texture=self._texture, pos=self.pos, size=self.size)
