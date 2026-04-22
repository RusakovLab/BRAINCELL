: P2X47_microglia.mod
: Ionotropic purinergic P2X4 / P2X7 receptor for microglial compartments.
:
: KINETIC SCHEME (3-state Markov):
:
:  C (closed) --kon*atpo^2--> O (open) --kdes--> D (desensitized)
:  C          <--koff--------  O       <--krec--  D
:
: For P2X7: kdes=0, PCa_ratio=11, EC50_atp~0.7 mM
: For P2X4 (default): kdes=0.01, PCa_ratio=4, EC50_atp~0.01 mM
:
: SIGN CONVENTION (NEURON standard):
:   Inward current  -> ica < 0
:   At rest (v=-70mV), cao=2.2mM >> cai=50nM:
:     GHK drives Ca2+ IN -> ica < 0 -> influx > 0 -> cai rises  (correct)
:
: ATP input:
:   USEION atp READ atpo -- populated by BrainCell extracellular engine.

NEURON {
    SUFFIX P2X47_microglia

    USEION atp READ atpo
    USEION ca READ cao WRITE cai, ica

    RANGE gmax, E_rev, PCa_ratio
    RANGE kon, koff, kdes, krec
    RANGE cai_rest, tau_pump
    RANGE ica_p2x, i_total, O_frac
}

PARAMETER {
    gmax      = 5e-3    : mS/cm2  (P2X4; ~0.5 nS for 1 um2 process)
    E_rev     = 0.0     : mV     (non-selective cation reversal)
    PCa_ratio = 4.0     : dimensionless  (P2X4; use 11 for P2X7)
    kon       = 10.0    : mM^-2 ms^-1   (2-ATP cooperative binding)
    koff      = 0.5     : ms^-1
    kdes      = 0.01    : ms^-1  (set 0 for P2X7)
    krec      = 0.003   : ms^-1

    cai_rest  = 5e-5    : mM   (resting cai ~50 nM)
    tau_pump  = 200.0   : ms   (PMCA/NCX extrusion time constant)
}

STATE {
    C               : closed
    O               : open
    D               : desensitized
    cai     (mM)    : intracellular Ca2+
}

ASSIGNED {
    v        (mV)
    ica      (mA/cm2)
    cao      (mM)
    atpo     (mM)
    diam     (um)
    ica_p2x  (mA/cm2)
    i_total  (mA/cm2)
    O_frac
}

INITIAL {
    C   = 1
    O   = 0
    D   = 0
    cai = cai_rest
    ica = 0
}

BREAKPOINT {
    LOCAL ghk_val
    SOLVE kstates METHOD sparse
    SOLVE ca_dynamics METHOD euler

    ghk_val = ghk_ca(v, cai, cao)

    : ica < 0 means inward Ca2+ current (correct at rest with cao >> cai)
    ica     = ghk_val * gmax * O
    ica_p2x = ica
    i_total = gmax * O * (v - E_rev)
    O_frac  = O
}

KINETIC kstates {
    LOCAL alpha
    alpha = kon * atpo * atpo

    ~ C <-> O  (alpha, koff)
    ~ O <-> D  (kdes,  krec)

    CONSERVE C + O + D = 1
}

DERIVATIVE ca_dynamics {
    LOCAL influx
    : ica < 0 (inward) -> -ica > 0 -> influx > 0 -> cai rises
    : Thin-shell conversion: mA/cm2 -> mM/ms
    : shell depth = diam/4 (um), factor 0.01 converts um to cm
    : factor 2 = valence of Ca2+
    influx = -ica / (2 * 96.49 * (diam/4) * 0.01)
    cai' = influx - (cai - cai_rest) / tau_pump
}

: GHK Ca2+ current function
: Returns ica (mA/cm2) per unit conductance (S/cm2)
:
: Standard GHK for z=2 (Ca2+):
:   I = P * (z*F)^2/(R*T) * V * (ci - co*exp(-z*F*V/RT)) / (1 - exp(-z*F*V/RT))
:
: At V=-70mV, ci=50nM, co=2.2mM:
:   zv = 0.0748*(-70) = -5.24
:   ef = exp(+5.24) = 189
:   numerator: ci - co*ef = 5e-5 - 415 < 0  (strongly negative)
:   denominator: 1 - ef = -188              (negative)
:   zv * (neg/neg) = negative * positive    = negative
:   -> ghk_ca < 0  (inward)  CORRECT
:
: L'Hopital limit as V->0:
:   I -> P * z*F * (ci - co)
:   with ci << co: I < 0 (inward)  CORRECT
:
: Factor 0.0001 converts units to mA/cm2
FUNCTION ghk_ca(v, ci, co) {
    LOCAL zv, ef
    : zF/RT: z=2, F=96485 C/mol, R=8.314 J/molK, T=310K
    : = 2*96485/(8.314*310) = 74.8 V^-1 = 0.0748 mV^-1
    zv = 0.0748 * v
    if (fabs(zv) < 1e-4) {
        : L'Hopital: limit of zv*(ci-co*ef)/(1-ef) as zv->0 is (ci-co)
        ghk_ca = (PCa_ratio / (PCa_ratio + 1)) * 0.0748 * (ci - co) * 0.0001
    } else {
        ef = exp(-zv)
        : zv*(ci - co*ef)/(1-ef): at v<0, zv<0, ef>1, (1-ef)<0, (ci-co*ef)<0
        : -> negative * negative / negative = negative  (inward) CORRECT
        ghk_ca = (PCa_ratio / (PCa_ratio + 1)) * 0.0748 * zv * (ci - co * ef) / (1 - ef) * 0.0001
    }
}
