
import math

from neuron import h

from Utils.UnitsUtils import UnitsUtils
from Utils.OtherUtils import *


class GensForHomogenVars:
    
    def initHomogenBiophysics(self):
        if not h.exportOptions.isExportDistMechs:
            return emptyParagraphHint()
            
        lines = []
        
        mmAllComps = h.mmAllComps
        
        # Create number of proc-s to prepare and set "isMechInserted" and "mechStds" for each mech comp
        procNames = []
        mth = h.mth
        enumDmPpFk = 0
        mechName = h.ref('')
        for compIdx in range(len(mmAllComps)):
            comp = mmAllComps[compIdx]
            procName = '_addHomogenVarsInfoToBiophysComp{}'.format(compIdx + 1)
            procNames.append(procName)
            lines.append('// "{}"'.format(comp.name))
            lines.append('proc {}() {{ local idx localobj comp, mechIdxs, mechStd'.format(procName))
            lines.append('    comp = $o1')
            lines.append('    ')
            
            numMechs = int(mth.getNumMechs(enumDmPpFk))
            insMechIdxs = [mechIdx for mechIdx in range(numMechs) if comp.isMechInserted[mechIdx]]
            numInsMechs = len(insMechIdxs)
            lines.append('    mechIdxs = new Vector({})'.format(numInsMechs))
            for mechInVecIdx, mechIdx in enumerate(insMechIdxs):
                mth.getMechName(enumDmPpFk, mechIdx, mechName)
                lines.append('    mechIdxs.x[{}] = mth.getMechIdx({}, "{}")'.format(mechInVecIdx, enumDmPpFk, mechName[0]))
            lines.append('    ')
            
            if numInsMechs > 1:
                lines.append('    for idx = 0, {} {{'.format(numInsMechs - 1))
                lines.append('        comp.isMechInserted[mechIdxs.x[idx]] = 1')
                lines.append('    }')
            else:
                lines.append('    comp.isMechInserted[mechIdxs.x[0]] = 1')
            lines.append('    ')
            
            for mechInVecIdx, mechIdx in enumerate(insMechIdxs):
                # Generate code to init "mechStds" array slice for this mech of this comp
                mechIdxStr = 'mechIdxs.x[{}]'.format(mechInVecIdx)
                newLines = self._exportHomogenVarsOfThisMech(-1, -1, compIdx, comp, mechIdx, mechIdxStr, h.exportOptions.isExportDistMechAssignedAndState, h.exportOptions.isExportDistMechInhoms)
                lines.extend(newLines)
                
            lines[-1] = '}'
            lines.append('')
            
        # For each comp, generate the call of corresponding proc
        newLines = self._finishExportOfHomogenVars(mmAllComps, 'mmAllComps', procNames)
        lines.extend(newLines)
        
        lines.append('')
        lines.append('for eachItemInList(_comp, mmAllComps) {')
        lines.append('    _comp.initHomogenBiophysics()')
        lines.append('}')
        
        # Export ion GLOBAL initial concentrations and cadifus GLOBAL overrides
        globalExportLines = []

        # Check if cadifus with ip3 dynamics is actually inserted
        isCaWaveActive = False
        try:
            if h.name_declared('isCaWaveSimActive') and int(h.isCaWaveSimActive) == 1:
                isCaWaveActive = True
        except Exception:
            pass

        if isCaWaveActive:
            for globalName in ['ip3i0_ip3_ion', 'cai0_ca_ion']:
                if h.name_declared(globalName):
                    value = getattr(h, globalName)
                    sweptLine = None
                    if h.exportOptions.isAnySweptVars():
                        for svIdx in range(len(h.exportOptions.sweptVarsList)):
                            sv = h.exportOptions.sweptVarsList[svIdx]
                            if hasattr(sv, 'customExpr') and globalName in sv.customExpr:
                                svName = getSweptVarName(svIdx)
                                sweptLine = f'{sv.customExpr} = getSweptVarValue("{svName}", {value})'
                                break
                    if sweptLine:
                        globalExportLines.append(sweptLine)
                    else:
                        globalExportLines.append(f'{globalName} = {value}    // (mM)')

            cadifusGlobals = [
                ('DCa_cadifus',   0.22),
                ('TBufs_cadifus', 0.450),
                ('TBufm_cadifus', 0.075),
                ('cath_cadifus',  0.2e-3),
                ('gamma_cadifus', 8.0),
            ]
            for globalName, modDefault in cadifusGlobals:
                if h.name_declared(globalName):
                    value = getattr(h, globalName)
                    if value != modDefault:
                        globalExportLines.append(f'{globalName} = {value}')

        if globalExportLines:
            lines.append('')
            lines.append('// Ion GLOBAL initial concentrations and cadifus overrides')
            lines.extend(globalExportLines)

        return lines
        
    def initHomogenTapVars(self, allComps, mechIdxsOrMinus1, gapJuncOrSynStr, tapSetIdx, isGapJuncOrSyn, isExportedCompPredicate, isExportAssignedAndState, isExportInhoms):
        
        lines = []
        
        if not isGapJuncOrSyn:
            lines.append('isMinRPlt1 = 0')
            lines.append('')
            
        # Create number of proc-s to prepare and set "mechStds" for each tap comp
        procNames = []
        mechName = h.ref('')
        for compIdx, mechIdxOrMinus1 in zip(range(len(allComps)), mechIdxsOrMinus1):
            comp = allComps[compIdx]
            procName = '_addHomogenVarsInfoTo{}Comp{}'.format(gapJuncOrSynStr, compIdx + 1)
            procNames.append(procName)
            lines.append('// "{}"'.format(comp.name))
            lines.append('proc {}() {{ local mechIdx localobj comp, mechStd'.format(procName))
            lines.append('    comp = $o1')
            lines.append('    ')
            if mechIdxOrMinus1 != -1 and isExportedCompPredicate(tapSetIdx, compIdx):
                newLines = self._exportHomogenVarsOfThisMech(isGapJuncOrSyn, tapSetIdx, compIdx, comp, mechIdxOrMinus1, 'mechIdx', isExportAssignedAndState, isExportInhoms)
                if newLines:
                    enumDmPpFk = comp.enumDmPpFk
                    h.mth.getMechName(enumDmPpFk, mechIdxOrMinus1, mechName)
                    lines.append('    mechIdx = mth.getMechIdx({}, "{}")'.format(int(enumDmPpFk), mechName[0]))
                    lines.append('    ')
                    lines.extend(newLines)
                    
            lines[-1] = '}'
            lines.append('')
            
        # For each comp, generate the call of corresponding proc
        newLines = self._finishExportOfHomogenVars(allComps, '_allComps', procNames)
        lines.extend(newLines)
        
        return lines
        
    def isExportedGapJuncComp(self, gapJuncSetIdx, compIdx):
        isExtOrInt = h.gjmAllGapJuncSets[gapJuncSetIdx].isExtOrInt
        enumGapJuncCompIdxs = h.enumGapJuncCompIdxs
        if isExtOrInt:
            return compIdx in [enumGapJuncCompIdxs.extGjPp, enumGapJuncCompIdxs.extGjExtValue]
        else:
            return compIdx == enumGapJuncCompIdxs.intGjPp
            
    def isExportedSynComp(self, synSetIdx, compIdx):
        is3Or1PartInSynStruc = h.smAllSynSets[synSetIdx].is3Or1PartInSynStruc()
        enumSynCompIdxs = h.enumSynCompIdxs
        if is3Or1PartInSynStruc:
            return compIdx in [enumSynCompIdxs.srcPp, enumSynCompIdxs.netCon, enumSynCompIdxs.trgPp]
        else:
            return compIdx == enumSynCompIdxs.sngPp
            
            
    # Generate code to init "mechStds" array slice for this mech of this comp
    def _exportHomogenVarsOfThisMech(self, isGapJuncOrSyn, tapSetIdx, compIdx, comp, mechIdx, mechIdxStr, isExportAssignedAndState, isExportInhoms):
        lines = []
        
        mth = h.mth
        mcu = h.mcu
        inhomAndStochLibrary = h.inhomAndStochLibrary
        
        isAnyExposedVars = h.exportOptions.isAnyExposedVars()
        isAnySweptVars = h.exportOptions.isAnySweptVars()
        
        mechName = h.ref('')
        enumDmPpFk = comp.enumDmPpFk
        mth.getMechName(enumDmPpFk, mechIdx, mechName)
        mechName = mechName[0]
        if enumDmPpFk != 2:
            if isExportAssignedAndState:
                maxVarType = 3
            else:
                maxVarType = 1
        else:
            maxVarType = 1
            
        for varType in range(1, maxVarType + 1):    # 1: "PARAMETER", 2: "ASSIGNED", 3: "STATE"
            varTypeIdx = int(mth.convertVarTypeToVarTypeIdx(varType))
            varTypeName = h.ref('')
            mth.getVarTypeName(varType, varTypeName)
            varTypeName = varTypeName[0]
            if enumDmPpFk != 2:
                defaultMechStd = h.MechanismStandard(mechName, varType)
            else:
                if isGapJuncOrSyn:
                    defaultMechStd = h.FakeMechanismStandardForExtValue()
                    fakeMechStdTemplName = 'FakeMechanismStandardForExtValue'
                else:
                    defaultMechStd = h.FakeMechanismStandardForNetCon()
                    fakeMechStdTemplName = 'FakeMechanismStandardForNetCon'
            newLines = []
            isAllDefault = True
            if enumDmPpFk != 2:
                newLines.append('    mechStd = new MechanismStandard("{}", {})    // {}'.format(mechName, varType, varTypeName))
            else:
                newLines.append('    mechStd = new {}()'.format(fakeMechStdTemplName))
            numVars = int(mth.getNumMechVars(enumDmPpFk, mechIdx, varType))
            for varIdx in range(numVars):
                varName = h.ref('')
                arraySize = int(mth.getVarNameAndArraySize(enumDmPpFk, mechIdx, varType, varIdx, varName))
                varName = varName[0]
                for arrayIndex in range(arraySize):
                    isContinue, isExposedOrSweptVar, isValueNaN, valueOrMathNaNOrExposedNameOrSweptInitializer, unitsCommentOrEmpty = self._getOneValueInfo(enumDmPpFk, isGapJuncOrSyn, tapSetIdx, compIdx, mechIdx, varType, varIdx, arrayIndex,  comp, varTypeIdx, varName, arraySize, defaultMechStd, isExportInhoms, isAnyExposedVars, isAnySweptVars)
                    if isContinue:
                        continue
                    if arraySize == 1:
                        newLines.append('    mechStd.set("{}", {}){}'.format(varName, valueOrMathNaNOrExposedNameOrSweptInitializer, unitsCommentOrEmpty))
                        if not isGapJuncOrSyn and enumDmPpFk == 2 and mcu.isMetaVar(varName):
                            if isExposedOrSweptVar:
                                # !! for swept vars, the generated code calls "getSweptVarValue" twice;
                                #    it would be better to assign the value to a local var and then use it twice
                                newLines.append(f'    isMinRPlt1 = ({valueOrMathNaNOrExposedNameOrSweptInitializer} < 1)')
                            elif isValueNaN or valueOrMathNaNOrExposedNameOrSweptInitializer < 1:
                                newLines.append('    isMinRPlt1 = 1')
                    else:
                        newLines.append('    mechStd.set("{}", {}, {}){}'.format(varName, valueOrMathNaNOrExposedNameOrSweptInitializer, arrayIndex, unitsCommentOrEmpty))
                    isAllDefault = False
                    
            if isAllDefault:
                continue
                
            newLines.append('    comp.mechStds[{}][{}] = mechStd'.format(mechIdxStr, varTypeIdx))
            newLines.append('    ')
            
            lines.extend(newLines)
            
        return lines
        
    def _getOneValueInfo(self, enumDmPpFk, isGapJuncOrSyn, tapSetIdx, compIdx, mechIdx, varType, varIdx, arrayIndex,  comp, varTypeIdx, varName, arraySize, defaultMechStd, isExportInhoms, isAnyExposedVars, isAnySweptVars):
    
        # !! need to make sure that user doesn't select the same var as both exposed and swept,
        #    but selection of a fixed exposed var (e.g. "v_init" or other from h.exportOptions.stdExposedVarsList) as a swept var is fine:
        #    in this case, we'll use the swept value and ignore the fixed exposed value
        
        mth = h.mth
        
        value = comp.mechStds[mechIdx][varTypeIdx].get(varName, arrayIndex)
        
        varNameWithIndex = h.ref('')
        mth.getVarNameWithIndex(varName, arraySize, arrayIndex, varNameWithIndex)
        varNameWithIndex = varNameWithIndex[0]
        unitsCommentOrEmpty = UnitsUtils.getUnitsCommentOrEmptyForDmOrTapPart(enumDmPpFk, mechIdx, varName, varNameWithIndex)
        
        if isAnySweptVars:
            sweptVarNameOrEmpty = self._getExposedOrSweptVarNameOrEmpty(False, enumDmPpFk, isGapJuncOrSyn, tapSetIdx, compIdx, mechIdx, varType, varName, arrayIndex, h.exportOptions.sweptVarsList, getSweptVarName)
            if sweptVarNameOrEmpty:
                sweptVarInitializer = f'getSweptVarValue("{sweptVarNameOrEmpty}", {value})'
                return False, True, None, sweptVarInitializer, unitsCommentOrEmpty
                
        if isAnyExposedVars:
            exposedVarNameOrEmpty = self._getExposedOrSweptVarNameOrEmpty(True, enumDmPpFk, isGapJuncOrSyn, tapSetIdx, compIdx, mechIdx, varType, varName, arrayIndex, h.exportOptions.exposedVarsList, getExposedVarName)
            if exposedVarNameOrEmpty:
                return False, True, None, exposedVarNameOrEmpty, ''
                
        # Decide whether to skip "mechStd.set" for this var;
        # for stoch vars, we don't skip it even though the value is default
        # because we'll need to read it just before adding the noise
        varLibId = h.VarLibId(enumDmPpFk, isGapJuncOrSyn, tapSetIdx, compIdx, mechIdx, varType, varIdx, arrayIndex)
        if not h.inhomAndStochLibrary.isStochEnabledFor(varLibId):
            defaultValue = defaultMechStd.get(varName, arrayIndex)
            # !! not sure about the 2nd condition in IF below,
            #    but it found out for ASSIGNED "ko_IKa" from "IPotassium.mod" that its default value
            #    is different depending on the moment when we created a new MechanismStandard:
            #    just after the start of our program (defaultValue = 0) or now (defaultValue = 2.5)
            if (varType == 1 and value == defaultValue) or (varType > 1 and value == 0):
                return True, None, None, None, None
                
        isValueNaN = math.isnan(value)
        if isValueNaN:
            unitsCommentOrEmpty = ''
            if isExportInhoms:
                value = 'math.nan'
            else:
                if mth.isDiamDistMechVar(mechIdx, varType, varName):
                    value = 'math.nan'
                else:
                    # If user applied an inhomogeneity to NetCon.@release_probability, but disabled export of syn inhoms,
                    # then the probability var gets effectively reverted to its default const value "1" and the 5-chain synapses become the 3-chain ones
                    # (except the case of stochasticity enabled)
                    return True, None, None, None, None
                    
        return False, False, isValueNaN, value, unitsCommentOrEmpty
        
    def _getExposedOrSweptVarNameOrEmpty(self, isExposedOrSweptVar, enumDmPpFk, isGapJuncOrSyn, tapSetIdx, compIdx, mechIdx, varType, varName, arrayIndex, varsList, getVarName):
        for varIdx in range(len(varsList)):
            if varsList[varIdx].isEqual(enumDmPpFk, isGapJuncOrSyn, tapSetIdx, compIdx, mechIdx, varType, varName, arrayIndex):
                if isExposedOrSweptVar:
                    varIdx += len(h.exportOptions.stdExposedVarsList)
                return getVarName(varIdx)
        return ''
        
    # For each comp, generate the call of corresponding proc
    def _finishExportOfHomogenVars(self, allComps, allCompsVarName, procNames):
        lines = []
        
        for compIdx in range(len(allComps)):
            if compIdx != 0:
                lines.append('')
            lines.append('_comp = {}.o({})'.format(allCompsVarName, compIdx))
            procName = procNames[compIdx]
            compName = allComps[compIdx].name
            lines.append('{}(_comp)    // "{}"'.format(procName, compName))
            
        # !! BUG: we don't export GLOBAL-s
        
        return lines
        