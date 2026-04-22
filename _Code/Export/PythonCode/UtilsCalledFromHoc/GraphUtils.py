
import os
from neuron import h
from TempFolderUtils import TempFolderUtils
from OtherInterModularUtils import codeContractViolation


class GraphUtils:
    
    # This method is just a workaround to achieve what cannot be done in NEURON directly.
    # Looking forward to delete it in favour of smth simple like Graph.getAllVars once NEURON has such a method.
    # The code below works fine in NEURON 8.2.6, but there is no guarantee for the future versions.
    # Warning: The usage of h.save_session below imposes one extra requirement on all templated widgets shown on the screen at the moment when we call this method.
    #          Particularly, for each shown widget, all variables being its data members and exposed with "xpvalue" must be declared as "public".
    #          Otherwise, we hit the error of type "{varName} not a public member of {widgetTemplName}" when calling GraphUtils.parseVarsFromTheGraph.
    #          Alternatively, to avoid the error, we must hide the widget automatically when user opens ExportManagerMainWidget.
    def parseVarsFromTheGraph(varsList):
        
        tempFolderPath = '_Code\\Export\\' + TempFolderUtils.tempFolderName
        sesFileName = 'last_session.ses'
        
        TempFolderUtils.createOrCleanUpTempFolder(tempFolderPath)
        
        sesFilePath = os.path.join(tempFolderPath, sesFileName)
        h.save_session(sesFilePath)
        
        # Find a particular Graph, then parse its vars
        isStartFound = False
        isEndFound = False
        with open(sesFilePath, 'r') as file:
            for line in file:
                if not isStartFound:
                    # Keep the var name in sync with WatchedVarsAndRecorderSettingsWidget.show
                    if line.startswith('someUniqueNameForTheParsedGraph = '):
                        isStartFound = True
                else:
                    # It turns out, NEURON saves the same variable using "addvar" or "addexpr" depending on
                    # how it was chosen by user in "Plot what?" widget:
                    # * Double click in the second list, then "Accept" => "addvar"
                    # * Single click in the second list, then "Accept" => "addexpr"
                    if '.addvar(' in line or '.addexpr(' in line:
                        startIdx = line.index('"') + 1
                        endIdx = line.index('"', startIdx)
                        varStr = line[startIdx : endIdx]
                        varsList.append(h.String(varStr))
                    elif line.startswith('}'):
                        isEndFound = True
                        break
                        
        if not (isStartFound and isEndFound):
            codeContractViolation()
            
        TempFolderUtils.deleteTempFolder(tempFolderPath)
        