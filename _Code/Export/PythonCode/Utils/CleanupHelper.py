
from Utils.OtherUtils import emptyParagraphHint, codeContractViolation


class CleanupHelper:
    
    _start = 'objref '
    _sep = ', '
    
    def __init__(self):
        self._newLines = []
        
    def scheduleCleanup(self, line):
        if not line.startswith(self._start):
            codeContractViolation()
            
        objrefNames = line[len(self._start) :] \
            .split(self._sep)
            
        if self._newLines:
            self._newLines.append('')
            
        for objrefName in objrefNames:
            self._newLines.append(f'{objrefName} = nil')
            
    def makeCleanup(self):
        if self._newLines:
            return self._newLines
        else:
            return emptyParagraphHint()
            