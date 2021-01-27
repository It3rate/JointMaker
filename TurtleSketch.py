
import adsk.core, adsk.fusion, traceback
import os, math, re, sys
from .Utils import Utils
from .TurtlePath import TurtlePath

f,core,app,ui,design,root = Utils.initGlobals()

class TurtleSketch:
    def __init__(self, sketchTarget:f.Sketch):
        self.sketch:f.Sketch = sketchTarget
        self.component = sketchTarget.parentComponent
        self.constraints:f.GeometricConstraints = sketchTarget.geometricConstraints
        self.dimensions:f.SketchDimensions = sketchTarget.sketchDimensions
        self.sketchLines:f.SketchLines = sketchTarget.sketchCurves.sketchLines
        self.profiles:f.Profiles = sketchTarget.profiles
        self.path:TurtlePath = TurtlePath(self.sketch)



    def draw(self, line:f.SketchLine, *data:str):
        data = " ".join(data)
        return self.path.draw(line, data, False)

    def drawClosed(self, line:f.SketchLine, *data:str):
        data = " ".join(data)
        return self.path.draw(line, data, True)

    def constrain(self, constraintList):
        self.path.setConstraints(constraintList)



    def setDistances(self, lines, indexValues):
        for pair in indexValues:
             self.addLineLength(self.sketch, lines[pair[0]], pair[1])

    def makeVertHorz(self, lines, indexes):
        for index in indexes:
            sp = lines[index].startSketchPoint.geometry
            ep = lines[index].endSketchPoint.geometry
            if(abs(sp.x - ep.x) < abs(sp.y - ep.y)):
                self.constraints.addVertical(lines[index])
            else:
                self.constraints.addHorizontal(lines[index])

    def makeEqual(self, curves, pairIndexes):
        for pair in pairIndexes:
            self.constraints.addEqual(curves[pair[0]], curves[pair[1]])

    def makeParallel(self, lines, pairIndexes):
        for pair in pairIndexes:
            self.constraints.addParallel(lines[pair[0]], lines[pair[1]])
            
    def makePerpendicular(self, lines, pairIndexes):
        for pair in pairIndexes:
            self.constraints.addPerpendicular(lines[pair[0]], lines[pair[1]])

    def makeCollinear(self, lines, pairIndexes):
        for pair in pairIndexes:
            self.constraints.addCollinear(lines[pair[0]], lines[pair[1]])

    def addLineLength(self, line:f.SketchLine, expr):
        dim = self.dimensions.addDistanceDimension(line.startSketchPoint, line.endSketchPoint, \
            f.DimensionOrientations.AlignedDimensionOrientation, line.startSketchPoint.geometry)
        dim.parameter.expression = expr

    def addTwoPointsDist(self, p0:f.SketchPoint, p1:f.SketchPoint, expr):
        dim = self.dimensions.addDistanceDimension(p0, p1, \
            f.DimensionOrientations.AlignedDimensionOrientation, p0.geometry)
        dim.parameter.expression = expr

    def addTwoLinesDist(self, line0:f.SketchLine, line1:f.SketchLine, expr):
        dim = self.dimensions.addOffsetDimension(line0, line1, line1.startSketchPoint.geometry)
        dim.parameter.expression = expr



    def projectLine(self, line:f.SketchLine):
        pp0 = self.sketch.project(line.startSketchPoint)
        pp1 = self.sketch.project(line.endSketchPoint)
        return self.sketchLines.addByTwoPoints(pp0[0], pp1[0])

    def addMidpointConstructionLine(self, baseLine:f.SketchLine, lengthExpr=None, toLeft=True):
        constraints = self.sketch.geometricConstraints
        path = "XM50LF50X" if toLeft else "XM50RF50X"
        lines = self.path.draw(baseLine, path)
        construction = lines[0]
        constraints.addPerpendicular(construction, baseLine)
        constraints.addMidPoint(construction.startSketchPoint, baseLine)
        if lengthExpr:
            self.addLineLength(construction, lengthExpr)
        else:
            constraints.addEqual(construction, baseLine)
        return lines[0]

    def duplicateLine(self, line:f.SketchLine):
        return self.sketchLines.addByTwoPoints(line.startSketchPoint, line.endSketchPoint)

    def addParallelLine(self, line:f.SketchLine, direction=1):
        p0 = line.startSketchPoint.geometry
        p1 = line.endSketchPoint.geometry
        rpx = (p1.y - p0.y) * direction # rotate to get perpendicular point to ensure direction
        rpy = (p1.x - p0.x) * -direction
        pp0 = core.Point3D.create(p0.x + rpx, p0.y + rpy, 0)
        pp1 = core.Point3D.create(p1.x + rpx, p1.y + rpy, 0)
        line2 = self.sketchLines.addByTwoPoints(pp0, pp1)
        return line2


    def getProfileAt(self, index:int):
        return self.sketch.profiles.item(index)

    def combineProfiles(self):
        result = core.ObjectCollection.create()
        for p in self.profiles:
            result.add(p)
        return result
        
    def findLargestProfile(self, profiles:core.ObjectCollection = None):
        collection = self.profiles if profiles == None else profiles
        index = 0
        largestArea = 0
        for i in range(collection.count):
            areaProps = collection.item(i).areaProperties(f.CalculationAccuracy.MediumCalculationAccuracy)
            if areaProps.area > largestArea:
                largestArea = areaProps.area
                index = i
        return collection.item(index)

    def findSmallestProfile(self, profiles:core.ObjectCollection = None):
        collection = self.profiles if profiles == None else profiles
        index = 0
        smallestArea = float('inf')
        for i in range(collection.count):
            areaProps = collection.item(i).areaProperties(f.CalculationAccuracy.MediumCalculationAccuracy)
            if areaProps.area < smallestArea:
                smallestArea = areaProps.area
                index = i
        return collection.item(index)

    def removeLargestProfile(self, profiles:core.ObjectCollection = None):
        collection = self.profiles if profiles == None else profiles
        result = self.findLargestProfile(collection)   
        collection.removeByItem(result)
        return result

    def removeSmallestProfile(self, profiles:core.ObjectCollection = None):
        collection = self.profiles if profiles == None else profiles
        result = self.findSmallestProfile(collection)   
        collection.removeByItem(result)
        return result
    