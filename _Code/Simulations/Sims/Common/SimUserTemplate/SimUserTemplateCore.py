# =============================================================================
#  SimUserTemplateCore.py
#  -----------------------------------------------------------------------------
#  Computation logic for SimUserTemplate, separated from the GUI layer.
#
#  THIS IS THE FILE TO EDIT when you want to change what is computed.
#  The GUI class (SimUserTemplate.py) calls the methods here but does not
#  need to know the details of how the computation works.
#
#  WHAT THIS FILE DOES:
#    * Allocates NEURON Vector objects to record time and somatic voltage
#    * Provides getResults() to retrieve the recorded data after a run
#    * Provides cleanup() to dereference all NEURON objects on dismiss
#
#  TO REPLACE WITH YOUR OWN COMPUTATION:
#    1. Add your own recording variables in prepareRecordingVectors()
#       e.g.  self._ca_vec = h.Vector().record(h.soma(0.5)._ref_cai)
#    2. Return your data from getResults() as a tuple of Python lists
#    3. Update SimUserTemplate.postRun() and user_sim_plot.py to use
#       the new variables
# =============================================================================

from neuron import h


class SimUserTemplateCore:

    # -- Data members added in prepareRecordingVectors -------------------------
    #   _t_vec    h.Vector  -- time points (ms)
    #   _v_vec    h.Vector  -- somatic membrane voltage (mV)

    # -- Computation parameters (set via setParams before each run) -----------
    # Replace these with the actual parameters your model needs.
    _param1 = 1.0
    _param2 = 0.5

    def __init__(self):
        self._t_vec = None
        self._v_vec = None

    def setParams(self, param1, param2):
        """
        Receive computation parameters from the GUI before each run.
        Called by SimUserTemplate._applyCompParams() inside preRun().

        TO ADAPT:
          * Add or remove keyword arguments to match your _def_comp_param* fields
          * Store them as instance attributes so prepareRecordingVectors() and
            any other methods can use them
          * Rename param1/param2 to something meaningful for your model,
            e.g. setParams(self, g_na_scale, tau_ca)
        """
        self._param1 = param1
        self._param2 = param2

    def prepareRecordingVectors(self):
        """
        Allocate NEURON recording vectors and attach them to the variables
        you want to observe.

        Called by SimUserTemplate.preRun() before each Init & Run.
        Re-creating vectors here ensures a clean recording even if the
        user presses Init & Run multiple times.

        -- To record additional variables ------------------------------------
        Add lines of the form:
            self._ik_vec = h.Vector().record(h.soma(0.5)._ref_ik)
        and return them from getResults() below.
        """
        # Computation parameters are available here as self._param1, self._param2.
        # Use them to scale mechanisms, set conductances, etc. before recording.
        # Example: h.soma_ref[0].sec.gbar_hh = self._param1 * 0.12

        # Time vector -- records h.t at every dt
        self._t_vec = h.Vector()
        self._t_vec.record(h._ref_t)

        # Voltage vector -- records V at the centre of soma at every dt
        # -- Change h.soma(0.5)._ref_v to any segment variable you need --------
        self._v_vec = h.Vector()
        self._v_vec.record(h.soma_ref[0].sec(0.5)._ref_v)

    def getResults(self):
        """
        Return the recorded data as plain Python lists.
        Called by SimUserTemplate.postRun() after the run completes.

        Returns
        -------
        t_vec : list of float   time points in ms
        v_vec : list of float   somatic voltage in mV

        -- If you added more vectors in prepareRecordingVectors --------------
        Return them here as additional list items and unpack them in
        SimUserTemplate.postRun().
        """
        if self._t_vec is None or self._v_vec is None:
            return [], []

        return list(self._t_vec), list(self._v_vec)

    def cleanup(self):
        """
        Dereference all NEURON Vector objects.
        Called by SimUserTemplate.simDismissHandler() when the user
        deselects the simulation.
        """
        self._t_vec = None
        self._v_vec = None
