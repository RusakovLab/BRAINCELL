
# !! TODOs:
#   1. when importing a HOC file, we lose all biophysics; in order to keep it, consider two options:
#      * update "wrapper1.hoc" to export a biophys JSON file in our format and then import it after the SWC file
#      * check if MorphML, Neurolucida or Eutectic supports biophysics; if so, look for corresponding "hoc2swc" alternative
#        (and don't forget to switch the output file format for "NLMorphologyConverter" to preserve biophysics from other input file formats)
#   2. it looks like BrainCell is a bit more accurate than hoc2swc in derivation of section type from section name
#      (at least for the soma section in "cellmorphology.hoc", which is named as a dendrite after loading the SWC file);
#      so prepare a new mapper based on our "func chooseDefaultSelectedNamesForCompartments" and embed it into hoc2swc as following:
#          from hoc2swc import swc_type_from_section_name
#          swc_type_from_section_name.__code__ = new_map.__code__
#   3. it would be nice to support the import of Python files which do "from neuron import h" and then create h.Section-s
#      (not only as an extra cell, but also as a "Base Geometry" file)

# !! investigate what difference we have in the results when importing a "Base Geometry" (no Import3d used) and an extra cell (Import3d used)

# !! a good list of file formats:
#       https://github.com/NeuroMorpho/xyz2swc?tab=readme-ov-file#supported-tools-and-formats

# !! a good collection of test files of different formats:
#       https://github.com/NeuroMorpho/xyz2swc/tree/main/input/to_convert


import os
import glob
import pickle
import subprocess
import sys

from neuron import h

from OtherInterModularUtils import convertPyIterableOfSecsToHocListOfSecRefs


h.load_file('import3d.hoc')

# "import3d.hoc" loads "import3d/import3d_gui.hoc" which loads "celbild.hoc"

if h.name_declared('restoreDefaultPanelScrollIvocStyle'):
    h.restoreDefaultPanelScrollIvocStyle()


class ExtraCell:
    
    # Data members added in the ctor:
    #   list_ref, _topLevelHocObjName
    #   filePathName, list_ref, _topLevelHocObjName
    
    def __init__(self, filePathName, tempFolderPath, topLevelHocObjName):
        """Read geometry from a given file and create a cell"""
        
        self._topLevelHocObjName = topLevelHocObjName
        self.filePathName = filePathName
        
        # Here is what NEURON supports via NEURON Main Menu -> Tools -> Miscellaneous -> Import 3D;
        # the code is here: %NEURONHOME%\lib\hoc\import3d\import3d_gui.hoc  ->  func some_format()
        #   * Import3d_MorphML
        #   * Import3d_SWC_read
        #   * Import3d_Neurolucida_read
        #   * Import3d_Eutectic_read
        #   * Import3d_Neurolucida3
        
        # Some examples of usage for "Import3d":
        #   * https://www.neuron.yale.edu/neuron/docs/extracellular-diffusion
        #   * https://nrn.readthedocs.io/en/latest/rxd-tutorials/extracellular.html
        #   * https://nrn.readthedocs.io/en/latest/guide/bio_faq.html
        #   * https://nrn.readthedocs.io/en/latest/guide/import3d.html
        
        # !! we also have HOC:getFileExtLowerCase
        fileExtLower = os.path.splitext(filePathName)[-1].lower()
        
        if filePathName.lower().endswith('.morph.xml'):
            i3dReader = h.Import3d_MorphML()
        elif fileExtLower == '.swc':    # !! we could add *.eswc here, but it would produce a lot of warnings
            i3dReader = h.Import3d_SWC_read()
        # !! elif fileExtLower == ???: # !! it looks like *.asc, *.dat, *.nrx and *.xml are not supported here
        #     i3dReader = h.Import3d_Neurolucida_read()
        elif fileExtLower == '.nts':
            i3dReader = h.Import3d_Eutectic_read()
        elif fileExtLower == '.asc':    # !! it looks like *.dat, *.nrx and *.xml are not supported here
            i3dReader = h.Import3d_Neurolucida3()
            
        elif fileExtLower == '.zip':
            if h.name_declared('createOrCleanUpTempFolderForImport'):
                h.createOrCleanUpTempFolderForImport()
            
            swcFilePathName = h.ref('')
            h.importSwcFileFromZipArchive_prologue(filePathName, swcFilePathName)
            filePathName = swcFilePathName
            
            i3dReader = h.Import3d_SWC_read()
            
        elif fileExtLower == '.hoc':
            
            if h.name_declared('createOrCleanUpTempFolderForImport'):
                h.createOrCleanUpTempFolderForImport()
            else:
                os.makedirs(tempFolderPath, exist_ok=True)
            # !! normalize path separators for Windows compatibility
            tempFolderPathNorm = tempFolderPath.replace('\\', '/')
            
            swcFilePathName = tempFolderPath + '/last_converted.swc'
            
            #scriptFileDirPath = os.path.dirname(os.path.abspath(__file__)) + '/Separated'
            _thisDir = os.path.dirname(os.path.abspath(__file__))
            _separatedPath = os.path.join(_thisDir, 'Separated')
            if not os.path.isdir(_separatedPath) or not os.path.exists(os.path.join(_separatedPath, 'wrapper1.hoc')):
                for _p in sys.path:
                    _candidate = os.path.join(_p, 'Separated')
                    if os.path.isdir(_candidate) and os.path.exists(os.path.join(_candidate, 'wrapper1.hoc')):
                        _separatedPath = _candidate
                        break
            scriptFileDirPath = _separatedPath
            scriptFileName = 'wrapper1.hoc'
            
            data = {
                'hocFilePathName': filePathName,
                'swcFilePathName': swcFilePathName}
                
            with open(scriptFileDirPath + '/temp.pickle', 'wb') as f:
                pickle.dump(data, f)
                
            neuronAppPathName = h.neuronhome() + '/bin/neuron.exe'
            
            print('')
            process = subprocess.Popen([neuronAppPathName, scriptFileName], cwd=scriptFileDirPath)
            process.wait()
            # !! wrapper1.hoc crashes with segfault on exit (NEURON 8.2 known issue),
            # !! but the SWC file may still be written; wait for it
            import time
            _deadline = time.time() + 10.0  # wait up to 10 seconds
            while time.time() < _deadline:
                if os.path.exists(swcFilePathName):
                    break
                time.sleep(0.2)    
            swcFilesPathNamePattern = tempFolderPath + '/last_converted*.swc'
            filePathNames = glob.glob(swcFilesPathNamePattern)
            
            if len(filePathNames) == 0:
              raise RuntimeError(
               f"ExtraCell: wrapper1.hoc did not produce any SWC file.\n"
               f"Pattern searched: '{swcFilesPathNamePattern}'\n"
               f"Check NEURON console output above."
              )
            elif len(filePathNames) == 1:
                 filePathName = filePathNames[0]
            else:
               print("\n     WARNING: There is more than one root in the topology. We'll import only the biggest tree.\n")
               filePathName = max(filePathNames, key=os.path.getsize)

            i3dReader = h.Import3d_SWC_read()
            
        else:
            
            # Make sure that Microsoft Visual C++ 2010 Redistributable Package is installed
            if h.name_declared('createOrCleanUpTempFolderForImport'):
                h.createOrCleanUpTempFolderForImport()
            
            swcFilePathName = h.ref('')
            h.convertFileToSwcWithNLMorphologyConverter(filePathName, swcFilePathName)
            
            filePathName = swcFilePathName
            i3dReader = h.Import3d_SWC_read()
            
            
        i3dReader.input(filePathName)
        
        i3dGui = h.Import3d_GUI(i3dReader, 0)   # !! what does 2nd optional arg mean?
        
        # !! i3dGui.build_panel()               # !! it looks like this already supports translation, rotation and scaling -- should we use it?
        
        # This is the only command which makes us use a Python class here rather than a HOC template
        i3dGui.instantiate(self)                # !! what does 2nd optional arg mean?
        
        self.list_ref = convertPyIterableOfSecsToHocListOfSecRefs(self.all)
        
    def __str__(self):
        # Without this, the new sections won't be accessible via the standard tool:
        #   "Graph -> Plot what?", then "Show -> Python Sections"
        # The name must be in sync with the one used in hoc:ExtraCellListItem.createNewTopLevelHocObjRefAndAssignPyExtraCell
        return self._topLevelHocObjName
        