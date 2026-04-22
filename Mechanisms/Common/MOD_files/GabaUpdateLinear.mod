: GABA_tonic_gabao.mod
: GABA tonic receptor - conductance gated by extracellular GABA concentration
:
: The steady-state conductance follows a Hill equation in gabao (mM):
:
:   g = g_max * gabao^n_Hill / (EC50^n_Hill + gabao^n_Hill)
:
: This captures the nonlinear occupancy of extrasynaptic GABA-A receptors
: (delta-subunit containing) as a function of ambient [GABA]o.
:
: gabao is supplied by GabaUpdate.mod (suffix gabaacum) which must be
: inserted in the same compartment (or communicated via the gaba ion).
:
: The resulting current is a Cl- ohmic current driven by (v - ECl).
:
: Units:
:   g_max   : S/cm2
:   i_tonic : mA/cm2
:   ECl     : mV
:   EC50    : mM
:   gabao   : mM   (READ from gaba ion, written by GabaUpdate.mod)
:
: BrainCell category: Neuron
: Savtchenko / Rusakov Lab, UCL

NEURON {
    SUFFIX GABA_tonic_gabao
    USEION gaba READ gabao VALENCE 0
    NONSPECIFIC_CURRENT i_tonic
    RANGE g_max, EC50, n_Hill, ECl, g_tonic, i_tonic
}

UNITS {
    (mA) = (milliamp)
    (mV) = (millivolt)
    (S)  = (siemens)
    (mM) = (milli/liter)
}

PARAMETER {
    g_max   = 1e-4  (S/cm2)  : maximum conductance at saturating [GABA]o
    EC50    = 1e-4  (mM)     : half-maximal [GABA]o (~0.1 uM, typical delta-GABA-A)
    n_Hill  = 1.0            : Hill coefficient (dimensionless)
    ECl     = -70   (mV)     : chloride reversal potential
}

ASSIGNED {
    v       (mV)
    gabao   (mM)
    g_tonic (S/cm2)
    i_tonic (mA/cm2)
}

BREAKPOINT {
    g_tonic = g_max * hill(gabao)
    i_tonic = g_tonic * (v - ECl)
}

FUNCTION hill(c (mM)) {
    LOCAL cn, EC50n
    if (c < 0) { c = 0 }
    cn    = c ^ n_Hill
    EC50n = EC50 ^ n_Hill
    hill  = cn / (EC50n + cn)
}