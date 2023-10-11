d = CurrentDesignspace()
loc = d.newDefaultLocation()
pairs = [('public.kern1.i', 'public.kern2.b')]
k = d.makeOneKerning(loc, pairs)
info = d.makeOneInfo(loc)
print(k.items())
print(info)