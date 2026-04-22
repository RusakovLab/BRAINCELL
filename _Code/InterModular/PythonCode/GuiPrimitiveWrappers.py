
# Helper wrapper classes for h.xpanel, h.VBox, h.HBox and h.Deck making the code shorter, more readable and Pythonic.
# The wrappers support some handy options like "elastic panel", empty panel or skipping "-1, -1".

# !! try to move the IF from __exit__ to _Mappable

# !! maybe somebody already implemented these "with" wrappers for NEURON GUI primitives -- need to look for a 3rd party package


from neuron import h


class Panel:
    # No data members
    
    def __enter__(self):
        h.xpanel('')
        return None
        
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            h.xpanel()
        return False
        
class _Mappable:
    # Data member: _mapArgs
    
    def __init__(self, mapArgs):
        numArgs = len(mapArgs)
        expNumArgs = (0, 3, 5)
        if numArgs == 3:
            mapArgs = mapArgs + (-1, -1)
        elif numArgs not in expNumArgs:
            # !! maybe use codeContractViolation here
            raise ValueError(f'Expected {expNumArgs} arguments, but got {numArgs}')
            
        self._mapArgs = mapArgs
        
class VBox(_Mappable):
    # Data members: _mapArgs (in _Mappable), _panel, _map, _vBox, _deck
    
    def __init__(self, *mapArgs, panel=False, map=True):
        """
        The panel is elastic (using Deck with just 1 card);
        WARNING: Don't pass "panel=True" if the VBox will contain something below the panel.
        """
        
        _Mappable.__init__(self, mapArgs)
        
        self._panel = panel
        self._map = map
        
    def __enter__(self):
        self._vBox = h.VBox()
        self._vBox.intercept(1)
        if self._panel:
            self._deck = h.Deck()
            self._deck.intercept(1)
            h.xpanel('')
        return self._vBox
        
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            if self._panel:
                h.xpanel()
                self._deck.intercept(0)
                self._deck.flip_to(0)
                self._deck.map()
            self._vBox.intercept(0)
            if self._map:
                self._vBox.map(*self._mapArgs)
        return False
        
class HBox(_Mappable):
    # Data members: _mapArgs (in _Mappable), _hBox
    
    def __init__(self, *mapArgs):
        _Mappable.__init__(self, mapArgs)
        
    def __enter__(self):
        self._hBox = h.HBox()
        self._hBox.intercept(1)
        return self._hBox
        
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self._hBox.intercept(0)
            self._hBox.map(*self._mapArgs)
        return False
        
class Deck(_Mappable):
    # Data members: _mapArgs (in _Mappable), _emptyPanel, _panel, _deck
    
    def __init__(self, *mapArgs, emptyPanel=False, panel=False):
        _Mappable.__init__(self, mapArgs)
        
        self._emptyPanel = emptyPanel
        self._panel = panel
        
    def __enter__(self):
        self._deck = h.Deck()
        self._deck.intercept(1)
        if self._emptyPanel:
            h.createEmptyPanel()
        if self._panel:
            h.xpanel('')
        return self._deck
        
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            if self._panel:
                h.xpanel()
            self._deck.intercept(0)
            self._deck.map(*self._mapArgs)
        return False
        