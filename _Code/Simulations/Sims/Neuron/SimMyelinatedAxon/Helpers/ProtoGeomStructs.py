
from dataclasses import dataclass

from neuron import h


@dataclass(frozen=True)
class _ProtoPoint:
    x: float
    y: float
    z: float
    diam: float
    
    
class ProtoSection:
    
    # Data members added in the ctor:
    #   _nseg, _listOf4dPts, _helperSetOf4dPts
    
    def __init__(self, nseg):
        self._nseg = nseg
        
        self._listOf4dPts = []
        self._helperSetOf4dPts = set()
        
    # !! designed for a thread-like axon structure spanning multiple sections
    def copyUniquePointsFromSecToList(self, sec):
        for ptIdx in range(sec.n3d()):
            pt = _ProtoPoint(sec.x3d(ptIdx), sec.y3d(ptIdx), sec.z3d(ptIdx), sec.diam3d(ptIdx))
            if pt not in self._helperSetOf4dPts:
                self._listOf4dPts.append(pt)
                self._helperSetOf4dPts.add(pt)
                
    def copyPointsFromListToSecAndAssignNseg(self, sec):
        sec.pt3dclear()
        for pt in self._listOf4dPts:
            sec.pt3dadd(pt.x, pt.y, pt.z, pt.diam)
            
        sec.nseg = self._nseg
        
    def isInhomDiam(self):
        firstPtDiam = self._listOf4dPts[0].diam
        return not all(pt.diam == firstPtDiam for pt in self._listOf4dPts[1 :])
        
        
class ProtoFork:
    
    # Data members added in the ctor:
    #   trunk, terminals
    
    def __init__(self, list_ref, _def_nseg_axon):
        
        # The main algorithm: trying to extract the fork structure
        tupleOrNone = self._tryToExtractProtoTrunkAndTerminals(list_ref, _def_nseg_axon)
        
        if tupleOrNone is not None:
            self.trunk, self.terminals = tupleOrNone
        else:
            # The fallback algorithm: merging all axon sections into one
            trunkLastSecIdx = len(list_ref) - 1
            self.trunk = self._extractProtoTrunk(list_ref, trunkLastSecIdx, _def_nseg_axon)
            self.terminals = []
            
            
    # out: (trunk, terminals) or None
    # !! quite a basic implementation with a room for improvement; we make a few assumptions:
    #   * the fork topology (i.e. no 2nd order branching; the bifurcation doesn't start immediately)
    #   * the trunk sections are sorted in the root-to-terminals order
    #   * the bifurcation doesn't start at "arc < 1"
    #   * for each sec in list_ref, there is no child secs outside list_ref
    def _tryToExtractProtoTrunkAndTerminals(self, list_ref, _def_nseg_axon):
        
        n = len(list_ref)
        
        # !! it would be better to leverage SectionList.wholetree here ensuring the order
        trunkLastSecIdx = n - 1
        for secIdx, sec_ref in enumerate(list_ref):
            if sec_ref.nchild() <= 1:
                continue
            if trunkLastSecIdx != n - 1:
                # 2nd order branching found
                return None
            trunkLastSecIdx = secIdx
            
        # "trunkLastSecIdx == n - 1" here means "no terminals"
        
        # Merging all axon trunk sections into one
        trunk = self._extractProtoTrunk(list_ref, trunkLastSecIdx, _def_nseg_axon)
        
        terminals = []
        trunkLastSec = list_ref[trunkLastSecIdx]
        for childSec in trunkLastSec.child:
            # Merging all subtree sections into one
            secList = h.SectionList()
            secList.subtree(childSec)
            nseg = 0
            for sec in secList:
                nseg += sec.nseg
            terminal = ProtoSection(nseg)
            for sec in secList:
                terminal.copyUniquePointsFromSecToList(sec)
            terminals.append(terminal)
            
        return trunk, terminals
        
    def _extractProtoTrunk(self, list_ref, trunkLastSecIdx, _def_nseg_axon):
        trunk = ProtoSection(_def_nseg_axon)
        for idx in range(trunkLastSecIdx + 1):
            sec = list_ref[idx].sec
            trunk.copyUniquePointsFromSecToList(sec)
        return trunk
        