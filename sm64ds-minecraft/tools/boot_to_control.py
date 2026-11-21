#!/usr/bin/env python3
"""
Cold-boot a (modded) SM64DS EUR ROM headlessly and drive it to the first moment the player can move:
title -> ADVENTURE -> new file A -> intro cutscenes -> Yoshi controllable in front of the castle.
Saves that point as a save state for tests.   needs: libretro-desmume, ndspy-free.

  python3 -I tools/boot_to_control.py <rom.nds> <mod.elf> <out.state> [screenshot.png]
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsrun import DS

CORE = '/usr/lib/x86_64-linux-gnu/libretro/desmume_libretro.so'
OPTS = {'desmume_pointer_mouse': 'enable', 'desmume_pointer_type': 'touch'}

def syms(elf):
    out = subprocess.run(['arm-none-eabi-nm', elf], check=True, capture_output=True, text=True).stdout
    return {p[2]: int(p[0], 16) for p in (l.split() for l in out.splitlines()) if len(p) == 3}

def open_ds(rom, workdir='dswork'):
    return DS(CORE, rom, workdir, options=OPTS)

def main(rom, elf, out_state, shot=None):
    s = syms(elf); mod = open(os.path.splitext(elf)[0] + '.bin', 'rb').read()
    ds = open_ds(rom)
    ds.run(600)                                   # logos -> "touch to start"
    ds.touch(128, 96, 6, 200); ds.touch(128, 96, 6, 200); ds.tap('A', after=200)
    ds.touch(127, 166, 6, 200)                    # ADVENTURE
    ds.tap('A', after=200); ds.tap('A', after=300)  # file A (new) -> peach's letter
    ds.locate_ram(s['__mod_start'], mod[:48])
    probe = out_state + '.probe'
    for step in range(120):                       # skip cutscenes until exactly one player can move
        ds.tap('START', 4, 40); ds.tap('B', 4, 40); ds.tap('A', 4, 40)
        h0 = ds.read32(s['mod_debug_frames']); ds.run(60)
        rate = (ds.read32(s['mod_debug_frames']) - h0) / 60
        if abs(rate - 0.5) > 0.05: continue       # 0.5/frame == one Player at the 30 Hz logic rate
        ds.run(120); ds.save_state(probe)
        p = ds.read32(s['mod_debug_player']) & 0xffffffff
        a = [ds.read32(p + 0x5c + 4 * i) for i in range(3)]
        ds.run(30, hold={'UP'})
        b = [ds.read32(p + 0x5c + 4 * i) for i in range(3)]
        ds.load_state(probe)
        if sum(abs(x - y) for x, y in zip(a, b)) / 4096 > 40:
            os.replace(probe, out_state)
            if shot: ds.run(1); ds.screenshot(shot)
            print(f'controllable after {ds.frames} frames; player {p:#010x}; state -> {out_state}')
            return ds
    sys.exit('never reached a controllable player')

if __name__ == '__main__':
    if len(sys.argv) not in (4, 5): sys.exit(__doc__)
    main(*sys.argv[1:])
