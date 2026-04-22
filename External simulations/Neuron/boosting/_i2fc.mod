
COMMENT
    
    i to flux converter
    
    This helper membrane mechanism is used in Python as following:
        node.include_flux(segm._ref_kflux_i2fc)
        
    NEURON RxD docs:
        https://nrn.readthedocs.io/en/latest/python/modelspec/programmatic/rxd.html#rxd.node.Node.include_flux
        
    Notice that the next command would be wrong:
        node.include_flux(segm._ref_ik)
        
    Derivation of "kflux" as a function of "ik":
    
    kflux =
        = [molecule] / [ms] =
        = charge[Coulomb] / valence / elemCharge[Coulomb] / [ms] =
        = 1e-3 * charge[mCoulomb] / valence / elemCharge[Coulomb] / 1e3[s] =
        = 1e-6 * charge[mCoulomb] / [s] / valence / elemCharge[Coulomb] =
        = 1e-6 * current[mA] / valence / elemCharge[Coulomb] =
        = 1e-6 * ik[mA/cm2] * segmArea[cm2] / valence / elemCharge[Coulomb] =
        = 1e-6 * ik[mA/cm2] * 1e-8 * segmArea[um2] / valence / elemCharge[Coulomb] =
        = 1e-14 * ik[mA/cm2] * segmArea[um2] / valence / 1.602176634e-19[Coulomb] = 
        = 62415.09074[1/Coulomb] * ik[mA/cm2] * segmArea[um2] / valence =
        = factor[1/Coulomb] * ik[mA/cm2] * segmArea[um2] / valence
    
ENDCOMMENT


: !! BUG: NEURON's units checker "modlunit" finds a problem in this MOD file


: !! TODO: Try to get rid of this MOD file as well as the calls of "node.include_flux" in favour of "rxd.Rate" and "rxd.Parameter" (still on the learning curve)


NEURON {
    SUFFIX i2fc
    USEION k READ ik
    RANGE segmArea, kflux
    GLOBAL valence, factor
}

UNITS {
    (mA) = (milliamp)
    (um) = (micron)
    (molecule) = (1)
}

PARAMETER {
    segmArea (um2)
    valence (1)
}

ASSIGNED {
    ik (mA/cm2)
    
    : This flux will be passed directly to the RxD method "node.include_flux"
    kflux (molecule/ms)
    
    factor (1/coulomb)
}

VERBATIM
    // Defined in "_InsideOutDiffHelper.mod"
    void codeContractViolation();
ENDVERBATIM

INITIAL {
    
    if (valence == 0) {
        codeContractViolation()
    }
    
    factor = 62415.09074
    
    kflux = getFlux()
}

BREAKPOINT {
    kflux = getFlux()
}

FUNCTION getFlux() {
    
    getFlux = factor * ik * segmArea / valence
    
    : !! printf("kflux: %g (molecule/ms)\n", getFlux)
}
