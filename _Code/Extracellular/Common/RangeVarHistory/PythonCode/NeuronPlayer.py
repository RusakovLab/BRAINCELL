
class NeuronPlayer:
    
    # Data member added in the ctor:
    #   _neuronPlayerWidget
    
    def __init__(self, rangeVar, t, varNameWithIndex, rangeVar_min, rangeVar_max, neuronPlayerWidget):
        neuronPlayerWidget.onPlayerInit(rangeVar, t, varNameWithIndex, rangeVar_min, rangeVar_max)
        self._neuronPlayerWidget = neuronPlayerWidget
        
    def show(self):
        self._neuronPlayerWidget.onPlayerShow()
        