import adsk.core, adsk.fusion, adsk.cam, traceback
import os, math, re
from .TurtleUtils import TurtleUtils
from .JointMaker import JointMaker

f,core,app,ui,design,root = TurtleUtils.initGlobals()

_handlers = []

class TurtleUICommand():
    def __init__(self, cmdId:str, cmdName:str, cmdDesc:str):
        super().__init__()
        try:
            self.commandDefinition = ui.commandDefinitions.itemById(cmdId)
            if not self.commandDefinition:
                self.commandDefinition = ui.commandDefinitions.addButtonDefinition(cmdId, cmdName, cmdDesc)

            onCommandCreated = self.getCreatedHandler()
            self.commandDefinition.commandCreated.add(onCommandCreated)
            _handlers.append(onCommandCreated)

            self.commandDefinition.execute()
            
            adsk.autoTerminate(False)
        except:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
    
    # Override 'on' methods to add custom funcionality
    def onStartedRunning(self, cmd:core.Command):
        pass

    def onCreateUI(self, cmd:core.Command):
        pass
        
    def onInputsChanged(self, cmd:core.Command):
        pass
        
    def onValidateInputs(self, cmd:core.Command):
        pass
        
    def onDestroy(self, cmd:core.Command):
        pass

    # get handlers, only need to override to inject custom handlers
    def getCreatedHandler(self):
        return BaseCommandCreatedHandler(self)

    def getExecuteHandler(self):
        return BaseCommandExecuteHandler(self)

    def getInputChangedHandler(self):
        return BaseCommandInputChangedHandler(self)

    def getValidateInputsHandler(self):
        return BaseValidateInputsHandler(self)

    def getDestroyHandler(self):
        return BaseCommandDestroyHandler(self)


class BaseCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self, turtleUICommand:TurtleUICommand):
        super().__init__()
        self.turtleUICommand = turtleUICommand

    def notify(self, args):
        cmd = args.command

        onDestroy = self.turtleUICommand.getDestroyHandler()
        cmd.destroy.add(onDestroy)
        _handlers.append(onDestroy)
        
        onInputChanged = self.turtleUICommand.getInputChangedHandler()
        cmd.inputChanged.add(onInputChanged)
        _handlers.append(onInputChanged)    

        onValidateInputs = self.turtleUICommand.getValidateInputsHandler()
        cmd.validateInputs.add(onValidateInputs)
        _handlers.append(onValidateInputs)

        self.turtleUICommand.onStartedRunning(cmd)
        self.turtleUICommand.onCreateUI(cmd)

class BaseCommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self, turtleUICommand:TurtleUICommand):
        super().__init__()
        self.turtleUICommand = turtleUICommand
    def notify(self, args):
        cmd = args.command
        self.turtleUICommand.onInputsChanged(cmd)

class BaseValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    def __init__(self, turtleCommand:TurtleUICommand):
        super().__init__()
        self.turtleCommand = turtleCommand
    def notify(self, args):
        cmd = args.command
        self.turtleCommand.onValidateInputs(cmd)


class BaseCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self, turtleUICommand:TurtleUICommand):
        super().__init__()
        self.turtleUICommand = turtleUICommand
    def notify(self, args):
        cmd = args.command
        self.turtleUICommand.onDestroy(cmd)
        adsk.terminate()
        