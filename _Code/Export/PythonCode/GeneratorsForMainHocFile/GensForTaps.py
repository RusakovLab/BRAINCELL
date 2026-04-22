
from neuron import h

from Utils.LoopUtils import LoopUtils
from Utils.OtherUtils import *


class GensForTaps:
    
    # Data members added in the ctor:
    #   _cleanupHelper
    #   _gensForHomogenVars
    #   _gensForInhomAndStochModels
    
    def __init__(self, cleanupHelper, gensForHomogenVars, gensForInhomAndStochModels):
        self._cleanupHelper = cleanupHelper
        self._gensForHomogenVars = gensForHomogenVars
        self._gensForInhomAndStochModels = gensForInhomAndStochModels
        
    # !! test all IF branches
    def createTemplatesForTaps(self):
        
        exportOptions = h.exportOptions
        
        if not exportOptions.isExportAnyTapSets():
            return emptyParagraphHint()
            
        lines = []
        
        newLines = getAllLinesFromReducedVersionFile('ReducedTapSet.hoc')
        lines.extend(newLines)
        lines.append('')
        
        if not exportOptions.isExportAnyInhomTapModels():
            reducedPPCompFileName = 'ReducedPPComp1.hoc'
        else:
            reducedPPCompFileName = 'ReducedPPComp2.hoc'
        newLines = getAllLinesFromReducedVersionFile(reducedPPCompFileName)
        lines.extend(newLines)
        lines.append('')
        
        # !! review the IF cond below
        if not (exportOptions.isExportAnyInhomExtValueGapJuncModels() and exportOptions.isExportAnyInhomNetConSynModels()):
            newLines = getAllLinesFromReducedVersionFile('ReducedFakeComp1.hoc')
            lines.extend(newLines)
            lines.append('')
            
        lines.append('objref _allComps')
        self._cleanupHelper.scheduleCleanup(lines[-1])
        
        return lines
        
    # !! test all IF branches
    def createTemplatesForGapJuncs(self):
        
        exportOptions = h.exportOptions
        
        if not exportOptions.isExportAnyGapJuncSets():
            return emptyParagraphHint()
            
        lines = []
        
        newLines = getAllLinesFromFile('_Code\\Managers\\GapJuncManager\\Exported\\GapJuncEnums.hoc')
        lines.extend(newLines)
        lines.append('')
        
        newLines = getAllLinesFromFile('_Code\\Prologue\\Exported\\GapJunction.hoc')
        lines.extend(newLines)
        lines.append('')
        
        if any(self._isPtrStubInExtGapJuncStrucOfAnySet(gapJuncSet) for gapJuncSet in h.gjmAllGapJuncSets):
            lines.append('{ makeSureDeclared("getGraphedOrPointedVarUnits", "proc %s() { codeContractViolation() }") }')
            lines.append('{ makeSureDeclared("pyObj") }')
            lines.append('')
            
            # !! maybe never export this (use nil)
            newLines = getAllLinesFromFile('_Code\\Managers\\GapJuncManager\\FakesForExtValue\\Exported\\UtilsForFakeMechanismForExtValue.hoc')
            lines.extend(newLines)
            lines.append('')
            
            newLines = getAllLinesFromFile('_Code\\Managers\\GapJuncManager\\FakesForExtValue\\Exported\\FakeMechanismStandardForExtValue.hoc')
            lines.extend(newLines)
        else:
            lines.append('objref utils4FakeMech4GapJuncExtValue')
        lines.append('')
        
        if exportOptions.isExportAnyInhomExtValueGapJuncModels():
            newLines = getAllLinesFromReducedVersionFile('GapJuncManager\\ReducedGapJuncExtValueComp2.hoc')
            lines.extend(newLines)
            lines.append('')
            
        # "Import & Edit" measures
        newLines = getAllLinesFromReducedVersionFile('GapJuncManager\\ReducedSeedingDensityHelper.hoc')
        lines.extend(newLines)
        lines.append('')
        
        newLines = getAllLinesFromReducedVersionFile('GapJuncManager\\ReducedGapJuncSet.hoc')
        lines.extend(newLines)
        lines.append('')
        
        lines.append('gjmAllGapJuncSets = new List()')
        lines.append('')
        
        # !! don't create _sec_ref and _otherSec_ref if there is no int gap juncs
        lines.append('objref _allGapJuncs, _sec_ref, _otherSec_ref, _selected_ref, _seedingDensityHelper, _gapJuncSet')
        self._cleanupHelper.scheduleCleanup(lines[-1])
        
        return lines
        
    # !! test all IF branches
    def createTemplatesForSyns(self):
        
        exportOptions = h.exportOptions
        
        if not exportOptions.isExportAnySynSets():
            return emptyParagraphHint()
            
        lines = []
        
        newLines = getAllLinesFromFile('_Code\\Managers\\SynManager\\Exported\\SynEnums.hoc')
        lines.extend(newLines)
        lines.append('')
        
        newLines = getAllLinesFromFile('_Code\\Prologue\\Neuron\\Exported\\Synapse.hoc')
        lines.extend(newLines)
        lines.append('')
        
        is3PartsInSynStrucOfAnySet = any(synSet.is3Or1PartInSynStruc() for synSet in h.smAllSynSets)
        
        cond = exportOptions.isExportSynEventsHelper() or is3PartsInSynStrucOfAnySet
        if cond:
            newLines = getAllLinesFromReducedVersionFile('ReducedManagersCommonUtils.hoc')
            lines.extend(newLines)
            lines.append('')
            
        if is3PartsInSynStrucOfAnySet:
            newLines = getAllLinesFromFile('_Code\\Managers\\SynManager\\FakesForNetCon\\Exported\\UtilsForFakeMechanismForNetCon.hoc')
            lines.extend(newLines)
            lines.append('')
            
            newLines = getAllLinesFromFile('_Code\\Managers\\SynManager\\FakesForNetCon\\Exported\\FakeMechanismStandardForNetCon.hoc')
            lines.extend(newLines)
        else:
            lines.append('objref utils4FakeMech4SynNetCon')
        lines.append('')
        
        if exportOptions.isExportAnyInhomNetConSynModels():
            newLines = getAllLinesFromReducedVersionFile('SynManager\\ReducedSynNCComp2.hoc')
            lines.extend(newLines)
            lines.append('')
            
        if cond:
            newLines = getAllLinesFromFile('_Code\\Managers\\SynManager\\Exported\\SynEventsHelper.hoc')
            lines.extend(newLines)
            lines.append('')
            
        # "Import & Edit" measures
        newLines = getAllLinesFromReducedVersionFile('SynManager\\ReducedSpineNeckDiamCache.hoc')
        lines.extend(newLines)
        lines.append('')
        
        newLines = getAllLinesFromReducedVersionFile('SynManager\\ReducedSynSet.hoc')
        lines.extend(newLines)
        lines.append('')
        
        lines.append('smAllSynSets = new List()')
        lines.append('')
        
        lines.append('objref _allSyns, _spineNecks_ref, _spineHeads_ref, _diamsVec, _spineNeckDiamCache, _synSet')
        self._cleanupHelper.scheduleCleanup(lines[-1])
        
        return lines
        
    def createGapJuncLocs(self, gapJuncSetIdx):
        
        lines = []
        
        gapJuncSet = h.gjmAllGapJuncSets[gapJuncSetIdx]
        
        lines.append('_allGapJuncs = new List()')
        
        for gapJunc in gapJuncSet.allGapJuncs:
            if gapJuncSet.isExtOrInt:
                lines.append('{} _allGapJuncs.append(new GapJunction(new SectionRef(), {}))'.format(gapJunc.sec_ref.sec, gapJunc.connectionPoint))
            else:
                lines.append('')
                lines.append('{} _sec_ref = new SectionRef()'.format(gapJunc.sec_ref.sec))
                lines.append('{} _otherSec_ref = new SectionRef()'.format(gapJunc.otherSec_ref.sec))
                lines.append('{{ _allGapJuncs.append(new GapJunction(_sec_ref, {}, _otherSec_ref, {})) }}'.format(gapJunc.connectionPoint, gapJunc.otherConnectionPoint))
                
        return lines
        
    def createSynLocs(self, synSetIdx):
        
        lines = []
        
        synSet = h.smAllSynSets[synSetIdx]
        
        lines.append('_allSyns = new List()')
        
        newLines = []
        for syn in synSet.allSyns:
            newLines.append('{} _allSyns.append(new Synapse(new SectionRef(), {}))'.format(syn.sec_ref.sec, syn.connectionPoint))
            
        enumSynLoc = synSet.enumSynLoc
        randomSynLocP = synSet.randomSynLocP
        if enumSynLoc == 0 or (enumSynLoc == 2 and randomSynLocP <= 0.25):  # !! some hardcoded heuristic threshold
            newLines = LoopUtils.tryInsertLoopsToShorten(newLines, False)
            
        lines.extend(newLines)
        
        return lines
        
    # Keep in sync with hoc:EnumGapJuncCompIdxs.init, hoc:GapJuncSet.init and py:GensForTaps.initHomogenGapJuncVars
    def createReducedGapJuncComps(self, gapJuncSetIdx):
        
        lines = []
        
        gapJuncSet = h.gjmAllGapJuncSets[gapJuncSetIdx]
        
        lines.append('_allComps = new List()')
        
        sngPpRoleStr = 'enumGapJuncPpRoles.sngPp'
        extMechIdxOrMinus1, intMechIdxOrMinus1 = self._getGapJuncMechIdxs(gapJuncSet)
        
        # Keep in sync with hoc:EnumGapJuncCompIdxs.init, hoc:GapJuncSet.init and py:GensForTaps.initHomogenGapJuncVars
        # Note: NEURON doesn't allow appending "nil" to a List, so we don't optimize this depending on isExtOrInt
        self._appendNewReducedPPComp(lines, 1, 'External GJ', sngPpRoleStr, extMechIdxOrMinus1)
        self._appendNewReducedFakeComp(lines, 1)
        self._appendNewReducedPPComp(lines, 1, 'Internal GJ', sngPpRoleStr, intMechIdxOrMinus1)
        
        return lines
        
    # Keep in sync with hoc:EnumSynCompIdxs.init, hoc:SynSet.init, py:GeneratorsForMainHocFile._analyzeUsedMechsInSynComps and py:GensForTaps.initHomogenSynVars
    def createReducedSynComps(self, synSetIdx):
        
        lines = []
        
        synSet = h.smAllSynSets[synSetIdx]
        enumSynPpRoles = h.enumSynPpRoles
        
        lines.append('_allComps = new List()')
        
        srcPpRoleStr = 'enumSynPpRoles.srcPp'
        trgPpRoleStr = 'enumSynPpRoles.trgPp'
        sngPpRoleStr = 'enumSynPpRoles.sngPp'
        srcMechIdxOrMinus1 = int(synSet.getMechIdxAndOptionalName(enumSynPpRoles.srcPp))
        trgMechIdxOrMinus1 = int(synSet.getMechIdxAndOptionalName(enumSynPpRoles.trgPp))
        sngMechIdxOrMinus1 = int(synSet.getMechIdxAndOptionalName(enumSynPpRoles.sngPp))
        
        # Keep in sync with hoc:EnumSynCompIdxs.init, hoc:SynSet.init and py:GensForTaps.initHomogenSynVars
        # Note: NEURON doesn't allow appending "nil" to a List, so we don't optimize this depending on is3Or1PartInSynStruc
        self._appendNewReducedPPComp(lines, 0, 'Source PP', srcPpRoleStr, srcMechIdxOrMinus1)
        self._appendNewReducedFakeComp(lines, 0)
        self._appendNewReducedPPComp(lines, 0, 'Target PP', trgPpRoleStr, trgMechIdxOrMinus1)
        self._appendNewReducedPPComp(lines, 0, 'Single PP', sngPpRoleStr, sngMechIdxOrMinus1)
        
        return lines
        
    # Keep in sync with hoc:EnumGapJuncCompIdxs.init, hoc:GapJuncSet.init and py:GensForTaps.createReducedGapJuncComps
    def initHomogenGapJuncVars(self, gapJuncSetIdx):
        
        gapJuncSet = h.gjmAllGapJuncSets[gapJuncSetIdx]
        
        extMechIdxOrMinus1, intMechIdxOrMinus1 = self._getGapJuncMechIdxs(gapJuncSet)
        
        mechIdxs = [None] * 3
        mechIdxs[0] = extMechIdxOrMinus1                                # "External GJ"
        mechIdxs[1] = int(h.utils4FakeMech4GapJuncExtValue.mechIdx)     # "External Value"
        mechIdxs[2] = intMechIdxOrMinus1                                # "Internal GJ"
        
        return self._gensForHomogenVars.initHomogenTapVars( \
            gapJuncSet.allComps, \
            mechIdxs, \
            'GapJunc', \
            gapJuncSetIdx, \
            1, \
            self._gensForHomogenVars.isExportedGapJuncComp, \
            h.exportOptions.isExportGapJuncAssignedAndState, \
            h.exportOptions.isExportGapJuncInhoms)
            
    # Keep in sync with hoc:EnumSynCompIdxs.init, hoc:SynSet.init, py:GeneratorsForMainHocFile._analyzeUsedMechsInSynComps and py:GensForTaps.createReducedSynComps
    def initHomogenSynVars(self, synSetIdx):
        
        synSet = h.smAllSynSets[synSetIdx]
        enumSynPpRoles = h.enumSynPpRoles
        
        mechIdxs = [None] * 4
        mechIdxs[0] = int(synSet.getMechIdxAndOptionalName(enumSynPpRoles.srcPp))   # "Source PP"
        mechIdxs[1] = int(h.utils4FakeMech4SynNetCon.mechIdx)                       # "NetCon"
        mechIdxs[2] = int(synSet.getMechIdxAndOptionalName(enumSynPpRoles.trgPp))   # "Target PP"
        mechIdxs[3] = int(synSet.getMechIdxAndOptionalName(enumSynPpRoles.sngPp))   # "Single PP"
        
        return self._gensForHomogenVars.initHomogenTapVars( \
            synSet.allComps, \
            mechIdxs, \
            'Syn', \
            synSetIdx, \
            0, \
            self._gensForHomogenVars.isExportedSynComp, \
            h.exportOptions.isExportSynAssignedAndState, \
            h.exportOptions.isExportSynInhoms)
            
    def createImportAndEditMeasuresForGapJuncs(self, gapJuncSetIdx):
        
        lines = []
        
        gapJuncSet = h.gjmAllGapJuncSets[gapJuncSetIdx]
        
        selected_ref = gapJuncSet.selected_ref
        seedingDensityHelper = gapJuncSet.seedingDensityHelper
        
        if selected_ref is not None:
            lines.append('_selected_ref = new List()')
            newLines = []
            for sec_ref in selected_ref:
                newLines.append('{} _selected_ref.append(new SectionRef())'.format(sec_ref.sec))
                
            # !! BUG 1: does nothing for "AstrocyteBasicGeometry.hoc" despite the clear pattern
            #    BUG 2: not very effective for "cellmorphology.hoc" because we don't sort the sections
            newLines = LoopUtils.tryInsertLoopsToShorten(newLines, True)
            
            lines.extend(newLines)
        else:
            lines.append('_selected_ref = nil')
            
        lines.append('')
        lines.append('_seedingDensityHelper = new ReducedSeedingDensityHelper({}, {}, "{}")'.format( \
            int(seedingDensityHelper.isUniform), \
            seedingDensityHelper.minSeedingDistance, \
            seedingDensityHelper.oneLinerPyDistFuncBody))
            
        return lines
        
    def createImportAndEditMeasuresForSyns(self, synSetIdx):
        
        lines = []
        
        synSet = h.smAllSynSets[synSetIdx]
        
        newLines = self._createListOfSpineNeckOrHeadRefs(synSet.spineNecks_ref, 'Necks')
        lines.extend(newLines)
        
        lines.append('')
        newLines = self._createListOfSpineNeckOrHeadRefs(synSet.spineHeads_ref, 'Heads')
        lines.extend(newLines)
        
        diamsVec = synSet.spineNeckDiamCache.diamsVec
        numSpines = len(diamsVec)
        
        lines.append('')
        lines.append('_diamsVec = new Vector({})'.format(numSpines))
        for spineIdx in range(numSpines):
            lines.append('_diamsVec.x({}) = {}'.format(spineIdx, diamsVec[spineIdx]))
            
        lines.append('')
        lines.append('_spineNeckDiamCache = new ReducedSpineNeckDiamCache(_diamsVec)')
        
        return lines
        
    def createMainPartForGapJuncs(self, gapJuncSetIdx):
        
        lines = []
        
        gapJuncSet = h.gjmAllGapJuncSets[gapJuncSetIdx]
        
        mechName = h.ref('')
        gapJuncSet.getMechIdxAndOptionalName(mechName)
        mechName = mechName[0]
        
        fixedMechIdx = int(h.utils4FakeMech4GapJuncExtValue.mechIdx)
        
        pyObj = h.pyObj     # !! or import ?
        doesHavePtr = pyObj.ms_doesGapJuncHavePtr(mechName)
        if doesHavePtr:
            ppPtrName = pyObj.ms_getGapJuncPtrName(mechName)
            dmVarNameWithIndex = pyObj.ms_getGapJuncExtVarNameWithIndex(mechName)
        else:
            ppPtrName = ''
            dmVarNameWithIndex = ''
            
        lines.append('_gapJuncSet = new ReducedGapJuncSet(_allGapJuncs, _allComps, {}, {}, _selected_ref, {}, {}, {}, _seedingDensityHelper)'.format( \
            int(gapJuncSet.isExtOrInt), \
            int(gapJuncSet.isAllOrSomeSecsSeeded), \
            int(gapJuncSet.maxNumGapJuncsPerSec), \
            gapJuncSet.maxRadiusForIntGapJuncs, \
            int(gapJuncSet.isCrissCrossForIntGapJuncs)))
        lines.append('')
        lines.append('{{ _gapJuncSet.createGapJuncStruc("{}", {}, "{}", "{}") }}'.format( \
            mechName, \
            int(doesHavePtr), \
            ppPtrName, \
            dmVarNameWithIndex))
        lines.append('{{ _gapJuncSet.initAllHomogenVars("{}", {}) }}'.format(mechName, fixedMechIdx))
        lines.append('')
        lines.append('// {}'.format(gapJuncSet.s))
        lines.append('{ gjmAllGapJuncSets.append(_gapJuncSet) }')
        
        return lines
        
    def createMainPartForSyns(self, synSetIdx):
        
        lines = []
        
        synSet = h.smAllSynSets[synSetIdx]
        enumSynPpRoles = h.enumSynPpRoles
        
        is3Or1PartInSynStruc = int(synSet.is3Or1PartInSynStruc())
        srcMechName = h.ref('')
        trgMechName = h.ref('')
        sngMechName = h.ref('')
        synSet.getMechIdxAndOptionalName(enumSynPpRoles.srcPp, srcMechName)
        synSet.getMechIdxAndOptionalName(enumSynPpRoles.trgPp, trgMechName)
        synSet.getMechIdxAndOptionalName(enumSynPpRoles.sngPp, sngMechName)
        srcMechName = srcMechName[0]
        trgMechName = trgMechName[0]
        sngMechName = sngMechName[0]
        
        lines.append('_synSet = new ReducedSynSet(_allSyns, _allComps, {}, {}, _spineNecks_ref, _spineHeads_ref, _spineNeckDiamCache, {}, isMinRPlt1, {})'.format( \
            int(synSet.enumSynLoc), \
            synSet.randomSynLocP, \
            int(synSet.idxForSynSet), \
            int(synSet.seh.isSefwEnabled())))
        lines.append('')
        args = '{}, "{}", "{}", "{}"'.format( \
            is3Or1PartInSynStruc, \
            srcMechName, \
            trgMechName, \
            sngMechName)
        lines.append('{{ _synSet.createSynStruc({}) }}'.format(args))
        lines.append('{{ _synSet.initAllHomogenVars({}) }}'.format(args))
        lines.append('')
        lines.append('// {}'.format(synSet.s))
        lines.append('{ smAllSynSets.append(_synSet) }')
        
        return lines
        
        
    def _isPtrStubInExtGapJuncStrucOfAnySet(self, gapJuncSet):
        pyObj = h.pyObj     # !!
        mechName = h.ref('')
        gapJuncSet.getPpNameOrEmpty(mechName)
        mechName = mechName[0]
        return gapJuncSet.isExtOrInt and pyObj.ms_doesGapJuncHavePtr(mechName)
        
    def _appendNewReducedPPComp(self, lines, isGapJuncOrSyn, compName, enumPpRoleStr, mechIdxOrMinus1):
        if mechIdxOrMinus1 != -1:
            mechName = h.ref('')
            h.mth.getMechName(1, mechIdxOrMinus1, mechName)
            mechNameOrEmpty = mechName[0]
        else:
            mechNameOrEmpty = ''
        lines.append('{{ _allComps.append(new ReducedPPComp({}, "{}", {}, "{}")) }}'.format(isGapJuncOrSyn, compName, enumPpRoleStr, mechNameOrEmpty))
        
    def _appendNewReducedFakeComp(self, lines, isGapJuncOrSyn):
        exportOptions = h.exportOptions
        if isGapJuncOrSyn:
            if exportOptions.isExportAnyInhomExtValueGapJuncModels():
                ctorNameWithArgs = 'ReducedGapJuncExtValueComp()'
            else:
                ctorNameWithArgs = 'ReducedFakeComp(enumGapJuncPpRoles.extValue, {})'.format(int(h.utils4FakeMech4GapJuncExtValue.mechIdx))
        else:
            if exportOptions.isExportAnyInhomNetConSynModels():
                ctorNameWithArgs = 'ReducedSynNCComp()'
            else:
                ctorNameWithArgs = 'ReducedFakeComp(enumSynPpRoles.netCon, {})'.format(int(h.utils4FakeMech4SynNetCon.mechIdx))
        lines.append(f'{{ _allComps.append(new {ctorNameWithArgs}) }}')
        
    def _createListOfSpineNeckOrHeadRefs(self, spineNecksOrHeads_ref, NeckOrHeadStr):
        lines = []
        lines.append('_spine{}_ref = new List()'.format(NeckOrHeadStr))
        for spineNeckOrHead_ref in spineNecksOrHeads_ref:
            lines.append('{} _spine{}_ref.append(new SectionRef())'.format(spineNeckOrHead_ref.sec, NeckOrHeadStr))
        lines = LoopUtils.tryInsertLoopsToShorten(lines, False)
        return lines
        
    def _getGapJuncMechIdxs(self, gapJuncSet):
        mechIdx = int(gapJuncSet.getMechIdxAndOptionalName())
        if gapJuncSet.isExtOrInt:
            extMechIdxOrMinus1 = mechIdx
            intMechIdxOrMinus1 = -1
        else:
            extMechIdxOrMinus1 = -1
            intMechIdxOrMinus1 = mechIdx
        return extMechIdxOrMinus1, intMechIdxOrMinus1
        