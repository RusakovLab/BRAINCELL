
# !! test the case "Dt < dt"

# !! maybe kill zombie subproc from the ctor

# !! when isShowPyplotFigsInSubProcess = True, can we make direct calls of Python methods in the subprocess (passing the args) rather than use the pickle files?
#    some ideas: stdin=subprocess.PIPE, multiprocessing.Queue, multiprocessing.Event, multiprocessing.managers.BaseManager

import sys
import math
import numpy as np

from neuron import h
from neuron.units import mM

from Helpers.BasicEnums import EnumMyelSheath
import MsgWarnHelperWrappers as mwhw
from OtherInterModularUtils import isShowPyplotFigsInSubProcess, codeContractViolation


if isShowPyplotFigsInSubProcess:
    from Helpers.PyplotHelpers.PyplotSubProcHelper import PyplotSubProcHelper
else:
    from Helpers.PyplotHelpers.PyplotAndSaveHelper_Separated import PyplotAndSaveHelper
    
    
class AnimSavePrintHelper:
    
    _isSmthRecorded = False
    
    # Data members added in the ctor:
    #   _presParams, _bac, _pyplotSubProcHelper
    
    # Data member added in "setModifAxonSecContainer":
    #   _mac
    
    # Data member added in "saveTxtFileCheckBoxHandler":
    #   _txtFilePathName
    
    # Data members added in "onPreRun":
    #   _Dt
    #   _radius_axon, _radius_outer, _numShells
    #   _enumMyelSheath, _isUseRealBiophysOrTestSines
    #   _isDeployMyelSheath
    #   _prevFrameIdx
    
    # Data members added in "onPreContinue":
    #   _graphs
    #   _shells, _k
    
    # Data member added in "onAdvance":
    #   _pyplotAndSaveHelper
    
    def __init__(self, presParams, baseAxonSecContainer):
        
        self._presParams = presParams
        self._bac = baseAxonSecContainer
        
        if isShowPyplotFigsInSubProcess:
            self._pyplotSubProcHelper = PyplotSubProcHelper()
            
    def setModifAxonSecContainer(self, modifAxonSecContainer):
        self._mac = modifAxonSecContainer
        
    def saveTxtFileCheckBoxHandler(self):
        
        if not self._presParams.isSave:
            return
            
        txtFilePathNameRef = h.ref('')
        isCancel = h.fbh.showSaveFileDialog(h.pyEnumOutFileTypes.textResultsTxtSMA, txtFilePathNameRef)
        
        if isCancel:
            self._presParams.isSave = False
            return
            
        self._txtFilePathName = txtFilePathNameRef[0]
        
        if not self._presParams.isAnim[1]:
            # !! maybe warn user that we are checking this checkbox because it's required for TXT files saving
            #    (in the future, me may eliminate this inconvenience)
            self._presParams.isAnim[1] = True
            
            # Cannot "Init & Run" without recording, then "Continue" with recording
            h.altRunControlWidget.isInited = 0
            
        if not self._isSmthRecorded:
            h.showWillBeSavedLaterMsg()
            return
            
        self._saveTxtFile()
        self.showTxtFileSavedMsg()
        
    def showTxtFileSavedMsg(self):
        h.showResultsWereSavedToMsg(self._txtFilePathName)
        
    def onPreRun(self, Dt, radius_axon, radius_outer, numShells, enumMyelSheath, isUseRealBiophysOrTestSines):
        
        self._Dt                          = Dt
        self._radius_axon                 = radius_axon
        self._radius_outer                = radius_outer
        self._numShells                   = numShells
        self._enumMyelSheath              = enumMyelSheath
        self._isUseRealBiophysOrTestSines = isUseRealBiophysOrTestSines
        
        self._isDeployMyelSheath = enumMyelSheath == EnumMyelSheath.deploy
        
        if isShowPyplotFigsInSubProcess:
            self._pyplotSubProcHelper.onPreRun(radius_axon, radius_outer, self._isDeployMyelSheath)
            
        self._prevFrameIdx = -1
        self._isSmthRecorded = False
        
    # !! would it make sense to leverage h.FInitializeHandler with type=2 to get rid of 2 explicit calls of this method?
    def makeSureZeroTimeFrameConsumed(self):
        if self._prevFrameIdx == -1:
            self.onAdvance()
            
    def onPreContinue(self, graphs, shells, k):
        
        self._graphs = graphs
        self._shells = shells
        self._k      = k
        
        if isShowPyplotFigsInSubProcess:
            self._pyplotSubProcHelper.onPreContinue()
            
    def onAdvance(self):
        
        if self._prevFrameIdx == -1:
            frameIdx = 0
        else:
            frameIdx = h.t / self._Dt
            if frameIdx < self._prevFrameIdx + 1 - math.sqrt(sys.float_info.epsilon):
                return
                
            frameIdx = int(round(frameIdx))
            
        if self._presParams.isPrint:
            
            print('t: %g (ms)' % h.t)
            
            if self._enumMyelSheath in [EnumMyelSheath.deploy, EnumMyelSheath.scalp]:
                if self._mac.axonBeforeFirstSchwannSecOrNone:
                    print(    '    axonBeforeFirstSchwann.ik(0.5): %8.4g (mA/cm2)   axonBeforeFirstSchwann.ko(0.5): %8.4g (mM)' % (self._mac.axonBeforeFirstSchwannSecOrNone(0.5).ik, self._mac.axonBeforeFirstSchwannSecOrNone(0.5).ko))
                    
                for secIdx, (sec1, sec2) in enumerate(zip(self._mac.axonUnderSchwannSecsList, self._mac.axonNodeOfRanvierSecsList)):
                    print(    '    axonUnderSchwann[%i].ik(0.5):   %8.4g (mA/cm2)   axonUnderSchwann[%i].ko(0.5):   %8.4g (mM)' % (secIdx, sec1(0.5).ik, secIdx, sec1(0.5).ko))
                    print(    '    axonNodeOfRanvier[%i].ik(0.5):  %8.4g (mA/cm2)   axonNodeOfRanvier[%i].ko(0.5):  %8.4g (mM)' % (secIdx, sec2(0.5).ik, secIdx, sec2(0.5).ko))
                    
                # The last Schwann cell
                # secIdx += 1   # !! error: not defined if the cycle above had no iterations
                secIdx = len(self._mac.axonUnderSchwannSecsList) - 1
                sec1 = self._mac.axonUnderSchwannSecsList[-1]
                print(        '    axonUnderSchwann[%i].ik(0.5):   %8.4g (mA/cm2)   axonUnderSchwann[%i].ko(0.5):   %8.4g (mM)' % (secIdx, sec1(0.5).ik, secIdx, sec1(0.5).ko))
                
                if self._mac.axonAfterLastSchwannSecOrNone:
                    print(    '    axonAfterLastSchwann.ik(0.5):   %8.4g (mA/cm2)   axonAfterLastSchwann.ko(0.5):   %8.4g (mM)' % (self._mac.axonAfterLastSchwannSecOrNone(0.5).ik, self._mac.axonAfterLastSchwannSecOrNone(0.5).ko))
                    
                if self._isDeployMyelSheath:
                    for secIdx, sec in enumerate(self._mac.schwannSecsList):
                        print('    schwann[%i].ik(0.5):            %8.4g (mA/cm2)   schwann[%i].ko(0.5):            %8.4g (mM)' % (secIdx, sec(0.5).ik, secIdx, sec(0.5).ko))
            elif self._enumMyelSheath == EnumMyelSheath.remove:
                print('    axon.ik(0.5): %8.4g (mA/cm2)   axon.ko(0.5): %8.4g (mM)' % (self._bac.axon(0.5).ik, self._bac.axon(0.5).ko))
            else:
                codeContractViolation()
                
        isAnim0 = self._presParams.isAnim[0]
        if isAnim0:
            subMats = [self._prepareOneConcMatrix(sec) for sec in self._mac.axonTrunkSecsExceptTerms]
            colourMapDataMatrixOrNone = np.concatenate(subMats, axis=1)
        else:
            colourMapDataMatrixOrNone = None
            
        isAnim1 = self._presParams.isAnim[1]
        if isAnim1:
            perShellCurvesXYTuplesOrNone = [None] * self._numShells
            for shellIdx, shell in enumerate(self._shells):
                nodes = self._k.nodes(shell)
                x = np.array([h.distance(nd) for nd in nodes])
                y = np.array([nd.concentration / mM for nd in nodes])
                perShellCurvesXYTuplesOrNone[shellIdx] = (x, y)
        else:
            perShellCurvesXYTuplesOrNone = None
            
        if isAnim0 or isAnim1:
            isFirstAnimFrame = self._prevFrameIdx == -1
            if isShowPyplotFigsInSubProcess:
                self._pyplotSubProcHelper.savePickleFile(frameIdx, h.t, colourMapDataMatrixOrNone, perShellCurvesXYTuplesOrNone)
                if isFirstAnimFrame:
                    self._pyplotSubProcHelper.launchSubProcess()
            else:
                if isFirstAnimFrame:
                    self._pyplotAndSaveHelper = PyplotAndSaveHelper(False)
                self._pyplotAndSaveHelper.addNewFrame(h.t, self._radius_axon, self._radius_outer, self._isDeployMyelSheath, colourMapDataMatrixOrNone, perShellCurvesXYTuplesOrNone)
                if isFirstAnimFrame:
                    self._pyplotAndSaveHelper.showFigure()
                    
        self._isSmthRecorded = isAnim1
        
        if self._isUseRealBiophysOrTestSines:
            for graph in self._graphs[:-1]:
                if graph:
                    graph.exec_menu('View = plot')
                    
        self._prevFrameIdx = frameIdx
        
    def onPostRun(self):
        
        if isShowPyplotFigsInSubProcess:
            self._pyplotSubProcHelper.onPostRun()
            
        if self._presParams.isSave:
            self._saveTxtFile()
            
    def cleanup(self, isCleanUpRxd):
        
        if isShowPyplotFigsInSubProcess:
            self._pyplotSubProcHelper.onCleanup()
        elif hasattr(self, '_pyplotAndSaveHelper'):
            self._pyplotAndSaveHelper.closeFigure()
            
        self._isSmthRecorded = False
        
        if isCleanUpRxd:
            self._k = None
            
            
    def _prepareOneConcMatrix(self, sec):
        return np.array(self._k.nodes(sec).concentration).reshape(self._numShells, sec.nseg) / mM
        
    def _saveTxtFile(self):
        
        with mwhw.PleaseWaitBox('Saving TXT file.'):
            if isShowPyplotFigsInSubProcess:
                self._pyplotSubProcHelper.requestTxtFileSavingThenWait(self._txtFilePathName)
            else:
                self._pyplotAndSaveHelper.saveToTxtFile(self._txtFilePathName)
                