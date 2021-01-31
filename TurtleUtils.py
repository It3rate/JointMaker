import adsk.core, adsk.fusion, adsk.cam, traceback

__decimalPlaces__ = 2

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


    @classmethod
    def ensureSelectionIsType(cls, selType):
        typeName = selType.__name__
        title = "Selection Required"
        if not design:
            ui.messageBox('No active Fusion design', title)
            return

        if ui.activeSelections.count < 1:
            ui.messageBox('Select ' + typeName + ' before running command.', title)
            return

        selected = ui.activeSelections.item(0).entity
        if not type(selected) is selType:
            ui.messageBox('Selected object needs to be a ' + typeName + ". It is a " + str(type(selected)) + ".", title)
            return
        return selected
    
    @classmethod
    def selectEntity(cls, entity):
        ui.activeSelections.clear()
        ui.activeSelections.add(entity)
    
    @classmethod
    def round(cls, val):
        return str(round(val, __decimalPlaces__))