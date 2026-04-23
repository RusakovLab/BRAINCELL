# =============================================================================
# BrainCell Docker image
#   - Base:       Ubuntu 22.04
#   - Python:     Anaconda 2023.09-0 (ships Python 3.11)
#   - NEURON:     8.2.2 (pip wheel, MPI-enabled via system OpenMPI)
#   - MPI:        OpenMPI (system package, used by both NEURON and mpi4py)
#   - Source:     BrainCell is cloned from GitHub at container *start* (entrypoint),
#                 NOT at build time. Keeps the image small and always up to date.
#   - Modes:      Both GUI (X11 forwarding) and headless (batch / cluster) supported
#                 from the SAME image. Mode is chosen by the user at `docker run` time.
#
# BrainCell architectural rules respected (see project policy):
#   - Rule 1 (init order):         entrypoint never modifies init.hoc; it only cd's
#                                  into the repo root and delegates.
#   - Rule 4 (distributed mechs):  we compile EACH of the four MOD_files dirs
#                                  separately, in-place, so the resulting libnrnmech.so
#                                  sits next to its source files (the BrainCell
#                                  convention: one nrnmech per mechanism folder).
#   - Rule 7 (GUI intertwined):    we don't try to force headless; we only provide a
#                                  display (Xvfb) when the user opts into batch mode.
#                                  The user's run script controls whether GUI widgets
#                                  are invoked.
# =============================================================================

FROM ubuntu:22.04

# -- Avoid interactive apt prompts during build -------------------------------
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Etc/UTC

# -----------------------------------------------------------------------------
# 1. System packages
#
#    Split into three groups so the reasoning is explicit:
#      (a) build toolchain     -> required by `nrnivmodl` to compile MOD files
#      (b) MPI stack           -> OpenMPI for parallel NEURON (`nrniv -mpi`)
#      (c) GUI / X11 support   -> InterViews (NEURON's GUI toolkit) needs X11
#                                 libs even when running headless with Xvfb
# -----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    # (a) Build toolchain
    build-essential \
    cmake \
    bison \
    flex \
    ca-certificates \
    wget \
    git \
    # (b) MPI
    libopenmpi-dev \
    openmpi-bin \
    # (c) GUI / X11 (needed by NEURON InterViews, even when headless via Xvfb)
    libx11-6 \
    libxt-6 \
    libxext6 \
    libxcomposite1 \
    libxrender1 \
    libxtst6 \
    libxrandr2 \
    libxi6 \
    libglu1-mesa \
    xvfb \
    x11-apps \
    xauth \
    # Misc runtime
    ncurses-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# 2. Anaconda 2023.09-0  (provides Python 3.11, numpy, matplotlib, scipy, ...)
#
#    Pinned version as specified by the project: this is the Anaconda release
#    against which BrainCell has been validated.
#    We install to /opt/anaconda3 and make it the default Python.
# -----------------------------------------------------------------------------
ENV ANACONDA_VERSION=2023.09-0 \
    CONDA_DIR=/opt/anaconda3

RUN wget -q https://repo.anaconda.com/archive/Anaconda3-${ANACONDA_VERSION}-Linux-x86_64.sh \
        -O /tmp/anaconda.sh \
 && bash /tmp/anaconda.sh -b -p ${CONDA_DIR} \
 && rm /tmp/anaconda.sh \
 && ${CONDA_DIR}/bin/conda clean -afy

ENV PATH=${CONDA_DIR}/bin:${PATH}

# -----------------------------------------------------------------------------
# 3. NEURON 8.2.2  (+ mpi4py)
#
#    Installed via pip into the Anaconda base environment. The wheel is built
#    against Python 3.11 and picks up the system OpenMPI we installed above.
#    We do NOT install `neuron-gpu` -- it was removed after 8.2.2 and pins a
#    specific NVIDIA HPC SDK, which is out of scope here.
# -----------------------------------------------------------------------------
RUN pip install --no-cache-dir \
        neuron==8.2.2 \
        mpi4py

# Sanity check: import works and MPI is discoverable
RUN python -c "import neuron; print('NEURON', neuron.__version__)" \
 && which mpirun \
 && which nrnivmodl

# -----------------------------------------------------------------------------
# 4. Working directory and entrypoint
#
#    /workspace is where BrainCell will be cloned at container start.
#    We deliberately do NOT clone at build time -- the entrypoint handles it
#    so users always get the latest code (or can pin a tag/commit).
#
#    /workspace/results is the canonical location for simulation outputs;
#    users should bind-mount a host directory here to persist results.
# -----------------------------------------------------------------------------
WORKDIR /workspace
RUN mkdir -p /workspace/results

# Copy the entrypoint script (clone + compile + dispatch)
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Default env vars -- overridable with `docker run -e ...`
ENV BRAINCELL_REPO=https://github.com/RusakovLab/BrainCell.git \
    BRAINCELL_REF=main \
    BRAINCELL_DIR=/workspace/BrainCell \
    BRAINCELL_MODE=shell

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD []
