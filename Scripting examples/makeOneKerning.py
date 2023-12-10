d = CurrentDesignspace()

#loc = d.newDefaultLocation()
loc = {'width': 140, 'weight': 400}
print(loc)

pairs = [('T', 'A')]
#pairs = None

k = d.makeOneKerning(loc, pairs)
k.round()
print(k.items())

info = d.makeOneInfo(loc)
info.round()
print("info.ascender", info.ascender, "info.descender", info.descender)