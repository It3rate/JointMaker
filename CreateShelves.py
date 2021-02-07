import adsk.core, adsk.fusion, adsk.cam, traceback
from .lib.TurtleUtils import TurtleUtils
from .lib.TurtleCommand import TurtleCommand
from .lib.JointMaker import JointMaker

# command
f,core,app,ui,design,root = TurtleUtils.initGlobals()

class CreateShelves(TurtleCommand):
    def __init__(self):
        cmdId = 'CreateShelvesId'
        cmdName = 'Create Shelves Command'
        cmdDescription = 'Creates three layer shelves and side walls based on a sketch.'
        super().__init__(cmdId, cmdName, cmdDescription)

    def runCommand(self):
        JointMaker()


def run(context):
    cmd = CreateShelves()
