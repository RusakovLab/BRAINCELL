#!/usr/bin/env bash
# =============================================================================
# BrainCell container entrypoint
#
# Responsibilities (in order):
#   1. Clone (or update) the BrainCell repo at $BRAINCELL_DIR
#   2. Compile MOD files in EACH of the four BrainCell mechanism locations,
#      in place. This is NOT a merge -- Rule 4 of the BrainCell architecture
#      says mechanism compilation is distributed, so we preserve that.
#   3. Dispatch based on $BRAINCELL_MODE:
#         gui       -> launch the full BrainCell GUI (requires X11)
#         headless  -> run a user-provided script with Xvfb if needed
#         shell     -> drop into an interactive bash shell (default)
#         <custom>  -> exec the arguments passed to `docker run` verbatim
#
# The script never modifies init.hoc, JSON biophysics presets, or any manager
# file (Rules 1, 3, 5).
# =============================================================================
set -euo pipefail

# -- Helpers ------------------------------------------------------------------
log()  { printf '\033[1;34m[braincell]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[braincell]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[braincell]\033[0m %s\n' "$*" >&2; exit 1; }

# -----------------------------------------------------------------------------
# Step 1: obtain the BrainCell source
#
#   - If $BRAINCELL_DIR is already a git repo (e.g. user bind-mounted it),
#     we leave it alone. This lets developers iterate without re-cloning.
#   - Otherwise clone $BRAINCELL_REPO at $BRAINCELL_REF.
# -----------------------------------------------------------------------------
if [ -d "${BRAINCELL_DIR}/.git" ]; then
    log "BrainCell already present at ${BRAINCELL_DIR} (leaving it untouched)."
else
    log "Cloning ${BRAINCELL_REPO} (ref: ${BRAINCELL_REF}) into ${BRAINCELL_DIR}"
    git clone --depth 1 --branch "${BRAINCELL_REF}" \
        "${BRAINCELL_REPO}" "${BRAINCELL_DIR}" \
        || die "git clone failed"
fi

cd "${BRAINCELL_DIR}"

# -----------------------------------------------------------------------------
# Step 2: compile MOD files (distributed, per Rule 4)
#
#   On Windows the BrainCell repo ships four nrnmech.dll files at:
#       Mechanisms/Astrocyte/nrnmech.dll
#       Mechanisms/Neuron/nrnmech.dll
#       Nanogeometry/Astrocyte/nrnmech.dll
#       Nanogeometry/Neuron/nrnmech.dll
#
#   On Linux the equivalent is a `x86_64/` subdirectory containing libnrnmech.so,
#   produced by running `nrnivmodl` inside a directory with MOD files.
#
#   We compile each location independently, in place. We do NOT merge them.
#   We skip recompilation if the .so is newer than all .mod files in that dir.
# -----------------------------------------------------------------------------
compile_mech_dir() {
    local src_dir="$1"       # directory containing .mod files
    local build_root="$2"    # directory where `x86_64/` should appear

    if [ ! -d "${src_dir}" ]; then
        warn "Skipping ${src_dir} (not found in this checkout)"
        return 0
    fi

    local mod_count
    mod_count=$(find "${src_dir}" -maxdepth 1 -name '*.mod' 2>/dev/null | wc -l)
    if [ "${mod_count}" -eq 0 ]; then
        warn "Skipping ${src_dir} (no .mod files)"
        return 0
    fi

    local so_file="${build_root}/x86_64/libnrnmech.so"
    if [ -f "${so_file}" ]; then
        # Skip if .so is newer than every .mod in src_dir
        local newest_mod
        newest_mod=$(find "${src_dir}" -maxdepth 1 -name '*.mod' -printf '%T@\n' \
                     | sort -n | tail -1)
        local so_time
        so_time=$(stat -c '%Y' "${so_file}")
        if [ "${so_time%.*}" -gt "${newest_mod%.*}" ]; then
            log "Mechanisms up to date in ${build_root} (skipping)"
            return 0
        fi
    fi

    log "Compiling mechanisms in ${src_dir} -> ${build_root}/x86_64/"
    (
        cd "${build_root}"
        # Remove stale build
        rm -rf x86_64
        # nrnivmodl takes a directory of .mod files as argument
        nrnivmodl "$(realpath --relative-to="${build_root}" "${src_dir}")"
    ) || die "nrnivmodl failed in ${build_root}"
}

# BrainCell's four mechanism locations. Source MOD files live in MOD_files/,
# but the compiled output must sit in the parent dir (next to the .bat files
# that BrainCell's own init scripts expect to find nrnmech beside).
compile_mech_dir "Mechanisms/Astrocyte/MOD_files"   "Mechanisms/Astrocyte"
compile_mech_dir "Mechanisms/Neuron/MOD_files"      "Mechanisms/Neuron"

# Some BrainCell checkouts keep a Common MOD_files folder that is merged into
# each of the above at build time via the build_astrocyte_&_neuron_mechs scripts.
# We replicate that: compile Common into BOTH targets so the resulting libnrnmech.so
# is complete. This follows the Windows build script convention -- it is NOT
# a schema change.
if [ -d "Mechanisms/Common/MOD_files" ]; then
    log "Merging Mechanisms/Common/MOD_files into Astrocyte and Neuron builds"
    # Re-run each target with Common appended. We do this by staging a temp
    # directory that contains BOTH sets, then compiling from it.
    for target in Astrocyte Neuron; do
        stage="Mechanisms/${target}/_staged_mods"
        rm -rf "${stage}"
        mkdir -p "${stage}"
        cp "Mechanisms/${target}/MOD_files/"*.mod "${stage}/" 2>/dev/null || true
        cp "Mechanisms/Common/MOD_files/"*.mod    "${stage}/" 2>/dev/null || true
        (
            cd "Mechanisms/${target}"
            rm -rf x86_64
            nrnivmodl _staged_mods
        ) || die "nrnivmodl failed for ${target} (with Common merged in)"
        rm -rf "${stage}"
    done
fi

# Nanogeometry locations (may or may not exist depending on the checkout).
# These typically contain no MOD files of their own -- the nrnmech.dll shipped
# there on Windows is a copy. On Linux, BrainCell's init logic loads the .so
# from the Mechanisms/ folders, so we don't need to duplicate them.
# If a future checkout puts MOD files under Nanogeometry/, the function below
# will compile them in place.
compile_mech_dir "Nanogeometry/Astrocyte/MOD_files" "Nanogeometry/Astrocyte" 2>/dev/null || true
compile_mech_dir "Nanogeometry/Neuron/MOD_files"    "Nanogeometry/Neuron"    2>/dev/null || true

log "Mechanism compilation complete."

# -----------------------------------------------------------------------------
# Step 3: dispatch
# -----------------------------------------------------------------------------

# If the user passed any command, just run it. This is the "power user" path.
if [ "$#" -gt 0 ]; then
    log "Executing user command: $*"
    exec "$@"
fi

case "${BRAINCELL_MODE}" in
    gui)
        # Requires DISPLAY to be set and /tmp/.X11-unix bind-mounted.
        if [ -z "${DISPLAY:-}" ]; then
            die "BRAINCELL_MODE=gui requires the DISPLAY env var and X11 socket.
    Run with:  docker run -e DISPLAY=\$DISPLAY \\
                          -v /tmp/.X11-unix:/tmp/.X11-unix \\
                          ..."
        fi
        log "Launching BrainCell GUI via init.hoc"
        # BrainCell's own init.hoc expects to be loaded from the repo root.
        # We use nrniv (not nrngui) because init.hoc itself loads nrngui.hoc.
        exec nrniv init.hoc
        ;;

    headless)
        # Headless batch mode. If the user's script tries to open GUI widgets
        # anyway (Rule 7 -- GUI and engine are intertwined), we transparently
        # provide an Xvfb virtual display so it won't crash.
        log "Starting Xvfb on :99 for headless mode"
        Xvfb :99 -screen 0 1024x768x24 >/dev/null 2>&1 &
        export DISPLAY=:99
        sleep 1

        if [ -z "${BRAINCELL_SCRIPT:-}" ]; then
            die "BRAINCELL_MODE=headless requires \$BRAINCELL_SCRIPT (path to a .py or .hoc file)"
        fi
        if [ ! -f "${BRAINCELL_SCRIPT}" ]; then
            die "Script not found: ${BRAINCELL_SCRIPT}"
        fi

        case "${BRAINCELL_SCRIPT}" in
            *.py)   log "Running Python script: ${BRAINCELL_SCRIPT}"
                    exec python "${BRAINCELL_SCRIPT}" ;;
            *.hoc)  log "Running HOC script: ${BRAINCELL_SCRIPT}"
                    exec nrniv "${BRAINCELL_SCRIPT}" ;;
            *)      die "Unknown script type (expected .py or .hoc): ${BRAINCELL_SCRIPT}" ;;
        esac
        ;;

    shell|"")
        log "Dropping into interactive shell. BrainCell is at ${BRAINCELL_DIR}."
        log "Useful commands:"
        log "    nrniv init.hoc                   # launch GUI (needs DISPLAY)"
        log "    python your_sim.py               # headless python sim"
        log "    mpirun -n 4 nrniv -mpi your.hoc  # MPI simulation"
        exec /bin/bash
        ;;

    *)
        die "Unknown BRAINCELL_MODE='${BRAINCELL_MODE}' (expected: gui|headless|shell)"
        ;;
esac
