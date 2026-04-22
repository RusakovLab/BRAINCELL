

# !! think about converting to [numFrames][nx_screen, ny_screen] for better performance
#    in rangeVar_3d[frameIdx]


# !! don't forget to use the actual x, y and time rather than indices

# !! make sure we have the equal scale by x and y even though dx != dy



# !! BUG: the image is not shown in the centre of the figure and overlaps with the slider and button


# !! do I need to use ax.set_aspect('equal') here?
#    it looks like it already preserves proportions when dx=dy, but need to check the case dx != dy


# !! test slices and projections carefully


from Separated.PyplotPlayerBase import PyplotPlayerBase
from Separated.TwoDimPlayerBase import TwoDimPlayerBase

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import numpy as np

from Separated.FakeGridOfSections import FakeGridOfSections
from Separated.FakeGridSlicerWidget import FakeGridSlicerWidget
import pickle


class Pyplot2dPlayer(PyplotPlayerBase, TwoDimPlayerBase):
    
    _rangeVar_3d = None
    
    _axesImage = None
    
    
    def __init__(self, rangeVar_2d, gridOfSections, gridSlicerWidget, varNameWithIndexAndUnits, isDesktopOrBrowser, rangeVar_min, rangeVar_max):
        
        numFrames = rangeVar_2d.shape[0]
        
        self._isDesktopOrBrowser = bool(isDesktopOrBrowser)
        
        # Reducing/transposing from (numFrames, numSegms) to (numFrames, nx_screen, ny_screen)
        rangeVar_3d = self.getRangeVarSlice(rangeVar_2d, gridOfSections, gridSlicerWidget)
        
        fig = plt.figure()
        
        # !! BUG: not shown in the centre of the figure and overlaps with the slider and button
        self._axesImage = plt.imshow(rangeVar_3d[0], vmin=rangeVar_min, vmax=rangeVar_max, origin='lower')
        
        # !! trying to center the image, but it doesn't work
        """
        width, height = rangeVar_3d.shape[1], rangeVar_3d.shape[2]
        h_offset = width / 2
        v_offset = height / 2
        
        ax = fig.add_subplot(111)
        
        self._axesImage = ax.imshow(rangeVar_3d[0], vmin=rangeVar_min, vmax=rangeVar_max, origin='lower', extent=[-h_offset, h_offset, -v_offset, v_offset])
        
        # Set the aspect ratio to be equal (preserve proportions)
        ax.set_aspect('equal')
        """
        
        xAxisLabel, yAxisLabel = self.getAxisLabels(gridSlicerWidget)
        plt.xlabel(xAxisLabel)
        plt.ylabel(yAxisLabel)
        
        plt.title(varNameWithIndexAndUnits)
        
        # !! maybe move this to PyplotPlayerBase
        interval = 0 if self._isDesktopOrBrowser else 1     # ms
        self._ani = FuncAnimation(fig, self._onNewFrame, frames=numFrames, interval=interval)
        
        # !! maybe move this to PyplotPlayerBase
        # Add a color bar to indicate the values
        colorBar = plt.colorbar(self._axesImage)
        colorBar.ax.set_title(varNameWithIndexAndUnits)
        
        # Adjust the margins of the entire figure to bring the colorbar closer to the edge
        fig.subplots_adjust(right=1)
        
        self._rangeVar_3d = rangeVar_3d
        
        self._showDataFromThisFrame = self._setColours
        
        if self._isDesktopOrBrowser:
            self.createStartStopButtonFrameSliderAndDensityStrip(rangeVar_3d)
        else:
            self.saveAnimToTempHtmlFile()
            
            
    def _setColours(self, frameIdx):
        # !! BUG: when switching projection, moving slider and starting the animation, sometimes we catch the next error:
        #         IndexError: index {N} is out of bounds for axis 0 with size {N}
        self._axesImage.set_data(self._rangeVar_3d[frameIdx])
        
        
if __name__ == '__main__':
    with open('temp.pickle', 'rb') as f:
        data = pickle.load(f)
        
    # !! maybe wrap the ctor call into a please wait box (use tkinter)
    player = Pyplot2dPlayer(
        data['rangeVar'],
        data['gridOfSections'],
        data['gridSlicerWidget'],
        data['varNameWithIndexAndUnits'],
        data['isDesktopOrBrowser'],
        data['rangeVar_min'],
        data['rangeVar_max'])
    
    player.show()
    