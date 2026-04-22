
from neuron import h

from Utils.OtherUtils import *


class GensForInhomAndStochModels:
    
    def createInhomBiophysModels(self):
        if not h.exportOptions.isExportAnyInhomBiophysModels():
            return emptyParagraphHint()
            
        selector = lambda actSpecVar : h.exportOptions.isExportedInhomBiophysVar(actSpecVar)
        lines = self._createAllInhomModels(selector)
        
        if lines:
            lines.append('')
            lines.append('{ inhomAndStochLibrary.applyAllBiophysInhomModels() }')
            
        return lines
        
    def createInhomGapJuncModels(self, gapJuncSetIdx):
        if not h.exportOptions.isExportAnyInhomGapJuncModels(gapJuncSetIdx):
            return emptyParagraphHint()
            
        selector = lambda actSpecVar : h.exportOptions.isExportedInhomGapJuncVar(actSpecVar, gapJuncSetIdx)
        lines = self._createAllInhomModels(selector)
        
        if lines:
            lines.append('')
            lines.append('{{ inhomAndStochLibrary.applyAllInhomModelsInTheTapSet(1, {}) }}'.format(gapJuncSetIdx))
            
        return lines
        
    def createInhomSynModels(self, synSetIdx):
        if not h.exportOptions.isExportAnyInhomSynModels(synSetIdx):
            return emptyParagraphHint()
            
        selector = lambda actSpecVar : h.exportOptions.isExportedInhomSynVar(actSpecVar, synSetIdx)
        lines = self._createAllInhomModels(selector)
        
        if lines:
            lines.append('')
            lines.append('{{ inhomAndStochLibrary.applyAllInhomModelsInTheTapSet(0, {}) }}'.format(synSetIdx))
            
        return lines
        
    def createStochBiophysModels(self):
        if not h.exportOptions.isExportAnyStochBiophysModels():
            return emptyParagraphHint()
            
        selector = lambda actSpecVar : h.exportOptions.isExportedStochBiophysVar(actSpecVar)
        lines = self._createAllStochModels(selector)
        
        return lines
        
    def createStochGapJuncModels(self, gapJuncSetIdx):
        if not h.exportOptions.isExportAnyStochGapJuncModels(gapJuncSetIdx):
            return emptyParagraphHint()
            
        selector = lambda actSpecVar : h.exportOptions.isExportedStochGapJuncVar(actSpecVar, gapJuncSetIdx)
        lines = self._createAllStochModels(selector)
        
        return lines
        
    def createStochSynModels(self, synSetIdx):
        if not h.exportOptions.isExportAnyStochSynModels(synSetIdx):
            return emptyParagraphHint()
            
        selector = lambda actSpecVar : h.exportOptions.isExportedStochSynVar(actSpecVar, synSetIdx)
        lines = self._createAllStochModels(selector)
        
        return lines
        
        
    def _createAllInhomModels(self, selector):
        lines = []
        
        for actSpecVar in h.inhomAndStochLibrary.activeSpecVars:
            if not selector(actSpecVar):
                continue
                
            if lines:
                lines.append('')
                
            distFuncHelper = actSpecVar.distFuncHelper
            segmentationHelper = actSpecVar.segmentationHelper
            
            if segmentationHelper is not None:
                lines.append('_segmentationHelper = new ReducedSegmentationHelper()')
                lines.append('_segmentationHelper.segmentationMode = {}'.format(int(segmentationHelper.segmentationMode)))
                lines.append('_segmentationHelper.total_nseg = {}'.format(int(segmentationHelper.total_nseg)))
                lines.append('_segmentationHelper.min_nseg = {}'.format(int(segmentationHelper.min_nseg)))
            else:
                lines.append('_segmentationHelper = nil')
                
            newLines = self._createAndInitOneDistOrStochFuncHelper(distFuncHelper, '_distFuncHelper')
            lines.extend(newLines)
            
            lines.append('{{ inhomAndStochLibrary.onInhomCreate({}, _segmentationHelper, _distFuncHelper, {}, {}) }}'.format( \
                self._createVarLibIdCtorCall(actSpecVar.varLibId), \
                int(actSpecVar.distFuncCatIdx), \
                int(actSpecVar.distFuncIdx)))
                
        return lines
        
    def _createAllStochModels(self, selector):
        lines = []
        
        for actSpecVar in h.inhomAndStochLibrary.activeSpecVars:
            if not selector(actSpecVar):
                continue
                
            if lines:
                lines.append('')
                
            boundingHelper = actSpecVar.boundingHelper
            colourizationHelper = boundingHelper.colourizationHelper
            stochFuncHelper = actSpecVar.stochFuncHelper
            
            lines.append('_colourizationHelper = new ColourizationHelper()')
            lines.append('_colourizationHelper.chromaticity = {}'.format(int(colourizationHelper.chromaticity)))
            lines.append('_colourizationHelper.colour = {}'.format(int(colourizationHelper.colour)))
            lines.append('_colourizationHelper.alpha = {}'.format(colourizationHelper.alpha))
            lines.append('{ _colourizationHelper.consumeSettings() }')
            
            lines.append('_boundingHelper = new BoundingHelper(_colourizationHelper)')
            lines.append('_boundingHelper.where = {}'.format(int(boundingHelper.where)))
            lines.append('_boundingHelper.mode = {}'.format(int(boundingHelper.mode)))
            lines.append('_boundingHelper.min = {}'.format(boundingHelper.min))
            lines.append('_boundingHelper.max = {}'.format(boundingHelper.max))
            
            newLines = self._createAndInitOneDistOrStochFuncHelper(stochFuncHelper, '_stochFuncHelper')
            lines.extend(newLines)
            
            lines.append('{{ inhomAndStochLibrary.onStochApply({}, _boundingHelper, _stochFuncHelper, {}, {}) }}'.format( \
                self._createVarLibIdCtorCall(actSpecVar.varLibId), \
                int(actSpecVar.stochFuncCatIdx), \
                int(actSpecVar.stochFuncIdx)))
                
        return lines
        
    def _createAndInitOneDistOrStochFuncHelper(self, distOrStochFuncHelper, varName):
        lines = []
        
        templName = getTemplOrClassName(distOrStochFuncHelper)
        lines.append('{} = new {}()'.format(varName, templName))
        lines.append('_vecOfVals = new Vector()')
        vecOfVals = h.Vector()
        listOfStrs = h.List()
        distOrStochFuncHelper.exportParams(vecOfVals, listOfStrs)
        for value in vecOfVals:
            lines.append('{{ _vecOfVals.append({}) }}'.format(value))   # Max. precision is applied here automatically
        lines.append('_listOfStrs = new List()')
        for thisStr in listOfStrs:
            thisStr = thisStr.s.replace('\n', '\\n')    # Needed for TablePlusLinInterp*FuncHelper 
            lines.append('{{ _listOfStrs.append(new String("{}")) }}'.format(thisStr))
        lines.append('{{ {}.importParams(_vecOfVals, _listOfStrs) }}'.format(varName))
        
        return lines
        
    def _createVarLibIdCtorCall(self, varLibId):
        
        # We hardcode names rather than indices for mechs and vars in the exported HOC file to be less dependant on the DLL file.
        # (User may want to add/modify/delete MOD files and replace the original DLL usually resulting in shifted mechIdx and varIdx.
        #  These shifts would make the old exported HOC file out of sync with the new DLL file.
        #  But we rely on mechName and varName and so the HOC file exported once is tolerant to DLL replacement in the future.)
        
        mechName = h.ref('')
        h.mth.getMechName(varLibId.enumDmPpFk, varLibId.mechIdx, mechName)
        mechName = mechName[0]
        
        if not (varLibId.enumDmPpFk == 2 and varLibId.isGapJuncOrSyn and varLibId.mechIdx == h.utils4FakeMech4GapJuncExtValue.mechIdx):
            varName = h.ref('')
            h.mth.getVarNameAndArraySize(varLibId.enumDmPpFk, varLibId.mechIdx, varLibId.varType, varLibId.varIdx, varName)
            varNameOrIdx = '"' + varName[0] + '"'
        else:
            # Gap junc ext value has dynamic varName, so we'll use varIdx instead
            varNameOrIdx = int(varLibId.varIdx)
            
        return 'new VarLibId({}, {}, {}, {}, "{}", {}, {}, {})'.format( \
            int(varLibId.enumDmPpFk), \
            int(varLibId.isGapJuncOrSyn), \
            int(varLibId.tapSetIdx), \
            int(varLibId.compIdx), \
            mechName, \
            int(varLibId.varType), \
            varNameOrIdx, \
            int(varLibId.arrayIndex))
            