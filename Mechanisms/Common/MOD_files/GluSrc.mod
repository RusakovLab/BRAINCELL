: GluSrc.mod
:
: Glutamate source mechanism for BrainCell.
: Savtchenko / Rusakov Lab, UCL.
:
: Generates iglu (mA/cm2) as a train of alpha-function pulses.
: _InsideOutDiffHelper.mod reads iglu and converts it to gluo via Faraday's law.
:
: Alpha function for each pulse:
:   iglu(t) = amplitude * ((t - t_pulse) / tau) * exp(1 - (t - t_pulse) / tau)
:   for t >= t_pulse, zero otherwise.
:   Peak occurs at t = t_pulse + tau, peak value = amplitude.
:
: Pulse train:
:   Pulse k fires at t0 + k * (1000/F)  ms,  k = 0, 1, ..., N-1
:   (F in Hz, so inter-pulse interval = 1000/F ms)
:
: Parameters:
:   t0        (ms)    - onset time of first pulse
:   N                 - number of pulses (integer, stored as real)
:   F         (Hz)    - pulse frequency
:   amplitude (mA/cm2)- peak iglu of each pulse (positive = release into ECS)
:   tau       (ms)    - alpha-function timescale (time to peak)
:
: Ion convention:
:   USEION glu WRITE iglu VALENCE -1
:   iglu > 0  means outward current  = glutamate leaving the cell into ECS
:   _InsideOutDiffHelper uses:
:       specieso << (iglu * (radius+Layer) * PI) / FARADAY / spcValence
:   With spcValence = -1, positive iglu produces positive flux into specieso.
:   This is the correct sign for a glutamate source (presynaptic release).

TITLE Glutamate source (alpha-function pulse train)

NEURON {
    SUFFIX GluSrc
    USEION glu WRITE iglu VALENCE -1
    RANGE t0, N, F, amplitude, tau
    RANGE iglu
}

UNITS {
    (mA) = (milliamp)
    (mV) = (millivolt)
}

PARAMETER {
    t0        = 10             : onset time of first pulse (ms)
    N         = 1              : number of pulses
    F         = 1             : pulse frequency in Hz (1000/F gives interval in ms)
    amplitude = 1e-4  (mA/cm2) : peak iglu per pulse
    tau       = 1              : alpha-function timescale in ms (time to peak)
}

ASSIGNED {
    iglu (mA/cm2)
}

BREAKPOINT {
    iglu = -computeIglu(t)
}

INITIAL {
    iglu = 0
}

FUNCTION computeIglu(tnow) (mA/cm2) {
    LOCAL k, t_pulse, dt, isi, result
    result = 0
    isi = 1000 / F         : inter-pulse interval in ms (F is in Hz)
    FROM k = 0 TO (N-1) {
        t_pulse = t0 + k * isi
        dt = tnow - t_pulse
        if (dt > 0) {
            result = result + amplitude * (dt / tau) * exp(1 - dt / tau)
        }
    }
    computeIglu = result
}
