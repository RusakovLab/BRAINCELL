
import numpy as np
from numba import cuda


class ArrayCache:
    
    # Data members added in the ctor:
    #   _recordA            (hoc.HocObject)
    #   _recordB            (hoc.HocObject)
    #   _recorderB          (hoc.HocObject)
    #   _concScalingHelper  (ConcScalingHelper)
    
    # Data members added in other methods:
    #   All NumPy arrays
    #   All CUDA arrays (only if isGpuOrCpu)
    
    
    def __init__(self, recordA, recordB, recorderB, concScalingHelper):
        self._recordA = recordA
        self._recordB = recordB
        self._recorderB = recorderB
        self._concScalingHelper = concScalingHelper
        
    def createFixedSizeArrsAndDeallocGrowingSizeArrs(self, isGpuOrCpu):
        
        # Create NumPy arrays from the fixed-size NEURON Vector-s (no actual data copying)
        
        self.xArrSrc = self._recordA.xVec.as_numpy()
        self.yArrSrc = self._recordA.yVec.as_numpy()
        self.zArrSrc = self._recordA.zVec.as_numpy()
        self.srcSegmSphDiamArr = self._recordA.segmSphDiamVecOrNil.as_numpy()
        
        self.xArrDst = self._createOneDstCoordsArr(self._recordB.xVec, self._concScalingHelper.xSoma)
        self.yArrDst = self._createOneDstCoordsArr(self._recordB.yVec, self._concScalingHelper.ySoma)
        self.zArrDst = self._createOneDstCoordsArr(self._recordB.zVec, self._concScalingHelper.zSoma)
        
        # Allocate memory for the recorded NumPy array
        self.dstConcArr = np.empty(len(self._recorderB.list_ref) + 1)   # We'll watch one extra point (on soma)
        
        # Deallocate memory of the NumPy arrays
        self.srcTimeArr = None
        self.srcRangeVarArr = None
        
        if isGpuOrCpu:
            
            # Allocate CUDA arrays on the device (GPU)
            
            self.d_xArrSrc = cuda.to_device(self.xArrSrc)
            self.d_yArrSrc = cuda.to_device(self.yArrSrc)
            self.d_zArrSrc = cuda.to_device(self.zArrSrc)
            self.d_srcSegmSphDiamArr = cuda.to_device(self.srcSegmSphDiamArr)
            
            self.d_xArrDst = cuda.to_device(self.xArrDst)
            self.d_yArrDst = cuda.to_device(self.yArrDst)
            self.d_zArrDst = cuda.to_device(self.zArrDst)
            
            self.d_dstConcArr = cuda.device_array(len(self.dstConcArr), dtype=np.float64)
            
            # Deallocate memory of the CUDA arrays
            self.d_srcTimeArr = None
            self.d_srcRangeVarArr = None
            
    def createGrowingSizeArrs(self, isGpuOrCpu):
        
        # Create NumPy arrays from the growing-size NEURON Vector-s (no actual data copying)
        self.srcTimeArr = self._recordA.timeVec.as_numpy()
        self.srcRangeVarArr = self._recordA.rangeVarVec.as_numpy()
        
        if isGpuOrCpu:
            # Allocate CUDA arrays on the device (GPU)
            self.d_srcTimeArr = cuda.to_device(self.srcTimeArr)
            self.d_srcRangeVarArr = cuda.to_device(self.srcRangeVarArr)
            
    def copyDstConcArrFromGpuToHost(self):
        
        # Copy the result back to the host
        self.d_dstConcArr.copy_to_host(self.dstConcArr)
        
    def deallocateGpuArrays(self):
        
        self.d_xArrSrc = None
        self.d_yArrSrc = None
        self.d_zArrSrc = None
        self.d_srcSegmSphDiamArr = None
        
        self.d_xArrDst = None
        self.d_yArrDst = None
        self.d_zArrDst = None
        
        self.d_dstConcArr = None
        
    def deallocateAllArrays(self):
        
        self.deallocateGpuArrays()
        
        self.xArrSrc = None
        self.yArrSrc = None
        self.zArrSrc = None
        self.srcSegmSphDiamArr = None
        
        self.xArrDst = None
        self.yArrDst = None
        self.zArrDst = None
        
        self.dstConcArr = None
        
        
    def _createOneDstCoordsArr(self, dstCoordsVec, somaCoord):
        
        # We'll watch one extra point (on soma)
        # dstCoordsArr = dstCoordsVec.as_numpy()
        
        numDstPts = len(dstCoordsVec)
        dstCoordsArr = np.empty(numDstPts + 1)
        dstCoordsArr[ : numDstPts] = dstCoordsVec
        dstCoordsArr[numDstPts] = somaCoord
        
        return dstCoordsArr
        