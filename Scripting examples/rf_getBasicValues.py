
d = CurrentDesignspace()

# go through all axes and see what we have
for a in d.axes:
    print(a)

# ask for discrete axes specifically
print(d.discreteAxes())