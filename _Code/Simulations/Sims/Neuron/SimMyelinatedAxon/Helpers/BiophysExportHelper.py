
import json
import os
from datetime import datetime

from neuron import h


class BiophysExportHelper:
    """Exports the current biophysics mechanism state from all MechComps to JSON and TXT files.
    
    The JSON output matches the format of SimMyelinatedAxon.json so it can be used
    as a drop-in replacement for the baseline biophysics file.
    
    The TXT output is a human-readable summary including GUI parameters and
    all mechanism parameters per compartment.
    """
    
    def __init__(self, paramsHelper, presParams):
        self._params = paramsHelper
        self._presParams = presParams
        self._jsonFilePathName = None
        self._txtFilePathName = None
        
    def exportCheckBoxHandler(self):
        """Called when the user toggles the export checkbox. Opens a file dialog to choose location."""
        
        if not self._presParams.isExportBiophys:
            return
        
        filePathNameRef = h.ref('')
        
        # Use the existing text file type for the dialog; we'll override extensions ourselves
        isCancel = h.fbh.showSaveFileDialog(h.pyEnumOutFileTypes.textResultsTxtSMA, filePathNameRef)
        
        if isCancel:
            self._presParams.isExportBiophys = False
            return
        
        basePath = filePathNameRef[0]
        
        # Strip any extension the dialog may have added, derive both file paths
        base, _ = os.path.splitext(basePath)
            
        self._jsonFilePathName = base + '.json'
        self._txtFilePathName = base + '.txt'
        
    def exportOnPreRun(self, simSettings=None):
        """Called during preRun to export the current biophysics state.
        
        Args:
            simSettings: optional dict of simulation mode settings for the TXT header
        """
        
        if not self._presParams.isExportBiophys:
            return
            
        if self._jsonFilePathName is None:
            return
        
        biophysDict = self._collectBiophysFromAllComps()
        guiParams = self._collectGuiParams()
        
        with open(self._jsonFilePathName, 'w') as f:
            json.dump(biophysDict, f, indent=4)
        print('Biophysics JSON exported to: %s' % self._jsonFilePathName)
            
        self._writeTxtFile(self._txtFilePathName, guiParams, biophysDict, simSettings)
        print('Biophysics TXT exported to: %s' % self._txtFilePathName)
        
    def _collectBiophysFromAllComps(self):
        """Iterate through all MechComps and extract mechanism parameters from a representative section."""
        
        biophysDict = {}
        
        for compIdx in range(len(h.mmAllComps)):
            comp = h.mmAllComps[compIdx]
            compName = comp.name
            
            # Get a representative section from this comp
            if comp.list_ref.count() == 0:
                continue
            sec = comp.list_ref[0].sec
            
            compDict = {}
            
            # Get all density mechanisms inserted in this section
            mt = h.MechanismType(0)  # 0 = distributed mechanisms
            for mechIdx in range(int(mt.count())):
                mt.select(mechIdx)
                mechNameRef = h.ref('')
                mt.selected(mechNameRef)
                mechName = mechNameRef[0]
                
                # Check if this mechanism is inserted in the section
                if not hasattr(sec(0.5), mechName):
                    # Some mechanisms don't map to segment attributes directly;
                    # use ismembrane as a more reliable check
                    pass
                    
                if not h.ismembrane(mechName, sec=sec):
                    continue
                    
                # Special case: skip i2fc (internal flux converter, not user-editable biophysics)
                if mechName == 'i2fc':
                    continue
                    
                # Read parameters using MechanismStandard
                ms = h.MechanismStandard(mechName, 1)  # 1 = PARAMETER panel variables
                numParams = int(ms.count())
                
                if numParams == 0:
                    # Mechanism with no editable parameters (e.g. na_ion, k_ion)
                    compDict[mechName] = {}
                else:
                    paramDict = {}
                    for paramIdx in range(numParams):
                        paramNameRef = h.ref('')
                        ms.name(paramNameRef, paramIdx)
                        fullParamName = paramNameRef[0]  # e.g. "gnabar_hh"
                        
                        # Get the value from the section
                        # fullParamName includes the suffix, e.g. "gnabar_hh"
                        val = getattr(sec(0.5), fullParamName)
                        
                        # Get units
                        unitsStr = h.units(fullParamName)
                        
                        # Format the key to match JSON convention: "paramName (units)"
                        if unitsStr:
                            paramKey = '%s (%s)' % (fullParamName, unitsStr)
                        else:
                            paramKey = fullParamName
                            
                        paramDict[paramKey] = val
                        
                    compDict[mechName] = {"PARAMETER": paramDict}
                    
            biophysDict[compName] = compDict
            
        return biophysDict
        
    def _collectGuiParams(self):
        """Collect all GUI parameters from ParamsHelper."""
        
        p = self._params
        params = {}
        
        # Geometry
        params['diam_axon (um)'] = float(p.diam_axon)
        params['diam_sheath (um)'] = float(p.diam_sheath)
        params['L_axon (um)'] = float(p.L_axon)
        params['nseg_axon'] = int(p.nseg_axon)
        
        # Schwann layout
        params['schwann1_start'] = float(p.schwann1_start)
        params['schwann1_end'] = float(p.schwann1_end)
        params['schwann2_start'] = float(p.schwann2_start)
        params['maxNumSchwannCells'] = int(p.maxNumSchwannCells)
        
        # Radial grid
        params['numInnerShells'] = int(p.numShells)
        params['numExtShells'] = int(p.numExtShells)
        params['Rmax (um)'] = float(p.Rmax)
        params['alpha'] = float(p.alpha)
        params['schwannKoShell'] = int(p.schwannKoShell)
        
        # Diffusion and concentration
        params['Diff_k (um2/ms)'] = float(p.Diff_k)
        params['ko0 (mM)'] = float(p.ko0)
        params['ki0 (mM)'] = float(p.ki0)
        params['veryMinOuterConc (mM)'] = float(p.veryMinOuterConc)
        
        # Timing
        params['Dt (ms)'] = float(p.Dt)
        params['dt (ms)'] = float(h.dt)
        params['tstop (ms)'] = float(h.tstop)
        
        # Global NEURON params
        params['celsius'] = float(h.celsius)
        params['v_init (mV)'] = float(h.v_init)
        
        return params
        
    def _writeTxtFile(self, txtFilePathName, guiParams, biophysDict, simSettings):
        """Write human-readable TXT summary."""
        
        with open(txtFilePathName, 'w') as f:
            
            f.write('=' * 70 + '\n')
            f.write('  Biophysics Parameter Export\n')
            f.write('  %s\n' % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            f.write('=' * 70 + '\n\n')
            
            # Simulation settings (mode, clamps, presentation)
            if simSettings:
                f.write('-' * 70 + '\n')
                f.write('  Simulation Settings\n')
                f.write('-' * 70 + '\n\n')
                for key, val in simSettings.items():
                    f.write('  %-35s  %s\n' % (key, val))
                f.write('\n')
            
            # GUI parameters
            f.write('-' * 70 + '\n')
            f.write('  Simulation Parameters (from GUI)\n')
            f.write('-' * 70 + '\n\n')
            
            for key, val in guiParams.items():
                f.write('  %-30s  %s\n' % (key, val))
                
            f.write('\n')
            
            # Mechanism parameters per compartment
            f.write('-' * 70 + '\n')
            f.write('  Mechanism Parameters (per compartment)\n')
            f.write('-' * 70 + '\n\n')
            
            for compName, compDict in biophysDict.items():
                f.write('[%s]\n' % compName)
                
                if not compDict:
                    f.write('  (no mechanisms)\n\n')
                    continue
                    
                for mechName, mechData in compDict.items():
                    if not mechData:
                        f.write('  %s\n' % mechName)
                    else:
                        f.write('  %s:\n' % mechName)
                        paramDict = mechData.get('PARAMETER', {})
                        for paramKey, val in paramDict.items():
                            f.write('    %-40s  %g\n' % (paramKey, val))
                            
                f.write('\n')
                
            f.write('=' * 70 + '\n')
            f.write('  End of export\n')
            f.write('=' * 70 + '\n')
