: Voltage gap junstion
NEURON {
    POINT_PROCESS Gap_neuron
    NONSPECIFIC_CURRENT i
    RANGE r, i, VoltageGap
}

PARAMETER {
    r = 100000(megohm)
    VoltageGap = -85 (millivolt)
}

ASSIGNED {
    v (millivolt)
    i (nanoamp)
}

BREAKPOINT {
    i = (-VoltageGap +v)/r
}