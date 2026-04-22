
from neuron import h

from enum import IntEnum

from OtherInterModularUtils import codeContractViolation


class EnumParamCats(IntEnum):
    # The higher value, the deeper changes
    none = 0
    anim = 1
    rxd = 2
    biophys = 3
    modifGeom = 4
    baseGeom = 5
    
    
class DirtyStatesHelper:
    
    # Data member: dirtyParamCat
    
    def __init__(self):
        self.dirtyParamCat = EnumParamCats.none
        
    def onParamChange(self, paramCat):
        
        if paramCat == EnumParamCats.none:
            codeContractViolation()
            
        self.dirtyParamCat = max(self.dirtyParamCat, paramCat)
        
        h.altRunControlWidget.isInited = 0
        
    def onAllClear(self):
        self.dirtyParamCat = EnumParamCats.none
        