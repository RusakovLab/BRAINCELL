
from OtherInterModularUtils import isShowPyplotFigsInSubProcess

if not isShowPyplotFigsInSubProcess:
    codeContractViolation()
    
import os
import pickle
import sys
import subprocess
import time

from Helpers.PyplotHelpers.PyplotAndSaveHelper_Separated import PyplotAndSaveHelper
from TempFolderUtils import TempFolderUtils


class PyplotSubProcHelper:
    
    _subProcScriptFileName = 'PyplotAndSaveHelper_Separated.py'
    
    # How often to look for the marker file
    # !! see also: PyplotAndSaveHelper._inputFilesCheckTimerInterval
    _alreadySavedMarkerFileCheckTimerInterval = 1   # s (real world time)
    
    # Data members added in the ctor:
    #   _thisFileDirPath, _tempFolderAbsPathName, _runningMarkerFileAbsPathName, _saveToMarkerFileAbsPathName, _alreadySavedMarkerFileAbsPathName, _subProcOrNone
    
    # Data members added in "onPreRun":
    #   _radius_axon, _radius_outer, _isDeployMyelSheath
    
    
    def __init__(self):
        self._thisFileDirPath = os.path.dirname(os.path.abspath(__file__))
        self._tempFolderAbsPathName = os.path.join(self._thisFileDirPath, TempFolderUtils.tempFolderName)
        self._runningMarkerFileAbsPathName = os.path.join(self._tempFolderAbsPathName, PyplotAndSaveHelper.runningMarkerFileName)
        self._saveToMarkerFileAbsPathName = os.path.join(self._tempFolderAbsPathName, PyplotAndSaveHelper.saveToMarkerFileName)
        self._alreadySavedMarkerFileAbsPathName = os.path.join(self._tempFolderAbsPathName, PyplotAndSaveHelper.alreadySavedMarkerFileName)
        self._subProcOrNone = None
        
    def onPreRun(self, radius_axon, radius_outer, isDeployMyelSheath):
        
        TempFolderUtils.createOrCleanUpTempFolder(self._tempFolderAbsPathName)
        
        self._radius_axon        = radius_axon
        self._radius_outer       = radius_outer
        self._isDeployMyelSheath = isDeployMyelSheath
        
    def onPreContinue(self):
        
        PyplotAndSaveHelper.createEmptyMarkerFile(self._runningMarkerFileAbsPathName)
        
    # !! PyplotAndSaveHelper caches the data, so no need to pass everything on each frame
    def savePickleFile(self, frameIdx, _time, colourMapDataMatrixOrNone, perShellCurvesXYTuplesOrNone):
        
        data = {
            'time'                        : _time,
            'radius_axon'                 : self._radius_axon,
            'radius_outer'                : self._radius_outer,
            'isDeployMyelSheath'          : self._isDeployMyelSheath,
            'colourMapDataMatrixOrNone'   : colourMapDataMatrixOrNone,
            'perShellCurvesXYTuplesOrNone': perShellCurvesXYTuplesOrNone}
        
        pickleFileName = PyplotAndSaveHelper.getPickleFileName(frameIdx)
        
        pickleFileAbsPathName = os.path.join(self._tempFolderAbsPathName, pickleFileName)
        
        with open(pickleFileAbsPathName, 'wb') as f:
            pickle.dump(data, f)
            
    def launchSubProcess(self):
        
        self._subProcOrNone = subprocess.Popen([sys.exec_prefix + '/python.exe', self._subProcScriptFileName, TempFolderUtils.tempFolderName], cwd=self._thisFileDirPath)
        
    def onPostRun(self):
        # No error if the marker file doesn't exist
        try:
            os.remove(self._runningMarkerFileAbsPathName)
        except FileNotFoundError:
            pass
            
    def requestTxtFileSavingThenWait(self, outTxtFilePathName):
        
        # !! do we need this?
        #    if we do, then move to a method and reuse in "onPostRun"
        try:
            os.remove(self._alreadySavedMarkerFileAbsPathName)
        except FileNotFoundError:
            pass
            
        with open(self._saveToMarkerFileAbsPathName, 'w') as outMarkerFile:
            outMarkerFile.write(outTxtFilePathName)
            
        while not os.path.exists(self._alreadySavedMarkerFileAbsPathName):
            time.sleep(self._alreadySavedMarkerFileCheckTimerInterval)
            
        os.remove(self._alreadySavedMarkerFileAbsPathName)
        
    def onCleanup(self):
        if self._subProcOrNone:
            self._subProcOrNone.kill()
            self._subProcOrNone = None
            # !! the temp folder is cleaned up in "onPreRun"
            