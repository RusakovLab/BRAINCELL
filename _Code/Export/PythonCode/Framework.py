
import os, shutil
from tkinter.messagebox import askyesno

from neuron import h

from GeneratorsForMainHocFile.MetaGensForTaps import MetaGensForTaps
from GeneratorsForMainHocFile.GeneratorsForMainHocFile import GeneratorsForMainHocFile
from GeneratorsForAuxHocFiles.GenForParamsHoc import GenForParamsHoc
from GeneratorsForAuxHocFiles.GensForRunnerHoc import GensForRunnerHoc
from Utils.OtherUtils import *


_genStartMarker = 'py:'
_metaGenMarker = '@'
_genEndMarker = ')'
_parStartMarker = parHdrStart + ' Start of '
_parEndMarker = parHdrStart + ' End of '
_emptyParMarker = emptyParagraphHint()


class _GenInfo:
    
    def __init__(self, startIdx, endIdx, pyCall):
        self.startIdx = startIdx
        self.endIdx = endIdx
        self.pyCall = pyCall
        
        
def exportCore(outMainHocFilePathName):
    
    isAstrocyteOrNeuron = h.isAstrocyteOrNeuron
    if isAstrocyteOrNeuron:
        inSkeletonFileName = 'MainHocFileSkeletonForAstrocyte.txt'
    else:
        inSkeletonFileName = 'MainHocFileSkeletonForNeuron.txt'
    gens = GeneratorsForMainHocFile(outMainHocFilePathName)
    _exportSkeletonBasedHocFile(inSkeletonFileName, gens, outMainHocFilePathName)
    
    outDirPath = os.path.dirname(outMainHocFilePathName)
    
    if h.exportOptions.isCreateParamsHoc:
        gen = GenForParamsHoc()
        lines = gen.getParamsCode()
        lines = _addNewLineChars(lines)
        outHocFilePathName = outDirPath + '\\params.hoc'
        with open(outHocFilePathName, 'w') as outFile:
            outFile.writelines(lines)
            
    if h.exportOptions.isCreateRunnerHoc:
        inSkeletonFileName = 'RunnerHocFileSkeleton.txt'
        outMainHocFileName = os.path.basename(outMainHocFilePathName)
        gens = GensForRunnerHoc(outMainHocFileName)
        outHocFilePathName = outDirPath + '\\runner.hoc'
        _exportSkeletonBasedHocFile(inSkeletonFileName, gens, outHocFilePathName)
        
    if h.exportOptions.isCopyDll:
        _copyMechsDllFile(outDirPath, h.mechsDllUtils.loadedDllDirPath)
        
        
def _exportSkeletonBasedHocFile(inSkeletonFileName, gens, outHocFilePathName):
    
    inSkeletonFileRelPathName = '_Code\\Export\\OutHocFileStructures\\Skeletons\\' + inSkeletonFileName
    
    with open(inSkeletonFileRelPathName, 'r') as inFile:
        lines = inFile.readlines()      # Preserving all newline characters here
        
    lines, lineIdxToGenInfoDict = _unwrapTapSetsAndFindGenerators(lines)
    
    # Iterating in reverse order would simplify the loop below making trgLineIdx equal to srcLineIdx,
    # but CleanupHelper requires the direct order
    delta = 0
    for srcLineIdx in lineIdxToGenInfoDict.keys():
        genInfo = lineIdxToGenInfoDict[srcLineIdx]
        genRes = eval('gens.' + genInfo.pyCall)
        trgLineIdx = srcLineIdx + delta
        tp = type(genRes)
        if tp == str:
            _insertSubstring(lines, trgLineIdx, genInfo.startIdx, genInfo.endIdx, genRes)
        elif tp == list:
            _insertLines(lines, trgLineIdx, genRes)
            delta += len(genRes) - 1
        else:
            codeContractViolation()
            
    _removeEmptyParagraphs(lines)
    
    _prependTableOfContents(lines)
    
    with open(outHocFilePathName, 'w') as outFile:
        outFile.writelines(lines)
        
def _copyMechsDllFile(outDirPath, loadedDllDirPath):
    
    dllFileName = 'nrnmech.dll'
    
    srcDllFilePath = loadedDllDirPath + '\\' + dllFileName
    dstDllFilePath = outDirPath + '/' + dllFileName     # Will be printed in case of uncaught PermissionError
    
    try:
        shutil.copyfile(srcDllFilePath, dstDllFilePath)
    except shutil.SameFileError:
        # Maybe user loaded a nano HOC file exported earlier and now just exports it again
        pass
    except PermissionError:
        isTryAgain = askyesno(
            title='Permission Error',
            message=f'Cannot replace "{dllFileName}" in the target folder.\nPerhaps it\'s in use by another instance of NEURON.\n\nTry again?')
        if isTryAgain:
            _copyMechsDllFile(outDirPath, loadedDllDirPath)
            
def _unwrapTapSetsAndFindGenerators(lines):
    lineIdxToGenInfoDict = {}
    lineIdx = 0
    while (lineIdx != len(lines)):
        line = lines[lineIdx]
        startIdx = line.find(_genStartMarker)
        if startIdx == -1:
            lineIdx += 1
            continue
        pyCallIdx = startIdx + len(_genStartMarker)
        endIdx = line.find(_genEndMarker, pyCallIdx)
        if endIdx == -1:
            codeContractViolation()
        endIdx += 1
        testIdx = line.find(_genStartMarker, endIdx)
        if testIdx != -1:
            # More than 1 generator in the same line: Not implemented
            codeContractViolation()
        pyCall = line[pyCallIdx : endIdx]
        if pyCall.startswith(_metaGenMarker):
            metaPyCall = pyCall[len(_metaGenMarker) :]
            newLines = eval('MetaGensForTaps.' + metaPyCall)
            if len(newLines) != 0:
                if newLines[0] != '\n':
                    codeContractViolation()
                lines[lineIdx : lineIdx + 1] = newLines[1 :]
            else:
                if lines[lineIdx + 1] != '\n':
                    codeContractViolation()
                lines[lineIdx : lineIdx + 2] = []
        else:
            lineIdxToGenInfoDict[lineIdx] = _GenInfo(startIdx, endIdx, pyCall)
            lineIdx += 1
            
    return lines, lineIdxToGenInfoDict
    
def _removeEmptyParagraphs(lines):
    lineIdx = len(lines) - 1
    while lineIdx > 0:
        line = lines[lineIdx]
        if line.startswith(_emptyParMarker):
            if lines[lineIdx - 3] != '\n' or not lines[lineIdx - 2].startswith(_parStartMarker) or not lines[lineIdx + 2].startswith(_parEndMarker):
                codeContractViolation()
            lines[lineIdx - 3 : lineIdx + 3] = []
            lineIdx -= 4
        else:
            lineIdx -= 1
            
def _prependTableOfContents(lines):
    hdrStartIdx = len(_parStartMarker)
    lineIdxToHeaderDict = {}
    for lineIdx in range(len(lines)):
        line = lines[lineIdx]
        if not line.startswith(_parStartMarker):
            continue
        hdrEndIdx = line.find(' /', hdrStartIdx)
        if hdrEndIdx == -1:
            codeContractViolation()
        header = line[hdrStartIdx : hdrEndIdx]
        header = header[0].upper() + header[1 :]
        lineIdxToHeaderDict[lineIdx] = header
    numHeaders = len(lineIdxToHeaderDict)
    if numHeaders == 0:
        codeContractViolation()
    elif numHeaders == 1:
        return
    numToCLines = numHeaders + 5
    genLines = []
    line = parHdrStart + ' Table of contents '
    line = line + '/' * (parHdrTotalLen - len(line))
    genLines.append(line)
    genLines.append('/*')
    for lineIdx, header in lineIdxToHeaderDict.items():
        linePtr = '    Line {}: '.format(lineIdx + numToCLines)
        spacer = ' ' * (24 - len(linePtr))
        genLines.append('{}{}{}'.format(linePtr, spacer, header))
    genLines.append('*/')
    genLines.append('/' * parHdrTotalLen)
    lines[: 0] = _addNewLineChars(genLines)
    
def _insertSubstring(lines, lineIdx, startIdx, endIdx, genSubstring):
    line = lines[lineIdx]
    line = line[: startIdx] + genSubstring + line[endIdx :]
    lines[lineIdx] = line
    
def _insertLines(lines, lineIdx, genLines):
    lines[lineIdx : lineIdx + 1] = _addNewLineChars(genLines)
    
def _addNewLineChars(genLines):
    return [genLine + '\n' for genLine in genLines]
    