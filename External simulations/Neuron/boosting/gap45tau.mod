NEURON {
	POINT_PROCESS Gap45	
	RANGE GVal, g, i, vgap, Ginf, Gtau
	GLOBAL Nj, g_main, GMax
	NONSPECIFIC_CURRENT i
	THREADSAFE : assigned GLOBALs will be per thread
}

STATE { G }

PARAMETER {
	Nj = 1000
	g_main = 32 (picosiemens)
	GMax (picosiemens)
}

INITIAL {
	GMax = (((32-4.2393)/(1+exp((0-39.55)/10.24)))+4.2393)+(((32-4.2393)/(1+exp((-0-39.55)/10.24)))+4.2393)-32
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
	GVal = (((32-4.2393)/(1+exp((Vj-39.55)/10.24)))+4.2393)+(((32-4.2393)/(1+exp((-Vj-39.55)/10.24)))+4.2393)-32
	Ginf = GVal/32
	Gtau = (5.652*exp(-((fabs(Vj)-15.63)/28.05)^2))*1000	:milliseconds
}
