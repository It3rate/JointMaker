import adsk.core, adsk.fusion, adsk.cam, traceback

class TurtleUtils:
    def __init__(self):
        super().__init__()
        
    @classmethod
    def initGlobals(cls):
        global f
        global core
        global app
        global ui
        global design
        global root
        f = adsk.fusion
        core = adsk.core
        app = adsk.core.Application.get()
        ui  = app.userInterface
        design = f.Design.cast(app.activeProduct)
        root = f.Component.cast(design.rootComponent)
        return f,core,app,ui,design,root
