
# !! Ideas:
#    * think about the usage of log colourbar (if supported) or explicit expressions for the watched var, e.g. "log(gabao)"
#    * maybe make "z" axis normal to the screen by default to be consistent with PlotShape default view direction
#    * maybe cache data in Python to make the wait time for "Show the last record once again" shorter

from NeuronPlayer import NeuronPlayer
from Plotly2dPlayer import Plotly2dPlayer
from Plotly3dPlayer import Plotly3dPlayer

import numpy as np
from neuron import h

import MsgWarnHelperWrappers as mwhw
from OtherInterModularUtils import isShowPyplotFigsInSubProcess, codeContractViolation


if isShowPyplotFigsInSubProcess:
    import sys
    import os
    import pickle
    import subprocess
    from Separated.FakeGridOfSections import FakeGridOfSections
    from Separated.FakeGridSlicerWidget import FakeGridSlicerWidget
else:
    from Pyplot2dPlayer_Separated import Pyplot2dPlayer
    from Pyplot3dPlayer_Separated import Pyplot3dPlayer
    
    
class RangeVarAnimationPlayer:
    
    # Data members added in the ctor:
    #   _record
    #   _neuronPlayerWidget
    
    def __init__(self, record, neuronPlayerWidget):
        self._record = record
        self._neuronPlayerWidget = neuronPlayerWidget
        
    def play(self, enumNeuronPyplotPlotly, is2dOr3D, isOpacitiesOrColours, isDesktopOrBrowser, gridSlicerWidget, isTestMode):
        
        if is2dOr3D and h.gridOfSections == None:
            h.mwh.showWarningBox('The recorded animation cannot be shown with \"2D slice (grid only)\" presentation', 'because it requires that the variable was watched on a grid.', 'Please choose \"3D scene\" presentation instead.')
            return
            
        if isTestMode:
            # !! just some test data here
            self._record.setTestData(enumNeuronPyplotPlotly)
            
        # 3D coordinates of segment centres
        x = self._record.xVec
        y = self._record.yVec
        z = self._record.zVec
        
        numSegms = len(x)
        
        if enumNeuronPyplotPlotly != 0 and is2dOr3D and h.gridOfSections.nx * h.gridOfSections.ny * h.gridOfSections.nz != numSegms:
            # !! BUG: we hit this branch if user recorded an animation, then deployed a grid with different numSegms
            #         and then tried to show the old animation; in this case, the message is just wrong
            h.mwh.showNotImplementedWarning('Currently the recorded animation cannot be shown Pyplot or Plotly animation module and \"2D slice (grid only)\" presentation', 'if the variable was watched not only on a grid, but also on the cell (the \"Both 2 above\" option).', 'Please choose \"3D scene\" presentation instead.')
            return
            
        varNameWithIndexAndUnits = self._record.varNameWithIndexAndUnits
        
        # The time grid
        t = self._record.timeVec
        
        numFrames = len(t)
        
        # !! minor BUG: if using Pyplot and isShowPyplotFigsInSubProcess == True, we hide the wait box too early
        with mwhw.PleaseWaitBox('Preparing animation.'):
            
            if isTestMode:
                # !! just some random test data here
                rangeVar = np.random.rand(numFrames, numSegms)
            else:
                rangeVar = np.empty(numSegms * numFrames)
                self._record.rangeVarVec.to_python(rangeVar)
                rangeVar = np.reshape(rangeVar, (numFrames, numSegms))
                
            rangeVar_min = self._getRangeVarMin(rangeVar, varNameWithIndexAndUnits)
            rangeVar_max = rangeVar.max()
            
            if enumNeuronPyplotPlotly == 0:
                
                varNameWithIndex = varNameWithIndexAndUnits.split(' (', 1)[0]
                player = NeuronPlayer(rangeVar, t, varNameWithIndex, rangeVar_min, rangeVar_max, self._neuronPlayerWidget)
                
            elif enumNeuronPyplotPlotly == 1:
                
                if isShowPyplotFigsInSubProcess:
                    # !! BUG: (minor) all the Pyplot figures are titled "Figure 1"
                    self._showPyplotPlayerInSubProcess(is2dOr3D, locals())
                else:
                    # !! BUG: (minor): calling hoc:AnimationSettingsWidget.showLastHandler for 2nd time (with the old Pyplot animation in progress) leads to the next error:
                    #                  "QCoreApplication::exec: The event loop is already running"
                    #                  (perhaps this can be fixed by simply stopping the animation programmatically)
                    if is2dOr3D:
                        player = Pyplot2dPlayer(rangeVar, h.gridOfSections, gridSlicerWidget, varNameWithIndexAndUnits, isDesktopOrBrowser, rangeVar_min, rangeVar_max)
                    else:
                        player = Pyplot3dPlayer(x, y, z, rangeVar, numFrames, varNameWithIndexAndUnits, isOpacitiesOrColours, isDesktopOrBrowser, rangeVar_min, rangeVar_max)
                        
            elif enumNeuronPyplotPlotly == 2:
                
                if is2dOr3D:
                    player = Plotly2dPlayer(rangeVar, gridSlicerWidget, varNameWithIndexAndUnits, rangeVar_min, rangeVar_max)
                else:
                    player = Plotly3dPlayer(x, y, z, rangeVar, t, varNameWithIndexAndUnits, isOpacitiesOrColours, rangeVar_min, rangeVar_max)
                    
            else:
                
                codeContractViolation()
                
        if not (enumNeuronPyplotPlotly == 1 and isShowPyplotFigsInSubProcess):
            player.show()
            
        # !! it would be better to do this before player.show() and inside the "please wait" block
        if enumNeuronPyplotPlotly == 0:
            self._neuronPlayerWidget.onAnimationSettingsChanged(is2dOr3D, gridSlicerWidget.projIdx, gridSlicerWidget.isOneLayerOrMean, gridSlicerWidget.sliceIdx_1Based, 0)
            
    def _showPyplotPlayerInSubProcess(self, is2dOr3D, localVars):
        
        data = {
            'rangeVar': localVars['rangeVar'],
            'varNameWithIndexAndUnits': localVars['varNameWithIndexAndUnits'],
            'isDesktopOrBrowser': localVars['isDesktopOrBrowser'],
            'rangeVar_min': localVars['rangeVar_min'],
            'rangeVar_max': localVars['rangeVar_max']}
        
        if is2dOr3D:
            scriptFileName = 'Pyplot2dPlayer_Separated.py'
            
            data.update({
                'gridOfSections': FakeGridOfSections(h.gridOfSections),
                'gridSlicerWidget': FakeGridSlicerWidget(localVars['gridSlicerWidget'])})
        else:
            scriptFileName = 'Pyplot3dPlayer_Separated.py'
            
            data.update({
                'x': localVars['x'].as_numpy(),
                'y': localVars['y'].as_numpy(),
                'z': localVars['z'].as_numpy(),
                'numFrames': localVars['numFrames'],
                'isOpacitiesOrColours': localVars['isOpacitiesOrColours']})
            
        thisFileDirPath = os.path.dirname(os.path.abspath(__file__))
        
        with open(thisFileDirPath + '\\temp.pickle', 'wb') as f:
            pickle.dump(data, f)
            
        subprocess.Popen([sys.exec_prefix + '/python.exe', scriptFileName], cwd=thisFileDirPath)
        
    def _getRangeVarMin(self, rangeVar, varNameWithIndexAndUnits):
        fallbackMin = rangeVar.min()
        varNameWithIndex = varNameWithIndexAndUnits.split(' ')[0]
        if varNameWithIndex[-1] == 'o':
            # This is probably an out concentration range var - we want to see some opacity (or elevated colour) even for the lowest value point
            # when it's higher than the base out concentration (e.g. when we have a static point source)
            ionName = varNameWithIndex[:-1]                     # e.g. "gaba"
            baseOutConcVarName = f'{ionName}o0_{ionName}_ion'   # e.g. "gabao0_gaba_ion"
            try:
                rangeVar_min = getattr(h, baseOutConcVarName)
                if fallbackMin < rangeVar_min:
                    # A case when we have some segment(s) where "{ionName}o < {ionName}o0_{ionName}_ion" - use full transparency for the lowest value point
                    rangeVar_min = fallbackMin
            except AttributeError:
                # Not an out concentration range var - use full transparency for the lowest value point
                rangeVar_min = fallbackMin
        else:
            # Not an out concentration range var - use full transparency for the lowest value point
            rangeVar_min = fallbackMin
        return rangeVar_min
        