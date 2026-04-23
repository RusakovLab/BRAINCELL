# BrainCell Docker image

A single container image that runs BrainCell in two ways:

* **GUI mode** — the NEURON InterViews UI appears on your desktop (local dev).
* **Headless mode** — batch simulations, no display, ideal for clusters.

Pinned versions (validated by the lab):

| Component | Version    |
| --------- | ---------- |
| Anaconda  | 2023.09-0  |
| NEURON    | 8.2.2      |
| Base OS   | Ubuntu 22.04 |
| MPI       | OpenMPI (system) |

BrainCell itself is **cloned from GitHub at container start**, so the image stays
small and users always get a fresh checkout.

---

## 1. Build the image

From the folder that contains the `Dockerfile`:

```bash
docker build -t braincell:8.2.2 .
```

This is a one-off ~5 min build (Anaconda is ~1 GB to download). The resulting
image is about 5-6 GB.

---

## 2. Run it

### 2a. Interactive shell (default)

```bash
docker run --rm -it \
    -v "$(pwd)/results:/workspace/results" \
    braincell:8.2.2
```

You land in `/workspace` with BrainCell cloned and compiled at `/workspace/BrainCell`.
All four mechanism folders have been compiled in place (see Rule 4 in the
project policy), preserving the distributed `nrnmech` layout.

Inside the container:

```bash
cd BrainCell
nrniv init.hoc                        # GUI (needs DISPLAY — see below)
python your_script.py                 # headless Python sim
mpirun -n 4 nrniv -mpi your_mpi.hoc   # parallel sim
```

### 2b. GUI mode

**Linux host:**

```bash
xhost +local:docker              # allow the container to talk to your X server
docker run --rm -it \
    -e BRAINCELL_MODE=gui \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v "$(pwd)/results:/workspace/results" \
    braincell:8.2.2
```

**macOS host:** install [XQuartz](https://www.xquartz.org/). In XQuartz preferences,
enable "Allow connections from network clients", then:

```bash
xhost +localhost
docker run --rm -it \
    -e BRAINCELL_MODE=gui \
    -e DISPLAY=host.docker.internal:0 \
    -v "$(pwd)/results:/workspace/results" \
    braincell:8.2.2
```

**Windows host:** install [VcXsrv](https://sourceforge.net/projects/vcxsrv/) or
Xming. Launch XLaunch with "Disable access control" checked, then (in PowerShell):

```powershell
docker run --rm -it `
    -e BRAINCELL_MODE=gui `
    -e DISPLAY=host.docker.internal:0 `
    -v ${PWD}/results:/workspace/results `
    braincell:8.2.2
```

### 2c. Headless batch mode

Put your run script somewhere the container can see it (either inside the
cloned repo, or in a bind-mounted folder), then:

```bash
docker run --rm \
    -e BRAINCELL_MODE=headless \
    -e BRAINCELL_SCRIPT=/workspace/BrainCell/_Testing/example_headless.py \
    -v "$(pwd)/results:/workspace/results" \
    braincell:8.2.2
```

A virtual X server (Xvfb) is started automatically, so scripts that accidentally
import GUI symbols won't crash. **However**, per Rule 7 of the project policy
("GUI and engine are intertwined"), the headless script itself must avoid calls
that pop up actual interactive widgets. A minimal headless template:

```python
# example_headless.py
from neuron import h
h.load_file("stdrun.hoc")
# load the mechanism DLL that was compiled at container start:
h.nrn_load_dll("/workspace/BrainCell/Mechanisms/Neuron/x86_64/libnrnmech.so")
# ... build geometry, apply biophysics JSON preset via BioManager,
#     then run the simulation. Results go to /workspace/results.
```

### 2d. Parallel (MPI) runs

```bash
docker run --rm \
    -v "$(pwd)/results:/workspace/results" \
    braincell:8.2.2 \
    mpirun --allow-run-as-root -n 4 nrniv -mpi \
        /workspace/BrainCell/_Testing/example_mpi.hoc
```

The `--allow-run-as-root` flag is needed because Docker processes run as root
by default; on a cluster under Singularity this flag is unnecessary and should
be removed.

---

## 3. Using docker-compose

If you prefer a shorter command line, `docker-compose.yml` predefines three
services:

```bash
docker compose run --rm braincell-shell      # interactive
docker compose run --rm braincell-gui        # GUI
BRAINCELL_SCRIPT=/workspace/BrainCell/_Testing/my_sim.py \
    docker compose run --rm braincell-headless
```

---

## 4. Running on an HPC cluster (Singularity / Apptainer)

Most academic clusters don't run Docker — they run Singularity (now called
Apptainer), which can import Docker images directly.

**Option A: pull from a registry** (after you push the image to Docker Hub):

```bash
# on the cluster login node:
singularity pull braincell.sif docker://your-dockerhub-user/braincell:8.2.2
```

**Option B: export locally, copy to the cluster:**

```bash
# on your workstation:
docker save braincell:8.2.2 -o braincell.tar
scp braincell.tar cluster:~/
# on the cluster:
singularity build braincell.sif docker-archive://braincell.tar
```

**Running under Singularity** (headless, MPI):

```bash
singularity exec braincell.sif \
    bash -c "cd /workspace && /usr/local/bin/docker-entrypoint.sh \
             mpirun -n $SLURM_NTASKS nrniv -mpi /workspace/BrainCell/_Testing/my_sim.hoc"
```

A sample SLURM script:

```bash
#!/bin/bash
#SBATCH --job-name=braincell
#SBATCH --ntasks=16
#SBATCH --time=04:00:00
#SBATCH --output=braincell_%j.log

module load singularity   # or apptainer -- check your cluster
srun singularity exec \
    --bind $HOME/braincell_results:/workspace/results \
    braincell.sif \
    /usr/local/bin/docker-entrypoint.sh \
    mpirun -n $SLURM_NTASKS nrniv -mpi /workspace/BrainCell/_Testing/my_sim.hoc
```

**Singularity quirks to know about:**

* Singularity mounts your `$HOME` and runs as *your* user, not root. The
  entrypoint is written to tolerate that — nothing writes to `/root/` or
  `/opt/` at runtime.
* `/workspace` is writable inside the image and gets overlaid per run, so
  the clone-and-compile step still works.
* If cold-start compile time is a problem, build once with BrainCell baked
  in (see Section 6 below) and rebuild the image when MOD files change.

---

## 5. Pinning a specific BrainCell version

By default the container clones the `main` branch at startup. To freeze to a
tag or commit:

```bash
docker run --rm -it \
    -e BRAINCELL_REF=v1.4.0 \
    braincell:8.2.2
```

or to point at a fork:

```bash
docker run --rm -it \
    -e BRAINCELL_REPO=https://github.com/someone/BrainCell-fork.git \
    -e BRAINCELL_REF=feature-branch \
    braincell:8.2.2
```

---

## 6. Iterating on a local checkout (developers)

If you're modifying BrainCell and don't want to commit + re-clone every run,
bind-mount your local checkout over `/workspace/BrainCell`:

```bash
docker run --rm -it \
    -v /home/me/code/BrainCell:/workspace/BrainCell \
    -v "$(pwd)/results:/workspace/results" \
    braincell:8.2.2
```

The entrypoint detects the existing `.git` and skips the clone, but still
recompiles mechanisms when `.mod` files are newer than the existing `.so`.

---

## 7. Where outputs go

Everything simulation-level should be written under `/workspace/results`. Bind
a host folder there (`-v ./results:/workspace/results`) so results survive
after the container exits.

The container does **not** touch `init.hoc`, biophysics JSON files, manager
files, or any `@meta` / `py:` export markers. Any persistent change you want
to make to the repo must be a git commit in a normal checkout.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `cannot connect to X server` | DISPLAY or `/tmp/.X11-unix` not forwarded | See Section 2b. On Linux try `xhost +local:docker`. |
| `nrnivmodl: command not found` | Container didn't build right | `docker build --no-cache -t braincell:8.2.2 .` |
| `libnrnmech.so: cannot open shared object` | Mechanism compile was skipped or failed | Check entrypoint log; remove `x86_64/` and rerun. |
| `mpirun detected that your launcher is root` | You're running Docker as root | Add `--allow-run-as-root` (dev only) or switch to Singularity. |
| Clone fails behind a firewall | Cluster node has no outbound HTTPS | Bind-mount a pre-cloned repo (Section 6). |

---

## 9. What this image intentionally does NOT do

Per the BrainCell project policy:

* It does **not** modify `init.hoc` or any file in `_Code/Managers/`.
* It does **not** rename JSON keys or change biophysics schema.
* It does **not** merge `Mechanisms/Astrocyte/` and `Mechanisms/Neuron/` into
  a single `nrnmech` — they remain separate per Rule 4.
* It does **not** flatten the repo directory structure.
* It does **not** strip `@meta` / `py:` export markers.
* It does **not** assume the testing entrypoints under `_Testing/` are a stable
  public API.

Scope is deliberately narrow: provide a reproducible Linux runtime for
BrainCell, nothing more.
