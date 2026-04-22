NEURON {
	POINT_PROCESS Gap43	
	RANGE GVal, g, i, vgap, Ginf, Gtau
	GLOBAL Nj, g_main, GMax
	NONSPECIFIC_CURRENT i
	THREADSAFE : assigned GLOBALs will be per thread
}

STATE { G }

PARAMETER {
	Nj = 1000
	g_main = 61 (picosiemens)
	GMax (picosiemens)
}

INITIAL {
	GMax = (((61-14.6460)/(1+exp((0-61.41)/8.405)))+14.6460)+(((61-14.6460)/(1+exp((-0-61.41)/8.405)))+14.6460)-61
	rates(0)
	G = Ginf
}

ASSIGNED {
	v (millivolt)
	vgap (millivolt)	
	GVal (picosiemens)	
	g (nanosiemens) 
	i (nanoamp)
	Ginf	
	Gtau (ms)	
}

BREAKPOINT {
	SOLVE states METHOD cnexp	
	g = G * g_main * Nj / 1000
	i = (v-vgap)*g / 1000
}

DERIVATIVE states {  
	rates(v-vgap)
	G' = (Ginf-G)/Gtau
}

PROCEDURE rates(Vj(mV))  {
	GVal = (((61-14.6460)/(1+exp((Vj-61.41)/8.405)))+14.6460)+(((61-14.6460)/(1+exp((-Vj-61.41)/8.405)))+14.6460)-61
	Ginf = GVal/61
	Gtau = (1.942*exp(-((fabs(Vj)-40.83)/33.21)^2))*1000	:milliseconds
}
