

# !! maybe use this class to create colourbar, store and set "_palette", create "_ani", set its "interval" etc.


import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider

import webbrowser

import numpy as np


# !! code dup. with PyplotAndSaveHelper (createStartStopButtonFrameSliderAndDensityStrip, _onNewFrame, _onButtonStartStopClick, _onSliderFrameChange)
class PyplotPlayerBase:
    
    _isDesktopOrBrowser = None
    
    # Used only when _isDesktopOrBrowser is False
    _animationEmbedLimit = 300  # MB
    _tempHtmlFileName = 'temp.html'
    
    # Used only when _isDesktopOrBrowser is True
    
    _buttonStartStop = None
    _sliderFrame = None
    
    _footerColour = 'skyblue'
    _footerAlpha = 0.4
    
    _ani = None
    
    _frameIdx = -1
    _isAnimRunning = True
    _isProgrammaticSliderFrameChange = False
    
    _showDataFromThisFrame = None
    
    
    def createStartStopButtonFrameSliderAndDensityStrip(self, data):
        
        numFrames = data.shape[0]
        
        sh = 0.05
        
        ax = plt.axes([0.1, 0.05, 0.8, sh])
        # !! maybe show "t (ms)" instead of "Frame"
        self._sliderFrame = Slider(ax, 'Frame', valmin=0, valmax=numFrames - 1, valstep=1)
        self._sliderFrame.on_changed(self._onSliderFrameChange)
        
        ax = plt.axes([0.025, 0.125, 0.1, 0.05])
        self._buttonStartStop = Button(ax, 'Stop')
        self._buttonStartStop.on_clicked(self._onButtonStartStopClick)
        
        ax = plt.axes([0.1, 0.02, 0.8, 0.03])
        x = np.linspace(0, numFrames - 1, numFrames)
        y = [frame.mean() for frame in data]
        ax.plot(x, y)
        plt.xlim(0, numFrames - 1)
        
        yMin = np.min(y)
        yMax = np.max(y)
        if yMin == yMax:
            # !! just preventing the next message printed by Pyplot (to reproduce, use RxD with Dirichlet boundary conditions and choose a boundary layer):
            #    "UserWarning: Attempting to set identical low and high ylims makes transformation singular; automatically expanding."
            yMin -= 0.5
            yMax += 0.5
        plt.ylim(yMin, yMax)
        
        plt.xticks([])
        plt.yticks([])
        ax.fill_between(x, y, color=self._footerColour, alpha=self._footerAlpha)
        
        return sh
        
    def saveAnimToTempHtmlFile(self):
        
        # Increase the animation size limit
        # !! not sure if we need this for 2D animation
        plt.rcParams['animation.embed_limit'] = self._animationEmbedLimit
        
        html = self._ani.to_jshtml()
        
        # Save the HTML string to a temporary HTML file
        with open(self._tempHtmlFileName, 'w') as f:
            f.write(html)
            
    def show(self):
        if self._isDesktopOrBrowser:
            # !! BUG: this shows the previous (already closed) figure as well
            plt.show()
        else:
            # Open the temporary HTML file in the default web browser
            webbrowser.open(self._tempHtmlFileName)
            
            
    def _onNewFrame(self, frameIdx):
        self._showDataFromThisFrame(frameIdx)
        
        if not self._isDesktopOrBrowser:
            return
            
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
        