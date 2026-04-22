
import numpy as np


class TwoDimPlayerBase:
    
    def getRangeVarSlice(self, rangeVar_2d, gridOfSections, gridSlicerWidget):
        
        nx = int(gridOfSections.nx)
        ny = int(gridOfSections.ny)
        nz = int(gridOfSections.nz)
        
        # !! maybe I need to use gridOfSections here rather than gridSlicerWidget
        projIdx = int(gridSlicerWidget.projIdx)
        
        isOneLayerOrMean = bool(gridSlicerWidget.isOneLayerOrMean)
        layerIdx = int(gridSlicerWidget.sliceIdx_1Based) - 1
        
        # Reshaping from (numFrames, numSegms) to (numFrames, nx, ny, nz) without actual data copying
        numFrames = rangeVar_2d.shape[0]
        rangeVar_4d = np.reshape(rangeVar_2d, (numFrames, nx, ny, nz))
        
        # Reducing from (numFrames, nx, ny, nz) to (numFrames, nx_screen, ny_screen)
        axis = 1 + int(gridSlicerWidget.projIdxToEnumXYZ(projIdx))
        if isOneLayerOrMean:
            slicing = [slice(None)] * 4
            slicing[axis] = layerIdx
            rangeVar_3d = rangeVar_4d[tuple(slicing)]
        else:
            rangeVar_3d = np.mean(rangeVar_4d, axis=axis)
            
        if projIdx != 1:
            # !! check if we need to reverse the data along an axis in some cases (test all projections and both pyplot and plotly)
            # !! BUG: (maybe already fixed - need to test) error when switching between the layer and the mean in GridSlicerWidget
            rangeVar_3d = np.swapaxes(rangeVar_3d, -1, -2)         # !! try to avoid this (maybe there is some option in pyplot and plotly to use the first dimension as x); test this carefully for all the cases
            
        return rangeVar_3d
        
    def getAxisLabels(self, gridSlicerWidget):
        projIdx = int(gridSlicerWidget.projIdx)
        
        xAxisName = 'xzx'[projIdx]
        yAxisName = 'yyz'[projIdx]
        # !! xAxisLabel = f'{xAxisName} (μm)'
        # !! yAxisLabel = f'{yAxisName} (μm)'
        xAxisLabel = f'{xAxisName} index'
        yAxisLabel = f'{yAxisName} index'
        
        return xAxisLabel, yAxisLabel
        