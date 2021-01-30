import adsk.core, adsk.fusion, adsk.cam, traceback
import os, math, re
from .TurtleUtils import TurtleUtils
from .JointMaker import JointMaker

f,core,app,ui,design,root = TurtleUtils.initGlobals()

class TurtleCommand():
    def __init__(self, cmdId:str, cmdName:str, cmdDesc:str):
        super().__init__()
        self.handlers = []
        try:
            cmdDef = ui.commandDefinitions.itemById(cmdId)
            if not cmdDef:
                cmdDef = ui.commandDefinitions.addButtonDefinition(cmdId, cmdName, cmdDesc)

            onCommandCreated = self.createdHandler()
            cmdDef.commandCreated.add(onCommandCreated)
            self.handlers.append(onCommandCreated)
            cmdDef.execute()
            # Prevent this module from being terminate when the script returns, because we are waiting for event handlers to fire
            adsk.autoTerminate(False)
        except:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

    def executeHandler(self):
        return BaseCommandExecuteHandler(self)

    def createdHandler(self):
        return BaseCommandCreatedHandler(self)

    def runCommand(self):
        pass

    def requiredSelection(self):
        pass




class BaseCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self, turtleCommand:TurtleCommand):
        super().__init__()
        self.turtleCommand = turtleCommand

    def notify(self, args):
        try:
            self.turtleCommand.runCommand()
            adsk.terminate()
        except:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class BaseCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self, turtleCommand:TurtleCommand):
        super().__init__()
        self.turtleCommand = turtleCommand

    def notify(self, args):
        cmd = args.command
        onExecute = self.turtleCommand.executeHandler()
        cmd.execute.add(onExecute)
        self.turtleCommand.handlers.append(onExecute)   
