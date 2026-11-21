#!/usr/bin/env python3
"""
Phase-1 regression test: from a controllable state, jump with and without L held.
PASS = without L the player lands; with L the player keeps rising at ~3.7 units per logic frame.

  python3 -I tools/test_float.py <modded.nds> <mod.elf> <control.state>
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from boot_to_control import open_ds, syms

def heights(ds, s, mod, state, extra):
    ds.load_state(state); ds.locate_ram(s['__mod_start'], mod[:48])
    p = ds.read32(s['mod_debug_player']) & 0xffffffff; y0 = ds.read32(p + 0x60) / 4096
    ys = []
    for k in range(25):                       # 'B' is jump with this core's default mapping
        ds.run(4, hold=({'B'} if k < 2 else set()) | extra); ys.append(ds.read32(p + 0x60) / 4096 - y0)
    return ys

def main(rom, elf, state):
    s = syms(elf); mod = open(os.path.splitext(elf)[0] + '.bin', 'rb').read()
    ds = open_ds(rom); ds.run(5)
    plain, floaty = heights(ds, s, mod, state, set()), heights(ds, s, mod, state, {'L'})
    print('jump only :', [round(y) for y in plain]); print('jump + L  :', [round(y) for y in floaty])
    rate = (floaty[-1] - floaty[-11]) / 20     # 10 samples * 4 frames = 20 logic frames
    ok = abs(plain[-1]) < 1 and abs(rate - 0x3B23 / 4096) < 0.2
    print(f'landed without L: {abs(plain[-1]) < 1}; rise rate with L: {rate:.2f}/logic frame -> {"PASS" if ok else "FAIL"}')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:])
