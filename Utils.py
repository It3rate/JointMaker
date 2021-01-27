import adsk.core, adsk.fusion, adsk.cam, traceback

class Utils:
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

#f,core,app,ui,design,root = initGlobals()

# def run(context):
#     ui = None
#     try:
#         app = adsk.core.Application.get()
#         ui  = app.userInterface
#         #ui.messageBox('Hello script')

#     except:
#         #if ui:
#         #    ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
