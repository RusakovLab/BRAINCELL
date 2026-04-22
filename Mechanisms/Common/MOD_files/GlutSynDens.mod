TITLE Glutamatergic synapses - distributed AMPA-like density mechanism

COMMENT
-------------------------------------------------------------------------------
GlutSynDens
-------------------------------------------------------------------------------

Density (distributed) mechanism that emulates AMPA-like glutamatergic synaptic
activity across an entire cell, without requiring external NetCon events. It is
intended for BrainCell's "second added cell" which carries a single section
type (extra cell) and admits spatial / stochastic parameter distribution via
BrainCell's inhomogeneous-and-stochastic infrastructure.

Kinetics
--------
Classical Exp2Syn double-exponential conductance:

        g(t) = gmax * factor * (B - A)
        dA/dt = -A / tau1
        dB/dt = -B / tau2

where "factor" normalises the peak of (B - A) to unity so that a single event
produces a conductance pulse whose peak equals exactly gmax. On each synaptic
event both A and B are incremented by 1 (event-driven jumps), so overlapping
events sum linearly - this matches the behaviour of NetCon-driven Exp2Syn.

Postsynaptic current (non-specific cation, AMPA-like):

        i = g * (v - e)              (e defaults to 0 mV)

Trigger
-------
Since density mechanisms cannot receive NetCon events, activity is produced by
an internal periodic trigger active in the window [t_start, t_stop] at mean
rate "freq" (Hz). Optional jitter (onset_jitter, ms) desynchronises adjacent
segments so that the ensemble does not fire in perfect lockstep.

All kinetic and trigger parameters are RANGE, so BrainCell's distribution
system can vary them across segments (stochastic or space-dependent profiles
of gmax, freq, tau1, tau2, etc.).

Notes for BrainCell integration
-------------------------------
- Pure 7-bit ASCII, no Unicode.
- UNITS block only declares non-predefined units.
- No USEION - purely postsynaptic non-specific cation current.
- No coupling to extracellular neurotransmitter species.
- No Ca2+ deposition.
- Insertable into any section: "insert GlutSynDens".
-------------------------------------------------------------------------------
ENDCOMMENT


NEURON {
    SUFFIX GlutSynDens
    NONSPECIFIC_CURRENT i
    RANGE gmax, tau1, tau2, e
    RANGE freq, t_start, t_stop, onset_jitter
    RANGE g, i
    RANGE factor
}

UNITS {
    (nA) = (nanoamp)
    (mV) = (millivolt)
    (uS) = (microsiemens)
    : (S/cm2), (ms) are predefined - do not redefine
}

PARAMETER {
    gmax        = 0.0001  : peak conductance per event (S/cm2)
    tau1        = 0.5     : rise time constant (ms)
    tau2        = 3.0     : decay time constant (ms)
    e           = 0       : reversal potential (mV), AMPA-like
    freq        = 10      : mean trigger rate (Hz)
    t_start     = 0       : trigger window start (ms)
    t_stop      = 1e9     : trigger window end (ms)
    onset_jitter = 0      : uniform jitter on next-event time (ms), 0 = deterministic
}

ASSIGNED {
    v           (mV)
    i           (mA/cm2)
    g           (S/cm2)
    factor                  : peak-normalisation constant (dimensionless)
    t_next      (ms)        : scheduled time of next synaptic event
    initialized             : 0 until INITIAL has run once, then 1
}

STATE {
    A           : rise-partner state (dimensionless)
    B           : decay-partner state (dimensionless)
}


INITIAL {
    LOCAL tp

    : --- Compute the Exp2Syn peak-normalisation factor ---
    : If tau1 ~ tau2, nudge tau1 slightly to keep the formula well-defined.
    if (tau1/tau2 > 0.9999) {
        tau1 = 0.9999 * tau2
    }
    if (tau1/tau2 < 1e-9) {
        tau1 = tau2 * 1e-9
    }
    tp = (tau1 * tau2) / (tau2 - tau1) * log(tau2 / tau1)
    factor = -exp(-tp / tau1) + exp(-tp / tau2)
    factor = 1 / factor

    : --- Initial kinetic state ---
    A = 0
    B = 0
    g = 0

    : --- Schedule the first event ---
    : We jitter only the first onset so the population is desynchronised;
    : subsequent events follow the deterministic period 1000/freq ms.
    : scop_random() returns a uniform deviate in [0,1) from NEURON's SCoP stream.
    if (freq > 0) {
        t_next = t_start + onset_jitter * scop_random()
    } else {
        t_next = 1e18   : effectively never
    }

    initialized = 1
}


BREAKPOINT {
    : Fire any events whose scheduled time has been reached.
    : This is a PROCEDURE (not solved as ODE) so it can perform discrete jumps.
    fireDueEvents()

    SOLVE states METHOD cnexp

    g = gmax * factor * (B - A)
    i = g * (v - e)
}


DERIVATIVE states {
    A' = -A / tau1
    B' = -B / tau2
}


: ---------------------------------------------------------------------------
: fireDueEvents
:
: Checks whether the simulation time t has reached the next scheduled event.
: If so, applies the event-driven jump (A += 1, B += 1) and advances t_next
: by the inter-event interval 1000/freq ms. Loops so that if dt is larger
: than the interval, multiple events collapse correctly. Outside the window
: [t_start, t_stop] no events fire.
: ---------------------------------------------------------------------------
PROCEDURE fireDueEvents() {
    LOCAL isi

    : If freq <= 0 the trigger is disabled. In that case t_next was set to
    : 1e18 in INITIAL, so the while loop below would never fire anyway; but
    : we short-circuit explicitly to avoid dividing by zero when computing isi.
    if (freq > 0) {
        isi = 1000 / freq   : inter-event interval (ms)

        while (t >= t_next && t <= t_stop) {
            if (t_next >= t_start) {
                A = A + 1
                B = B + 1
            }
            t_next = t_next + isi
        }
    }
}


: ---------------------------------------------------------------------------
: Notes on randomness
: ---------------------------------------------------------------------------
: scop_random() is a built-in NMODL function provided by NEURON's SCoP runtime
: returning a uniform deviate in [0, 1). It is called directly in INITIAL
: (no FUNCTION declaration required) to produce the first-event jitter. For
: reproducibility across simulations, seed via "use_mcell_ran4(1)" and
: "mcell_ran4_init(seed)" in HOC, or set a fixed seed from BrainCell's
: stochastic infrastructure.
: ---------------------------------------------------------------------------
