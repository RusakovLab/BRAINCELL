
import os

from numba import cuda as nb_cuda   # This one is installed with Anaconda by default (but without cudatoolkit) ...
# import cupy as cp                 # ... and this one is NOT installed by default

from neuron import h


class XpuUtils:
    
    # https://stackoverflow.com/questions/63823395/how-can-i-get-the-number-of-cuda-cores-in-my-gpu-using-python-and-numba
    # The dictionary below needs to be extended as new devices become
    # available, and currently does not account for all Jetson devices
    cc_cores_per_SM_dict = {
        (2,0) : 32,
        (2,1) : 48,
        (3,0) : 192,
        (3,5) : 192,
        (3,7) : 192,
        (5,0) : 128,
        (5,2) : 128,
        (6,0) : 64,
        (6,1) : 128,
        (7,0) : 64,
        (7,5) : 64,
        (8,0) : 64,
        (8,6) : 128,
        (8,9) : 128,
        (9,0) : 128 }
    
    # Data members added in the ctor:
    #   numCpuCores
    #   numGpuCoresOrMinus1
    #   isGpuOrCpuByDefault_numpy
    #   isGpuOrCpuByDefault_cupy
    
    def __init__(self):
        
        self.numCpuCores = os.cpu_count()
        
        numGpuCoresOrMinus1_numpy = self._getNumGpuCoresOrMinus1_numpy()
        numGpuCoresOrMinus1_cupy = self._getNumGpuCoresOrMinus1_cupy()
        self.numGpuCoresOrMinus1 = numGpuCoresOrMinus1_numpy if numGpuCoresOrMinus1_numpy != -1 else numGpuCoresOrMinus1_cupy
        
        self.isGpuOrCpuByDefault_numpy = numGpuCoresOrMinus1_numpy > self.numCpuCores
        self.isGpuOrCpuByDefault_cupy = numGpuCoresOrMinus1_cupy > self.numCpuCores
        
    def checkGpuPrereqs(self, isIODorLFP):
        
        msgTempl = 'Cannot use GPU until you execute \"conda install {}\" in Anaconda Prompt and restart BrainCell.'
        cpuFallbackMsg = 'CPU will be used instead.'
        
        try:
            nb_cuda.detect()
        except nb_cuda.cudadrv.error.CudaSupportError:
            h.mwh.showWarningBox('No GPU detected.')
            return True
        except nb_cuda.cudadrv.error.CudaDriverError:
            line1 = 'No GPU driver detected.'
            if isIODorLFP:
                h.mwh.showWarningBox(line1)
            else:
                h.mwh.showWarningBox(line1, cpuFallbackMsg)
            return True
            
        if isIODorLFP:
            if not nb_cuda.is_available():
                h.mwh.showWarningBox(msgTempl.format('cudatoolkit'))
                return True
        else:
            try:
                import cupy as cp
            except ModuleNotFoundError:
                h.mwh.showWarningBox(msgTempl.format('cupy'), 'Until then, {}'.format(cpuFallbackMsg))
                return True
                
        return False
        
    def printMsgOnCalcStart(self, what, numSrcPts, numDstPts, isGpuOrCpu):
        
        if isGpuOrCpu:
            numCores = self.numGpuCoresOrMinus1
            device = 'GPU'
        else:
            numCores = self.numCpuCores
            device = 'CPU'
        print(f'\nCalculating {what} from {numSrcPts} src pts to {numDstPts} dst pts with {numCores} {device} cores ...')
        # !! for GPU, ideally print the number of actually used cores
        
        
    def _getNumGpuCoresOrMinus1_numpy(self):
        
        if not nb_cuda.is_available():
            return -1
            
        device = nb_cuda.get_current_device()
        my_cc = device.compute_capability
        try:
            cores_per_sm = self.cc_cores_per_SM_dict[my_cc]
        except KeyError:
            return -1
            
        my_sms = getattr(device, 'MULTIPROCESSOR_COUNT')
        total_cores = cores_per_sm * my_sms
        
        return total_cores
        
    def _getNumGpuCoresOrMinus1_cupy(self):
        
        try:
            import cupy as cp
        except ModuleNotFoundError:
            return -1
            
        if not cp.cuda.is_available():
            return -1
            
        device_id = cp.cuda.runtime.getDevice()
        device_properties = cp.cuda.runtime.getDeviceProperties(device_id)
        my_cc = device_properties['major'], device_properties['minor']
        try:
            cores_per_sm = self.cc_cores_per_SM_dict[my_cc]
        except KeyError:
            return -1
            
        my_sms = device_properties['multiProcessorCount']
        total_cores = cores_per_sm * my_sms
        
        return total_cores
        
        
xpuUtils = XpuUtils()
