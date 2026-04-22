


# !! idea:
#    * to improve performance, try to convert _rangeVar (or _rangeVar0To1) to "array of arrays" for faster slicing rangeVar[frameIdx]



# !! BUGs:
#    * when _isOpacitiesOrColours is True and rotating the scene, the markers disappear randomly
#      UPD 1: tried to disable GPU rendering with "matplotlib.use('Agg')", but it gave me an error (perhaps missing dependency)
#      UPD 2: when showing 2nd, 3rd etc. animations, CPU load steps up, but GPU load does not
#    * when resizing the figure to full screen, the "Max" TextBox obstructs the RangeSlider label
#      (and the same problem when showing the default random test data)

# https://matplotlib.org/stable/gallery/animation/random_walk.html

from Separated.PyplotPlayerBase import PyplotPlayerBase
from Separated.ThreeDimPlayerBase import ThreeDimPlayerBase

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, RangeSlider, TextBox

from scipy.special import logit, expit
import numpy as np

import pickle


class Pyplot3dPlayer(PyplotPlayerBase, ThreeDimPlayerBase):
    
    # !! the bigger marker, the slower animation
    _defaultMarkerSize = 500
    
    # Used only when _isOpacitiesOrColours is True
    _defaultBalance = 0
    _markerColour = 'c'
    
    # Used only when _isOpacitiesOrColours is False
    _alpha = 0.25
    _palette = 'viridis'
    
    
    _rangeVar = None
    _numFrames = None
    _isOpacitiesOrColours = None
    
    _rangeVar0To1 = None
    _rangeVar0To1Balanced = None
    _scatter = None
    
    # Used only when _isDesktopOrBrowser is True
    _numSegms = None
    _sliderOpacity = None
    _sliderRange = None
    _textBoxMin = None
    _textBoxMax = None
    
    _isProgrammaticTextBoxMinMaxChange = False
    
    # Used only when _isOpacitiesOrColours is True
    _balance = 0
    _min = None
    _max = None
    _rangeVar_min = None
    _rangeVar_rangeOr1 = None
    
    
    def __init__(self, x, y, z, rangeVar, numFrames, varNameWithIndexAndUnits, isOpacitiesOrColours, isDesktopOrBrowser, rangeVar_min, rangeVar_max):
        
        self._numFrames = numFrames     # !! pyplot prints UserWarning-s if numFrames == 1
        self._isOpacitiesOrColours = isOpacitiesOrColours
        self._isDesktopOrBrowser = isDesktopOrBrowser
        
        if isDesktopOrBrowser:
            self._numSegms = len(x)
            
        if isOpacitiesOrColours:
            # Make a linear transformation of the data to fit [0, 1] range
            self._rangeVar0To1, self._rangeVar_rangeOr1 = self.makeZeroToOne(rangeVar, rangeVar_min, rangeVar_max)
            
            self._balance = self._defaultBalance
            self._min = rangeVar_min
            self._max = rangeVar_max
            self._rangeVar_min = rangeVar_min
            
            self._transformRangeVarToOpacities()    # This sets self._rangeVar0To1Balanced
        else:
            self._rangeVar = rangeVar
            
        # Create a 3D plot
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        
        if isDesktopOrBrowser and isOpacitiesOrColours:
            # Reserve some space for sliders and title
            ax.set_position([0.2, 0.2, 0.6, 0.6])
            
        if isOpacitiesOrColours:
            # Plot the 3D point cloud
            self._scatter = ax.scatter(x, y, z, alpha=self._rangeVar0To1Balanced[0], s=self._defaultMarkerSize, c=self._markerColour, linewidths=0)
        else:
            # Create a colormap
            cmap = plt.get_cmap(self._palette)
            
            # Set the colormap normalization based on the global min and max
            norm = plt.Normalize(vmin=rangeVar_min, vmax=rangeVar_max)
            
            # Plot the 3D point cloud
            self._scatter = ax.scatter(x, y, z, c=self._rangeVar[0], alpha=self._alpha, cmap=cmap, norm=norm, s=self._defaultMarkerSize, linewidths=0)
            
            # Add a color bar to indicate the values
            colorBar = plt.colorbar(self._scatter)
            colorBar.ax.set_title(varNameWithIndexAndUnits)
            
            # Adjust the margins of the entire figure to bring the colorbar closer to the edge
            fig.subplots_adjust(right=1)
            
        # Set the aspect ratio to be equal (preserve proportions)
        ax.set_aspect('equal')
        
        # Set labels for the axes
        ax.set_xlabel('x (μm)')
        ax.set_ylabel('y (μm)')
        ax.set_zlabel('z (μm)')
        
        fig.suptitle(varNameWithIndexAndUnits)
        
        # !! use blit=True and update method _onNewFrame when we show the extracellular sources
        interval = 0 if isDesktopOrBrowser else 1   # ms
        self._ani = FuncAnimation(fig, self._onNewFrame, frames=numFrames, interval=interval)
        
        # !! it looks like we don't need this
        self._ani.frame_seq = self._getFrameSeq()
        
        self._showDataFromThisFrame = self._setOpacitiesOrColours
        
        if isDesktopOrBrowser:
            
            if isOpacitiesOrColours:
                data = self._rangeVar0To1
            else:
                data = self._rangeVar
                
            sh = self.createStartStopButtonFrameSliderAndDensityStrip(data)
            
            sz = fig.get_size_inches()
            ratio = sz[1] / sz[0]
            sw = sh * ratio
            
            ax = plt.axes([0.025, 0.25, sw, 0.65])
            self._sliderSize = Slider(ax, 'Size', orientation='vertical', valmin=10, valmax=2000, valinit=self._defaultMarkerSize)
            self._sliderSize.on_changed(self._onSliderSizeChange)
            
            if isOpacitiesOrColours:
                ax = plt.axes([0.1, 0.25, sw, 0.65])
                self._sliderOpacity = Slider(ax, 'Opacity', orientation='vertical', valmin=-10, valmax=10, valinit=self._balance)
                self._sliderOpacity.on_changed(self._onSliderOpacityChange)
                
                tokens = varNameWithIndexAndUnits.split(' ', 1) # Spaces in units is OK
                if len(tokens) == 2:
                    units = '\n' + tokens[1]
                    sh = 0.6
                else:
                    units = ''
                    sh = 0.65
                    
                ax = plt.axes([1-0.085-sw, 0.25, sw, sh])
                self._sliderRange = RangeSlider(ax, 'Range' + units + '\n', orientation='vertical', valmin=rangeVar_min, valmax=rangeVar_max, valinit=(self._min, self._max), valfmt='%d')
                self._sliderRange.on_changed(self._onSliderRangeChange)
                
                ax = plt.axes([1-0.14-sw, 0.863, 0.15, 0.05])
                self._textBoxMax = TextBox(ax, 'Max: ', initial=self._formatForTextBox(self._max))
                self._textBoxMax.on_submit(self._onTextBoxMaxChange)
                
                ax = plt.axes([1-0.14-sw, 0.186, 0.15, 0.05])
                self._textBoxMin = TextBox(ax, 'Min: ', initial=self._formatForTextBox(self._min))
                self._textBoxMin.on_submit(self._onTextBoxMinChange)
                
        else:
            
            self.saveAnimToTempHtmlFile()
            
            
    def _onSliderSizeChange(self, val):
        markerSize = int(val)
        self._scatter.set_sizes(np.full(self._numSegms, markerSize))
        
    def _onSliderOpacityChange(self, val):
        self._balance = val
        self._transformRangeVarToOpacities()
        
    def _onSliderRangeChange(self, val):
        self._min = val[0]
        self._max = val[1]
        self._isProgrammaticTextBoxMinMaxChange = True
        self._textBoxMin.set_val(self._formatForTextBox(val[0]))    # --> _onTextBoxMinChange
        self._textBoxMax.set_val(self._formatForTextBox(val[1]))    # --> _onTextBoxMaxChange
        self._isProgrammaticTextBoxMinMaxChange = False
        self._transformRangeVarToOpacities()
        
    def _onTextBoxMaxChange(self, val):
        if self._isProgrammaticTextBoxMinMaxChange:
            return
        try:
            val = float(val)
        except ValueError:
            return
        self._max = val
        val = (self._min, val)
        self._sliderRange.set_val(val)      # --> _onSliderRangeChange
        
    def _onTextBoxMinChange(self, val):
        if self._isProgrammaticTextBoxMinMaxChange:
            return
        try:
            val = float(val)
        except ValueError:
            return
        self._min = val
        val = (val, self._max)
        self._sliderRange.set_val(val)      # --> _onSliderRangeChange
        
        
    def _formatForTextBox(self, val):
        return '%g' % val
        
    def _getFrameSeq(self):
        while True:
            self._frameIdx = (self._frameIdx + 1) % self._numFrames
            yield self._frameIdx
            
    def _transformRangeVarToOpacities(self):
        temp = logit(self._rangeVar0To1)            # Mapping [0, 1] to (-inf, inf)
        temp += self._balance                       # Balancing opacities
        self._rangeVar0To1Balanced = expit(temp)    # Mapping (-inf, inf) back to [0, 1]
        
        # Replace all values outside the range with 0
        min0To1 = (self._min - self._rangeVar_min) / self._rangeVar_rangeOr1
        max0To1 = (self._max - self._rangeVar_min) / self._rangeVar_rangeOr1
        mask = (self._rangeVar0To1 < min0To1) | (self._rangeVar0To1 > max0To1)
        self._rangeVar0To1Balanced[mask] = 0
        # !! np.clip(self._rangeVar0To1Balanced, min0To1, max0To1, out=self._rangeVar0To1Balanced)
        
        if not self._isAnimRunning:
            self._setOpacitiesOrColours(self._frameIdx)
            
    def _setOpacitiesOrColours(self, frameIdx):
        if self._isOpacitiesOrColours:
            self._scatter.set_alpha(self._rangeVar0To1Balanced[frameIdx])
        else:
            self._scatter.set_array(self._rangeVar[frameIdx])
            
            
if __name__ == '__main__':
    with open('temp.pickle', 'rb') as f:
        data = pickle.load(f)
        
    # !! maybe wrap the ctor call into a please wait box (use tkinter)
    player = Pyplot3dPlayer(
        data['x'],
        data['y'],
        data['z'],
        data['rangeVar'],
        data['numFrames'],
        data['varNameWithIndexAndUnits'],
        data['isOpacitiesOrColours'],
        data['isDesktopOrBrowser'],
        data['rangeVar_min'],
        data['rangeVar_max'])
    
    player.show()
    