
# !! for the slider, ideally show not only "frameIdx", but "frameIdx / maxFrameIdx" (or maybe use the window name to show it)

# !! kill zombie procs: we can save pids in the temp folder and read them before cleaning up the folder;
#    alternatively, we can look for the procs named "t: * (ms)"

# !! no need to pass radius_axon, radius_outer and isDeployMyelSheath for colourMapDataMatrixOrNone each time
# !! no need to pass the "x" data for each curve in perShellCurvesXYTuplesOrNone; also, no need to pass the "x" data on each frame

import sys
import os
import pickle
import math
from threading import Timer

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button, Slider

try:
    from neuron import h
except ModuleNotFoundError:
    pass
    
    
# !! code dup. with OtherInterModularUtils (which is not separated)
# !! maybe define it in each "_Separated" file
def codeContractViolation():
    print('\n    Bug in BrainCell program: Code contract violation\n    Please report this problem to the developer along with the call stack shown below\n')
    raise Exception
    
    
# !! code dup. with Extracellular->PyplotPlayerBase (createStartStopButtonFrameSlider, _onNewFrame, _onButtonStartStopClick, _onSliderFrameChange)
class PyplotAndSaveHelper:
    
    _cumulativeMin = math.inf
    _cumulativeMax = -math.inf
    
    class OneFrame:
        
        def __init__(self, time, colourMapDataMatrixOrNone, perShellCurvesXYTuplesOrNone):
            
            if colourMapDataMatrixOrNone is None and perShellCurvesXYTuplesOrNone is None:
                codeContractViolation()
                
            self.time = time
            self.colourMapDataMatrixOrNone = colourMapDataMatrixOrNone
            self.perShellCurvesXYTuplesOrNone = perShellCurvesXYTuplesOrNone
            
            if colourMapDataMatrixOrNone is not None:
                PyplotAndSaveHelper._cumulativeMin = min(PyplotAndSaveHelper._cumulativeMin, colourMapDataMatrixOrNone.min())
                PyplotAndSaveHelper._cumulativeMax = max(PyplotAndSaveHelper._cumulativeMax, colourMapDataMatrixOrNone.max())
            else:
                for curveData in perShellCurvesXYTuplesOrNone:
                    PyplotAndSaveHelper._cumulativeMin = min(PyplotAndSaveHelper._cumulativeMin, curveData[1].min())
                    PyplotAndSaveHelper._cumulativeMax = max(PyplotAndSaveHelper._cumulativeMax, curveData[1].max())
                    
        def getTimeStrForTitle(self):
            return 't: %g (ms)' % self.time
            
    def getPickleFileName(frameIdx):
        
        pickleFileNameSuffix = str(frameIdx).zfill(4)
        return f'frame{pickleFileNameSuffix}.pickle'
        
    def createEmptyMarkerFile(fileAbsPathName):
        
        # No error if the marker file already exists
        open(fileAbsPathName, 'w').close()
        
    runningMarkerFileName = 'running'
    saveToMarkerFileName = 'save_to'
    alreadySavedMarkerFileName = 'saved'
    
    # The next 3 params are subjects for tuning
    
    # Delay between animation frames: slow anim if too big, choppy anim if too small
    _animInterval = 250     # ms (real world time)
    
    # How often to look for new pickle and marker files: choppy anim and TXT save delay in the end if too big
    # !! see also: PyplotSubProcHelper._alreadySavedMarkerFileCheckTimerInterval
    _inputFilesCheckTimerInterval = 1   # s (real world time)
    
    # How many pickle files to load at once: slow anim if too small, choppy anim if too big; TXT save delay in the end if too small
    _maxNumPickleFilesLoadedPerTimerShot = 5
    
    
    _sliderFrame = None
    _buttonStartStop = None
    
    _ani = None
    
    _frameIdx = -1
    _isAnimRunning = True
    _isProgrammaticSliderFrameChange = False
    
    
    # Data members added in the ctor:
    #   _isSubProc
    #   _colourMapOrNone, _perShellCurvesOrNone
    #   _frames
    #   _tempFolderAbsPathName, _runningMarkerFileAbsPathName, _saveToMarkerFileAbsPathName, _alreadySavedMarkerFileAbsPathName
    
    # Data members added in "showFigure":
    #   _figure, _colourBarOrNone, _axes2OrNone
    
    # Data members added in "_onInputFilesCheckTimer":
    #   _radius_axon, _radius_outer
    #   _isDeployMyelSheath
    
    
    def __init__(self, isSubProc, tempFolderNameOrNone=None):
        
        self._isSubProc = isSubProc
        self._colourMapOrNone = None
        self._perShellCurvesOrNone = None
        self._frames = []
        
        if isSubProc:
            thisFileDirPath = os.path.dirname(os.path.abspath(__file__))
            self._tempFolderAbsPathName = os.path.join(thisFileDirPath, tempFolderNameOrNone)
            self._runningMarkerFileAbsPathName = os.path.join(self._tempFolderAbsPathName, self.runningMarkerFileName)
            self._saveToMarkerFileAbsPathName = os.path.join(self._tempFolderAbsPathName, self.saveToMarkerFileName)
            self._alreadySavedMarkerFileAbsPathName = os.path.join(self._tempFolderAbsPathName, self.alreadySavedMarkerFileName)
            
            # Loading the first pickle file
            self._onInputFilesCheckTimer(True)
        else:
            PyplotAndSaveHelper._cumulativeMin = math.inf
            PyplotAndSaveHelper._cumulativeMax = -math.inf
            
    def showFigure(self):
        
        numFrames = len(self._frames)
        
        if numFrames == 0:
            codeContractViolation()
            
        firstFrame = self._frames[0]
        
        fig = plt.figure(figsize=(3, 1), num=firstFrame.getTimeStrForTitle())
        self._figure = fig
        
        isAnim0 = firstFrame.colourMapDataMatrixOrNone is not None
        isAnim1 = firstFrame.perShellCurvesXYTuplesOrNone is not None
        
        if self._isDeployMyelSheath:
            where = 'between axon and Schwann cells'
        else:
            where = 'around axon'
            
        if isAnim0:
            # Plot the potassium concentration between axon and Schwann cells OR around axon
            arg = 121 if isAnim1 else 111
            fig.add_subplot(arg)
            plt.title('K$^{+}$ conc ' + where)
            self._colourMapOrNone = plt.imshow(
                firstFrame.colourMapDataMatrixOrNone,
                origin='lower',
                extent=(0, firstFrame.colourMapDataMatrixOrNone.shape[1], self._radius_axon, self._radius_outer),
                aspect='auto')
            self._colourBarOrNone = plt.colorbar()
            self._colourBarOrNone.ax.set_title('ko (mM)')
            plt.xlabel('End-to-end index of segment along axon sections')    # !! it would be better to show 'Distance ($\mu$m)'
            plt.ylabel('Radius ($\mu$m)')
            
        if isAnim1:
            # Plot the potassium concentration in each shell between axon and Schwann cells OR around axon
            arg = 122 if isAnim0 else 111
            self._axes2OrNone = fig.add_subplot(arg)
            plt.title('K$^{+}$ conc in each shell ' + where)
            self._perShellCurvesOrNone = []
            for shellIdx, xyTuple in enumerate(firstFrame.perShellCurvesXYTuplesOrNone):
                label = 'shell$_{%i}$' % (shellIdx + 1)
                curve = plt.plot(xyTuple[0], xyTuple[1], label=label)
                self._perShellCurvesOrNone.append(curve[0])     # !! why do we need to take [0] here?
            plt.legend(frameon=False)
            plt.xlabel('Distance ($\mu$m)')
            plt.ylabel('ko (mM)')
            
        fig.subplots_adjust(bottom=0.25)
        
        self._createStartStopButtonAndFrameSlider(numFrames)
        
        # !! setting "frames" just to avoid UserWarning: frames=None which we can infer the length of, did not pass an explicit *save_count* and passed cache_frame_data=True.  To avoid a possibly unbounded cache, frame data caching has been disabled. To suppress this warning either pass `cache_frame_data=False` or `save_count=MAX_FRAMES`.
        self._ani = FuncAnimation(fig, self._onNewFrame, frames=numFrames, interval=self._animInterval)
        
        self._ani.frame_seq = self._getFrameSeq()
        
        if self._isSubProc:
            self._startOneShotTimerForInputFilesCheck()
            plt.show()
        else:
            fig.show()
            
    # !! code dup. with _onInputFilesCheckTimer
    def addNewFrame(self, time, radius_axon, radius_outer, isDeployMyelSheath, colourMapDataMatrixOrNone, perShellCurvesXYTuplesOrNone):
        
        if self._isSubProc:
            codeContractViolation()
            
        # !! no need to assign them again on each frame
        self._radius_axon        = radius_axon
        self._radius_outer       = radius_outer
        self._isDeployMyelSheath = isDeployMyelSheath
        
        newFrame = self.OneFrame(time, colourMapDataMatrixOrNone, perShellCurvesXYTuplesOrNone)
        self._frames.append(newFrame)
        
        if self._sliderFrame:
            
            lastFrameIdx = len(self._frames) - 1
            self._sliderFrame.valmax = lastFrameIdx
            self._sliderFrame.ax.set_xlim(0, lastFrameIdx)
            
            if not self._isAnimRunning:
                # Refresh the slider
                plt.draw()
                
    # !! see also: hoc:RangeVarAnimationRecord.saveToTxtFile
    def saveToTxtFile(self, outTxtFilePathName):
        
        header = 't (ms)\tdist (um)\tradius (um)\tK_conc (mM)\n'
        recordTempl = '%g\t%g\t%g\t%g\n'
        
        # We have took measures to prevent empty frames list or None here
        firstFrameData = self._frames[0].perShellCurvesXYTuplesOrNone
        
        numShells = len(firstFrameData)
        dr = (self._radius_outer - self._radius_axon) / (numShells - 1)
        
        numSegms = len(firstFrameData[0][0])    # i.e. len of x data of first shell
        
        with open(outTxtFilePathName, 'w') as outFile:
            outFile.write(header)
            for frame in self._frames:
                for segmIdx in range(numSegms):
                    for shellIdx in range(numShells):
                        radius = self._radius_axon + shellIdx * dr
                        xyTuple = frame.perShellCurvesXYTuplesOrNone[shellIdx]
                        dist = xyTuple[0][segmIdx]
                        conc = xyTuple[1][segmIdx]
                        outFile.write(recordTempl % (frame.time, dist, radius, conc))
                        
    def closeFigure(self):
        plt.close(self._figure)
        self._frames = []
        
        
    # !! code dup. with addNewFrame
    def _onInputFilesCheckTimer(self, isFirstCall=False):
        
        if not self._isSubProc:
            codeContractViolation()
            
        numLoadedPickleFiles = len(self._frames)
        
        for _ in range(self._maxNumPickleFilesLoadedPerTimerShot):
            
            nextPickleFileName = PyplotAndSaveHelper.getPickleFileName(numLoadedPickleFiles)
            nextPickleFileAbsPathName = os.path.join(self._tempFolderAbsPathName, nextPickleFileName)
            
            if not os.path.exists(nextPickleFileAbsPathName):
                if isFirstCall and numLoadedPickleFiles == 0:
                    codeContractViolation()
                break
                
            # !! can I hit an error here when the file is partially written at the moment?
            try:
             with open(nextPickleFileAbsPathName, 'rb') as f:
                 data = pickle.load(f)
            except (EOFError, pickle.UnpicklingError):
                break  # file not fully written yet, try again on next timer tick
            #with open(nextPickleFileAbsPathName, 'rb') as f:
                #data = pickle.load(f)
                
            if isFirstCall:
                self._radius_axon        = data['radius_axon']
                self._radius_outer       = data['radius_outer']
                self._isDeployMyelSheath = data['isDeployMyelSheath']
                
            newFrame = self.OneFrame(
                data['time'],
                data['colourMapDataMatrixOrNone'],
                data['perShellCurvesXYTuplesOrNone'])
            self._frames.append(newFrame)
            
            numLoadedPickleFiles += 1
            
        if not isFirstCall:
            
            lastFrameIdx = numLoadedPickleFiles - 1
            valmax = max(lastFrameIdx, 1)   # !! just to avoid UserWarning: Attempting to set identical low and high xlims makes transformation singular; automatically expanding.
            self._sliderFrame.valmax = valmax
            self._sliderFrame.ax.set_xlim(0, valmax)
            if not self._isAnimRunning:
                # Refresh the slider
                # !! BUG: sporadic UserWarning: Starting a Matplotlib GUI outside of the main thread will likely fail.
                plt.draw()
                
            nextPickleFileName = PyplotAndSaveHelper.getPickleFileName(numLoadedPickleFiles)            # !! code dup. with the one in the cycle above: maybe move to a method
            nextPickleFileAbsPathName = os.path.join(self._tempFolderAbsPathName, nextPickleFileName)   #
            if not os.path.exists(nextPickleFileAbsPathName):                                           #
                # We have verified that there are no unparsed pickle files
                self._checkForTxtSaveRequest()
                
            self._startOneShotTimerForInputFilesCheck()
            
    def _startOneShotTimerForInputFilesCheck(self):
        
        if not self._isSubProc:
            codeContractViolation()
            
        Timer(self._inputFilesCheckTimerInterval, self._onInputFilesCheckTimer).start()
        
        
    def _getFrameSeq(self):
        while True:
            # !! when user clicks "continue til/for", maybe jump to the last frame immediately
            if self._isSubProc:
                isSimRunning = os.path.exists(self._runningMarkerFileAbsPathName)
            else:
                isSimRunning = h.altRunControlWidget.isRunning
            nextFrameIdx = self._frameIdx + 1
            numFrames = len(self._frames)
            if isSimRunning:
                # Following the last frame
                self._frameIdx = min(nextFrameIdx, numFrames - 1)
            else:
                # Looping
                self._frameIdx = nextFrameIdx % numFrames
                
            yield self._frameIdx
            
    def _createStartStopButtonAndFrameSlider(self, numFrames):
        
        sh = 0.05
        
        ax = plt.axes([0.1, 0.05, 0.8, sh])
        # !! maybe show "t (ms)" instead of "Frame"
        valmax = max(numFrames - 1, 1)  # !! just to avoid UserWarning: Attempting to set identical low and high xlims makes transformation singular; automatically expanding.
        self._sliderFrame = Slider(ax, 'Frame', valmin=0, valmax=valmax, valstep=1)
        self._sliderFrame.on_changed(self._onSliderFrameChange)
        
        ax = plt.axes([0.025, 0.125, 0.1, 0.05])
        self._buttonStartStop = Button(ax, 'Stop')
        self._buttonStartStop.on_clicked(self._onButtonStartStopClick)
        
    def _onNewFrame(self, frameIdx):
        self._showDataFromThisFrame(frameIdx)
        
        self._isProgrammaticSliderFrameChange = True
        self._sliderFrame.set_val(frameIdx)             # --> _onSliderFrameChange
        self._isProgrammaticSliderFrameChange = False
        
    def _onButtonStartStopClick(self, _):
        if self._isAnimRunning:
            self._ani.event_source.stop()
            self._buttonStartStop.label.set_text('Start')
        else:
            self._ani.event_source.start()
            self._buttonStartStop.label.set_text('Stop')
        self._isAnimRunning = not self._isAnimRunning
        
        # Refresh the button text
        plt.draw()
        
    def _onSliderFrameChange(self, val):
        
        frameIdx = int(val)
        self._frameIdx = frameIdx
        
        if self._isProgrammaticSliderFrameChange:
            return
            
        self._ani.event_source.stop()
        self._isAnimRunning = False
        
        self._showDataFromThisFrame(frameIdx)
        self._buttonStartStop.label.set_text('Start')
        
        # Refresh the button text
        plt.draw()
        
    def _showDataFromThisFrame(self, frameIdx):
        
        frame = self._frames[frameIdx]
        
        yMin = PyplotAndSaveHelper._cumulativeMin
        yMax = PyplotAndSaveHelper._cumulativeMax
        if yMin == yMax:
            # !! just preventing the next message printed by Pyplot for "self._axes2OrNone.set_ylim(...)":
            #    "UserWarning: Attempting to set identical low and high ylims makes transformation singular; automatically expanding."
            yMin -= 0.5
            yMax += 0.5
            
        if self._colourMapOrNone:
            self._colourMapOrNone.set_array(frame.colourMapDataMatrixOrNone)
            self._colourMapOrNone.set_clim(vmin=yMin, vmax=yMax)
            self._colourBarOrNone.update_normal(self._colourMapOrNone)
            
        if self._perShellCurvesOrNone:
            for curve, xyTuple in zip(self._perShellCurvesOrNone, frame.perShellCurvesXYTuplesOrNone):
                curve.set_ydata(xyTuple[1])
            self._axes2OrNone.set_ylim(yMin, yMax)
            
        self._figure.canvas.manager.set_window_title(frame.getTimeStrForTitle())
        
    def _checkForTxtSaveRequest(self):
        
        isTxtSaveRequest = os.path.exists(self._saveToMarkerFileAbsPathName)
        
        if not isTxtSaveRequest:
            return
            
        with open(self._saveToMarkerFileAbsPathName, 'r') as inMarkerFile:
            outTxtFilePathName = inMarkerFile.read()
            
        self.saveToTxtFile(outTxtFilePathName)
        
        os.remove(self._saveToMarkerFileAbsPathName) 
        
        PyplotAndSaveHelper.createEmptyMarkerFile(self._alreadySavedMarkerFileAbsPathName)
        
        
if __name__ == '__main__':
    
    tempFolderName = sys.argv[1]
    
    player = PyplotAndSaveHelper(True, tempFolderName)
    
    player.showFigure()
    