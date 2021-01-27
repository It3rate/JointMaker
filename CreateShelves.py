#Author-
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback
import os, math, re
from .Utils import Utils
from .TurtleSketch import TurtleSketch
from .TurtleParams import TurtleParams
from .TurtlePath import TurtlePath
from .MultiLayer import MultiLayer

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

        self.parameters = TurtleParams.instance()
        self.parameters.addParams(
            pMID, 3,
            pOUTER, 2,
            pFULL, "mid + outer * 2",
            pLIP, 1,
            pSHELF_WIDTH, 40,
            pZIP_WIDTH, 1,
            pZIP_LENGTH, "zipWidth * 10")

        self.comp = f.Component.cast(design.activeComponent)
        self.wallComp = self.comp
        self.actSel = ui.activeSelections

        self.componentCounter = 0

        tsketch = TurtleSketch(self.baseSketch)
        fullProfile = tsketch.combineProfiles()
        self.shelfLines = self.getSingleLines(self.baseSketch)

        self.getAppearances() # this will deselct everything
        self.createWalls(fullProfile)
        self.createShelves()
    
    def createWalls(self, profile):
        ml = MultiLayer(self.comp, profile, [pOUTER, pMID, pOUTER], [self.colOuter,self.colMid,self.colOuter])

        root.isConstructionFolderLightBulbOn = True
        planeInput:f.ConstructionPlaneInput = root.constructionPlanes.createInput()
        dist = self.parameters.createValue(pSHELF_WIDTH)
        planeInput.setByOffset(self.baseSketch.referencePlane, dist)
        self.midPlane:f.ConstructionPlane = root.constructionPlanes.add(planeInput)
        self.midPlane.name = "MidPlane"

        tsketch:TurtleSketch = self.createSketch(ml.startFaceAt(0)) 
        fullProfile = self.createWallOuterCuts(tsketch)
        ml.cutBodiesWithProfiles(fullProfile, 0)

        tsketch:TurtleSketch = self.createSketch(ml.startFaceAt(1))
        fullProfile = self.createWallInsideCuts(tsketch)
        ml.cutBodiesWithProfiles(fullProfile, 1,2)

        self.mirrorComponent(self.wallComp, self.midPlane, False)

    def createShelves(self):
        for idx, line in enumerate(self.shelfLines):
            comp = self.createHalfShelf(line, idx)
            self.mirrorComponent(comp, self.midPlane, True)
    

    def createWallOuterCuts(self, tsketch:TurtleSketch):
        for idx, line in enumerate(self.shelfLines):
            self.createWallZipCutProfile(tsketch, line)
        fullProfile = tsketch.combineProfiles()
        tsketch.removeLargestProfile(fullProfile)
        return fullProfile

    def createWallZipCutProfile(self, tsketch:TurtleSketch, shelfLine:f.SketchLine):
        baseLine:f.SketchLine = tsketch.projectLine(shelfLine)
        construction = tsketch.addMidpointConstructionLine(baseLine, pOUTER, True)

        tsketch.draw(construction, "M75LF50 RF50 RF50 RF50")
        tsketch.constrain( [
            "ME", [0,0,3,1],
            "PE", [0, construction],
            "PA", [0,2, 1,3],
            "PE", [0, 1],
            "MI", [construction, 1, 0],
            "LL", [0, pZIP_WIDTH, 
                    1, pMID]
        ])

    def createWallInsideCuts(self, tsketch:TurtleSketch):
        for idx, line in enumerate(self.shelfLines):
            baseLine:f.SketchLine = tsketch.projectLine(line)
            baseLine.isConstruction = True
            construction = tsketch.addMidpointConstructionLine(baseLine, None, True)

            lines = tsketch.drawClosed(construction, "RM20L180 F40 RF2 RF40 RF20")
            tsketch.constrain( [
                "PA", [0,2, 1,3],
                "PE", [0, 1],
                "CO", [0, baseLine],
                "LL", [1, pFULL],
                "SY", [1, 3, construction],
                "PD", [baseLine, 0, 0, 0, pLIP]
            ])

        fullProfile = tsketch.combineProfiles()
        fullProfile.removeByIndex(0)
        return fullProfile

    def createHalfShelf(self, line:f.SketchLine, index):
        self.comp = self.createComponent("shelf"+ str(index))
        plane = self.createOrthoganalPlane(line)
        tsketch:TurtleSketch = self.createSketch(plane)
        prj = tsketch.sketch.project(line)
        baseLine = prj[0]
        construction = tsketch.addMidpointConstructionLine(baseLine)

        lines = tsketch.draw(construction, 
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

        tsketch.constrain( [
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
        ] )

        cutProfile = tsketch.getProfileAt(0)
        fullProfile = tsketch.combineProfiles()
        
        shelfExtrusions = MultiLayer(self.comp, [fullProfile,cutProfile,fullProfile], [pOUTER, pMID, pOUTER], [self.colOuter,self.colMid,self.colOuter])
        return self.comp
    
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
                if TurtlePath.isEquivalentLine(t, line):
                    isTouched = True
                    break
            if not isTouched:
                result.append(line)

        return result
    





    def createComponent(self, name):
        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occ.component.name = name
        return occ.component

    def createSketch(self, plane):
        sketch = self.comp.sketches.add(plane)
        return TurtleSketch(sketch)

    def createOrthoganalPlane(self, line:f.SketchLine):
        refPlane = self.baseSketch.referencePlane # line.parentSketch.referencePlane
        planeInput = self.comp.constructionPlanes.createInput()
        planeInput.setByAngle(line, adsk.core.ValueInput.createByReal(-math.pi/2.0), refPlane)
        result = self.comp.constructionPlanes.add(planeInput)
        return result

    def mirrorComponent(self, component:f.Component, plane:f.ConstructionPlane, isJoined:bool = False):
        mirrorFeatures = component.features.mirrorFeatures
        inputEntites = adsk.core.ObjectCollection.create()
        for body in component.bRepBodies:
            inputEntites.add(body)
        mirrorInput:f.MirrorFeatureInput = mirrorFeatures.createInput(inputEntites, plane)
        mirrorInput.isCombine = isJoined
        mirrorFeature = mirrorFeatures.add(mirrorInput)

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
        dist = self.parameters.createValue(expression)
        extrudeInput = extrudes.createInput(profile, f.FeatureOperations.NewBodyFeatureOperation) 
        extentDistance = f.DistanceExtentDefinition.create(dist) 
        extrudeInput.setOneSideExtent(extentDistance, f.ExtentDirections.PositiveExtentDirection)
        if start:
            startFrom = f.FromEntityStartDefinition.create(start, self.parameters.createValue(0))
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
        cutInput.setSymmetricExtent(self.parameters.createValue("full * 2"), True)

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

    def ensureBodiesAsList(self, fBodies):
        if isinstance(fBodies, list):
            return fBodies
        bodies = []
        if isinstance(fBodies, f.Component):
            fBodies = fBodies.bRepBodies
        for b in fBodies:
            bodies.append(b)
        return bodies

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

    def getAppearances(self):
        matLib = app.materialLibraries.item(2).appearances
        self.colOuter = matLib.itemByName("Plastic - Translucent Matte (Yellow)")
        self.colOuter.copyTo(design)
        self.colMid = matLib.itemByName("Plastic - Translucent Matte (Green)")
        self.colMid.copyTo(design)
    


# todo: make a turtle graphics style method that creates lines with forward 2, rotate left 90, forward 1, rotate right 90... and return array of lines