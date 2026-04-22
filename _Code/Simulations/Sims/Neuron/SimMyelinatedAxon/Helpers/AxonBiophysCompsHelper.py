
import itertools

from neuron import h

from OtherInterModularUtils import convertPyIterableOfSecsToHocListOfSecRefs


class AxonBiophysCompsHelper:
    
    # Data members added in "setSecContainers":
    #   _bac, _mac
    
    def setSecContainers(self, baseAxonSecContainer, modifAxonSecContainer):
        self._bac = baseAxonSecContainer
        self._mac = modifAxonSecContainer
        
    def onAxonDeleted(self):
        
        h.axon_ref.remove_all()
        
        self._deleteAxonComps()
        
    def onBaseAxonCreated(self):
        
        self.onAxonDeleted()
        
        pyIter = itertools.chain([self._bac.axon], self._bac.axonTerminalSecsList)
        h.axon_ref = convertPyIterableOfSecsToHocListOfSecRefs(pyIter)
        
        self._createBaseAxonComps()
        
    def onModifGeomAxonCreated(self):
        
        self.onAxonDeleted()
        
        h.axon_ref = convertPyIterableOfSecsToHocListOfSecRefs(self._mac.axonTreeSecsWithTerms)
        
        self._createModifGeomAxonComps()
        
    def restoreStdAxonComp(self):
        
        self._deleteAxonComps()
        
        self._createComp('Axon', h.axon_ref)
        
        
    def _createBaseAxonComps(self):
        self._createSimSpecificComp(    'Before Bifurcation',   [self._bac.axon])
        if self._bac.axonTerminalSecsList:
            self._createSimSpecificComp('Terminals',             self._bac.axonTerminalSecsList)
            
    def _createModifGeomAxonComps(self):
        self._createSimSpecificComp(    'AISPs',                [self._mac.AISPs])
        self._createSimSpecificComp(    'AISDs',                [self._mac.AISDs])
        if self._mac.axonBeforeFirstSchwannSecOrNone:
            self._createSimSpecificComp('Before First Schwann', [self._mac.axonBeforeFirstSchwannSecOrNone])
        self._createSimSpecificComp(    'Under Schwann',         self._mac.axonUnderSchwannSecsList)
        if self._mac.axonNodeOfRanvierSecsList:
            self._createSimSpecificComp('Nodes of Ranvier',      self._mac.axonNodeOfRanvierSecsList)
        if self._mac.axonAfterLastSchwannSecOrNone:
            self._createSimSpecificComp('After Last Schwann',   [self._mac.axonAfterLastSchwannSecOrNone])
        if self._mac.insulatorSecsList:
            self._createSimSpecificComp('Insulators',            self._mac.insulatorSecsList)
        if self._mac.schwannSecsList:
            self._createSimSpecificComp('Schwann Cells',         self._mac.schwannSecsList)
        if self._bac.axonTerminalSecsList:
            self._createSimSpecificComp('Terminals',             self._bac.axonTerminalSecsList)
        
    def _createSimSpecificComp(self, name, secsList):
        
        compName = 'Axon \ ' + name
        list_ref = convertPyIterableOfSecsToHocListOfSecRefs(secsList)
        
        self._createComp(compName, list_ref)
        
    def _deleteAxonComps(self):
        
        # h.inhomAndStochLibrary.remove(!!)
        
        # !! fragile
        for compIdx in range(len(h.mmAllComps) - 1, -1, -1):
            if h.mmAllComps[compIdx].name.startswith('Axon'):
                h.mmAllComps.remove(compIdx)
                
    def _createComp(self, compName, list_ref):
        
        comp = h.MechComp(compName, list_ref)
        h.mmAllComps.append(comp)
        
        self._mac.dismissMechManagerAndScheduleRescan()
        