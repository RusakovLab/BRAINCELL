
class FakeGridOfSections:
    
    # Data members added in the ctor:
    #   nx, ny, nz
    
    def __init__(self, gridOfSections):
        self.nx = gridOfSections.nx
        self.ny = gridOfSections.ny
        self.nz = gridOfSections.nz
        