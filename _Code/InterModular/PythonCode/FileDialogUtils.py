
import os
import tkinter as tk
from enum import Enum
from tkinter import filedialog, messagebox


root = tk.Tk()
root.withdraw()


class FileDialogUtils:

    class EnumInFileTypes(Enum):
        baseGeometryAny = 0
        baseGeometryHoc = 1
        extraCellAny = 2
        nanoGeometryHoc = 3
        biophysJson = 4
        binaryResultsBin = 5
        binaryResultsBinA = 6
        binaryResultsBinB = 7
        """ !! in the future, we can add support for:
        distFuncHoc
        distFuncPy
        distFuncTxt
        distFuncXlsx
        diamDistrFile
        """
        
    class EnumOutFileTypes(Enum):
        baseGeometryHoc = 0
        nanoGeometryHoc = 1
        nsgDataZip = 2
        biophysJson = 3
        binaryResultsBin = 4
        textResultsTxt = 5
        binaryResultsBinA = 6
        textResultsTxtA = 7
        binaryResultsBinB = 8
        textResultsTxtB = 9
        textResultsTxtSMA = 10
        """ !! in the future, we can add support for these files saved to "Text results" folder:
        volumFractionTxt
        cadynamicsTxt
        circularFrapAverageTxt
        timeFRAPTxt
        """
        
    _inFileTypeToArgsDict = {
        EnumInFileTypes.baseGeometryAny: {
            'title': 'Import brain cell base geometry',
            'initialdir': 'Geometry',
            'filetypes': [('All Files', '*.*'), ('NEURON HOC File', '*.hoc'), ('SWC or ESWC File', '*.swc;*.eswc'), ('MorphML XML File', '*.morph.xml'), ('Eutectics NTS File', '*.nts'), ('Neurolucida Files', '*.asc;*.dat;*.nrx;*.xml'), ('Genesis P File', '*.p'), ('Imaris IMS File', '*.ims'), ('NeuronJ NDF File', '*.ndf'), ('NINDS3D ANAT File', '*.anat'), ('PSICS XML File', '*.xml'), ('ZIP Archive from NeuroMorpho.org', '*.zip')]},  # !! TODO: enlist other file types mentioned in the NLMorphologyConverter docs (e.g. ArborVitae, Douglas3D, Glasgow, GulyasTree, AmiraMesh, MaxSim, NeuroML, NeuroZoom, Nevin, Oxford, Amaral, Korogod), but test them first and add to the repository
        EnumInFileTypes.baseGeometryHoc: {
            'title': 'Import external NEURON simulation',
            'initialdir': 'External simulations',
            'filetypes': [('NEURON HOC File', '*.hoc'), ('All Files', '*.*')],
            'defaultextension': '.hoc'},
        EnumInFileTypes.extraCellAny: {
            'title': 'Import extra cell',
            'initialdir': 'Geometry',
            'filetypes': [('All Files', '*.*'), ('NEURON HOC File', '*.hoc'), ('SWC or ESWC File', '*.swc;*.eswc'), ('MorphML XML File', '*.morph.xml'), ('Eutectics NTS File', '*.nts'), ('Neurolucida Files', '*.asc;*.dat;*.nrx;*.xml'), ('Genesis P File', '*.p'), ('Imaris IMS File', '*.ims'), ('NeuronJ NDF File', '*.ndf'), ('NINDS3D ANAT File', '*.anat'), ('PSICS XML File', '*.xml'), ('ZIP Archive from NeuroMorpho.org', '*.zip')]},  # !! see the comment for baseGeometryAny
        EnumInFileTypes.nanoGeometryHoc: {
            'title': 'Import brain cell with nanogeometry',
            'initialdir': 'Nanogeometry',
            'filetypes': [('NEURON HOC File', '*.hoc'), ('All Files', '*.*')],
            'defaultextension': '.hoc'},
        EnumInFileTypes.biophysJson: {
            'title': 'Import brain cell biophysics',
            'initialdir': 'Biophysics',
            'filetypes': [('JSON File', '*.json'), ('All Files', '*.*')],
            'defaultextension': '.json'},
        EnumInFileTypes.binaryResultsBin: {
            'title': 'Load outside-in diffusion animation',
            'initialdir': 'Binary results',
            'filetypes': [('BIN File', '*.oid'), ('All Files', '*.*')],
            'defaultextension': '.oid'},
        EnumInFileTypes.binaryResultsBinA: {
            'title': 'Load conc on membrane for inside-out diffusion',
            'initialdir': 'Binary results',
            'filetypes': [('BIN File', '*.iod_a'), ('All Files', '*.*')],
            'defaultextension': '.iod_a'},
        EnumInFileTypes.binaryResultsBinB: {
            'title': 'Load inside-out diffusion animation',
            'initialdir': 'Binary results',
            'filetypes': [('BIN File', '*.iod_b'), ('All Files', '*.*')],
            'defaultextension': '.iod_b'}
    }
    
    _outFileTypeToArgsDict = {
        EnumOutFileTypes.baseGeometryHoc: {
            'title': 'Export brain cell base geometry',
            'initialdir': 'Geometry',
            'filetypes': [('NEURON HOC File', '*.hoc'), ('All Files', '*.*')],
            'defaultextension': '.hoc'},
        EnumOutFileTypes.nanoGeometryHoc: {
            'title': 'Export brain cell with nanogeometry',
            'initialdir': 'Nanogeometry',
            'filetypes': [('NEURON HOC File', '*.hoc'), ('All Files', '*.*')],
            'defaultextension': '.hoc'},
        EnumOutFileTypes.nsgDataZip: {
            'title': 'Export BrainCell simulation',
            'initialdir': 'Nanogeometry',
            'filetypes': [('ZIP archive for NSG supercomputer', '*.zip'), ('All Files', '*.*')],
            'defaultextension': '.zip'},
        EnumOutFileTypes.biophysJson: {
            'title': 'Export brain cell biophysics',
            'initialdir': 'Biophysics',
            'filetypes': [('JSON File', '*.json'), ('All Files', '*.*')],
            'defaultextension': '.json'},
        EnumOutFileTypes.binaryResultsBin: {
            'title': 'Save outside-in diffusion animation',
            'initialdir': 'Binary results',
            'filetypes': [('BIN File', '*.oid'), ('All Files', '*.*')],
            'defaultextension': '.oid'},
        EnumOutFileTypes.textResultsTxt: {
            'title': 'Save outside-in diffusion animation',
            'initialdir': 'Text results',
            'filetypes': [('TXT File', '*.txt'), ('All Files', '*.*')],
            'defaultextension': '.txt'},
        EnumOutFileTypes.binaryResultsBinA: {
            'title': 'Save conc on membrane for inside-out diffusion',
            'initialdir': 'Binary results',
            'filetypes': [('BIN File', '*.iod_a'), ('All Files', '*.*')],
            'defaultextension': '.iod_a'},
        EnumOutFileTypes.textResultsTxtA: {
            'title': 'Save conc on membrane for inside-out diffusion',
            'initialdir': 'Text results',
            'filetypes': [('TXT File', '*.txt'), ('All Files', '*.*')],
            'defaultextension': '.txt'},
        EnumOutFileTypes.binaryResultsBinB: {
            'title': 'Save inside-out diffusion animation',
            'initialdir': 'Binary results',
            'filetypes': [('BIN File', '*.iod_b'), ('All Files', '*.*')],
            'defaultextension': '.iod_b'},
        EnumOutFileTypes.textResultsTxtB: {
            'title': 'Save inside-out diffusion animation',
            'initialdir': 'Text results',
            'filetypes': [('TXT File', '*.txt'), ('All Files', '*.*')],
            'defaultextension': '.txt'},
        EnumOutFileTypes.textResultsTxtSMA: {
            'title': 'Save K+ conc(t, dist, radius) to TXT file',
            'initialdir': 'Text results',
            'filetypes': [('TXT File', '*.txt'), ('All Files', '*.*')],
            'defaultextension': '.txt'}
    }
    
    # !! keep these file names in sync with other code
    _reservedHocFileNamesLower = {'params.hoc', 'runner.hoc'}
    _reservedJsonFileNamesLower = {'hide_stoch_btn_for.json', 'diffusible_species.json', 'gap_junc_ptr_info.json'}
    
    _isBusy = False
    _top = None
    
    # !! BUG: import biophysics -> leave dialog open -> export biophysics -> click "Export" -> it puts the old "import" file dialog in focus
    #         the correct behaviour would be to close it once user clicks export biophysics
    #         (the same problem when first clicking export biophysics, then import biophysics)
    
    
    # !! a lot of code dupl. in two methods below
    
    @classmethod
    def showLoadFileDialog(cls, enumInFileType):
        
        if cls._isBusy:
            cls._top.lift()
            return ''
            
        cls._isBusy = True
        
        cls._top = tk.Toplevel(root)
        cls._top.withdraw()
        
        argsDict = cls._inFileTypeToArgsDict[enumInFileType]
        
        try:
            while True:
                inFilePathName = filedialog.askopenfilename(parent=cls._top, **argsDict)
                
                fileName = os.path.basename(inFilePathName)
                
                cond1 = enumInFileType in [cls.EnumInFileTypes.baseGeometryAny, cls.EnumInFileTypes.nanoGeometryHoc] and \
                   fileName.lower() in cls._reservedHocFileNamesLower       # !! os.path.samefile would be more correct than lower-case comparison
                cond2 = enumInFileType == cls.EnumInFileTypes.biophysJson and \
                   fileName.lower() in cls._reservedJsonFileNamesLower
                if cond1 or cond2:
                    messagebox.showwarning(
                        title='Reserved name',
                        message=f'Cannot import "{fileName}" because it\'s a reserved file name.\n\nPlease use some other name.')
                    # !! use just selected folder as 'initialdir' when calling filedialog.askopenfilename next time
                else:
                    break
                    
            return inFilePathName
            
        finally:
            cls._top.destroy()
            cls._isBusy = False
            
    @classmethod
    def showSaveFileDialog(cls, enumOutFileType, defaultFileName):
        
        if cls._isBusy:
            cls._top.lift()
            return ''
            
        cls._isBusy = True
        
        cls._top = tk.Toplevel(root)
        cls._top.withdraw()
        
        argsDict = cls._outFileTypeToArgsDict[enumOutFileType]
        
        try:
            while True:
                outFilePathName = filedialog.asksaveasfilename(parent=cls._top, initialfile=defaultFileName, **argsDict)
                
                fileName = os.path.basename(outFilePathName)
                
                cond1 = enumOutFileType in [cls.EnumOutFileTypes.baseGeometryHoc, cls.EnumOutFileTypes.nanoGeometryHoc] and \
                   fileName.lower() in cls._reservedHocFileNamesLower       # !! os.path.samefile would be more correct than lower-case comparison
                cond2 = enumOutFileType == cls.EnumOutFileTypes.biophysJson and \
                   fileName.lower() in cls._reservedJsonFileNamesLower
                if cond1 or cond2:
                    messagebox.showwarning(
                        title='Reserved name',
                        message=f'Cannot export to "{fileName}" because it\'s a reserved file name.\n\nPlease use some other name.')
                    # !! use just selected folder as 'initialdir' when calling filedialog.asksaveasfilename next time
                else:
                    break
                    
            # !! for EnumOutFileTypes.nanoGeometryHoc, if the folder is not empty, then ask user whether to clean up
            
            return outFilePathName
            
        finally:
            cls._top.destroy()
            cls._isBusy = False
            