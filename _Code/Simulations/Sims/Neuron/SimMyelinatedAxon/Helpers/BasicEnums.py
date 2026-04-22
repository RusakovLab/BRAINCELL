
from enum import Enum

class EnumAxonGeometry(Enum):
    imported = 0
    predefined = 1
    drawnByHand = 2
    
class EnumMyelSheath(Enum):
    deploy = 0
    scalp = 1
    remove = 2
    
# See also: MyelRegionHelper.EnumMyelRegion and DirtyStatesHelper.EnumParamCats
