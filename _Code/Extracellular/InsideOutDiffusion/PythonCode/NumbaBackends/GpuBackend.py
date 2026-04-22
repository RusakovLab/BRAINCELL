
# !! maybe BUG: the difference between the results obtained with CPU and GPU is unexpectedly more significant than the difference between the results obtained with two runs on GPU

# !! clean up the args chaos: maybe group them into container objects, e.g. scalars.t_alpha, arrays.d_xArrSrc etc.


from NumbaBackends.CommonBackend import calcConcsInParallelXPU_kernel1, calcConcsInParallelXPU_kernel2

from numba import cuda
from numba.core.errors import NumbaPerformanceWarning

import warnings
import numpy as np


# The number of threads in a block (2D)
_threads_per_block = (16, 16)   # 256 threads total, arranged in a 16x16 grid


def calcConcsInParallelOnGPU( \
        d_srcTimeArr, d_srcRangeVarArr, d_xArrSrc, d_yArrSrc, d_zArrSrc, d_srcSegmSphDiamArr, d_xArrDst, d_yArrDst, d_zArrDst, \
        t, baseConc, diff, isEnableUptake, t_alpha, dynBaseConc, veryMinConc, \
        concScalingHelper, dstTimeIdxOrMinus1, \
        d_dstConcArr):
    
    numSrcSegms = len(d_xArrSrc)
    numDstSecs = len(d_dstConcArr)
    
    # The number of blocks in the grid (2D)
    blocks_x = (numSrcSegms + _threads_per_block[0] - 1) // _threads_per_block[0]
    blocks_y = (numDstSecs + _threads_per_block[1] - 1) // _threads_per_block[1]
    blocks_per_grid = (blocks_x, blocks_y)
    
    if cuda.runtime.get_version()[0] >= 11:
        cuda.cudadrv.driver.device_memset(d_dstConcArr, 0, d_dstConcArr.nbytes)     # "memset" was introduced only in 2020
    else:
        warnings.simplefilter("ignore", category=NumbaPerformanceWarning)   # The warning in the kernel 2 is enough
        try:
            _calcConcsInParallelOnGPU_kernel1[blocks_per_grid[1], _threads_per_block[1]](d_dstConcArr)
        finally:
            warnings.simplefilter("default", category=NumbaPerformanceWarning)
            
    _calcConcsInParallelOnGPU_kernel2[blocks_per_grid, _threads_per_block]( \
        d_srcTimeArr, d_srcRangeVarArr, d_xArrSrc, d_yArrSrc, d_zArrSrc, d_srcSegmSphDiamArr, d_xArrDst, d_yArrDst, d_zArrDst, \
        t, baseConc, diff, isEnableUptake, t_alpha, \
        d_dstConcArr)
    
    somaActConcMinusBaseConc = d_dstConcArr[-1]
    scaleFactor = concScalingHelper.getConcScaleFactor(d_srcRangeVarArr, numSrcSegms, baseConc, dstTimeIdxOrMinus1, somaActConcMinusBaseConc)
    
    warnings.simplefilter("ignore", category=NumbaPerformanceWarning)   # The warning in the kernel 2 is enough
    try:
        # We don't combine kernels 2 and 3 into one just to ensure all blocks are synced
        _calcConcsInParallelOnGPU_kernel3[blocks_per_grid[1], _threads_per_block[1]](dynBaseConc, d_dstConcArr, scaleFactor, veryMinConc)
    finally:
        warnings.simplefilter("default", category=NumbaPerformanceWarning)
        
        
@cuda.jit
def _calcConcsInParallelOnGPU_kernel1(d_dstConcArr):
    
    tx = cuda.threadIdx.x
    bx = cuda.blockIdx.x
    dstSecIdx = bx * cuda.blockDim.x + tx
    
    if dstSecIdx < len(d_dstConcArr):
        d_dstConcArr[dstSecIdx] = 0
        
@cuda.jit
def _calcConcsInParallelOnGPU_kernel2( \
        d_srcTimeArr, d_srcRangeVarArr, d_xArrSrc, d_yArrSrc, d_zArrSrc, d_srcSegmSphDiamArr, d_xArrDst, d_yArrDst, d_zArrDst, \
        t, baseConc, diff, isEnableUptake, t_alpha, \
        d_dstConcArr):
    
    numSrcSegms = len(d_xArrSrc)
    numDstSecs = len(d_dstConcArr)
    
    bx, by = cuda.blockIdx.x, cuda.blockIdx.y
    tx, ty = cuda.threadIdx.x, cuda.threadIdx.y
    
    # Shared memory for partial results
    ds_sums1 = cuda.shared.array(shape=_threads_per_block, dtype=np.float64)
    
    srcSegmIdx = bx * cuda.blockDim.x + tx
    dstSecIdx = by * cuda.blockDim.y + ty
    
    if srcSegmIdx < numSrcSegms and dstSecIdx < numDstSecs:
        ds_sums1[tx, ty] = calcConcsInParallelXPU_kernel1( \
            d_srcTimeArr, d_srcRangeVarArr, d_xArrSrc, d_yArrSrc, d_zArrSrc, d_srcSegmSphDiamArr, d_xArrDst, d_yArrDst, d_zArrDst, \
            t, baseConc, diff, isEnableUptake, t_alpha, \
            srcSegmIdx, dstSecIdx)
        
    # Ensure all threads have written to the shared memory
    cuda.syncthreads()
    
    if tx == 0 and dstSecIdx < numDstSecs:
        
        # Sum up along the x-axis within the block
        sum2 = 0.0
        for i in range(cuda.blockDim.x):
            sum2 += ds_sums1[i, ty]
            
        # Sum up along the x-axis by all blocks (this is the line of code that makes the results slightly different from run to run)
        cuda.atomic.add(d_dstConcArr, dstSecIdx, sum2)
        
@cuda.jit
def _calcConcsInParallelOnGPU_kernel3(dynBaseConc, d_dstConcArr, scaleFactor, veryMinConc):
    
    tx = cuda.threadIdx.x
    bx = cuda.blockIdx.x
    dstSecIdx = bx * cuda.blockDim.x + tx
    
    if dstSecIdx < len(d_dstConcArr):
        
        calcConcsInParallelXPU_kernel2(dynBaseConc, d_dstConcArr, dstSecIdx, scaleFactor, veryMinConc)
        