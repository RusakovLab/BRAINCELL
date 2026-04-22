
# !! BUGs:
#   * see the comment in simDismissHandler
#   * enable outside-in diffusion, open and work with this sim => the mech "OutsideInDiffHelper" is not inserted into the newly created sections (axon and soma)
#   * there are some solitons moving in the wrong direction (from axon bifurcation to soma)
#   * change "Trunk params", click "init", remove myelin => "Trunk params" are reset to defaults
#   * see 2 bug comments in _core.colourSectsAndAddLabels
#   * in "Draw by hand" mode for axon geometry, if user draws a tree, it's merged into a single section
#   * "test sines", axon drawn by hand, soma is overwritten => we don't restore biophysics (particularly, "pas") in the new "soma"
#   * in _core, enable warning with "h.beih.importForSim(biophysJsonFileName, 1)" => the warning looks wrong
#   * switching real biophys / test sines doesn't hide the Graph-s
#   * start with external simulation "boosting"; start this sim => error "pas mechanism not inserted in section AISPs"

# !! test carefully:
#   * what happens when there is a gap junction PP (or its pointer) on axon or soma, and we delete this section; can this cause Segmentation errors?
#   * what happens when user exits sim and opens again

# !! TODOs:
#   * soliton velocity measurement
#   * "Equilibrium potential" and "Volatage along axon" Graph-s start from soma in contrast to "current in axon" and "conc on axon" Graph-s
#   * maybe update "preRun" not to hide/show the main widget in case of "init" click
#   * there are 2 not impl. scenarios in CellBuildHelper (see analyzeSecNamesAndCheckForNotImplScenario)

# !! minor:
#   * axon validation and more accurate extraction of the bifurcation in the imported axon and the one drawn by hand
#   * the msg "Axon length before transformation: ..." is printed unnecessarily when toggling between "Myelin sheath: Deploy / Scalp" in "Myelin: REMOVED" state
#   * when a Schwann section contains only one segment, the range var plots animating "ik" and "ko" look empty (they cannot show only 1 pt vs distance)
#   * for the PlotShape from SimMyelinatedAxonCore, maybe show in red not one, but all soma sections
#   * when using "zebra", maybe make it possible to choose the points "schwann1_start" and "schwannN_end" using the PlotShape
#   * remove myelin, init, switch to test sines, init => "Topology before axon transformation" shows two axons; UPD: if we call "topology()" again, it shows one

# !! mini BUG (FIXED):
#   * edit biophysics, then switch to "test sines", then switch back to "real biophysics" => the biophysics is reset to defaults
#     FIX: initBiophysics now skips JSON re-import if _isBiophysFromJsonApplied is True;
#          switching to test sines warns user and resets the flag since sections are destroyed

# !! clamps:
#   * maybe it makes sense to unify the clamps logic between MainUI, this sim and other sims with some new Clamp Manager
#   * how about VClamp, VClamp Family, OClamp, IClampSin, IClampNoise etc. ?
#   * maybe disallow deploying IClamp and SEClamp into soma centre at the same time (but this looks like the logic for IClampHelper and SEClampHelper rather than SimMyelinatedAxon)

# !! low priority:
#   * while in "Draw by hand" mode for axon geometry, click "init & run" => error; UPD: we've added a warning in CellBuildHelper._auxBoxOrNone footer
#   * for "Axonated/Fast Spiking Basket cells Somogyi_1.hoc" RxD initialization takes too long even when decreasing nseg and L


from SimABCs import *

from neuron import h

from Helpers.PresentationParams import PresentationParams
from Helpers.BasicEnums import EnumAxonGeometry, EnumMyelSheath
from Helpers.DirtyStatesHelper import DirtyStatesHelper, EnumParamCats
from Helpers.MyelRegionHelper import MyelRegionHelper, EnumMyelRegion
from Helpers.AxonBiophysCompsHelper import AxonBiophysCompsHelper
from Helpers.BaseAxonHelper import BaseAxonHelper
from Helpers.CellBuildHelper import CellBuildHelper
from Helpers.AnimSavePrintHelper import AnimSavePrintHelper
from Helpers.BiophysExportHelper import BiophysExportHelper

from SimCore import SimMyelinatedAxonCore

import GuiPrimitiveWrappers as bc

import MsgWarnHelperWrappers as mwhw
from OtherInterModularUtils import codeContractViolation


h.load_file('Sims/Neuron/SimMyelinatedAxon/HocCode/ParamsHelper.hoc')


class SimMyelinatedAxon(RequiresAltRunControl, UsesCustomProcAdvance, Simulation):
    
    _def_tstop = 500    # ms
    _def_dt = 0.01      # ms
    
    _isShowAxonOnly = False
    _enumAxonGeometry = EnumAxonGeometry.imported
    _enumMyelSheath = EnumMyelSheath.deploy
    _isUseRealBiophysOrTestSines = True
    _isInsertIClamp = True
    _isInsertSEClamp = False
    
    # We'll select it even when "self._enumMyelSheath == EnumMyelSheath.remove" or "self._myelRegionHelper.enumMyelRegion != EnumMyelRegion.drawnByHand"
    # just because the default menu tool "Section" allows selection and highlights the segms in red unnecessarily
    _menuToolName = 'Draw Myelinated Region'
    
    _myelinStatusStr = h.ref('')
    
    _isProgrammaticCall = False
    _isCellBuildHelperShown = False     # !! maybe get rid of this since we've added a warning in CellBuildHelper._auxBoxOrNone footer
    _wasManagerOfBiophysicsShown = False
    
    _predefAxonFallbackMsg = f"We'll use a predefined axon instead."
    
    # Data members added in the ctor:
    #   _presParams, _dirtyStatesHelper, _paramsHelper, _axonBiophysCompsHelper, _baseAxonHelper, _myelRegionHelper, _cellBuildHelper, _animSavePrintHelper, _core
    
    # Data members added in "show":
    #   _isImportedAxonInvalid
    #   _mainBox, _trunkParamsDeck, _sheathParamsDeck, _shape, _myelinParamsDeck1, _myelinParamsDeck2, _myelinParamsDeck3, _biophysAndClampsParamsDeck, _testBiophysParamsDeck
    
    # Data member added in "onCellBuilderDoneOrCancel":
    #   _isAxonDrawnByHandInvalid
    
    
    def __init__(self):
        
        # !! maybe we can move some calls of the ctors below to the class level
        
        self._presParams = PresentationParams()
        
        self._dirtyStatesHelper = DirtyStatesHelper()
        
        self._paramsHelper = h.SimMyelinatedAxonParamsHelper(self, self._dirtyStatesHelper)
        
        self._axonBiophysCompsHelper = AxonBiophysCompsHelper()
        
        self._baseAxonHelper = BaseAxonHelper(self._paramsHelper, self._axonBiophysCompsHelper)
        
        self._myelRegionHelper = MyelRegionHelper(self._paramsHelper, self._baseAxonHelper)
        
        self._cellBuildHelper = CellBuildHelper(self._baseAxonHelper, self)
        
        self._animSavePrintHelper = AnimSavePrintHelper(self._presParams, self._baseAxonHelper)
        
        self._core = SimMyelinatedAxonCore(self._paramsHelper, self._enumMyelSheath, self._isUseRealBiophysOrTestSines, self._baseAxonHelper, self._myelRegionHelper, self._axonBiophysCompsHelper, self._presParams, self._animSavePrintHelper, self.onMyelStatusChanged)
        
        self._presParams.setSaveTxtFileCheckBoxHandler(self._animSavePrintHelper.saveTxtFileCheckBoxHandler)
        
        self._biophysExportHelper = BiophysExportHelper(self._paramsHelper, self._presParams)
        self._presParams.setExportBiophysCheckBoxHandler(self._biophysExportHelper.exportCheckBoxHandler)
        
        self._axonBiophysCompsHelper.setSecContainers(self._baseAxonHelper, self._core)
        self._animSavePrintHelper.setModifAxonSecContainer(self._core)
        
        self._dirtyStatesHelper.onParamChange(EnumParamCats.modifGeom)
        
    def preShowCheck(self):
        
        return False
        
    def show(self, isFirstShow, isCalledFromSelf=False):
        
        if isFirstShow:
            if self._enumAxonGeometry != EnumAxonGeometry.imported:
                codeContractViolation()
            self._isImportedAxonInvalid = self._baseAxonHelper.consumeImportedAxonOrAxonDrawnByHand(True)
            self._ifAxonInvalidThenWarnAndSwitchToPredefAxon(False)     # --> self._enumAxonGeometry
            
            self._removeElectrodeAndSetUpDefaultClampParams()
            
        elif self._enumAxonGeometry == EnumAxonGeometry.drawnByHand and self._isAxonDrawnByHandInvalid:
            self._ifAxonInvalidThenWarnAndSwitchToPredefAxon(False)     # --> self._enumAxonGeometry
            
        with bc.VBox('Axon simulation', 400, 180) as self._mainBox:
            
            with bc.HBox():
                
                with bc.VBox():
                    with bc.VBox():
                        with bc.Panel():
                            h.xlabel('Axon trunk params:')
                        with bc.Deck() as self._trunkParamsDeck:
                            self._createCannotEditVBox()
                            with bc.Panel():
                                self._paramsHelper.populateTrunkParamsPanel()
                                h.xlabel('')
                    with bc.VBox():
                        with bc.Panel():
                            h.xlabel('Axon sheath params:')
                        with bc.Deck() as self._sheathParamsDeck:
                            self._createCannotEditVBox()
                            with bc.VBox(panel=True):
                                self._paramsHelper.populateSheathParamsPanel()
                                h.xlabel('')
                                
                with bc.VBox('', 1, 1, 250, 340):
                    with bc.Panel():
                        h.xlabel('Geometry and sheath:')
                    with bc.HBox():
                        with bc.VBox(panel=True):
                            h.xlabel('Axon geometry:')
                            h.xradiobutton('Use imported', lambda: self._axonGeomRadioButtonHandler(EnumAxonGeometry.imported), self._enumAxonGeometry == EnumAxonGeometry.imported)
                            h.xradiobutton('Use predefined', lambda: self._axonGeomRadioButtonHandler(EnumAxonGeometry.predefined), self._enumAxonGeometry == EnumAxonGeometry.predefined)
                            h.xradiobutton('Draw by hand', lambda: self._axonGeomRadioButtonHandler(EnumAxonGeometry.drawnByHand), self._enumAxonGeometry == EnumAxonGeometry.drawnByHand)
                        with bc.VBox(panel=True):
                            h.xlabel('Myelin sheath:')
                            h.xradiobutton('Deploy', lambda: self._myelSheathRadioButtonHandler(EnumMyelSheath.deploy), self._enumMyelSheath == EnumMyelSheath.deploy)
                            h.xradiobutton('Scalp', lambda: self._myelSheathRadioButtonHandler(EnumMyelSheath.scalp), self._enumMyelSheath == EnumMyelSheath.scalp)
                            h.xradiobutton('Remove', lambda: self._myelSheathRadioButtonHandler(EnumMyelSheath.remove), self._enumMyelSheath == EnumMyelSheath.remove)
                    self._shape = h.Shape()
                    self._shape.menu_tool(self._menuToolName, self._mouseEventsHandler)
                    self._shape.exec_menu(self._menuToolName)   # !! maybe get rid of this call in favour of radiobutton handlers called below
                    with bc.HBox():
                        with bc.Panel():
                            h.xbutton('Start simulation', self._startSimButtonHandler)
                            self._updateGuiOnMyelStatusChanged(self._core.isTransformed)    # !! calling it here just to reserve enough horizontal space for the panel
                            # self._myelinStatusStr = '********'
                            h.xvarlabel(self._myelinStatusStr)
                        with bc.Panel():
                            h.xlabel('Show:')
                            h.xradiobutton('Entire cell', lambda: self._whatToShowRadioButtonHandler(False), not self._isShowAxonOnly)
                            h.xradiobutton('Axon only', lambda: self._whatToShowRadioButtonHandler(True), self._isShowAxonOnly)
                            
                with bc.Deck(emptyPanel=True) as self._myelinParamsDeck1:
                    with bc.VBox():
                        with bc.Panel():
                            h.xlabel('Myelin params:')
                        with bc.Deck() as self._myelinParamsDeck2:
                            self._createCannotEditVBox()
                            with bc.VBox():
                                with bc.Panel():
                                    h.xlabel('Myelinated region:')
                                    h.xradiobutton('Use entire axon', lambda: self._myelRegionRadioButtonHandler(EnumMyelRegion.entireAxon), self._myelRegionHelper.enumMyelRegion == EnumMyelRegion.entireAxon)
                                    h.xradiobutton('Use zebra', lambda: self._myelRegionRadioButtonHandler(EnumMyelRegion.zebra), self._myelRegionHelper.enumMyelRegion == EnumMyelRegion.zebra)
                                    h.xradiobutton('Draw by hand', lambda: self._myelRegionRadioButtonHandler(EnumMyelRegion.drawnByHand), self._myelRegionHelper.enumMyelRegion == EnumMyelRegion.drawnByHand)
                                    h.xlabel('')
                                with bc.Deck(emptyPanel=True) as self._myelinParamsDeck3:
                                    self._paramsHelper.populateMyelinParamsDeck()
                                    # self._myelinParamsDeck3.flip_to(*)    # Will be done downstream in self._myelRegionRadioButtonHandler
                            # self._myelinParamsDeck2.flip_to(*)    # Will be done downstream in self.onMyelStatusChanged
                    # self._myelinParamsDeck1.flip_to(*)    # Will be done downstream in self._myelSheathRadioButtonHandler
                    
            with bc.HBox():
                
                with bc.VBox():
                    with bc.Panel():
                        h.xlabel('Biophysics and clamps:')
                    with bc.VBox():
                        with bc.Panel():
                            h.xradiobutton('Use real biophysics', lambda: self._biophysRadioButtonHandler(True), self._isUseRealBiophysOrTestSines)
                            h.xradiobutton('Use test sines', lambda: self._biophysRadioButtonHandler(False), not self._isUseRealBiophysOrTestSines)
                        with bc.Deck() as self._biophysAndClampsParamsDeck:
                            with bc.Deck() as self._testBiophysParamsDeck:
                                with bc.Panel():
                                    self._paramsHelper.populateTestBiophysParamsPanel(False)
                                with bc.Panel():
                                    self._paramsHelper.populateTestBiophysParamsPanel(True)
                                # self._testBiophysParamsDeck.flip_to(*)    # Will be done downstream in self._biophysRadioButtonHandler
                            with bc.Panel():
                                h.xlabel('')
                                h.xbutton('Show Manager of Biophysics', self._showManagerOfBiophysicsButtonHandler)
                                h.xlabel('')
                                h.xlabel('Clamps in soma:')
                                h.xcheckbox('Insert IClamp', (self, '_isInsertIClamp'), self._isInsertIClampCheckBoxHandler)
                                h.xcheckbox('Insert SEClamp', (self, '_isInsertSEClamp'), self._isInsertSEClampCheckBoxHandler)
                            # self._biophysAndClampsParamsDeck.flip_to(*)   # Will be done downstream in self._biophysRadioButtonHandler
                            
                with bc.VBox():
                    with bc.Panel():
                        h.xlabel('Diffusion and conc params:')
                    with bc.VBox(panel=True):
                        self._paramsHelper.populateDiffAndConcParamsPanel()
                        h.xlabel('')
                    with bc.Panel():
                        h.xlabel('Presentation params (part 1):')
                    with bc.VBox(panel=True):
                        self._presParams.populatePresParamsPart1Panel()
                        self._paramsHelper.populatePresParamsPanel()
                        
                with bc.VBox():
                    with bc.Panel():
                        h.xlabel('Presentation params (part 2):')
                    with bc.VBox():
                        self._presParams.populatePresParamsPart2Panel()
                        
            self._mainBox.dismiss_action(self._dismissHandler)
            
        isEnumMyelSheathInDeployScalp = self._isEnumMyelSheathInDeployScalp()
        
        if isFirstShow or self._isAxonDrawnByHandInvalid:
            self._isProgrammaticCall = True
            self._axonGeomRadioButtonHandler(self._enumAxonGeometry)
            self._myelSheathRadioButtonHandler(self._enumMyelSheath)
            if isEnumMyelSheathInDeployScalp:
                self._myelRegionRadioButtonHandler(self._myelRegionHelper.enumMyelRegion)
            self._biophysRadioButtonHandler(self._isUseRealBiophysOrTestSines)
            self._isProgrammaticCall = False
            
        if isFirstShow:
            h.tstop = self._def_tstop
            h.dt = self._def_dt
        else:
            self._flipDecksDepOnIsUseRealBiophysOrTestSines()
            self._flipDecksDepOnEnumMyelSheath()
            isShow = not self._core.isTransformed
            self._showOrHideTrunkAndSheathParams(isShow)
            self._showOrHideMyelinParams(isShow)
            if isEnumMyelSheathInDeployScalp:
                self._flipSheathParamsDecks()
                
            if not isCalledFromSelf and self._isUseRealBiophysOrTestSines and not self._isAxonDrawnByHandInvalid:
                self._isProgrammaticCall = True
                self._deployClampsIfChecked()
                self._isProgrammaticCall = False
                
            if not self._core.isTransformed:
                if isEnumMyelSheathInDeployScalp:
                    self._myelRegionHelper.showMyelinMarkers(self._shape)
                    
                self._axonBiophysCompsHelper.onBaseAxonCreated()
                
        self._updateShape()
        
    def preRun(self, isInitOnly):
        
        isEnumMyelSheathInDeployScalp = self._isEnumMyelSheathInDeployScalp()
        
        if isEnumMyelSheathInDeployScalp:
            isCancel = self._validateBeforeTransformation()
            if isCancel:
                return True
                
        self._dismissHandler()
        
        dirtyParamCat = self._getDirtyParamCat()
        
        self._core.cleanup(dirtyParamCat >= EnumParamCats.rxd, dirtyParamCat >= EnumParamCats.modifGeom)
        
        if dirtyParamCat >= EnumParamCats.baseGeom:
            self._core.createBaseGeomAxon(self._enumAxonGeometry)
            if self._enumMyelSheath == EnumMyelSheath.remove:
                self._core.prepareSecListsForBaseGeometryAxon()
                
        if isEnumMyelSheathInDeployScalp:
            if dirtyParamCat >= EnumParamCats.modifGeom:
                self._myelRegionHelper.destroyPPMs()
                self._core.createModifiedGeometryAxon()
            self._core.showPlotShapeIfNeeded()
            
        if dirtyParamCat >= EnumParamCats.biophys:
            self._core.initBiophysics()
            
        # Export biophysics if checkbox is checked
        simSettings = {
            'Axon geometry':       self._enumAxonGeometry.name,
            'Myelin sheath':       self._enumMyelSheath.name,
            'Myelinated region':   self._myelRegionHelper.enumMyelRegion.name,
            'Biophysics':          'real biophysics' if self._isUseRealBiophysOrTestSines else 'test sines',
            'IClamp inserted':     self._isInsertIClamp,
            'SEClamp inserted':    self._isInsertSEClamp,
        }
        self._biophysExportHelper.exportOnPreRun(simSettings)
            
        self._dirtyStatesHelper.dirtyParamCat = min(dirtyParamCat, EnumParamCats.rxd)
        
        self._core.callAnimSavePrintHelperOnPreRun()
        
        if isInitOnly:
            mainBoxCopy = self._mainBox     # !! preventing sporadic "Segmentation violation" (presumably)
            self.show(False, True)
            return False
            
        isCancel = self.preContinue()
        if isCancel:
            return True
            
        # Without this, the very first animated/saved/printed frame would be t=dt rather than t=0 when user clicks "Init & Run"
        self._animSavePrintHelper.makeSureZeroTimeFrameConsumed()
        
        return False
        
    def preContinue(self):
        
        h.dismissIfNotNil(h.mechManagerMainWidget)
        
        self._dismissHandler()
        
        dirtyParamCat = self._getDirtyParamCat()
        
        if dirtyParamCat >= EnumParamCats.rxd:
            self._core.initRxDStaff()
            
        self._dirtyStatesHelper.onAllClear()
        
        self._core.makeGraphsIfNeeded()
        
        self._core.callAnimSavePrintHelperOnPreContinue()
        
        # Without this, the very first animated/saved/printed frame would be t=dt rather than t=0 when user clicks "Init" and then "Continue"
        self._animSavePrintHelper.makeSureZeroTimeFrameConsumed()
        
        return False
        
    def advance(self):
        
        h.fadvance()
        
        if hasattr(self._core, 'procAdvanceHelper') and self._core.procAdvanceHelper:
            self._core.procAdvanceHelper.onAdvance()
            
        self._animSavePrintHelper.onAdvance()
        
    def postRun(self):
        
        self._core.dismissMechManagerAndScheduleRescan()
        
        self._animSavePrintHelper.onPostRun()
        
        mainBoxCopy = self._mainBox     # !! preventing sporadic "Segmentation violation" (presumably)
        self.show(False, True)
        
        if self._presParams.isSave:
            # Showing it now not to be obstructed by the main widget
            self._animSavePrintHelper.showTxtFileSavedMsg()
            
    def onBaseAxonParamChanged(self, isLenChanged, isNsegChanged):
        
        isLenChanged = bool(isLenChanged)
        isNsegChanged = bool(isNsegChanged)
        
        self._core.cleanup(True, True)
        
        self._core.onBaseGeomAxonChanged(isLenChanged, isNsegChanged)
        if self._enumAxonGeometry != EnumAxonGeometry.imported:
            for terminal in self._baseAxonHelper.axonTerminalSecsList:
                terminal.diam = self._paramsHelper.diam_axon
                
        self.removeMyelinMarkers(isNsegChanged)
        
        if self._isEnumMyelSheathInDeployScalp():
            
            self._myelRegionHelper.showMyelinMarkers(self._shape)
            
            self._dirtyStatesHelper.onParamChange(EnumParamCats.modifGeom)
            
    def removeMyelinMarkers(self, isForgetOldDrawing):
        
        if isForgetOldDrawing:
            self._myelRegionHelper.forget()
        else:
            self._myelRegionHelper.destroyPPMs()
            
        if not self._isProgrammaticCall:
            self._updateShape()
            
    def onMyelStatusChanged(self, isTransformed):
        
        if isTransformed:
            self._axonBiophysCompsHelper.onModifGeomAxonCreated()
            
        self._updateGuiOnMyelStatusChanged(isTransformed)
        
    def drawMyelinZebra(self):
        
        self._myelRegionHelper.showMyelinMarkers(self._shape)
        
    def onCellBuilderDoneOrCancel(self, isCancel):
        
        self._onDoneOrCancelInCellBuildHelper(isCancel)
        
        if isCancel:
            self._isAxonDrawnByHandInvalid = True
        else:
            self._isAxonDrawnByHandInvalid = self._baseAxonHelper.consumeImportedAxonOrAxonDrawnByHand(False)
            
        self._ifAxonInvalidThenWarnAndSwitchToPredefAxon(isCancel)      # --> self._enumAxonGeometry
        
        self._core.createBaseGeomAxon(self._enumAxonGeometry)
        
        self._deleteModifGeomAxonAndCreateBaseGeomAxonEpilogue()
        
        self._axonGeomRadioButtonHandlerEpilogue()
        
    def simDismissHandler(self):
        
        wasCellBuildHelperShown = self._isCellBuildHelperShown
        
        self._dismissHandler()
        
        if not wasCellBuildHelperShown:
            if self._isUseRealBiophysOrTestSines:
                self._removeClampsIfChecked()
                
            if not self._core.isTransformed:
                # Doing this so user can proceed with other sims that import biophysics from JSON files
                # !! BUG: error here if user closes the widget with "x" in "draw by hand" mode for axon, then unchecks the sim button
                self._axonBiophysCompsHelper.restoreStdAxonComp()
                
        self._core.cleanup(True, False)
        self._dirtyStatesHelper.onParamChange(EnumParamCats.rxd)
        
        self._myelRegionHelper.destroyPPMs()
        
    # All next staff is private
    
    
    def _mouseEventsHandler(self, eventType, x, y, keystate):
        
        if not self._myelRegionHelper.enumMyelRegion == EnumMyelRegion.drawnByHand:
            return
            
        isTransformationRequired = self._isEnumMyelSheathInDeployScalp()
        
        if not isTransformationRequired or self._myelRegionHelper.enumMyelRegion != EnumMyelRegion.drawnByHand:
            if isTransformationRequired and self._myelRegionHelper.enumMyelRegion == EnumMyelRegion.zebra and eventType == h.enumMouseEvents.press:
                h.mwh.showNotImplementedWarning()
            return
            
        if self._core.isTransformed:
            if eventType == h.enumMouseEvents.press:
                h.mwh.showWarningBox('Not available when the myelin is deployed.')
            return
            
        if eventType in [h.enumMouseEvents.press, h.enumMouseEvents.dragging]:
            
            # Make the nearest section currently accessed
            self._shape.nearest(x, y)
            
            arc = self._shape.push_selected()
            sec = h.cas()
            h.pop_section()
            
            if sec != self._baseAxonHelper.axon:
                return
                
            self._myelRegionHelper.onMousePressOrDragging(self._shape, arc)
            
        elif eventType == h.enumMouseEvents.release:
            
            self._myelRegionHelper.onMouseRelease(self._shape)
            
        else:
            codeContractViolation()
            
        self._dirtyStatesHelper.onParamChange(EnumParamCats.modifGeom)
        
    def _axonGeomRadioButtonHandler(self, enumAxonGeometry):
        
        self._enumAxonGeometry = enumAxonGeometry
        
        if self._isCellBuildHelperShown and not self._isProgrammaticCall:
            self._onDoneOrCancelInCellBuildHelper(True)
            
        if self._enumAxonGeometry != EnumAxonGeometry.drawnByHand:
            self._ifAxonInvalidThenWarnAndSwitchToPredefAxon(False)     # --> self._enumAxonGeometry
            
        isCancel = self._deleteModifGeomAxonAndCreateBaseGeomAxon(False)
        if isCancel:
            return
            
        self._showOrHideTrunkAndSheathParams(True)
        
        if self._isProgrammaticCall:
            return
            
        self._axonGeomRadioButtonHandlerEpilogue()
        
    def _myelSheathRadioButtonHandler(self, enumMyelSheath):
        
        enumMyelSheath_old = self._enumMyelSheath
        
        self._enumMyelSheath = enumMyelSheath
        self._core.enumMyelSheath = enumMyelSheath
        
        self._flipDecksDepOnEnumMyelSheath()
        
        if self._isCellBuildHelperShown:
            return
            
        if self._isEnumMyelSheathInDeployScalp():
            
            if self._isProgrammaticCall:
                return
                
            self._showOrHideMyelinParams(False)
            
            if self._isEnumMyelSheathInDeployScalp(enumMyelSheath_old):
                isCancel = self._deleteModifGeomAxonAndCreateBaseGeomAxon(True)
                if isCancel:
                    return
                    
            self._myelRegionRadioButtonHandler(self._myelRegionHelper.enumMyelRegion)
            
            dirtyParamCat = EnumParamCats.modifGeom
            
        elif enumMyelSheath == EnumMyelSheath.remove:
            self._showOrHideTrunkAndSheathParams(True)
            
            self._showOrHideMyelinParams(True)
            
            if self._isProgrammaticCall:
                return
                
            isCancel = self._deleteModifGeomAxonAndCreateBaseGeomAxon(True)
            if isCancel:
                return
                
            self.removeMyelinMarkers(False)
            
            self._shape.exec_menu(self._menuToolName)
            
            dirtyParamCat = EnumParamCats.baseGeom
            
        else:
            codeContractViolation()
            
        self._dirtyStatesHelper.onParamChange(dirtyParamCat)
        
    def _myelRegionRadioButtonHandler(self, enumMyelRegion):
        
        self._myelRegionHelper.enumMyelRegion = enumMyelRegion
        
        self._flipSheathParamsDecks()
        
        self._core.cleanup(True, True)
        
        self.removeMyelinMarkers(False)
        
        self._myelRegionHelper.showMyelinMarkers(self._shape)
        
        self._shape.exec_menu(self._menuToolName)
        
        if not self._isProgrammaticCall:
            self._dirtyStatesHelper.onParamChange(EnumParamCats.modifGeom)
            
    def _removeMyelinButtonHandler(self):
        
        if self._wasManagerOfBiophysicsShown:
            isCancel = not h.boolean_dialog('This operation will discard all changes to biophysics made with Manager of Biophysics. Do you want to proceed?', 'Yes', 'No')
            if isCancel:
                return
                
        self._core.cleanup(True, True)
        
        self._isProgrammaticCall = True
        self._axonGeomRadioButtonHandler(self._enumAxonGeometry)
        self._myelRegionRadioButtonHandler(self._myelRegionHelper.enumMyelRegion)
        self._isProgrammaticCall = False
        
        self._dirtyStatesHelper.onParamChange(EnumParamCats.modifGeom)
        
        self._updateShape()
        
        self._wasManagerOfBiophysicsShown = False
        self._core._userHasEditedBiophys = False
        
    def _biophysRadioButtonHandler(self, isUseRealBiophysOrTestSines):
        
        # Warn user if switching to test sines will destroy their biophysics edits
        if not isUseRealBiophysOrTestSines and self._core._userHasEditedBiophys:
            isCancel = not h.boolean_dialog(
                'Switching to test sines will recreate all sections and discard your biophysics edits made in Manager of Biophysics. Do you want to proceed?',
                'Yes', 'No')
            if isCancel:
                return
        
        self._isUseRealBiophysOrTestSines = isUseRealBiophysOrTestSines
        
        self._core.isUseRealBiophysOrTestSines = isUseRealBiophysOrTestSines
        
        self._flipDecksDepOnIsUseRealBiophysOrTestSines()
        
        if self._isUseRealBiophysOrTestSines:
            self._deployClampsIfChecked()
        elif not self._isProgrammaticCall:
            self._removeClampsIfChecked()
            
        if not self._isProgrammaticCall:
            
            # !! ideally, we would always use "biophys" here, but have to use "baseGeom" as a workaround to simplify the code in self._core.initBiophysics
            #    avoiding explicit uninsertion of the mechs after switching from "real biophysics" to "test sines";
            #    details:
            #    * without the uninsertion, "i_cap", "i_pas" and "ina" become NaN-s resulting in CCV in altRunControlWidget.initAndRunHandler -> MechComp.analyzeMechInhomogeneityCore;
            #    * but when trying to uninsert in different ways, we hit these three errors which look like NEURON bugs/features:
            #      (1) TypeError: Cannot access capacitance (NEURON type 312) directly.
            #      (2) ValueError: argument not a density mechanism name
            #      (3) Assertion failed: file D:/a/nrn/nrn/src/nrnoc/treeset.cpp, line 548
            #          C:\nrn\bin\nrniv.exe: _nt->tml->index == CAP
            #      the first two seem to go when using "h(f'_pysec.{pySec} uninsert {mechName}')" syntax for the sections created in Python,
            #      but the third one is still a puzzle to solve (it's related to some special management of "capacitance" on NEURON side)
            # !! UPD: try MechanismType.remove
            paramCats = EnumParamCats.biophys if self._isUseRealBiophysOrTestSines else EnumParamCats.baseGeom
            
            self._dirtyStatesHelper.onParamChange(paramCats)
            
    def _isInsertIClampCheckBoxHandler(self):
        if self._isInsertIClamp:
            h.iClampHelper.deployClamp(1)
        else:
            h.iClampHelper.removeClamp()
            
    def _isInsertSEClampCheckBoxHandler(self):
        if self._isInsertSEClamp:
            h.seClampHelper.deployClamp(1)
        else:
            h.seClampHelper.removeClamp()
            
    def _showManagerOfBiophysicsButtonHandler(self):
        
        isTransformationRequired = self._isEnumMyelSheathInDeployScalp()
        
        if isTransformationRequired:
            
            isCancel = self._validateBeforeTransformation()
            if isCancel:
                return
                
            if not self._core.isTransformed:
                isCancel = not h.boolean_dialog('To proceed, we need to lock the ability to edit the geometry params. Do you want to proceed?', 'Yes', 'No')
                if isCancel:
                    return
                    
        dirtyParamCat = self._getDirtyParamCat()
        if isTransformationRequired != self._core.isTransformed or dirtyParamCat >= EnumParamCats.biophys:
            mainBoxCopy = self._mainBox     # !! preventing sporadic "Segmentation violation"
            h.altRunControlWidget.initHandler()
            
        # !! maybe call a less general method here
        h.makeSureMechCompsCreatedOrImportedAndRescannedThenShowMechManagerBaseWidget()
        h.mechManagerMainWidget.shapeBox.unmap()
        
        self._wasManagerOfBiophysicsShown = True
        
        # Mark that user may have edited biophysics manually;
        # this prevents re-import from JSON on subsequent initBiophysics calls
        self._core._userHasEditedBiophys = True
        
    def _startSimButtonHandler(self):
        h.altRunControlWidget.initAndRunHandler()
        
    def _deleteModifGeomAxonAndCreateBaseGeomAxon(self, isCalledFromSheathRadioButtonHandler):
        
        self._core.cleanup(True, True)
        
        enumAxonGeometry = self._enumAxonGeometry
        
        # !! we could use "match-case" here, but it was introduced only in Python 3.10 (2021),
        #    and user may have an older version installed
        if enumAxonGeometry in [EnumAxonGeometry.imported, EnumAxonGeometry.predefined]:
            
            if self._isCellBuildHelperShown:
                self._onDoneOrCancelInCellBuildHelper(True)
            elif not (self._core.isTransformed or self._isProgrammaticCall or isCalledFromSheathRadioButtonHandler):
                self._core.deleteBaseGeomAxon()
                
            self._core.createBaseGeomAxon(enumAxonGeometry)
            
        elif enumAxonGeometry == EnumAxonGeometry.drawnByHand:
            
            if self._isProgrammaticCall or isCalledFromSheathRadioButtonHandler:
                # Restoring the axon drawn by hand from the cache
                self._core.createBaseGeomAxon(enumAxonGeometry)
            else:
                
                self._core.deleteBaseGeomAxon()
                
                isNotImpl = self._cellBuildHelper.analyzeSecNamesAndCheckForNotImplScenario()
                if not isNotImpl:
                    
                    # We'll show the CellBuild-er
                    
                    self._updateShape(True)
                    
                    if self._isUseRealBiophysOrTestSines:
                        self._removeClampsIfChecked()
                        
                    self._isCellBuildHelperShown = True
                    
                    self._cellBuildHelper.show()    # --> onCellBuilderDoneOrCancel
                    
                    return True
                else:
                    self._isAxonDrawnByHandInvalid = True
                    self._core.createBaseGeomAxon(EnumAxonGeometry.predefined)
        else:
            
            codeContractViolation()
            
        self._deleteModifGeomAxonAndCreateBaseGeomAxonEpilogue()
        
        return False
        
    def _whatToShowRadioButtonHandler(self, isShowAxonOnly):
        
        self._isShowAxonOnly = isShowAxonOnly
        
        self._updateShape()
        
    def _updateShape(self, isCalledJustBeforeShowingCellBuilder=False):
        
        self._shape.erase_all()
        
        if self._isShowAxonOnly:
            axonSecList = h.listOfSecRefToSecList(h.axon_ref)
            self._shape.observe(axonSecList)
        else:
            self._shape.observe()
            
        self._shape.exec_menu('View = plot')
        
        self._core.colourSectsAndAddLabels(self._shape, isCalledJustBeforeShowingCellBuilder, self._isShowAxonOnly)
        
        if not self._core.isTransformed and self._isEnumMyelSheathInDeployScalp():
            self._myelRegionHelper.showMyelinMarkers(self._shape)
            
        self._shape.flush()
        
    def _deleteModifGeomAxonAndCreateBaseGeomAxonEpilogue(self):
        self._axonBiophysCompsHelper.onBaseAxonCreated()
        
    def _axonGeomRadioButtonHandlerEpilogue(self):
        
        if self._isEnumMyelSheathInDeployScalp():
            self._myelRegionRadioButtonHandler(self._myelRegionHelper.enumMyelRegion)
        elif self._enumMyelSheath == EnumMyelSheath.remove:
            self.removeMyelinMarkers(False)
        else:
            codeContractViolation()
            
        self._dirtyStatesHelper.onParamChange(EnumParamCats.modifGeom)
        
    def _flipDecksDepOnEnumMyelSheath(self):
        
        cardIdx = 1 if self._isEnumMyelSheathInDeployScalp() else 0
        self._myelinParamsDeck1.flip_to(cardIdx)
        
        cardIdx = 1 if self._enumMyelSheath == EnumMyelSheath.deploy else 0
        self._testBiophysParamsDeck.flip_to(cardIdx)
        self._presParams.deck1.flip_to(cardIdx)
        
    def _flipSheathParamsDecks(self):
        cardIdx = 0 if self._core.isTransformed else 1
        self._myelinParamsDeck2.flip_to(cardIdx)
        
        cardIdx = int(self._myelRegionHelper.enumMyelRegion)
        self._myelinParamsDeck3.flip_to(cardIdx)
        
    def _flipDecksDepOnIsUseRealBiophysOrTestSines(self):
        cardIdx = 1 if self._isUseRealBiophysOrTestSines else 0
        self._biophysAndClampsParamsDeck.flip_to(cardIdx)
        self._presParams.deck2.flip_to(cardIdx)
        
    def _showOrHideTrunkAndSheathParams(self, isShow):
        cardIdx = 1 if isShow else 0
        self._trunkParamsDeck.flip_to(cardIdx)
        self._sheathParamsDeck.flip_to(cardIdx)
        
    def _showOrHideMyelinParams(self, isShow):
        cardIdx = 1 if isShow else 0
        self._myelinParamsDeck3.flip_to(cardIdx)
        
    def _onDoneOrCancelInCellBuildHelper(self, isCancel, isCalledFromDismissHandler=False):
        
        if isCancel:
            self._cellBuildHelper.dismissBoxesAndRollBackAllChangesToSoma()
            
        if self._isUseRealBiophysOrTestSines and not isCalledFromDismissHandler:
            self._deployClampsIfChecked()
            
        self._isCellBuildHelperShown = False
        
    def _removeElectrodeAndSetUpDefaultClampParams(self):
        
        if hasattr(h, '_iClampPPGM'):   # Not defined in the test mode
            h._iClampPPGM.unmap()
            
        ms = h.MechanismStandard('IClamp', 1)
        ms.set('del', 0)        # ms
        ms.set('dur', 5000)     # ms
        ms.set('amp', 2)        # nA
        h.iClampHelper.ms = ms
        h.iClampHelper.isRestoreParamsOnNextDeployment = True
        
        ms = h.MechanismStandard('SEClamp', 1)
        ms.set('rs', 1)         # megohm
        ms.set('dur1', 300)     # ms
        ms.set('amp1', -85)     # mV
        ms.set('dur2', 300)     # ms
        ms.set('amp2', 10)      # mV
        ms.set('dur3', 0)       # ms
        ms.set('amp3', 0)       # mV
        h.seClampHelper.ms = ms
        h.seClampHelper.isRestoreParamsOnNextDeployment = True
        
    def _deployClampsIfChecked(self):
        with mwhw.MsgWarnInterceptor():
            if self._isInsertIClamp:
                h.iClampHelper.deployClamp(1)
            if self._isInsertSEClamp:
                h.seClampHelper.deployClamp(1)
                
    def _removeClampsIfChecked(self):
        if self._isInsertIClamp:
            h.iClampHelper.removeClamp()
        if self._isInsertSEClamp:
            h.seClampHelper.removeClamp()
            
    def _updateGuiOnMyelStatusChanged(self, isTransformed):
        
        if isTransformed:
            if self._enumMyelSheath == EnumMyelSheath.deploy:
                statusStr = 'DEPLOYED'
            elif self._enumMyelSheath == EnumMyelSheath.scalp:
                statusStr = 'SCALPED'
            else:
                codeContractViolation()
        else:
            statusStr = 'REMOVED'
            
        h.sprint(self._myelinStatusStr, 'Myelin: %s', statusStr)
        
        if hasattr(self, '_myelinParamsDeck2'):
            cardIdx = 0 if isTransformed else 0
            self._myelinParamsDeck2.flip_to(cardIdx)
            
    def _ifAxonInvalidThenWarnAndSwitchToPredefAxon(self, isDrawnByHandCancel):
        
        if self._enumAxonGeometry == EnumAxonGeometry.predefined:
            return
            
        if self._enumAxonGeometry == EnumAxonGeometry.imported:
            if self._isImportedAxonInvalid:
                what = 'imported axon'
            else:
                return
        elif self._enumAxonGeometry == EnumAxonGeometry.drawnByHand:
            if self._isAxonDrawnByHandInvalid:
                what = 'axon drawn by hand'
            else:
                return
        else:
            codeContractViolation()
            
        if isDrawnByHandCancel:
            msg = self._predefAxonFallbackMsg
        else:
            msg = f"The {what} is not valid for this simulation. {self._predefAxonFallbackMsg}"
        h.mwh.showWarningBox(msg)
        
        self._enumAxonGeometry = EnumAxonGeometry.predefined
        
    def _isEnumMyelSheathInDeployScalp(self, _enumMyelSheath=None):
        if _enumMyelSheath is None:
            _enumMyelSheath = self._enumMyelSheath
        return _enumMyelSheath in [EnumMyelSheath.deploy, EnumMyelSheath.scalp]
        
    def _getDirtyParamCat(self):
        dirtyParamCat = self._dirtyStatesHelper.dirtyParamCat
        if dirtyParamCat == EnumParamCats.anim and not self._isUseRealBiophysOrTestSines:
            dirtyParamCat = EnumParamCats.biophys
        return dirtyParamCat
        
    def _createCannotEditVBox(self):
        with bc.VBox(panel=True):
            h.xlabel('')
            h.xlabel('Cannot edit these params')
            h.xlabel('when the axon is transformed')
            h.xlabel('')
            h.xbutton('Return to initial axon state', self._removeMyelinButtonHandler)
            
    def _validateBeforeTransformation(self):
        
        isCancel = self._core.validate(self._myelRegionHelper.enumMyelRegion == EnumMyelRegion.zebra)
        if isCancel:
            return True
            
        if self._myelRegionHelper.enumMyelRegion == EnumMyelRegion.drawnByHand:
            isCancel = self._myelRegionHelper.validate()
            if isCancel:
                return True
                
        return False
        
    def _dismissHandler(self):
        
        self._isAxonDrawnByHandInvalid = self._isCellBuildHelperShown
        
        if self._isCellBuildHelperShown:
            self._onDoneOrCancelInCellBuildHelper(True, True)
            
        h.unmapIfNotNil(self._mainBox)
        