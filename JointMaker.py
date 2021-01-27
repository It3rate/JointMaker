
import adsk.core, adsk.fusion, adsk.cam, traceback
import os, math, re
from .TurtleUtils import TurtleUtils
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

class JointMaker:
    def __init__(self):
        self.baseSketch:f.Sketch = self.ensureSelectionIsType(f.Sketch)
        if not self.baseSketch:
            return
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType

        self.rootTSketch = TurtleSketch(self.baseSketch)

        self.parameters = TurtleParams.instance()
        self.parameters.addParams(
            pMID, 3,
            pOUTER, 2,
            pFULL, "mid + outer * 2",
            pLIP, 1,
            pSHELF_WIDTH, 40,
            pZIP_WIDTH, 1,
            pZIP_LENGTH, "zipWidth * 10")

        self.actSel = ui.activeSelections

        self.componentCounter = 0

        fullProfile = self.rootTSketch.combineProfiles()
        self.shelfLines = self.rootTSketch.getSingleLines()

        self.createWalls(fullProfile)
        self.createShelves()
    
    def createWalls(self, profile):
        comp = self.rootTSketch.component
        layers = TurtleLayers(comp, profile, [pOUTER, pMID, pOUTER])

        self.midPlane = self.rootTSketch.createOffsetPlane(pSHELF_WIDTH, root, "MidPlane")

        tsketch = TurtleSketch.createWithPlane(comp, layers.startFaceAt(0)) 
        fullProfile = self.createWallOuterCuts(tsketch)
        layers.cutBodiesWithProfiles(fullProfile, 0)

        tsketch = TurtleSketch.createWithPlane(comp, layers.startFaceAt(1))
        fullProfile = self.createWallInsideCuts(tsketch)
        layers.cutBodiesWithProfiles(fullProfile, 1,2)
        layers.mirrorLayers(self.midPlane, False)

    def createShelves(self):
        for idx, line in enumerate(self.shelfLines):
            layers = self.createHalfShelf(line, idx)
            layers.mirrorLayers(self.midPlane, True)
    
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

    def createWallOuterCuts(self, tsketch:TurtleSketch):
        for idx, line in enumerate(self.shelfLines):
            self.createWallZipCutProfile(tsketch, line)
        fullProfile = tsketch.combineProfiles()
        tsketch.removeLargestProfile(fullProfile)
        return fullProfile

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

    def createHalfShelf(self, line:f.SketchLine, index) -> TurtleLayers:
        comp = self.createComponent("shelf"+ str(index))
        plane = self.rootTSketch.createOrthoganalPlane(line, comp)
        tsketch = TurtleSketch.createWithPlane(comp, plane)
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
        
        layers = TurtleLayers(comp, [fullProfile,cutProfile,fullProfile], [pOUTER, pMID, pOUTER])
        return layers
    

    def createComponent(self, name):
        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occ.component.name = name
        return occ.component

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


