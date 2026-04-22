
from neuron import h

from Utils.OtherUtils import *


class MetaGensForTaps:
    
    _gapJuncOrSynMarker = '{gapJuncOrSyn}'
    _isGapJuncOrSynMarker = '{isGapJuncOrSyn}'
    _tapSetIdx1BasedMarker = '{tapSetIdx1Based}'
    _tapSetIdx0BasedMarker = '{tapSetIdx0Based}'
    _slashesMarker = '{slashes}'
    
    
    @classmethod
    def createAllGapJuncSets(cls):
        if h.exportOptions.isExportAnyGapJuncSets():
            return cls._metaUnwrapAllTapSets(1)
        else:
            return []
            
    @classmethod
    def createAllSynSets(cls):
        if h.exportOptions.isExportAnySynSets():
            return cls._metaUnwrapAllTapSets(0)
        else:
            return []
            
            
    @classmethod
    def _metaUnwrapAllTapSets(cls, isGapJuncOrSyn):
        
        newLines = []
        
        if isGapJuncOrSyn:
            gapJuncOrSynStr = 'GJ'
            xmAllTapSets = h.gjmAllGapJuncSets
        else:
            gapJuncOrSynStr = 'syn'
            xmAllTapSets = h.smAllSynSets
            
        inSkeletonFileRelPathName = '_Code\\Export\\OutHocFileStructures\\Skeletons\\MetaSkeletonForOneTapSetFromMainHocFile.txt'
        
        with open(inSkeletonFileRelPathName, 'r') as inFile:
            lines = inFile.readlines()      # !! Preserving all newline characters here
            
        isGapJuncOrSynStr = str(isGapJuncOrSyn)
        
        for lineIdx in range(len(lines)):
            lines[lineIdx] = lines[lineIdx] \
                .replace(cls._gapJuncOrSynMarker, gapJuncOrSynStr) \
                .replace(cls._isGapJuncOrSynMarker, isGapJuncOrSynStr)
                
        baseNumSlashes = parHdrTotalLen + 1 + len(cls._slashesMarker)
        
        for tapSetIdx in range(len(xmAllTapSets)):
            for line in lines:
                if isGapJuncOrSyn:
                    tapSetIdx1Based = tapSetIdx + 1
                else:
                    tapSetIdx1Based = int(h.smAllSynSets[tapSetIdx].idxForSynSet)
                newLine = line.replace(cls._tapSetIdx1BasedMarker, str(tapSetIdx1Based))
                numSlashes = baseNumSlashes - len(newLine)
                newLine = newLine.replace(cls._slashesMarker, '/' * numSlashes) \
                    .replace(cls._tapSetIdx0BasedMarker, str(tapSetIdx))
                newLines.append(newLine)
                
        return newLines
        