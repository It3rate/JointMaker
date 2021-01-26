
import adsk.core, adsk.fusion, traceback
import os, math, re, sys
f = adsk.fusion
core = adsk.core

class TurtlePath:

    def __init__(self, sketch:f.Sketch):
        self.sketch:f.Sketch = sketch
        self.dimensions = sketch.sketchDimensions
        self.constraints:f.GeometricConstraints = self.sketch.geometricConstraints
        
    def draw(self, constructionLine:f.SketchLine, path:str, isClosed=False, makeCurrent=True):
        self.contructionLine:f.SketchLine = constructionLine
        cmds = re.findall("[#FLRMX][0-9\-\.]*", path) #lazy number :)
        startPt = self.contructionLine.startSketchPoint.geometry
        endPt = self.contructionLine.endSketchPoint.geometry
        difX = endPt.x - startPt.x
        difY = endPt.y - startPt.y
        length = math.sqrt(difX * difX + difY * difY)
        angle = math.atan2(difY,difX) + math.pi * 4.0
        curPt:f.SketchPoint = self.contructionLine.startSketchPoint
        lastLine:f.SketchLine = self.contructionLine
        lines = []
        cmd:str
        num:float
        for cmd in cmds:
            num = float(cmd[1:]) if len(cmd) > 1 else 90
            if cmd.startswith('F'):
                p2 = self.getEndPoint(curPt.geometry, angle, (num / 100.0) * length)
                lastLine = self.sketch.sketchCurves.sketchLines.addByTwoPoints(curPt, p2)
                lines.append(lastLine)
                curPt = lastLine.endSketchPoint
            elif cmd.startswith('L'):
                angle -= num/180.0 * math.pi
            elif cmd.startswith('R'):
                angle += num/180.0 * math.pi
            elif cmd.startswith('M'):
                curPt = self.sketch.sketchPoints.add(self.getEndPoint(curPt.geometry, angle, (num / 100.0) * length))
            elif cmd.startswith('X'):
                lastLine.isConstruction = True
            elif cmd.startswith('#'):
                pass # comment number
        if isClosed:
            lines[0].startSketchPoint.merge(lines[len(lines) - 1].endSketchPoint)
        if makeCurrent:
            self.curLines = lines
        return lines


# ME VH PA PE EQ CO SY LL
    def setConstraints(self, constraintList):
        # consts = [
        #     "ME", [0,0,13,1, 9,0,14,1],
        #     "PA", [baseLine, 0],
        #     "EQ", [baseLine, 4],
        #     "CO", [0,8, 2,6],
        #     "PA", [0,4, 1,7, 3,5, 9,13, 11,13, 12,10],
        #     "SY", [9,13,construction, 1,7,construction, 3,5,construction],
        #     "PE", [2,3, 9,10]
        pairs = [constraintList[i:i + 2] for i in range(0, len(constraintList), 2)]

        for pair in pairs:
            cmd:str = pair[0].upper()
            data = pair[1]

            if cmd.startswith('ME'): # MERGE
                for valsIndex in range(0, len(data), 4):
                    pts = self.grabPoints(data, valsIndex, 4)
                    self.mergePoints(pts[0], pts[1])

            elif cmd.startswith('VH'): # VERTICAL HORIZONTAL
                for valsIndex in range(0, len(data), 1):
                    lines = self.grabLines(data, valsIndex, 1)
                    self.makeVertHorz(lines[0], lines[1])

            elif cmd.startswith('PA'): # PARALLEL
                for valsIndex in range(0, len(data), 2):
                    lines = self.grabLines(data, valsIndex, 2)
                    self.makeParallel(lines[0], lines[1])

            elif cmd.startswith('PE'): # PERPENDICULAR
                for valsIndex in range(0, len(data), 2):
                    lines = self.grabLines(data, valsIndex, 2)
                    self.makePerpendicular(lines[0], lines[1])
                    
            elif cmd.startswith('EQ'): # EQUAL
                for valsIndex in range(0, len(data), 2):
                    lines = self.grabLines(data, valsIndex, 2)
                    self.makeEqual(lines[0], lines[1])

            elif cmd.startswith('CO'): # COLLINEAR
                for valsIndex in range(0, len(data), 2):
                    lines = self.grabLines(data, valsIndex, 2)
                    self.makeCollinear(lines[0], lines[1])

            elif cmd.startswith('MI'): # MIDPOINT
                for valsIndex in range(0, len(data), 3):
                    pts = self.grabPoints(data, valsIndex, 2)
                    lines = self.grabLines(data, valsIndex + 2, 1)
                    self.makeMidpoint(pts[0], lines[0])
                    
            elif cmd.startswith('SY'): # SYMETRIC
                for valsIndex in range(0, len(data), 3):
                    lines = self.grabLines(data, valsIndex, 3)
                    self.makeSymetric(lines[0], lines[1], lines[2])

            elif cmd.startswith('LL'): # LINE LENGTH
                for valsIndex in range(0, len(data), 2):
                    lines = self.grabLines(data, valsIndex, 1)
                    expr = data[valsIndex + 1]
                    self.setLineLength(lines[0], expr)
                    
            elif cmd.startswith('LD'): # LINES DISTANCE
                for valsIndex in range(0, len(data), 3):
                    lines = self.grabLines(data, valsIndex, 2)
                    expr = data[valsIndex + 2]
                    self.setTwoLinesDist(lines[0], lines[1], expr)

            elif cmd.startswith('PD'): # POINTS DISTANCE
                for valsIndex in range(0, len(data), 3):
                    p0 = data[valsIndex + 0]
                    p1 = data[valsIndex + 1]
                    expr = data[valsIndex + 2]
                    self.setTwoPointsDist(p0, p1, expr)



    def grabLines(self, indexes, start:int, count:int):
        result = []
        for i in range(0, count):
            val = indexes[start + i]
            line = self.curLines[val] if (type(val) == int) else val # is index or actual line
            result.append(line)
        return result

    def grabPoints(self, indexes, start:int, count:int):
        result = []
        for i in range(0, count, 2):
            val = indexes[start + i]
            line = self.curLines[val] if (type(val) == int)  else val
            p0:SketchPoint = line.startSketchPoint if indexes[start + i + 1] == 0 else line.endSketchPoint
            result.append(p0)
        return result



    def mergePoints(self, p0:f.SketchPoint, p1:f.SketchPoint):
        p0.merge(p1)
    
    def makeVertHorz(self, a:f.SketchLine):
        sp = self.curLines[index].startSketchPoint.geometry
        ep = self.curLines[index].endSketchPoint.geometry
        if(abs(sp.x - ep.x) < abs(sp.y - ep.y)):
            self.constraints.addVertical(self.curLines[index])
        else:
            self.constraints.addHorizontal(self.curLines[index])

    def makeParallel(self, a:f.SketchLine, b:f.SketchLine):
        self.constraints.addParallel(a, b)
            
    def makePerpendicular(self, a:f.SketchLine, b:f.SketchLine):
        self.constraints.addPerpendicular(a, b)

    def makeCollinear(self,  a:f.SketchLine, b:f.SketchLine):
        self.constraints.addCollinear(a, b)

    def makeEqual(self, a:f.SketchLine, b:f.SketchLine):
        self.constraints.addEqual(a, b)
        
    def makeSymetric(self, left:f.SketchLine, right:f.SketchLine, center:f.SketchLine):
        self.constraints.addSymmetry(left, right, center)

    def makeMidpoint(self, point:f.SketchPoint, line:f.SketchLine):
        self.constraints.addMidPoint(point, line)

    def setLineLength(self, line:f.SketchLine, expr:str):
        dim = self.dimensions.addDistanceDimension(line.startSketchPoint, line.endSketchPoint, \
            f.DimensionOrientations.AlignedDimensionOrientation, line.startSketchPoint.geometry)
        dim.parameter.expression = expr

    def setTwoLinesDist(self, line0:f.SketchLine, line1:f.SketchLine, expr):
        dim = self.dimensions.addOffsetDimension(line0, line1, line1.startSketchPoint.geometry)
        dim.parameter.expression = expr


    def setTwoPointsDist(self, p0:f.SketchPoint, p1:f.SketchPoint, expr):
        dim = self.dimensions.addDistanceDimension(p0, p1, \
            f.DimensionOrientations.AlignedDimensionOrientation, p0.geometry)
        dim.parameter.expression = expr



    def addMidpointConstructionLine(self, baseLine:f.SketchLine, lengthExpr, toLeft=True):
        path = "XM1L90F1X" if toLeft else "XM1R90F1X"
        lines = self.draw(baseLine, path, False)
        construction = lines[0]
        self.constraints.addMidPoint(construction.startSketchPoint, baseLine)
        #self.constraints.addPerpendicular(construction, baseLine)
        self.setLineLength(self.sketch, construction, lengthExpr)
        return lines[0]
        
    def duplicateLine(self, line:f.SketchLine):
        line = self.sketchLines.addByTwoPoints(line.startSketchPoint, line.endSketchPoint)
        return line

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