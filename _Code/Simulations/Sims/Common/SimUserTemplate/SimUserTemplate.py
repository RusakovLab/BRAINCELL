# =============================================================================
#  SimUserTemplate.py
#  -----------------------------------------------------------------------------
#  A ready-to-run template for adding your own simulation to BrainCell.
#
#  WHAT THIS SIMULATION DOES (template behaviour):
#    * Injects a constant current step (IClamp) into the soma
#    * Records somatic membrane voltage V(t)
#    * Displays the result in a matplotlib figure via subprocess
#    * Optionally saves V(t) to a plain-text file (two columns: time, voltage)
#
#  HOW TO TURN THIS INTO YOUR OWN SIMULATION:
#    Step 1 -- Rename the file and the class
#             SimUserTemplate.py  ->  SimYourName.py
#             class SimUserTemplate  ->  class SimYourName
#
#    Step 2 -- Register it in SimManager.init()
#             simIdxToWidget[14] = pyObj.SimYourName()
#             and set  numSims = 15  (or higher)
#
#    Step 3 -- Add a button in SimManager.createSimulationsPanel(), Page 5:
#             xlabel("One-line description of what your simulation does")
#             createSimStateButton("Your sim label", 14)
#             insertSpacer()
#
#    Step 4 -- Edit _DESCRIPTION, _SIM_LABEL and the parameter defaults below
#
#    Step 5 -- Replace the computation in SimUserTemplateCore (separate file)
#             with your own biophysics
#
#  INTERFACE CONTRACT (do not remove these methods -- SimManager calls them):
#    preShowCheck()          validate before the panel is shown
#    show(isFirstShow)       build and display the GUI panel
#    simDismissHandler()     clean up when the user deselects this simulation
#    preRun(isInitOnly)      called by AltRunControl before Init & Run
#    preContinue()           called by AltRunControl before Continue
#    postRun()               called by AltRunControl after the run completes
#
#  ATTRIBUTES READ BY SimManager (do not remove):
#    isCustomProcAdvance     True  -> SimManager calls deployCustomProcAdvance()
#    isAltRunControl         True  -> SimManager plugs AltRunControl
#    biophysJsonFileNameOrEmpty   "" -> no JSON preset loaded automatically
# =============================================================================

from neuron import h

import os
import subprocess
import sys
import pickle

import GuiPrimitiveWrappers as bc
import MsgWarnHelperWrappers as mwhw
from OtherInterModularUtils import codeContractViolation

from SimUserTemplateCore import SimUserTemplateCore


# -- Labels shown in the GUI ----------------------------------------------------
# Edit these two strings when you rename/repurpose the simulation.
_DESCRIPTION = "Current step -> somatic voltage"
_SIM_LABEL   = "User template simulation"


class SimUserTemplate:

    # -- SimManager interface attributes ---------------------------------------
    isCustomProcAdvance      = False   # Set True if you implement a custom proc advance
    isAltRunControl          = True    # We use AltRunControl (Init & Run / Continue buttons)
    biophysJsonFileNameOrEmpty = ""    # Set a path string to auto-load a JSON biophysics preset

    # -- Default parameter values ----------------------------------------------
    # These are the starting values shown in the GUI sliders/fields.
    # Change them to suit your simulation.
    _def_iclamp_amp   =  0.3    # nA   -- injected current amplitude
    _def_iclamp_delay = 50.0    # ms   -- delay before current onset
    _def_iclamp_dur   = 200.0   # ms   -- current duration
    _def_tstop        = 350.0   # ms   -- total simulation time (shown in AltRunControl)
    _def_dt           = 0.025   # ms   -- integration time step

    # -- Computation parameters ------------------------------------------------
    # These parameters are passed to SimUserTemplateCore before each run.
    # Add, remove, or rename them to match your own biophysics model.
    # Each one gets its own xvalue field in the "Computation" panel in show().
    _def_comp_param1  = 1.0     # (units) -- example: membrane resistance scale factor
    _def_comp_param2  = 0.5     # (units) -- example: channel density scale factor

    # -- Internal state --------------------------------------------------------
    _isSaveToTxt = False        # controlled by the "Save to TXT" checkbox in the GUI
    _savePath    = ""           # filled in by _onSaveButtonHandler

    def __init__(self):
        self._core = SimUserTemplateCore()
        self._iclampOrNone = None

    # -- SimManager interface --------------------------------------------------

    def preShowCheck(self):
        """
        Called by SimManager before showing the panel.
        Return 1 to cancel (e.g. missing geometry), 0 to proceed.
        Add your own validation logic here.
        """
        # Check that a soma section exists
        if not hasattr(h, 'soma_ref') or h.soma_ref.count() == 0:
            mwhw.showWarningBox(
                "No soma section found.",
                "Please load a cell geometry before starting this simulation.")
            return 1    # cancel
        return 0        # proceed

    def show(self, isFirstShow):
        """
        Called by SimManager while intercepting its own panel.
        Do NOT use bc.VBox here -- that creates a separate popup window.
        Use h.xpanel("") / h.xpanel() blocks directly instead.
        """
        # -- Description -----------------------------------------------
        h.xpanel("")
        h.xlabel(_DESCRIPTION)
        h.xpanel()

        # -- Stimulation parameters ------------------------------------
        h.xpanel("")
        h.xlabel("-- Current injection parameters ------------------")
        h.xvalue("Amplitude (nA)",    (self, '_def_iclamp_amp'),   1, self._onParamChanged)
        h.xvalue("Delay (ms)",         (self, '_def_iclamp_delay'), 1, self._onParamChanged)
        h.xvalue("Duration (ms)",      (self, '_def_iclamp_dur'),   1, self._onParamChanged)
        h.xpanel()

        # -- Computation parameters ------------------------------------
        # Rename labels and _def_comp_param* vars to match your model.
        h.xpanel("")
        h.xlabel("-- Computation parameters ----------------------------")
        h.xvalue("Param 1 (units)", (self, '_def_comp_param1'), 1, self._onCompParamChanged)
        h.xvalue("Param 2 (units)", (self, '_def_comp_param2'), 1, self._onCompParamChanged)
        h.xlabel("(Rename these to match your model variables.)")
        h.xpanel()

        # -- Run parameters --------------------------------------------
        h.xpanel("")
        h.xlabel("-- Simulation time ---------------------------------")
        h.xvalue("Total time tstop (ms)", (self, '_def_tstop'), 1, self._onTstopChanged)
        h.xvalue("Time step dt (ms)",     (self, '_def_dt'),    1, self._onDtChanged)
        h.xpanel()

        # -- Output options --------------------------------------------
        h.xpanel("")
        h.xlabel("-- Output ------------------------------------------")
        h.xcheckbox("Save V(t) to TXT file after run", (self, '_isSaveToTxt'))
        h.xlabel("Note: plot opens automatically after each run.")
        h.xpanel()

        # Apply tstop and dt to AltRunControl on first show
        if isFirstShow:
            self._applyRunParams()

    def simDismissHandler(self):
        """
        Called by SimManager when the user deselects this simulation.
        Remove IClamp, clean up vectors, close any open subprocess windows.
        """
        self._removeIClamp()
        self._core.cleanup()

    def preRun(self, isInitOnly):
        """
        Called before Init & Run (and before Init-only).
        Insert the IClamp and record vectors here.
        Return 1 to abort the run, 0 to proceed.
        """
        self._applyRunParams()
        self._applyCompParams()
        self._insertIClamp()
        self._core.prepareRecordingVectors()
        return 0    # proceed

    def preContinue(self):
        """
        Called before Continue.
        Return 1 to abort the continue, 0 to proceed.
        """
        # Nothing special needed for a simple IClamp simulation
        return 0

    def postRun(self):
        """
        Called after the run or continue completes.
        Launch the plot subprocess and optionally save to TXT.
        """
        t_vec, v_vec = self._core.getResults()

        # Launch the plot in a separate process so NEURON's GUI stays responsive
        self._launchPlotSubprocess(t_vec, v_vec)

        # Optionally save to TXT
        if self._isSaveToTxt:
            self._saveToTxt(t_vec, v_vec)

    # -- Parameter change handlers ---------------------------------------------

    def _onParamChanged(self):
        """Update the live IClamp if it already exists (i.e. mid-run edit)."""
        if self._iclampOrNone is not None:
            self._applyIClampParams(self._iclampOrNone)

    def _onTstopChanged(self):
        h.tstop = self._def_tstop

    def _onDtChanged(self):
        h.dt = self._def_dt

    def _onCompParamChanged(self):
        """
        Called when the user edits a computation parameter field.
        Values are read in preRun() via _applyCompParams() -- nothing to do here
        unless you want live parameter updates during a running simulation.
        """
        pass

    def _applyCompParams(self):
        """
        Push current GUI parameter values into the core before each run.
        Add one line per computation parameter you define above.
        """
        self._core.setParams(
            param1 = self._def_comp_param1,
            param2 = self._def_comp_param2,
        )

    def _applyRunParams(self):
        h.tstop = self._def_tstop
        h.dt    = self._def_dt

    # -- IClamp helpers --------------------------------------------------------

    def _insertIClamp(self):
        """Insert a new IClamp at the centre of soma and apply current parameters."""
        self._removeIClamp()
        clamp = h.IClamp(h.soma_ref[0].sec(0.5))
        self._applyIClampParams(clamp)
        self._iclampOrNone = clamp

    def _applyIClampParams(self, clamp):
        clamp.amp   = self._def_iclamp_amp
        clamp.delay = self._def_iclamp_delay
        clamp.dur   = self._def_iclamp_dur

    def _removeIClamp(self):
        self._iclampOrNone = None   # dereferencing removes it from NEURON

    # -- Plot subprocess -------------------------------------------------------

    def _launchPlotSubprocess(self, t_vec, v_vec):
        """
        Serialise the result vectors to a temporary pickle file and launch
        plots/user_sim_plot.py in a separate Python process.
        The subprocess reads the pickle and shows the matplotlib figure.
        This matches the existing BrainCell pattern (PyplotSubProcHelper).
        """
        thisDir     = os.path.dirname(os.path.abspath(__file__))
        pickleFile  = os.path.join(thisDir, '_user_sim_temp.pkl')
        plotScript  = os.path.join(thisDir, 'plots', 'user_sim_plot.py')

        data = {
            't'         : list(t_vec),
            'v'         : list(v_vec),
            'iclamp_amp'  : self._def_iclamp_amp,
            'iclamp_delay': self._def_iclamp_delay,
            'iclamp_dur'  : self._def_iclamp_dur,
            'tstop'       : self._def_tstop,
        }

        with open(pickleFile, 'wb') as f:
            pickle.dump(data, f)

        subprocess.Popen(
            [sys.exec_prefix + '/python.exe', plotScript, pickleFile],
            cwd=thisDir)

    # -- TXT save -------------------------------------------------------------

    def _saveToTxt(self, t_vec, v_vec):
        """
        Save V(t) as a two-column plain-text file.
        Column 1: time (ms)   Column 2: voltage (mV)
        The file is written next to this script with a fixed name.
        Change the path logic here if you need a file dialog or a custom folder.
        """
        thisDir  = os.path.dirname(os.path.abspath(__file__))
        outPath  = os.path.join(thisDir, 'user_sim_output.txt')

        with open(outPath, 'w') as f:
            f.write("# BrainCell -- User Simulation output\n")
            f.write(f"# IClamp: amp={self._def_iclamp_amp} nA  "
                    f"delay={self._def_iclamp_delay} ms  "
                    f"dur={self._def_iclamp_dur} ms\n")
            f.write("# time(ms)\tvoltage(mV)\n")
            for t, v in zip(t_vec, v_vec):
                f.write(f"{t:.6f}\t{v:.6f}\n")

        print(f"[SimUserTemplate] Saved V(t) to: {outPath}")
