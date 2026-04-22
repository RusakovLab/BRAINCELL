
# !!
# * don't forget to get rid of the old gens/utils for syns (see the old skeleton)
# * make sure we export each "Reduced*" template somewhere
# * maybe replace everywhere:
#   * exportOptions.isExportGapJuncs -> exportOptions.isExportAnyGapJuncSets()
#   * exportOptions.isExportSyns -> exportOptions.isExportAnySynSets()

import glob
import os
import platform
import re
import shutil
import re as _re

from neuron import h, nrn

from Utils.CleanupHelper import CleanupHelper
from GeneratorsForMainHocFile.GensForHomogenVars import GensForHomogenVars
from GeneratorsForMainHocFile.GensForInhomAndStochModels import GensForInhomAndStochModels
from GeneratorsForMainHocFile.GensForTaps import GensForTaps
from GeneratorsForMainHocFile.GensForExtracellularDiffusion import GensForExtracellularDiffusion
from Utils.LoopUtils import LoopUtils
from Utils.UnitsUtils import UnitsUtils
from Utils.OtherUtils import *


class GeneratorsForMainHocFile:
    
    _defaultNseg = 1
    _defaultRa = 35.4
    
    # _cleanupHelper
    
    _gensForHomogenVars = GensForHomogenVars()
    _gensForInhomAndStochModels = GensForInhomAndStochModels()
    # _gensForTaps
    _gensForExtracellularDiffusion = GensForExtracellularDiffusion()
    
    def __init__(self, outMainHocFilePathName=None):
        self._outMainHocFilePathName = outMainHocFilePathName
        self._cleanupHelper = CleanupHelper()
        self._gensForTaps = GensForTaps(self._cleanupHelper, self._gensForHomogenVars, self._gensForInhomAndStochModels)
        
    def getVersionInfo(self):
        lines = []
        
        bcv = h.ref('')
        h.getBrainCellVersionStr(bcv)
        
        lines.append('/*')
        lines.append('    This HOC file was generated using:')
        lines.append('      * BrainCell version: ' + bcv[0])
        lines.append('      * NEURON version:    ' + h.nrnversion(0))
        lines.append('      * Python version:    ' + platform.python_version())     # !! maybe get rid of this
        lines.append('*/')
        
        return lines
        
    def getUtilsPrologue(self):
        if not h.exportOptions.isAnyCustomSweptVars():
            return emptyParagraphHint()
            
        lines = self.insertAllLinesFromFile('_Code\\Export\\OutHocFileStructures\\MainHocUtils\\MainHocSweptVarsUtils.hoc')
        
        return lines
        
    # Keep in sync with GenForParamsHoc.getParamsCode
    def getParams(self):
        lines = []
        if h.exportOptions.isCreateParamsHoc:
            
            lines.append('{ load_file("params.hoc") }')
            lines.append('')
            
            lines.append('// Exposed vars')
            concExposedVarsList = list(h.exportOptions.stdExposedVarsList) + list(h.exportOptions.exposedVarsList)
            newLines = self._initCustOrStdExposedOrSweptVars(concExposedVarsList, getExposedVarName, False)
            lines.extend(newLines)
        else:
            for stdExposedVar in h.exportOptions.stdExposedVarsList:
                value = stdExposedVar.getValue()
                if stdExposedVar.isInteger:
                    value = int(value)
                unitsCommentOrEmpty = UnitsUtils.getUnitsCommentOrEmptyForExposedOrSweptVar2(stdExposedVar)
                lines.append(f'{stdExposedVar.customExpr} = {value}{unitsCommentOrEmpty}')
                
        if h.exportOptions.isAnySweptVars():
            newLines = self._initCustOrStdExposedOrSweptVars(h.exportOptions.sweptVarsList, getSweptVarName, True)
            if len(newLines) != 0:
                lines.append('')
                lines.append('// Swept vars')
                lines.extend(newLines)
                
        if h.cvode.active():
            lines.append('')
            lines.append('// CVode')
            lines.append('{ cvode.active(1) }')
            lines.append(f'{{ cvode.atol({h.cvode.atol()}) }}')
            
        return lines
        
    def getUtils(self):
        lines = []
        
        lines.append('objref nil')
        lines.append('')
        
        fileNames = [
            'InterModularErrWarnUtilsPart1_Exported.hoc',
            'InterModularErrWarnUtilsPart2_Exported.hoc',
            'InterModularListUtils_Exported.hoc',
            'InterModularStringUtils_Exported.hoc',
            'InterModularSectionUtilsPart1_Exported.hoc',
        ]
        if h.exportOptions.isExportExtracellularLibrary():
            fileNames.append('InterModularSectionUtilsPart2_Exported.hoc')
        fileNames.append('InterModularOtherUtils_Exported.hoc')
        
        for fileName in fileNames:
            newLines = self.insertAllLinesFromFile('_Code\\InterModular\\Exported\\' + fileName)
            lines.extend(newLines)
            lines.append('')
            
        # The instances of the next reduced templates from "InterModular" folder are created
        # only in standalone mode; otherwise we just reuse the instances created earlier in the main program
        
        newLines = getAllLinesFromReducedVersionFile('InterModular\\ReducedBasicMath.hoc')  # Keep in sync with hoc:loadNanoHocFile
        lines.extend(newLines)
        
        if h.exportOptions.isExportAltRunControl():
            lines.append('')
            newLines = getAllLinesFromReducedVersionFile('InterModular\\ReducedRNGUtils.hoc')
            lines.extend(newLines)
            
        if h.exportOptions.isAnySweptVars() and not h.exportOptions.isAnyCustomSweptVars():
            lines.append('')
            newLines = self.insertAllLinesFromFile('_Code\\Export\\OutHocFileStructures\\MainHocUtils\\MainHocSweptVarsUtils.hoc')
            lines.extend(newLines)
            
        return lines
        
    def checkPrerequisites(self):
        if not h.exportOptions.isPythonRequired():
            return emptyParagraphHint()
            
        lines = []
        
        lines = self.insertAllLinesFromFile('_Code\\Export\\OutHocFileStructures\\PythonCheck.hoc')
        lines.append('')
        
        lines.append('objref pyObj')
        lines.append('pyObj = new PythonObject()')
        
        # !!
        if h.exportOptions.isExportSyns:
            lines.append('')
            newLines = self.insertAllLinesFromFile('_Code\\InterModular\\Exported\\InterModularPythonUtils_Exported.hoc')
            lines.extend(newLines)
            
        return lines
        
    def getAllCreateStatementsExceptNanogeometry(self):
        # output: a string like 'create name1, name2[123], name3[456][7], ...'
        
        secNames = getAllSectionNamesExceptNanogeometry()
        
        createdNames = []
        for secName in secNames:
            createdName = secName.s
            if re.match(r'^(_pysec\.)?EXTRA_CELL_\d+\.', createdName):
                continue    # Extra cell sections are created by createExtraCells(), not by HOC "create"
            
            secObj = self._getHocVar(createdName)
            while True:
                isSecObjOrArray = self._isSecObjOrArray(secObj)
                if isSecObjOrArray:
                    break
                else:
                    createdName += '[{}]'.format(len(secObj))
                    secObj = secObj[0]
                    
            createdNames.append(createdName)
            
        resStr = 'create ' + ', '.join(createdNames)

        return resStr
        
    def createListOfSectionRef(self, usedNamesHocListName, secRefHocListName):
        allLines = []
        newLine = '{} = new List()'.format(secRefHocListName)
        allLines.append(newLine)
        for usedNameHocString in self._getHocVar(usedNamesHocListName):
            usedName = usedNameHocString.s
            secObj = self._getHocVar(usedName)
            isSecObjOrArray = self._isSecObjOrArray(secObj)
            if isSecObjOrArray:
                newLine = '{} {}.append(new SectionRef())'.format(usedName, secRefHocListName)
                allLines.append(newLine)
            else:
                newLines = [
                    'for idx = 0, {} {{'.format(len(secObj) - 1),
                    '    {}[idx] {}.append(new SectionRef())'.format(usedName, secRefHocListName),
                    '}']
                allLines.extend(newLines)
        return allLines
        
    # !! maybe split topology by blocks for soma, dendrites, axon, nanogeometry, other
    def initTopology(self):
        lines = []
        for sec in h.allsec():
            if re.match(r'^EXTRA_CELL_\d+\.', sec.name()):
                continue    # Extra cell topology is built by ExtraCell.__init__, no need to reconnect
            secRef = h.SectionRef(sec)
            if not secRef.has_parent():
                continue
            # Some comments:
            # 1. The syntax "connect child(x), parent(y)" looks simpler than "parent connect child(x), y",
            #    but the former does not work for the sections owned by templates (all nanogeometry in our case)
            # 2. The syntax "sec=sec" is important here; do not replace it with "sec", because the called methods will always return 0
            # 3. Max. precision is applied in the next line by Python automatically
            line = '{} connect {}({}), {}'.format(secRef.parent.name(), sec.name(), h.section_orientation(sec=sec), h.parent_connection(sec=sec))
            lines.append(line)
        return lines
        
    # !! for file "Geometry\Neuron\test.hoc", we have:
    #    AstrocyteNanoBranch[0].SmallGlia[0] { ... pt3dadd(0.075074203312397, -0.07739131152629852, 0.0, 0.10000000149011612
    #    why garbage in diam?
    # !! for file "Geometry\Astrocyte\New Style\AstrocyteBasicGeometry.hoc", we have:
    #    soma[0] { ... pt3dadd(0.23000000417232513, 5.829999923706055, 0.0, 7.22599983215332)
    #    why garbage in x?
    # !! for file "Geometry\Neuron\cellmorphology.hoc", the value of "y" passed to "pt3dadd" is unstable,
    #    i.e. it varies from one export to other
    # !! investigate at which stage of the program the 3D-coordinates of 1st point of 1st imported dendrite become changed (at least in the next files: AstrocyteBasicGeometry.hoc and cellmorphology.hoc)
    #    "connect" command does not change them, so maybe "finitialize"?
    def initGeometry(self):
        lines = []
        for sec in h.allsec():
            if re.match(r'^EXTRA_CELL_\d+\.', sec.name()):
                continue    # Extra cell geometry is built by ExtraCell.__init__, no need to re-emit
            line = '{} {{'.format(sec.name())
            lines.append(line)
            lines.append('    pt3dclear()') # Almost sure that not needed, but Cell Builder's Exporter adds this
            for ptIdx in range(sec.n3d()):
                # Max. precision is applied here automatically
                line = '    pt3dadd({}, {}, {}, {})'.format(sec.x3d(ptIdx), sec.y3d(ptIdx), sec.z3d(ptIdx), sec.diam3d(ptIdx))
                lines.append(line)
            if sec.nseg != self._defaultNseg:
                line = '    nseg = {}'.format(sec.nseg)
                lines.append(line)
            if sec.Ra != self._defaultRa:
                line = '    Ra = {}'.format(sec.Ra)
                lines.append(line)
            lines.append('}')
        return lines
        
    def createDllCheckImportAndEditMeasures(self):
        
        exportOptions = h.exportOptions
        
        lines = []
        
        # Check whether we are in "start with BrainCell export" mode or "standalone" mode
        lines.append('isLoadedFromMainProgram = 1')
        lines.append('{ makeSureDeclared("isBaseOrNanoStart", "isLoadedFromMainProgram = 0") }')
        lines.append('')
        
        cond = exportOptions.isExportDistMechs or exportOptions.isExportGapJuncs or exportOptions.isExportSyns
        
        # Make sure "nrnmech.dll" or "libnrnmech.so" is loaded and valid
        # (doing it even though user could disable the export of biophysics, gap juncs and syns)
        
        lines.append('{ makeSureDeclared("mechsDllUtils") }')
        lines.append('')
        
        if cond:
            lines.append('strdef libErrMsg, libFileName')
            lines.append('libErrMsg = "Please make sure the correct file \\"nrnmech.dll\\" is present in the same folder with this HOC file."')
            lines.append('libFileName = "nrnmech.dll"')
        lines.append('if (isLoadedFromMainProgram) {')
        lines.append('    mechsDllUtils.ifMissingInThisFolderThenLoadDefaultMechsDllDependingOnCellType()')
        if cond:
            lines.append('} else {')
            lines.append('    platformId = unix_mac_pc()')
            lines.append('    if (platformId == 1) {')
            lines.append('        // Assuming NSG supercomputer environment')
            lines.append('        libErrMsg = "Please make sure the file \\"x86_64/.libs/libnrnmech.so\\" was built successfully."')
            lines.append('        libFileName = "libnrnmech.so"')
            lines.append('    } else if (platformId == 3) {')
            lines.append('        // Assuming desktop environment (empty by design)')
            lines.append('    } else {')
            lines.append('        codeContractViolation()')
            lines.append('    }')
        lines.append('}')
        lines.append('')
        
        if cond:
            newLines = getAllLinesFromReducedVersionFile('ReducedMechTypeHelper.hoc')
            lines.extend(newLines)
            lines.append('')
            
            flagNames = []
            if exportOptions.isExportDistMechs:
                newLineOrNone = self._createCallOfCheckForMissingMechsIfNeeded(0)
                if newLineOrNone:
                    lines.append(newLineOrNone)
                    flagNames.append('isAnyDmMissing')
            if exportOptions.isExportGapJuncs or exportOptions.isExportSyns:
                newLineOrNone = self._createCallOfCheckForMissingMechsIfNeeded(1)
                if newLineOrNone:
                    lines.append(newLineOrNone)
                    flagNames.append('isAnyPpMissing')
            if flagNames:
                condStr = ' || '.join(flagNames)
                lines.append(f'if ({condStr}) {{')
                lines.append('    printf("\\n\\n")')
                lines.append('    printMsgAndRaiseError(libErrMsg)')
                lines.append('}')
                lines.append('// !! for better user experience, we should add two more checks here:')
                lines.append('//    1. given mech used in HOC, all referred var names exist in DLL/SO (see the comment in mth.getVarIdx just before printMsgAndRaiseError);')
                lines.append("//    2. given mech array var used in HOC, all referred array idxs don't exceed the array size in DLL/SO")
                
            lines.append('')
            
        if h.isAstrocyteOrNeuron:
            varName = 'GPassive'
            line = '{} = {}    // ({})'.format(varName, h.GPassive, h.units(varName))
            lines.append(line)
            line = '{{ units(&{}, units("g_pas")) }}'.format(varName)
            lines.append(line)      # These units are used by biophys export module
            lines.append('')
            
        # Make sure the staff from ReducedVersions\InterModular is either:
        #   preserved ("start with BrainCell export" mode)
        #   created ("standalone" mode with real usage)
        #   declared as nil ("standalone" mode without real usage OR we'll use it, but first need to bound as template's external, and only then define)
        
        lines.append('{ makeSureDeclared("math", "objref %s", "%s = new ReducedBasicMath()") }')
        
        if exportOptions.isExportAltRunControl():
            # !! BUG: The random sequences won't be the same in the main program and the exported file until
            #         each seed given by rngUtils.getFor_stochFunc_withUniqueSeed is saved into corresponding stocDistFunc
            #         and exported/imported as a part of it
            lines.append('{ makeSureDeclared("rngUtils", "objref %s", "%s = new ReducedRNGUtils()") }')
        elif exportOptions.isExportSyns or exportOptions.isExportInhomAndStochLibrary():    # !!
            lines.append('{ makeSureDeclared("rngUtils") }')
            
        # !! review vvvvv
        
        lines.append('')
        
        # Make sure all the required objref-s are declared as nil
        names = []
        names.append('mmAllComps')
        if exportOptions.isExportInhomAndStochLibrary() or exportOptions.isExportGapJuncs:
            names.append('gjmAllGapJuncSets')
        if exportOptions.isExportInhomAndStochLibrary() or exportOptions.isExportSyns:
            names.append('smAllSynSets')
        if exportOptions.isExportAnyInhomSynModels() or exportOptions.isExportAnyInhomGapJuncModels():  # review !!
            names.append('mcu')     # !! how about mcu4t ?
        if exportOptions.isExportAltRunControl():
            names.append('mmIcrHelper')
        line = 'objref ' + ', '.join(names)
        lines.append(line)
        
        lines.append('objref _comp')
        self._cleanupHelper.scheduleCleanup(lines[-1])
        
        # !! review ^^^^^
        
        return lines
        
    def createInhomAndStochLibrary(self):
        if not h.exportOptions.isExportInhomAndStochLibrary():
            return emptyParagraphHint()
            
        lines = []
        
        newLines = self.insertAllLinesFromFile('_Code\\Managers\\InhomAndStochLibrary\\Exported\\VarLibId.hoc')
        lines.extend(newLines)
        lines.append('')
        
        # !! try to avoid exporting the RNG staff in ReducedInhomAndStochTarget if not h.exportOptions.isExportAnyStochFuncs()
        newLines = getAllLinesFromReducedVersionFile('InhomAndStochLibrary\\ReducedInhomAndStochTarget.hoc')
        lines.extend(newLines)
        lines.append('')
        
        newLines = getAllLinesFromReducedVersionFile('InhomAndStochLibrary\\ReducedInhomAndStochLibrary.hoc')
        lines.extend(newLines)
        lines.append('')
        
        if h.exportOptions.isExportAltRunControl():
            newLines = self.insertAllLinesFromFile('_Code\\Managers\\InhomAndStochLibrary\\Exported\\InhomAndStochApplicator.hoc')
            lines.extend(newLines)
            lines.append('')
            
        lines.append('objref _vecOfVals, _listOfStrs')
        self._cleanupHelper.scheduleCleanup(lines[-1])
        
        return lines
        
    # !! some code dupl. with insertAllUsedStochFuncs
    def insertAllUsedDistFuncs(self):
        if not h.exportOptions.isExportAnyDistFuncs():
            return emptyParagraphHint()
            
        lines = []
        
        dfhTemplNames = set()
        isTablePlusLinInterpDistFuncExported = False
        for actSpecVar in h.inhomAndStochLibrary.activeSpecVars:
            if not h.exportOptions.isExportedInhomVar(actSpecVar):
                continue
            dfhTemplNames.add(getTemplOrClassName(actSpecVar.distFuncHelper))
            if actSpecVar.distFuncCatIdx == h.dfc.tablePlusLinInterpDistFuncCatIdx:
                isTablePlusLinInterpDistFuncExported = True
            
        if isTablePlusLinInterpDistFuncExported:
            # !! just a temp solution: to get rid of this, we need to split TablePlusLinInterpDistFuncHelper template into two:
            #    table from TextEditor/Vector-s and table from file (only the first one will be exported)
            lines.append('{ makeSureDeclared("mwh") }')
            lines.append('')
            lines.append('func selectDistFuncInputFile_deprecated() { codeContractViolation() }')
            lines.append('')
        
        relDirPath = '_Code\\Managers\\InhomAndStochLibrary\\InhomModels\\DistFuncHelpers\\Exported'
        exportTheseTemplatesFromThisDir(lines, relDirPath, dfhTemplNames)
        lines.append('')
        
        if h.exportOptions.isExportSegmentationHelper():
            newLines = getAllLinesFromReducedVersionFile('MechManager\\ReducedSegmentationHelper.hoc')
            lines.extend(newLines)
            lines.append('')
            
        lines.append('objref _segmentationHelper, _distFuncHelper')
        self._cleanupHelper.scheduleCleanup(lines[-1])
        
        return lines
        
    # !! some code dupl. with insertAllUsedDistFuncs
    def insertAllUsedStochFuncs(self):
        if not h.exportOptions.isExportAnyStochFuncs():
            return emptyParagraphHint()
            
        lines = []
        
        # We need to bind these names as templates' external-s even though
        # they won't be used (because we don't call all the methods in the exported file);
        # at the same time, when the file is loaded from the main program, the file needs to:
        # (1) preserve all already created "InterModular" objects and callables (e.g. "mwh" and "eachPointInGrid")
        # (2) stub all required objects and callables allowing them to be defined later in the main program (e.g. "specMath" and "callPythonFunction")
        lines.append('{ makeSureDeclared("mwh") }')
        lines.append('{ makeSureDeclared("eachPointInGrid", "iterator %s() { codeContractViolation() }") }')
        lines.append('{ makeSureDeclared("graphUtils") }')
        lines.append('objref specMath')
        lines.append('func callPythonFunction() { codeContractViolation() }')
        lines.append('proc definePythonFunction() { codeContractViolation() }')
        lines.append('func loadPythonFile() { codeContractViolation() }')
        lines.append('func selectDistFuncInputFile_deprecated() { codeContractViolation() }')
        lines.append('')
        
        sdhTemplNames = set()
        sfhTemplNames = set()
        for actSpecVar in h.inhomAndStochLibrary.activeSpecVars:
            if not h.exportOptions.isExportedStochVar(actSpecVar):
                continue
            stochFuncHelper = actSpecVar.stochFuncHelper
            if actSpecVar.stochFuncCatIdx == h.sfc.simpleModelStochFuncCatIdx:
                sdhTemplNames.add(getTemplOrClassName(stochFuncHelper.distHelper))
            sfhTemplNames.add(getTemplOrClassName(stochFuncHelper))
            
        relDirPath = '_Code\\Managers\\InhomAndStochLibrary\\StochModels\\StochDistHelpers\\Exported'
        exportTheseTemplatesFromThisDir(lines, relDirPath, sdhTemplNames)
        
        relDirPath = '_Code\\Managers\\InhomAndStochLibrary\\StochModels\\StochFuncHelpers\\Exported'
        exportTheseTemplatesFromThisDir(lines, relDirPath, sfhTemplNames)
        
        newLines = self.insertAllLinesFromFile('_Code\\Managers\\Widgets\\Stochasticity\\Exported\\ColourizationHelper.hoc')
        lines.extend(newLines)
        lines.append('')
        
        newLines = self.insertAllLinesFromFile('_Code\\Managers\\Widgets\\Stochasticity\\Exported\\BoundingHelper.hoc')
        lines.extend(newLines)
        lines.append('')
        
        lines.append('objref _colourizationHelper, _boundingHelper, _stochFuncHelper')
        self._cleanupHelper.scheduleCleanup(lines[-1])
        
        return lines
        
    def createReducedMechComps(self):
    
        lines = []
        
        if not h.exportOptions.isExportDistMechs:
            fileName = 'ReducedMechComp1.hoc'   # name, list_ref
        else:
            fileName = 'ReducedMechComp2.hoc'   # name, list_ref, isMechInserted, mechStds
        newLines = getAllLinesFromReducedVersionFile('MechManager\\' + fileName)
        lines.extend(newLines)
        lines.append('')
        
        mmAllComps = h.mmAllComps
        
        # Create number of obfunc-s to prepare "list_ref" for each comp
        # !! BUG: In rare cases, an error "procedure too big" may occur when user loads the exported file.
        #         This error takes place when sourcing one of obfunc-s named "getListOfSecRefsForComp*".
        #         The root cause is that the base geometry file imported earlier
        #         created so many sections on the top level, that we cannot create now in the scope of just one obfunc.
        #         To fix this error, we'll have to init all list_ref-s on the top level rather than in the obfunc-s.
        obfuncNames = []

        for compIdx in range(len(mmAllComps)):
            comp = mmAllComps[compIdx]
            obfuncName = '_getListOfSecRefsForComp{}'.format(compIdx + 1)
            obfuncNames.append(obfuncName)
            lines.append('// "{}"'.format(comp.name))

            # Check if this comp belongs to an extra cell
            extraCellPrefix = None
            m = re.match(r'^Extra Cell #(\d+)$', comp.name)
            if m:
                extraCellPrefix = 'EXTRA_CELL_{}'.format(m.group(1))

            if extraCellPrefix is not None:
                lines.append('obfunc {}() {{ localobj list_ref'.format(obfuncName))
                lines.append('    list_ref = new List()')
                for sec_ref in comp.list_ref:
                    secName = sec_ref.sec.name()
                    lines.append('    forsec "{}" {{ list_ref.append(new SectionRef()) }}'.format(secName))
                lines.append('    return list_ref')
                lines.append('}')
                lines.append('')
            else:
                lines.append('obfunc {}() {{ local idx1, idx2 localobj list_ref'.format(obfuncName))
                lines.append('    list_ref = new List()')
                newLines = []
                for sec_ref in comp.list_ref:
                    newLines.append('    {} list_ref.append(new SectionRef())'.format(sec_ref.sec))
                newLines = LoopUtils.tryInsertLoopsToShorten(newLines, True)
                lines.extend(newLines)
                lines.append('    return list_ref')
                lines.append('}')
                lines.append('')
                
                
            
        lines.append('mmAllComps = new List()')
        
        for (comp, obfuncName) in zip(mmAllComps, obfuncNames):
            lines.append('')
            lines.append('_comp = new ReducedMechComp("{}", {}())'.format(comp.name, obfuncName))
            lines.append('{ mmAllComps.append(_comp) }')
            
        return lines
        
    def initHomogenBiophysics(self):
        return self._gensForHomogenVars.initHomogenBiophysics()
    def createSimAdvanceProc(self):
        try:
            if not h.name_declared('isCaWaveSimActive') or int(h.isCaWaveSimActive) != 1:
                return emptyParagraphHint()

            # Find SimCalciumWave parameters by duck-typing
            caWaveSim = None
            for idx in range(20):
                try:
                    sim = h.simManager.simIdxToWidget[idx]
                    timeDelay = float(sim.TimeDelayCaWave)
                    peakDur   = float(sim.PeakDuration)
                    peakIp3   = float(sim.PeakIp3)
                    caWaveSim = sim
                    break
                except Exception:
                    continue

            if caWaveSim is None:
                return emptyParagraphHint()

            lines = []
            lines.append(f'TimeDelayCaWave = {timeDelay}')
            lines.append(f'PeakDuration    = {peakDur}')
            lines.append(f'PeakIp3         = {peakIp3}')
            lines.append('')
            lines.append('proc advance() {')
            lines.append('    fadvance()')
            lines.append('    if ((t > TimeDelayCaWave) && (t < TimeDelayCaWave + PeakDuration)) {')
            lines.append('        forsec "soma"     { ip3i = PeakIp3 }')
            lines.append('        forsec "dendrite" { ip3i = PeakIp3 }')
            lines.append('    } else {')
            lines.append('        forsec "soma"     { ip3i = ip3i0_ip3_ion }')
            lines.append('        forsec "dendrite" { ip3i = ip3i0_ip3_ion }')
            lines.append('    }')
            lines.append('}')
            return lines

        except Exception:
            return emptyParagraphHint()
    def createInhomBiophysModels(self):
        return self._gensForInhomAndStochModels.createInhomBiophysModels()
        
    def createStochBiophysModels(self):
        return self._gensForInhomAndStochModels.createStochBiophysModels()
        
    def createTemplatesForTaps(self):
        return self._gensForTaps.createTemplatesForTaps()
        
    def createTemplatesForGapJuncs(self):
        return self._gensForTaps.createTemplatesForGapJuncs()
        
    def createTemplatesForSyns(self):
        return self._gensForTaps.createTemplatesForSyns()
        
    def createLocsGivenTapSet(self, isGapJuncOrSyn, tapSetIdx):
        if isGapJuncOrSyn:
            return self._gensForTaps.createGapJuncLocs(tapSetIdx)
        else:
            return self._gensForTaps.createSynLocs(tapSetIdx)
            
    def createReducedCompsGivenTapSet(self, isGapJuncOrSyn, tapSetIdx):
        if isGapJuncOrSyn:
            return self._gensForTaps.createReducedGapJuncComps(tapSetIdx)
        else:
            return self._gensForTaps.createReducedSynComps(tapSetIdx)
            
    def initHomogenVarsGivenTapSet(self, isGapJuncOrSyn, tapSetIdx):
        if isGapJuncOrSyn:
            return self._gensForTaps.initHomogenGapJuncVars(tapSetIdx)
        else:
            return self._gensForTaps.initHomogenSynVars(tapSetIdx)
            
    def createImportAndEditMeasuresGivenTapSet(self, isGapJuncOrSyn, tapSetIdx):
        if isGapJuncOrSyn:
            return self._gensForTaps.createImportAndEditMeasuresForGapJuncs(tapSetIdx)
        else:
            return self._gensForTaps.createImportAndEditMeasuresForSyns(tapSetIdx)
            
    def createMainPartGivenTapSet(self, isGapJuncOrSyn, tapSetIdx):
        if isGapJuncOrSyn:
            return self._gensForTaps.createMainPartForGapJuncs(tapSetIdx)
        else:
            return self._gensForTaps.createMainPartForSyns(tapSetIdx)
            
    def createInhomModelsGivenTapSet(self, isGapJuncOrSyn, tapSetIdx):
        if isGapJuncOrSyn:
            return self._gensForInhomAndStochModels.createInhomGapJuncModels(tapSetIdx)
        else:
            return self._gensForInhomAndStochModels.createInhomSynModels(tapSetIdx)
            
    def createStochModelsGivenTapSet(self, isGapJuncOrSyn, tapSetIdx):
        if isGapJuncOrSyn:
            return self._gensForInhomAndStochModels.createStochGapJuncModels(tapSetIdx)
        else:
            return self._gensForInhomAndStochModels.createStochSynModels(tapSetIdx)
            
    def createCleanup(self):
        return self._cleanupHelper.makeCleanup()

    def createExtraCells(self):
        if not h.name_declared('extraCellsManagerWidget'):
            return emptyParagraphHint()
        widget = h.extraCellsManagerWidget
        if widget is None:
            return emptyParagraphHint()
        items = widget.listOfExtraCellListItems
        if items.count() == 0:
            return emptyParagraphHint()

        # Compute output subdirectory named after the exported HOC file (e.g. "test/" for "test.hoc")
        outMainHocFilePathName = self._outMainHocFilePathName
        outDirPath = os.path.dirname(outMainHocFilePathName)
        outMainHocBaseName = os.path.splitext(os.path.basename(outMainHocFilePathName))[0]
        extraCellsSubDirPath = os.path.join(outDirPath, outMainHocBaseName)
        os.makedirs(extraCellsSubDirPath, exist_ok=True)

        # Copy Python dependencies into export subdirectory for portability
        pyCodeSrcPath = (os.getcwd() + '/_Code/Import/ImportExtraCells/PythonCode').replace('\\', '/')
        interModSrcPath = (os.getcwd() + '/_Code/InterModular/PythonCode').replace('\\', '/')
        tempFolderPath = (os.getcwd() + '/_Code/Import/temp_folder').replace('\\', '/')

        for srcFile, dstName in [
            (pyCodeSrcPath + '/ExtraCell.py',                'ExtraCell.py'),
            (interModSrcPath + '/OtherInterModularUtils.py', 'OtherInterModularUtils.py'),
        ]:
            if os.path.exists(srcFile):
                shutil.copyfile(srcFile, os.path.join(extraCellsSubDirPath, dstName))

        # Relative path from HOC file to the subdirectory containing Python deps and SWC files
        relSubDir = outMainHocBaseName  # e.g. "test" for "test.hoc"
        absExportDir = outDirPath.replace('\\', '/')

        lines = []
        lines.append('load_file("import3d.hoc")')
        lines.append('{ makeSureDeclared("isLoadedFromMainProgram", "isLoadedFromMainProgram = 0") }')

        # Declare objref at top level, guarded by name_declared to avoid resetting on second load
        for itemIdx in range(int(items.count())):
            topLevelName = str(items.o(itemIdx).pyExtraCell)
            lines.append(f'{{ if (!name_declared("{topLevelName}")) execute("objref {topLevelName}") }}')

        lines.append('// Re-instantiate extra cells -- skipped when loaded from BrainCell (cells already exist)')
        lines.append('if (!isLoadedFromMainProgram) {')
        lines.append(f'    {{ nrnpython("import sys, os; _d = os.path.join(os.getcwd(), \'{relSubDir}\'); sys.path.insert(0, _d) if _d not in sys.path else None") }}')
        lines.append('    { nrnpython("from ExtraCell import ExtraCell") }')
        lines.append('    strdef _swcPath')

        for itemIdx in range(int(items.count())):
            item = items.o(itemIdx)
            pyCell = item.pyExtraCell
            srcFilePathName = pyCell.filePathName.replace('\\', '/')
            topLevelName = str(pyCell)
            srcBaseName = os.path.basename(srcFilePathName)
            srcExt = os.path.splitext(srcBaseName)[1].lower()
            dstBaseName = f'extra_cell_{itemIdx + 1}_{os.path.splitext(srcBaseName)[0]}.swc'
            dstFilePathName = os.path.join(extraCellsSubDirPath, dstBaseName).replace('\\', '/')
            if srcExt == '.swc':
                shutil.copyfile(srcFilePathName, dstFilePathName)
            else:
                swcFiles = glob.glob(tempFolderPath + '/*.swc')
                if swcFiles:
                    srcSwcFile = max(swcFiles, key=os.path.getmtime)
                    shutil.copyfile(srcSwcFile, dstFilePathName)
                else:
                    dstBaseName = f'extra_cell_{itemIdx + 1}_{srcBaseName}'
                    dstFilePathName = os.path.join(extraCellsSubDirPath, dstBaseName).replace('\\', '/')
                    shutil.copyfile(srcFilePathName, dstFilePathName)

            # Post-process SWC: remove 3-point soma block and duplicate origin point
            # that cause root section ambiguity on re-import
            with open(dstFilePathName, 'r') as f:
                swcLines = f.readlines()
            filteredLines = []
            somaPointIds = set()
            for swcLine in swcLines:
                parts = swcLine.strip().split()
                if len(parts) < 7:
                    filteredLines.append(swcLine)
                    continue
                pointId, typeId, x, y, z, r, parentId = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6]
                if typeId == '1':  # soma point — skip all
                    somaPointIds.add(pointId)
                elif parentId in somaPointIds and x == '0.0' and y == '0.0' and z == '0.0':
                    # skip duplicate origin dendrite point connected to soma
                    somaPointIds.add(pointId)
                else:
                    filteredLines.append(swcLine)
            with open(dstFilePathName, 'w') as f:
                f.writelines(filteredLines)
            absFilePathName = dstFilePathName.replace('\\', '/')

            xCur = h.ref(0)
            yCur = h.ref(0)
            zCur = h.ref(0)
            item.getCoords(xCur, yCur, zCur)
            xTarget = xCur[0]
            yTarget = yCur[0]
            zTarget = zCur[0]

            swcBaseName = os.path.basename(dstFilePathName)
            lines.append('')
            lines.append(f'    // Extra cell {itemIdx + 1}: {absFilePathName}')
            lines.append(f'    {{ makeSureDeclared("{topLevelName}", "objref {topLevelName}") }}')
            lines.append(f'    {{ nrnpython("from neuron import h; import os; _abs = \'{absExportDir}/{relSubDir}/{swcBaseName}\'; _rel = os.path.join(os.getcwd(), \'{relSubDir}\', \'{swcBaseName}\'); _rel2 = os.path.join(os.path.dirname(os.getcwd()), \'{relSubDir}\', \'{swcBaseName}\'); h._swcPath = _abs if os.path.exists(_abs) else (_rel if os.path.exists(_rel) else _rel2)") }}')
            lines.append(f'    {{ {topLevelName} = pyObj.ExtraCell(_swcPath, "{tempFolderPath}", "{topLevelName}") }}')
            if abs(xTarget) > 1e-9 or abs(yTarget) > 1e-9 or abs(zTarget) > 1e-9:
                lines.append(f'    // Apply spatial position: ({xTarget}, {yTarget}, {zTarget})')
                pyShift = (
                    f"from neuron import h; "
                    f"_ec = h.{topLevelName}; "
                    f"_root = next(sr.sec for sr in _ec.list_ref if not h.SectionRef(sec=sr.sec).has_parent()); "
                    f"_n = _root.n3d(); "
                    f"_cx = (_root.x3d(0) + _root.x3d(_n-1)) / 2; "
                    f"_cy = (_root.y3d(0) + _root.y3d(_n-1)) / 2; "
                    f"_cz = (_root.z3d(0) + _root.z3d(_n-1)) / 2; "
                    f"_dx = {xTarget}-_cx; _dy = {yTarget}-_cy; _dz = {zTarget}-_cz; "
                    f"[s.pt3dchange(i, s.x3d(i)+_dx, s.y3d(i)+_dy, s.z3d(i)+_dz, s.diam3d(i)) "
                    f"for sr in _ec.list_ref for s in [sr.sec] for i in range(s.n3d())]"
                )
                lines.append(f'    {{ nrnpython("{pyShift}") }}')

        lines.append('}')
        return lines


    def createDiffSpeciesLibrary(self):
        return self._gensForExtracellularDiffusion.createSpeciesLibrary()
        
    def createExtraSourcesLibrary(self):
        return self._gensForExtracellularDiffusion.createSourcesLibrary()
        
    def createExtraDiffFinale(self):
        return self._gensForExtracellularDiffusion.createExtraDiffFinale()
        
    def insertAltRunControlWidget(self):
        if not h.exportOptions.isExportAltRunControl():
            return emptyParagraphHint()
            
        lines = self.insertAllLinesFromFile('_Code\\AltRunControl\\Exported\\alt_stdrun.hoc')
        lines.append('')
        
        lines.append('{ makeSureDeclared("mwh") }')
        lines.append('')
        
        newLines = self.insertAllLinesFromFile('_Code\\AltRunControl\\Exported\\AltRunControlWidget.hoc')
        lines.extend(newLines)
        lines.append('')
        
        lines.append('objref altRunControlWidget')
        lines.append('altRunControlWidget = new AltRunControlWidget()')
        lines.append('{ altRunControlWidget.show() }')
        
        return lines
        
    # Keep the filtration logic in sync with hoc:ExportOptions.isAnyWatchedAPCounts and .getFirstValidAPCountOrNil
    def createAPCounts(self):
        
        # By design, we export APCount-s independently on h.exportOptions
        
        allAPCs = h.List('APCount')
        numAPCs = len(allAPCs)
        if numAPCs == 0:
            return emptyParagraphHint()
            
        newLines = []
        threshUnits = UnitsUtils.getUnitsForWatchedVar('APCount[0].thresh')
        for apcIdx in range(numAPCs):
            apc = allAPCs[apcIdx]
            seg = apc.get_segment()
            if seg is None:
                # !! maybe we need to warn user that we skip exporting those APCount-s not attached to any section
                #    (but even an attempt to set or get "thresh" for them leads to an error)
                continue
            newLines.append('')
            newLines.append('{} apCounts[{}] = new APCount({})'.format(seg.sec, apcIdx, seg.x))
            newLines.append('apCounts[{}].thresh = {}    // ({})'.format(apcIdx, apc.thresh, threshUnits))
            
        if len(newLines) == 0:
            return emptyParagraphHint()
            
        lines = []
        lines.append('objref apCounts[{}]'.format(numAPCs))
        lines.extend(newLines)
        
        return lines
        
    def insertAllLinesFromFile(self, relFilePathName):
        return getAllLinesFromFile(relFilePathName)
        
    def getIntegerValueFromTopLevel(self, varName):
        return self._generateAssignment(varName, True)
        
    def getDoubleValueFromTopLevel(self, varName):
        return self._generateAssignment(varName, False)
        
    def getListOfStringsFromTopLevel(self, varName):
        lines = []
        lines.append('objref {}'.format(varName))
        lines.append('{} = new List()'.format(varName))
        listOfStrs = self._getHocVar(varName)
        for thisStr in listOfStrs:
            lines.append('{{ {}.append(new String("{}")) }}'.format(varName, thisStr.s))
        return lines
        
        
    def _initCustOrStdExposedOrSweptVars(self, varsList, getVarName, isSwept):
        lines = []
        for varIdx in range(len(varsList)):
            var = varsList[varIdx]
            if var.enumBioGjSynCeSt < 3:
                continue
            varName = getVarName(varIdx)
            if isSwept:
                notRunnedModeValue = var.getValue()
                sweptVarInitializer = f'getSweptVarValue("{varName}", {notRunnedModeValue})'
                unitsCommentOrEmpty = UnitsUtils.getUnitsCommentOrEmptyForExposedOrSweptVar2(var)
                lines.append(f'{var.customExpr} = {sweptVarInitializer}{unitsCommentOrEmpty}')
            else:
                lines.append(f'{var.customExpr} = {varName}')
        return lines
        
    def _createCallOfCheckForMissingMechsIfNeeded(self, enumDmPp):
        if enumDmPp == 0:
            suffix = 'Dm'
        elif enumDmPp == 1:
            suffix = 'Pp'
        else:
            codeContractViolation()
        mechNames = self._getAllInsertedMechNamesExceptStdAndIons(enumDmPp)
        if len(mechNames) != 0:
            mechNamesStr = '"' + '", "'.join(mechNames) + '"'
            return f'isAny{suffix}Missing = mth.checkForMissingMechs({enumDmPp}, {mechNamesStr})'
        else:
            return None
            
    def _getAllInsertedMechNamesExceptStdAndIons(self, enumDmPp):
        mechIdxsSet = set()
        numMechs = int(h.mth.getNumMechs(enumDmPp))
        mechName = h.ref('')
        
        if enumDmPp == 0:
            if h.exportOptions.isExportDistMechs:
                minMechIdx = int(h.mechsDllUtils.firstCustomDmMechIdx)
                self._analyzeInsertedMechsInAllBiophysComps(h.mmAllComps, minMechIdx, numMechs, mechIdxsSet)
                for mechIdx in list(mechIdxsSet):
                    h.mth.getMechName(0, mechIdx, mechName)
                    if h.mth.isIon(mechName):
                        mechIdxsSet.remove(mechIdx)
        elif enumDmPp == 1:
            minMechIdx = int(h.mechsDllUtils.firstCustomPpMechIdx)
            if h.exportOptions.isExportGapJuncs:
                for gapJuncSet in h.gjmAllGapJuncSets:
                    self._analyzeUsedMechInGapJuncComp(gapJuncSet, minMechIdx, mechIdxsSet)
            if h.exportOptions.isExportSyns:
                for synSet in h.smAllSynSets:
                    self._analyzeUsedMechsInSynComps(synSet, minMechIdx, mechIdxsSet)
        else:
            codeContractViolation()
            
        mechNamesList = []
        for mechIdx in sorted(mechIdxsSet):
            h.mth.getMechName(enumDmPp, mechIdx, mechName)
            mechNamesList.append(mechName[0])
            
        return mechNamesList
        
    def _analyzeInsertedMechsInAllBiophysComps(self, allComps, minMechIdx, numMechs, mechIdxsSet):
        for comp in allComps:
            for mechIdx in range(minMechIdx, numMechs):
                if comp.isMechInserted[mechIdx]:
                    mechIdxsSet.add(mechIdx)
                    
    def _analyzeUsedMechInGapJuncComp(self, gapJuncSet, minMechIdx, mechIdxsSet):
        mechIdx = gapJuncSet.getMechIdxAndOptionalName()    # !! it can return -1, but that's fine
        if mechIdx >= minMechIdx:
            mechIdxsSet.add(mechIdx)
            
    # Keep in sync with hoc:EnumSynCompIdxs.init, hoc:SynSet.init, py:GensForTaps.createReducedSynComps and py:initHomogenSynVars
    def _analyzeUsedMechsInSynComps(self, synSet, minMechIdx, mechIdxsSet):
        if synSet.is3Or1PartInSynStruc():
            enumPpRoles = [h.enumSynPpRoles.srcPp, h.enumSynPpRoles.trgPp]
        else:
            enumPpRoles = [h.enumSynPpRoles.sngPp]
        for enumPpRole in enumPpRoles:
            mechIdx = synSet.getMechIdxAndOptionalName(enumPpRole)  # !! it can return -1, but that's fine
            if mechIdx >= minMechIdx:
                mechIdxsSet.add(mechIdx)
                
    def _getHocVar(self, varName):
        return getattr(h, varName)
        """ !!
        if '.' not in varName:
            return getattr(h, varName)
        else:
            return eval(f'h.{varName}')     # !! for the sections owned by custom templates
        """
        
    def _generateAssignment(self, varName, isIntegerOrDouble):
        value = self._getHocVar(varName)
        if isIntegerOrDouble:
            value = int(value)
        return '{} = {}'.format(varName, value)
        
    def _isSecObjOrArray(self, secObj):
        tp = type(secObj)
        # !! we could use "match-case" here, but it was introduced only in Python 3.10 (2021),
        #    and user may have an older version installed
        if tp == nrn.Section:
            return 1
        elif tp == hoc.HocObject:
            return 0
        else:
            codeContractViolation()
