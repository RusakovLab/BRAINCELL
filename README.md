# BRAINCELL

[![License: BSD 3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Version](https://img.shields.io/badge/version-2026.03-brightgreen.svg)](#)
[![Built on NEURON](https://img.shields.io/badge/built%20on-NEURON-8A2BE2.svg)](#)
[![Platform](https://img.shields.io/badge/GUI-Windows%2010%2F11-lightgrey.svg)](#platform-support)

BrainCell is a NEURON-based platform for modelling neurons, astrocytes and
extracellular dynamics at nanoscale resolution. It combines NEURON (HOC and
MOD) with a Python export framework, JSON biophysics presets and a
manager-driven architecture, and it provides a GUI-driven workflow that takes
a model from geometry (imported reconstructions or procedurally seeded
nano-morphology), through biophysics presets and simulation, to an exported,
self-contained HOC and MOD package that runs anywhere NEURON runs.

## Platform support

| Component | Windows 10/11 | macOS | Linux |
|---|---|---|---|
| Graphical environment (Main UI, Managers) | Supported | In development | In development |
| Mechanism compilation (bundled build scripts) | Supported | Manual (nrnivmodl) | Manual (nrnivmodl) |
| Morphology import (NLMorphologyConverter) | Supported | Planned | Not available |
| Model export (HOC + MOD package) | Supported | - | - |
| Running an exported model | Supported | Supported | Supported |
| NSG / cluster submission | Supported | Supported | Supported |

The BrainCell graphical environment currently runs on Windows 10/11. Models
exported from BrainCell are platform-independent: the generated HOC and MOD
package compiles and runs unchanged on macOS, Linux and HPC clusters,
including the Neuroscience Gateway. Support for the graphical environment on
macOS and Linux is under active development.

## Requirements

- Windows 10 or 11 (64-bit) for the graphical environment
- NEURON 8.2.x (tested with 8.2.2, mingw build)
- Python 3.11 (tested with Anaconda3 2023.09-0, which ships Python 3.11.5)
- 4 GB RAM minimum, 8 GB recommended; about 5 GB of free disk space

Python packages used at run time are listed in `requirements.txt`. Anaconda
2023.09-0 already provides all of them except `plotly` in some builds.

## Installation

Full instructions, including the three installation categories and
troubleshooting, are in `BRAINCELL_Instalation.docx` (also part of
`BRAINCELL_User_Guide.docx`). In short:

1. Install Anaconda 2023.09-0 for the current user only ("Just Me").
   Download it from the official Anaconda archive:
   https://repo.anaconda.com/archive/Anaconda3-2023.09-0-Windows-x86_64.exe
   (all versions: https://repo.anaconda.com/archive/ ).
   SHA256: `810da8bff79c10a708b7af9e8f21e6bb47467261a31741240f27bd807f155cb9`
   Do not use third-party mirrors.
2. Install NEURON 8.2.2 (64-bit, mingw build) and restart Windows.
3. Clone or unpack this repository into a short path, for example
   `C:\braincell`.
4. Compile the mechanisms only if you added or changed MOD files: run
   `build_mechs.bat` in the repository root.

## Quick start

1. Double-click `init.bat` in the repository root (or run `nrngui init.hoc`
   from a Command Prompt opened there).
2. Choose Astrocyte or Neuron mode in the BrainCell main window.
3. Load a demo: `Examples/01_CA1_SingleNeuron/Run.bat` builds and runs a
   single CA1 neuron; `Examples/02_init_InsideOutDiffManager/Run.bat` runs the
   inside-out diffusion demo.
4. Use the Managers (MechManager, BioManager, SynManager, ExportManager) to
   apply a biophysics preset and export a runnable model package.

## Citation

If you use BrainCell in published work, please cite the platform paper and the
ModelDB entry:

```
Savtchenko, L. P., et al. BrainCell: a simulation platform for nanoscale
neuron-astrocyte-extracellular modelling. Nature Communications,
<in press>, <in press>. doi:<in press>

ModelDB accession 243508. https://modeldb.science/243508
```

A `CITATION.cff` file in this repository carries the same metadata in machine
-readable form. The volume, page range and DOI will be completed on
publication.

## Licence

BrainCell's own source code is distributed under the BSD-3-Clause licence; see
`LICENSE` for the full text. The repository additionally contains third-party
binaries, vendored source and reference models that carry their own separate
licences - including one component that is licensed for non-commercial use
only - so read `THIRD_PARTY_NOTICES.md` before redistributing BrainCell or
using it commercially.

## Contact and issues

- Bug reports and feature requests: https://github.com/RusakovLab/BRAINCELL/issues
- Community forum and installation support: https://forum.neuroalgebra.net
- BrainCell is developed by the Rusakov Lab, UCL Queen Square Institute of
  Neurology.

## Architecture at a glance

Contributors should respect these layer boundaries (see `CLAUDE.md` and
`AGENTS.md` for the full contribution rules):

- Geometry (classic and nano) - morphologies with or without seeded nano-structures
- Biophysics - JSON presets under `Biophysics/Astrocyte/` and `Biophysics/Neuron/`
- Mechanisms - MOD files split into `Astrocyte/`, `Neuron/` and `Common/` trees
- Managers - `BioManager`, `SynManager`, `GapJuncManager`, `InhomManager`,
  `StochManager`, `ExportManager`
- Simulation layer - ready-to-run scenarios under `_Code/Simulations/`
- Extracellular engines - inside-out and outside-in diffusion calculators
- Export framework - marker-driven (`@meta`, `py:`) generators and skeletons
- Reduced inhomogeneous / stochastic system - segmentation and variable mapping
- GUI widgets - interleaved with the engine, not separable today
- Testing entry points - `_Testing/init_*.hoc`, for development only
