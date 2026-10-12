# check if decomp symbol addresses match function boundaries in this rom's arm9
import sys, re, struct, ndspy.rom
r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
a9 = r.loadArm9(); base = r.arm9RamAddress
code = bytearray()
for s in a9.sections:
    if s.ramAddress == base: code = bytearray(s.data); break
ok = bad = 0; samples = []
for line in open(sys.argv[2]):
    m = re.match(r'(\S+) kind:function\(arm,size=0x([0-9a-f]+)\) addr:0x([0-9a-f]+)', line)
    if not m: continue
    size, addr = int(m[2],16), int(m[3],16)
    off = addr - base
    if off < 0 or off + size > len(code) or size < 8: continue
    first = struct.unpack_from('<I', code, off)[0]
    last = struct.unpack_from('<I', code, off+size-4)[0]
    prologue = (first & 0xFFFF0000) == 0xE92D0000           # push {...}
    epilogue = last == 0xE12FFF1E or (last & 0xFFFF8000) == 0xE8BD8000 or (last & 0x0FFF8000) == 0x08BD8000  # bx lr / pop {...,pc}
    if prologue or epilogue: ok += 1
    else: bad += 1; samples.append(m[1])
print(f'matched {ok}, mismatched {bad} ({ok/(ok+bad)*100:.1f}% look like real functions)')
print('some mismatches:', samples[:5])
