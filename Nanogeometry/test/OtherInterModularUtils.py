
import os
import numpy as np

from neuron import h, hoc


# We call Pyplot scripts in a subprocess as a workaround for the next problem:
#   when the first Pyplot figure is created, all NEURON widgets become smaller;
#   this happens only when "Size of text, apps, and other items" parameter in Display settings of Windows OS is greater than 100%;
#   the root cause is that the command "plt.figure()" changes the DPI awareness of the process from False to True and increases its DPI from 96 to a higher value
# !! BUG: the subprocess is not destroyed when the parent process is killed (but no problem for normal exit)
isShowPyplotFigsInSubProcess = True


def codeContractViolation():
    # !! we don't pass the message to Exception ctor just because in this case the shown call stack will be split into two parts:
    #    the Python call stack (printed above our text) and the HOC call stack (printed below our text)
    print('\n    Bug in BrainCell program: Code contract violation\n    Please report this problem to the developer along with the call stack shown below\n')
    raise Exception
    
def getTemplOrClassName(hocOrPyObjInst):
    if type(hocOrPyObjInst) == hoc.HocObject:
        fullName = str(hocOrPyObjInst)
        idx = fullName.index('[')
        return fullName[: idx]
    else:
        return hocOrPyObjInst.__class__.__name__
        
def convertPyIterableOfStrsToHocListOfStrObjs(pyIter):
    hocList = h.List()
    for item in pyIter:
        hocList.append(h.String(item))
    return hocList
    
def convertPyIterableOfSecsToHocListOfSecRefs(pyIter):
    list_ref = h.List()
    for sec in pyIter:
        list_ref.append(h.SectionRef(sec))
    return list_ref
    
def isNanoGeometrySection(secName):
    return secName.startswith('AstrocyteNanoBranch[') or secName.startswith('NeuronNanoBranch[')    # !! hardcode
    
# Called from both Python and HOC
# !! fragile logic in the callers of this method:
#    there is no guarantee that user didn't apply, say, liner function to g_pas in LargeGlia and then clicked "Deep rescan" making it verbatim
def isAstrocyteSpecificInhomVar(compIdx, mechIdx, varType, varIdx, arrayIndex):
    
    mth = h.mth
    
    tp = type(compIdx)
    if tp == int or tp == float:
        compName = h.mmAllComps[int(compIdx)].name
    else:
        codeContractViolation()
        
    mechName = h.ref('')
    varName = h.ref('')
    mth.getMechName(0, mechIdx, mechName)
    mth.getVarNameAndArraySize(0, mechIdx, varType, varIdx, varName)
    
    # !! checking the comp name below is a fragile solution because user could rename the comp;
    #    a better approach would be to have a Boolean flag in each comp (but what to do with it on comp split and merge ops?)
    cond = (h.isAstrocyteOrNeuron and
        compName == 'Large Glia' and
        mechName[0] == 'pas' and
        varType == 1 and    # 1: PARAMETER
        varName[0] == 'g_pas' and
        arrayIndex == 0)
        
    return cond
    
# !! find a better place for this
def isInPySet(theSet, theItem):
    return theItem in theSet
    
# !! not intermodular
# !! rename to get1dArrayElem ?
def getArrayElem(theArray, idx):
    return theArray[int(idx)]   # !! called often and converted each time
    
# !! not intermodular
# !! test this
def getIdxInSortedArray(sortedArray, value):
    return np.searchsorted(sortedArray, value)
    
def getDirPath(anyFilePathName):
    return os.path.dirname(anyFilePathName)
    
# !! not intermodular actually
def getDllFilePathName(anyFilePathName):
    dirPath = getDirPath(anyFilePathName)
    sepChar = anyFilePathName[len(dirPath)]
    return dirPath + sepChar + 'nrnmech.dll'
    
def getAllBiophysMechNamesSet():
    mechNames = set()
    mechName = h.ref('')
    for mechIdx in range(int(h.mth.getNumMechs(0))):
        h.mth.getMechName(0, mechIdx, mechName)
        mechNames.add(mechName[0])
    return mechNames
    
def getAllUninsertableBiophysMechNamesList():
    mechNames = []
    mechIdxs = range(int(h.mth.getNumMechs(0)))
    keepIfPred = lambda mechIdx: not (mechIdx == h.mth.morphologyMechIdx or h.mth.isDistMechSticky(mechIdx))
    mechName = h.ref('')
    for mechIdx in filter(keepIfPred, mechIdxs):
        h.mth.getMechName(0, mechIdx, mechName)
        mechNames.append(mechName[0])
    return mechNames
    