
import adsk.core, adsk.fusion, adsk.cam, traceback
import os, math, re
from .TurtleUtils import TurtleUtils
from .TurtleComponent import TurtleComponent
from .TurtleSketch import TurtleSketch
from .TurtleParams import TurtleParams
from .TurtlePath import TurtlePath
from .TurtleLayers import TurtleLayers

f,core,app,ui,design,root = TurtleUtils.initGlobals()

pMID = "mid"
pOUTER = "outer"
pFULL = "full"
pLIP = "lip"
pSHELF_WIDTH = "shelfWidth"
pZIP_WIDTH = "zipWidth"
pZIP_LENGTH = "zipLength"

class SketchEncoder:
    def __init__(self):
        # self.baseLine:f.SketchLine = TurtleUtils.ensureSelectionIsType(f.SketchLine)
        # if not self.baseLine:
        #     return
        # self.tcomponent = TurtleComponent.createFromSketch(self.baseLine.parentSketch)
        # self.tsketch = self.tcomponent.getTSketch(self.baseLine.parentSketch)

        self.sketch:f.Sketch = TurtleUtils.ensureSelectionIsType(f.Sketch)
        if not self.sketch:
            return
        self.tcomponent = TurtleComponent.createFromSketch(self.sketch)
        #self.tsketch = self.tcomponent.getTSketch(sketch)
        
        self.points = {}
        self.pointKeys = []
        self.pointValues = []
        self.lines = {}
        self.lineKeys = []
        self.lineValues = []
        self.chains = []
        self.constraints = []
        self.dimensions = {}
        self.encodeFromSketch()

        TurtleUtils.selectEntity(self.sketch)
        

    def encodeFromSketch(self):
        self.encodeAllPoints()
        self.pointKeys = list(self.points)
        self.pointValues = list(self.points.values())
        TurtlePath.printPoints(self.points.values())

        chains = self.encodeAllChains()
        self.lineKeys = list(self.lines)
        self.lineValues = list(self.lines.values())
        for chain in chains:
            print("")
            comma = ""
            for lineIndex in chain:
                line = self.lineValues[lineIndex]
                print(comma + self.printLineIndexes(line), end="")
                comma = ","

        print("\ndimensions:")
        self.encodeAllDimensions()
        
        #TurtlePath.printLines(chain)
        
    def encodeAllPoints(self):
        for point in self.sketch.sketchPoints:
            self.points[point.entityToken] = point
        self.pointKeys = list(self.points)

    def encodeAllChains(self):
        tokens = []
        chains = []
        for line in self.sketch.sketchCurves:
            if not line.entityToken in tokens:
                chains.append(self.appendConnectedCurves(line, tokens))
        return chains

    def encodeAllDimensions(self):
        dims = []
        for dim in self.sketch.sketchDimensions:
            self.dimensions[dim.entityToken] = self.encodeDimension(dim)
        

    def appendConnectedCurves(self, baseLine:f.SketchLine, tokens:list):
        connected = self.sketch.findConnectedCurves(baseLine)
        result = []
        for line in connected:
            self.lines[line.entityToken] = line
            result.append(len(self.lines) - 1)
            tokens.append(line.entityToken)
        return result

    def findConnectedCurves(self, baseLine:f.SketchLine):
        connected = self.sketch.findConnectedCurves(baseLine)
        result = []
        for line in connected:
            result.append(line)
        return result


    def pointIndex(self, token):
        return self.pointKeys.index(token)

    def linePointIndexes(self, line:f.SketchLine):
        return [self.pointIndex(line.startSketchPoint.entityToken), self.pointIndex(line.endSketchPoint.entityToken)]

    def encodeDimension(self, dim:f.SketchDimension):
        result = ""
        if(type(dim) == f.SketchLinearDimension):
            tdim:f.SketchLinearDimension = dim
            result = "SLD" + self.encodeEntity(tdim.entityOne) + self.encodeEntity(tdim.entityTwo) + self.encodeExpression(tdim.parameter)
              # all points, lines etc need to be stored and indexed in one array?, as len can be point to line. Have points first, and a 'lastPointIndex' if needed. 
        elif(type(dim) == f.SketchOffsetDimension):
            tdim:f.SketchOffsetDimension = dim
            result = "SOD" + self.encodeEntity(tdim.line) + self.encodeEntity(tdim.entityTwo) + self.encodeExpression(tdim.parameter)

        print(result)
        return result

    def encodeEntity(self, entity):
        result = ""
        if entity in self.pointValues:
            result = "p" + str(self.pointValues.index(entity))
        elif entity in self.lineValues:
            result = "l" + str(self.lineValues.index(entity))
        return result

    def encodeExpression(self, expr):
        result = ""
        if expr:
            result = "v" + str(expr.expression)
        return result

    def printLineIndexes(self, line:f.SketchLine):
        return "(" + str(self.pointIndex(line.startSketchPoint.entityToken)) + "," + str(self.pointIndex(line.endSketchPoint.entityToken)) + ")"
