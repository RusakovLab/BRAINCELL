: AMPARec.mod
:
: Concentration-gated AMPA receptor for BrainCell
: Savtchenko / Rusakov Lab, UCL
:
: Reads extracellular glutamate concentration (gluo, mM) from the BrainCell
: ECS diffusion system (_OutsideInDiffHelper.mod / _InsideOutDiffHelper.mod)
: and produces a postsynaptic inward cation current iampa (mA/cm2).
:
: Kinetic scheme - three-state (C, O, D):
:
:        kon * gluo        kdes
:   C  <============>  O  ----->  D
:        koff                |
:                        krec  |
:                            v
:                            C
:
:   C  = closed (unbound)
:   O  = open   (conducting)
:   D  = desensitised
:
: The three-state scheme captures:
:   - fast activation  (kon, koff)
:   - desensitisation  (kdes) during prolonged / repeated [Glu]o exposure
:   - recovery         (krec) from desensitisation back to closed
:
: This is the minimal scheme sufficient to show the difference between
: Scenario A (astrocyte present, [Glu]o cleared quickly, little desensitisation)
: and Scenario B (no astrocyte, [Glu]o prolonged, desensitisation accumulates).
:
: Ion convention:
:   USEION glu READ gluo   - identical to GluTrans.mod in BrainCell
:   No glu WRITE (the receptor does not transport glutamate)
:   Current iampa written to the membrane via NONSPECIFIC_CURRENT
:   (AMPA receptors are non-selective cation channels; they do not
:    appear in any single-ion USEION declaration)
:
: Units (NEURON standard):
:   gmax   S/cm2
:   iampa  mA/cm2
:   gluo   mM
:   v      mV
:   kon    /mM/ms    (second-order binding rate)
:   koff   /ms       (unbinding rate)
:   kdes   /ms       (desensitisation rate)
:   krec   /ms       (recovery from desensitisation)
:   Erev   mV        (reversal potential, ~0 mV for AMPA)
:
: RANGE variables exposed for HOC/Python access and recording:
:   O      - open fraction          (dimensionless, 0..1)
:   D      - desensitised fraction  (dimensionless, 0..1)
:   iampa  - AMPA current           (mA/cm2)
:   g      - conductance            (S/cm2)
:
: Placement:
:   insert AMPARec into spine head sections on the postsynaptic neuron.
:   Typical density: gmax ~ 5e-4 S/cm2 for a single spine head
:   (equivalent to ~10-20 AMPA receptors at ~25 pS each in a 0.5 um head).
:
: Literature basis for default parameters:
:   kon  = 4.0   /mM/ms  - Jonas et al. 1993 (CA3 mossy fibre AMPA)
:   koff = 4.0   /ms     - Colquhoun et al. 1992
:   kdes = 1.0   /ms     - Raman & Trussell 1992 (fast desensitisation)
:   krec = 0.04  /ms     - Colquhoun et al. 1992 (recovery ~25 ms)
:   Erev = 0.0   mV      - non-selective cation channel
:   gmax = 5e-4  S/cm2   - calibrated for BrainCell spine head geometry

TITLE AMPA receptor (concentration-gated, 3-state)

NEURON {
    SUFFIX AMPARec
    USEION glu READ gluo
    NONSPECIFIC_CURRENT iampa
    RANGE gmax, Erev, kon, koff, kdes, krec
    RANGE O, D, iampa, g
}

UNITS {
    (mV)    = (millivolt)
    (mA)    = (milliamp)
    (S)     = (siemens)
    (mM)    = (milli/liter)
}

PARAMETER {
    gmax = 5e-4  (S/cm2)   : peak conductance density
    Erev = 0.0   (mV)      : AMPA reversal potential (non-selective cation)
    kon  = 4.0   (/mM/ms)  : glutamate binding rate (second-order)
    koff = 4.0   (/ms)     : glutamate unbinding rate
    kdes = 1.0   (/ms)     : desensitisation rate from open state
    krec = 0.04  (/ms)     : recovery rate from desensitised to closed
}

ASSIGNED {
    v      (mV)
    gluo   (mM)    : extracellular [Glu] - READ from BrainCell ECS
    iampa  (mA/cm2)
    g      (S/cm2)
}

STATE {
    C          : closed (unbound)
    O          : open   (conducting)
    D          : desensitised
}

INITIAL {
    : At rest, all receptors are in the closed unbound state.
    : gluo at rest is ~25 nM = 2.5e-5 mM; essentially zero occupancy.
    C = 1.0
    O = 0.0
    D = 0.0
}

BREAKPOINT {
    SOLVE ampa_kin METHOD sparse
    g     = gmax * O
    iampa = g * (v - Erev)
}

KINETIC ampa_kin {
    : Binding step: closed <-> open  (gluo-dependent, second-order forward rate)
    ~ C <-> O  (kon * gluo, koff)

    : Desensitisation: open -> desensitised  (first-order, no reversal from O)
    ~ O <-> D  (kdes, 0)

    : Recovery: desensitised -> closed  (first-order)
    ~ D <-> C  (krec, 0)

    : Conservation: C + O + D = 1
    CONSERVE C + O + D = 1
}
