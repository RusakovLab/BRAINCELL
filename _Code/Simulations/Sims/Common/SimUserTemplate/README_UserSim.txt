================================================================================
 BrainCell -- User Simulation Template
 README_UserSim.txt
================================================================================

WHAT IS THIS?
-------------
This folder contains a minimal, fully working simulation template that plugs
directly into BrainCell's SimulationManager.

Out of the box it:
  * Injects a constant current step (IClamp) into the soma
  * Records somatic membrane voltage V(t)
  * Opens a matplotlib plot in a separate window after each run
  * Optionally saves V(t) as a two-column TXT file (time, voltage)


FILES IN THIS FOLDER
--------------------
  SimUserTemplate.py        GUI class -- controls panel layout, parameter
                            fields, and the SimManager interface.
                            Do not remove any public methods.

  SimUserTemplateCore.py    Computation logic -- recording vectors, parameter
                            storage, and result retrieval.
                            THIS IS THE FILE TO EDIT when you want to change
                            what is computed or which parameters exist.

  user_sim_params.json      Optional JSON parameter preset; loaded
                            automatically if you set biophysJsonFileNameOrEmpty
                            in SimUserTemplate.py.

  plots/user_sim_plot.py    Standalone matplotlib script launched as a
                            subprocess after each run; edit this to change
                            the graph appearance or add panels.

  README_UserSim.txt        This file.


GUI PANELS
----------
The simulation panel contains four sections:

  1. Current injection parameters
     Amplitude, delay, and duration of the IClamp injected into the soma.
     Changes take effect on the next Init & Run.

  2. Computation parameters
     Model-specific parameters passed to SimUserTemplateCore before each run.
     The template provides two placeholder fields (Param 1, Param 2).
     RENAME AND REPLACE THESE with the variables your model actually uses,
     for example: g_na_scale, tau_ca, diffusion_coeff, etc.
     See "HOW TO ADD YOUR OWN COMPUTATION PARAMETERS" below.

  3. Simulation time
     tstop and dt, applied to AltRunControl.

  4. Output
     Checkbox to save V(t) to a plain-text file after each run.


HOW TO ADD YOUR OWN COMPUTATION PARAMETERS
-------------------------------------------
This is the most important customisation step. Follow this pattern:

  Step A -- Add the default value in SimUserTemplate.py:

      _def_comp_param1 = 1.0   # (units) -- description of what it controls

  Step B -- Add an xvalue field in show(), inside the "Computation" panel:

      h.xvalue("My param label (units)", (self, '_def_comp_param1'),
               1, self._onCompParamChanged)

  Step C -- Add the argument to _applyCompParams() in SimUserTemplate.py:

      self._core.setParams(
          param1 = self._def_comp_param1,
          my_new_param = self._def_my_new_param,   # <-- add this
      )

  Step D -- Add the matching argument to setParams() in SimUserTemplateCore.py:

      def setParams(self, param1, my_new_param):
          self._param1       = param1
          self._my_new_param = my_new_param   # <-- add this

  Step E -- Use self._my_new_param inside prepareRecordingVectors() or
            any other method in SimUserTemplateCore to affect the computation:

      h.soma_ref[0].sec.gbar_hh = self._my_new_param * 0.12


QUICK-START CHECKLIST
---------------------
To turn this template into your own simulation, complete these steps in order:

  [ ] 1. Copy this entire folder and give it a new name
         e.g.  SimUserTemplate/  ->  SimMyCalcium/

  [ ] 2. Rename the Python files to match your simulation
         SimUserTemplate.py      ->  SimMyCalcium.py
         SimUserTemplateCore.py  ->  SimMyCalciumCore.py

  [ ] 3. Inside SimMyCalcium.py, update the import line at the top:
         from SimUserTemplateCore import SimUserTemplateCore
         ->  from SimMyCalciumCore import SimMyCalciumCore
         And rename the class: class SimUserTemplate -> class SimMyCalcium

  [ ] 4. Edit the two label strings near the top of SimMyCalcium.py:
         _DESCRIPTION = "..."   (one-line xlabel above the button)
         _SIM_LABEL   = "..."   (panel window title)
         IMPORTANT: use only plain ASCII -- no Unicode arrows or dashes.

  [ ] 5. Replace the IClamp parameters with whatever stimulation your
         simulation needs, or remove them entirely if not applicable.

  [ ] 6. Rename the computation parameters in the "Computation" panel
         (see "HOW TO ADD YOUR OWN COMPUTATION PARAMETERS" above).

  [ ] 7. Edit SimMyCalciumCore.setParams() to accept your renamed parameters
         and store them as instance attributes.

  [ ] 8. Edit SimMyCalciumCore.prepareRecordingVectors() to:
         a. Apply your parameters (e.g. set conductances, diffusion coeffs)
         b. Record the variables you want to observe

  [ ] 9. Update SimMyCalciumCore.getResults() to return your new vectors.

  [ ] 10. Update SimMyCalcium.postRun() and plots/user_sim_plot.py to pass
          and display the new variables.

  [ ] 11. Register the simulation in SimManager.hoc:
          a. Add the sys.path line in SimManagerLoads.hoc (or init()):
               sourcePythonCode("\\Sims\\Common\\SimMyCalcium",
                                "from SimMyCalcium import SimMyCalcium",
                                "SimManager init")
          b. In SimManager.init(), add:
               simIdxToWidget[14] = pyObj.SimMyCalcium()
             and increase numSims by 1.

  [ ] 12. Add a button on Page 5 of SimManager.createSimulationsPanel():
          xpanel("")
          xlabel("One-line description of your simulation")
          createSimStateButton("Your sim label", 14)
          insertSpacer()
          xpanel()

  [ ] 13. Restart BrainCell, select "User simulations" in the category bar,
          and click your button.


INTERFACE CONTRACT (methods SimManager calls -- do not rename or remove)
------------------------------------------------------------------------
  preShowCheck()            Return 0 to proceed, 1 to cancel with a warning.
                            Checks geometry, mechanisms, etc.

  show(isFirstShow)         Build the GUI panel. isFirstShow == 1 on the
                            very first call, 0 on subsequent calls.
                            All strings passed to HOC calls (h.xlabel,
                            h.xvalue, bc.VBox title) must be pure ASCII.

  simDismissHandler()       Clean up: remove IClamp, dereference vectors,
                            kill any open subprocess.

  preRun(isInitOnly)        Apply parameters, insert stimuli, prepare
                            recording vectors. Return 0 to proceed, 1 to abort.

  preContinue()             Return 0 to proceed, 1 to abort.

  postRun()                 Retrieve results and launch plot / save TXT.

  isCustomProcAdvance       Bool. True if you replace proc advance.
  isAltRunControl           Bool. True = use AltRunControl buttons.
  biophysJsonFileNameOrEmpty  String. Path to JSON preset or "".


KEY BRAINCELL CONVENTIONS
--------------------------
  Soma section access:
    CORRECT:  h.soma_ref[0].sec(0.5)
    WRONG:    h.soma(0.5)  /  h.soma.sec(0.5)

  Soma existence check:
    hasattr(h, 'soma_ref') and h.soma_ref.count() > 0

  VBox arguments:
    bc.VBox()                      -- 0 args: no title, default position
    bc.VBox(title, x, y)           -- 3 args: title + screen position
    bc.VBox(title, x, y, w, h)     -- 5 args: title + position + size
    NEVER pass a single string title alone.

  ASCII-only strings:
    Any string passed to h.xlabel(), h.xvalue(), h.xbutton(),
    h.xcheckbox(), bc.VBox() title must contain only ASCII characters.
    Use -> not ->, -- not --, * not * etc.

  sys.path registration:
    Every Python simulation folder needs sourcePythonCode(...) called
    before pyObj.SimName() in SimManager.


TIPS
----
  * Keep SimUserTemplate.py focused on GUI and SimManager glue.
    Put all NEURON/biophysics logic in SimUserTemplateCore.py.
    This makes it much easier to test the computation independently.

  * The pickle file (_user_sim_temp.pkl) is a temporary file created in
    the same folder as SimUserTemplate.py. It is overwritten on each run.

  * To save the plot as a PNG automatically, uncomment the savefig line
    near the bottom of plots/user_sim_plot.py.

  * If you need a file-save dialog instead of a fixed output path,
    replace the path logic in SimUserTemplate._saveToTxt() with a call
    to tkinter.filedialog.asksaveasfilename().

  * If your simulation requires a custom proc advance (e.g. for RxD),
    set isCustomProcAdvance = True and implement an onAdvance() method,
    following the pattern in ProcAdvanceHelper.py.

================================================================================
