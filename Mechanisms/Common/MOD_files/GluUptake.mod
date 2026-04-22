: GluUptake.mod
:
: Linear glutamate uptake mechanism for BrainCell.
: Savtchenko / Rusakov Lab, UCL.
:
: Simple passive uptake driven by the difference between
: the local extracellular glutamate concentration (gluo) and
: a baseline resting concentration (gluobasic).
:
: Formula:
:   iglu = gluconductance * (gluo - gluobasic)
:
: When gluo > gluobasic:  iglu > 0  (outward by NEURON convention)
:   -> _InsideOutDiffHelper flux term becomes negative (removal from ECS)
:   -> glutamate is taken up. Correct.
:
: When gluo < gluobasic:  iglu < 0
:   -> small reverse flux, nudges gluo back up to baseline. Correct.
:
: When gluo = gluobasic:  iglu = 0. No flux. Correct.
:
: Insert into astrocyte sections alongside InsideOutDiffHelper.
: gluconductance sets the uptake rate:
:   larger value = faster clearance of extracellular glutamate.
:
: Units:
:   gluconductance  (cm/s)   : permeability-like rate constant
:   gluobasic       (mM)     : resting extracellular [Glu]
:   gluo            (mM)     : local extracellular [Glu] (read from glu ion)
:   iglu            (mA/cm2) : membrane current density written to glu ion

TITLE Linear glutamate uptake

NEURON {
    SUFFIX GluUptake
    USEION glu READ gluo WRITE iglu VALENCE -1
    RANGE gluconductance, gluobasic
    RANGE iglu
}

UNITS {
    (mA)  = (milliamp)
    (mM)  = (milli/liter)
}

PARAMETER {
    gluconductance = 1e-4          : uptake rate constant (cm/s)
    gluobasic      = 1e-5  (mM)   : resting extracellular [Glu] baseline
}

ASSIGNED {
    gluo (mM)
    iglu (mA/cm2)
}

BREAKPOINT {
    iglu = gluconductance * (gluo - gluobasic)
}

INITIAL {
    iglu = 0
}
