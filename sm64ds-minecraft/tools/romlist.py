import sys, ndspy.rom, collections
r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
names = []
def walk(folder, prefix):
    for i, n in enumerate(folder.files): names.append(prefix + n)
    for n, sub in folder.folders: walk(sub, prefix + n + '/')
walk(r.filenames, '')
print(len(names), 'files')
print(collections.Counter(n.rsplit('.',1)[-1] for n in names).most_common(12))
print('top dirs:', sorted({n.split('/')[0] for n in names if '/' in n}))
print([n for n in names if 'mario' in n.lower() or 'player' in n.lower()][:25])
