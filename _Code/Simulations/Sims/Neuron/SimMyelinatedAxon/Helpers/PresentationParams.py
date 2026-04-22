
from neuron import h

import GuiPrimitiveWrappers as bc


class PresentationParams:
    
    isAnim = [True] * 2
    isSave = False
    isExportBiophys = False
    isDraw = [True] * 7
    isPrint = False
    
    # Data member added in "setSaveTxtFileCheckBoxHandler":
    #   _saveTxtFileCheckBoxHandler
    
    # Data member added in "setExportBiophysCheckBoxHandler":
    #   _exportBiophysCheckBoxHandler
    
    # Data members added in "populatePresParamsPart2Panel":
    #   deck1, deck2
    
    def setSaveTxtFileCheckBoxHandler(self, saveTxtFileCheckBoxHandler):
        self._saveTxtFileCheckBoxHandler = saveTxtFileCheckBoxHandler
        
    def setExportBiophysCheckBoxHandler(self, exportBiophysCheckBoxHandler):
        self._exportBiophysCheckBoxHandler = exportBiophysCheckBoxHandler
        
    def populatePresParamsPart1Panel(self):
        h.xcheckbox('Animate K+ radial conc colourmap vs segm idx',       (self.isAnim, 0), self._isAnim0CheckBoxHandler)
        h.xcheckbox('Animate K+ radial conc vs dist for each shell',      (self.isAnim, 1), self._isAnim1CheckBoxHandler)
        h.xcheckbox('Save K+ conc(t, dist, radius) to TXT file',          (self, 'isSave'), self._saveTxtFileCheckBoxHandler)
        h.xcheckbox('Export biophysics (JSON + TXT) on Init',             (self, 'isExportBiophys'), self._exportBiophysCheckBoxHandler)
        
    def populatePresParamsPart2Panel(self):
        with bc.Panel():
            h.xcheckbox('Draw "ik" vs dist for axon trunk',               (self.isDraw, 0))
            h.xcheckbox('Draw "ko" vs dist for axon trunk',               (self.isDraw, 1))
        with bc.Deck(emptyPanel=True, panel=True) as self.deck1:
            h.xcheckbox('Draw "ik" vs dist for each Schwann cell',        (self.isDraw, 2))
            h.xcheckbox('Draw "ko" vs dist for each Schwann cell',        (self.isDraw, 3))
            # self.deck1.flip_to(*)     # Will be done downstream in SimMyelinatedAxon._myelSheathRadioButtonHandler
        with bc.Deck(emptyPanel=True, panel=True) as self.deck2:
            h.xcheckbox('Draw "v" vs time in 3 points along axon trunk',  (self.isDraw, 4))
            h.xcheckbox('Draw "ek" vs dist for axon trunk',               (self.isDraw, 5))
            h.xcheckbox('Draw "v" vs dist for axon trunk',                (self.isDraw, 6))
            # self.deck2.flip_to(*)     # Will be done downstream in SimMyelinatedAxon._biophysRadioButtonHandler
        with bc.Panel():
            # !! maybe don't mention each "Dt" here because we already have a hint below "Dt"
            h.xcheckbox('Print "ik" and "ko" in sec centres (each "Dt")', (self, 'isPrint'))
            h.addEmptyLabels(5)
            
            
    def _isAnim0CheckBoxHandler(self):
        # Locking "Continue" to avoid an error in PyplotAndSaveHelper
        h.altRunControlWidget.isInited = 0
        
    def _isAnim1CheckBoxHandler(self):
        
        if not self.isAnim[1]:
            # !! maybe warn user that we are unchecking this checkbox because it requires self.isAnim[1] to be set first
            #    (in the future, me may eliminate this inconvenience)
            self.isSave = False
            
        # Locking "Continue" to avoid an error in PyplotAndSaveHelper
        h.altRunControlWidget.isInited = 0
        