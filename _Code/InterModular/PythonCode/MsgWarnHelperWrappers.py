
from neuron import h


class PleaseWaitBox:
    # Data member: _lines
    
    def __init__(self, *lines):
        self._lines = lines
        
    def __enter__(self):
        h.mwh.showPleaseWaitBox(*self._lines)
        return None
        
    def __exit__(self, exc_type, exc_value, traceback):
        # In case of exception, keeping the "please wait" box on the screen
        if exc_type is None:
            h.mwh.hidePleaseWaitBox()
        return False
        
class MsgWarnInterceptor:
    
    def __enter__(self):
        h.mwh.startIntercepting()
        return None
        
    def __exit__(self, exc_type, exc_value, traceback):
        # In case of exception, showing all intercepted messages and warnings now
        h.mwh.endIntercepting()
        return False
        