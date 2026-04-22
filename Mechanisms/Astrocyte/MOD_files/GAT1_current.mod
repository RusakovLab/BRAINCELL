NEURON {
	SUFFIX GAT1_current
	GLOBAL Temperature
	 USEION gaba READ gabai, gabao WRITE igaba VALENCE 0
	RANGE  Egat, conductance
	NONSPECIFIC_CURRENT iGAT	:add to local membrane current but not affecting particular ion conc.
	: Na+ and Cl- read live from ion pools each timestep.
	: READ only -- electrogenic charge already in iGAT (NONSPECIFIC).
	USEION na READ nai, nao
	USEION cl READ cli, clo
	}

UNITS {
	(mV) = (millivolt)
	(mA) = (milliamp)
	(mM) = (milli/liter)
	(mS) = (millisiemens)
	(mol) = (/liter)
	(mol-3) = (/liter3)
}

PARAMETER {	:define numbers & units of variables
	GasConstant=8.314 (joule/mol)
	Temperature=298
	Faraday=96487 (coulomb/mol)
	conductance=0.1 (mS/cm2)
	: Nai, Nao, Cli, Clo removed -- now read live from na_ion / cl_ion pools.
	: Set initial values in HOC/Python before simulation:
	:   seg.nai0_na_ion = 1    (mM)
	:   seg.nao0_na_ion = 140  (mM)
	:   seg.cli0_cl_ion = 1    (mM)
	:   seg.clo0_cl_ion = 144  (mM)
}

ASSIGNED {	:define units only; values will be calculated
	v (mV)
	iGAT (mA/cm2)
	Egat (mV)
	: Na+ and Cl- ion variables -- filled by NEURON from ion pools each step
	nai (mM)
	nao (mM)
	cli (mM)
	clo (mM)
	    : GABA ion variables (set by NEURON from gaba_ion pool each step)
    gabai  (mM)            : intracellular [GABA] -- read from ion pool
    gabao  (mM)            : extracellular [GABA] -- read from ion pool
	    : Outputs
    igaba        (mol/cm2/ms) : molar GABA flux -- written to gaba_ion pool
}

BREAKPOINT {
	Egat = (GasConstant*1000(mV/volt)*Temperature/Faraday)*log((nao/nai)^2*(gabao/gabai)*(cli/clo))
	iGAT = (0.001)*conductance*(v-Egat)
	igaba=iGAT
}
	