
import os
import re

from neuron import h

from OtherInterModularUtils import *


# Keep in sync with the skeleton TXT files
parHdrStart = '/' * 20
parHdrTotalLen = 74

indentSize = 4
stdIndent = ' ' * indentSize


def getAllSectionNamesExceptNanogeometry():
    # Get all names (base geometry, nanogeometry, etc.)
    # !! it's not optimal because:
    # (1) there is a lot of nanogeometry sections with known names (no need to use slow "forall")
    # (2) we already had all base geometry names at some point before (in Import module)
    allSecNames = h.getAllSectionNames()
    
    if len(allSecNames) == 0:
        codeContractViolation()
        
    for secName in allSecNames:
        if isNanoGeometrySection(secName.s):
            continue
        yield secName
        
def getAllLinesFromFile(relFilePathName):
    absFilePathName = os.getcwd() + '\\' + relFilePathName
    with open(absFilePathName, 'r') as inFile:
        inText = inFile.read()
    return inText.strip().splitlines()  # All newline characters are removed here
    
def getAllLinesFromReducedVersionFile(redVerRelFilePathName):
    relFilePathName = '_Code\\Export\\OutHocFileStructures\\MainHocUtils\\ReducedVersions\\' + redVerRelFilePathName
    return getAllLinesFromFile(relFilePathName)
    
def exportTheseTemplatesFromThisDir(lines, relDirPath, templNames):
    isFirstTemplate = True
    for templName in templNames:
        if not isFirstTemplate:
            lines.append('')
        relFilePathName = relDirPath + '\\' + templName + '.hoc'
        newLines = getAllLinesFromFile(relFilePathName)
        lines.extend(newLines)
        lines.append('')
        isFirstTemplate = False
        
def getExposedVarName(exposedVarIdx):
    return f'EXPOSED_VAR_{exposedVarIdx + 1}'
    
def getSweptVarName(sweptVarIdx):
    return f'SWEPT_VAR_{sweptVarIdx + 1}'
    
def emptyParagraphHint():
    return '// (Empty paragraph)'
    
def getIndent(line):
    for idx, char in enumerate(line):
        if not char.isspace():
            return ' ' * idx
    codeContractViolation()


EXTRA_CELL_PREFIX_RE = re.compile(r'^_pysec\.(EXTRA_CELL_\d+)\.')


def getExtraCellPrefixes():
    """Return sorted list of distinct EXTRA_CELL_N prefix strings
    found among all non-nanogeometry section names.
    E.g. ['EXTRA_CELL_1', 'EXTRA_CELL_2']
    """
    prefixes = set()
    for secName in getAllSectionNamesExceptNanogeometry():
        m = EXTRA_CELL_PREFIX_RE.match(secName.s)
        if m:
            prefixes.add(m.group(1))
    return sorted(prefixes)