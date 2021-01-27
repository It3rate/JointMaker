import adsk.core, adsk.fusion, adsk.cam, traceback
import os, math, re
from .Utils import Utils
from .JointMaker import JointMaker
from .TurtleSketch import TurtleSketch
from .TurtleParams import TurtleParams
from .TurtlePath import TurtlePath
from .MultiLayer import MultiLayer

f,core,app,ui,design,root = Utils.initGlobals()

# command
commandId = 'CreateShelvesId'
commandName = 'Create Shelves Command'
commandDescription = 'Creates three layer shelves and side walls based on a sketch.'
handlers = []
        
f,core,app,ui,design,root = Utils.initGlobals()

class CreateShelvesExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            jm = JointMaker()
            adsk.terminate()
        except:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class CreateShelvesCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        cmd = args.command
        onExecute = CreateShelvesExecuteHandler()
        cmd.execute.add(onExecute)
        handlers.append(onExecute)    

def run(context):
    try:
        cmdDef = ui.commandDefinitions.itemById(commandId)
        if not cmdDef:
            cmdDef = ui.commandDefinitions.addButtonDefinition(commandId, commandName, commandDescription)

        onCommandCreated = CreateShelvesCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)
        cmdDef.execute()
        # Prevent this module from being terminate when the script returns, because we are waiting for event handlers to fire
        adsk.autoTerminate(False)
    except:
        ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
