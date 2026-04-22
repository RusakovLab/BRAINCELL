
# !! BUG: it looks like calling rxd.nthread(numCpuCores) gives us worse performance than calling rxd.nthread(1)

# !! maybe remove "with mwhw.PleaseWaitBox" below because RxD seems to have the most time-consuming stage later on h.finitialize() call


from neuron import h, rxd

import MsgWarnHelperWrappers as mwhw
from OtherInterModularUtils import codeContractViolation

# https://www.neuron.yale.edu/neuron/docs/extracellular-diffusion
# https://nrn.readthedocs.io/en/latest/rxd-tutorials/extracellular.html
# https://neuron.yale.edu/neuron/static/docs/rxd/tut_main.html

class RxdBackend:
    
    # Data members added in "setParams":
    #   _xMin, _yMin, _zMin                                         (um)
    #   _xMax, _yMax, _zMax                                         (um)
    #   _dw                                                         (3-tuple of um)
    #   _volumeFraction, _tortuosityOrNone, _permeabilityOrNone     (float)
    #   _diff                                                       (um2/ms)
    #   _isEnableUptake                                             (bool)
    #   _t_alpha                                                    (ms)
    #   _uptakeReversalConc                                         (mM)
    #   _suffix                                                     (str)
    #   _charge                                                     (float)
    #   _initial                                                    (mM)
    #   _ecs_boundary_conditions                                    (mM or None)
    #   _varName                                                    (str)
    
    # Data members added in "onTheFlyPreRun":
    #   _ecs                                                        (rxd.Extracellular)
    #   _species                                                    (rxd.Species)
    #   _uptakeRate                                                 (rxd.Rate)
    
    def __init__(self, numCpuCores):
        
        # !! is it OK to call it before rxd.options.enable.extracellular = True ?
        # !! code dup. with SimMyelinatedAxonCore
        rxd.nthread(numCpuCores)
        
    def setParams(self, gridRegion, genSettingsWidget, diff, isEnableUptake, t_alpha, uptakeReversalConc, suffix, charge, baseConc, varName):
        
        self._xMin, self._yMin, self._zMin, self._xMax, self._yMax, self._zMax, self._dw = self._getGridParams(gridRegion)
        
        self._volumeFraction = genSettingsWidget.volumeFraction
        self._tortuosityOrNone = genSettingsWidget.tortuosityOrMinus1 if genSettingsWidget.tortuosityOrMinus1 != -1 else None
        self._permeabilityOrNone = genSettingsWidget.permeabilityOrMinus1 if genSettingsWidget.permeabilityOrMinus1 != -1 else None
        self._diff = diff
        self._isEnableUptake = isEnableUptake
        self._t_alpha = t_alpha
        self._uptakeReversalConc = uptakeReversalConc
        self._suffix = suffix
        self._charge = charge
        self._initial = baseConc
        if genSettingsWidget.rxdIsDirichletOrNeumannBndConds:
            self._ecs_boundary_conditions = baseConc
        else:
            self._ecs_boundary_conditions = None
        self._varName = varName
        
    def onTheFlyPreRun(self):
        
        # When self._isEnableUptake = True, this call is a must to avoid NEURON RxD internal error on 2nd run
        self.cleanup()
        
        rxd.options.enable.extracellular = True
        
        with mwhw.PleaseWaitBox('Initializing RxD module.'):
            
            # 1. Where
            self._ecs = rxd.Extracellular(self._xMin, self._yMin, self._zMin,
                                          self._xMax, self._yMax, self._zMax,
                                          self._dw, volume_fraction=self._volumeFraction, tortuosity=self._tortuosityOrNone, permeability=self._permeabilityOrNone)
            
            # 2. Who (depends on Where)
            self._species = rxd.Species(self._ecs, d=self._diff, name=self._suffix, charge=self._charge, initial=self._initial, ecs_boundary_conditions=self._ecs_boundary_conditions)
            
            if self._isEnableUptake:
                # 3. How (depends on Who)
                self._uptakeRate = rxd.Rate(self._species, (self._uptakeReversalConc - self._species) / self._t_alpha)
                
    def cleanup(self):
        self._uptakeRate = None
        self._species = None
        self._ecs = None
        rxd.options.enable.extracellular = False
        
        
    # !! a lot of code dup. with hoc:GridOfSections.initForRegularGrid (need to extract a common util)
    def _getGridParams(self, gridRegion):
        
        nx = int(gridRegion.nx)
        ny = int(gridRegion.ny)
        nz = int(gridRegion.nz)
        
        xMin = gridRegion.xyzCentre[0] - gridRegion.xyzRange[0] / 2
        yMin = gridRegion.xyzCentre[1] - gridRegion.xyzRange[1] / 2
        zMin = gridRegion.xyzCentre[2] - gridRegion.xyzRange[2] / 2
        xMax = gridRegion.xyzCentre[0] + gridRegion.xyzRange[0] / 2
        yMax = gridRegion.xyzCentre[1] + gridRegion.xyzRange[1] / 2
        zMax = gridRegion.xyzCentre[2] + gridRegion.xyzRange[2] / 2
        
        if not gridRegion.is3dOr2dGrid:
            if gridRegion.twoDimGridPlaneIdx == 0:      # 0: XY
                nz = 1
                zMin = gridRegion.xyzCentre[2]
                zMax = zMin
            elif gridRegion.twoDimGridPlaneIdx == 1:    # 1: ZY
                nx = 1
                xMin = gridRegion.xyzCentre[0]
                xMax = xMin
            elif gridRegion.twoDimGridPlaneIdx == 2:    # 2: XZ
                ny = 1
                yMin = gridRegion.xyzCentre[1]
                yMax = yMin
            else:
                codeContractViolation()
                
        dxOrPlus1 = self._getStepOrPlus1(xMin, xMax, nx)
        dyOrPlus1 = self._getStepOrPlus1(yMin, yMax, ny)
        dzOrPlus1 = self._getStepOrPlus1(zMin, zMax, nz)
        
        xMin -= dxOrPlus1 / 2
        yMin -= dyOrPlus1 / 2
        zMin -= dzOrPlus1 / 2
        xMax += dxOrPlus1 / 2
        yMax += dyOrPlus1 / 2
        zMax += dzOrPlus1 / 2
        
        dw = (dxOrPlus1, dyOrPlus1, dzOrPlus1)
        
        return xMin, yMin, zMin, xMax, yMax, zMax, dw
        
    # !! very similar to hoc:GridOfSections.getStepOrMinus1
    #    but here we return "+1" because NEURON RxD seems to have a problem with negative steps
    def _getStepOrPlus1(self, uMin, uMax, nu):
        if nu != 1:
            return (uMax - uMin) / (nu - 1)
        else:
            return +1
            