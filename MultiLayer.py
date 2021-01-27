import adsk.core, adsk.fusion, traceback
import os, math, re, sys
from .Utils import Utils
from .TurtleParams import TurtleParams

f,core,app,ui,design,root = Utils.initGlobals()

class MultiLayer(list):
    # pass lists, or optionally single elements if specifying layerCount. layerCount should match list sizes if one is passed.
    def __init__(self, component:f.Component, profiles:list, thicknesses:list, appearances:list = [], layerCount:int = 1):
        self.component = component
        self.parameters = TurtleParams.instance()
        self.appearances = appearances # todo: make appearances based on thickness

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
            extruded = self.extrude(self.profiles[i], startFace, self.thicknesses[i])
            extrudes.append(extruded)
            self.colorExtrudedBodies(i, extruded)
            startFace = extruded.endFaces.item(0)
        return extrudes

    def colorExtrudedBodies(self, appearanceIndex:int, extruded:f.ExtrudeFeature):
        if len(self.appearances) > 0:
            index = min(len(self.appearances) - 1, appearanceIndex)
            for body in extruded.bodies:
                body.appearance = self.appearances[index]

    def cutBodiesWithProfiles(self, profiles, *bodyIndexes:int):
        profiles = profiles if isinstance(profiles, list) else [profiles] * len(bodyIndexes)
        for i in range(len(bodyIndexes)):
            bodies = self.getBodiesFrom(bodyIndexes[i])
            pindex = min(i, len(profiles) - 1)
            for body in bodies:
                self.cutBodyWithProfile(profiles[pindex], body)

    def extrude(self, profile, start, expression):
        if profile is None:
            return
        extrudes = self.component.features.extrudeFeatures
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