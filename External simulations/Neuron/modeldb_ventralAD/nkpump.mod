TITLE sodium potassium pump
:  from Lindblad et al Am J Physiol 1996 275:H1666

NEURON {
	SUFFIX NaKpump
	USEION k READ ko WRITE ik
	USEION na READ nai WRITE ina
	RANGE ik, ina , INaKmax, ink, Kmko, Kmnai, ki0, nao0
	GLOBAL dummy : prevent vectorization for use with CVODE
}

UNITS {
	(mA) = (milliamp)
	(mV) = (millivolt)
	
}

PARAMETER {
	INaKmax = 0.06       (mA/cm2) <0,1e6>
	Kmnai =    10          (mM)    <0,1e6>
	Kmko =      2.5         (mM)    <0,1e6>
	ki0 = 130
	nao0 = 145
}

ASSIGNED {
	celsius (degC)
	v (mV)
	ik (mA/cm2)
	ina (mA/cm2)
	ko (mM)
    ki (mM)
	nao (mM)
	nai (mM)
	ink (mA/cm2)
	dummy
}

INITIAL {
    ki = ki0
	nao = nao0
}

BREAKPOINT { LOCAL q10 , fnk 
	
		q10 = 3^((celsius - 37)/10 (degC))
	
	fnk = (v + 150)/(v + 200)
	
			
	ink= q10*INaKmax*fnk/((1 + (Kmnai/nai)^1.5)*(1 + Kmko/ko))
	ina = 3*ink
	ik = -2*ink
}






