NEURON {
	POINT_PROCESS Gap40	
	RANGE GVal, g, i, vgap, Ginf, Gtau
	GLOBAL Nj, g_main, GMax
	NONSPECIFIC_CURRENT i
	THREADSAFE : assigned GLOBALs will be per thread
}

STATE { G }

PARAMETER {
	Nj = 1000
	g_main = 162 (picosiemens)
	GMax (picosiemens)
}

INITIAL {
	GMax = (((162-23.6384)/(1+exp((0-57.74 )/13.42)))+23.6384)+(((162-23.6384)/(1+exp((-0-57.74 )/13.42)))+23.6384)-162
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
	GVal = (((162-23.6384)/(1+exp((Vj-57.74 )/13.42)))+23.6384)+(((162-23.6384)/(1+exp((-Vj-57.74 )/13.42)))+23.6384)-162	
	Ginf = GVal/162
	Gtau = (1.942*exp(-((fabs(Vj)-40.83)/33.21)^2))*1000	:milliseconds
}
