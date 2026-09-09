# Third-Party Notices

BrainCell is distributed under the BSD-3-Clause licence (see LICENSE). That
licence applies to the BrainCell source code authored by the Rusakov Lab.
This repository also includes or depends on third-party components that are
licensed separately by their respective owners, as listed below.

## Redistributed components

### NLMorphologyConverter

- Location in this repository: `_Code/Import/3rdParty/NLMorphologyConverter/NLMorphologyConverter.exe`
  (with `NLMorphologyConverter_UserManual_0_10_0.pdf` and `readme.txt` in the same folder)
- Origin / upstream: http://neuronland.org/NLMorphologyConverter/NLMorphologyConverter.html
- Version: 0.10.0.dev, 10 January 2016
- Licence: Neuronland proprietary licence, non-commercial use only. Free copying
  and redistribution are permitted provided the distributed files are not
  modified in any way and all copyright and licence information is retained.
  The upstream licence text is reproduced verbatim in
  `_Code/Import/3rdParty/NLMorphologyConverter/readme.txt`.
- Notes: Windows 32-bit binary; requires the Microsoft Visual C++ 2010
  Redistributable (x86). The upstream project appears to be unmaintained.
  This licence is more restrictive than BSD-3-Clause: it does not permit
  commercial use. Downstream users who need a commercially usable distribution
  must obtain this component separately or omit it. The wrapper scripts in the
  same folder (`nlmc_swc.py`, `convert_hoc_to_swc.bat`) are BrainCell code and
  are covered by LICENSE.

### ModelDB reference model - Watanabe et al. 2002 (dendritic K+ channels)

- Location in this repository: `External simulations/Neuron/boosting/`
- Origin / upstream: ModelDB, accompanying S. Watanabe, D. A. Hoffman,
  M. Migliore and D. Johnston, "Dendritic K+ channels contribute to
  spike-timing dependent long-term potentiation in hippocampal pyramidal
  neurons", Proc. Natl. Acad. Sci. USA 99:8366-8371, 2002.
  https://modeldb.science/
- Licence: to be confirmed. No licence file accompanies the downloaded model;
  ModelDB entries are published under the terms chosen by their authors.
  Contact michele.migliore@pa.ibf.cnr.it (the address given in the model's
  own `readme.txt`) before redistributing.
- Notes: MOD files by M. Migliore and colleagues (`kadist.mod`, `kaprox.mod`,
  `kdrca1.mod`, `na3.mod`, `nax.mod`, `h.mod`, `nethhwbm.mod`, `netstimm.mod`
  and others), plus `cadifus.mod` derived from Hines and Carnevale, "The
  NEURON Book", chapter 9. The folder also contains a prebuilt `nrnmech.dll`.
  Some MOD files in this folder are BrainCell mechanisms (those prefixed with
  an underscore) and are covered by LICENSE.

### ModelDB reference model - Spoleti et al. 2021 (ventral CA1 in Alzheimer's disease)

- Location in this repository: `External simulations/Neuron/modeldb_ventralAD/`
- Origin / upstream: ModelDB, accompanying E. Spoleti, P. Krashia,
  L. La Barbera, A. Nobili, C. A. Lupascu, E. Giacalone, F. Keller,
  M. Migliore, M. Renzi and M. D'Amelio, "Early derailment of firing
  properties in CA1 pyramidal cells of the ventral hippocampus in an
  Alzheimer's disease mouse model", Experimental Neurology 350:113969, 2021.
  https://doi.org/10.1016/j.expneurol.2021.113969
- Licence: to be confirmed. No licence file accompanies the downloaded model.
- Notes: MOD files, HOC files and a prebuilt `nrnmech.dll`. `README.htm` in
  that folder is the original ModelDB readme and is retained unmodified.

### Reference morphologies

- Location in this repository: `Geometry/Zoo/`, `Geometry/Neuron/Somogyi_Viney.zip`,
  and other reconstruction files under `Geometry/`
- Origin / upstream, as recorded in `Geometry/Zoo/README.txt`:
  https://neuromorpho.org/ ,
  https://github.com/NeuroMorpho/xyz2swc/tree/main/input/to_convert ,
  https://github.com/openworm/CElegansNeuroML/tree/master/CElegans/generatedMorphML
- Licence: to be confirmed per file. NeuroMorpho.org reconstructions remain
  the property of their contributing laboratories and carry per-archive terms;
  the OpenWorm CElegansNeuroML repository is MIT-licensed.
- Notes: These are test and demonstration data, not code. Each file should be
  attributed to its original laboratory before publication.

## Vendored source code

### hoc2swc

- Location: `_Code/Import/ImportExtraCells/PythonCode/Separated/ThirdParty/hoc2swc.py`
- Origin: https://github.com/JustasB/hoc2swc (source as of the last commit of
  20 July 2020)
- Licence: MIT (Copyright (c) 2019). The full MIT text is reproduced in
  `_Code/Import/ImportExtraCells/PythonCode/Separated/ThirdParty/readme.txt`,
  in the same folder as the source file.
- Modifications: yes. The file was adapted for BrainCell, as recorded in the
  accompanying `readme.txt`. The MIT permission notice is retained in that
  `readme.txt` rather than as a header comment inside `hoc2swc.py`.

## Runtime dependencies (not redistributed)

Installed separately by the user; listed for information only.

| Package | Licence | Used for |
|---|---|---|
| numpy | BSD-3-Clause | Arrays and numerics throughout the Python layer |
| scipy | BSD-3-Clause | Interpolation and spatial queries (gap junction seeding, 3D plotting) |
| matplotlib | PSF-based (matplotlib licence) | Pyplot 2D and 3D range-variable animation players |
| numba | BSD-2-Clause | CPU and CUDA backends of the inside-out diffusion calculator |
| plotly | MIT | Plotly 2D and 3D animation front-ends |
| pandas | BSD-3-Clause | Frame assembly for the Plotly 3D player |
| cupy | MIT | Optional GPU arrays (LFP calculator, XpuUtils); not required |
| paramiko | LGPL-2.1-or-later | SSH transport used only by the optional cluster panel in `Docker/` |
| anthropic | MIT | Optional AI assistant scripts (`braincell_agent.py`, `braincell_panel.py`) |
| tkinter | PSF (part of CPython) | File dialogs and GUI wrappers |

Anaconda is recommended as the Python distribution. Anaconda installers are
not redistributed with BrainCell; the documentation links to the official
Anaconda archive at https://repo.anaconda.com/archive/ .

## Simulation environment

NEURON is developed by Yale University and Duke University and is required to
run BrainCell. It is not redistributed as part of this repository. NEURON
itself is distributed under the BSD-3-Clause licence
(https://github.com/neuronsimulator/nrn).

The compiled mechanism libraries checked into this repository
(`nrnmech.dll` under `Mechanisms/`, `Nanogeometry/` and
`External simulations/`) are build products of NEURON's `nrnivmodl`/`mknrndll`
applied to the MOD files in this repository and to the third-party MOD files
listed above. They therefore link NEURON runtime code and inherit the licence
of the MOD sources they were built from.
