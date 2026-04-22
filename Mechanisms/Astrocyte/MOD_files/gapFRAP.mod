COMMENT
================================================================================
gapFRAP.mod  --  Gap junction flux for FRAP tracer ion
================================================================================

Origin
------
Derived from ifrap.mod (2018).  Models the intercellular flux of a custom
fluorescent tracer ion ("frapion") through an astrocyte gap junction.

This mechanism is used to simulate FRAP (Fluorescence Recovery After
Photobleaching) experiments in coupled astrocyte networks.  After photobleaching
a region, the recovery of fluorescence is driven by diffusion of the tracer
through gap junctions from neighbouring unbleached cells.

Mechanism type
--------------
POINT_PROCESS: inserted at a specific location in a section (not distributed
over membrane area).  Suitable for a gap junction coupling two specific
compartments.

Physics
-------
The gap junction flux is modelled as a first-order diffusive exchange:

    J = (frapioni - gapFRAPP) / (BasicFRAP * TimeRelex)

where:
  frapioni  = tracer concentration in the local (postsynaptic) compartment  [mM]
  gapFRAPP  = tracer concentration in the coupled (presynaptic) compartment [mM]
              accessed via a POINTER set in HOC to frapioni in the partner cell
  BasicFRAP = reference concentration normalising the driving force            [mM]
  TimeRelex = relaxation time constant of the gap junction exchange            [ms]

The flux J has units [1/ms] and is multiplied by FARADAY to convert to a
transmembrane current density suitable for the USEION framework:

    ifrapion = J * FARADAY   [mA/cm2 equivalent for POINT_PROCESS]

Note: frapion is declared with VALENCE 1 (monovalent tracer), so the
conversion factor is 1*FARADAY, not 2*FARADAY (which would apply to Ca2+).

HOC setup required
------------------
Before running, in HOC/Python:
  1. Define the custom ion:  ion_style("frapion", ...)
  2. Set the initial tracer concentration in each compartment:
       section.frapioni = initial_value
  3. Connect the POINTER gapFRAPP of the GapFRAP object in cell A
     to frapioni in the coupled compartment of cell B:
       setpointer gapfrap_objref.gapFRAPP, coupled_section.frapioni(x)

Parameters to adjust
--------------------
  TimeRelex  : larger value = slower/weaker gap junction coupling
               (equivalent to lower permeability)
  BasicFRAP  : reference concentration; scales the sensitivity of the flux
               to the concentration difference

================================================================================
CHANGELOG
================================================================================
  04/01/2018  -- Initial version derived from ifrap.mod
  [current]   -- Dead variables removed; duplicate assignment removed;
                 FARADAY factor corrected (valence 1, not 2);
                 INITIAL block added; full commentary added;
                 indentation unified to 4-space.

ENDCOMMENT


: ==============================================================================
: NEURON block -- mechanism registration
: ==============================================================================

NEURON {
    : POINT_PROCESS: inserted at a discrete location, not spread over area.
    : Use for gap junctions coupling specific compartment pairs.
    POINT_PROCESS GapFRAP

    : Custom tracer ion "frapion" (monovalent, VALENCE 1).
    : frapioni : local tracer concentration (read -- drives flux)
    : ifrapion : resulting tracer current (write -- updates ion dynamics)
    : Requires ion_style("frapion",...) to be called in HOC before use.
    USEION frapion READ frapioni WRITE ifrapion VALENCE 1

    : Per-instance accessible variables
    RANGE TimeRelex  : gap junction relaxation time constant (ms)
    RANGE BasicFRAP  : reference concentration for flux normalisation (mM)
    RANGE fluxion    : intermediate flux normalisation term (mM*ms)
    RANGE ifrapion   : tracer current written to ion (see ASSIGNED)

    : gapFRAPP: POINTER to frapioni in the coupled (partner) compartment.
    : Must be set in HOC via setpointer before simulation begins.
    : Points to the tracer concentration on the other side of the gap junction.
    POINTER gapFRAPP

    : NOTE: the following RANGE variables from the original were removed
    : because they were declared but never defined or used anywhere:
    :   jd         -- undefined, never assigned
    :   ControlGap -- undefined, never assigned
    :   ifrap      -- duplicate of ifrapion concept, never assigned
}


: ==============================================================================
: UNITS
: ==============================================================================

UNITS {
    (molar) = (1/liter)
    (mM)    = (millimolar)
    (um)    = (micron)
    (mA)    = (milliamp)
    (nA)    = (nanoamp)
    FARADAY = (faraday)  (10000 coulomb)
    PI      = (pi)       (1)
}


: ==============================================================================
: PARAMETER block -- adjustable constants
: ==============================================================================

PARAMETER {
    : Relaxation time constant of gap junction exchange.
    : Larger value = slower coupling (lower effective permeability).
    : Units: ms.  Default: 10000 ms = 10 s (slow diffusive exchange).
    TimeRelex = 10000  (ms)

    : Reference concentration used to normalise the driving force.
    : The flux is proportional to (frapioni - gapFRAPP) / BasicFRAP.
    : Effectively sets the scale at which concentration differences become
    : significant for driving current.
    : Units: mM.  Default: 1 mM.
    BasicFRAP = 1  (mM)
}


: ==============================================================================
: ASSIGNED block -- computed variables and externally provided quantities
: ==============================================================================

ASSIGNED {
    : Local tracer concentration [mM].
    : Provided by the USEION frapion READ declaration.
    : Represents [frapion] in the compartment where this POINT_PROCESS is inserted.
    frapioni  (mM)

    : Tracer concentration in the coupled (partner) compartment [mM].
    : This is a POINTER -- must be connected via setpointer in HOC to
    : frapioni of the partner cell before simulation begins.
    : The concentration difference (frapioni - gapFRAPP) is the driving force.
    gapFRAPP  (mM)

    : Section diameter [um].
    : Available automatically in NEURON for POINT_PROCESS mechanisms.
    diam  (um)

    : Intermediate normalisation term for the flux calculation [mM*ms].
    : fluxion = BasicFRAP * TimeRelex
    : Dividing the concentration difference by fluxion gives a rate [1/ms].
    fluxion  (mM ms)

    : Tracer ion current [mA/cm2 equivalent].
    : Written to the frapion ion pool by USEION WRITE.
    : Positive value = outward current (tracer leaving the local compartment).
    : Negative value = inward current (tracer entering from coupled compartment).
    ifrapion

    : NOTE: 'iFRAPgap (nanoamp)' from the original was removed -- it was
    : declared but never assigned or used in any equation.
}


: ==============================================================================
: INITIAL -- set starting conditions
: ==============================================================================

INITIAL {
    : Compute the static normalisation term once at initialisation.
    : fluxion = BasicFRAP * TimeRelex
    : This term does not change during simulation (both parameters are constant),
    : so computing it here avoids redundant multiplication each timestep.
    fluxion = BasicFRAP * TimeRelex

    : Initialise the tracer current to zero.
    : The first BREAKPOINT call will set the correct value based on
    : the initial concentration difference across the gap junction.
    ifrapion = 0
}


: ==============================================================================
: BREAKPOINT -- evaluated every integration timestep
: ==============================================================================

BREAKPOINT {
    : Recompute fluxion each step to reflect any runtime changes to parameters.
    : (In practice BasicFRAP and TimeRelex are constant, but this allows
    :  HOC-level parameter sweeps without reinitialising the mechanism.)
    fluxion = BasicFRAP * TimeRelex

    : Gap junction tracer flux (first-order diffusive exchange):
    :
    :   ifrapion = [(frapioni - gapFRAPP) / fluxion] * FARADAY
    :
    : Term-by-term:
    :   (frapioni - gapFRAPP) : concentration gradient across gap junction [mM]
    :   / fluxion             : normalise by BasicFRAP*TimeRelex [mM*ms]
    :                           --> rate [1/ms]
    :   * FARADAY             : convert molar flux to electrical current [C/mol]
    :                           (factor 1 because frapion VALENCE = 1, monovalent)
    :
    : Sign convention: if local [frapion] > partner [frapion], flux is outward
    : (positive ifrapion), meaning tracer leaves this compartment.
    :
    : NOTE: original code used 2*FARADAY, which is correct only for divalent ions
    : (e.g. Ca2+).  frapion is declared VALENCE 1 so the correct factor is 1*FARADAY.
    ifrapion = ( (frapioni - gapFRAPP) / fluxion ) * FARADAY

    : NOTE: original code computed fluxion twice with identical expressions
    : (lines 41 and 43 of the original).  The duplicate has been removed.
}
