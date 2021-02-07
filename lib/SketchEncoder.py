
import adsk.core, adsk.fusion, adsk.cam, traceback
import os, math, re
from collections.abc import Iterable
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

        self.offsetParams = []

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

        # need to remove all unused points?

        self.data["Params"] = self.params
        self.data["Points"] = self.pointValues
        self.data["Chains"] = self.chains
        self.data["Constraints"] = self.constraints.values()
        self.data["Dimensions"] = self.dimensions.values()

        result = ("#Turtle Generated Data\n{\n")
        result += ("\'Params\':{\n" + self.encodeParams() + "},\n")
        result += ("\'Points\':[\n" + self.encodePoints(*self.data["Points"]) + "\n],\n")
        result += ("\'Chains\':[\n" + self.encodeChains(self.data["Chains"]) + "\n],\n")
        if len(self.data["Constraints"]) > 0:
            result += ("\'Constraints\':[\n\'" + "\',\'".join(self.data["Constraints"]) + "\'\n],\n")
        if len(self.data["Dimensions"]) > 0:
            result += ("\'Dimensions\':[\n\'" + "\',\'".join(self.data["Dimensions"]) + "\'\n]\n")
        result += ("}\n\n")


        TurtleUtils.setClipboardText(result)
        # f = open("sketchData.txt", "w")
        # f.write(result)
        # f.close()
        # command = 'type sketchData.txt | clip'
        # os.system(command)
        
        print(result)
        print("\n\nSketch data is now on clipboard.")
    

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
            econ = self.encodeConstraint(con)
            if econ != "":
                self.constraints[con.entityToken] = econ

    def parseAllDimensions(self):
        for dim in self.sketch.sketchDimensions:
            edim = self.encodeDimension(dim)
            if edim != "":
                self.dimensions[dim.entityToken] = edim
    

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
        print(tp)
        ctrn = "x" if curve.isConstruction else ""
        if tp is f.SketchLine:
            result = "L" + ctrn + self.encodeEntities(curve.startSketchPoint, curve.endSketchPoint)
        elif tp is f.SketchArc:
            pointOnLine = TurtleSketch.getMidpoint(curve)
            #return "A" + ctrn + self.encodeEntities(curve.centerSketchPoint, curve.startSketchPoint, curve.endSketchPoint) + self.encodeExpression(curve.geometry.endAngle)
            return "A" + ctrn + self.encodeEntities(curve.startSketchPoint) + self.encodeExpression(pointOnLine) + self.encodeEntities(curve.endSketchPoint) 
        elif tp is f.SketchCircle:
            result = "C" + ctrn + self.encodeEntities(curve.centerSketchPoint) + self.encodeExpression(curve.radius)
        elif tp is f.SketchEllipse:
            result = "E" + ctrn + self.encodeEntities(curve.centerSketchPoint, curve.majorAxisLine.startSketchPoint, curve.minorAxisLine.startSketchPoint)
        elif tp is f.SketchConicCurve:
            result = "O" + ctrn + self.encodeEntities(curve.startSketchPoint, curve.apexSketchPoint, curve.endSketchPoint) + self.encodeExpressions(curve.length)
        elif tp is f.SketchFittedSpline:
            result = "F" + ctrn + self.encodeEntities(curve.fitPoints) #note: control point splines are not supported, only fixed point splines work.
        else: 
            print("*** Curve not parsed: " + str(tp))
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
        elif(tp is f.ConcentricConstraint):
            cCon:f.ConcentricConstraint = con
            result = "CC" + self.encodeEntities(cCon.entityOne,cCon.entityTwo)
        elif(tp is f.CollinearConstraint):
            cCon:f.CollinearConstraint = con
            result = "CL" + self.encodeEntities(cCon.lineOne,cCon.lineTwo)
        elif(tp is f.CoincidentConstraint):
            cCon:f.CoincidentConstraint = con
            result = "CO" + self.encodeEntities(cCon.point, cCon.entity)
        elif(tp is f.MidPointConstraint):
            cCon:f.MidPointConstraint = con
            result = "MI" + self.encodeEntities(cCon.point,cCon.midPointCurve)
        elif(tp is f.OffsetConstraint):
            cCon:f.OffsetConstraint = con
            result += "OF" + self.encodeEntities(cCon.parentCurves, cCon.distance, cCon.childCurves)
        elif(tp is f.SmoothConstraint):
            cCon:f.SmoothConstraint = con
            result = "SM" + self.encodeEntities(cCon.curveOne, cCon.curveTwo)
        elif(tp is f.SymmetryConstraint):
            cCon:f.SymmetryConstraint = con
            result = "SY" + self.encodeEntities(cCon.entityOne,cCon.entityTwo,cCon.symmetryLine)
        elif(tp is f.TangentConstraint):
            cCon:f.TangentConstraint = con
            result = "TA" + self.encodeEntities(cCon.curveOne, cCon.curveTwo)
        else:
            # not supported?
            # PolygonConstraint, RectangularPatternConstraint, CircularPatternConstraint
            print("*** Constraint not parsed: " + str(tp))
        return result


    def encodeDimension(self, dim:f.SketchDimension):
        result = ""
        tp = type(dim)
        if(tp == f.SketchLinearDimension):
            tdim:f.SketchLinearDimension = dim # DistanceDimension
            result = "SLD" + self.encodeEntities(tdim.entityOne,tdim.entityTwo) + self.encodeExpressions(tdim.parameter, tdim.textPosition)

        elif(tp == f.SketchOffsetDimension):
            tdim:f.SketchOffsetDimension = dim
            result = "SOD" + self.encodeEntities(tdim.line,tdim.entityTwo) + self.encodeExpressions(tdim.parameter, tdim.textPosition)

        elif(tp == f.SketchAngularDimension):
            tdim:f.SketchAngularDimension = dim
            result = "SAD" + self.encodeEntities(tdim.lineOne,tdim.lineTwo) + self.encodeExpressions(tdim.parameter, tdim.textPosition)

        elif(tp == f.SketchDiameterDimension):
            tdim:f.SketchDiameterDimension = dim
            result = "SDD" + self.encodeEntities(tdim.entity) + self.encodeExpressions(tdim.parameter, tdim.textPosition)

        elif(tp == f.SketchRadialDimension):
            tdim:f.SketchRadialDimension = dim
            result = "SRD" + self.encodeEntities(tdim.entity) + self.encodeExpressions(tdim.parameter, tdim.textPosition)

        elif(tp == f.SketchEllipseMajorRadiusDimension):
            tdim:f.SketchEllipseMajorRadiusDimension = dim
            result = "SMA" + self.encodeEntities(tdim.ellipse) + self.encodeExpressions(tdim.parameter, tdim.textPosition)

        elif(tp == f.SketchEllipseMinorRadiusDimension):
            tdim:f.SketchEllipseMinorRadiusDimension = dim
            result = "SMI" + self.encodeEntities(tdim.ellipse) + self.encodeExpressions(tdim.parameter, tdim.textPosition)

        elif(tp == f.SketchConcentricCircleDimension):
            tdim:f.SketchConcentricCircleDimension = dim
            result = "SCC" + self.encodeEntities(tdim.circleOne,tdim.circleTwo) + self.encodeExpressions(tdim.parameter, tdim.textPosition)

        elif(tp == f.SketchOffsetCurvesDimension):
            tdim:f.SketchOffsetCurvesDimension = dim
            result = "SOC" + self.encodeEntities(tdim.offsetConstraint) + self.encodeExpressions(tdim.parameter, tdim.textPosition)

        else:
            print("*** Dimension not parsed: " + str(tp))

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
        elif type(entity) == f.SketchPointList: # splines
            result = "s"
            sep = ""
            for c in entity:
                result += sep + str(self.pointValues.index(c))
                sep = "|"
        elif isinstance(entity, Iterable): # curves
            result = "a"
            sep = ""
            for c in entity:
                result += sep + str(self.curveValues.index(c))
                sep = "|"
        elif type(entity) == f.OffsetConstraint:
            result = "o" + str(list(self.constraints).index(entity.entityToken))
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
