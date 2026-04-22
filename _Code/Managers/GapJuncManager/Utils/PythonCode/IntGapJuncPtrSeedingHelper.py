
from neuron import h

import numpy as np
from scipy.spatial import KDTree


class IntGapJuncPtrSeedingHelper:
    
    _segm3DPtsKDTree = None
    
    # !! maybe split this list of tuples into two: a list of sections and an np.array of connection points (to save memory and performance a bit)
    _segmGlobalIdxToSecAndSegmLocalIdxListOfTuples = None
    
    
    # !! some code dup. with LFPCalculator._cacheData
    def cacheAllSegms3DCoords(self):
        
        totalNumSegms = int(h.getTotalNumSegms())
        
        segm3DPtsArray = np.empty((totalNumSegms, 3))
        
        self._segmGlobalIdxToSecAndSegmLocalIdxListOfTuples = [None] * totalNumSegms
        
        xSegm_vec = h.Vector()
        ySegm_vec = h.Vector()
        zSegm_vec = h.Vector()
        
        segmGlobalIdx = 0
        for sec in h.allsec():
            h.interpEachSegmCentreCoordsFromSec3DPointCoords_CalledFromPython(h.SectionRef(sec), xSegm_vec, ySegm_vec, zSegm_vec)
            
            for segmLocalIdx in range(sec.nseg):
                # !! maybe np.array allows doing such a slice assignment without the cycle by segmLocalIdx
                segm3DPtsArray[segmGlobalIdx, 0] = xSegm_vec[segmLocalIdx]
                segm3DPtsArray[segmGlobalIdx, 1] = ySegm_vec[segmLocalIdx]
                segm3DPtsArray[segmGlobalIdx, 2] = zSegm_vec[segmLocalIdx]
                
                self._segmGlobalIdxToSecAndSegmLocalIdxListOfTuples[segmGlobalIdx] = (sec, segmLocalIdx)    # !! maybe just save the segm obj here
                
                segmGlobalIdx += 1
                
        self._segm3DPtsKDTree = KDTree(segm3DPtsArray)
        
    def findSegmClosestToThis3DPoint(self, xPtrWanted, yPtrWanted, zPtrWanted, bestSecList_ref):
        
        query3DPt = np.array([xPtrWanted, yPtrWanted, zPtrWanted])
        
        _, segmGlobalIdx = self._segm3DPtsKDTree.query(query3DPt)   # Euclidean distance by default
        
        secAndSegmLocalIdxTuple = self._segmGlobalIdxToSecAndSegmLocalIdxListOfTuples[segmGlobalIdx]
        sec = secAndSegmLocalIdxTuple[0]
        segmLocalIdx = secAndSegmLocalIdxTuple[1]
        
        bestSec_ref = h.SectionRef(sec)
        bestSecList_ref.append(bestSec_ref)
        
        bestConnectionPoint = (segmLocalIdx + 0.5) / sec.nseg
        return bestConnectionPoint
        
    def destroyCache(self):
        self._segm3DPtsKDTree = None
        self._segmGlobalIdxToSecAndSegmLocalIdxListOfTuples = None
        
        
intGapJuncPtrSeedingHelper = IntGapJuncPtrSeedingHelper()
