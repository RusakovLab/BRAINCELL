
from abc import ABC, abstractmethod

# Use these three abstract base classes when implementing a new Python simulation as following:
#   class MyNewPythonSimulation([RequiresAltRunControl], [UsesCustomProcAdvance], Simulation):
#       ...
# "Simulation" is required, the other two are optional.
#
# WARNING: Make sure "Simulation" goes last in the inheritance list.

class Simulation(ABC):
    
    biophysJsonFileNameOrEmpty = ''
    isCustomProcAdvance = False
    isAltRunControl = False
    
    @abstractmethod
    def preShowCheck(self):
        pass
        
    @abstractmethod
    def show(self, isFirstShow):
        pass
        
    @abstractmethod
    def simDismissHandler(self):
        pass
        
class UsesCustomProcAdvance(ABC):
    
    isCustomProcAdvance = True
    
    @abstractmethod
    def advance(self):
        pass                # !! maybe call h.fadvance() here?
        
class RequiresAltRunControl(ABC):
    
    isAltRunControl = True
    
    @abstractmethod
    def preRun(self, isInitOnly):
        pass
        
    @abstractmethod
    def preContinue(self):
        pass
        
    @abstractmethod
    def postRun(self):
        pass
        