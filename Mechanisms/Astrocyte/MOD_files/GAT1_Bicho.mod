COMMENT
================================================================================
GAT1_Bicho.mod  --  8-state alternating-access kinetic model of GAT1
                    GABA treated as a tracked ion (VALENCE 0)
================================================================================

REFERENCE
  Bicho A., Grewer C. (2005).
  Rapid substrate-induced charge movements of the GABA transporter GAT1.
  Biophys. J. 89, 211-231.  DOI: 10.1529/biophysj.105.061002  PMC1366519

  Correction: Biophys. J. 90(2):709 (2006).

================================================================================
GABA AS AN ION -- DESIGN RATIONALE
================================================================================

In this version GABAi and GABAo are live concentrations maintained by
NEURON's ion pool mechanism rather than fixed parameters.  This allows:
  - gabai and gabao to change during simulation as GABA is transported
  - coupling to other mechanisms that produce or consume GABA (e.g.
    GAD, GABA-T, GABA_A receptors that set synaptic [GABA])
  - spatial diffusion of GABA if used with rxd or extracellular mechanism

CHARGE ACCOUNTING
-----------------
GABA is a zwitterion at physiological pH (pKa_NH3+ ~10.6, pKa_COOH ~4.0).
Net charge = 0.  Therefore VALENCE 0 is declared for the gaba ion.

Consequences:
  1. igaba does NOT contribute to membrane current / Vm changes.
     All electrogenic charge comes from the Na+/Cl- co-transport steps
     and is carried by the NONSPECIFIC_CURRENT iGABAcharge.
  2. NEURON's concentration update for VALENCE 0 ions uses a simplified
     molar flux rather than the electrical formula i/(z*F).
     The update is: d[gaba]i/dt = -igaba / (F * volume_factor)
     where igaba carries units of mol/cm2/ms (molar flux density).
     NOTE: for VALENCE 0, igaba must be a MOLAR FLUX, not a current.
     Units of igaba: mol/cm2/ms  (NOT mA/cm2).

HOW TO USE
----------
Before using this mechanism, declare the gaba ion in HOC/Python:

    HOC:
        ion_style("gaba_ion", 1, 2, 0, 0, 0)
        : args: name, c_style, e_style, einit, erev_corr, celsius_dep

    Python (NEURON):
        h.ion_style("gaba_ion", 1, 2, 0, 0, 0)

    This tells NEURON to track gaba concentrations but not add igaba
    to the membrane current (VALENCE 0 behaviour).

Set initial concentrations in each segment:
    seg.gabai0_gaba_ion = 1.0    : mM; intracellular GABA
    seg.gabao0_gaba_ion = 1e-5   : mM; extracellular GABA

GABA FLUX EXPRESSION (igaba)
----------------------------
The net GABA flux across the membrane is identified with the
translocation step AN2G <-> BN2G:
    J_GABA = k45*AN2G - k54*BN2G    [1/ms, dimensionless state fractions]

Forward transport (J_GABA > 0) moves GABA from extracellular to
intracellular: gabao decreases, gabai increases.

Units of igaba (molar flux density):
    igaba [mol/cm2/ms] = density [mol/cm2] * J_GABA [1/ms]

No 1e6 or Faraday factor here because this is a MOLAR FLUX, not a current.
NEURON uses this to update concentration pools directly.

ELECTROGENIC CURRENT (iGABAcharge)
-----------------------------------
iGABAcharge is a NONSPECIFIC_CURRENT carrying all electrogenic charge.
It is computed from the partial charge flux sum as before:
    iGABAcharge [mA/cm2] = -(1e6)*F*density * sum(z_i * net_flux_i)
This drives Vm changes.  It does NOT update any ion concentrations.

Na+ and Cl- concentrations are now live ion values read from NEURON's
built-in na_ion and cl_ion pools each timestep (USEION na/cl READ).
This allows nai/nao and cli/clo to change dynamically if other mechanisms
(e.g. Na+/K+-ATPase, KCC2, Na+ channels) modify the ion pools.
No WRITE is needed for na or cl: the electrogenic Na+/Cl- charge flux
is already captured entirely by iGABAcharge (NONSPECIFIC_CURRENT).
Writing ina/icl would double-count the charge and corrupt Vm.

================================================================================
KINETIC SCHEME (Fig. 11, Bicho & Grewer 2005)
================================================================================

8 states; sequential alternating-access with Cl side-branch:

  A    = empty transporter, outward-facing
  AN   = 1 Na+ bound (extracellular)
  AN2  = 2 Na+ bound (extracellular)
  AN2G = 2 Na+ + GABA bound (extracellular, fully loaded)
  BN2G = 2 Na+ + GABA bound (inward-facing, translocating)  <-- GABA crosses here
  B    = empty transporter, inward-facing
  BC   = B with extracellular Cl- bound
  AC   = Cl- occluded, ready for intracellular release

  Forward cycle: A->AN->AN2->AN2G->BN2G->B->(BC->AC->A or direct ->A)

================================================================================
PARAMETER CORRECTIONS vs ORIGINAL Bicho & Grewer CODE
================================================================================
  z23:  0.3  -> 0.1   (paper: z23=0.1)
  k560: 0.015 -> 0.001 /ms/mM3  (paper: 1e6 M-3ms-1 = 0.001 mM-3ms-1)
  k160: 0.005 -> 0.02  /ms       (paper: 0.02 ms-1)
  z61:  -0.8  -> -0.215           (paper: z61=-0.215)
  z81:  -0.215 -> -0.8            (z61/z81 swap, see previous version notes)
  k760: 20    -> 10    /ms        (paper: 10 ms-1)

================================================================================
BUGS FIXED (inherited from previous version)
================================================================================
  Bug 1: SOLVE before rate update in BREAKPOINT -> one-step lag. Fixed.
  Bug 2: INITIAL calls STEADYSTATE with all k_ij=0. Fixed.

================================================================================
ENDCOMMENT


NEURON {
    SUFFIX GAT1_Bicho

    : GABA treated as a tracked ion with VALENCE 0.
    : gabai and gabao are read from the gaba ion pool each timestep.
    : igaba is written back as a molar flux to update concentrations.
    : VALENCE 0: igaba does NOT contribute to membrane current.
    : Requires ion_style("gaba_ion", ...) in HOC/Python -- see header.
    USEION gaba READ gabai, gabao WRITE igaba VALENCE 0

    : All electrogenic charge from Na+/Cl- steps carried here.
    : This is the only current that affects Vm.
    NONSPECIFIC_CURRENT iGABAcharge

    : Na+ concentrations read live from na_ion pool each timestep.
    : READ only -- electrogenic Na+ charge is in iGABAcharge (NONSPECIFIC).
    USEION na READ nai, nao

    : Cl- concentrations read live from cl_ion pool each timestep.
    : READ only -- electrogenic Cl- charge is in iGABAcharge (NONSPECIFIC).
    USEION cl READ cli, clo

    RANGE density, iGABA1
    : nai, nao, cli, clo are now ion variables (not RANGE parameters)
}

UNITS {
    (mV)    = (millivolt)
    (mA)    = (milliamp)
    (mM) = (milli/liter)
    (mS)    = (millisiemens)
    (molar) = (1/liter)
}

PARAMETER {

    : Physical constants
    GasConstant = 8.314   (joule/mol)
    Temp        = 25                     : degC; room temperature (paper conditions)
    Faraday     = 96487   (coulomb/mol)
    pi          = 3.1415926

    : Na+ and Cl- are now read from NEURON ion pools (USEION na/cl).
    : Set initial concentrations in HOC/Python before simulation:
    :   seg.nai0_na_ion = 10    (mM)
    :   seg.nao0_na_ion = 145   (mM)  : usually set by default already
    :   seg.cli0_cl_ion = 5     (mM)
    :   seg.clo0_cl_ion = 130   (mM)

    : Transporter surface density (~6678/um2 for HEK293; scale down for neurons)
    density = 1.10895e-12  (mol/cm2)

    : ------------------------------------------------------------------
    : Intrinsic rate constants (paper values; mM units throughout)
    : ------------------------------------------------------------------

    : A <-> AN  (1st extracellular Na+)
    k120 = 0.0005  (/ms /mM)   : 0.5 M-1ms-1 = 0.0005 mM-1ms-1
    k210 = 0.01    (/ms)

    : AN <-> AN2  (2nd extracellular Na+)
    k230 = 0.01    (/ms /mM)   : 10 M-1ms-1 = 0.01 mM-1ms-1
    k320 = 0.1     (/ms)

    : AN2 <-> AN2G  (extracellular GABA binding; z34=0, voltage-independent)
    : gabao read from ion pool each step (not a parameter)
    k340 = 10      (/ms /mM)   : 10000 M-1ms-1 = 10 mM-1ms-1
    k430 = 1       (/ms)

    : AN2G <-> BN2G  (translocation; electrogenic per Bicho & Grewer 2005)
    k450 = 1       (/ms)
    k540 = 1       (/ms)

    : BN2G <-> B  (intracellular substrate release; 3rd-order ON)
    : gabai read from ion pool each step (not a parameter)
    : CORRECTED: was 0.015 (15x too large)
    k560 = 0.001   (/ms /mM3)  : 1e6 M-3ms-1 = 0.001 mM-3ms-1
    k650 = 0.3     (/ms)

    : B <-> A  (direct empty carrier return)
    : CORRECTED: k160 was 0.005 (4x too small)
    k160 = 0.02    (/ms)
    k610 = 0.005   (/ms)

    : B <-> BC  (extracellular Cl- binding)
    : CORRECTED: k760 was 20 (2x too large)
    k670 = 0.2     (/ms /mM)   : 200 M-1ms-1 = 0.2 mM-1ms-1
    k760 = 10      (/ms)

    : BC <-> AC  (Cl- translocation)
    k780 = 0.4     (/ms)
    k870 = 0.02    (/ms)

    : A <-> AC  (intracellular Cl- release/rebinding)
    k810 = 50      (/ms)
    k180 = 10      (/ms /mM)

    : ------------------------------------------------------------------
    : Partial charge factors (dimensionless, empirically fitted)
    : z > 0: step moves +charge inward (forward rate enhanced at -v)
    : z < 0: step moves +charge outward (forward rate enhanced at +v)
    : ------------------------------------------------------------------
    z12 =  0.9    : 1st Na+ binding; dominant (~90% of total charge)
    z23 =  0.1    : CORRECTED from 0.3; paper: z23=0.1
    z34 =  0      : GABA binding; electroneutral (GABA is zwitterion)
    z45 =  0.2    : translocation; electrogenic per Bicho & Grewer 2005
    z56 =  0.2    : intracellular substrate release
    z61 = -0.215  : CORRECTED from -0.8; direct empty carrier return B->A
    z67 =  0.01   : Cl- binding to B; near electroneutral
    z78 =  0.005  : Cl- translocation BC->AC; near electroneutral
    z81 = -0.8    : CORRECTED from -0.215; intracellular Cl- release AC->A
}

ASSIGNED {
    v (mV)

    : Na+ ion variables -- filled by NEURON from na_ion pool each step
    nai  (mM)              : intracellular [Na+]
    nao  (mM)              : extracellular [Na+]

    : Cl- ion variables -- filled by NEURON from cl_ion pool each step
    cli  (mM)              : intracellular [Cl-]
    clo  (mM)              : extracellular [Cl-]

    : GABA ion variables (set by NEURON from gaba_ion pool each step)
    gabai  (mM)            : intracellular [GABA] -- read from ion pool
    gabao  (mM)            : extracellular [GABA] -- read from ion pool

    : Outputs
    igaba        (mol/cm2/ms) : molar GABA flux -- written to gaba_ion pool
                               : VALENCE 0: no contribution to membrane current
    iGABAcharge  (mA/cm2)    : electrogenic current (Na+/Cl- charge movement)
    iGABA1       (mA)        : total single-cell current for validation

    : Voltage-scaled rate constants (computed each timestep)
    k12 (/ms /mM)
    k21 (/ms)
    k23 (/ms /mM)
    k32 (/ms)
    k34 (/ms /mM)
    k43 (/ms)
    k45 (/ms)
    k54 (/ms)
    k56 (/ms /mM3)
    k65 (/ms)
    k16 (/ms)
    k61 (/ms)
    k67 (/ms /mM)
    k76 (/ms)
    k78 (/ms)
    k87 (/ms)
    k81 (/ms)
    k18 (/ms /mM)
}

STATE {
    : Transporter state occupancy fractions (dimensionless; sum = 1)
    A AN AN2 AN2G BN2G B BC AC
}

INITIAL {
    : Compute voltage-dependent rates from initial v BEFORE STEADYSTATE solve.
    : (Bug fix: original code left all k_ij = 0 at this point.)
    k12 = k120*u(v, -z12)
    k21 = k210*u(v,  z12)
    k23 = k230*u(v, -z23)
    k32 = k320*u(v,  z23)
    k34 = k340*u(v, -z34)
    k43 = k430*u(v,  z34)
    k45 = k450*u(v, -z45)
    k54 = k540*u(v,  z45)
    k56 = k560*u(v, -z56)
    k65 = k650*u(v,  z56)
    k16 = k160*u(v,  z61)
    k61 = k610*u(v, -z61)
    k67 = k670*u(v, -z67)
    k76 = k760*u(v,  z67)
    k78 = k780*u(v, -z78)
    k87 = k870*u(v,  z78)
    k81 = k810*u(v, -z81)
    k18 = k180*u(v,  z81)
    SOLVE kin STEADYSTATE sparse
}

BREAKPOINT {
    : Step 1: update all voltage-dependent rates with current v.
    : (Bug fix: original code ran SOLVE first, using stale rates.)

    k12 = k120*u(v, -z12)
    k21 = k210*u(v,  z12)

    k23 = k230*u(v, -z23)
    k32 = k320*u(v,  z23)

    : z34=0 -> u(v,0)=1; GABA binding is voltage-independent.
    : gabao is read live from the gaba_ion pool (not a parameter here).
    k34 = k340*u(v, -z34)
    k43 = k430*u(v,  z34)

    : Translocation: KEY electrogenic step per Bicho & Grewer 2005
    k45 = k450*u(v, -z45)
    k54 = k540*u(v,  z45)

    : Intracellular substrate release.
    : gabai is read live from the gaba_ion pool.
    k56 = k560*u(v, -z56)
    k65 = k650*u(v,  z56)

    : Direct empty carrier return (z61=-0.215)
    k16 = k160*u(v,  z61)
    k61 = k610*u(v, -z61)

    : Cl- binding/translocation/release
    k67 = k670*u(v, -z67)
    k76 = k760*u(v,  z67)

    k78 = k780*u(v, -z78)
    k87 = k870*u(v,  z78)

    : z81=-0.8: Cl- exits to cytoplasm, outward conventional current
    k81 = k810*u(v, -z81)
    k18 = k180*u(v,  z81)

    : Step 2: integrate kinetic ODEs with current-step rates
    SOLVE kin METHOD sparse

    : ------------------------------------------------------------------
    : Step 3a: GABA molar flux  (drives gaba_ion concentration changes)
    :
    : igaba [mol/cm2/ms] = density * net_GABA_translocation_rate
    :
    : The translocation step AN2G <-> BN2G is where GABA physically
    : crosses the membrane, so it defines the GABA molar flux.
    :
    : J_GABA = k45*AN2G - k54*BN2G  [1/ms]
    :   > 0 during forward transport (GABA entering cytoplasm)
    :   < 0 during reverse transport (GABA efflux)
    :
    : Sign convention for USEION WRITE igaba:
    :   NEURON convention: positive igaba = outward ion flow
    :   GABA entering cell (forward transport) = inward flow = negative igaba
    :   Therefore: igaba = -density * (k45*AN2G - k54*BN2G)
    :
    : NEURON then updates:
    :   dgabai/dt += -igaba / (volume_factor)   [inward flux increases gabai]
    :   dgabao/dt +=  igaba / (volume_factor)   [inward flux decreases gabao]
    :
    : Units check:
    :   density [mol/cm2] * rate [1/ms] = mol/cm2/ms  OK for VALENCE 0 ion flux
    : ------------------------------------------------------------------
    igaba = -density * (k45*AN2G - k54*BN2G)

    : ------------------------------------------------------------------
    : Step 3b: Electrogenic current  (drives Vm changes via NONSPECIFIC)
    :
    : iGABAcharge [mA/cm2] = -(1e6)*F*density * sum_i(z_i * net_flux_i)
    :
    : This is identical to the original iGABA expression.
    : ALL electrogenic charge from Na+/Cl- co-transport is here.
    : GABA contributes z34=0 so the AN2G term is zero -- included
    : for completeness and consistency.
    :
    : Units: F[C/mol] * density[mol/cm2] * flux[1/ms]
    :        = C/(cm2*ms) = 1e3 A/cm2 = 1e6 mA/cm2
    :        The prefactor 1e6 makes the result in mA/cm2.
    : ------------------------------------------------------------------
    : iGABAcharge = -(1e+06)*Faraday*density*(         \
        : z12*(A*k12*nao    - AN*k21)                  \
      : + z23*(AN*k23*nao   - AN2*k32)                 \
      : + z34*(AN2*k34*gabao - AN2G*k43)               \
      : + z45*(AN2G*k45     - BN2G*k54)                \
      : + z56*(BN2G*k56*nai*nai*gabai - B*k65)         \
      : + z61*(B*k61        - A*k16)                   \
      : + z67*(B*k67*clo    - BC*k76)                  \
      : + z78*(BC*k78       - AC*k87)                  \
      : + z81*(AC*k81       - A*k18*cli)               \
	  
	  
	  iGABAcharge = -(1e+06)*Faraday*density*(z12*(A*k12*nao - AN*k21)+ z23*(AN*k23*nao - AN2*k32)+ z34*(AN2*k34*gabao - AN2G*k43)+ z45*(AN2G*k45 - BN2G*k54)+ z56*(BN2G*k56*nai*nai*gabai - B*k65)  + z61*(B*k61 - A*k16) +z67*(B*k67*clo - BC*k76) + z78*(BC*k78 - AC*k87)+ z81*(AC*k81 - A*k18*cli)
    
    )

    : Single-cell total current (for comparison with patch-clamp recordings)
    : Sphere ~40 um diameter; area = pi*d^2 = pi*4e-6 cm2
    : Multiply by 1e9 to convert mA -> pA
    iGABA1 = iGABAcharge * (4e-6(cm2)*pi)
}

KINETIC kin {
    : gabao and gabai are now live ion concentrations (from USEION gaba),
    : not parameters, so they reflect the current pool values at each step.

    ~ A   <-> AN    (k12*nao,            k21)   : 1st extracellular Na+
    ~ AN  <-> AN2   (k23*nao,            k32)   : 2nd extracellular Na+
    ~ AN2 <-> AN2G  (k34*gabao,          k43)   : extracellular GABA  [uses ion pool]
    ~ AN2G<-> BN2G  (k45,                k54)   : translocation (electrogenic)
    ~ BN2G<-> B     (k56*nai*nai*gabai,  k65)   : intracellular release [uses ion pool]
    ~ B   <-> A     (k61,                k16)   : direct empty carrier return
    ~ B   <-> BC    (k67*clo,            k76)   : extracellular Cl- binding
    ~ BC  <-> AC    (k78,                k87)   : Cl- occlusion
    ~ A   <-> AC    (k18*cli,            k81)   : intracellular Cl- release
    CONSERVE A+AN+AN2+AN2G+BN2G+B+BC+AC = 1
}

FUNCTION u(v(mV), z) {
    : Half-field Eyring rate scaling: u(v,z) = exp(z*F*v / (2*R*T))
    : 2*R*1000*(273+Temp) is the denominator with v in mV (1000 converts mV->V).
    LOCAL temp
    temp = 2*GasConstant*1000(mV/volt)*(273(degC)+Temp)
    u = exp(z*Faraday*v/temp)
}
