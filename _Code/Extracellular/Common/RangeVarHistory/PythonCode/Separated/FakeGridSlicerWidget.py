
class FakeGridSlicerWidget:
    
    # Data members added in the ctor:
    #   projIdx, isOneLayerOrMean, sliceIdx_1Based
    
    def __init__(self, gridSlicerWidget):
        self.projIdx = gridSlicerWidget.projIdx
        self.isOneLayerOrMean = gridSlicerWidget.isOneLayerOrMean
        self.sliceIdx_1Based = gridSlicerWidget.sliceIdx_1Based
        
    # !! code dup. with hoc:GridSlicerWidget.projIdxToEnumXYZ
    def projIdxToEnumXYZ(self, projIdx):
        return (2 + projIdx) % 3
        