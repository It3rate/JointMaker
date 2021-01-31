
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
        self.curves = {}
        self.curveKeys = []
        self.curveValues = []
        self.chains = []
        self.constraints = {}
        self.dimensions = {}
        self.encodeFromSketch()

        TurtleUtils.selectEntity(self.sketch)
        

    def encodeFromSketch(self):
        self.encodeAllPoints()
        self.pointKeys = list(self.points)
        self.pointValues = list(self.points.values())
        TurtlePath.printPoints(self.points.values())

        chains = self.encodeAllChains()
        self.curveKeys = list(self.curves)
        self.curveValues = list(self.curves.values())
        index = 0
        for chain in chains:
            comma = ""
            print(str(index) + "# ", end="")
            for curveIndex in chain:
                curve:f.SketchCurve = self.curveValues[curveIndex]
                print(comma + self.encodeCurve(curve), end="")
                comma = ","
                index += 1
            print("")

        print("\nconstraints:")
        self.encodeAllConstraints()
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

    def encodeAllConstraints(self):
        dims = []
        for con in self.sketch.geometricConstraints:
            self.constraints[con.entityToken] = self.encodeConstraint(con)

    def encodeAllDimensions(self):
        dims = []
        for dim in self.sketch.sketchDimensions:
            self.dimensions[dim.entityToken] = self.encodeDimension(dim)
        
    def appendConnectedCurves(self, baseLine:f.SketchLine, tokens:list):
        connected = self.sketch.findConnectedCurves(baseLine)
        result = []
        for curve in connected:
            self.curves[curve.entityToken] = curve
            result.append(len(self.curves) - 1)
            tokens.append(curve.entityToken)
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

    def encodeCurve(self, curve:f.SketchCurve):
        result = ""
        tp = type(curve)
        if tp is f.SketchLine:
            result = "L" + self.encodeEntities(curve.startSketchPoint, curve.endSketchPoint)
        elif tp is f.SketchArc:
            return "A" + self.encodeEntities(curve.startSketchPoint, curve.centerSketchPoint, curve.endSketchPoint)
        elif tp is f.SketchCircle:
            result = "C" + self.encodeEntities(curve.centerSketchPoint) + self.encodeExpression(curve.radius)
        elif tp is f.SketchEllipse:
            result = "E" + self.encodeEntities(curve.centerSketchPoint) + self.encodeExpressions(curve.majorAxis, curve.majorAxisRadius, curve.minorAxisRadius)
        return result
    #  SketchConicCurve SketchEllipticalArc SketchFittedSpline SketchFixedSpline 

    def encodeConstraint(self, con:f.GeometricConstraint):
        result = ""
        cType = type(con)
        if(cType is f.VerticalConstraint or cType is f.HorizontalConstraint):
            result = "VH" + self.encodeEntity(con.line)
        elif(cType is f.ParallelConstraint):
            cCon:f.ParallelConstraint = con
            result = "PA" + self.encodeEntity(cCon.lineOne) + self.encodeEntity(cCon.lineTwo)
        elif(cType is f.PerpendicularConstraint):
            cCon:f.PerpendicularConstraint = con
            result = "PE" + self.encodeEntity(cCon.lineOne) + self.encodeEntity(cCon.lineTwo)
        elif(cType is f.EqualConstraint):
            cCon:f.EqualConstraint = con
            result = "EQ" + self.encodeEntity(cCon.curveOne) + self.encodeEntity(cCon.curveTwo)
        elif(cType is f.CollinearConstraint):
            cCon:f.CollinearConstraint = con
            result = "CO" + self.encodeEntity(cCon.lineOne) + self.encodeEntity(cCon.lineTwo)
        elif(cType is f.SymmetryConstraint):
            cCon:f.SymmetryConstraint = con
            result = "SY" + self.encodeEntity(cCon.entityOne) + self.encodeEntity(cCon.entityTwo) + self.encodeEntity(cCon.symmetryLine)
        elif(cType is f.MidPointConstraint):
            cCon:f.MidPointConstraint = con
            result = "MI" + self.encodeEntity(cCon.midPointCurve) + self.encodeEntity(cCon.point)
            
        print(result)
        return result


    def encodeDimension(self, dim:f.SketchDimension):
        result = ""
        if(type(dim) == f.SketchLinearDimension):
            tdim:f.SketchLinearDimension = dim
            result = "SLD" + self.encodeEntity(tdim.entityOne) + self.encodeEntity(tdim.entityOne) + self.encodeExpression(tdim.parameter)

        elif(type(dim) == f.SketchOffsetDimension):
            tdim:f.SketchOffsetDimension = dim
            result = "SOD" + self.encodeEntity(tdim.line) + self.encodeExpression(tdim.parameter)

        elif(type(dim) == f.SketchAngularDimension):
            tdim:f.SketchAngularDimension = dim
            result = "SAD" + self.encodeEntity(tdim.lineOne) + self.encodeEntity(tdim.lineTwo) + self.encodeExpression(tdim.parameter)

        elif(type(dim) == f.SketchDiameterDimension):
            tdim:f.SketchDiameterDimension = dim
            result = "SDD" + self.encodeEntity(tdim.entity) + self.encodeExpression(tdim.parameter)

        elif(type(dim) == f.SketchRadialDimension):
            tdim:f.SketchRadialDimension = dim
            result = "SRD" + self.encodeEntity(tdim.entity) + self.encodeExpression(tdim.parameter)

        elif(type(dim) == f.SketchEllipseMajorRadiusDimension):
            tdim:f.SketchEllipseMajorRadiusDimension = dim
            result = "SMA" + self.encodeEntity(tdim.ellipse) + self.encodeExpression(tdim.parameter)

        elif(type(dim) == f.SketchEllipseMinorRadiusDimension):
            tdim:f.SketchEllipseMinorRadiusDimension = dim
            result = "SMI" + self.encodeEntity(tdim.ellipse) + self.encodeExpression(tdim.parameter)

        elif(type(dim) == f.SketchConcentricCircleDimension):
            tdim:f.SketchConcentricCircleDimension = dim
            result = "SCC" + self.encodeEntity(tdim.circleOne) +self.encodeEntity(tdim.circleTwo) + self.encodeExpression(tdim.parameter)

            # def addDistanceDimension(self, pointOne, pointTwo, orientation, textPoint, isDriving):
            # def addOffsetDimension(self, line, entityTwo, textPoint, isDriving): # also SketchOffsetCurvesDimension
            # def addAngularDimension(self, lineOne, lineTwo, textPoint, isDriving):
            # def addDiameterDimension(self, entity, textPoint, isDriving):
            # def addRadialDimension(self, entity, textPoint, isDriving):
            # def addEllipseMajorRadiusDimension(self, ellipse, textPoint, isDriving):
            # def addEllipseMinorRadiusDimension(self, ellipse, textPoint, isDriving):
            # def addConcentricCircleDimension(self, circleOne, circleTwo, textPoint, isDriving):

        print(result)
        return result

    def encodeEntities(self, *points):
        result = ""
        for pt in points:
            result += self.encodeEntity(pt)
        return result

    def encodeEntity(self, entity):
        result = ""
        if entity in self.pointValues:
            result = "p" + str(self.pointValues.index(entity))
        elif entity in self.curveValues:
            result = "c" + str(self.curveValues.index(entity))
        return result

    def encodeExpressions(self, *expressions):
        result = ""
        for expr in expressions:
            result += self.encodeExpression(expr)
        return result

    def encodeExpression(self, expr):
        tp = type(expr)
        result = "v"
        if tp is float or tp is int:
            result += TurtleUtils.round(expr)
        elif tp is f.ModelParameter:
            result += str(expr.expression).replace(" ", "")
        elif tp is core.Point2D or tp is core.Vector2D:
            pt:core.Point2D = expr
            result += "["+TurtleUtils.round(expr.x)+","+TurtleUtils.round(expr.y)+"]"
        elif tp is core.Point3D or tp is core.Vector3D:
            pt:core.Point3D = expr
            result += "["+TurtleUtils.round(expr.x)+","+TurtleUtils.round(expr.y)+","+TurtleUtils.round(expr.z)+"]"
        return result

