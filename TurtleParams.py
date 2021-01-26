
import adsk.core, adsk.fusion, traceback
import os, math, re, sys
from .Utils import Utils

f,core,app,ui,design,root = Utils.initGlobals()

class TurtleParams:

    def __init__(self, units:str="mm"):
        self.curUnits = units

    def getValue(self, name):
        param = design.userParameters.itemByName(name)
        return "" if param is None else param.expression

    def addParams(self, *nameValArray):
        result = []
        for i in range(0, len(nameValArray), 2):
            result.append(self.addParam(nameValArray[i], nameValArray[i+1]))
        return result

    def addParam(self, name, val, unitKind="", msg=""):
        units = self.curUnits if unitKind=="" else unitKind
        result = design.userParameters.itemByName(name)
        if result is None:
            result = design.userParameters.add(name, self.createValue(val, units), units, msg)
        return result

    def createValue(self, val, unitKind=""):
        units = self.curUnits if unitKind=="" else unitKind
        if isinstance(val, str):
            return adsk.core.ValueInput.createByString(val)
        elif isinstance(val, (int, float)):
            return adsk.core.ValueInput.createByString(str(val) + units)
        elif isinstance(val, bool):
            return adsk.core.ValueInput.createByBoolean(val)
        else:
            return adsk.core.ValueInput.createByObject(val)

    def printAllParams(self):
        for param in design.userParameters:
            print(param.name + ": " + param.expression)

    
        