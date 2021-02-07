import adsk.core, adsk.fusion, adsk.cam, traceback
import tkinter as tk

__decimalPlaces__ = 3

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
        
        # special case to make working with sketches easier 
        if selType is f.Sketch and app.activeEditObject.classType == f.Sketch.classType:
            return app.activeEditObject

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
        

    @classmethod
    def getClipboardText(cls):
        root = tk.Tk()
        root.withdraw()
        try:
            result = root.clipboard_get()
        except tk.TclError:
            result = ""
        return result

    @classmethod
    def setClipboardText(cls, data):
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(data)
        root.update() # now it stays on the clipboard after the window is closed
        root.destroy()

    @classmethod
    def clearClipboardText(cls):
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.update()
        root.destroy()