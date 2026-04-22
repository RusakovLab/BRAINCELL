
# !! maybe this is just a temp implementation until we leverage "LFPykit" (however, it neither integrates with NEURON directly nor supports GPU);
#    as for "LFPy", it might be difficult to use it from BrainCell because Anaconda doesn't provide it for Windows in contrast to "LFPykit";
#    just an idea: BrainCell can generate a standalone Python script for "LFPy" like we generate "runner.hoc" in the export module

# !! Ideas:
#   * think about taking FFT and showing the PSD curves like we do in Arachne
#   * maybe show this "LFP sim" widget just as a panel at right-hand side of PointsToWatchWidget
#   * block user interaction with the Shape in PointsToWatchWidget during the run like we do for FRAP sims

# !! BUG: for astrocyte, the Graph-s show no line; UPD: this is NEURON's behaviour for const 0

from neuron import h

from SimABCs import *

from LFPCalculator import LFPCalculator

import GuiPrimitiveWrappers as bc
import MsgWarnHelperWrappers as mwhw

from XpuUtils import xpuUtils


class SimLocalFieldPotential(RequiresAltRunControl, UsesCustomProcAdvance, Simulation):
    
    _sigma = 0.3    # (S/m)
    
    _isSkipNanoSects = True
    _isGpuOrCpu = False     # !! assign "xpuUtils.isGpuOrCpuByDefault_cupy" here once we support massive grids of observation points in this sim
    
    # Data members added in the ctor:
    #   _calc, _ptsToWatchWidget
    
    # Data member added in "show":
    #   _mainBox
    
    # Data member added in "onDoneInPtsToWatchWidget":
    #   _listOfGraphs
    
    
    def __init__(self):
        
        self._calc = LFPCalculator()
        
        self._ptsToWatchWidget = h.PointsToWatchWidget('potential', 0, self)
        
    def preShowCheck(self):
        
        return False
        
    def show(self, isFirstShow):
        
        with bc.VBox('LFP sim', 810, 155, panel=True) as self._mainBox:
            # !! try xpvalue here
            # !! don't forget about the variable domain (we divide by sigma)
            h.xlabel('Extracellular conductivity:')
            h.xvalue('sigma (S/m)', (self, '_sigma'), 1)
            h.xlabel('')
            
            h.xbutton('Place electrodes', self._placeElectrodesButtonHandler)
            h.xlabel('')
            
            h.xcheckbox('Skip all nanogeom sections (faster)', (self, '_isSkipNanoSects'), self._isSkipNanoSectsCheckBoxHandler)
            h.xlabel('')
            
            h.xlabel('Device:')
            h.xradiobutton(f'Use CPU ({xpuUtils.numCpuCores} cores detected)', lambda: self._xpuRadioButtonHandler(False), not self._isGpuOrCpu)
            h.xradiobutton(f'Use GPU ({xpuUtils.numGpuCoresOrMinus1} cores detected)', lambda: self._xpuRadioButtonHandler(True), self._isGpuOrCpu)
            h.xlabel('')
            
            self._mainBox.dismiss_action(self._dismissHandler)
            
        self._placeElectrodesButtonHandler()
        
        # !! just to show the warning
        self._xpuRadioButtonHandler(self._isGpuOrCpu)
        
    # !! see also: InsideOutDiffManagerMainWidget.onDoneInPtsToWatchWidget, createGraphsForAllOPs
    def onDoneInPtsToWatchWidget(self, listOfPts, listOfGraphs):
        
        self._calc.setListOfPts(listOfPts)
        
        self._listOfGraphs = listOfGraphs
        
        yLabel = 'LFP (uV)'
        yMin = 0
        yMax = 1
        
        for pt in listOfPts:
            ref = pt._ref_theValue
            pt.createGraphAndAddToTwoLists(ref, yLabel, yMin, yMax, listOfGraphs)
            
    def preRun(self, isInitOnly):
        
        if not self._ptsToWatchWidget.isDoneClicked:
            self._ptsToWatchWidget.doneHandler()
            
        isCancel = self._calc.onPreRun(self._sigma, self._isSkipNanoSects, self._isGpuOrCpu)
        if isCancel:
            return True
            
        return self.preContinue()
        
    def preContinue(self):
        
        return False
        
    def advance(self):
        
        h.fadvance()
        
        self._calc.onAdvance()
        
        # !! maybe make a proc in PointsToWatchWidget and reuse for IOD ?
        #    (and get rid of "_listOfGraphs" in this class)
        for graph in self._listOfGraphs:
            graph.exec_menu('View = plot')
            
    def postRun(self):
        
        pass
        
    def simDismissHandler(self):
        
        self._ptsToWatchWidget.dismissHandler(1)
        
        self._dismissHandler()
        
        self._calc.cleanup(True)
        
    # All next staff is private
    
    
    def _placeElectrodesButtonHandler(self):
        
        self._ptsToWatchWidget.dismissHandler(1)
        self._ptsToWatchWidget.isDoneClicked = 0    # !! ideally, do this only on changes in PointsToWatchWidget
        self._ptsToWatchWidget.show()
        
        self._cleanup(True)
        
    def _xpuRadioButtonHandler(self, isGpuOrCpu):
        
        with mwhw.MsgWarnInterceptor():
            if isGpuOrCpu:
                isCancel = xpuUtils.checkGpuPrereqs(False)
                if isCancel:
                    isGpuOrCpu = False
                else:
                    h.mwh.showWarningBox("The GPU mode is made for the future when we'll support massive grids of observation points.", "Currently it's not efficient because you specify just a few OPs.", 'Use CPU instead.')
                    
        self._isGpuOrCpu = isGpuOrCpu
        
        self._cleanup(False)
        
    def _isSkipNanoSectsCheckBoxHandler(self):
        
        self._cleanup(False)
        
    def _cleanup(self, isDestroyListOfPtsInCalc):
        
        self._calc.cleanup(isDestroyListOfPtsInCalc)
        h.altRunControlWidget.isInited = 0
        
    def _dismissHandler(self):
        
        h.unmapIfNotNil(self._mainBox)
        