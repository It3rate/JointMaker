
import adsk.core, adsk.fusion, adsk.cam, traceback
import os, math, re, ast
from collections.abc import Iterable
from .TurtleUtils import TurtleUtils
from .TurtleComponent import TurtleComponent
from .TurtleSketch import TurtleSketch
from .TurtleParams import TurtleParams
from .TurtlePath import TurtlePath
from .TurtleLayers import TurtleLayers

f,core,app,ui,design,root = TurtleUtils.initGlobals()

class SketchDecoder:
    def __init__(self, data):
        self.sketch:f.Sketch = TurtleUtils.ensureSelectionIsType(f.Sketch)
        if not self.sketch:
            return
        self.tcomponent = TurtleComponent.createFromSketch(self.sketch)
        self.tparams = TurtleParams.instance()
        
        self.decodeFromSketch(data)

        TurtleUtils.selectEntity(self.sketch)

    def decodeFromSketch(self, data):
        if "Params" in data:
            params = data["Params"]
            for p in params:
                self.tparams.addParam(p, params[p])
        else:
            params = {}

        self.offsetRefs = {}

        pointValues = data["Points"] if "Points" in data else []
        chains = data["Chains"] if "Chains" in data else []
        constraints = data["Constraints"] if "Constraints" in data else []
        dimensions = data["Dimensions"] if "Dimensions" in data else []

        self.points = self.generatePoints(pointValues)
        self.curves = self.generateCurves(chains)
        self.constraints = self.generateConstraints(constraints)
        self.dimensions = self.generateDimensions(dimensions)

    def generatePoints(self, ptVals):
        result = []
        for pv in ptVals:
            result.append(self.sketch.sketchPoints.add(core.Point3D.create(pv[0], pv[1], 0)))
        return result

    def generateCurves(self, chains):
        result = []
        sketchCurves = self.sketch.sketchCurves
        for chain in chains:
            segs = chain.split(" ")
            for seg in segs:
                # can't capture repeating groups with re, so max 4 params. Use pip regex to improve
                parse = re.findall(r"([LACEOF])(x?)([pvas][0-9\[\]\.\-,|]*)([pvas][0-9\[\]\.\-,|]*)?([pvas][0-9\[\]\.\-,|]*)?([pvas][0-9\[\]\.\-,|]*)?", seg)[0]
                kind = parse[0]
                isConstruction = parse[1] == "x"
                params = self.parseParams(parse[2:])
                curve = None
                if kind == "L":
                    curve = sketchCurves.sketchLines.addByTwoPoints(params[0], params[1])
                elif kind == "A":
                    curve = sketchCurves.sketchArcs.addByThreePoints(params[0], self.asPoint3D(params[1]), params[2])
                elif kind == "C":
                    curve = sketchCurves.sketchCircles.addByCenterRadius(params[0], params[1][0])
                elif kind == "E":
                    curve = sketchCurves.sketchEllipses.add(params[0], self.asPoint3D(params[1]), self.asPoint3D(params[2]))
                elif kind == "O":
                    # seems there is no add for conic curves yet?
                    #curve = sketchCurves.sketchConicCurves.add()
                    pass
                elif kind == "F":
                    pts = self.asObjectCollection(params[0])
                    spline = sketchCurves.sketchFittedSplines.add(pts)
                    fitPoints = spline.fitPoints
                    count = 0
                    for pt in params[0]:
                        idx = self.points.index(pt)
                        self.points[idx] = fitPoints.item(count)
                        pt.deleteMe()
                        count += 1

                if curve: 
                    curve.isConstruction = isConstruction
                    result.append(curve)
        return result
            
    def generateConstraints(self, cons):
        result = []
        constraints:f.GeometricConstraints = self.sketch.geometricConstraints
        index = 0
        for con in cons:
            constraint = None
            parse = re.findall(r"(VH|PA|PE|EQ|CC|CL|CO|MI|OC|OF|SY|SM|TA)([pcav][0-9|\[\]\.\-,]*)([pcav][0-9|\[\]\.\-,]*)?([pcav][0-9|\[\]\.\-,]*)?", con)[0]
            
            kind = parse[0]
            params = self.parseParams(parse[1:])
            p0 = params[0]
            p1 = params[1] if len(params) > 1 else None
            p2 = params[2] if len(params) > 2 else None
            try:
                if(kind == "VH"):
                    sp = p0.startSketchPoint.geometry
                    ep = p0.endSketchPoint.geometry
                    if(abs(sp.x - ep.x) < abs(sp.y - ep.y)):
                        constraint = constraints.addVertical(p0)
                    else:
                        constraint = constraints.addHorizontal(p0)
                elif(kind == "PA"):
                    constraint = constraints.addParallel(p0, p1)
                elif(kind == "PE"):
                    constraint = constraints.addPerpendicular(p0, p1)
                elif(kind == "EQ"):
                    constraint = constraints.addEqual(p0, p1)
                elif(kind == "CC"):
                    constraint = constraints.addConcentric(p0, p1)
                elif(kind == "CL"):
                    constraint = constraints.addCollinear(p0, p1)
                elif(kind == "CO"):
                    constraint = constraints.addCoincident(p0, p1)
                elif(kind == "MI"):
                    constraint = constraints.addMidPoint(p0, p1)
                elif(kind == "SY"):
                    constraint = constraints.addSymmetry(p0, p1, p2)
                elif(kind == "SM"):
                    constraint = constraints.addSmooth(p0, p1)
                elif(kind == "TA"):
                    constraint = constraints.addTangent(p0, p1)
                    
                elif(kind == "OF"):
                    # offsets are weird, but this helps a lot: https://forums.autodesk.com/t5/fusion-360-api-and-scripts/create-a-parametric-curves-offset-from-python-api/m-p/9391531
                    try:
                        c0 = p2[0]
                        if type(c0) == f.SketchCircle:
                            dirPoint = c0.geometry.center
                            dist = -abs(p1[0])
                        else:
                            dirPoint = c0.startSketchPoint.geometry
                            dist = abs(p1[0])

                        #dirPoint = c0.geometry.center if type(c0) == f.SketchCircle else c0.startSketchPoint.geometry 
                        oc = self.asObjectCollection(p0)
                        # the direction is set by the dirPoint geometry afaict, so distance is always positive relative to that
                        # this will generate new curves
                        offsetCurves = self.sketch.offset(oc, dirPoint, dist) 

                        # now remove matching elements that were generated
                        for rc in p2:
                            for curve in offsetCurves:
                                if(TurtlePath.isEquivalentLine(curve, rc, 0.01)):
                                    idx = self.curves.index(rc)
                                    self.curves[idx] = curve
                                    rc.deleteMe()
                                    break
                        self.offsetRefs[index] = self.sketch.parentComponent.modelParameters[self.sketch.parentComponent.modelParameters.count - 1]
                    except:
                        print('Failed:\n{}'.format(traceback.format_exc()))

            except:
                print("Unable to generate constraint: " + con)
            index += 1
        return result


    
    def generateDimensions(self, dims):
        result = []
        dimensions:f.SketchDimensions = self.sketch.sketchDimensions
        for dim in dims:
            dimension = None
            orientation = f.DimensionOrientations.AlignedDimensionOrientation
            parse = re.findall(r"(SLD|SOD|SAD|SDD|SRD|SMA|SMI|SCC|SOC)([pcvo][^pcvo]*)([pcvo][^pcvo]*)?([pcvo][^pcvo]*)?([pcvo][^pcvo]*)?", dim)[0]
            kind = parse[0]
            params = self.parseParams(parse[1:])
            p0 = params[0]
            p1 = params[1] if len(params) > 1 else None
            p2 = params[2] if len(params) > 2 else None
            p3 = params[3] if len(params) > 3 else None

            if kind == "SLD":
                dimension = dimensions.addDistanceDimension(p0, p1, orientation,self.asPoint3D(p3))# self.textPoint(p0,p1))
                dimension.parameter.expression = p2
            elif kind == "SOD":
                dimension = dimensions.addOffsetDimension(p0,p1,self.asPoint3D(p3))# self.textPoint(p0,p1))
                dimension.parameter.expression = p2
            elif kind == "SAD": # SketchAngularDimension
                midText = self.textPoint(p0, p1) # this must be mid centers as the quadrant dimensioned is based on the text postion.
                dimension = dimensions.addAngularDimension(p0,p1, midText)
                dimension.parameter.expression = p2
            elif kind == "SDD":
                dimension = dimensions.addDiameterDimension(p0, self.asPoint3D(p2)) # self.textPoint(p0.geometry.center))
                dimension.parameter.expression = p1
            elif kind == "SRD": # SketchRadialDimension
                dimension = dimensions.addRadialDimension(p0, self.asPoint3D(p2))
                dimension.parameter.expression = p1
            elif kind == "SMA": # SketchEllipseMajorRadiusDimension
                dimension = dimensions.addEllipseMajorRadiusDimension(p0, self.asPoint3D(p2))
                dimension.parameter.expression = p1
            elif kind == "SMI": # SketchEllipseMinorRadiusDimension
                dimension = dimensions.addEllipseMinorRadiusDimension(p0, self.asPoint3D(p2))
                dimension.parameter.expression = p1
            elif kind == "SCC": # SketchConcentricCircleDimension
                dimension = dimensions.addConcentricCircleDimension(p0,p1,self.asPoint3D(p3))
                dimension.parameter.expression = p2
            elif kind == "SOC": # SketchOffsetCurvesDimension
                parameter = self.offsetRefs[p0] 
                parameter.expression = p1

    def textPoint(self, p0, p1 = None):
        if p1 == None:
            return core.Point3D.create(p0.x + 1,p0.y+1,0)
        else:
            g0 = TurtleSketch.getMidpoint(p0) if type(p0) == f.SketchLine else p0.geometry 
            g1 = TurtleSketch.getMidpoint(p1) if type(p1) == f.SketchLine else p1.geometry 
            distance = g0.distanceTo(g1)
            angle = -0.5 * math.pi
            offset = distance * 0.2
            mid = core.Point3D.create(g0.x + (g1.x - g0.x)/2.0, g0.y + (g1.y - g0.y)/2.0)
            x = mid.x + offset * math.cos(angle)
            y = mid.y + offset * math.sin(angle) 
            return core.Point3D.create(x, y, 0)


    def parseParams(self, params):
        result = []
        for param in params:
            if not param == "":
                result.append(self.parseParam(param))
        return result

    def parseParam(self, param):
        result = None
        kind = param[0]
        val = param[1:]

        if kind == "p": # point
            result = self.points[int(val)]
        elif kind == "c": # curve
            result = self.curves[int(val)]
        elif kind == "v": # array of values
            if val.startswith("["):
                result = ast.literal_eval(val) # self.parseNums(val)
            else:
                result = val
        elif kind == "o": # object index (so far just used for tracking offset constraints)
            result = int(val)
        elif kind == "a": # list of curve indexes
            result = []
            idxs = val.split("|")
            for idx in idxs:
                result.append(self.curves[int(idx)])
        elif kind == "s": # list of point indexes (for splines)
            result = []
            idxs = val.split("|")
            for idx in idxs:
                result.append(self.points[int(idx)])
        return result
    
    def asPoint3D(self, pts):
        result = 0
        if isinstance(pts, Iterable):
            result = core.Point3D.create(pts[0],pts[1] if len(pts) > 1 else 0,pts[2] if len(pts) > 1 else 0)
        elif type(pts) == f.SketchPoint:
            result = pts.geometry
        return result
    
    def asObjectCollection(self, items):
        result = core.ObjectCollection.create()
        for item in items:
            result.add(item)
        return result
