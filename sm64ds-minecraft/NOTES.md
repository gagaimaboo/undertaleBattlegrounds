# sm64ds × minecraft (steve mod) — research notes

## inputs (kept local, never committed)
- **target rom: Super Mario 64 DS (Europe) rev0, game code `ASMP`, sha1 `1367529f2cb23e76ef295cb1727333ae8f0a6cd7`**
- (unused) USA rev0 `ASME`, sha1 `a5b8bd846725965c588b6fc591f1fe822f7bbdbd` — community symbols don't fit it
- minecraft: 1.21.6 client.jar, sha1 `740a125b83dd3447feaa3c5e891ead7fbb21ae28` (matches mojang's official build)

## minecraft reference pipeline
1. fetch official `client_mappings` (client.txt) for 1.21.6 from piston-meta
2. `python3 tools/pg2srg.py client.txt client.srg` (proguard -> srg; SpecialSource can't read proguard)
3. `java -jar SpecialSource-1.11.4-shaded.jar -i client.jar -m client.srg -o client-named.jar`
4. `java -jar vineflower-1.11.1.jar --only=net/minecraft/world/ client-named.jar src/`
- used as a *behavior reference only* (numbers/formulas); the mod is original C++.

## sm64ds toolchain findings
- devkitPro is blocked from this cloud env (cloudflare 403); apt `gcc-arm-none-eabi` 13.2 works for arm946e-s.
- `ndspy` (pip) reads the rom: 1833 files, player models/anims in `data/player/*.bmd|*.bca`, 103 arm9 overlays.
- SM64DS-PI (pants64DS/SM64DS-PI): headers + 3358 arm9 symbols — **EUR (ASMP) addresses**.
  evidence: `LEVEL_OVL_MAP = 0x020758c8` == SM64DSe's EUR level-overlay table offset `0x758c8`
  (USA rev0 uses `0x73594`).
- tangOS sm64ds-decomp: first 64KB of arm9 matches USA rev0, then drifts (-0x124, +0x374, ...) —
  also not USA rev0. `tools/symcheck.py` reproduces this.
- SM64DSe-Ultimate supports EUR / USA_v1 (rev0) / USA_v2 / JAP for level + model editing.

## region verification (`tools/pushcheck.py`: symbol addrs landing on a `push {...}` prologue)
| symbols | USA rev0 | EUR rev0 | random |
|---|---|---|---|
| SM64DS-PI symbols9.x | 3.7% | **55.7%** | ~1.3% |
| sm64ds-decomp symbols.txt | 3.2% | **44.4%** | ~1.1% |
- `Player::Behavior` (0x020e4d24) lives in **overlay 2** and begins `push {r4-r6, lr}` on EUR.
- non-hits are mostly leaf functions (no push) and data symbols. => build against EUR.
