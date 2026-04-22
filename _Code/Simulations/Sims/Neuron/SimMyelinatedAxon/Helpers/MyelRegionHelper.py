
from enum import IntEnum

from sortedcontainers import SortedSet

from neuron import h

from OtherInterModularUtils import codeContractViolation


class EnumMyelRegion(IntEnum):
    entireAxon = 0
    zebra = 1
    drawnByHand = 2
    
# Used independently for _segmIdxInts and arcInts
class Interval:
    def __init__(self, start, end):
        if start > end:
            codeContractViolation()
        self.start = start
        self.end = end
        
    def extend(self, value):
        self.start = min(self.start, value)
        self.end = max(self.end, value)
        
class MyelRegionHelper:
    
    enumMyelRegion = EnumMyelRegion.zebra
    
    _baseMarkerColour = h.enumColours.blue
    
    # Data members added in ctor:
    #   _params, _bac
    #   _segmIdxsSortedSet, _ppms
    
    # Data member added in "onMousePressOrDragging":
    #   _segmIdxInts
    
    def __init__(self, params, baseAxonSecContainer):
        self._params = params
        self._bac = baseAxonSecContainer
        
        self._segmIdxsSortedSet = SortedSet()
        self._ppms = []
        
    def onMousePressOrDragging(self, shape, arc):
        
        if self.enumMyelRegion != EnumMyelRegion.drawnByHand:
            codeContractViolation()
            
        if arc == 0 or arc == 1:
            return
            
        segmIdx = self._arcToSegmIdx(arc)
        
        if segmIdx not in self._segmIdxsSortedSet:
            self._createOnePPMAndAddSegmIdxToSet(shape, arc, segmIdx)
            
        if hasattr(self, '_segmIdxInts'):
            self._segmIdxInts.extend(segmIdx)
        else:
            self._segmIdxInts = Interval(segmIdx, segmIdx)
            
    def onMouseRelease(self, shape):
        
        if self.enumMyelRegion != EnumMyelRegion.drawnByHand:
            codeContractViolation()
            
        if not hasattr(self, '_segmIdxInts'):
            return
            
        for segmIdx in range(self._segmIdxInts.start, self._segmIdxInts.end + 1):
            if segmIdx in self._segmIdxsSortedSet:
                continue
            arc = self._segmIdxToArc(segmIdx)
            self._createOnePPMAndAddSegmIdxToSet(shape, arc, segmIdx)
            
        del self._segmIdxInts
        
    def validate(self):
        isCancel = len(self._segmIdxsSortedSet) == 0
        if isCancel:
            h.mwh.showWarningBox('Please draw some myelin on the axon.')
        return isCancel
        
    def getAllMyelArcIntervals(self):
        
        if self.enumMyelRegion == EnumMyelRegion.entireAxon:
            
            return [Interval(0, 1)]
            
        elif self.enumMyelRegion == EnumMyelRegion.zebra:
            
            arcInts = []
            
            schwann_start = self._params.schwann1_start
            schwann_end   = self._params.schwann1_end
            schwann2_start = self._params.schwann2_start
            period = schwann2_start - schwann_start
            
            if schwann_start == 1:
                codeContractViolation()
                
            for _ in range(int(self._params.maxNumSchwannCells)):
                
                arcInts.append(Interval(schwann_start, schwann_end))
                
                schwann_start += period
                schwann_end   += period
                
                if schwann_start >= 1:
                    break
                    
                schwann_end = min(schwann_end, 1)
                
            return arcInts
            
        elif self.enumMyelRegion == EnumMyelRegion.drawnByHand:
            
            if not self._segmIdxsSortedSet:
                codeContractViolation()
                
            arcInts = []
            
            # Extract continuous segment sequences (intervals) from self._segmIdxsSortedSet
            
            seqStartSegmIdx = seqEndSegmIdx = self._segmIdxsSortedSet[0]
            
            for segmIdx in self._segmIdxsSortedSet[1:]:
                if segmIdx == seqEndSegmIdx + 1:
                    # Continue the sequence
                    seqEndSegmIdx = segmIdx
                else:
                    # Close the sequence
                    self._closeSegmSequence(arcInts, seqStartSegmIdx, seqEndSegmIdx)
                    
                    # Start a new sequence
                    seqStartSegmIdx = seqEndSegmIdx = segmIdx
                    
            # Close the last sequence
            self._closeSegmSequence(arcInts, seqStartSegmIdx, seqEndSegmIdx)
            
            if not arcInts:
                codeContractViolation()
                
            return arcInts
            
        else:
            
            codeContractViolation()
            
    def showMyelinMarkers(self, shape):
        
        self.destroyPPMs()
        
        axon = self._bac.axon
        if axon is None:
            # We just entered the "Draw by hand" mode for axon
            return
            
        if self.enumMyelRegion == EnumMyelRegion.entireAxon:
            
            for segm in axon:
                self._createOnePPM(shape, segm=segm)
                
        elif self.enumMyelRegion == EnumMyelRegion.zebra:
            
            params = self._params
            
            isCancel = params.validateSchwannForZebra()
            if isCancel:
                return
                
            dx = 1 / axon.nseg
            x = dx / 2
            y = x - params.schwann1_start
            period = params.schwann2_start - params.schwann1_start
            end1 = params.schwann1_end - params.schwann1_start
            
            for segm in axon:
                if y >= 0:
                    schwannCellIdx = int(y / period)
                    if schwannCellIdx >= params.maxNumSchwannCells:
                        break
                    if y % period <= end1:
                        colour = h.enumColours.makeSureNotWhite2(self._baseMarkerColour + schwannCellIdx)
                        self._createOnePPM(shape, segm=segm, colour=colour)
                y += dx
                
        elif self.enumMyelRegion == EnumMyelRegion.drawnByHand:
            
            segmIdx = 0
            for segm in axon:
                if segmIdx in self._segmIdxsSortedSet:
                    self._createOnePPM(shape, segm=segm)
                segmIdx += 1
                
        else:
            
            codeContractViolation()
            
    def destroyPPMs(self):
        
        self._ppms.clear()
        
    def forget(self):
        
        self.destroyPPMs()
        
        self._segmIdxsSortedSet.clear()
        
    # All next staff is private
    
    
    def _createOnePPMAndAddSegmIdxToSet(self, shape, arc, segmIdx):
        self._createOnePPM(shape, arc=arc)
        self._segmIdxsSortedSet.add(segmIdx)
        
    # !! code dup. with hoc:SimVoltageCA1Neuron.createOnePPM
    def _createOnePPM(self, shape, segm=None, arc=None, colour=_baseMarkerColour):
        if segm is not None:
            ppm = h.PointProcessMark(segm)
        else:
            ppm = h.PointProcessMark(arc, sec=self._bac.axon)
            
        shape.point_mark(ppm, colour)
        
        # Without the next command, the marker won't be shown correctly after "3D Rotate"
        self._ppms.append(ppm)
        
    def _closeSegmSequence(self, arcInts, seqStartSegmIdx, seqEndSegmIdx):
        startArc = self._segmIdxToArc(seqStartSegmIdx - 0.5)
        endArc = self._segmIdxToArc(seqEndSegmIdx + 0.5)
        arcInts.append(Interval(startArc, endArc))
        
    def _arcToSegmIdx(self, arc):
        return int(round(arc * self._bac.axon.nseg - 0.5))
        
    def _segmIdxToArc(self, segmIdx):
        return (0.5 + segmIdx) / self._bac.axon.nseg
        