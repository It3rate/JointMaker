
import adsk.core, adsk.fusion, adsk.cam, traceback
import os, math, re, ast
from .TurtleUtils import TurtleUtils
from .TurtleComponent import TurtleComponent
from .TurtleSketch import TurtleSketch
from .TurtleParams import TurtleParams
from .TurtlePath import TurtlePath
from .TurtleLayers import TurtleLayers

f,core,app,ui,design,root = TurtleUtils.initGlobals()

class SketchDecoder:
    def __init__(self):
        self.sketch:f.Sketch = TurtleUtils.ensureSelectionIsType(f.Sketch)
        if not self.sketch:
            return
        self.tcomponent = TurtleComponent.createFromSketch(self.sketch)
        self.tparams = TurtleParams.instance()

        self.decodeFromSketch()

        TurtleUtils.selectEntity(self.sketch)

    def decodeFromSketch(self):
        data = self.getTestData()
        
        params = data["Params"]
        for p in params:
            self.tparams.addParam(p, params[p])

        pointValues = data["Points"]
        chains = data["Chains"]
        constraints = data["Constraints"]
        dimensions = data["Dimensions"]

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
                parse = re.findall(r"([LACEO])(x?)([pv][0-9\[\]\.\-,]*)([pv][0-9\[\]\.\-,]*)?([pv][0-9\[\]\.\-,]*)?([pv][0-9\[\]\.\-,]*)?", seg)[0]
                kind = parse[0]
                isConstruction = parse[1] == "x"
                params = self.parseParams(parse[2:])
                curve = None
                if kind == "L":
                    curve = sketchCurves.sketchLines.addByTwoPoints(params[0], params[1])
                elif kind == "A":
                    curve = sketchCurves.sketchArcs.addByCenterStartSweep(params[0], params[1].geometry, params[2][0])
                    pass
                elif kind == "C":
                    curve = sketchCurves.sketchCircles.addByCenterRadius(params[0], params[1][0])
                    pass
                elif kind == "E":
                    curve = sketchCurves.sketchEllipses.add(params[0], self.asPoint3D(params[1]), self.asPoint3D(params[2]))
                    pass
                elif kind == "O":
                    # seems there is no add for conic curves yet?
                    #curve = sketchCurves.sketchConicCurves.add()
                    pass
                if curve: 
                    curve.isConstruction = isConstruction
                    result.append(curve)
        return result
            
    def generateConstraints(self, cons):
        result = []
        constraints:f.GeometricConstraints = self.sketch.geometricConstraints
        for con in cons:
            constraint = None
            parse = re.findall(r"(VH|PA|PE|EQ|CL|CO|SY|MI|TA)([pc][0-9]*)([pc][0-9]*)?([pc][0-9]*)?", con)[0]
            
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
                elif(kind == "CL"):
                    constraint = constraints.addCollinear(p0, p1)
                elif(kind == "CO"):
                    constraint = constraints.addCoincident(p0, p1)
                elif(kind == "SY"):
                    constraint = constraints.addSymmetry(p0, p1, p2)
                elif(kind == "MI"):
                    constraint = constraints.addMidPoint(p0, p1)
                elif(kind == "TA"):
                    constraint = constraints.addTangent(p0, p1)
            except:
                print("Unable to generate constraint: " + con)
        return result


    
    def generateDimensions(self, dims):
        result = []
        dimensions:f.SketchDimensions = self.sketch.sketchDimensions
        #'SLDp5p5v35mm','SLDp11p11v30mm','SODc9vtest','SDDc13v20mm'
        for dim in dims:
            dimension = None
            orientation = f.DimensionOrientations.AlignedDimensionOrientation
            parse = re.findall(r"(SLD|SOD|SAD|SDD|SRD|SMA|SMI|SCC)([pcv][^pcv]*)([pcv][^pcv]*)?([pcv][^pcv]*)?([pcv][^pcv]*)?", dim)[0]
            print(parse)
            kind = parse[0]
            params = self.parseParams(parse[1:])
            p0 = params[0]
            p1 = params[1] if len(params) > 1 else None
            p2 = params[2] if len(params) > 2 else None
            p3 = params[3] if len(params) > 3 else None

            if kind == "SLD":
                dimension = dimensions.addDistanceDimension(p0, p1, orientation, self.textPoint(p0,p1))
                dimension.parameter.expression = p2
            elif kind == "SOD":
                dimension = dimensions.addOffsetDimension(p0,p1, self.textPoint(p0,p1))
                dimension.parameter.expression = p2
            # elif kind == "SAD":
            #     dimension = dimensions.(p0,p1,p2)
            elif kind == "SDD":
                dimension = dimensions.addDiameterDimension(p0, self.textPoint(p0.geometry.center))
                dimension.parameter.expression = p1
            # elif kind == "SRD":
            #     dimension = dimensions.(p0,p1,p2)
            # elif kind == "SMA":
            #     dimension = dimensions.(p0,p1,p2)
            # elif kind == "SMI":
            #     dimension = dimensions.(p0,p1,p2)
            # elif kind == "SCC":
            #     dimension = dimensions.(p0,p1,p2)

    def textPoint(self, p0, p1 = None):
        if p1 == None:
            return core.Point3D.create(p0.x + 1,p0.y+1,0)
        else:
            g0 = self.midpoint(p0) if type(p0) == f.SketchLine else p0.geometry 
            g1 = self.midpoint(p1) if type(p1) == f.SketchLine else p1.geometry 
            distance = g0.distanceTo(g1)
            angle = -0.5 * math.pi
            offset = distance * 0.2
            mid = core.Point3D.create(g0.x + (g1.x - g0.x)/2.0, g0.y + (g1.y - g0.y)/2.0)
            x = mid.x + offset * math.cos(angle)
            y = mid.y + offset * math.sin(angle) 
            return core.Point3D.create(x, y, 0)

    def midpoint(self, line:f.SketchLine):
        ev = line.geometry.evaluator
        pe = ev.getParameterExtents()
        return ev.getPointAtParameter((pe[2] - pe[1]) * 0.5)[1]


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
        if kind == "p":
            result = self.points[int(val)]
        elif kind == "c":
            result = self.curves[int(val)]
        elif kind == "v":
            if val.startswith("["):
                result = ast.literal_eval(val) # self.parseNums(val)
            else:
                result = val
        return result
    
    def asPoint3D(self, pts):
        return core.Point3D.create(pts[0],pts[1],pts[2] if len(pts)>2 else 0)

    def getTestData(self):
        return {
                'Params':{
                'test':'25 mm'
                },
                'Points':[
                [0.0,0.0],[1.53,-3.17],[4.25,-3.9],[4.25,-1.63],[7.13,-1.51],[7.13,-7.08],[4.0,-8.66],[-0.37,-6.66],[-4.03,-3.33],[-4.49,-2.42],[-1.93,-1.13],[-1.47,-2.04],[-2.83,-5.53],[-0.82,-6.45],[8.13,-3.24],[5.69,-1.57],[5.69,-3.18],[-1.83,-7.84],[-1.18,-7.24],[9.77,-7.79],[9.14,-9.18],[10.4,-6.41],[10.43,-8.09],[9.11,-7.49],[11.5,-5.0],[13.65,-5.07],[12.61,-7.19]
                ],
                'Chains':[
                'Lp2p3 Lp3p4 Lp4p5 Lp5p6 Lp6p7 Lp7p1 Lp1p2', # 0-6
                'Lp9p10 Lp10p11 Lp11p8 Lp8p9', # 7-10
                'Lp12p13 Ap18p17v[3.54]', # 11-12
                'Cp14v[1.0]', # 13
                'Lxp15p16', # 14
                'Ep19v[9.14,-9.18]v[10.43,-8.09]', # 15
                'Lxp20p21', # 16
                'Lxp22p23', # 17
                'Op24p26p25v[3.49]', # 18
                ],
                'Constraints':[
                'VHc0','PEc10c3','PEc7c10','TAc13c2','MIp15c1','VHc14','SYc0c2c14','EQc9c7','PAc8c10','CLc4c11','TAc12c11','PEc16c4','COp20c15','COp21c15','COp22c15','COp23c15'
                ],
                'Dimensions':[
                'SLDp5p6v35mm','SLDp11p1v30mm','SODc9p12vtest','SDDc13v20mm'
                ]
                }
