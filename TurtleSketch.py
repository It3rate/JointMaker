
import adsk.core, adsk.fusion, traceback
import os, math, re, sys
from .TurtlePath import TurtlePath

f = adsk.fusion
core = adsk.core

class TurtleSketch:
    def __init__(self, sketchTarget:f.Sketch):
        self.sketch:f.Sketch = sketchTarget
        self.component = sketchTarget.parentComponent
        self.constraints:f.GeometricConstraints = sketchTarget.geometricConstraints
        self.dimensions:f.SketchDimensions = sketchTarget.sketchDimensions
        self.sketchLines:f.SketchLines = sketchTarget.sketchCurves.sketchLines
        self.profiles:f.Profiles = sketchTarget.profiles
        self.path:TurtlePath = TurtlePath(self.sketch)



    def draw(self, line:f.SketchLine, *data:str, isClosed=False):
        data = " ".join(data)
        return self.path.draw(line, data, isClosed)

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

    def addPointsDist(self, p0:f.SketchPoint, p1:f.SketchPoint, expr):
        dim = self.dimensions.addDistanceDimension(p0, p1, \
            f.DimensionOrientations.AlignedDimensionOrientation, p0.geometry)
        dim.parameter.expression = expr

    def addTwoLinesDist(self, line0:f.SketchLine, line1:f.SketchLine, expr):
        dim = self.dimensions.addOffsetDimension(line0, line1, line1.startSketchPoint.geometry)
        dim.parameter.expression = expr

    def createRect(self, baseLine:f.SketchLine, widthExpr, sideOffsetExpr = None):
        opp:f.SketchLine = self.addParallelLine(self.sketch, baseLine)

        self.constraints.addEqual(baseLine, opp)
        dim = self.dimensions.addDistanceDimension(baseLine.startSketchPoint, opp.startSketchPoint, \
            f.DimensionOrientations.AlignedDimensionOrientation, baseLine.startSketchPoint.geometry)
        dim.parameter.expression = widthExpr

        side0 = self.sketchLines.addByTwoPoints(baseLine.startSketchPoint, opp.startSketchPoint)
        self.constraints.addPerpendicular(baseLine, side0)

        side1 = self.sketchLines.addByTwoPoints(baseLine.endSketchPoint, opp.endSketchPoint)
        self.constraints.addPerpendicular(baseLine, side1)
        self.constraints.addPerpendicular(opp, side1)
        return [baseLine, side0, opp, side1]
    
    def projectLine(self, line:f.SketchLine):
        pp0 = self.sketch.project(line.startSketchPoint)
        pp1 = self.sketch.project(line.endSketchPoint)
        return self.sketchLines.addByTwoPoints(pp0[0], pp1[0])

    def combineProfiles(self):
        result = core.ObjectCollection.create()
        for p in self.profiles:
            result.add(p)
        return result
        
    def findLargestProfile(self):
        index = 0
        largestArea = 0
        for i in range(self.profiles.count):
            areaProps = self.profiles.item(i).areaProperties(f.CalculationAccuracy.MediumCalculationAccuracy)
            if areaProps.area > largestArea:
                largestArea = areaProps.area
                index = i
        return self.profiles.item(index)

    def findSmallestProfile(self):
        index = 0
        smallestArea = float('inf')
        for i in range(self.profiles.count):
            areaProps = self.profiles.item(i).areaProperties(f.CalculationAccuracy.MediumCalculationAccuracy)
            if areaProps.area < smallestArea:
                smallestArea = areaProps.area
                index = i
        return self.profiles.item(index)

    def removeLargestProfile(self):
        result = self.findLargestProfile()   
        self.profiles.removeByItem(result)
        return result

    def removeSmallestProfile(self):
        result = self.findLargestProfile()   
        self.profiles.removeByItem(result)
        return result

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
        #self.sketch.geometricself.constraints.addParallel(line, line2)
        return line2
    
    def getEndPoint(self, start:core.Point3D, angle:float, distance:float):
        x = start.x + distance * math.cos(angle)
        y = start.y + distance * math.sin(angle) 
        return core.Point3D.create(x, y, 0)

    def isOnLine(self, a:core.Point3D, line:f.SketchLine):
        b = line.startSketchPoint.geometry
        c = line.endSketchPoint.geometry
        cross = (c.y - a.y) * (b.x - a.x) - (c.x - a.x) * (b.y - a.y)
        return abs(cross) < 0.0001

    def distanceToLine(self, a:core.Point3D, line:f.SketchLine):
        b = line.startSketchPoint.geometry
        c = line.endSketchPoint.geometry
        x_diff = c.x - b.x
        y_diff = c.y - b.y
        num = abs(y_diff * a.x - x_diff * a.y + c.x*b.y - c.y*b.x)
        den = math.sqrt(y_diff**2 + x_diff**2)
        return num / den