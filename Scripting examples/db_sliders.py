# drawbot
ds =  CurrentDesignspace()

settings = [
    dict(name="glyphName", ui="EditText", args=dict(text="A"))
]

for axis in ds.getOrderedContinuousAxes():
    aD_minimum, aD_default, aD_maximum = ds.getAxisExtremes(axis)
    settings.append(dict(
        name=axis.name,
        ui="Slider",
        args=dict(
            value=aD_default,
            minValue=aD_minimum,
            maxValue=aD_maximum
            )  
        )      
    )
for axis in ds.getOrderedDiscreteAxes():
    print(axis.name)
    settings.append(dict(
        name=axis.name,
        ui="PopUpButton",
        args=dict(
            items=[str(v) for v in axis.values],
            )  
        )      
    )
location = dict()    
Variable(settings, location)

for axis in ds.getOrderedDiscreteAxes():
    if axis.name in location:
        location[axis.name] = axis.values[location[axis.name]]
        
glyphName = location.pop("glyphName")
if glyphName:
    result = ds.makeOneGlyph(glyphName=glyphName, location=location)
    drawGlyph(result)