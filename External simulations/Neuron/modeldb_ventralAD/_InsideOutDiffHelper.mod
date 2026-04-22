
COMMENT
    Inside-Out Diffusion Helper (membrane mechanism)
    
    Its job is to read "i{species}", then calculate and write "{species}o". Not used when user chooses "neuron.rxd" as the diffusion module.
    
    If you want to add new species (or delete old ones), look for 5 blocks of code below marked as "Edit here when changing the species list"
    Warning: Any changes to the blocks must be done synchronously with the changes to two other files:
             * the file "Mechanisms\Settings\diffusible_species.json"
             * the file "Mechanisms\Common\MOD_files\_OutsideInDiffHelper.mod"
             The lists of species in the two MOD files and the JSON file must always be in sync (including the total number of species, their order and "ionMechName").
ENDCOMMENT

: !! BUGs:
:   1. if the membrane current doesn't stop, then we add the concentration infinitely, however, the correct behaviour would be to increase it until reaching saturation due to the inflow-outflow balance
:   2. in contrast to RxD module, the concentration is not accumulated around the soma and has more or less uniform distribution throughout the cell
:   3. when we turn off the membrane current, the concentration doesn't start relaxing to the base value "spcOinit"
:
:   to fix them all, it's enough to uncomment the line "~ species_ext << (-...)" in KINETIC block,
:   but, unfortunately, this leads to significant numerical instability when we decrease "Layer"

: !! questions:
:   1. do we need to use "{species}_ion\GLOBAL\{species}i0_{species}_ion" somewhere in this file?
:   2. do we really need to make "ispecies" ASSIGNED or just LOCAL would be enough?

NEURON {
    SUFFIX InsideOutDiffHelper
    
    : Warning: Be cautious specifying VALENCE below because it's easy to introduce a regression that will mainfest itself
    :          sometimes as a clear error message in NEURON (best case), but sometimes as a hanging of NEURON without any error messages (worst case) *
    :
    :          To do everything right, make sure that:
    :          1. Each ion has VALENCE specified in this file or some other MOD file. The only three ions for which NEURON already "knows" the valence are:
    :             Na+, K+ and Ca2+ (even though the last one is not "visible" to NEURON without a custom MOD file).
    :             You don't need to specify the valence for these three ions explicitly, but for all other ions specifying VALENCE somewhere is a must.
    :          2. The valence of a given ion doesn't have different values in different MOD files.
    :             If an ion used in 2+ MOD files, it's OK to specify VALENCE in only one MOD file and omit it in all other files.
    :
    :          * The hanging takes place when NEURON tries to load "nrnmech.dll" automatically from the current folder at start
    :            (e.g. when you export with "Export manager" and then run the exported HOC file in the standalone mode).
    :            The clear error message is printed when the DLL is loaded from a custom folder with "proc nrn_load_dll" (which corresponds to the common BrainCell workflow).
    :
    : Be aware: If an ion has no VALENCE specified anywhere, then no error in BrainCell program, but silent hanging in the exported file.
    
    : vvvvvvvvvv Edit here when changing the species list vvvvvvvvvv
    : Basic ions
    USEION na READ ina WRITE nao
    USEION k READ ik WRITE ko
    USEION ca READ ica WRITE cao
    USEION cl READ icl WRITE clo VALENCE -1
    : Neurotransmitters
    USEION ach READ iach WRITE acho VALENCE 1
    USEION glu READ iglu WRITE gluo
    USEION gaba READ igaba WRITE gabao VALENCE 0
    : Specific
    USEION frapion READ ifrapion WRITE frapiono
    USEION ip3 READ iip3 WRITE ip3o
    : User-defined
    USEION extra1 READ iextra1 WRITE extra1o VALENCE 1
    USEION extra2 READ iextra2 WRITE extra2o VALENCE -1
    : ^^^^^^^^^^ Edit here when changing the species list ^^^^^^^^^^
    
    GLOBAL spcIdx, spcValence, spcOinit, spcDiff
    
    : !! warning: don't declare the "Layer" and "N" params as "RANGE" here; otherwise, they would appear in the "KINETIC" block with the value of "-1"
}

UNITS {
    (mM)    = (milli/liter)
    (um)    = (micron)
    (mA)    = (milliamp)
    FARADAY = (faraday) (10000 coulomb)
    PI      = (pi) (1)
}

PARAMETER {
    : The next 5 params will be set from GeneralSettingsWidget and InsideOutDiffManagerMainWidget before the first use
    
    Layer = -1 (um)         : Thickness of the near-membrane layer
    N = -1                  : How much the 2nd layer is thicker than the 1st one
    
    spcIdx = -1             : Flat index of the species
    spcValence = -1         : Valence; will be initialized with ion_charge("{species}_ion") or explicitly specified by user
    spcOinit = -1 (mM)      : Initial concentration; will be copied from "{species}_ion\GLOBAL\{species}o0_{species}_ion"
    spcDiff = -1 (um2/ms)   : Diffusion coefficient
}

ASSIGNED {
    diam (um)               : Diameter of this segment
    radius (um)             : Radius of this segment (!! making it ASSIGNED rather than LOCAL just to calm down the units checker)
    
    vol_specieso (um2)          : Per-length volume of the near-membrane layer
    vol_species_ext (um2)       : Per-length volume of the external space
    diff_area_specieso (um2)    : Diffusion area for near-membrane layer
    diff_area_species_ext (um2) : Diffusion area for external space
    
    ispecies (mA/cm2)       : Current density
    
    : vvvvvvvvvv Edit here when changing the species list vvvvvvvvvv
    : Basic ions
    ina (mA/cm2)        nao (mM)
    ik (mA/cm2)         ko (mM)
    ica (mA/cm2)        cao (mM)
    icl (mA/cm2)        clo (mM)
    : Neurotransmitters
    iach (mA/cm2)       acho (mM)
    iglu (mA/cm2)       gluo (mM)
    igaba (mA/cm2)      gabao (mM)
    : Specific
    ifrapion (mA/cm2)   frapiono (mM)
    iip3 (mA/cm2)       ip3o (mM)
    : User-defined
    iextra1 (mA/cm2)    extra1o (mM)
    iextra2 (mA/cm2)    extra2o (mM)
    : ^^^^^^^^^^ Edit here when changing the species list ^^^^^^^^^^
}

STATE {
    specieso (mM)       : Concentration in the near-membrane layer
    species_ext (mM)    : Concentration in the external space
}

: !! compiler warning here: VERBATIM blocks are not thread safe
VERBATIM
    // vvvvvvvvvv Edit here when changing the species list vvvvvvvvvv
    #define NUM_SPECIES_IN_MOD 11
    // ^^^^^^^^^^ Edit here when changing the species list ^^^^^^^^^^
    
    static double *ptr_vec_i[NUM_SPECIES_IN_MOD];
    static double *ptr_vec_o[NUM_SPECIES_IN_MOD];
    
    void codeContractViolation() {
        hoc_execerror("\n\n    Bug in BrainCell program: Code contract violation", "\n    Please report this problem to the developer along with the call stack shown below\n");
    }
    
ENDVERBATIM

: Called from HOC
FUNCTION getNumSpeciesInMOD() {
    VERBATIM
        _lgetNumSpeciesInMOD = NUM_SPECIES_IN_MOD;
    ENDVERBATIM
}

INITIAL {
    
    if (spcValence == 0) {
        codeContractViolation()
    }
    
    specieso = spcOinit     : Initialize concentration in the near-membrane layer
    species_ext = spcOinit  : Initialize concentration in the external space
    
    radius = diam / 2
    diff_area_specieso    = PI * ((radius +       Layer)^2 - (radius)^2)
    diff_area_species_ext = PI * ((radius + (1+N)*Layer)^2 - (radius + Layer)^2)
    
    : Per-length volumes
    vol_specieso          = diff_area_specieso
    vol_species_ext       = diff_area_species_ext
    
    assignPointers()
    
    writeOutConc()
}

BREAKPOINT {
    : !! that's strange that we have to call this now even though it was called in INITIAL (see the comments in "_OutsideInDiffHelper.mod")
    assignPointers()
    
    SOLVE conc METHOD sparse
    
    writeOutConc()
}

KINETIC conc {
    
    : !! warning: don't move this VERBATIM block inside BREAKPOINT because this will result in a "memory" between two "Init & Run"-s
    VERBATIM
        ispecies = *ptr_vec_i[(int)spcIdx];
    ENDVERBATIM
    
    : Define the compartment volumes for diffusion (NEURON uses per-length volumes)
    COMPARTMENT vol_specieso    {specieso}
    COMPARTMENT vol_species_ext {species_ext}
    
    : Define the longitudinal diffusion terms
    LONGITUDINAL_DIFFUSION spcDiff * diff_area_specieso    {specieso}
    LONGITUDINAL_DIFFUSION spcDiff * diff_area_species_ext {species_ext}
    
    : Flux between the cell and the 1st external layer due to the membrane current density
    ~ specieso << ((ispecies * (radius + Layer) * PI) / FARADAY / spcValence)
    
    : Diffusion exchange between the two external layers
    ~ specieso <-> species_ext (spcDiff, spcDiff)
    
    : Flux in the 2nd external layer due to the leak to/from the infinite space
    : ~ species_ext << (-(species_ext - spcOinit) * spcDiff)
    
    : !! the block below is just a workaround to prevent the next error while translating this MOD file to C code:
    :    "{species}o is WRITE but is not a STATE and has no assignment statement"
    
    : vvvvvvvvvv Edit here when changing the species list vvvvvvvvvv
    : Basic ions
    nao = nao
    ko = ko
    cao = cao
    clo = clo
    : Neurotransmitters
    acho = acho
    gluo = gluo
    gabao = gabao
    : Specific
    frapiono = frapiono
    ip3o = ip3o
    : User-defined
    extra1o = extra1o
    extra2o = extra2o
    : ^^^^^^^^^^ Edit here when changing the species list ^^^^^^^^^^
}

PROCEDURE assignPointers() {
    
    VERBATIM
        // !! why do I need to assign the next pointers on each breakpoint?
        //    (they behave like shared between the segments - need to look into C code)
        //    UPD 1: VERBATIM block is not allowed inside NEURON, PARAMETER or ASSIGNED,
        //           so cannot move the declarations of the pointers there
        //    UPD 2: if I declare 2 vars with the same name in different MOD files, compiler gives an error
        
        // !! maybe I can call some HOC code here to do this in order to be more flexible with regard to adding/deleting species
        
        // vvvvvvvvvv Edit here when changing the species list vvvvvvvvvv
        // Basic ions
        ptr_vec_i[0] = &ina;        ptr_vec_o[0] = &nao;
        ptr_vec_i[1] = &ik;         ptr_vec_o[1] = &ko;
        ptr_vec_i[2] = &ica;        ptr_vec_o[2] = &cao;
        ptr_vec_i[3] = &icl;        ptr_vec_o[3] = &clo;
        // Neurotransmitters
        ptr_vec_i[4] = &iach;       ptr_vec_o[4] = &acho;
        ptr_vec_i[5] = &iglu;       ptr_vec_o[5] = &gluo;
        ptr_vec_i[6] = &igaba;      ptr_vec_o[6] = &gabao;
        // Specific
        ptr_vec_i[7] = &ifrapion;   ptr_vec_o[7] = &frapiono;
        ptr_vec_i[8] = &iip3;       ptr_vec_o[8] = &ip3o;
        // User-defined
        ptr_vec_i[9] = &iextra1;    ptr_vec_o[9] = &extra1o;
        ptr_vec_i[10] = &iextra2;   ptr_vec_o[10] = &extra2o;
        // ^^^^^^^^^^ Edit here when changing the species list ^^^^^^^^^^
        
        /* !!
        // Make sure HOC and MOD code is synced with regard to the species list
        // !! move this check to the beginning of this PROCEDURE (before we start writing to "ptr_vec_i[*]");
        //    alternatively, expose NUM_SPECIES_IN_MOD here, read it in HOC and do this check on the HOC side (because earlier is better)
        if (numSpeciesInHOC != NUM_SPECIES_IN_MOD) {
            codeContractViolation();    // !! replace with a message saying that the MOD files list and this MOD file are out of sync and how to fix this problem
        }
        */
    ENDVERBATIM
    
}

PROCEDURE writeOutConc() {
    
    VERBATIM
        *ptr_vec_o[(int)spcIdx] = specieso;
    ENDVERBATIM
    
}
