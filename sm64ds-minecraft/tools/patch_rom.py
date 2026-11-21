#!/usr/bin/env python3
"""
Inject the steve mod into a Super Mario 64 DS (EUR, ASMP rev0) ROM.

  python3 -I tools/patch_rom.py <clean_eur.nds> mod/build/mod.elf <out.nds>   (mod.bin must sit next to it)

- adds mod.bin as a new ARM9 autoload section at MOD_BASE (crt0 copies it there at boot)
- bumps the main arena start (OS_GetInitArenaLo literal) past the mod so the heap can't overwrite it
- writes "b <trampoline>" over the first instruction of each hooked function
Every original word is checked before it is touched, so a wrong ROM fails loudly instead of crashing.
"""
import hashlib, os, struct, subprocess, sys
import ndspy.rom, ndspy.code

EUR_SHA1 = '1367529f2cb23e76ef295cb1727333ae8f0a6cd7'
MOD_BASE = 0x0214EAA0          # end of the highest overlay (ov102) == vanilla main arena start
ARENA_LO_LITERAL = 0x02058DE0  # literal pool word returned by OS_GetInitArenaLo(OS_ARENA_MAIN)

# (overlay id, address, expected original word, trampoline symbol in mod.elf)
HOOKS = [
    (2, 0x020E4D24, 0xE92D4070, 'mod_hook_player_behavior'),       # Player::Behavior: push {r4,r5,r6,lr}
    (2, 0x020E50AC, 0xE0000094, 'mod_hook_player_behavior_late'),  # inside Behavior: mul r0, r4, r0
]

def elf_symbols(elf):
    out = subprocess.run(['arm-none-eabi-nm', elf], check=True, capture_output=True, text=True).stdout
    return {parts[2]: int(parts[0], 16) for parts in (l.split() for l in out.splitlines()) if len(parts) == 3}

def branch(src, dst):
    off = (dst - (src + 8)) >> 2
    assert -(1 << 23) <= off < (1 << 23), 'branch out of range'
    return 0xEA000000 | (off & 0xFFFFFF)

def word(buf, base, addr):
    return struct.unpack_from('<I', buf, addr - base)[0]

def put(buf, base, addr, val, expect):
    got = word(buf, base, addr)
    if got != expect:
        sys.exit(f'refusing to patch {addr:#010x}: expected {expect:#010x}, found {got:#010x}')
    struct.pack_into('<I', buf, addr - base, val)

def main(rom_path, elf_path, out_path):
    syms = elf_symbols(elf_path)
    mod_path = os.path.splitext(elf_path)[0] + '.bin'
    if syms.get('__mod_start') != MOD_BASE: sys.exit('mod.elf is not linked at MOD_BASE')
    raw = open(rom_path, 'rb').read()
    if hashlib.sha1(raw).hexdigest() != EUR_SHA1:
        sys.exit('this is not the clean SM64DS EUR rev0 ROM this mod targets (sha1 mismatch)')
    rom = ndspy.rom.NintendoDSRom(raw)
    mod = open(mod_path, 'rb').read()
    mod_end = (MOD_BASE + len(mod) + 31) & ~31

    # --- arm9: arena bump + new autoload section
    arm9 = rom.loadArm9()
    cso = arm9.codeSettingsOffs
    arm9_compressed = struct.unpack_from('<I', rom.arm9, cso + 0x14)[0] != 0
    main_sec = arm9.sections[0]
    data = bytearray(main_sec.data)
    put(data, main_sec.ramAddress, ARENA_LO_LITERAL, mod_end, MOD_BASE)
    main_sec.data = bytes(data)
    if any(s.ramAddress == MOD_BASE for s in arm9.sections):
        sys.exit('ROM already contains a mod section')
    arm9.sections.append(ndspy.code.MainCodeFile.Section(mod, MOD_BASE, 0))
    rom.arm9 = arm9.save(compress=arm9_compressed)

    # --- overlays: hook branches
    ovs = rom.loadArm9Overlays()
    touched = {}
    for ov_id, addr, expect, sym in HOOKS:
        ov = ovs[ov_id]
        buf = touched.setdefault(ov_id, bytearray(ov.data))
        put(buf, ov.ramAddress, addr, branch(addr, syms[sym]), expect)
        print(f'hook {addr:#010x} (ov{ov_id}) -> {sym} @ {syms[sym]:#010x}')
    for ov_id, buf in touched.items():
        ov = ovs[ov_id]
        was_compressed = ov.compressed
        ov.data = bytes(buf)
        rom.files[ov.fileID] = ov.save(compress=was_compressed)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)

    open(out_path, 'wb').write(rom.save())
    print(f'mod: {len(mod)} bytes at {MOD_BASE:#010x}..{mod_end:#010x}; arena lo -> {mod_end:#010x}')
    print(f'arm9 compressed={arm9_compressed}; hooked {len(HOOKS)} function(s); wrote {out_path}')

if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:])
