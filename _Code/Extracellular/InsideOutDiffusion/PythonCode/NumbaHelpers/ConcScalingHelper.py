
# !! currently we use the middle segment in the middle section of soma;
#    alternatively, we can use: geometrical centre of soma, centre of mass for soma, geometrical centre of cell, centre of mass for cell etc.
#    (in all 4 cases we can find the segment closest to this point using KDTree);
#    also, it would make sense to check if the selected section has the diffusion source mechanism inserted


import sys
import math

from neuron import h

from OtherInterModularUtils import codeContractViolation


class ConcScalingHelper:
    
    # Data members added in the ctor:
    #   _somaSrcSec_ref         (hoc.HocObject)
    #   _somaSrcSegmIdx         (int)
    #   _somaSrcSegm            (nrn.Segment)
    #   xSoma, ySoma, zSoma     (float)
    #   _eps                    (float)
    
    # Data members added in other methods:
    #   _somaSrcSegmFlatIdx     (int)
    #   _varName                (str)
    
    def __init__(self):
        
        secInListIdx = int(len(h.soma_ref) / 2)
        self._somaSrcSec_ref = h.soma_ref[secInListIdx]
        
        xSegm_vec = h.Vector()
        ySegm_vec = h.Vector()
        zSegm_vec = h.Vector()
        h.interpEachSegmCentreCoordsFromSec3DPointCoords_CalledFromPython(self._somaSrcSec_ref, xSegm_vec, ySegm_vec, zSegm_vec)
        
        nseg = self._somaSrcSec_ref.sec.nseg
        if len(xSegm_vec) != nseg:
            codeContractViolation()
            
        self._somaSrcSegmIdx = int(nseg / 2)
        u = (0.5 + self._somaSrcSegmIdx) / nseg
        self._somaSrcSegm = self._somaSrcSec_ref.sec(u)
        
        self.xSoma = xSegm_vec[self._somaSrcSegmIdx]
        self.ySoma = ySegm_vec[self._somaSrcSegmIdx]
        self.zSoma = zSegm_vec[self._somaSrcSegmIdx]
        
        self._eps = math.sqrt(sys.float_info.epsilon)
        
    def preRun(self, srcList_ref):
        
        self._somaSrcSegmFlatIdx = 0
        
        isFound = False
        for sec_ref in srcList_ref:
            if sec_ref.sec == self._somaSrcSec_ref.sec:
                isFound = True
                break
            self._somaSrcSegmFlatIdx += sec_ref.sec.nseg
            
        if not isFound:
            codeContractViolation()
            
        self._somaSrcSegmFlatIdx += self._somaSrcSegmIdx
        
    def setVarName(self, varName):
        self._varName = varName
        
    def getConcScaleFactor(self, srcRangeVarArr, numSrcSegms, baseConc, dstTimeIdxOrMinus1, somaActConcMinusBaseConc):
        
        if dstTimeIdxOrMinus1 != -1:
            # "Deferred" mode
            
            idx = numSrcSegms * dstTimeIdxOrMinus1 + self._somaSrcSegmFlatIdx
            somaExpConc = srcRangeVarArr[idx]
        else:
            # "On the fly" mode
            # !! maybe get rid of this IF branch and read srcRangeVarArr[idx] like for "Deferred" mode just above (but we need to know dstTimeIdx for "On the fly" mode)
            
            # !! make sure it coincides with srcRangeVarArr[idx]
            somaExpConc = getattr(self._somaSrcSegm, self._varName)
            
        if abs(somaActConcMinusBaseConc) > self._eps:                           # !! fragile
            scaleFactor = (somaExpConc - baseConc) / somaActConcMinusBaseConc   #
        else:
            scaleFactor = 1.0
            
        # !!
        # print("\nsomaExpConc: ", somaExpConc)
        # print("somaActConc: ", somaActConcMinusBaseConc + baseConc)
        # print("scaleFactor: ", scaleFactor)
        
        return scaleFactor
        