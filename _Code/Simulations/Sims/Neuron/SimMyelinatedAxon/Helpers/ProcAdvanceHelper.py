
from OtherInterModularUtils import codeContractViolation


# Our appendix to NEURON RxD that does three things on each iteration (Configuration B):
#
#   * applies the Dirichlet boundary condition "conc = ko0" at R_max
#     for the outermost shells of NON-MYELINATED axon sections (nodes of Ranvier, before/after Schwann, etc.)
#
#   * crops the concentration below "self._veryMinOuterConc" to prevent negative values (which tend to bring NaN-s into simulation)
#
#   * copies the concentration from the SHEATH-BOUNDARY shells (at R_sheath, not R_max)
#     of "axonUnderSchwann" sections to "schwann.ko"
#
# Configuration B boundary conditions at R_max:
#   - Myelin zone:  zero flux (dK/dr = 0)  -- no explicit action needed, RxD default is zero flux
#   - Node zone:    fixed concentration     -- Dirichlet [K] = ko0

class ProcAdvanceHelper:
    
    # Data members added in the ctor:
    #   _nodeOfRanvierOuterNodesList  -- outermost nodes (at Rmax) of non-myelinated sections: Dirichlet BC
    #   _ko0
    #   _schwannSegmNodePairs         -- pre-computed (segment, node) pairs for copying conc to schwann.ko
    #   _allNodes
    #   _veryMinOuterConc
    
    def __init__(self, nodeOfRanvierOuterNodesList, ko0, schwannSecsList, schwannSheathNodesList, allNodes, veryMinOuterConc):
        
        self._nodeOfRanvierOuterNodesList = nodeOfRanvierOuterNodesList
        self._ko0 = ko0
        
        # Pre-compute (segment, node) pairs for Schwann ko copying
        # In Config B, we read concentration from the sheath-boundary nodes (at R_sheath),
        # not from the outermost nodes (at R_max), because the Schwann cell physically sits at R_sheath
        numSegms = sum(sec_sch.nseg for sec_sch in schwannSecsList)
        numNodes = len(schwannSheathNodesList)
        if numSegms != numNodes:
            codeContractViolation()
            
        self._schwannSegmNodePairs = []
        nodeIdx = 0
        for sec_sch in schwannSecsList:
            for segm_sch in sec_sch:
                self._schwannSegmNodePairs.append((segm_sch, schwannSheathNodesList[nodeIdx]))
                nodeIdx += 1
        
        self._allNodes = allNodes
        self._veryMinOuterConc = veryMinOuterConc
        
    # !! think about improving performance for this method, especially for the cycle by self._allNodes:
    #    we can do it in parallel (with @njit and prange) or
    #    maybe we can loop just by the boundary shells (which include the flux) 
    def onAdvance(self):
        
        ko0 = self._ko0
        veryMin = self._veryMinOuterConc
        
        # Applying the Dirichlet boundary condition "conc = ko0" at R_max
        # for the outermost shells of NON-MYELINATED axon sections
        # (For myelinated sections, zero-flux BC is the RxD default -- no action needed)
        # !! it's a workaround that we do this explicitly on each iteration
        #    (NEURON RxD doesn't support "ecs_boundary_conditions" arg in "rxd.Species" ctor for radial diffusion)
        for node_ax in self._nodeOfRanvierOuterNodesList:
            node_ax.concentration = ko0
            
        # Cropping the concentration below "veryMinOuterConc" to prevent negative values (which tend to bring NaN-s into simulation)
        for node in self._allNodes:
            conc = node.concentration
            if conc < veryMin:
                node.concentration = veryMin
                
        # Copying the concentration from the SHEATH-BOUNDARY shells to "schwann.ko"
        # In Config B, this reads from R_sheath (not R_max) because that's where the Schwann cell sits
        for segm_sch, node in self._schwannSegmNodePairs:
            segm_sch.ko = node.concentration
                
    def cleanup(self):
        
        self._nodeOfRanvierOuterNodesList = None
        self._schwannSegmNodePairs = None
        self._allNodes = None
