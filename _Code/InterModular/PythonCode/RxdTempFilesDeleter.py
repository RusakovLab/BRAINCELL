
# NEURON creates the temp files in the root folder for SimCore (each time) and RxdBackend (only when isEnableUptake = True)

# !! idea: maybe we can prevent saving the files in the root by switching the current working directory for a moment to some "temp_folder"

import os
import glob


class RxdTempFilesDeleter:
    
    # Data member added in the ctor:
    #   _rootDirPath
    
    def __init__(self):
        thisFileDirPath = os.path.dirname(os.path.abspath(__file__))
        self._rootDirPath = os.path.normpath(os.path.join(thisFileDirPath, '..', '..', '..'))
        
    def deleteNeuronTempFilesFromBrainCellRootFolder(self):
        self._deleteFilesByFilter('rxddll*.so')     # NEURON never deletes them
        self._deleteFilesByFilter('rxddll*.c')      # NEURON usually deletes them, but may leave in case of internal errors
        
        
    def _deleteFilesByFilter(self, fileNameFilter):
        filePathNameFilter = os.path.join(self._rootDirPath, fileNameFilter)
        for filePathName in glob.iglob(filePathNameFilter):
            try:
                os.remove(filePathName)
            except PermissionError:
                pass
                
tfd = RxdTempFilesDeleter()

tfd.deleteNeuronTempFilesFromBrainCellRootFolder()

del tfd
