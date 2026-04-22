
# !!
# ideas to improve performance on GPU:
# * since the product "num src pts by num dst pts" is often not enough to have the full GPU occupancy, think about:
#   1. shrinking the "_threads_per_block" over time down to (1, 1) to have higher GPU occupancy on later iterations;
#   2. the usage of 3D grid arrangement instead of 2D one to include the "time" dimension (either src time or dst time)
# * for "deferred" mode, it makes sense to move the cycle by time into the GPU_kernel method to avoid switching between GPU and CPU contexts on each time step;
#   but make sure that user still can use the "Stop" button (also, maybe makes sense for "CPU" mode as well)
# * investigate if the usage of cuda.stream can help us improve performance
# * [sacrificing accuracy] add support for float32 (also, maybe makes sense for "CPU" mode as well)

# !!
# ideas to improve performance on both CPU and GPU:
# * [high priority] refactor calcConcsInParallelXPU_kernel1 to calculate erfc only once per iteration: -a*erfc + b*erfc = (b-a)*erfc
# * if we have enough memory, then cache all the cross-distances between src pts and dst pts to a matrix in ArrayCache before the calculations
#   (or, at least, cache it in cuda.shared.array so we don't need to calculate it on each call of calcConcsInParallelXPU_kernel1);
#   don't forget to deallocate it once not needed
# * [sacrificing accuracy] for very old time steps, we can calculate the diffusion as if the source was a delta-spike rather than an on-off pulse
# * [sacrificing accuracy] we can advice user enabling the uptake mechanics, and then truncate the sum forgetting very old time steps (depending on t_alpha)

# !!
# other ideas:
# * [high priority] when calculating ETA in "deferred" mode, it doesn't work well for very short iterations (especially on GPU),
#   so apply some kind of moving average with FIR or IIR filter (the latter is easier, e.g. cumulative MA or exponential MA)
# * in an exotic case of a tiny cell, a few observation points, but a long run, think about arranging threads by recordA time steps ("deferred" mode only);
#   at the same time, arranging by recordB time steps doesn't seem useful due to threads imbalance (the later time, the more calculations)

# !! replace two self._nextTimeIdx and self._lastTime with one self._nextTimeIdx

from NumbaHelpers.ConcScalingHelper import ConcScalingHelper
from NumbaHelpers.ArrayCache import ArrayCache
from NumbaBackends.CpuBackend import calcConcsInParallelOnCPU
from NumbaBackends.GpuBackend import calcConcsInParallelOnGPU

from RxdBackend import RxdBackend

import math
import time

from neuron import h

from XpuUtils import xpuUtils
from OtherInterModularUtils import codeContractViolation


class InsideOutDiffCalculator:
    
    # !! BUG: Segmentation violation if setting True here by default and just starting the test
    isUseRxD = False
    
    isFloat32or64 = False   # !! use this
    
    # Data members added in the ctor:
    #   isGpuOrCpu          (bool)
    #   _recordA            (hoc.HocObject)
    #   _recordB            (hoc.HocObject)
    #   _recorderB          (hoc.HocObject)
    #   concScalingHelper   (ConcScalingHelper)
    #   _arrayCache         (ArrayCache)
    #   _rxdBackend         (RxdBackend)
    #   _veryMinConc        (mM)
    
    # Data members added in "setThisSpeciesAndRxdParams":
    #   _varName            (str)
    #   _baseConc           (mM)
    #   _diff               (um2/ms)
    #   _isEnableUptake     (bool)
    #   _t_alpha            (ms)
    #   _uptakeReversalConc (mM)
    
    # Data member added in "onTheFlyPreRun":
    #   _lastTime           (ms)
    
    # Data members added in "deferredPreRun":
    #   _nextTimeIdx        (int)
    #   _lastIterTook       (s)
    
    
    def __init__(self, recordA, recordB, recorderB, veryMinConc):
        
        numCpuCores = xpuUtils.numCpuCores
        
        self.isGpuOrCpu = xpuUtils.isGpuOrCpuByDefault_numpy                                # (bool)
        
        self._recordA = recordA                                                             # (hoc.HocObject)
        self._recordB = recordB                                                             # (hoc.HocObject)
        self._recorderB = recorderB                                                         # (hoc.HocObject)
        
        self.concScalingHelper = ConcScalingHelper()                                        # (ConcScalingHelper)
        self._arrayCache = ArrayCache(recordA, recordB, recorderB, self.concScalingHelper)  # (ArrayCache)
        self._rxdBackend = RxdBackend(numCpuCores)                                          # (RxdBackend)
        
        self._veryMinConc = veryMinConc                                                     # (mM)
        
    def consumeHpcSettings(self, isUseRxD, isGpuOrCpu, isFloat32or64):
        self.isUseRxD = isUseRxD
        self.isGpuOrCpu = isGpuOrCpu
        self.isFloat32or64 = isFloat32or64
        
        if isUseRxD or not isGpuOrCpu:
            
            # !! not sure about this;
            #    currently commented out just so user could switch between CPU and GPU and "continue" (by the cost of a bigger memory footprint)
            # self._arrayCache.deallocateGpuArrays()
            
            return 0
            
        return xpuUtils.checkGpuPrereqs(True)
        
    # !! no need to set the RxD subset of params each time user changes species
    def setThisSpeciesAndRxdParams(self, suffix, baseConc, speciesInfo, gridRegion, genSettingsWidget):
        self._varName = suffix + 'o'                                # (str)
        self._baseConc = baseConc                                   # (mM)
        self._diff = speciesInfo.diff                               # (um2/ms)
        self._isEnableUptake = bool(speciesInfo.isEnableUptake)     # (bool)
        self._t_alpha = speciesInfo.t_alpha                         # (ms)
        self._uptakeReversalConc = speciesInfo.uptakeReversalConc   # (mM)
        
        if not self.isUseRxD:
            self._diff = genSettingsWidget.getEffectiveDiff(self._diff)
            self.concScalingHelper.setVarName(self._varName)
        else:
            ionMechName = suffix + '_ion'
            charge = h.ion_charge(ionMechName)
            if charge == 0:
                msg = f'{ionMechName} has VALENCE of 0, so RxD diffusion module will ignore its electric current "i{suffix}" and make no diffusion (NEURON behaviour). Consider switching to BrainCell diffusion module which allows you to specify some other VALENCE. Do you want to proceed with RxD anyway?'
                isCancel = not h.boolean_dialog(msg, 'Yes', 'No')
                if isCancel:
                    return 1
            self._rxdBackend.setParams(gridRegion, genSettingsWidget, self._diff, self._isEnableUptake, self._t_alpha, self._uptakeReversalConc, suffix, charge, baseConc, self._varName)
            
        return 0
        
    def onTheFlyPreRun(self):
        self._lastTime = -math.inf              # (ms)
        
        if not self.isUseRxD:
            self._arrayCache.createFixedSizeArrsAndDeallocGrowingSizeArrs(self.isGpuOrCpu)
            # !! maybe call xpuUtils.printMsgOnCalcStart here (but not on "init" click)
        else:
            self._rxdBackend.onTheFlyPreRun()
            
    def onTheFlyStep(self):
        if not self.isUseRxD:
            time = self._recordA.timeVec[-1]
            if time == self._lastTime:
                return
            self._arrayCache.createGrowingSizeArrs(self.isGpuOrCpu)
            self._calcOneStepCore(-1)
        else:
            time = self._recordB.timeVec[-1]
            if time == self._lastTime:
                return
            self._recorderB.onStep()
            
        self._lastTime = time                           # For onTheFlyStep
        self._nextTimeIdx = len(self._recordA.timeVec)  # For deferredPostRun
        
    def deferredPreRun(self):
        self._nextTimeIdx = 0           # (int)
        self._lastIterTook = math.nan   # (s)
        
        self._arrayCache.createFixedSizeArrsAndDeallocGrowingSizeArrs(self.isGpuOrCpu)
        
    def deferredPostRun(self):
        
        numTimes = len(self._recordA.timeVec)
        
        if self._nextTimeIdx == numTimes:
            return
        elif self._nextTimeIdx > numTimes:
            codeContractViolation()
            
        numSrcPts = len(self._recordA.xVec)
        numDstPts = len(self._recordB.xVec) + 1     # We'll watch one extra point (on soma)
        xpuUtils.printMsgOnCalcStart('inside-out diffusion', numSrcPts, numDstPts, self.isGpuOrCpu)
        
        self._arrayCache.createGrowingSizeArrs(self.isGpuOrCpu)
        
        # !! maybe break 2nd cycle in _calcDiffusedConcInThisDstSec once srcStartTime > t_copy
        t_copy = h.t
        h.stoprun = 0       # !! maybe not needed
        
        tic = time.time()
        
        for dstTimeIdx in range(self._nextTimeIdx, numTimes):
            
            dstTime = self._recordA.timeVec[dstTimeIdx]
            
            # !! BUG: when using tstop = 100 ms, this prints "... / 99.6 (ms)" (maybe due to round-off errors)
            iterAndTimeStr = f'    iter {dstTimeIdx + 1} of {numTimes}: t = {dstTime:g} (ms) ... '
            print(iterAndTimeStr, end='', flush=True)
            
            h.t = dstTime
            h.doNotify()    # !! just to update the time in RunControl and AltRunControl
            
            self._calcOneStepCore(dstTimeIdx)
            
            self._recorderB.onStep(dstTime)
            
            toc = time.time()
            iterTook = toc - tic
            lenIterAndTimeStr = len(iterAndTimeStr)
            spacerOrEmpty = ' ' * (38 - lenIterAndTimeStr)
            iterTookStr = f'{spacerOrEmpty}iter took {iterTook:g} (s)'
            if not math.isnan(self._lastIterTook):
                iterTookStep = iterTook - self._lastIterTook
                numRemIters = numTimes - 1 - dstTimeIdx
                a1 = iterTook + iterTookStep
                an = iterTook + numRemIters * iterTookStep
                eta = (a1 + an) / 2 * numRemIters
                if eta >= 0:
                    etaStr = self._secondsToHhMmSs(eta)
                    spacerOrEmpty = ' ' * (63 - lenIterAndTimeStr - len(iterTookStr))
                    etaStrOrEmpty = f'{spacerOrEmpty} | ETA: {etaStr}'
                else:
                    etaStrOrEmpty = ''
            else:
                etaStrOrEmpty = ''
            print(f'{iterTookStr}{etaStrOrEmpty}')
            tic = toc
            self._lastIterTook = iterTook
            
            self._nextTimeIdx = dstTimeIdx + 1  # For deferredPostRun
            self._lastTime = dstTime            # For onTheFlyStep
            
            if h.stoprun:
                break
                
        h.t = t_copy
        h.stoprun = 0
        
        print('Done!')
        
    def cleanup(self):
        self._arrayCache.deallocateAllArrays()
        self._rxdBackend.cleanup()
        
        
    def _calcOneStepCore(self, dstTimeIdxOrMinus1):
        
        arrayCache = self._arrayCache
        
        if self._isEnableUptake:
            dynBaseConc = self._uptakeReversalConc + (self._baseConc - self._uptakeReversalConc) * math.exp(-h.t / self._t_alpha)
        else:
            dynBaseConc = self._baseConc
            
        # Call the parallel core
        if self.isGpuOrCpu:
            calcConcsInParallelOnGPU( \
                arrayCache.d_srcTimeArr, arrayCache.d_srcRangeVarArr, arrayCache.d_xArrSrc, arrayCache.d_yArrSrc, arrayCache.d_zArrSrc, arrayCache.d_srcSegmSphDiamArr, arrayCache.d_xArrDst, arrayCache.d_yArrDst, arrayCache.d_zArrDst, \
                h.t, self._baseConc, self._diff, self._isEnableUptake, self._t_alpha, dynBaseConc, self._veryMinConc, \
                self.concScalingHelper, dstTimeIdxOrMinus1, \
                arrayCache.d_dstConcArr)
            
            # We could skip this step and use arrayCache.d_dstConcArr directly in the cycle below, but this would lead to much worse performance
            arrayCache.copyDstConcArrFromGpuToHost()
        else:
            calcConcsInParallelOnCPU( \
                arrayCache.srcTimeArr, arrayCache.srcRangeVarArr, arrayCache.xArrSrc, arrayCache.yArrSrc, arrayCache.zArrSrc, arrayCache.srcSegmSphDiamArr, arrayCache.xArrDst, arrayCache.yArrDst, arrayCache.zArrDst, \
                h.t, self._baseConc, self._diff, self._isEnableUptake, self._t_alpha, dynBaseConc, self._veryMinConc, \
                self.concScalingHelper, dstTimeIdxOrMinus1, \
                arrayCache.dstConcArr)
            
        # Write the calculated concs from NumPy array to the sections
        for dstSec_ref, conc in zip(self._recorderB.list_ref, arrayCache.dstConcArr):
            setattr(dstSec_ref.sec, self._varName, conc)
            
    def _secondsToHhMmSs(self, seconds):
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f'{hours:02}:{minutes:02}:{seconds:02}'
        