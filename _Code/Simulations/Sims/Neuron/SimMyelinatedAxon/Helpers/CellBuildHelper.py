
# WARNING: all new sections created with NEURON's CellBuild-er:
#   * have the same length of 100 um even though the lines drawn by user may have different length
#   * are created with the huge diam of 500 um; we'll correct it immediately once user clicks "Done", but until then the sections look ugly if "Shape Style = Show Diam"

# !! check if we need to use "has_trueparent", "trueparent" and "section_orientation" somewhere in the code when "soma" is overwritten
# !! do we need to consume any biophysics that user might specify for axon in CellBuild-er ?
# !! test what happens when the overwritten "soma" has some PPs (particularly, our GJs)

from neuron import h, nrn

import GuiPrimitiveWrappers as bc

from Helpers.ProtoGeomStructs import ProtoSection

from OtherInterModularUtils import codeContractViolation


class CellBuildHelper:
    
    _mainBoxOrNone = None
    _auxBoxOrNone = None
    
    # Data members added in the ctor:
    #   _baseAxonHelper, _sim
    
    # Data members added in "analyzeSecNamesAndCheckForNotImplScenario":
    #   _isSomaOverwritten, _soma
    
    # Data members added in "_consumeQuoteSoma":
    #   _impSomaProtoSection, _impSomaParentSecAndArcOrNone, _impSomaChildSecAndArcListExceptAxon, _impSomaRa
    
    
    def __init__(self, baseAxonHelper, sim):
        self._baseAxonHelper = baseAxonHelper
        self._sim = sim
        
    def analyzeSecNamesAndCheckForNotImplScenario(self):
        
        lines1 = []
        line2 = "This requires more sophisticated interaction between BrainCell and NEURON's CellBuild-er."
        line3 = "We'll use a predefined axon instead."
        
        isSomaFound, isAxonFound = self._analyzeSecNames()
        
        if isSomaFound and type(h.soma) != nrn.Section and len(h.soma) > 1:
            lines1.append("There is \"soma[*]\" array of sections in the base geometry.")
            # NEURON's CellBuild-er is about to destroy the array and create a single section "soma" instead
            
        if isAxonFound:
            lines1.append("There is some \"axon\" section(s) not tagged as axon during the base geometry import.")
            # NEURON's CellBuild-er is about to destroy some section(s) outside "axon_ref"
            
        if lines1:
            h.mwh.showNotImplementedWarning(*lines1, line2, line3, '')
            return True
            
        self._isSomaOverwritten = isSomaFound
        
        if isSomaFound:
            if type(h.soma) == nrn.Section:
                self._soma = h.soma
            else:
                self._soma = h.soma[0]
                
        return False
        
    def show(self):
        
        if self._isSomaOverwritten:
            
            self._consumeQuoteSoma()
            
            # Just to avoid the next warning from CellBuild-er: "Previously existing soma[0] points to a section which is being deleted"
            h.delete_section(sec=self._soma)
            
        h.load_file('celbild.hoc')
        h.restoreDefaultPanelScrollIvocStyle()
        
        # We wrap NEURON's CellBuild-er into our VBox in order to:
        #   * move it to a better position so user can see the axon in SimMyelinatedAxon widget when working with NEURON's CellBuild-er ("Continuous Create" mode)
        #   * handle the "dismiss_action"
        with bc.VBox('CellBuild[0]', 0, 0) as self._mainBoxOrNone:  # !! can we inherit the name from cb.vbox?
            
            # !! Beware: it creates a new "soma" which overwrites our "soma" if we have a section with such a name
            #       option 1 (implemented): manage this new "soma"
            #       option 2 (alternative): push_object, then overwrite "sname" in CellBuildTopology
            #                               UPD: we have to overwrite the ctor proc definition
            #       option 3 (alternative): NEURON's CellBuild-er HOC files substitution
            #       option 4 (alternative): separate process + export/import
            # !! maybe don't create a new NEURON's CellBuild-er each time, but show the last one again
            # !! Q1: what happens when our "soma" is defined as an array of sections?
            # !! Q2: what if name "soma" is used for smth else (not a section)?
            cb = h.CellBuild()      # %NEURONHOME%\lib\hoc\celbild\celbild1.hoc
            
            # !! BUG: despite we flip to "Topology" page, the "About" radiobutton is shown as selected anyway
            cb.page(1)
            
            cb.cexport(1)
            
            # !! ideally, we need to be ready for a rare case when "axon" name is used for a section outside "axon_ref" list OR
            #    when the name is used for some top-level var
            cb.topol.sname = 'axon'
            
            self._mainBoxOrNone.dismiss_action(self._cancelButtonHandler)
            
        # !! alternatively, we can set up a timer and check for cb.vbox.ismapped()
        with bc.VBox('Axon drawn by hand', 0, 400, panel=True) as self._auxBoxOrNone:
            h.xlabel('Use NEURON\'s CellBuild-er above to draw axon, then click "Done" below.')
            h.xlabel('The axon may have either thread-like or fork-like topology.')
            h.xlabel('')
            h.xbutton('* Done', self._doneButtonHandler)
            h.xbutton('* Cancel', self._cancelButtonHandler)
            h.xlabel('* Please don\'t interact with "Axon simulation" widget and don\'t start the sim before clicking any of these.')   # or "X"
            self._auxBoxOrNone.dismiss_action(self._cancelButtonHandler)
            
    def dismissBoxesAndRollBackAllChangesToSoma(self):
        
        self._dismissBoxes()
        
        if self._isSomaOverwritten:
            
            # Modifying "soma" section created by CellBuild-er to be similar to the deleted "soma" as much as possible
            self._restoreQuoteSoma()
            
        else:
            
            # Deleting "soma" section created by CellBuild-er
            h.delete_section(sec=h.soma)
            
        self._soma = None
        
        
    def _doneButtonHandler(self):
        
        _, isAxonFound = self._analyzeSecNames()
        if not isAxonFound:
            h.mwh.showWarningBox('Please draw at least one axon section.')
            return
            
        self.dismissBoxesAndRollBackAllChangesToSoma()
        
        axonSecsList = self._getQuoteAxonSecsList()
        
        if not self._isSomaOverwritten:
            # Connecting the new axon root to the old soma
            axonRootSecIdx = 0          # !! fragile: ideally, we need to find a section among "axon_ref" List being the old soma child
            axonSecsList[axonRootSecIdx].connect(self._baseAxonHelper.soma, self._baseAxonHelper.somaConnectionPoint)
            
        # Populating the List of SectionRef-s for axon
        if h.axon_ref:
            codeContractViolation()
        for sec in axonSecsList:
            h.axon_ref.append(h.SectionRef(sec=sec))
            
        self._sim.onCellBuilderDoneOrCancel(False)
        
    def _cancelButtonHandler(self):
        
        _, isAxonFound = self._analyzeSecNames()
        if isAxonFound:
            for sec in self._getQuoteAxonSecsList():
                h.delete_section(sec=sec)
                
        self._sim.onCellBuilderDoneOrCancel(True)   # --> self.dismissBoxesAndRollBackAllChangesToSoma()
        
    def _consumeQuoteSoma(self):
        
        soma = self._soma
        
        # Save "soma" section geometry and "nseg" so we can restore it later
        self._impSomaProtoSection = ProtoSection(soma.nseg)
        self._impSomaProtoSection.copyUniquePointsFromSecToList(soma)
        
        # Saving the info about "soma" parent connection
        sec_ref = h.SectionRef(soma)
        if sec_ref.has_parent():
            parentSec = sec_ref.parent
            y = h.parent_connection(sec=sec_ref.sec)
            self._impSomaParentSecAndArcOrNone = (parentSec, y)
        else:
            self._impSomaParentSecAndArcOrNone = None
            
        # Saving the info about all "soma" child connections except axon (the axon was deleted earlier)
        axonSecsSet = set(sec_ref.sec for sec_ref in h.axon_ref)
        self._impSomaChildSecAndArcListExceptAxon = []
        for childIdx in range(sec_ref.nchild()):
            childSec = sec_ref.child[childIdx]
            if childSec in axonSecsSet:
                codeContractViolation()
            y = h.parent_connection(sec=childSec)
            self._impSomaChildSecAndArcListExceptAxon.append((childSec, y))
            
        # Biophysics currently ignored by the JSON framework
        self._impSomaRa = soma.Ra
        
    def _restoreQuoteSoma(self):
        
        soma = h.soma
        
        # Correcting "soma" section created by CellBuild-er to restore the old geometry and nseg
        self._impSomaProtoSection.copyPointsFromListToSecAndAssignNseg(soma)
        
        # Restoring all connections with other sections
        if self._impSomaParentSecAndArcOrNone:
            parentSec, arc = self._impSomaParentSecAndArcOrNone
            soma.connect(parentSec, arc)
        for childSec, arc in self._impSomaChildSecAndArcListExceptAxon:
            childSec.connect(soma, arc)
            
        # Biophysics currently ignored by the JSON framework
        soma.Ra = self._impSomaRa
        
        # Replacing one SectionRef in two list_ref-s
        isFound = self._replaceOneSecRefInTheList(h.soma_ref)   # !! fragile: ideally, we need to look in "dendrite_ref", "other_ref" etc.
        if not isFound:
            codeContractViolation()
        somaCompIdx = 0             # !! fragile: ideally, we need to loop through mmAllComps
                                    #    and find the comp such that comp.list_ref contains a SectionRef to "soma" section
        somaComp = h.mmAllComps[somaCompIdx]
        self._replaceOneSecRefInTheList(somaComp.list_ref)
        # !! we don't check isFound here because somaComp.list_ref and h.soma_ref might be the same List reference
        
        # Initializing the distance centre in case if we replaced h.soma_ref[0]
        if h.soma_ref[0].sec == soma:
            h.distance(sec=soma)
            
        # !! maybe restore biophysics in soma using "Soma" MechComp
        #    UPD 1: we call dirtyStatesHelper.onParamChange(EnumParamCats.modifGeom) downstream which will result in applying all biophysics
        #    UPD 2: for "test sines", we lose "soma" biophysics indeed (BUG)
        
        # Pass the new soma section to BaseAxonHelper (somaConnectionPoint never changes)
        self._baseAxonHelper.onSomaOverwritten(soma)
        
    def _getQuoteAxonSecsList(self):
        
        # Converting "h.axon" to a regular list of sections
        tp = type(h.axon)
        return [h.axon] if tp == nrn.Section else list(h.axon)
        
    def _replaceOneSecRefInTheList(self, list_ref):
        isFound = False
        for idx, sec_ref in enumerate(list_ref):
            if sec_ref.exists():
                continue
            if isFound:
                codeContractViolation()
            h.replaceItemInList(list_ref, h.SectionRef(h.soma), idx)
            isFound = True
        return isFound
        
    # We use this method instead of "hasattr(h, 'name')" because it never gives False and just raises the non-interceptable error "name : section was deleted"
    # (looks like a bug in NEURON's __getattr__ override)
    # !! maybe rewrite it using h.issection(regex)
    def _analyzeSecNames(self):
        isSomaFound, isAxonFound = False, False
        for sec in h.allsec():
            secName = str(sec)  # !! sec.name() ?
            if secName == 'soma' or secName.startswith('soma['):
                isSomaFound = True
                if isAxonFound:
                    break
            if secName == 'axon' or secName.startswith('axon['):
                isAxonFound = True
                if isSomaFound:
                    break
        return isSomaFound, isAxonFound
        
    def _dismissBoxes(self):
        h.unmapIfNotNil(self._mainBoxOrNone)
        h.unmapIfNotNil(self._auxBoxOrNone)
        