# fraction of symbol addresses (in main arm9) that sit on a push{} prologue, vs random baseline
import sys, re, struct, random, ndspy.rom
r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1]); base = r.arm9RamAddress
code = r.loadArm9().sections[0].data
txt = open(sys.argv[2]).read()
addrs = [int(a,16) for a in re.findall(r'(?:addr:|= )0x([0-9a-fA-F]{8})', txt)]
addrs = [a-base for a in addrs if 0 <= a-base < len(code) and a % 4 == 0]
push = lambda o: struct.unpack_from('<I', code, o)[0] >> 16 == 0xE92D
hits = sum(push(o) for o in addrs)
rnd = [random.randrange(0, len(code)//4)*4 for _ in range(5000)]
print(f'{sys.argv[2].split("/")[-1]}: {hits}/{len(addrs)} = {hits/len(addrs)*100:.1f}% on push (random baseline {sum(map(push,rnd))/50:.1f}%)')
