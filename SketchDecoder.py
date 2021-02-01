
import adsk.core, adsk.fusion, adsk.cam, traceback
import os, math, re
from .TurtleUtils import TurtleUtils
from .TurtleComponent import TurtleComponent
from .TurtleSketch import TurtleSketch
from .TurtleParams import TurtleParams
from .TurtlePath import TurtlePath
from .TurtleLayers import TurtleLayers

f,core,app,ui,design,root = TurtleUtils.initGlobals()

class SketchDecoder:
    def __init__(self):
        # self.sketch:f.Sketch = TurtleUtils.ensureSelectionIsType(f.Sketch)
        # if not self.sketch:
        #     return
        # self.tcomponent = TurtleComponent.createFromSketch(self.sketch)
        self.decodeFromSketch()
        # TurtleUtils.selectEntity(self.sketch)

    def decodeFromSketch(self):
        data = self.getTestData()
        
        self.pointValues = data["Points"]
        self.chains = data["Chains"]
        self.constraints = data["Constraints"]
        self.dimensions = data["Dimensions"]
        self.curves = self.parseCurves(self.chains)

        print(self.curves)

    def parseCurves(self, chains):
        for chain in chains:
            segs = chain.split(" ")
            for seg in segs:
                parse = re.findall(r"([LACEO])(x?)([pv][0-9\[\]\.,]*)([pv][0-9\[\]\.,]*)?([pv][0-9\[\]\.,]*)?([pv][0-9\[\]\.,]*)", seg) 
                #parse = regex.match(r"([LACEO])(x?)([pv][0-9])+")
                print(seg)
                print(parse)




    def getTestData(self):
        return  {
        'Points':[
        [0.0,0.0],[1.53,-3.17],[4.25,-3.9],[4.25,-1.63],[7.13,-1.51],[7.13,-7.08],[4.0,-8.66],[-0.37,-6.66],[-4.03,-3.33],[-4.49,-2.42],[-1.93,-1.13],[-1.47,-2.04],[-2.83,-5.53],[-0.82,-6.45],[8.13,-3.24],[5.69,-1.57],[5.69,-3.18],[-1.83,-7.84],[-1.18,-7.24],[9.77,-7.79],[9.14,-9.18],[10.4,-6.41],[10.43,-8.09],[9.11,-7.49],[11.5,-5.0],[13.65,-5.07],[12.61,-7.19]
        ],
        'Chains':[
        'Lp2p3 Lp3p4 Lp4p5 Lp5p6 Lp6p7 Lp7p1 Lp1p2', # 0-6
        'Lp9p10 Lp10p11 Lp11p8 Lp8p9', # 7-10
        'Lp12p13 Ap17p18p13', # 11-12
        'Cp14v[1.0]', # 13
        'Lxp15p16', # 14
        'Ep19v[0.63,1.38,0.0]v[1.52]v[0.73]', # 15
        'Lxp20p21', # 16
        'Lxp22p23', # 17
        'Op24p26p25v[3.49]', # 18
        ],
        'Constraints':[
        'VHc0','PEc10c3','PEc7c10','TAc13c2','MIc1p15','VHc14','SYc0c2c14','EQc9c7','PAc8c10','CLc4c11','TAc12c11','PEc16c4','COp20c15','COp21c15','COp22c15','COp23c15'
        ],
        'Dimensions':[
        'SLDp5p5v35mm','SLDp11p11v30mm','SODc9vtest','SDDc13v20mm'
        ]
        }