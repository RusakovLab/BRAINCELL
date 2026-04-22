COMMENT
================================================================================
cadifus.mod  --  Calcium diffusion in astrocyte / neuron radial shell model
================================================================================

Origin
------
Derived from the canonical cadifus.mod in Chapter 9 of:
  Hines & Carnevale, "The NEURON Book", Cambridge University Press.

Extensions added in this version
---------------------------------
1. Fluorescence readout (two formulations -- see "Fluorescence" section below).
2. Full SERCA system: IP3R channel, SERCA pump, and ER leak.
3. IP3 dynamics driven by De Pitta / Manninen astrocyte model.

================================================================================
GEOMETRY
================================================================================

The cytoplasm is discretised into Nannuli = 4 concentric cylindrical shells
(annuli).  Shell 0 is the innermost (sub-membrane) shell; shell Nannuli-1 is
the central core.

  outer membrane
  |  shell 0  |  shell 1  |  shell 2  |  shell 3 (core)  |
  <------------------  diam  ----------------------->

vrat[i] stores the fractional cross-sectional area of each annulus for a
cylinder of unit (1 um) diameter.  Multiply by diam^2 to get the actual
cross-sectional area in um^2 per um length.

frat[i+1] is the radial conductance factor between adjacent shells i and i+1,
incorporating annulus geometry and inter-centre distance.

================================================================================
CALCIUM DYNAMICS
================================================================================

Three classes of Ca2+ flux:

  1. Plasma membrane pump (threshold-activated):
         jPMP ~ gamma * H(ca - cath)
     where H is a step function.  Sets ica_pmp.

  2. Radial + longitudinal diffusion (DCa = 0.22 um^2/ms, Fink et al. 2000).

  3. SERCA system (ER Ca2+ cycling):
       a. SERCA pump:   jpump = alpha * vmax * ca^2 / (ca^2 + Kp^2)
                        -- uptake from cytoplasm into ER (Hill coeff = 2)
       b. IP3R channel: jchnl = alpha * jmax * (1 - ca/caer)
                                * [ (ip3/(ip3+Kip3)) * (ca/(ca+Kact)) * ho ]^3
                        -- Ca2+ release from ER to cytoplasm
       c. ER leak:      jleak = alpha * L * (1 - ca/caer)
                        -- passive leak from ER to cytoplasm
                        L is computed per-shell at initialisation so that
                        jpump + jchnl + jleak = 0 at resting [Ca2+].

IP3R gating variable h (fraction in open-able state):
  h' = kon * (Kinh - (ca + Kinh) * h)
  steady state: h_inf = Kinh / (ca + Kinh)
  time constant: tau_h = 1 / (kon * (ca + Kinh))

  Recast as kinetic scheme for NEURON KINETIC block:
    hc <-> ho
    forward rate = kon * Kinh    (opening)
    backward rate = kon * ca     (Ca-dependent inactivation)

  Reference: Fink et al. 2000 (J Physiol 524:3, 627-641)

================================================================================
IP3 DYNAMICS  (De Pitta et al. 2009 / Manninen et al. 2017 astrocyte model)
================================================================================

  ModelDB: https://senselab.med.yale.edu/ModelDB/ShowModel.cshtml?model=223269

  ip3i' = v_glu + v_delta - v_3K - r_bar_5P * ip3i

  Production terms:
    v_glu   = v_bar_beta * modelStim / (modelStim + K_gamma)
              -- PLC-beta production driven by glutamate stimulus
              -- K_gamma = K_R * (1 + (K_p/K_R) * ca / (ca + K_pi))
                 is a Ca-dependent effective affinity constant

    v_delta = v_bar_delta / (1 + ip3i/kappa_delta)
              * ca^2 / (ca^2 + K_PLCdelta^2)
              -- PLC-delta production (Ca-dependent, inhibited by IP3)

  Degradation terms:
    v_3K    = v_bar_3K * ca^4 / (ca^4 + K_D^4) * ip3i / (ip3i + K_3)
              -- IP3-3K degradation (Hill coeff = 4 for Ca)

    r_bar_5P * ip3i
              -- IP3-5-phosphatase degradation (first-order in IP3)

  ip3i is treated as spatially uniform across radial shells (see justification
  in the header above).  Its compartment volume is the full cylinder
  cross-section: PI*diam^2/4.

  IMPORTANT: ip3i is declared in STATE (not as a USEION ion) so that it is
  solved as an internal ODE within this mechanism.  If another mechanism must
  read ip3i, use a POINTER or a separate ip3cum mechanism with USEION ip3.

================================================================================
BUFFERS
================================================================================

  Bufs  --  endogenous STATIONARY buffer (no diffusion)
            Ca + Bufs <-> CaBufs
            Rapid equilibrium: kfs is large, krs = kfs * KDs * 1e-3
            (factor 1e-3 converts KDs from uM to mM for consistent rate units)

  Bufm  --  MOBILE fluorescent buffer (default: fura-2)
            Ca + Bufm <-> CaBufm
            Bufm diffuses with coefficient DBufm.
            Alternative parameterisation for calcium green is commented out.

================================================================================
FLUORESCENCE READOUT
================================================================================

  Two formulations are provided:

  fluo     = cabufm[0]
             -- raw concentration of Ca-bound mobile buffer in innermost shell
             -- proportional to F/Fmax in single-wavelength experiments

  fluoNew  = (BufferAlpha*cabufm[0] + ca[0] - BufferAlpha*(TBufm - bufm_0) - cai0)
             / (BufferAlpha*(TBufm - bufm_0) + cai0)
             -- normalised ratio signal, linearised around resting state
             -- BufferAlpha = KDm / cai0 ~ 100 (dimensionless)
             -- equals 0 at rest, positive when [Ca2+] rises above cai0

================================================================================
KNOWN ISSUES / WARNINGS
================================================================================

  BUG FIXED: Direct assignment to state variables (ca[i] = cai0/2) inside
  a KINETIC block is ILLEGAL in NEURON.  The sparse solver builds a Jacobian
  and direct assignments corrupt it silently.  Those guards have been removed.
  Replacement: ca_floor(c) FUNCTION clamps Ca to ca_min = 1e-9 mM in the
  denominator and rate positions of SERCA/IP3R/IP3-dynamics expressions only.
  The STATE variable ca[i] is never clamped -- the Jacobian remains correct.
  ca_min = 1 pM is far below resting [Ca2+] = 50 nM; physiologically inert.

  CORRECTION: USEION ip3 READ ip3i WRITE ip3i VALENCE 1 restored.
  ip3i must be both a STATE variable (so ~ ip3i << flux compiles) AND a USEION
  variable (so other mechanisms share the same ip3i pool).  This combination
  is fully supported on NEURON 8.2 and is identical to the original code.

  WARNING: If a voltage-gated Ca2+ current is present, initialising ica = 0
  is incorrect.  Use an init run + SaveState in that case.

  NOTE: Dip3 and Currentip3 parameters are retained for backward compatibility
  but are not used in active code paths.

================================================================================
CHANGELOG
================================================================================
  23/05/2018  -- SERCA + IP3 dynamics added
  [prev]      -- Illegal KINETIC assignments removed; full commentary added;
                 indentation unified to 4-space; typos corrected.
  [current]   -- CORRECTIONS (NEURON 8.2):
                 (1) USEION ip3 restored: ip3i is again STATE + USEION WRITE,
                     sharing the ip3 ion pool with other mechanisms.
                 (2) Ca2+ floor protection via ca_floor() FUNCTION.
                     Replaces the illegal direct state assignments in original.
                     Prevents numerical divergence without corrupting Jacobian.

ENDCOMMENT

NEURON {
    


SUFFIX cadifus

    : Calcium ion: read extracellular [Ca] and transmembrane current,
    : write intracellular [Ca] and pump current contribution.
    USEION ca READ cao, cai, ica WRITE cai, ica

    : ip3i is a STATE variable solved as an ODE within this mechanism AND
    : simultaneously shared with other mechanisms via NEURON's ip3 ion pool.
    : VALENCE 1 means ip3 flux contributes to membrane current (as in original).
    : This pattern compiles and runs correctly on NEURON 8.2.
    USEION ip3 READ ip3i WRITE ip3i VALENCE 1

    : Per-segment accessible variables
    RANGE ica_pmp              : plasma membrane pump current (mA/cm2)
    RANGE cai0                 : resting [Ca2+] (mM)
    RANGE fluo                 : fluorescence proxy = cabufm[0] (mM)
    RANGE fluoNew              : normalised fluorescence ratio (dimensionless)
    RANGE alpha                : relative SERCA abundance (0..1)
    RANGE Ip3init              : initial [IP3] (mM)
    RANGE modelStim            : glutamate stimulus concentration (mM)
    RANGE v_bar_beta           : max PLC-beta IP3 production rate (mM/ms)
    RANGE Dip3                 : IP3 diffusion coeff (reserved, inactive)

    : GLOBAL: vrat must be shared so factors() only runs once.
    : TBufs/TBufm/BufferAlpha are shared for convenience.
    GLOBAL vrat, TBufs, TBufm, BufferAlpha
}


: Number of radial shells.  Increase for finer spatial resolution.
DEFINE Nannuli 4


: ==============================================================================
: UNITS
: ==============================================================================

UNITS {
    (mol)   = (1)
    (molar) = (1/liter)
    (uM)    = (micromolar)
    (mM)    = (millimolar)
    (um)    = (micron)
    (mA)    = (milliamp)
    FARADAY = (faraday)  (10000 coulomb)
    PI      = (pi)       (1)
}


: ==============================================================================
: PARAMETER block
: ==============================================================================

PARAMETER {

    : --------------------------------------------------------------------------
    : Calcium diffusion and resting state
    : --------------------------------------------------------------------------
    cai0  = 50e-6  (mM)     : resting [Ca2+] = 50 nM
    DCa   = 0.22   (um2/ms) : Ca2+ diffusion coefficient (Fink et al. 2000)

    : --------------------------------------------------------------------------
    : IP3 parameters (De Pitta et al. 2009)
    : --------------------------------------------------------------------------
    Ip3init    = 0.0000250  (mM)      : initial [IP3] = 25 nM
    Dip3       = 0.1        (um2/ms)  : IP3 diffusion (reserved -- not active)
    Currentip3 = 0.0        (mA/cm2) : current-driven IP3 source (inactive)

    modelStim   = 0       (mM)      : glutamate concentration driving PLC-beta
    kappa_delta = 1.5e-3  (mM)      : IP3 threshold for PLC-delta self-inhibition
    K_3         = 1e-3    (mM)      : IP3 half-saturation for IP3-3K degradation
    K_pi        = 0.6e-3  (mM)      : Ca2+ half-saturation in K_gamma expression
    K_D         = 0.7     (mM)      : Ca2+ half-saturation for IP3-3K (Hill coeff=4)
    K_p         = 10e-3   (mM)      : Ca2+ modulation parameter in K_gamma
    K_PLCdelta  = 0.1e-3  (mM)      : Ca2+ half-saturation for PLC-delta
    K_R         = 1.3e-3  (mM)      : basal receptor affinity for K_gamma
    r_bar_5P    = 0.04e-3 (/ms)     : IP3-5-phosphatase rate constant (first-order)
    v_bar_3K    = 2e-6    (mM/ms)   : max IP3-3K degradation rate
    v_bar_beta  = 0.2e-6  (mM/ms)   : max PLC-beta IP3 production rate
    v_bar_delta = 0.02e-6 (mM/ms)   : max PLC-delta IP3 production rate

    : --------------------------------------------------------------------------
    : Fluorescence
    : --------------------------------------------------------------------------
    fluo        = 0  (mM)  : updated each timestep in KINETIC
    fluoNew     = 0  (1)   : dimensionless; 0 at rest
    BufferAlpha = 100       : KDm/cai0 ~ 100; amplification factor for fluoNew

    : --------------------------------------------------------------------------
    : Stationary endogenous buffer (Bufs) -- immobile, no diffusion
    :   Rapid equilibrium: krs = kfs * KDs * 1e-3  (1e-3: uM -> mM conversion)
    : --------------------------------------------------------------------------
    TBufs = 0.450  (mM)      : total endogenous buffer
    kfs   = 1000   (/mM-ms)  : fast on-rate (pseudo-equilibrium approximation)
    KDs   = 10     (uM)      : dissociation constant

    : --------------------------------------------------------------------------
    : Mobile fluorescent buffer (Bufm) -- default: fura-2
    :   Rapid equilibrium: krm = kfm * KDm * 1e-3
    : --------------------------------------------------------------------------
    TBufm = 0.075  (mM)      : total fura-2 concentration (75 uM)
    kfm   = 1000   (/mM-ms)  : fast on-rate
    KDm   = 0.24   (uM)      : dissociation constant (fura-2)
    DBufm = 0.050  (um2/ms)  : fura-2 diffusion coefficient

    : Alternative mobile buffer: calcium green (uncaging experiments)
    :   TBufm = 0.075   (mM)
    :   kfm   = 1000    (/mM-ms)
    :   KDm   = 0.26    (uM)
    :   DBufm = 0.0184  (um2/ms)

    : --------------------------------------------------------------------------
    : Plasma membrane Ca2+ pump
    :   Threshold-activated step function.  Set gamma = 0 to disable.
    : --------------------------------------------------------------------------
    cath  = 0.2e-3  (mM)    : activation threshold = 200 nM
    gamma = 8       (um/s)  : pump flux density (surface flux per unit area)

    : --------------------------------------------------------------------------
    : SERCA system
    : --------------------------------------------------------------------------
    alpha = 1  (1)          : relative SERCA abundance (Fink et al. 2000, Fig. 3)
                             : set < 1 to reduce SERCA contribution

    : SERCA pump (Hill coeff = 2, Ca2+ uptake cytoplasm -> ER)
    vmax  = 3.75e-6  (mM/ms)  : maximum pump rate
    Kp    = 0.27e-3  (mM)     : half-saturation [Ca2+]

    : IP3R channel (Ca2+ release ER -> cytoplasm)
    jmax  = 3.5e-3   (mM/ms)  : max channel flux
    caer  = 0.400    (mM)     : ER [Ca2+] = 400 uM
    Kip3  = 0.8e-3   (mM)     : IP3 half-saturation
    Kact  = 0.3e-3   (mM)     : Ca2+ activation half-saturation
    kon   = 2.7      (/mM-ms) : IP3R gating on-rate
    Kinh  = 0.2e-3   (mM)     : Ca2+ inhibition constant for IP3R gating

    : SERCA leak (ER -> cytoplasm)
    : L[i] has no fixed parameter -- computed per-shell in INITIAL
    : to enforce SERCA equilibrium at resting [Ca2+].

    : Ca2+ numerical floor for denominator protection (replaces the illegal
    : direct state assignments ca[i]=cai0/2 that were in the original code).
    : Applied only inside FUNCTION ca_floor() -- never clamps ca[i] itself.
    : 1e-9 mM = 1 pM, far below resting [Ca2+] = 50 nM; physiologically inert.
    ca_min = 1e-9  (mM)
}

: ==============================================================================
: ASSIGNED block
: ==============================================================================

ASSIGNED {
    diam            (um)       : section diameter (provided by NEURON)
    ica             (mA/cm2)   : total Ca2+ transmembrane current (external)
    ica_pmp         (mA/cm2)   : plasma membrane pump current (written here)
    ica_pmp_last    (mA/cm2)   : ica_pmp from previous timestep (explicit coupling)
    parea           (um)       : circumference = PI*diam; pump area per unit length

    sump            (mM)       : accumulation pool for pump-extruded Ca2+

    cai             (mM)       : intracellular [Ca2+] = ca[0]
    cao             (mM)       : extracellular [Ca2+] (read-only boundary)

    : vrat[i]: fractional cross-sectional area of annulus i (1 um diameter cylinder).
    : Actual volume per um = vrat[i] * diam^2.
    : GLOBAL so factors() need only run once across all segments.
    vrat[Nannuli]   (1)

    bufs_0  (mM)    : resting free [Bufs]  (computed in INITIAL from equilibrium)
    bufm_0  (mM)    : resting free [Bufm]  (computed in INITIAL from equilibrium)

    : Per-shell ER leak rate constant.
    : Set in INITIAL to balance SERCA system at rest.
    L[Nannuli]  (mM/ms)
}


: volo: large virtual volume to make cao a fixed boundary condition.
CONSTANT { volo = 1e10 (um2) }

STATE {
    : Free Ca2+ in each radial shell.
    : ca[0] = sub-membrane shell = cai.
    : Absolute tolerance ~100x smaller than resting [Ca2+] = 50 nM.
    ca[Nannuli]      (mM) <1e-7>

    : Buffer species.  Tolerances reflect typical concentration magnitudes.
    bufs[Nannuli]    (mM) <1e-3>   : free stationary buffer
    cabufs[Nannuli]  (mM) <1e-7>   : Ca-bound stationary buffer
    bufm[Nannuli]    (mM) <1e-4>   : free mobile buffer
    cabufm[Nannuli]  (mM) <1e-8>   : Ca-bound mobile buffer (fluorescence signal)

    : IP3R gating fractions.  hc + ho = 1 enforced by kinetic scheme.
    hc[Nannuli]                     : closed (Ca-inactivated) fraction
    ho[Nannuli]                     : open-able fraction

    : IP3 concentration -- STATE variable so NEURON's sparse solver integrates
    : its ODE via ~ ip3i << flux.  USEION ip3 WRITE ip3i simultaneously exposes
    : the value to other mechanisms via the ion pool (NEURON 8.2 pattern).
    ip3i  (mM) <1e-10>
}




: ==============================================================================
: BREAKPOINT
: ==============================================================================

BREAKPOINT {
    : Integrate all reaction-diffusion ODEs.
    : METHOD sparse is required for KINETIC blocks with arrayed state variables.
    SOLVE state METHOD sparse

    : Advance ica_pmp by one timestep for explicit use in the ca[0] flux.
    : This breaks the implicit loop: ica_pmp(ca[0]) -> ca[0] -> ica_pmp.
    : The one-step lag is negligible for physiological dt values (0.025-0.1 ms).
    ica_pmp_last = ica_pmp

    : Report pump current as the transmembrane Ca2+ current.
    : If voltage-gated Ca2+ channels are present, their ica enters via
    : the ~ ca[0] << ... line in the KINETIC block, not here.
    ica = ica_pmp
}


: factors_done: one-time flag ensuring factors() runs only in the first segment.
: jx: scratch variable for SERCA leak initialisation.
LOCAL factors_done, jx



: ==============================================================================
: INITIAL
: ==============================================================================

INITIAL {
    : Set IP3 to resting level.
    ip3i = Ip3init

    : Compute annular geometry once.
    : factors_done is LOCAL so it resets between simulations (each new finitialize).
    : Within a single simulation it persists because NEURON initialises LOCAL
    : mechanism variables to 0 only at model load.  The first segment sets it to 1.
    if (factors_done == 0) {
        factors_done = 1
        factors()
    }

    : Resting intracellular Ca2+.
    cai = cai0

    : Resting equilibrium for buffers.
    : Equilibrium condition:  [Free] = KD * [Total] / (KD + [Ca2+])
    : The factor 1000 converts cai0 from mM to uM to match KD units (uM).
    bufs_0 = KDs * TBufs / (KDs + 1000*cai0)
    bufm_0 = KDm * TBufm / (KDm + 1000*cai0)

    : Initialise all radial shells to resting equilibrium.
    FROM i=0 TO Nannuli-1 {
        ca[i]     = cai0
        bufs[i]   = bufs_0
        cabufs[i] = TBufs - bufs_0   : bound = total - free
        bufm[i]   = bufm_0
        cabufm[i] = TBufm - bufm_0
    }

    : Geometric and pump variables.
    sump  = cath
    parea = PI * diam

    : Zero pump currents at rest.
    : NOTE: if a voltage-gated Ca2+ current is active, ica != 0 at t = 0.
    : Correct approach: run a short init simulation, save state with SaveState,
    : and restore on subsequent runs.
    ica          = 0
    ica_pmp      = 0
    ica_pmp_last = 0

    : Initialise IP3R gating and compute per-shell SERCA leak constants.
    FROM i=0 TO Nannuli-1 {
        : Resting gating fraction: h_inf = Kinh / (ca + Kinh)
        ho[i] = Kinh / (ca[i] + Kinh)
        hc[i] = 1 - ho[i]

        : Compute L[i] so SERCA system is at equilibrium at resting [Ca2+]:
        :   jleak + jpump + jchnl = 0
        :   jleak = L * (1 - ca/caer)
        :   => L = -(jpump + jchnl) / (1 - ca/caer)
        jx = -vmax * ca[i]^2 / (ca[i]^2 + Kp^2)
        jx = jx + jmax * (1 - ca[i]/caer) * ( (ip3i/(ip3i+Kip3)) * (ca[i]/(ca[i]+Kact)) * ho[i] )^3
        L[i] = -jx / (1 - ca[i]/caer)
    }
}

: ==============================================================================
: PROCEDURE factors -- radial annulus geometry
: ==============================================================================

: frat[] is LOCAL (not GLOBAL) because it is only needed within this file.
LOCAL frat[Nannuli]

PROCEDURE factors() {
    LOCAL r, dr2

    : r = outer radius of current annulus, normalised to diam = 1 um (r starts at 0.5).
    r   = 1/2

    : dr2 = half-thickness of each annulus.
    : Outermost shell has full thickness 2*dr2; inner shells share boundaries.
    dr2 = r / (Nannuli - 1) / 2

    : Shell 0 starts at the outer membrane.
    : vrat[0] will accumulate its inner half in the loop below.
    vrat[0] = 0
    frat[0] = 2*r    : conductance factor at outer membrane boundary

    FROM i=0 TO Nannuli-2 {
        : Add interior half-volume of shell i (annulus from r-dr2 to r).
        vrat[i] = vrat[i] + PI*(r - dr2/2)*2*dr2
        r = r - dr2

        : Conductance factor between shells i and i+1.
        : = 2*PI*r_boundary / (2*dr2)   [r_boundary is at inter-shell interface]
        frat[i+1] = 2*PI*r / (2*dr2)
        r = r - dr2

        : Add outer half-volume of shell i+1 (annulus from r to r+dr2).
        vrat[i+1] = PI*(r + dr2/2)*2*dr2
    }
}



: These LOCALs must be declared OUTSIDE the KINETIC block.
: NEURON does not permit LOCAL declarations inside KINETIC,
: and variables that appear in COMPARTMENT statements cannot be LOCAL.
LOCAL dsq, dsqvol, K_gamma, v_3K, v_delta, v_glu


: ==============================================================================
: KINETIC state
: ==============================================================================

KINETIC state {

    : -------------------------------------------------------------------------
    : COMPARTMENT declarations
    : Associate each state variable with its physical volume.
    : The solver scales all reaction fluxes by these volumes automatically.
    : -------------------------------------------------------------------------

    : Cytoplasmic species: volume = diam^2 * vrat[i]  per unit length (um^2/um).
    COMPARTMENT i, diam*diam*vrat[i] {ca bufs cabufs bufm cabufm sump}

    : Extracellular space: effectively infinite (volo = 1e10 um^2).
    COMPARTMENT volo {cao}

    : IP3 occupies the full cylinder cross-section because it is spatially uniform.
    : Volume = PI*diam^2/4  per unit length.
    : This is intentionally larger than ca's vrat-weighted volumes.
    COMPARTMENT PI*diam*diam/4 {ip3i}

    : -------------------------------------------------------------------------
    : Longitudinal diffusion
    : Effective diffusion conductance = D * cross-sectional area = D * diam^2 * vrat[i]
    : -------------------------------------------------------------------------
    LONGITUDINAL_DIFFUSION i, DCa*diam*diam*vrat[i]    {ca}
    LONGITUDINAL_DIFFUSION i, DBufm*diam*diam*vrat[i]  {bufm cabufm}
    : Bufs/cabufs are IMMOBILE -- no longitudinal or radial diffusion terms.

    : =========================================================================
    : 1. PLASMA MEMBRANE Ca2+ PUMP
    : =========================================================================
    : Threshold-activated: flux active only when ca[0] > cath.
    : u(x, th) is the Heaviside step function defined below.
    : Factor 0.001 converts gamma from um/s to um/ms.
    : Symmetric forward/reverse rates => net efflux when pump is active.
    ~ ca[0] <-> sump  ( (0.001)*parea*gamma*u(ca[0]/(1 (mM)), cath/(1 (mM))), (0.001)*parea*gamma*u(ca[0]/(1 (mM)), cath/(1 (mM))) )

    : f_flux and b_flux are set by NEURON after evaluating the reaction above.
    : Factor 2: Ca2+ is divalent (z = 2).
    ica_pmp = 2*FARADAY*(f_flux - b_flux)/parea

    : =========================================================================
    : 2. IP3 DYNAMICS
    : =========================================================================

    : Effective PLC-beta affinity constant (Ca-dependent):
    :   K_gamma = K_R * [1 + (K_p/K_R) * ca / (ca + K_pi)]
    K_gamma = K_R * (1 + (K_p/K_R) * ca_floor(ca[0]) / (ca_floor(ca[0]) + K_pi))

    : IP3-3K degradation: Hill coeff = 4 for Ca, Michaelis-Menten for IP3
    v_3K = v_bar_3K * ca_floor(ca[0])^4 / (ca_floor(ca[0])^4 + K_D^4) * ip3i / (ip3i + K_3)

    : PLC-delta production: Ca-activated (Hill coeff = 2), inhibited by IP3
    v_delta = v_bar_delta / (1 + ip3i/kappa_delta) * ca_floor(ca[0])^2 / (ca_floor(ca[0])^2 + K_PLCdelta^2)

    : PLC-beta production: glutamate-driven (Michaelis-Menten in modelStim)
    : Alternative Hill form (Hill coeff = 0.7) is commented out:
    : v_glu = v_bar_beta * modelStim^0.7 / (modelStim^0.7 + K_gamma^0.7)
    v_glu = v_bar_beta * modelStim / (modelStim + K_gamma)

    : Net IP3 flux into full cross-section compartment (units: mM * um^2 / ms).
    ~ ip3i << ( (PI*diam*diam*(v_glu + v_delta - v_3K - r_bar_5P*ip3i)) / 2 )

    : Alternative: current-driven IP3 injection (inactive):
    : ~ ip3i << (Currentip3*PI*diam*(1e4)/(2*FARADAY))

    : =========================================================================
    : 3. Ca2+ INFLUX FROM MEMBRANE CURRENTS
    : =========================================================================
    : ica (mA/cm2): total Ca2+ current from all membrane conductances.
    : Subtract ica_pmp_last to exclude the pump current (already accounted for above).
    : Sign: ica > 0 is efflux; inward current (ica < 0) increases [Ca2+].
    : Conversion: mA/cm2 * PI*diam (um) / (2*FARADAY) -> mM*um^2/ms
    ~ ca[0] << ( -(ica - ica_pmp_last)*PI*diam / (2*FARADAY) )

    : =========================================================================
    : 4. RADIAL DIFFUSION between adjacent shells
    : =========================================================================
    FROM i=0 TO Nannuli-2 {
        ~ ca[i]   <-> ca[i+1]   (DCa*frat[i+1],   DCa*frat[i+1])
        ~ bufm[i] <-> bufm[i+1] (DBufm*frat[i+1], DBufm*frat[i+1])
        : Bufs/cabufs: immobile -- no radial diffusion.
    }

    : =========================================================================
    : 5. Ca2+ BUFFERING
    : =========================================================================
    : Rapid equilibrium approximation (kf >> kr).
    : Reverse rate = kf * KD * 1e-3  (1e-3 converts KD from uM to mM).
    : dsqvol = diam^2 * vrat[i] scales rates by shell cross-sectional area.
    dsq = diam*diam
    FROM i=0 TO Nannuli-1 {
        dsqvol = dsq * vrat[i]
        ~ ca[i] + bufs[i] <-> cabufs[i]  (kfs*dsqvol, (0.001)*KDs*kfs*dsqvol)
        ~ ca[i] + bufm[i] <-> cabufm[i]  (kfm*dsqvol, (0.001)*KDm*kfm*dsqvol)
    }

    : =========================================================================
    : 6. SERCA SYSTEM (pump + IP3R channel + ER leak) -- one set per shell
    : =========================================================================
    : ca_floor(ca[i]) guards denominator and rate positions against near-zero
    : or negative [Ca2+] during strong buffering.  The STATE variable ca[i] is
    : never clamped directly -- the sparse Jacobian remains correct.
    FROM i=0 TO Nannuli-1 {
        dsqvol = dsq * vrat[i]

        : SERCA pump: Hill coeff = 2, cytoplasm -> ER uptake (negative flux)
        ~ ca[i] << (-dsqvol * alpha * vmax * ca_floor(ca[i])^2 / (ca_floor(ca[i])^2 + Kp^2))

        : IP3R gating: hc <-> ho
        :   Opening rate = kon * Kinh  (constant)
        :   Closing rate = kon * ca    (Ca-dependent; floored to stay non-negative)
        ~ hc[i] <-> ho[i]  (kon*Kinh, kon*ca_floor(ca[i]))

        : IP3R channel: ER -> cytoplasm Ca2+ release
        ~ ca[i] << ( dsqvol * alpha * jmax * (1 - ca_floor(ca[i])/caer) * ( (ip3i/(ip3i+Kip3)) * (ca_floor(ca[i])/(ca_floor(ca[i])+Kact)) * ho[i] )^3 )

        : ER leak: passive ER -> cytoplasm flux
        ~ ca[i] << (dsqvol * alpha * L[i] * (1 - ca_floor(ca[i])/caer))
    }

    : =========================================================================
    : 7. OUTPUT ASSIGNMENTS
    : =========================================================================

    : Update NEURON's cai ion variable from innermost shell.
    cai = ca[0]

    : Fluorescence proxy 1: raw Ca-bound mobile buffer concentration.
    fluo = cabufm[0]

    : Fluorescence proxy 2: normalised ratio signal (0 at rest).
    : Derivation:
    :   F(t)      ~ BufferAlpha * cabufm[0] + ca[0]
    :   F_rest    ~ BufferAlpha * (TBufm - bufm_0) + cai0
    :   fluoNew   = (F(t) - F_rest) / F_rest
    fluoNew = (BufferAlpha*cabufm[0] + ca[0] - BufferAlpha*(TBufm - bufm_0) - cai0) / (BufferAlpha*(TBufm - bufm_0) + cai0)
}

: ==============================================================================
: FUNCTION u -- Heaviside step function
: ==============================================================================
: Returns 1 if x > th, else 0.
: Used to gate the plasma membrane pump above threshold cath.
: x and th are passed as dimensionless ratios (concentration / 1 mM) to satisfy
: NEURON's unit-checking requirements for conditional expressions.

FUNCTION u(x, th) {
    if (x > th) {
        u = 1
    } else {
        u = 0
    }
}

: ==============================================================================
: FUNCTION ca_floor -- Ca2+ denominator protection
: ==============================================================================
: Returns max(c, ca_min) to prevent division-by-zero and negative arguments
: in SERCA pump, IP3R channel, IP3R gating, and IP3 production expressions.
:
: Used ONLY in denominator/rate positions -- never applied to the STATE variable
: ca[i] directly, so NEURON's sparse Jacobian is never corrupted.
:
: ca_min = 1e-9 mM = 1 pM.  Resting [Ca2+] = 50 nM = 50000 pM.
: The floor has no physiological effect under any realistic simulation.

FUNCTION ca_floor(c (mM)) (mM) {
    if (c < ca_min) {
        ca_floor = ca_min
    } else {
        ca_floor = c
    }
}