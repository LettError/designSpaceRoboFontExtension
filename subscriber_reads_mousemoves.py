from mojo.subscriber import Subscriber, registerGlyphEditorSubscriber

class GlyphEditorSubscriber(Subscriber):
    
    debug = True
    
    def glyphEditorDidMouseDrag(self, info):
        print(info["lowLevelEvents"][-1]["tool"].__class__.__name__)
    
registerGlyphEditorSubscriber(GlyphEditorSubscriber)