#Author-
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback
import os, math, re
from .Utils import Utils
from .TurtleSketch import TurtleSketch

f,core,app,ui,design,root = Utils.initGlobals()


pMID = "mid"
pOUTER = "outer"
pFULL = "full"
pLIP = "lip"
pSHELF_WIDTH = "shelfWidth"
pZIP_WIDTH = "zipWidth"
pZIP_LENGTH = "zipLength"

# command
commandId = 'CreateShelvesId'
commandName = 'Create Shelves Command'
commandDescription = 'Creates three layer shelves and side walls based on a sketch.'
handlers = []
        
f,core,app,ui,design,root = Utils.initGlobals()

class CreateShelvesExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            jm = JointMaker()
            adsk.terminate()
        except:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class CreateShelvesCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        cmd = args.command
        onExecute = CreateShelvesExecuteHandler()
        cmd.execute.add(onExecute)
        handlers.append(onExecute)    

def run(context):
    try:
        cmdDef = ui.commandDefinitions.itemById(commandId)
        if not cmdDef:
            cmdDef = ui.commandDefinitions.addButtonDefinition(commandId, commandName, commandDescription)

        onCommandCreated = CreateShelvesCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)
        cmdDef.execute()
        # Prevent this module from being terminate when the script returns, because we are waiting for event handlers to fire
        adsk.autoTerminate(False)
    except:
        ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class JointMaker:
    def __init__(self):
        self.baseSketch:f.Sketch = self.ensureSelectionIsType(f.Sketch)
        if not self.baseSketch:
            return
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType

        self.turtle = TurtleSketch(self.baseSketch)

        self.comp = f.Component.cast(design.activeComponent)
        self.wallComp = self.comp
        self.actSel = ui.activeSelections
        self.addMMParam(pMID, 3)
        self.addMMParam(pOUTER, 2)
        self.addMMParam(pFULL, "mid + outer * 2")
        self.addMMParam(pLIP, 1)
        self.addMMParam(pSHELF_WIDTH, 40)
        self.addMMParam(pZIP_WIDTH, 1)
        self.addMMParam(pZIP_LENGTH, "zipWidth * 10")

        self.componentCounter = 0


        self.shelfLines = self.getSingleLines(self.baseSketch)
        fullProfile = self.combineProfiles(self.baseSketch)

        self.getAppearances() # this will deselct everything
        self.createWall(fullProfile)
        self.createShelves()
    
    def createWall(self, profile):
        extrudes = self.extrudeThreeLayers(profile)

        root.isConstructionFolderLightBulbOn = True
        planeInput:f.ConstructionPlaneInput = root.constructionPlanes.createInput()
        dist = self.getValueInputMM(pSHELF_WIDTH)
        planeInput.setByOffset(self.baseSketch.referencePlane, dist)
        self.midPlane:f.ConstructionPlane = root.constructionPlanes.add(planeInput)
        self.midPlane.name = "MidPlane"

        wallStartFace = extrudes[0].startFaces.item(0)
        sketch:f.Sketch = self.comp.sketches.add(wallStartFace)
        fullProfile = self.createWallOuterCuts(sketch)
        #self.cutComponent(fullProfile, self.wallComp)
        self.cutBodiesWithProfiles([extrudes[0].bodies.item(0)], [fullProfile])

        wallNextFace = extrudes[1].startFaces.item(0)
        sketch:f.Sketch = self.comp.sketches.add(wallNextFace)
        fullProfile = self.createWallInsideCuts(sketch)
        self.cutBodiesWithProfiles([ extrudes[1].bodies.item(0), extrudes[2].bodies.item(0)], [fullProfile,fullProfile])

        self.mirrorComponent(self.wallComp, self.midPlane, False)

    
    def createWallOuterCuts(self, sketch:f.Sketch):
        for idx, line in enumerate(self.shelfLines):
            self.createWallZipCutProfile(sketch, line)
        fullProfile = self.combineProfiles(sketch)
        #fullProfile.removeByIndex(0)
        self.removeLargestProfile(fullProfile)
        return fullProfile

    def createWallZipCutProfile(self, sketch:f.Sketch, shelfLine:f.SketchLine):
        constraints = sketch.geometricConstraints
        baseLine:f.SketchLine = self.projectLine(sketch, shelfLine)
        
        construction = self.addMidpointConstructionLine(sketch, baseLine, pOUTER, True) # hmm...
        # draw square
        lines = Turtle.draw(sketch, construction, "M75LF50 RF50 RF50 RF50")
        lines[0].startSketchPoint.merge(lines[3].endSketchPoint)
        constraints.addPerpendicular(lines[0], construction)
        
        self.makeParallel(constraints, lines, [[0,2],[1,3]])
        self.makePerpendicular(constraints, lines, [[0,1]])
        constraints.addMidPoint(construction.endSketchPoint, lines[0])
        self.addLineLength(sketch, lines[0], pZIP_WIDTH)
        self.addLineLength(sketch, lines[1], pMID)


    def createWallInsideCuts(self, sketch:f.Sketch):
        constraints = sketch.geometricConstraints
        for idx, line in enumerate(self.shelfLines):
            baseLine:f.SketchLine = self.projectLine(sketch, line)
            baseLine.isConstruction = True
            construction = self.addMidpointConstructionLine(sketch, baseLine, None, True)

            lines = Turtle.draw(sketch, construction, "RM20L180 F40 RF2 RF40 RF20", True)
            self.makeParallel(constraints, lines, [[0,2],[1,3]])
            self.makePerpendicular(constraints, lines, [[0,1]])

            constraints.addCollinear(lines[0], baseLine)
            self.addLineLength(sketch, lines[1], pFULL)
            constraints.addSymmetry(lines[1], lines[3], construction)

            dim = sketch.sketchDimensions.addDistanceDimension(baseLine.startSketchPoint, lines[0].startSketchPoint, \
            f.DimensionOrientations.AlignedDimensionOrientation, lines[0].startSketchPoint.geometry)
            dim.parameter.expression = pLIP

        fullProfile = self.combineProfiles(sketch)
        fullProfile.removeByIndex(0)
        return fullProfile

    def createShelves(self):
        for idx, line in enumerate(self.shelfLines):
            comp = self.createHalfShelf(line, idx)
            self.mirrorComponent(comp, self.midPlane, True)

    # def mirrorComponent(self, component:f.Component, plane:f.ConstructionPlane):
    #     mirrorFeatures = component.features.mirrorFeatures
    #     inputEntites = adsk.core.ObjectCollection.create()
    #     inputEntites.add(component)
    #     mirrorInput:f.MirrorFeatureInput = mirrorFeatures.createInput(inputEntites, plane)
    #     mirrorFeature = mirrorFeatures.add(mirrorInput)

    def mirrorComponent(self, component:f.Component, plane:f.ConstructionPlane, isJoined:bool = False):
        mirrorFeatures = component.features.mirrorFeatures
        inputEntites = adsk.core.ObjectCollection.create()
        for body in component.bRepBodies:
            inputEntites.add(body)
        mirrorInput:f.MirrorFeatureInput = mirrorFeatures.createInput(inputEntites, plane)
        mirrorInput.isCombine = isJoined
        mirrorFeature = mirrorFeatures.add(mirrorInput)

    def createHalfShelf(self, line:f.SketchLine, index):
        self.comp = self.createComponent("shelf"+ str(index))
        plane = self.createOrthoganalPlane(line)

        sketch:f.Sketch = self.createSketch(plane)
        ts = TurtleSketch(sketch)

        prj = sketch.project(line)
        baseLine = prj[0]
        construction = ts.addMidpointConstructionLine(baseLine)
        lines = ts.draw(construction, 
            "M10 LM1",
            "#0 F47",
            "#1 RF200",
            "#2 LF2",
            "#3 RF400",
            "#4 RF100",
            "#5 RF400",
            "#6 RF2",
            "#7 LF200",
            "#8 RF47",
            "#9 RF200",
            "#10 RF2",
            "#11 LF100",
            "#12 LF4",
            "#13 LF300",
            "#14 LF2")

        constraintList = [
            "ME", [0,0,13,1, 9,0,14,1],
            "PA", [baseLine, 0],
            "EQ", [baseLine, 4],
            "CO", [0,8, 2,6],
            "PA", [0,4, 1,7, 3,5, 9,13, 11,13, 12,10],
            "SY", [9,13,construction, 1,7,construction, 3,5,construction],
            "PE", [2,3, 9,10],

            "LD", [0,baseLine,pOUTER],
            "LL", [11, pZIP_LENGTH + " - " + pLIP, 
                    13, pZIP_LENGTH, 
                    1, pOUTER + " + " + pMID, 
                    3, pSHELF_WIDTH + " - " + pFULL, 
                    14, pZIP_WIDTH,
                    12, pZIP_WIDTH + " * 2",
                    2, pLIP]
        ] 
        ts.constrain(constraintList)

        cutProfile = sketch.profiles.item(0)
        fullProfile = self.combineProfiles(sketch)
        shelfExtrusions = self.extrudeThreeLayers([fullProfile,cutProfile,fullProfile])
        
        return self.comp
    
    def createComponent(self, name):
        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occ.component.name = name
        return occ.component

    def createSketch(self, plane:f.ConstructionPlane):
        return self.comp.sketches.add(plane)

    def createOrthoganalPlane(self, line:f.SketchLine):
        refPlane = self.baseSketch.referencePlane # line.parentSketch.referencePlane
        planeInput = self.comp.constructionPlanes.createInput()
        planeInput.setByAngle(line, adsk.core.ValueInput.createByReal(-math.pi/2.0), refPlane)
        result = self.comp.constructionPlanes.add(planeInput)
        return result

    def extrudeThreeLayers(self, profiles):
        # optionally pass a single profile
        result = []
        if not isinstance(profiles, list):
            profiles = [profiles, profiles, profiles]

        extruded = self.extrude(profiles[0], 0, pOUTER)
        if extruded:
            result.append(extruded)
            extruded.bodies.item(0).appearance = self.colOuter
            extruded = self.extrude(profiles[1], extruded.endFaces.item(0), pMID)
            result.append(extruded)
            extruded.bodies.item(0).appearance = self.colMid
            extruded = self.extrude(profiles[2], extruded.endFaces.item(0), pOUTER)
            result.append(extruded)
            extruded.bodies.item(0).appearance = self.colOuter
        return result

    def extrude(self, profile, start, expression):
        if profile is None:
            return
        extrudes = self.comp.features.extrudeFeatures
        dist = self.getValueInputMM(expression)
        extrudeInput = extrudes.createInput(profile, f.FeatureOperations.NewBodyFeatureOperation) 
        extentDistance = f.DistanceExtentDefinition.create(dist) 
        extrudeInput.setOneSideExtent(extentDistance, f.ExtentDirections.PositiveExtentDirection)
        if start:
            startFrom = f.FromEntityStartDefinition.create(start, self.getValueInputMM(0))
            extrudeInput.startExtent = startFrom

        extrude = extrudes.add(extrudeInput) 
        # bug: Need to reassign expression
        extDef = f.DistanceExtentDefinition.cast(extrude.extentOne)
        extDef.distance.expression = expression

        # extrude = extrudes.addSimple(profile, dist, f.FeatureOperations.NewBodyFeatureOperation) 
        body = extrude.bodies.item(0) 
        return extrude

    def cutBodiesWithProfiles(self, bodies:list, profiles:list):
        bodies = self.ensureBodiesAsList(bodies)
        if len(profiles) != len(bodies):
            return
        for i in range(len(profiles)):
            self.cutBodyWithProfile(profiles[i], bodies[i])

    def cutBodyWithProfile(self, profile:f.Profile, body:f.BRepBody):
        extrudes = body.parentComponent.features.extrudeFeatures
        cutInput = extrudes.createInput(profile, f.FeatureOperations.CutFeatureOperation) 

        # ** this will sometimes only cut to bodies first face causing an error. 
        # To be robust needs to use bodies farthest face as entity, but for now just use full*2 symetrically
        # This works in the context of joints because we have participating bodies, but is weak in a lot of cases
        #ext = f.ToEntityExtentDefinition.create(body, True)
        #cutInput.setAllExtent(f.ExtentDirections.NegativeExtentDirection)
        cutInput.setSymmetricExtent(self.getValueInputMM("full * 2"), True)

        cutInput.participantBodies = [body]
        extrude = extrudes.add(cutInput) 
        return extrude

            
    def cutComponent(self, profile, component:f.Component):
        if profile is None:
            return
        extrudes = self.comp.features.extrudeFeatures
        extrudeInput = extrudes.createInput(profile, f.FeatureOperations.CutFeatureOperation)
        distanceForCut = adsk.core.ValueInput.createByString("-" + pFULL)
        extrudeInput.setDistanceExtent(False, distanceForCut)
        bodies = []
        for body in component.bRepBodies:
            bodies.append(body)
        extrudeInput.participantBodies = bodies
        extrude = extrudes.add(extrudeInput) 
        return extrude

    def addMMParam(self, name, val, msg=""):
        result = design.userParameters.itemByName(name)
        if result is None:
            result = design.userParameters.add(name, self.getValueInputMM(val), "mm", msg)
        return result

    def getValueInputMM(self, val):
            if isinstance(val, str):
                return adsk.core.ValueInput.createByString(val)
            elif isinstance(val, (int, float)):
                return adsk.core.ValueInput.createByString(str(val) + " mm")
            elif isinstance(val, bool):
                return adsk.core.ValueInput.createByBoolean(val)
            else:
                return adsk.core.ValueInput.createByObject(val)
    
    def ensureSelectionIsType(self, selType):
        typeName = selType.__name__
        title = "Selection Required"
        if not design:
            ui.messageBox('No active Fusion design', title)
            return

        if ui.activeSelections.count < 1:
            ui.messageBox('Select ' + typeName + ' before running command.', title)
            return

        selected = ui.activeSelections.item(0).entity
        if not type(selected) is selType:
            ui.messageBox('Selected object needs to be a ' + typeName + ". It is a " + str(type(selected)) + ".", title)
            return
        return selected
    
    def ensureBodiesAsList(self, fBodies):
        if isinstance(fBodies, list):
            return fBodies
        bodies = []
        if isinstance(fBodies, f.Component):
            fBodies = fBodies.bRepBodies
        for b in fBodies:
            bodies.append(b)
        return bodies

    def getAppearances(self):
        matLib = app.materialLibraries.item(2).appearances
        self.colOuter = matLib.itemByName("Plastic - Translucent Matte (Yellow)")
        self.colOuter.copyTo(design)
        self.colMid = matLib.itemByName("Plastic - Translucent Matte (Green)")
        self.colMid.copyTo(design)
    
    def setDistances(self, sketch:f.Sketch, lines, indexValues):
        for pair in indexValues:
             self.addLineLength(sketch, lines[pair[0]], pair[1])

    def makeVertHorz(self, constraints:f.GeometricConstraints, lines, indexes):
        for index in indexes:
            sp = lines[index].startSketchPoint.geometry
            ep = lines[index].endSketchPoint.geometry
            if(abs(sp.x - ep.x) < abs(sp.y - ep.y)):
                constraints.addVertical(lines[index])
            else:
                constraints.addHorizontal(lines[index])

    def makeEqual(self, constraints:f.GeometricConstraints, curves, pairIndexes):
        for pair in pairIndexes:
            constraints.addEqual(curves[pair[0]], curves[pair[1]])

    def makeParallel(self, constraints:f.GeometricConstraints, lines, pairIndexes):
        for pair in pairIndexes:
            constraints.addParallel(lines[pair[0]], lines[pair[1]])
            
    def makePerpendicular(self, constraints:f.GeometricConstraints, lines, pairIndexes):
        for pair in pairIndexes:
            constraints.addPerpendicular(lines[pair[0]], lines[pair[1]])

    def makeCollinear(self, constraints:f.GeometricConstraints, lines, pairIndexes):
        for pair in pairIndexes:
            constraints.addCollinear(lines[pair[0]], lines[pair[1]])

    def addLineLength(self, sketch:f.Sketch, line:f.SketchLine, expr):
        dim = sketch.sketchDimensions.addDistanceDimension(line.startSketchPoint, line.endSketchPoint, \
            f.DimensionOrientations.AlignedDimensionOrientation, line.startSketchPoint.geometry)
        dim.parameter.expression = expr

    def addPointsDist(self, sketch:f.Sketch, p0:f.SketchPoint, p1:f.SketchPoint, expr):
        dim = sketch.sketchDimensions.addDistanceDimension(p0, p1, \
            f.DimensionOrientations.AlignedDimensionOrientation, p0.geometry)
        dim.parameter.expression = expr

    def addTwoLinesDist(self, sketch:f.Sketch, line0:f.SketchLine, line1:f.SketchLine, expr):
        dim = sketch.sketchDimensions.addOffsetDimension(line0, line1, line1.startSketchPoint.geometry)
        dim.parameter.expression = expr

    def addMidpointConstructionLine(self, sketch:f.Sketch, baseLine:f.SketchLine, lengthExpr=None, toLeft=True):
        constraints = sketch.geometricConstraints
        path = "XM50LF50X" if toLeft else "XM50RF50X"
        lines = Turtle.draw(sketch, baseLine, path)
        construction = lines[0]
        constraints.addPerpendicular(construction, baseLine)
        constraints.addMidPoint(construction.startSketchPoint, baseLine)
        if lengthExpr:
            self.addLineLength(sketch, construction, lengthExpr)
        else:
            constraints.addEqual(construction, baseLine)

        return lines[0]

    def combineProfiles(self, sketch:f.SketchLine):
        result = core.ObjectCollection.create()
        for p in sketch.profiles:
            result.add(p)
        return result
        
    def removeLargestProfile(self, profiles:core.ObjectCollection):
        largestIndex = 0
        largestArea = 0
        for i in range(profiles.count):
            areaProps = profiles.item(i).areaProperties(f.CalculationAccuracy.MediumCalculationAccuracy)
            if areaProps.area > largestArea:
                largestArea = areaProps.area
                largestIndex = i
        result = profiles.item(largestIndex)        
        profiles.removeByIndex(largestIndex)
        return result
        
    def createRect(self, sketch:f.Sketch, baseLine:f.SketchLine, widthExpr, sideOffsetExpr = None):
        contraints = sketch.geometricConstraints
        opp:f.SketchLine = self.addParallelLine(sketch, baseLine)

        constraints.addEqual(baseLine, opp)
        dim = sketch.sketchDimensions.addDistanceDimension(baseLine.startSketchPoint, opp.startSketchPoint, \
            f.DimensionOrientations.AlignedDimensionOrientation, baseLine.startSketchPoint.geometry)
        dim.parameter.expression = widthExpr

        side0 = sketch.sketchCurves.sketchLines.addByTwoPoints(baseLine.startSketchPoint, opp.startSketchPoint)
        constraints.addPerpendicular(baseLine, side0)

        side1 = sketch.sketchCurves.sketchLines.addByTwoPoints(baseLine.endSketchPoint, opp.endSketchPoint)
        constraints.addPerpendicular(baseLine, side1)
        constraints.addPerpendicular(opp, side1)
        return [baseLine, side0, opp, side1]
    
    def projectLine(self, sketch:f.Sketch, line:f.SketchLine):
        pp0 = sketch.project(line.startSketchPoint)
        pp1 = sketch.project(line.endSketchPoint)
        return sketch.sketchCurves.sketchLines.addByTwoPoints(pp0[0], pp1[0])

    def duplicateLine(self, sketch:f.Sketch, line:f.SketchLine):
        return sketch.sketchCurves.sketchLines.addByTwoPoints(line.startSketchPoint, line.endSketchPoint)

    def addParallelLine(self, sketch:f.Sketch, line:f.SketchLine, direction=1):
        p0 = line.startSketchPoint.geometry
        p1 = line.endSketchPoint.geometry
        rpx = (p1.y - p0.y) * direction # rotate to get perpendicular point to ensure direction
        rpy = (p1.x - p0.x) * -direction
        pp0 = core.Point3D.create(p0.x + rpx, p0.y + rpy, 0)
        pp1 = core.Point3D.create(p1.x + rpx, p1.y + rpy, 0)
        line2 = sketch.sketchCurves.sketchLines.addByTwoPoints(pp0, pp1)
        #sketch.geometricConstraints.addParallel(line, line2)
        return line2
    
    def getSingleLines(self, sketch:f.Sketch):
        lines = []
        touched = []
        for gc in sketch.geometricConstraints:
            if isinstance(gc, f.CoincidentConstraint) and gc.point.connectedEntities:
                for con in gc.point.connectedEntities:
                    if isinstance(con, f.SketchLine):
                        touched.append(con) 
                if isinstance(gc.entity, f.SketchLine):
                    touched.append(gc.entity) # bug: enity reference doesn't seem to be the same object as original

        for line in sketch.sketchCurves.sketchLines:
            if line.isConstruction:
                continue
            if line.startSketchPoint.connectedEntities.count > 1:
                continue
            if line.endSketchPoint.connectedEntities.count > 1:
                continue

            lines.append(line)

        result = []
        for line in lines:
            isTouched = False
            for t in touched:
                if self.isEquivalentLine(t, line):
                    isTouched = True
                    break
            if not isTouched:
                result.append(line)

        print(str(len(result)) + " result: ",end="")
        self.printLines(result)
        return result
    
    def isEquivalentLine(self, a:f.SketchLine, b:f.SketchLine, maxDist = 0):
        result = abs(a.geometry.startPoint.x - b.geometry.startPoint.x) <= maxDist and \
            abs(a.geometry.startPoint.y - b.geometry.startPoint.y) <= maxDist and \
            abs(a.geometry.endPoint.x - b.geometry.endPoint.x) <= maxDist and \
            abs(a.geometry.endPoint.y - b.geometry.endPoint.y) <= maxDist
        # print(result, end=" ")    
        # self.printLines([a,b])
        return result

    def printLines(self, lines, newLine="\n"):
        spc = "Line: "
        for line in lines:
            print(spc, end="")
            self.printLine(line, "")
            spc=", "
        print("",end=newLine)

    def printLine(self, line:f.SketchLine, newLine="\n"):
        print("[",end="")
        self.printPoint(line.startSketchPoint)
        print(", ",end="")
        self.printPoint(line.endSketchPoint)
        print("("+ str(round(line.length, 2)) + ")", end="")
        print("]", end=newLine)

    def printPoint(self, pt:f.SketchPoint):
        print(str(round(pt.geometry.x, 2)) +", " + str(round(pt.geometry.y,2)),end="")

class ZipJoint:
    def createShelf(self):
        pass
    def createWallCuts(self):
        pass

class Turtle:
    # draws a polyline using directions and distances. Distances are percent of line lenght, start direction is p0->p1 of line.
    @staticmethod
    def draw(sketch:f.Sketch, line:f.SketchLine, path:str, isClosed=False):
        cmds = re.findall("[#FLRMX][0-9\-\.]*", path) #lazy number :)
        startPt = line.startSketchPoint.geometry
        endPt = line.endSketchPoint.geometry
        difX = endPt.x - startPt.x
        difY = endPt.y - startPt.y
        length = math.sqrt(difX * difX + difY * difY)
        angle = math.atan2(difY,difX) + math.pi * 4.0
        curPt:f.SketchPoint = line.startSketchPoint
        lastLine:f.SketchLine = line
        lines = []

        cmd:str
        num:float
        for cmd in cmds:
            num = float(cmd[1:]) if len(cmd) > 1 else 90
            if cmd.startswith('F'):
                p2 = Turtle.getEndPoint(curPt.geometry, angle, (num / 100.0) * length)
                lastLine = sketch.sketchCurves.sketchLines.addByTwoPoints(curPt, p2)
                lines.append(lastLine)
                curPt = lastLine.endSketchPoint
            elif cmd.startswith('L'):
                angle -= num/180.0 * math.pi
            elif cmd.startswith('R'):
                angle += num/180.0 * math.pi
            elif cmd.startswith('M'):
                curPt = sketch.sketchPoints.add(Turtle.getEndPoint(curPt.geometry, angle, (num / 100.0) * length))
            elif cmd.startswith('X'):
                lastLine.isConstruction = True
            elif cmd.startswith('#'):
                pass # comment number
        
        if isClosed:
            lines[0].startSketchPoint.merge(lines[len(lines) - 1].endSketchPoint)
        # if start or end is on line, add constraint
        # *** or maybe this is just confusing...
        # if Turtle.isOnLine(lines[0].startSketchPoint.geometry, line):
        #     sketch.geometricConstraints.addCoincident(lines[0].startSketchPoint, line)
        # if Turtle.isOnLine(lastLine.endSketchPoint.geometry, line):
        #     sketch.geometricConstraints.addCoincident(lastLine.endSketchPoint, line)
            
        return lines

    @staticmethod
    def getEndPoint(start:core.Point3D, angle:float, distance:float):
        x = start.x + distance * math.cos(angle)
        y = start.y + distance * math.sin(angle) 
        return core.Point3D.create(x, y, 0)

    @staticmethod
    def isOnLine(a:core.Point3D, line:f.SketchLine):
        b = line.startSketchPoint.geometry
        c = line.endSketchPoint.geometry
        cross = (c.y - a.y) * (b.x - a.x) - (c.x - a.x) * (b.y - a.y)
        return abs(cross) < 0.0001

    @staticmethod
    def distanceToLine(a:core.Point3D, line:f.SketchLine):
        b = line.startSketchPoint.geometry
        c = line.endSketchPoint.geometry
        x_diff = c.x - b.x
        y_diff = c.y - b.y
        num = abs(y_diff * a.x - x_diff * a.y + c.x*b.y - c.y*b.x)
        den = math.sqrt(y_diff**2 + x_diff**2)
        return num / den

# todo: make a turtle graphics style method that creates lines with forward 2, rotate left 90, forward 1, rotate right 90... and return array of lines