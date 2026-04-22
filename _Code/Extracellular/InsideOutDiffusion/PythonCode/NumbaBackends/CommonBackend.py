
import math
from numba import njit


@njit
def calcConcsInParallelXPU_kernel1(
        srcTimeArr, srcRangeVarArr, xArrSrc, yArrSrc, zArrSrc, srcSegmSphDiamArr, xArrDst, yArrDst, zArrDst,
        t, baseConc, diff, isEnableUptake, t_alpha,
        srcSegmIdx, dstSecIdx):
    
    epsilon = 1e-8      # (um) Small number to prevent division by zero
    
    numSrcSegms = len(xArrSrc)
    
    diffFactor = 4 * diff
    
    _sum = 0.0
    
    srcSegmSphDiam = srcSegmSphDiamArr[srcSegmIdx]
    
    # !! try to use smth like np.sumsq here
    distance = math.sqrt( \
        (xArrSrc[srcSegmIdx] - xArrDst[dstSecIdx]) ** 2 + \
        (yArrSrc[srcSegmIdx] - yArrDst[dstSecIdx]) ** 2 + \
        (zArrSrc[srcSegmIdx] - zArrDst[dstSecIdx]) ** 2)
    
    geomFactor = srcSegmSphDiam / (srcSegmSphDiam + distance + epsilon)
    
    for srcStartTimeIdx in range(len(srcTimeArr) - 1):
        
        srcStartTime = srcTimeArr[srcStartTimeIdx]
        
        # For t == srcStartTime, we would have 1/0 in _getTimeFactorTerm below
        if srcStartTime >= t:
            # !! for "deferred" mode only (maybe add codeContractViolation if we hit it in "on the fly" mode)
            break
            
        delta_t = t - srcStartTime
        timeFactor = _getTimeFactorTerm(distance, diffFactor, delta_t, isEnableUptake, t_alpha)
        
        srcEndTime = srcTimeArr[srcStartTimeIdx + 1]
        
        # For t == srcEndTime, we would have 1/0 in _getTimeFactorTerm below
        if srcEndTime < t:
            delta_t = t - srcEndTime
            timeFactor -= _getTimeFactorTerm(distance, diffFactor, delta_t, isEnableUptake, t_alpha)
            
        idx = numSrcSegms * srcStartTimeIdx + srcSegmIdx
        srcConcFactor = srcRangeVarArr[idx] - baseConc
        
        _sum += srcConcFactor * geomFactor * timeFactor
        
    return _sum
    
@njit
def calcConcsInParallelXPU_kernel2(dynBaseConc, dstConcArr, dstSecIdx, scaleFactor, veryMinConc):
    
    conc = dynBaseConc + dstConcArr[dstSecIdx] * scaleFactor
    
    if conc < veryMinConc:
        conc = veryMinConc
        
    dstConcArr[dstSecIdx] = conc
    
    
@njit
def _getTimeFactorTerm(distance, diffFactor, delta_t, isEnableUptake, t_alpha):
    timeFactorTerm = math.erfc(distance / math.sqrt(diffFactor * delta_t))
    if isEnableUptake:
        timeFactorTerm *= math.exp(-delta_t / t_alpha)
    return timeFactorTerm
    