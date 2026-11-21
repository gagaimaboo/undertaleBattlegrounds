#!/usr/bin/env python3
"""
Tiny headless libretro frontend for the DeSmuME core, for testing mod ROMs without a screen.

    from dsrun import DS
    ds = DS('/usr/lib/x86_64-linux-gnu/libretro/desmume_libretro.so', 'game.nds', workdir)
    ds.run(60, hold={'A'})        # advance frames while holding buttons
    ds.read32(0x0214EAF0)         # read main RAM (0x02000000-0x023FFFFF)
    ds.screenshot('shot.png')     # both screens stacked
"""
import ctypes as C, os, struct

ENV_GET_CAN_DUPE, ENV_SET_PIXEL_FORMAT, ENV_GET_SYSTEM_DIRECTORY = 3, 10, 9
ENV_GET_VARIABLE, ENV_GET_SAVE_DIRECTORY, ENV_GET_CORE_OPTIONS_VERSION = 15, 31, 52
ENV_EXPERIMENTAL = 0x10000
JOYPAD = {'B':0,'Y':1,'SELECT':2,'START':3,'UP':4,'DOWN':5,'LEFT':6,'RIGHT':7,'A':8,'X':9,'L':10,'R':11}
RETRO_MEMORY_SYSTEM_RAM = 2

class GameInfo(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]
class Variable(C.Structure):
    _fields_ = [('key', C.c_char_p), ('value', C.c_char_p)]

ENV_CB   = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO_CB = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
BATCH_CB = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
POLL_CB  = C.CFUNCTYPE(None)
STATE_CB = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)

class DS:
    def __init__(self, core, rom, workdir, options=None):
        self.core = C.CDLL(core)
        self.workdir = os.path.abspath(workdir).encode(); os.makedirs(workdir, exist_ok=True)
        self.options = {k.encode(): v.encode() for k, v in (options or {}).items()}
        self._keep = []
        self.pixfmt = 0; self.frame = None; self._held_ids = set(); self._touch = None; self.frames = 0
        self._cbs = [ENV_CB(self._env), VIDEO_CB(self._video), AUDIO_CB(lambda l, r: None),
                     BATCH_CB(lambda d, n: n), POLL_CB(lambda: None), STATE_CB(self._state)]
        c = self.core
        c.retro_set_environment(self._cbs[0]); c.retro_init()
        for fn, cb in zip(['video_refresh','audio_sample','audio_sample_batch','input_poll','input_state'], self._cbs[1:]):
            getattr(c, 'retro_set_' + fn)(cb)
        self.romdata = open(rom, 'rb').read()
        self._buf = C.create_string_buffer(self.romdata, len(self.romdata))
        info = GameInfo(os.path.abspath(rom).encode(), C.cast(self._buf, C.c_void_p), len(self.romdata), None)
        c.retro_load_game.restype = C.c_bool
        if not c.retro_load_game(C.byref(info)): raise RuntimeError('core refused to load the ROM')
        c.retro_get_memory_data.restype = C.c_void_p; c.retro_get_memory_size.restype = C.c_size_t
        self.ram_ptr = c.retro_get_memory_data(RETRO_MEMORY_SYSTEM_RAM)
        self.ram_size = c.retro_get_memory_size(RETRO_MEMORY_SYSTEM_RAM)

    def _env(self, cmd, data):
        cmd &= ~ENV_EXPERIMENTAL
        if cmd in (ENV_GET_SYSTEM_DIRECTORY, ENV_GET_SAVE_DIRECTORY):
            p = C.c_char_p(self.workdir); self._keep.append(p)
            C.cast(data, C.POINTER(C.c_char_p))[0] = self.workdir; return True
        if cmd == ENV_SET_PIXEL_FORMAT:
            self.pixfmt = C.cast(data, C.POINTER(C.c_int))[0]; return True
        if cmd == ENV_GET_CAN_DUPE:
            C.cast(data, C.POINTER(C.c_bool))[0] = True; return True
        if cmd == ENV_GET_VARIABLE:
            v = C.cast(data, C.POINTER(Variable))[0]
            if v.key in self.options:
                s = C.c_char_p(self.options[v.key]); self._keep.append(s)
                C.cast(data, C.POINTER(Variable))[0].value = s.value; return True
            return False
        return False

    def _video(self, data, w, h, pitch):
        if data: self.frame = (C.string_at(data, pitch * h), w, h, pitch)

    def _state(self, port, device, index, id_):
        if port != 0: return 0
        if device == 1: return 1 if id_ in self._held_ids else 0          # joypad
        if device == 6 and self._touch:                                    # pointer = touchscreen
            x, y = self._touch                                             # bottom-screen pixels
            if id_ == 0: return int(x * 65535 / 255 - 32767)
            if id_ == 1: return int((y + 192) * 65535 / 383 - 32767)       # screens are stacked 256x384
            if id_ == 2: return 1
        return 0

    def run(self, n=1, hold=(), touch=None):
        self._held_ids = {JOYPAD[b] for b in hold}; self._touch = touch
        for _ in range(n): self.core.retro_run(); self.frames += 1
        self._held_ids = set(); self._touch = None

    def touch(self, x, y, frames=4, after=20):
        self.run(frames, touch=(x, y)); self.run(after)

    def tap(self, button, frames=4, after=20):
        self.run(frames, hold={button}); self.run(after)

    # the core exposes no RAM pointer, so main RAM is read out of a save state. its offset inside the
    # state is found once by searching for a known 64-byte signature at a known address.
    def snapshot(self):
        c = self.core; c.retro_serialize_size.restype = C.c_size_t
        n = c.retro_serialize_size(); buf = C.create_string_buffer(n)
        c.retro_serialize.restype = C.c_bool
        if not c.retro_serialize(buf, n): raise RuntimeError('serialize failed')
        self._state_bytes = buf.raw
        return self._state_bytes
    def locate_ram(self, sig_addr, sig):
        st = self.snapshot(); i = st.find(sig)
        if i < 0 or st.find(sig, i + 1) >= 0: raise RuntimeError('signature not found exactly once')
        self.ram_base_in_state = i - (sig_addr - 0x02000000)
    def read32(self, addr, fresh=True):
        st = self.snapshot() if fresh else self._state_bytes
        o = self.ram_base_in_state + addr - 0x02000000
        return struct.unpack_from('<i', st, o)[0]

    def screenshot(self, path):
        from PIL import Image
        data, w, h, pitch = self.frame
        if self.pixfmt == 1:   # XRGB8888
            img = Image.frombuffer('RGBX', (w, h), data, 'raw', 'BGRX', pitch, 1).convert('RGB')
        else:                  # RGB565
            img = Image.frombuffer('RGB', (w, h), data, 'raw', 'BGR;16', pitch, 1)
        img.save(path)

def _save_state(self, path):
    open(path, 'wb').write(self.snapshot())
def _load_state(self, path):
    data = open(path, 'rb').read(); self.core.retro_unserialize.restype = C.c_bool
    if not self.core.retro_unserialize(C.create_string_buffer(data, len(data)), len(data)):
        raise RuntimeError('unserialize failed')
DS.save_state, DS.load_state = _save_state, _load_state
