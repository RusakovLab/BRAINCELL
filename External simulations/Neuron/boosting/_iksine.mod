
: A simple membrane mechanism just for demo
: Can be replaced with any other which "USEION k READ ko WRITE ik"

NEURON {
    SUFFIX iksine
    USEION k READ ko WRITE ik
    RANGE ik0, A, x, X, T
}

UNITS {
    PI = (pi) (1)
}

PARAMETER {
    ik0 (mA/cm2)
    A (mA/cm2)
    x (um)
    X (um)
    T (ms)
}

ASSIGNED {
    ik (mA/cm2)
    ko (mM)
}

INITIAL {
    ik = foo(x, 0)
}

BREAKPOINT {
    ik = foo(x, t)
}

FUNCTION foo(x, t) {
    : We can use "ko" in the right-hand side of this assignment to account for the influence of the extracellular space on the cell
    foo = ik0 + A * sin(2 * PI * (x / X - t / T))
}
