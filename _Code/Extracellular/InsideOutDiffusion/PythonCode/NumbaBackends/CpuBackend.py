
# !! clean up the args chaos: maybe group them into container objects, e.g. scalars.t_alpha, arrays.xArrSrc etc.

from NumbaBackends.CommonBackend import calcConcsInParallelXPU_kernel1, calcConcsInParallelXPU_kernel2

from numba import njit, prange


def calcConcsInParallelOnCPU( \
        srcTimeArr, srcRangeVarArr, xArrSrc, yArrSrc, zArrSrc, srcSegmSphDiamArr, xArrDst, yArrDst, zArrDst, \
        t, baseConc, diff, isEnableUptake, t_alpha, dynBaseConc, veryMinConc, \
        concScalingHelper, dstTimeIdxOrMinus1, \
        dstConcArr):
    
    _calcConcsInParallelOnCPU_kernel1( \
        srcTimeArr, srcRangeVarArr, xArrSrc, yArrSrc, zArrSrc, srcSegmSphDiamArr, xArrDst, yArrDst, zArrDst, \
        t, baseConc, diff, isEnableUptake, t_alpha, \
        dstConcArr)
    
    numSrcSegms = len(xArrSrc)
    somaActConcMinusBaseConc = dstConcArr[-1]
    scaleFactor = concScalingHelper.getConcScaleFactor(srcRangeVarArr, numSrcSegms, baseConc, dstTimeIdxOrMinus1, somaActConcMinusBaseConc)
    
    _calcConcsInParallelOnCPU_kernel2(dynBaseConc, dstConcArr, scaleFactor, veryMinConc)
    
    
@njit(parallel=True)
def _calcConcsInParallelOnCPU_kernel1( \
        srcTimeArr, srcRangeVarArr, xArrSrc, yArrSrc, zArrSrc, srcSegmSphDiamArr, xArrDst, yArrDst, zArrDst, \
        t, baseConc, diff, isEnableUptake, t_alpha, \
        dstConcArr):
    
    numSrcSegms = len(xArrSrc)
    numDstSecs = len(dstConcArr)
    
    for dstSecIdx in prange(numDstSecs):
        
        _sum = 0.0
        
        for srcSegmIdx in range(numSrcSegms):
            
            _sum += calcConcsInParallelXPU_kernel1( \
                srcTimeArr, srcRangeVarArr, xArrSrc, yArrSrc, zArrSrc, srcSegmSphDiamArr, xArrDst, yArrDst, zArrDst, \
                t, baseConc, diff, isEnableUptake, t_alpha, \
                srcSegmIdx, dstSecIdx)
                
        dstConcArr[dstSecIdx] = _sum
        
@njit(parallel=True)
def _calcConcsInParallelOnCPU_kernel2(dynBaseConc, dstConcArr, scaleFactor, veryMinConc):
    
    numDstSecs = len(dstConcArr)
    
    for dstSecIdx in prange(numDstSecs):
        
        calcConcsInParallelXPU_kernel2(dynBaseConc, dstConcArr, dstSecIdx, scaleFactor, veryMinConc)
        