
import adsk.core, adsk.fusion, traceback
import os, math, re, sys
from .TurtleUtils import TurtleUtils
from .TurtleParams import TurtleParams

f,core,app,ui,design,root = TurtleUtils.initGlobals()

class TurtleLayers(list):
    # pass lists, or optionally single elements if specifying layerCount. layerCount should match list sizes if one is passed.
    def __init__(self, tcomponent:'TurtleComponent', profiles:list, thicknesses:list, layerCount:int = 1):
        self.tcomponent = tcomponent
        self.component = tcomponent.component
        self.parameters = TurtleParams.instance()

        isListProfiles = isinstance(profiles, list)
        isListThickness = isinstance(thicknesses, list)
        self.layerCount = len(profiles) if isListProfiles else len(thicknesses) if isListThickness else layerCount
        self.profiles = profiles if isListProfiles else [profiles] * self.layerCount
        self.thicknesses = thicknesses if isListThickness else [thicknesses] * self.layerCount

        self.extrudes = self._extrudeAllLayers()
        self.extend(self.extrudes)

    def __getitem__(self, item) -> f.ExtrudeFeature:
        return self.extrudes.__getitem__(item)

    def bodyAt(self, extrudeIndex:int, bodyIndex:int = 0) -> f.BRepBody:
        return self[extrudeIndex].bodies.item(bodyIndex)

    def startFaceAt(self, extrudeIndex:int) -> f.BRepFace:
        return self[extrudeIndex].startFaces.item(0)

    def endFaceAt(self, extrudeIndex:int) -> f.BRepFace:
        return self[extrudeIndex].endFaces.item(0)

    def outerExtrudes(self):
        return [self[0], self[-1]]

    def getBodiesFrom(self, *extrudeIndexes:int):
        result = []
        for index in extrudeIndexes:
            result.extend(self.ensureBodiesAsList(self[index].bodies))
        return result

    def allBodies(self):
        result = []
        for index in range(self.layerCount):
            result.extend(self.ensureBodiesAsList(self[index].bodies))
        return result

    def cutWithProfiles(self, profiles):
        cuttingProfiles = profiles if isinstance(profiles, list) else [profiles] * self.layerCount
        #todo

    def _extrudeAllLayers(self):
        extrudes = []
        startFace = 0
        for i in range(self.layerCount):
            extruded = self.tcomponent.extrude(self.profiles[i], startFace, self.thicknesses[i])
            extrudes.append(extruded)
            startFace = extruded.endFaces.item(0)
        return extrudes


    def cutWithProfiles(self, profiles):
        profiles = profiles if isinstance(profiles, list) else [profiles] * len(self.layerCount)
        for i in range(len(profiles)):
            bodies = self.getBodiesFrom(i)
            pindex = min(i, len(profiles) - 1)
            for body in bodies:
                self.cutBodyWithProfile(profiles[pindex], body)

    def cutBodiesWithProfiles(self, profiles, *bodyIndexes:int):
        profiles = profiles if isinstance(profiles, list) else [profiles] * len(bodyIndexes)
        for i in range(len(bodyIndexes)):
            bodies = self.getBodiesFrom(bodyIndexes[i])
            pindex = min(i, len(profiles) - 1)
            for body in bodies:
                self.cutBodyWithProfile(profiles[pindex], body)

    def cutBodyWithProfile(self, profile:f.Profile, body:f.BRepBody):
        extrudes = body.parentComponent.features.extrudeFeatures
        cutInput = extrudes.createInput(profile, f.FeatureOperations.CutFeatureOperation) 

        # ** this will sometimes only cut to bodies first face causing an error. 
        # To be robust needs to use bodies farthest face as entity, but for now just use full*2 symetrically
        # This works in the context of joints because we have participating bodies, but is weak in a lot of cases
        #ext = f.ToEntityExtentDefinition.create(body, True)
        cutInput.setSymmetricExtent(self.parameters.createValue("full * 2"), True)

        cutInput.participantBodies = [body]
        extrude = extrudes.add(cutInput) 
        return extrude

    def mirrorLayers(self, plane:f.ConstructionPlane, isJoined:bool = False):
        mirrorFeatures = self.component.features.mirrorFeatures
        inputEntites = adsk.core.ObjectCollection.create()
        for body in self.allBodies():
            inputEntites.add(body)
        mirrorInput:f.MirrorFeatureInput = mirrorFeatures.createInput(inputEntites, plane)
        mirrorInput.isCombine = isJoined
        mirrorFeature = mirrorFeatures.add(mirrorInput)
        return mirrorFeature
            
    def cutComponent(self, profile, component:f.Component):
        if profile is None:
            return
        extrudes = self.comp.features.extrudeFeatures
        extrudeInput = extrudes.createInput(profile, f.FeatureOperations.CutFeatureOperation)
        distanceForCut = adsk.core.ValueInput.createByString("-" + pFULL) # should be all, and move to tcomponent
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