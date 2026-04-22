TITLE the leak current

UNITS {
	(S) = (siemens)
	(mV) = (millivolt)
	(mA) = (milliamp)
}

NEURON {
    SUFFIX leak
    NONSPECIFIC_CURRENT i
    RANGE gmax
    THREADSAFE
}

PARAMETER {
    gmax  = 0.0001 (S/cm2)
	Eleak = -65 (mV)
}

ASSIGNED { 
    v (mV)
    i (mA/cm2)
}

BREAKPOINT {
    i = gmax*(v-Eleak)
}

