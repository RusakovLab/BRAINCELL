
# Here we simulate inside-out diffusion of potassium from axon and Schwann cells into the space between them (radial diffusion from both sides)
# We define some currents "ik" in axon and Schwann cells and observe how they contribute to potassium concentration in the common space
# The resulting concentration is written to "ko" in axon segments and Schwann cells segments; it can be READ and used in the same MOD file that WRITE-s "ik"

# !! Current limitations:
#   1. Only potassium is supported for the radial diffusion
#   2. No support for inhomogeneous diam along axon (and the same limitation for Schwann cells)
#   3. No support for inhomogeneous shells along axon (i.e. different "numShells" and "dr" for different sections);
#      as a result of this limitation, "diam_sheath" specifies not only inner diam of Schwann cells,
#      but also the diam where we apply the Dirichlet boundary condition "conc = ko0" for non-myelinated segments of axon
#   4. The model doesn't apply any longitudinal diffusion, however, its role may be significant, at least in the nodes of Ranvier

# !! BUG:
#    NEURON's units checker "modlunit" finds a problem in the helper MOD file "_i2fc.mod"

# !! Other imperfections:
#   1. The colourmap shows all the columns using the same column width even though they represent segments of different length
#   2. When isUseRealBiophysOrTestSines == True, our MOD files do:
#         WRITE ik, ina, ica  --  ok
#         READ ko, cao        --  ok (but in fact, cao is not used in the MOD file)
#         READ nai, cai       --  maybe BUG: we don't assign them anywhere

# !! Caution:
#   * For any distributed mechanisms inserted into Schwann sections, if they read "diam", it represents the inner diam of the Schwann cell, which may be unexpected for the mechanism

# Docs for RxD:
#   https://nrn.readthedocs.io/en/latest/python/modelspec/programmatic/rxd.html

# Some useful examples for RxD radial diffusion:
#   https://neuron.yale.edu/ftp/neuron/20210703-rxd-tutorial.pdf
#   https://neuron.yale.edu/neuron/docs/radial-diffusion
#   https://nrn.readthedocs.io/en/latest/rxd-tutorials/combining%20currents%20from%20mod%20files%20with%20rxd.html
#   https://neuron.yale.edu/neuron/docs/hodgkin-huxley-using-rxd
#   %NEURONHOME%\lib\python\neuron\rxdtests\tests\include_flux.py


from neuron import h, rxd

# import os
import itertools

from Helpers.BasicEnums import EnumAxonGeometry, EnumMyelSheath
from Helpers.AxonTransformationHelper import AxonTransformationHelper
from Helpers.ProcAdvanceHelper import ProcAdvanceHelper

import MsgWarnHelperWrappers as mwhw
from OtherInterModularUtils import getAllUninsertableBiophysMechNamesList, codeContractViolation


class SimMyelinatedAxonCore:
    
    # Public methods:
    #   ctor, createBaseGeomAxon, onBaseGeomAxonChanged, deleteBaseGeomAxon, validate, createModifiedGeometryAxon, prepareSecListsForBaseGeometryAxon, showPlotShapeIfNeeded, initBiophysics, dismissMechManagerAndScheduleRescan, initRxDStaff, makeGraphsIfNeeded, callAnimSavePrintHelperOnPreRun, callAnimSavePrintHelperOnPreContinue, colourSectsAndAddLabels, cleanup
    
    # Data members and callables added in ctor:
    #   _params, enumMyelSheath, isUseRealBiophysOrTestSines, _baseAxonHelper, _axonBiophysCompsHelper, _presParams, _animSavePrintHelper, _onMyelStatusChanged, _axonTransformationHelper, isTransformed
    #   _isBiophysFromJsonApplied, _userHasEditedBiophys
    #   _allUninsertableMechNames
    
    # Data members added in "createBaseGeomAxon":
    #   _L_axon, _diam_axon
    
    # Data members added in "createModifiedGeometryAxon" or "prepareSecListsForBaseGeometryAxon":
    #   AISPs, AISDs
    #   axonBeforeFirstSchwannSecOrNone, axonUnderSchwannSecsList, axonNodeOfRanvierSecsList, axonAfterLastSchwannSecOrNone, insulatorSecsList, schwannSecsList
    #   _axonUnderSchwannSecToSchwannSecDict
    #   _axonFirstSec, _axonLastSec
    #   axonTrunkSecsExceptTerms, _axonTrunkSecsWithTerms, _axonTreeSecsExceptTerms, axonTreeSecsWithTerms
    
    # Data member added in "showPlotShapeIfNeeded":
    #   _plotShape
    
    # Data members added in "initRxDStaff":
    #   _shells, _k, _diffusions
    
    # Data member added in "makeGraphsIfNeeded":
    #   _graphs
    
    def __init__(self, params, enumMyelSheath, isUseRealBiophysOrTestSines, baseAxonHelper, myelRegionHelper, axonBiophysCompsHelper, presParams, animSavePrintHelper, onMyelStatusChanged):
        
        self._params                     = params
        self.enumMyelSheath              = enumMyelSheath
        self.isUseRealBiophysOrTestSines = isUseRealBiophysOrTestSines
        self._baseAxonHelper             = baseAxonHelper
        self._axonBiophysCompsHelper     = axonBiophysCompsHelper
        self._presParams                 = presParams
        self._animSavePrintHelper        = animSavePrintHelper
        self._onMyelStatusChanged        = onMyelStatusChanged
        
        self._axonTransformationHelper = AxonTransformationHelper(params, baseAxonHelper, myelRegionHelper)
        
        self.isTransformed = False
        
        # Tracks whether JSON biophysics has been imported at least once for the current sections.
        # Reset to False when sections are destroyed (cleanup with isDeleteAllModifGeomAxonSecs=True).
        self._isBiophysFromJsonApplied = False
        
        # Tracks whether the user has made manual edits via Manager of Biophysics.
        # When True and sections must be recreated, the user is warned that edits will be lost.
        self._userHasEditedBiophys = False
        
        self._allUninsertableMechNames = getAllUninsertableBiophysMechNamesList()
        
    # ----- Start of base axon geometry -----
    
    def createBaseGeomAxon(self, enumAxonGeometry):
        
        if enumAxonGeometry == EnumAxonGeometry.imported:
            self._baseAxonHelper.switchToImportedAxonOrAxonDrawnByHand(True)
        elif enumAxonGeometry == EnumAxonGeometry.predefined:
            self._baseAxonHelper.switchToPredefGeometryAxon()
        elif enumAxonGeometry == EnumAxonGeometry.drawnByHand:
            self._baseAxonHelper.switchToImportedAxonOrAxonDrawnByHand(False)
        else:
            codeContractViolation()
        
        # A new base axon section was created; JSON biophysics must be re-imported
        self._isBiophysFromJsonApplied = False
        
        axon = self._baseAxonHelper.axon
        
        self._L_axon = axon.L
        self._diam_axon = axon.diam
        
        self._params.setTrunkParams(axon.L, axon.diam, axon.nseg)
        
        self._printBaseAxonStats()
        
        self._onMyelStatusChanged(False)
        
    def onBaseGeomAxonChanged(self, isLenChanged, isNsegChanged):
        
        axon = self._baseAxonHelper.axon
        
        if isLenChanged:
            axon.L = self._params.L_axon
            self._L_axon = axon.L
            self._printBaseAxonLen()
            
        axon.diam = self._params.diam_axon
        self._diam_axon = axon.diam
        
        if isNsegChanged:
            axon.nseg = int(self._params.nseg_axon)
            
    def deleteBaseGeomAxon(self):
        self._cleanupSecContainersAndBiophysComps()
        self._baseAxonHelper.deleteAxon()
        
        # Base axon sections are destroyed, so JSON must be re-imported
        self._isBiophysFromJsonApplied = False
        
        
    def _printBaseAxonStats(self):
        
        self._printTopologyIfNotTooLong('before')
        
        self._printBaseAxonLen()
        
    def _printTopologyIfNotTooLong(self, beforeOrAfter):
        
        totalNumSecs = sum(1 for _ in h.allsec())
        if totalNumSecs <= 100:
            print(f'Topology {beforeOrAfter} axon transformation:')
            h.topology()
            
    def _printBaseAxonLen(self):
        print('Axon length before transformation: ', self._baseAxonHelper.axon.L, ' (um)')
        
    # ----- End of base axon geometry -----
    
    
    # ----- Start of modified axon geometry -----
    
    def validate(self, isZebraMyelRegion):
        return self._params.validate(self._diam_axon, isZebraMyelRegion)
        
    def createModifiedGeometryAxon(self):
        
        if self.enumMyelSheath == EnumMyelSheath.remove:
            codeContractViolation()
            
        # New sections will be created; JSON biophysics must be re-imported
        self._isBiophysFromJsonApplied = False
            
        # The transformation itself: creating new sections and deleting old ones
        
        AISPs, \
        AISDs, \
        axonBeforeFirstSchwannSecOrNone, \
        axonUnderSchwannSecsList, \
        axonNodeOfRanvierSecsList, \
        axonAfterLastSchwannSecOrNone, \
        insulatorSecsList, \
        schwannSecsList, \
        axonUnderSchwannSecToSchwannSecDict = self._axonTransformationHelper.createModifiedGeometryAxon(self.enumMyelSheath == EnumMyelSheath.deploy)
        
        axonFirstSec = axonBeforeFirstSchwannSecOrNone if axonBeforeFirstSchwannSecOrNone else axonUnderSchwannSecsList[0]
        axonLastSec = axonAfterLastSchwannSecOrNone if axonAfterLastSchwannSecOrNone else axonUnderSchwannSecsList[-1]
        
        self._baseAxonHelper.deleteBaseTrunkAndConnectTerminalsToModifiedTrunk(axonLastSec)
        
        # Prepare some iterables for axon sections
        
        axonTrunkSecsExceptTerms = []
        if axonBeforeFirstSchwannSecOrNone:
            axonTrunkSecsExceptTerms.append(axonBeforeFirstSchwannSecOrNone)
        for sec1, sec2 in zip(axonUnderSchwannSecsList, axonNodeOfRanvierSecsList):
            axonTrunkSecsExceptTerms.append(sec1)
            axonTrunkSecsExceptTerms.append(sec2)
        axonTrunkSecsExceptTerms.append(axonUnderSchwannSecsList[-1])
        if axonAfterLastSchwannSecOrNone:
            axonTrunkSecsExceptTerms.append(axonAfterLastSchwannSecOrNone)
        
        axonTrunkSecsWithTerms = axonTrunkSecsExceptTerms + self._baseAxonHelper.axonTerminalSecsList
        axonTreeSecsExceptTerms = [AISPs] + [AISDs] + axonTrunkSecsExceptTerms + insulatorSecsList + schwannSecsList
        axonTreeSecsWithTerms = [AISPs] + [AISDs] + axonTrunkSecsWithTerms + insulatorSecsList + schwannSecsList
        
        # Save the sections in the class
        
        self.AISPs = AISPs
        self.AISDs = AISDs
        
        self.axonBeforeFirstSchwannSecOrNone = axonBeforeFirstSchwannSecOrNone
        self.axonUnderSchwannSecsList = axonUnderSchwannSecsList
        self.axonNodeOfRanvierSecsList = axonNodeOfRanvierSecsList
        self.axonAfterLastSchwannSecOrNone = axonAfterLastSchwannSecOrNone
        self.insulatorSecsList = insulatorSecsList
        self.schwannSecsList = schwannSecsList
        
        self._axonFirstSec = axonFirstSec
        self._axonLastSec = axonLastSec
        
        self._axonUnderSchwannSecToSchwannSecDict = axonUnderSchwannSecToSchwannSecDict
        
        self.axonTrunkSecsExceptTerms = axonTrunkSecsExceptTerms
        self._axonTrunkSecsWithTerms = axonTrunkSecsWithTerms
        self._axonTreeSecsExceptTerms = axonTreeSecsExceptTerms
        self.axonTreeSecsWithTerms = axonTreeSecsWithTerms
        
        
        self.isTransformed = True
        self._onMyelStatusChanged(True)
        
        self._printModifiedAxonStatsAndShowPlotShape()
        
    # !! code dup. with "_cleanupSecContainersAndBiophysComps"
    def prepareSecListsForBaseGeometryAxon(self):
        
        self.AISPs = None
        self.AISDs = None
        
        self.axonBeforeFirstSchwannSecOrNone = None
        self.axonUnderSchwannSecsList = []
        self.axonNodeOfRanvierSecsList = self._baseAxonHelper.axon
        self.axonAfterLastSchwannSecOrNone = None
        self.insulatorSecsList = []
        self.schwannSecsList = []
        
        self._axonFirstSec = None
        self._axonLastSec = None
        
        self._axonUnderSchwannSecToSchwannSecDict = dict()
        
        self.axonTrunkSecsExceptTerms = [self._baseAxonHelper.axon]
        self._axonTrunkSecsWithTerms = [self._baseAxonHelper.axon] + self._baseAxonHelper.axonTerminalSecsList
        self._axonTreeSecsExceptTerms = self.axonTrunkSecsExceptTerms
        self.axonTreeSecsWithTerms = self._axonTrunkSecsWithTerms
        
    def showPlotShapeIfNeeded(self):
        
        if hasattr(self, '_plotShape'):
            return
            
        plotShape = h.PlotShape(0)
        self._setSecsColourAndAddLabel(    plotShape, 'Soma',            h.enumColours.red,    0.9,  [self._baseAxonHelper.soma])
        self._setSecsColourAndAddLabel(    plotShape, 'AISPs and AISDs', h.enumColours.green,  0.85, [self.AISPs, self.AISDs])
        self._setSecsColourAndAddLabel(    plotShape, 'Axon',            h.enumColours.blue,   0.8,   self._axonTrunkSecsWithTerms)
        if self.schwannSecsList:
            self._setSecsColourAndAddLabel(plotShape, 'Schwann cells',   h.enumColours.orange, 0.75,  self.schwannSecsList)
        plotShape.view(0, 0, 1, 1, 0, 0, 290, 175)
        plotShape.exec_menu('Show Diam')
        plotShape.exec_menu('View = plot')
        
        self._plotShape = plotShape
        
        
    def _printModifiedAxonStatsAndShowPlotShape(self):
        
        self._printTopologyIfNotTooLong('after')
        
        axonLengthAfterSplitting = sum(sec.L for sec in self.axonTrunkSecsExceptTerms)
        print('Axon length after transformation:  ', axonLengthAfterSplitting, ' (um)')
        print('Number of Schwann cells:    ', len(self.schwannSecsList))
        print('Number of nodes of Ranvier: ', len(self.axonNodeOfRanvierSecsList))
        for secIdx in range(len(self.schwannSecsList)):
            print(    f'schwann[{secIdx}].L:           ', self.schwannSecsList[secIdx].L, ' (um)')
            if secIdx < len(self.axonNodeOfRanvierSecsList):
                print(f'axonNodeOfRanvier[{secIdx}].L: ', self.axonNodeOfRanvierSecsList[secIdx].L, ' (um)')
                
        self.showPlotShapeIfNeeded()
        
    def _setSecsColourAndAddLabel(self, shape, label, colour, y, secs):
        # !! would it make sense to use h.listOfSecRefToSecList here?
        for sec in secs:
            shape.color(colour, sec=sec)
        shape.label(0.1, y, label, 2, 1, 0, 1, colour)
        
    # ----- End of modified axon geometry -----
    
    
    # ----- Start of biophysics -----
    
    def initBiophysics(self):
        
        # Always update ion initial concentrations from GUI params
        h.ko0_k_ion = self._params.ko0
        h.ki0_k_ion = self._params.ki0
        
        if self.isTransformed:
            axonExceptTermsSecsList = self.axonTrunkSecsExceptTerms
            schwannSecsListOrEmpty = self.schwannSecsList
        else:
            axonExceptTermsSecsList = [self._baseAxonHelper.axon]
            schwannSecsListOrEmpty = []
            
        if self.isUseRealBiophysOrTestSines:
            
            if not self._isBiophysFromJsonApplied:
                # First time or after sections were recreated: import mechanisms from JSON
                biophysJsonFileName = 'SimMyelinatedAxon.json'
                isError = h.beih.importForSim(biophysJsonFileName, 0)
                if isError:
                    codeContractViolation()
                    
                # An appendix to axon biophysics (must use xopen, not load_file, to re-execute on section recreation)
                h.xopen('_Code/Simulations/Sims/Neuron/SimMyelinatedAxon/HocCode/biophysics_deprecated.hoc')
                
                self._isBiophysFromJsonApplied = True
                
            # else: user has already imported JSON and possibly edited mechanisms via Manager of Biophysics;
            #       skip re-import to preserve user's edits
            
        else:
            
            # We don't uninsert the old mechs here because switching from "real biophysics" to "test sines"
            # is done through destruction / creation of the sections (see the comment in SimMyelinatedAxon._biophysRadioButtonHandler)
            
            # Initializing the test sines mech
            for sec in axonExceptTermsSecsList:
                self._initSectionBiophysicsWithTestSines(sec, self._params.Xfactor_axon, self._params.Tfactor_axon)
            for sec in schwannSecsListOrEmpty:
                self._initSectionBiophysicsWithTestSines(sec, self._params.Xfactor_schwann, self._params.Tfactor_schwann)
                
        # Initializing the current-to-flux converter mech
        for sec in itertools.chain(axonExceptTermsSecsList, schwannSecsListOrEmpty):
            sec.insert('i2fc')
            for segm in sec:
                segm.i2fc.segmArea = segm.area()    # !! can I get this area directly in the MOD file?
                
        h.valence_i2fc = h.ion_charge('k_ion')
        
        self.dismissMechManagerAndScheduleRescan()
        
    # !! maybe move this to SimMyelinatedAxon
    def dismissMechManagerAndScheduleRescan(self):
        h.dismissIfNotNil(h.mechManagerMainWidget)
        h.mmIcrHelper.scheduleRescan(2)
        
        
    def _initSectionBiophysicsWithTestSines(self, sec, Xfactor, Tfactor):
        
        sec.insert('iksine')
        
        for segm in sec:
            
            mech = segm.iksine
            
            mech.ik0 = self._params.ik0
            mech.A = self._params.A
            
            mech.x = h.distance(segm)
            
            mech.X = Xfactor * self._L_axon
            mech.T = Tfactor * self._params.Dt
            
    # ----- End of biophysics -----
    
    
    # ----- Start of RxD staff -----
    
    def initRxDStaff(self):
        """Configuration B: Extended shell model with piecewise diffusion.
        
        Radial grid layout (all radii normalized to axon radius = 1.0):
        
          Inner zone:   shells 1..numShells        from R_a to R_sheath        diffusion D
          Outer zone:   shells numShells+1..total   from R_sheath to R_max     diffusion D (node) or D/alpha (myelin)
        
        Boundary conditions at R_max:
          - Myelin zone (axonUnderSchwann):     zero flux  dK/dr = 0
          - Node zone (all other axon secs):    Dirichlet  [K] = ko0
        """
        
        with mwhw.PleaseWaitBox('Initializing NEURON RxD.'):
            
            # !! code dup. with RxdBackend
            # !! NEURON docs read: "Currently has no effect on 1D reaction-diffusion models."
            # rxd.nthread(os.cpu_count())
            
            # --- Radial grid geometry ---
            
            numInnerShells, numExtShells, totalNumShells, dr_inner, dr_ext, R_sheath_norm = self._computeExtendedShellCounts()
            
            R_axon = self._diam_axon / 2.0      # um (absolute)
            Rmax = self._params.Rmax             # um (absolute)
            R_sheath = self._params.diam_sheath / 2.0   # um (absolute)
            
            # Store for later use (visualization, ProcAdvanceHelper)
            self._numInnerShells = numInnerShells
            self._numExtShells = numExtShells
            self._totalNumShells = totalNumShells
            
            # --- 1. Where -- define shells and borders between them ---
            
            shells = []
            borders = []
            
            # The innermost shell touches axon; the outermost one extends to Rmax
            nrn_region = None # 'o'
            # !! for some reason, specifying nrn_region='o' for shells[0] results in neglecting "axon.ik", so we have to do it for shells[1] in the cycle below
            #    (no idea why this happens, maybe we need to add a border before shells[0] or specify geometry=rxd.membrane() for shells[0])
            
            # Shell 0 (innermost, touches axon membrane)
            shells.append(rxd.Region(self.axonTrunkSecsExceptTerms, name='shell%i' % 1,
                                     geometry=rxd.Shell(1.0, 1 + dr_inner),
                                     nrn_region=nrn_region))
            
            # Inner zone shells 1..numInnerShells-1
            for i in range(1, numInnerShells):
                borders.append(rxd.Region(self.axonTrunkSecsExceptTerms, name='border%i' % i,
                                          geometry=rxd.FixedPerimeter(2 * h.PI * (1 + i * dr_inner))))
                if i == 1:
                    # Telling NEURON to write the concentration from shells[1] to "axon.ko"
                    nrn_region = 'o'
                    # !! alternatively, we can copy the conc from shells[0] explicitly in _ProcAdvanceHelper.onAdvance -- would it be more correct?
                else:
                    nrn_region = None
                shells.append(rxd.Region(self.axonTrunkSecsExceptTerms, name='shell%i' % (i + 1),
                                         geometry=rxd.Shell(1 + i * dr_inner, 1 + (i + 1) * dr_inner),
                                         nrn_region=nrn_region))
            
            # Border at the sheath boundary (between inner and outer zones)
            borders.append(rxd.Region(self.axonTrunkSecsExceptTerms, name='border%i' % numInnerShells,
                                      geometry=rxd.FixedPerimeter(2 * h.PI * R_sheath_norm)))
            
            # Outer (external) zone shells
            for j in range(numExtShells):
                r_lo = R_sheath_norm + j * dr_ext
                r_hi = R_sheath_norm + (j + 1) * dr_ext
                shellIdx = numInnerShells + j + 1
                shells.append(rxd.Region(self.axonTrunkSecsExceptTerms, name='shell%i' % shellIdx,
                                         geometry=rxd.Shell(r_lo, r_hi),
                                         nrn_region=None))
                if j > 0:
                    borders.append(rxd.Region(self.axonTrunkSecsExceptTerms, name='border%i' % (numInnerShells + j),
                                              geometry=rxd.FixedPerimeter(2 * h.PI * r_lo)))
            
            # --- 2. Who -- potassium ---
            k = rxd.Species(shells, d=self._params.Diff_k, name='k', charge=h.ion_charge('k_ion'), initial=h.ko0_k_ion)
            
            # --- 3. What -- use reactions to setup diffusion between the shells ---
            ks = [k[reg] for reg in shells]    # potassium on each shell
            
            # Scale factor so the flux (Diff_k/dr)*K has units molecules/um^2/ms (where dr is the thickness of the shell)
            mM_to_mol_per_um = 6.0221409e+23 * 1e-18
            
            Diff_k = self._params.Diff_k
            alpha = self._params.alpha
            
            # Create the multi-compartment reactions between the pairs of shells
            # Piecewise diffusion:
            #   - Inner zone (shells 0..numInnerShells-1): D = Diff_k
            #   - Outer zone (shells numInnerShells..totalNumShells-1): D = Diff_k / alpha for myelinated, D = Diff_k for node
            #
            # Since RxD MultiCompartmentReaction applies uniformly to all sections in the region,
            # and we need DIFFERENT diffusion coefficients for myelinated vs non-myelinated sections
            # in the outer zone, we use a single D for all reactions and handle the piecewise behavior
            # by using different rates per shell pair:
            #   - For the outer zone, we use Diff_k / alpha as the rate
            #     (this applies to both myelinated and non-myelinated sections uniformly)
            #   - For non-myelinated sections, ProcAdvanceHelper will apply the Dirichlet BC at R_max anyway,
            #     so the diffusion rate in the outer zone doesn't matter much there since the BC dominates
            #
            # !! If we need truly section-dependent diffusion in the outer zone, we would need separate
            #    rxd.Region objects for myelinated vs non-myelinated axon trunk sections.
            #    For now, we use D/alpha uniformly in the outer zone as a reasonable approximation.
            
            diffusions = []
            
            # Inner zone reactions (shells 0 to numInnerShells-1)
            for i in range(numInnerShells - 1):
                scaledD = mM_to_mol_per_um * Diff_k
                diffusions.append(rxd.MultiCompartmentReaction(ks[i], ks[i + 1],
                                                               scaledD, scaledD,
                                                               border=borders[i]))
            
            # Transition border reaction (inner shell numInnerShells-1 <-> outer shell numInnerShells)
            # Use the harmonic mean of the two diffusion coefficients at the interface
            D_inner = Diff_k
            D_outer = Diff_k / alpha
            D_interface = 2.0 * D_inner * D_outer / (D_inner + D_outer)
            scaledD_interface = mM_to_mol_per_um * D_interface
            diffusions.append(rxd.MultiCompartmentReaction(ks[numInnerShells - 1], ks[numInnerShells],
                                                           scaledD_interface, scaledD_interface,
                                                           border=borders[numInnerShells - 1]))
            
            # Outer zone reactions (shells numInnerShells to totalNumShells-1)
            scaledD_ext = mM_to_mol_per_um * D_outer
            for j in range(numExtShells - 1):
                shellPairIdx = numInnerShells + j
                borderIdx = numInnerShells + j   # borders list index
                diffusions.append(rxd.MultiCompartmentReaction(ks[shellPairIdx], ks[shellPairIdx + 1],
                                                               scaledD_ext, scaledD_ext,
                                                               border=borders[borderIdx]))
            
            # --- 4. Add fluxes and prepare boundary condition node lists ---
            
            def _includeSchwannFlux(sec_sch, segmIdx_sch, node_ax):
                u = (0.5 + segmIdx_sch) / sec_sch.nseg  # !! can we replace this with smth straightforward like segm_sch = sec_sch.segments[segmIdx_sch] ?
                segm_sch = sec_sch(u)                   #
                node_ax.include_flux(segm_sch._ref_kflux_i2fc)      # Default units: molecule/ms
                
            # Node lists for ProcAdvanceHelper:
            #   - nodeOfRanvierOuterNodesList:  outermost nodes of non-myelinated sections -> Dirichlet [K]=ko0 at Rmax
            #   - myelinatedOuterNodesList:     outermost nodes of myelinated sections -> zero flux at Rmax (no explicit BC needed)
            #   - schwannSheathNodesList:        nodes at the user-chosen shell for:
            #       (a) reading concentration to copy to schwann.ko each timestep
            #       (b) injecting Schwann cell flux into the radial grid
            #     Controlled by schwannKoShell (offset from R_sheath: 0=default, negative=inward, positive=outward)
            
            nodeOfRanvierOuterNodesList = []    # Dirichlet BC at Rmax
            myelinatedOuterNodesList = []       # Zero-flux at Rmax (just for bookkeeping, no explicit action)
            schwannSheathNodesList = []         # Nodes at the user-chosen shell for copying to schwann.ko
            
            # Determine which shell index feeds schwann.ko and receives Schwann flux.
            # schwannKoShell is an offset from R_sheath (shell numInnerShells-1):
            #   0 = at R_sheath (default), negative = towards axon, positive = towards R_max
            schwannKoOffset = int(self._params.schwannKoShell)
            sheathShellIdx = numInnerShells - 1   # 0-based index of the last inner shell (at R_sheath)
            schwannKoShellIdx = sheathShellIdx + schwannKoOffset
            
            # Clamp to valid range [0, totalNumShells-1] and update the GUI if clamped
            minOffset = -sheathShellIdx                          # -(numInnerShells - 1)
            maxOffset = totalNumShells - 1 - sheathShellIdx      # numExtShells
            if schwannKoOffset < minOffset:
                schwannKoOffset = minOffset
                schwannKoShellIdx = 0
                self._params.schwannKoShell = schwannKoOffset
            elif schwannKoOffset > maxOffset:
                schwannKoOffset = maxOffset
                schwannKoShellIdx = totalNumShells - 1
                self._params.schwannKoShell = schwannKoOffset
            
            outerMostShellIdx = totalNumShells - 1   # index into shells[] for the outermost shell at Rmax
            
            for sec_ax in self.axonTrunkSecsExceptTerms:
                
                schwannSec = self._axonUnderSchwannSecToSchwannSecDict.get(sec_ax)
                
                for segmIdx_ax, segm_ax in enumerate(sec_ax):
                    nodes = k.nodes(segm_ax)
                    firstNode = nodes[0]                # innermost shell (touches axon membrane)
                    outerMostNode = nodes[-1]            # outermost shell (at Rmax)
                    schwannKoNode = nodes[schwannKoShellIdx]  # shell for Schwann ko read & flux inject
                    
                    # Axon membrane flux always goes into the innermost shell
                    firstNode.include_flux(segm_ax._ref_kflux_i2fc)     # Default units: molecule/ms
                    
                    if schwannSec:
                        # Myelinated segment: Schwann flux injected at the user-chosen shell
                        _includeSchwannFlux(schwannSec, segmIdx_ax, schwannKoNode)    # segmIdx_ax = segmIdx_sch
                        schwannSheathNodesList.append(schwannKoNode)
                        myelinatedOuterNodesList.append(outerMostNode)
                        # Zero-flux BC at Rmax: nothing to do (RxD default is zero flux at boundaries)
                    else:
                        # Non-myelinated segment: Dirichlet BC at Rmax
                        nodeOfRanvierOuterNodesList.append(outerMostNode)
                        
                        
            allNodes = [node for sec in self.axonTrunkSecsExceptTerms for node in k.nodes(sec)]
                    
            self.procAdvanceHelper = ProcAdvanceHelper(
                nodeOfRanvierOuterNodesList,
                self._params.ko0,
                self.schwannSecsList,
                schwannSheathNodesList,
                allNodes,
                self._params.veryMinOuterConc)
            
            
            self._shells = shells
            self._k = k
            self._diffusions = diffusions
            
    # ----- End of RxD staff -----
    
    
    # ----- Start of Graph-s -----
    
    def _computeExtendedShellCounts(self):
        """Compute inner/outer/total shell counts for the Config B extended radial grid.
        
        Returns:
            (numInnerShells, numExtShells, totalNumShells, dr_inner, dr_ext, R_sheath_norm)
        """
        numInnerShells = int(self._params.numShells)
        numExtShells = int(self._params.numExtShells)
        
        dr_inner = (self._params.diam_sheath / self._diam_axon - 1) / numInnerShells      # unitless (normalized to axon radius)
        R_sheath_norm = 1.0 + numInnerShells * dr_inner     # normalized to axon radius
        
        R_axon = self._diam_axon / 2.0                       # um (absolute)
        Rmax = self._params.Rmax                             # um (absolute)
        
        dr_ext = (Rmax / R_axon - R_sheath_norm) / numExtShells   # unitless (normalized to axon radius)
        
        totalNumShells = numInnerShells + numExtShells
        
        return numInnerShells, numExtShells, totalNumShells, dr_inner, dr_ext, R_sheath_norm
    
    def callAnimSavePrintHelperOnPreRun(self):
        
        # In Config B, the visualization extends to Rmax (not diam_sheath/2)
        # This method is called BEFORE initRxDStaff, so compute totalNumShells from params
        _, _, totalNumShells, _, _, _ = self._computeExtendedShellCounts()
        
        self._animSavePrintHelper.onPreRun(
            self._params.Dt,
            self._diam_axon / 2, self._params.Rmax, totalNumShells,
            self.enumMyelSheath, self.isUseRealBiophysOrTestSines)
        
    def makeGraphsIfNeeded(self):
        
        if hasattr(self, '_graphs'):
            return
            
        def _addXLabel(graph, label):
            graph.label(0.45, 0.01, label, 2, 1, 0, 0, h.enumColours.black)
            
        def _addCentralLabel(graph, label):
            graph.label(0.8, 0.7, label, 2, 1, 1, 0, h.enumColours.red)
            
        def _createOneRangeVarGraph(sec1, sec2, varName, label, mwidth, mbottom, mheight, wleft, wtop, wwidth, isMoving):
            graph = h.Graph(0)
            h.flush_list.append(graph)
            dx1 = 1 / sec1.nseg
            dx2 = 1 / sec2.nseg
            segm1 = sec1(dx1/2)
            rangeVarPlot = h.RangeVarPlot(varName, segm1, sec2(1 - dx2/2))
            mleft = h.distance(segm1)
            rangeVarPlot.origin(mleft)
            graph.size(0, self._L_axon, -1, 1)  # !! the y range is just a placeholder
            graph.addobject(rangeVarPlot)
            _addXLabel(graph, 'Distance (um)')
            _addCentralLabel(graph, f'{label}')
            if not self.isUseRealBiophysOrTestSines and isMoving:
                textTempl = 'It moves %s slowly due to ik0 %s 0'
                if self._params.ik0 > 0:
                    text = textTempl % ('up', '>')
                elif self._params.ik0 < 0:
                    text = textTempl % ('down', '<')
                else:
                    text = ''
                graph.label(0.8, 0.6, text, 2, 1, 1, 0, h.enumColours.blue)
            graph.view(mleft, mbottom, mwidth-dx1-dx2, mheight, wleft, wtop, wwidth, 175)
            return graph
            
            
        if self.isUseRealBiophysOrTestSines:
            # Just some placeholders (we'll call "View = plot" on each iter)
            imin = -0.01
            irange = 0.02
            omin = self._params.ko0 - 0.001
            orange = 0.002
        else:
            imin = self._params.ik0 - self._params.A
            irange = 2 * self._params.A
            omin = self._params.ko0 - 0.01
            orange = 0.15
            
        graphs = []
        
        if self.isTransformed:
            for schSecIdx, schwann in enumerate(self.schwannSecsList):
                sch_len = schwann.L
                
                wleft = 400 + schSecIdx * 410
                wwidth = 300
                
                graph = None
                if self._presParams.isDraw[2]:
                    graph = _createOneRangeVarGraph(schwann, schwann, 'ik', f'current in Schwann cell #{schSecIdx+1} (mA/cm2) -- we WRITE it', sch_len, imin, irange, wleft, 0, wwidth, False)
                graphs.append(graph)
                
                graph = None
                if self._presParams.isDraw[3]:
                    graph = _createOneRangeVarGraph(schwann, schwann, 'ko', f'conc on Schwann cell #{schSecIdx+1} (mM) -- we READ it', sch_len, omin, orange, wleft, 900, wwidth, True)
                graphs.append(graph)
                
        wleft = 0
        wwidth = 1000
        
        if self.isTransformed:
            firstSec = self._axonFirstSec
            lastSec = self._axonLastSec
        else:
            firstSec = self._baseAxonHelper.axon
            lastSec = self._baseAxonHelper.axon
            
        graph = None
        if self._presParams.isDraw[0]:
            graph = _createOneRangeVarGraph(firstSec, lastSec, 'ik', 'current in axon (mA/cm2) -- we WRITE it', self._L_axon, imin, irange, wleft, 300, wwidth, False)
        graphs.append(graph)
        
        graph = None
        if self._presParams.isDraw[1]:
            graph = _createOneRangeVarGraph(firstSec, lastSec, 'ko', 'conc on axon (mM) -- we READ it', self._L_axon, omin, orange, wleft, 600, wwidth, True)
        graphs.append(graph)
        
        if self.isTransformed:
            
            def _addOneVerticalLine(graph, x, ymin, ymax):
                graph.beginline(h.enumColours.red, 0)
                graph.line(x, ymin)
                graph.line(x, ymax)
                
            def _addVerticalLines(graph, ymin, ymax):
                for schwann in self.schwannSecsList:
                    schwann_start = h.distance(schwann(0))
                    schwann_end = h.distance(schwann(1))
                    _addOneVerticalLine(graph, schwann_start, ymin, ymax)
                    _addOneVerticalLine(graph, schwann_end, ymin, ymax)
                    
            if not self.isUseRealBiophysOrTestSines:
                if graphs[-2]:
                    _addVerticalLines(graphs[-2], imin, imin + irange)
                if graphs[-1]:
                    _addVerticalLines(graphs[-1], omin, omin + orange)
                    
                    
        if self.isUseRealBiophysOrTestSines:
            
            brushIdx = 1
            mbottom1 = -80  # mV
            mtop1 = 70      # mV
            wleft = 1300
            wwidth = 735
            wheight = 175
            
            graph = None
            if self._presParams.isDraw[4]:
                # Creating Graph for Voltage in 3 points along axon (mV)
                graph = h.Graph(0)
                mleft = 0           # ms
                mright = h.tstop    # ms
                graph.size(mleft, mright, mbottom1, mtop1)
                graph.view(mleft, mbottom1, mright - mleft, mtop1 - mbottom1, wleft, 200, wwidth, wheight)
                h.graphList[0].append(graph)
                graph.addexpr(    'soma_ref.o(0).sec.v(.5)',                       h.enumColours.red,    brushIdx)
                if self.isTransformed:
                    middleIdx = len(self.axonUnderSchwannSecsList) / 2
                    graph.addexpr('_pysec.axonUnderSchwann[%i].v(.5)' % middleIdx, h.enumColours.orange, brushIdx)
                    graph.addexpr(f'_pysec.{self._axonLastSec}.v(1)',              h.enumColours.blue,   brushIdx)
                else:
                    graph.addexpr('_pysec.axon.v(.5)',                             h.enumColours.orange, brushIdx)
                    graph.addexpr('_pysec.axon.v(1)',                              h.enumColours.blue,   brushIdx)
                _addXLabel(graph, 't (ms)')
                _addCentralLabel(graph, 'Voltage (mV)     ')
            graphs.append(graph)
            
            startSegm = self._baseAxonHelper.soma(self._baseAxonHelper.somaConnectionPoint)
            
            arc = 1
            if self._baseAxonHelper.axonTerminalSecsList:
                middleIdx = int(len(self._baseAxonHelper.axonTerminalSecsList) / 2)
                endSegm = self._baseAxonHelper.axonTerminalSecsList[middleIdx](arc)
            else:
                if self.isTransformed:
                    endSegm = self._axonLastSec(arc)
                else:
                    endSegm = self._baseAxonHelper.axon(arc)
                    
            graph = None
            if self._presParams.isDraw[5]:
                # Creating Graph for Equilibrium potential for K+ (mV)
                graph = h.Graph(0)
                mleft = h.distance(startSegm)   # um
                mright = h.distance(endSegm)    # um
                mbottom2 = -80                  # mV
                mtop2 = -60                     # mV
                graph.size(mleft, mright, mbottom2, mtop2)
                graph.view(mleft, mbottom2, mright - mleft, mtop2 - mbottom2, wleft, 500, wwidth, wheight)
                h.flush_list.append(graph)
                rvp = h.RangeVarPlot('ek', startSegm, endSegm)
                rvp.origin(mleft)
                graph.addobject(rvp, h.enumColours.red, brushIdx)
                _addXLabel(graph, 'Distance (um)')
                _addCentralLabel(graph, 'Equilibrium potential for K+ (mV)')
            graphs.append(graph)
            
            graph = None
            if self._presParams.isDraw[6]:
                # Creating Graph for Voltage along axon (mV)
                graph = h.Graph(0)
                mleft = h.distance(startSegm)   # um
                mright = h.distance(endSegm)    # um
                graph.size(mleft, mright, mbottom1, mtop1)
                graph.view(mleft, mbottom1, mright - mleft, mtop1 - mbottom1, wleft, 800, wwidth, wheight)
                h.flush_list.append(graph)
                rvp = h.RangeVarPlot('v', startSegm, endSegm)
                rvp.origin(mleft)
                graph.addobject(rvp, h.enumColours.red, brushIdx)
                _addXLabel(graph, 'Distance (um)')
                _addCentralLabel(graph, 'Voltage along axon (mV)')
            graphs.append(graph)
            
        self._graphs = graphs
        
    def callAnimSavePrintHelperOnPreContinue(self):
        
        self._animSavePrintHelper.onPreContinue(self._graphs, self._shells, self._k,)
        
    # ----- End of Graph-s -----
    
    
    # ----- Start of other -----
    
    def colourSectsAndAddLabels(self, shape, isCalledJustBeforeShowingCellBuilder, isShowAxonOnly):
        
        axonToTransformColour = h.enumColours.red
        otherColour = h.enumColours.grey
        y = 0.9
        dy = 0.05
        
        if not isCalledJustBeforeShowingCellBuilder:
            if not isShowAxonOnly:
                # Non-selectable sections outside axon (part 1)
                shape.color_all(otherColour)
                
            # Selectable section within axon
            if not self.isTransformed and self._baseAxonHelper.axon is not None:    # self._baseAxonHelper.axon is None when we enter the "Draw by hand" mode for axon
                self._setSecsColourAndAddLabel(shape, 'Axon: Region to transform', axonToTransformColour, y, [self._baseAxonHelper.axon])
                y -= dy
        else:
            # !! BUG 1: when working with CellBuild-er, entire cell is shown in black rather than grey ...
            # !! BUG 2: ... and the new added sections are shown in black rather than red
            
            # Selectable sections within axon (will be added later)
            shape.color_all(h.enumColours.red)
            self._setSecsColourAndAddLabel(shape, 'Axon: Region to transform', axonToTransformColour, y, [])
            y -= dy
            
            if not isShowAxonOnly:
                # Non-selectable sections outside axon (part 1)
                for sec in h.allsec():
                    shape.color(otherColour, sec=sec)
                    
        # Non-selectable sections within axon
        if self.isTransformed:
            self._setSecsColourAndAddLabel(shape, 'Axon: Transformed region', h.enumColours.violet, y, self.axonTreeSecsWithTerms)
            y -= dy
        if self._baseAxonHelper.axonTerminalSecsList:
            self._setSecsColourAndAddLabel(shape, 'Axon: Terminals', h.enumColours.orange, y, self._baseAxonHelper.axonTerminalSecsList)
            y -= dy
            
        if not isShowAxonOnly:
            # Non-selectable sections outside axon (part 2)
            self._setSecsColourAndAddLabel(shape, 'Not Axon', otherColour, y, [])
            
    # !! use "del obj" ?
    def cleanup(self, isCleanUpRxd, isDeleteAllModifGeomAxonSecs):
        
        if hasattr(self, '_plotShape'):
            self._plotShape.unmap()
            del self._plotShape
            
        if hasattr(self, '_graphs'):
            for graph in self._graphs:
                if graph:
                    h.removeItemFromList(h.flush_list, graph)
                    h.removeItemFromList(h.graphList[0], graph)
                    graph.unmap()
            del self._graphs
            
        # Dereferencing RxD objects now to avoid errors in "initRxDStaff" when we'll call it downstream
        
        if isCleanUpRxd:
            self._diffusions = None     # rxd.MultiCompartmentReaction
            self._k = None              # rxd.Species
            self._shells = None         # rxd.Region (looks like dereferencing can be skipped, just for sanity)
            
            if hasattr(self, 'procAdvanceHelper'):
                self.procAdvanceHelper.cleanup()    # rxd.node.Node1D
                
        self._animSavePrintHelper.cleanup(isCleanUpRxd)     # rxd.Species
        
        if not isDeleteAllModifGeomAxonSecs or not self.isTransformed:
            return
            
        # Deleting all sections of the transformed axon
        self._cleanupSecContainersAndBiophysComps()
        
        # Sections are destroyed, so JSON must be re-imported on next initBiophysics call
        self._isBiophysFromJsonApplied = False
        
        self.isTransformed = False
        self._onMyelStatusChanged(False)
        
    # !! code dup. with "prepareSecListsForBaseGeometryAxon"
    def _cleanupSecContainersAndBiophysComps(self):
        
        self.AISPs = None
        self.AISDs = None
        
        self.axonBeforeFirstSchwannSecOrNone = None
        self.axonUnderSchwannSecsList = []
        self.axonNodeOfRanvierSecsList = []
        self.axonAfterLastSchwannSecOrNone = None
        self.insulatorSecsList = []
        if hasattr(self, 'schwannSecsList'):
            self.schwannSecsList.clear()        # !! don't replace with "=None" or "=[]" because h.topology would show them despite the cleanup
            
        self._axonFirstSec = None
        self._axonLastSec = None
        
        self._axonUnderSchwannSecToSchwannSecDict = dict()
        
        self.axonTrunkSecsExceptTerms = []
        self._axonTrunkSecsWithTerms = []
        self._axonTreeSecsExceptTerms = []
        self.axonTreeSecsWithTerms = []
        
        
        self._axonBiophysCompsHelper.onAxonDeleted()
        
    # ----- End of other -----
    