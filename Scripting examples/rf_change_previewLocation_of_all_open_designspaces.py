for ds in AllDesignspaces():
    loc = ds.randomLocation()
    print(loc)
    ds.setPreviewLocation(loc)