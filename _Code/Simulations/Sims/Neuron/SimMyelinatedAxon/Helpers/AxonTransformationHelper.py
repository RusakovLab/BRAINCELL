# The base axon, before we start modifying it in AxonTransformationHelper, must have a single section up to the bifurcation
# (and BaseAxonHelper produces such an axon upstream)

from neuron import h

from OtherInterModularUtils import codeContractViolation


class AxonArcInterval:
    def __init__(self, start, end, secName):
        if start < 0 or end > 1 or start >= end:
            codeContractViolation()
        self.start = start
        self.end = end
        self.secName = secName
        
    @property
    def secCategory(self):
        """Extract the category name from the section name (e.g. 'axonUnderSchwann[0]' -> 'axonUnderSchwann')."""
        return self.secName.split('[')[0]
        
class Axon3DPointWithArc:
    __slots__ = ('x', 'y', 'z', 'arc')
    
    def __init__(self, x, y, z, arc):
        self.x = x
        self.y = y
        self.z = z
        self.arc = arc
        
class AxonTransformationHelper:
    
    _AISPsSecLenAndDiam = 40.0      # um
    _AISDsSecLenAndDiam = 30.0      # um
    _insulatorSecLenAndDiam = 1e-9  # um
    _insulatorSecNseg = 1
    
    def __init__(self, params, baseAxonSecContainer, myelRegionHelper):
        self._params = params
        self._bac = baseAxonSecContainer
        self._myelRegionHelper = myelRegionHelper
        
    def createModifiedGeometryAxon(self, isDeployOrScalpMyelSheath):
        
        # !! why "-s" in names? maybe make them multi-section?
        
        AISPs = h.Section(name='AISPs')
        AISPs.L = AISPs.diam = self._AISPsSecLenAndDiam
        # !! would it make sense to postpone this until the base axon is deleted?
        AISPs.connect(self._bac.soma, self._bac.somaConnectionPoint)
        
        AISDs = h.Section(name='AISDs')
        AISDs.L = AISDs.diam = self._AISDsSecLenAndDiam
        AISDs.connect(AISPs, 1)
        
        # Split the base axon section into smaller sections
        myelArcInts = self._myelRegionHelper.getAllMyelArcIntervals()
        axonArcInts = self._getAllAxonArcIntervals(myelArcInts)
        axon3dPtsWithArcs = self._getAllAxon3dPtsWithArcs()
        (axonBeforeFirstSchwannSecOrNone,
         axonUnderSchwannSecsList,
         axonNodeOfRanvierSecsList,
         axonAfterLastSchwannSecOrNone) = self._splitBaseAxonSectionAndConnect(axon3dPtsWithArcs, axonArcInts, AISDs)
        
        if len(axonUnderSchwannSecsList) != len(axonNodeOfRanvierSecsList) + 1:
            codeContractViolation()
            
        # Create Schwann cells and prepare a dict to map "axon under Schwann" sects to Schwann sects
        insulatorSecsList = []
        schwannSecsList = []
        axonUnderSchwannSecToSchwannSecDict = {}
        if isDeployOrScalpMyelSheath:
            for secIdx, axonUnderSchwannSec in enumerate(axonUnderSchwannSecsList):
                if secIdx == 0:
                    parentSec = axonBeforeFirstSchwannSecOrNone if axonBeforeFirstSchwannSecOrNone else AISDs
                else:
                    parentSec = axonNodeOfRanvierSecsList[secIdx - 1]
                insulator, schwann = self._createSchwannSectionFromAxonUnderSchwannSection(axonUnderSchwannSec, secIdx, parentSec)
                insulatorSecsList.append(insulator)
                schwannSecsList.append(schwann)
                axonUnderSchwannSecToSchwannSecDict[axonUnderSchwannSec] = schwann
                
        return (AISPs, AISDs,
                axonBeforeFirstSchwannSecOrNone,
                axonUnderSchwannSecsList,
                axonNodeOfRanvierSecsList,
                axonAfterLastSchwannSecOrNone,
                insulatorSecsList,
                schwannSecsList,
                axonUnderSchwannSecToSchwannSecDict)
            
            
    # !! keep in sync with _splitBaseAxonSectionAndConnect
    def _getAllAxonArcIntervals(self, myelArcInts):
        
        axonArcInts = []
        
        # WARNING: be careful renaming the sections because we use the category names in _splitBaseAxonSectionAndConnect
        
        start = myelArcInts[0].start
        if start > 0:
            axonArcInts.append(    AxonArcInterval(0,                   start,         'axonBeforeFirstSchwann'))
            
        for scwIdx, myelInt in enumerate(myelArcInts):
            
            if scwIdx != 0:
                norIdx = scwIdx - 1
                axonArcInts.append(AxonArcInterval(axonArcInts[-1].end, myelInt.start, 'axonNodeOfRanvier[%i]' % norIdx))
                
            axonArcInts.append(    AxonArcInterval(myelInt.start,       myelInt.end,   'axonUnderSchwann[%i]' % scwIdx))
            
        end = myelArcInts[-1].end
        if end < 1:
            axonArcInts.append(    AxonArcInterval(end,                 1,             'axonAfterLastSchwann'))
            
        return axonArcInts
        
    def _getAllAxon3dPtsWithArcs(self):
        
        axon = self._bac.axon
        L = axon.L
        
        allPoints = [
            Axon3DPointWithArc(axon.x3d(i), axon.y3d(i), axon.z3d(i), axon.arc3d(i) / L)
            for i in range(axon.n3d())
        ]
            
        if allPoints[0].arc != 0 or allPoints[-1].arc != 1:
            codeContractViolation()
            
        return allPoints
        
    def _splitBaseAxonSectionAndConnect(self, axon3dPtsWithArcs, axonArcInts, parentSec):
        
        # Dictionary dispatch replaces fragile eval()-based reflection
        # !! keep in sync with _getAllAxonArcIntervals
        secsLists = {
            'axonBeforeFirstSchwann': [],
            'axonUnderSchwann':       [],
            'axonNodeOfRanvier':      [],
            'axonAfterLastSchwann':   [],
        }
        
        xVec = h.Vector(pt.x for pt in axon3dPtsWithArcs)
        yVec = h.Vector(pt.y for pt in axon3dPtsWithArcs)
        zVec = h.Vector(pt.z for pt in axon3dPtsWithArcs)
        arcVec = h.Vector(pt.arc for pt in axon3dPtsWithArcs)
        
        axon = self._bac.axon
        
        for axonArcInt in axonArcInts:
            
            sec = h.Section(name=axonArcInt.secName)
            
            sec.connect(parentSec, 1)
            
            sec.pt3dclear()
            
            self._addInterpolated3dPoint(sec, axonArcInt.start, xVec, yVec, zVec, arcVec)
            
            self._copy3dPointsBetweenArcs(sec, axonArcInt.start, axonArcInt.end, xVec, yVec, zVec, arcVec)
            
            self._addInterpolated3dPoint(sec, axonArcInt.end, xVec, yVec, zVec, arcVec)
            
            sec.diam = axon.diam
            
            nseg = int(round((axonArcInt.end - axonArcInt.start) * axon.nseg))
            sec.nseg = max(1, nseg)
            
            secsLists[axonArcInt.secCategory].append(sec)
            
            parentSec = sec
            
        bfs = secsLists['axonBeforeFirstSchwann']
        als = secsLists['axonAfterLastSchwann']
        
        return (
            bfs[0] if bfs else None,
            secsLists['axonUnderSchwann'],
            secsLists['axonNodeOfRanvier'],
            als[0] if als else None,
        )
        
    def _createSchwannSectionFromAxonUnderSchwannSection(self, axonUnderSchwannSec, secIdx, parentSec):
        schwannSec = h.Section(name='schwann[%i]' % secIdx)
        
        # !! just a workaround so we know "distance" along the Schwann cell
        #    (remove this when we don't use the "sine by x" current and don't create RangeVarPlot-s for the Schwann cells)
        insulatorSec = h.Section(name='insulator[%i]' % secIdx)
        insulatorSec.connect(parentSec, 1)
        insulatorSec.L = insulatorSec.diam = self._insulatorSecLenAndDiam
        insulatorSec.nseg = self._insulatorSecNseg
        schwannSec.connect(insulatorSec, 1)
        
        schwannSec.pt3dclear()
        
        diam_sheath = self._params.diam_sheath
        for ptIdx in range(axonUnderSchwannSec.n3d()):
            schwannSec.pt3dadd(axonUnderSchwannSec.x3d(ptIdx), axonUnderSchwannSec.y3d(ptIdx), axonUnderSchwannSec.z3d(ptIdx), diam_sheath)
            
        schwannSec.nseg = axonUnderSchwannSec.nseg
        
        return insulatorSec, schwannSec
        
    # !! ideally, don't call it twice for each middle edge point
    def _addInterpolated3dPoint(self, sec, to_arc, from_xVec, from_yVec, from_zVec, from_arcVec):
        
        to_arcVec = h.createVecOfVals(to_arc)
        
        to_xVec = h.Vector(1)
        to_yVec = h.Vector(1)
        to_zVec = h.Vector(1)
        
        to_xVec.interpolate(to_arcVec, from_arcVec, from_xVec)
        to_yVec.interpolate(to_arcVec, from_arcVec, from_yVec)
        to_zVec.interpolate(to_arcVec, from_arcVec, from_zVec)
        
        diam = self._bac.axon.diam
        sec.pt3dadd(to_xVec[0], to_yVec[0], to_zVec[0], diam)
        
    def _copy3dPointsBetweenArcs(self, sec, startArc, endArc, from_xVec, from_yVec, from_zVec, from_arcVec):
        diam = self._bac.axon.diam
        for x, y, z, arc in zip(from_xVec, from_yVec, from_zVec, from_arcVec):
            if startArc < arc < endArc:
                sec.pt3dadd(x, y, z, diam)
