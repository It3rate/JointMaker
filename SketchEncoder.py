
import adsk.core, adsk.fusion, adsk.cam, traceback
import os, math, re
from .TurtleUtils import TurtleUtils
from .TurtleComponent import TurtleComponent
from .TurtleSketch import TurtleSketch
from .TurtleParams import TurtleParams
from .TurtlePath import TurtlePath
from .TurtleLayers import TurtleLayers

f,core,app,ui,design,root = TurtleUtils.initGlobals()

class SketchEncoder:
    def __init__(self):
        self.sketch:f.Sketch = TurtleUtils.ensureSelectionIsType(f.Sketch)
        if not self.sketch:
            return
        
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
        os.system('cls')
        self.data = {}
        tparams = TurtleParams.instance()
        self.usedParams = []
        self.params = tparams.getUserParams()

        self.parseAllPoints()
        self.pointKeys = list(self.points)
        self.pointValues = list(self.points.values())

        self.chains = self.parseAllChains()
        self.curveKeys = list(self.curves)
        self.curveValues = list(self.curves.values())

        self.parseAllConstraints()
        self.parseAllDimensions()

        self.data["Params"] = self.params
        self.data["Points"] = self.pointValues
        self.data["Chains"] = self.chains
        self.data["Constraints"] = self.constraints.values()
        self.data["Dimensions"] = self.dimensions.values()

        print("{")
        print("\'Params\':{\n" + self.encodeParams() + "},")
        print("\'Points\':[\n" + self.encodePoints(*self.data["Points"]) + "\n],")
        print("\'Chains\':[\n" + self.encodeChains(self.data["Chains"]) + "\n],")
        print("\'Constraints\':[\n\'" + "\',\'".join(self.data["Constraints"]) + "\'\n],")
        print("\'Dimensions\':[\n\'" + "\',\'".join(self.data["Dimensions"]) + "\'\n]")
        print("}")

        
        #TurtlePath.printLines(chain)
    

    def parseAllPoints(self):
        for point in self.sketch.sketchPoints:
            self.points[point.entityToken] = point

    def parseAllChains(self):
        tokens = []
        chains = []
        for line in self.sketch.sketchCurves:
            if not line.entityToken in tokens:
                chains.append(self.appendConnectedCurves(line, tokens))
        return chains

    def parseAllConstraints(self):
        for con in self.sketch.geometricConstraints:
            self.constraints[con.entityToken] = self.encodeConstraint(con)

    def parseAllDimensions(self):
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

    def encodeParams(self):
        result = ""
        for key in self.usedParams:
            result += "\'" + key + "\':\'" + self.params[key] + "\'\n"
        return result

    def encodeCurve(self, curve:f.SketchCurve):
        result = ""
        tp = type(curve)
        ctrn = "x" if curve.isConstruction else ""
        if tp is f.SketchLine:
            result = "L" + ctrn + self.encodeEntities(curve.startSketchPoint, curve.endSketchPoint)
        elif tp is f.SketchArc:
            return "A" + ctrn + self.encodeEntities(curve.centerSketchPoint, curve.startSketchPoint) + self.encodeExpression(curve.geometry.endAngle)
        elif tp is f.SketchCircle:
            result = "C" + ctrn + self.encodeEntities(curve.centerSketchPoint) + self.encodeExpression(curve.radius)
        elif tp is f.SketchEllipse:
            result = "E" + ctrn + self.encodeEntities(curve.centerSketchPoint, curve.majorAxisLine.startSketchPoint, curve.minorAxisLine.startSketchPoint)
        elif tp is f.SketchConicCurve:
            result = "O" + ctrn + self.encodeEntities(curve.startSketchPoint, curve.apexSketchPoint, curve.endSketchPoint) + self.encodeExpressions(curve.length)
        return result
    #  SketchConicCurve SketchEllipticalArc SketchFittedSpline SketchFixedSpline 

    def encodeConstraint(self, con:f.GeometricConstraint):
        result = ""
        tp = type(con)
        if(tp is f.VerticalConstraint or tp is f.HorizontalConstraint):
            result = "VH" + self.encodeEntity(con.line)
        elif(tp is f.ParallelConstraint):
            cCon:f.ParallelConstraint = con
            result = "PA" + self.encodeEntities(cCon.lineOne,cCon.lineTwo)
        elif(tp is f.PerpendicularConstraint):
            cCon:f.PerpendicularConstraint = con
            result = "PE" + self.encodeEntities(cCon.lineOne,cCon.lineTwo)
        elif(tp is f.EqualConstraint):
            cCon:f.EqualConstraint = con
            result = "EQ" + self.encodeEntities(cCon.curveOne,cCon.curveTwo)
        elif(tp is f.CollinearConstraint):
            cCon:f.CollinearConstraint = con
            result = "CL" + self.encodeEntities(cCon.lineOne,cCon.lineTwo)
        elif(tp is f.CoincidentConstraint):
            cCon:f.CoincidentConstraint = con
            result = "CO" + self.encodeEntities(cCon.point, cCon.entity)
        elif(tp is f.SymmetryConstraint):
            cCon:f.SymmetryConstraint = con
            result = "SY" + self.encodeEntities(cCon.entityOne,cCon.entityTwo,cCon.symmetryLine)
        elif(tp is f.MidPointConstraint):
            cCon:f.MidPointConstraint = con
            result = "MI" + self.encodeEntities(cCon.point,cCon.midPointCurve)
        elif(tp is f.TangentConstraint):
            cCon:f.TangentConstraint = con
            result = "TA" + self.encodeEntities(cCon.curveOne, cCon.curveTwo)
        else:
            print("*** Constraint not parsed: " + str(tp))
        return result


    def encodeDimension(self, dim:f.SketchDimension):
        result = ""
        tp = type(dim)
        if(tp == f.SketchLinearDimension):
            tdim:f.SketchLinearDimension = dim
            result = "SLD" + self.encodeEntities(tdim.entityOne,tdim.entityTwo) + self.encodeExpression(tdim.parameter)

        elif(tp == f.SketchOffsetDimension):
            tdim:f.SketchOffsetDimension = dim
            result = "SOD" + self.encodeEntities(tdim.line,tdim.entityTwo) + self.encodeExpression(tdim.parameter)

        elif(tp == f.SketchAngularDimension):
            tdim:f.SketchAngularDimension = dim
            result = "SAD" + self.encodeEntities(tdim.lineOne,tdim.lineTwo) + self.encodeExpression(tdim.parameter)

        elif(tp == f.SketchDiameterDimension):
            tdim:f.SketchDiameterDimension = dim
            result = "SDD" + self.encodeEntities(tdim.entity) + self.encodeExpression(tdim.parameter)

        elif(tp == f.SketchRadialDimension):
            tdim:f.SketchRadialDimension = dim
            result = "SRD" + self.encodeEntities(tdim.entity) + self.encodeExpression(tdim.parameter)

        elif(tp == f.SketchEllipseMajorRadiusDimension):
            tdim:f.SketchEllipseMajorRadiusDimension = dim
            result = "SMA" + self.encodeEntities(tdim.ellipse) + self.encodeExpression(tdim.parameter)

        elif(tp == f.SketchEllipseMinorRadiusDimension):
            tdim:f.SketchEllipseMinorRadiusDimension = dim
            result = "SMI" + self.encodeEntities(tdim.ellipse) + self.encodeExpression(tdim.parameter)

        elif(tp == f.SketchConcentricCircleDimension):
            tdim:f.SketchConcentricCircleDimension = dim
            result = "SCC" + self.encodeEntities(tdim.circleOne,tdim.circleTwo) + self.encodeExpression(tdim.parameter)
        else:
            print("*** Dimension not parsed: " + str(tp))

            # def addDistanceDimension(self, pointOne, pointTwo, orientation, textPoint, isDriving):
            # def addOffsetDimension(self, line, entityTwo, textPoint, isDriving): # also SketchOffsetCurvesDimension
            # def addAngularDimension(self, lineOne, lineTwo, textPoint, isDriving):
            # def addDiameterDimension(self, entity, textPoint, isDriving):
            # def addRadialDimension(self, entity, textPoint, isDriving):
            # def addEllipseMajorRadiusDimension(self, ellipse, textPoint, isDriving):
            # def addEllipseMinorRadiusDimension(self, ellipse, textPoint, isDriving):
            # def addConcentricCircleDimension(self, circleOne, circleTwo, textPoint, isDriving):

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
        else:
            result = self.encodeExpression(entity)

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
            result += "[" + TurtleUtils.round(expr) + "]"
        elif tp is f.ModelParameter:
            p = str(expr.expression).replace(" ", "")
            result += p
            if (p in self.params) and (not p in self.usedParams):
                self.usedParams.append(p)
        else:
            result += self.encodePoint(expr)
        return result

    def encodePoints(self, *points):
        result = ""
        comma = ""
        for pt in points:
            result += comma + self.encodePoint(pt)
            comma=","
        return result

    def encodePoint(self, pt:f.SketchPoint):  
        tp = type(pt)
        result = ""
        if tp is f.SketchPoint:
            result += "["+TurtleUtils.round(pt.geometry.x)+","+TurtleUtils.round(pt.geometry.y)+"]"
        elif tp is core.Point2D or tp is core.Vector2D:
            result += "["+TurtleUtils.round(pt.x)+","+TurtleUtils.round(pt.y)+"]"
        elif tp is core.Point3D or tp is core.Vector3D:
            result += "["+TurtleUtils.round(pt.x)+","+TurtleUtils.round(pt.y)+","+TurtleUtils.round(pt.z)+"]"
        return result
        
    def encodeChains(self, chains):
        result = []
        index = 0
        for chain in chains:
            startIndex = index
            s = "\'"
            comma = ""
            for curveIndex in chain:
                curve:f.SketchCurve = self.curveValues[curveIndex]
                s += comma + self.encodeCurve(curve)
                comma = " "
                index += 1
            rng = str(startIndex) + "-" + str(index - 1) if index - 1 > startIndex else str(startIndex)
            s += "\', # " + rng
            result.append(s)
        return "\n".join(result)
