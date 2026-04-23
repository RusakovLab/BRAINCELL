# BRAINCELL

> **An immersive modeling platform for computational neuroscience and neurology — focused on cell and tissue physiology, stochastic nano-morphology, and experimental-design replication.**

[![License: BSD 3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Version](https://img.shields.io/badge/version-2026.03-brightgreen.svg)](#)
[![Built on NEURON](https://img.shields.io/badge/built%20on-NEURON-8A2BE2.svg)](#)
[![Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#installation)

---

BRAINCELL is developed by the **Savtchenko / Rusakov Lab (UCL)** as a structured simulation environment that combines the numerical rigor of NEURON (HOC + MOD) with a Python-driven export framework, JSON biophysics presets, and a manager-based architecture. It lets experimentalists and theorists model neurons, astrocytes, and surrounding tissue with nano-scale geometric precision — and reproduce in silico the conditions of the bench.

---

## Key Features

- **Stochastic nano-morphology generation** — procedurally seed spines, processes, and fine nano-structures on imported cell skeletons, producing statistically realistic ultrastructure rather than smoothed cylinders.
- **Stop-save-go simulation control** — pause long-running simulations, save full state to disk, and resume later (or on a different machine) without loss of fidelity. Essential for parameter sweeps and interactive exploration.
- **Adaptive morphology import** — ingest a wide range of reconstruction formats (SWC, ASC, HOC, NRX, XML, ESWC, IMS, and more) and adaptively refine segmentation for biophysically meaningful compartmentalization.
- **Dynamic extracellular interactions** — coupled inside-out / outside-in ion diffusion engines for realistic tissue-scale ionic dynamics (K⁺ buffering, glutamate spillover, Ca²⁺ waves).
- **Manager-driven architecture** — `BioManager`, `SynManager`, `GapJuncManager`, `InhomManager`, `StochManager`, and `ExportManager` provide clean separation of biophysics, synapses, gap junctions, inhomogeneity, stochasticity, and export.
- **JSON biophysics presets** — version-controllable, reproducible configurations for astrocyte and neuron models.
- **Ready-to-run simulations** — including `SimMyelinatedAxon`, calcium dynamics, FRAP, calcium waves, glutamate dynamics, and voltage distributions.

---

## Installation

> [!IMPORTANT]
> **Forum registration is required.** Downloads and the setup password are distributed through the Neuroalgebra Forum. Please register at **[forum.neuroalgebra.net](https://forum.neuroalgebra.net)** before attempting installation.

### System Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 4 GB | 8 GB or more |
| Disk space | 5 GB | 10 GB (for saved simulation states) |
| Python | 3.10+ (Anaconda suggested) | 3.11 via Anaconda |
| NEURON | 8.x | 8.2 or newer |
| Graphics | Any OpenGL-capable GPU | Discrete GPU for nano-geometry rendering |

### Platform-Specific Installation

| Platform | Method | Notes |
|---|---|---|
| **Windows** | All-in-One Installer (`.exe`) | Recommended path. Bundles NEURON, compiled mechanisms (`nrnmech.dll`), and BRAINCELL. Run as administrator. |
| **macOS** | Source build + NEURON wheel | Install NEURON via `pip install neuron`, then clone the repository. Compile MOD files with `nrnivmodl` in each `Mechanisms/*/MOD_files` directory. Apple Silicon is supported. |
| **Linux** | Source build + system NEURON | Install NEURON from your distribution or via `pip`. Compile mechanisms with `nrnivmodl`. Works on Ubuntu 22.04+, Debian 12+, and Fedora 38+. |

> [!WARNING]
> **Password required during setup.** The All-in-One Installer and source archives are protected. Obtain the current password from the **[Neuroalgebra Forum](https://forum.neuroalgebra.net)** after registration.

### Post-installation check

After installation, launch the main entry point. You should see the BRAINCELL GUI load with the Main UI panel, geometry selectors, and manager buttons (MechManager, GapJuncManager, SynManager, ExportManager).

---

## Usage & AI Agents

BRAINCELL ships with two companion AI assistants that help new users navigate the codebase and run simulations.

- **Setup & Installation AI Guide** — step-by-step walk-through of Anaconda, API keys, the `anthropic` package, file placement, and first-run diagnostics. See `BrainCell_Agent_Setup_Manual.html` in the repository root.
- **End-User AI Manual** — how to ask questions about MOD files, KINETIC schemes, biophysics, architecture, and request code modifications. See `BrainCell_Agent_User_Manual.html`.

The agents themselves are provided as two Python scripts in the repository root:

| Script | Purpose |
|---|---|
| `braincell_mapper.py` | Indexes all MOD, HOC, and Python files into `braincell_map.json`. Run once after installation and again whenever files are added. |
| `braincell_agent.py` | Interactive AI assistant that answers questions about the codebase and proposes changes. Also available as a GUI via `braincell_panel.py`. |

> [!NOTE]
> The AI agents use the Anthropic API and require an API key. Running cost is typically **$5–20 / month** for active research use.

---

## Resources

| Resource | Link |
|---|---|
| Community Forum | [forum.neuroalgebra.net](https://forum.neuroalgebra.net) |
| Documentation PDFs | Available through the Forum downloads area |
| GitHub repository | *To be published — see Forum for current link* |
| NEURON simulator | [neuron.yale.edu](https://neuron.yale.edu) |

---

## Architecture at a Glance

BRAINCELL is organized into clearly separated layers. Contributors should respect these boundaries:

- **Geometry** (classic + nano) — cell morphologies, with or without procedural nano-structures
- **Biophysics** — JSON presets under `Biophysics/Astrocyte/` and `Biophysics/Neuron/`
- **Mechanisms** — MOD files, split into `Astrocyte/`, `Neuron/`, and `Common/` trees
- **Managers** — `BioManager`, `SynManager`, `GapJuncManager`, `InhomManager`, `StochManager`, `ExportManager`
- **Simulation layer** — ready-to-run scenarios in `_Code/Simulations/`
- **Extracellular engines** — inside-out and outside-in diffusion calculators
- **Export framework** — marker-driven (`@meta`, `py:`) Python generators and skeleton templates
- **Reduced Inhomogeneous / Stochastic system** — segmentation, distribution, and variable mapping
- **GUI widgets** — Tk-based control panels, interleaved with the engine
- **Testing entry points** — `_Testing/init_*.hoc` for development

---

## License

BRAINCELL is distributed under the **3-clause BSD license**. See `LICENSE` for the full text.

---

## Citing BRAINCELL

If you use BRAINCELL in published research, please cite the platform and the Savtchenko / Rusakov Lab. Canonical citation details are available on the Forum.
