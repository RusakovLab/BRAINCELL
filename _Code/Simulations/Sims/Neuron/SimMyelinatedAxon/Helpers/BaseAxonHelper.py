
# !! don't forget to update "consumeImportedAxonOrAxonDrawnByHand" and "deleteBaseTrunkAndConnectTerminalsToModifiedTrunk":
#       1. validate the axon; our expectation:
#           * at least 1 section, at least 2 points
#           * only one root
#           * the bifurcation doesn't start immediately
#           * axon_ref doesn't contain any secs being parents for other comps (e.g. dendrite_ref)
#       2. there is a room for improvement in the fork structure extraction algorithm (see the comment in ProtoFork._tryToExtractProtoTrunkAndTerminals)
#       3. instead of hardcoding "soma" and "somaConnectionPoint", find the actual parent segment for the axon root
#       4. fix the BUG that the callers are not ready for axon with some side branches appearing before the bifurcation

from neuron import h

from Helpers.ProtoGeomStructs import ProtoFork


class BaseAxonHelper:
    
    _def_L_axon = 1000.0    # (um) for predefined only
    _def_diam_axon = 2.0    # (um) for predefined and drawnByHand (trunk and terminals)
    _def_nseg_axon = 100    #      for imported, predefined and drawnByHand
    
    # Data members added in the ctor:
    #   _paramsHelper, _axonBiophysCompsHelper
    
    # Data members added in "consumeImportedAxonOrAxonDrawnByHand":
    #   soma, somaConnectionPoint   !! maybe just keep one argument here: soma segment
    #   _impAxonProtoFork, _dbhAxonProtoFork
    
    # Data members added in "switchToImportedAxonOrAxonDrawnByHand" and "switchToPredefGeometryAxon":
    #   axon, axonTerminalSecsList
    
    
    def __init__(self, paramsHelper, axonBiophysCompsHelper):
        self._paramsHelper = paramsHelper
        self._axonBiophysCompsHelper = axonBiophysCompsHelper
        
    def consumeImportedAxonOrAxonDrawnByHand(self, isImportedOrDrawnByHand):
        
        # !! just a temp stub: rewrite this to use the actual parent section and the actual connection point (where the imported "axon" was connected)
        self.soma = h.soma_ref[0].sec
        self.somaConnectionPoint = 0.5
        
        
        isInvalid = self._validateImportedAxonOrAxonDrawnByHand()   # !! maybe move to ProtoFork ctor
        if isInvalid:
            return True
            
        # !! assigning default "nseg" looks reasonable not only for the axon drawn by hand (where each section has only 1 segment),
        #    but also for the imported axon where "nseg" might be either too low or too high
        # !! for the axon drawn by hand, would it make sense to propagate "nseg" from CellBuild-er to our "Axon params" panel?
        protoFork = ProtoFork(h.axon_ref, self._def_nseg_axon)
        
        if protoFork.trunk.isInhomDiam():
            if isImportedOrDrawnByHand:
                what = 'imported axon'
            else:
                what = 'axon drawn by hand'
            # !! we can provide support for inhom "diam" in the future
            h.mwh.showWarningBox(f'The {what} has "diam" varying along the distance.', 'We\'ll have to make it const to use in this simulation.')
            
        # !! would it make sense to warn about merging all axon sects into one and changing "nseg"?
        
        if isImportedOrDrawnByHand:
            self._impAxonProtoFork = protoFork
        else:
            self._dbhAxonProtoFork = protoFork
            
        for sec_ref in reversed(h.axon_ref):
            h.delete_section(sec=sec_ref.sec)
            
        if isImportedOrDrawnByHand:
            self._axonBiophysCompsHelper.onAxonDeleted()
        else:
            # We've called it before showing the CellBuildHelper
            pass
            
        return False
        
    def onSomaOverwritten(self, soma):
        self.soma = soma
        
    def switchToImportedAxonOrAxonDrawnByHand(self, isImportedOrDrawnByHand):
        
        axon = self._switchCommonPrologue()
        
        if isImportedOrDrawnByHand:
            protoFork = self._impAxonProtoFork
        else:
            protoFork = self._dbhAxonProtoFork
            
        protoFork.trunk.copyPointsFromListToSecAndAssignNseg(axon)
        
        # Syncing with "Axon params" panel and making axon diam homogeneous
        if isImportedOrDrawnByHand:
            axon.diam = axon(0.5).diam      # !! maybe calculate the average by all segments here
            self._paramsHelper.diam_axon = axon.diam
        else:
            axon.diam = self._def_diam_axon
        self._paramsHelper.L_axon = axon.L
        
        self.axon = axon
        
        axonTerminalSecsList = []
        for i, protoTerminal in enumerate(protoFork.terminals):
            terminal = self._createAndConnectOneTerminalBranch(i, axon)
            protoTerminal.copyPointsFromListToSecAndAssignNseg(terminal)
            if not isImportedOrDrawnByHand:
                terminal.diam = self._def_diam_axon
            axonTerminalSecsList.append(terminal)
            
        self.axonTerminalSecsList = axonTerminalSecsList
        
        self._switchCommonEpilogue()
        
    def switchToPredefGeometryAxon(self):
        
        L_axon    = self._def_L_axon
        diam_axon = self._def_diam_axon
        nseg_axon = self._def_nseg_axon
        
        axon = self._switchCommonPrologue()
        
        axon.pt3dclear()
        axon.pt3dadd(-1, -1.67, 0.12, diam_axon)
        axon.pt3dadd(-0.67, -1.34, 0.12, diam_axon)
        axon.pt3dadd(-0.67, -0.67, 0.12, diam_axon)
        axon.pt3dadd(-0.33, 0, 0.12, diam_axon)
        axon.pt3dadd(0, 0.33, 0.12, diam_axon)
        axon.pt3dadd(0.33, 1, 0.12, diam_axon)
        axon.pt3dadd(0.67, 1.34, 0.12, diam_axon)
        axon.pt3dadd(1,2, 0.12, diam_axon)
        axon.pt3dadd(2, 2.5, 0.22, diam_axon)
        
        axon.L    = L_axon
        axon.nseg = nseg_axon
        
        def _createAndConnectOneTerminalBranchForPredefGeometryAxon(i):
            terminal = self._createAndConnectOneTerminalBranch(i, axon)
            terminal.L = L_axon / 10.0
            terminal.diam = diam_axon
            return terminal
            
        terminal0 = _createAndConnectOneTerminalBranchForPredefGeometryAxon(0)
        terminal1 = _createAndConnectOneTerminalBranchForPredefGeometryAxon(1)
        terminal2 = _createAndConnectOneTerminalBranchForPredefGeometryAxon(2)
        
        self.axon = axon
        self.axonTerminalSecsList = [terminal0, terminal1, terminal2]
        
        self._switchCommonEpilogue()
        
    def deleteBaseTrunkAndConnectTerminalsToModifiedTrunk(self, axonLastSec):
        
        self.deleteAxon(True)
        
        # !! just a temp stub
        for axonTerminal in self.axonTerminalSecsList:
            axonTerminal.connect(axonLastSec, 1)
            
    def deleteAxon(self, isKeepTerminals=False):
        
        if not isKeepTerminals:
            self.axonTerminalSecsList = None
            
        self.axon = None
        
        self._axonBiophysCompsHelper.onAxonDeleted()
        
        
    def _validateImportedAxonOrAxonDrawnByHand(self):
        
        # !! just a temp stub
        return False
        
    def _switchCommonPrologue(self):
        
        self.deleteAxon()
        
        axon = h.Section(name='axon')
        
        axon.connect(self.soma, self.somaConnectionPoint)
        
        return axon
        
    def _createAndConnectOneTerminalBranch(self, i, axon):
        terminal = h.Section(name='terminal[%i]' % i)
        terminal.connect(axon, 1.0)
        return terminal
        
    def _switchCommonEpilogue(self):
        
        self._axonBiophysCompsHelper.onBaseAxonCreated()
        