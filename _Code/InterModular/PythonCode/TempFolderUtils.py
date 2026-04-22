
import os, shutil

from OtherInterModularUtils import codeContractViolation


class TempFolderUtils:
    
    tempFolderName = 'temp_folder'
    
    @classmethod
    def createOrCleanUpTempFolder(cls, tempFolderPath):
        if os.path.exists(tempFolderPath):
            for entryName in os.listdir(tempFolderPath):
                entryPath = os.path.join(tempFolderPath, entryName)
                if os.path.isfile(entryPath):
                    os.remove(entryPath)
                elif os.path.isdir(entryPath):
                    cls.deleteTempFolder(entryPath)
                else:
                    codeContractViolation()
        else:
            os.mkdir(tempFolderPath)
            
    def deleteTempFolder(tempFolderPath):
        shutil.rmtree(tempFolderPath)
        