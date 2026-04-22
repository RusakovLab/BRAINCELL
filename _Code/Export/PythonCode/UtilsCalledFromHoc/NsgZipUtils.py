
import os
import zipfile

from neuron import h


class NsgZipUtils:
    
    _inMechsDirName = 'Mechanisms'
    _inMechsCommonSubDirName = 'Common'
    _inMechsSubSubDirName = 'MOD_files'
    
    _outZippedDirName = 'BrainCell_export'
    _outZippedSubDirName = 'mod_nsgportal'
    
    
    @classmethod
    def createNsgDataZipFile(cls, inTempExportDirRelPath, outZipFilePathName):
        
        inMechsCommonDirPath = os.path.join(cls._inMechsDirName, cls._inMechsCommonSubDirName, cls._inMechsSubSubDirName)
        
        cellTypeName = h.ref('')
        h.getCellTypeName(cellTypeName)
        inMechsCellTypeDirPath = os.path.join(cls._inMechsDirName, cellTypeName[0], cls._inMechsSubSubDirName)
        
        with zipfile.ZipFile(outZipFilePathName, 'w') as outZipFile:
            cls._zipAllFilesFromThisDir(outZipFile, inTempExportDirRelPath)
            cls._zipAllFilesFromThisDir(outZipFile, inMechsCommonDirPath, cls._outZippedSubDirName)
            cls._zipAllFilesFromThisDir(outZipFile, inMechsCellTypeDirPath, cls._outZippedSubDirName)
            
            
    @classmethod
    def _zipAllFilesFromThisDir(cls, outZipFile, inDirPath, outZippedSubDirNameOrEmpty=''):
        for inEntry in os.scandir(inDirPath):
            if not inEntry.is_file():
                continue
            outZippedFilePathName = os.path.join(cls._outZippedDirName, outZippedSubDirNameOrEmpty, inEntry.name)
            outZipFile.write(inEntry, outZippedFilePathName)
            