# BrainCell Cluster Deployer

A small Tkinter GUI that helps a BrainCell user set up the container on
**their own** remote Linux machine (lab server, HPC cluster, cloud VM)
without having to remember SSH commands or `docker build` syntax.

It does **not** host BrainCell or run simulations itself. It just:

1. Opens an SSH connection to the user's machine.
2. Detects whether Docker or Singularity/Apptainer is available there.
3. Uploads the `Dockerfile` + entrypoint.
4. Runs the right command sequence to build (Docker) or pull (Singularity)
   the image.
5. Prints the exact one-liner the user should run to launch BrainCell.

## Quick start

```bash
# Install the one dependency
pip install paramiko

# Run the panel
python braincell_panel.py
```

A window opens with two tabs:

- **1. Connect** — enter your cluster's host/IP, username, and either a
  password or an SSH key file. Click **Connect + Detect**.
- **2. Deploy BrainCell** — point at the local folder containing the
  `Dockerfile` and `docker-entrypoint.sh` (both already written in a prior
  step of this project). Click **Deploy BrainCell**.

Everything streams into the log pane at the bottom in real time, so you
can watch the build progress or diagnose failures.

## File layout

```
braincell-panel/
├── braincell_panel.py     <-- the Tkinter GUI (entry point)
├── cluster_session.py     <-- SSH + detection + deployment logic
├── dockerfiles/
│   ├── Dockerfile         <-- from the earlier BrainCell Docker design
│   └── docker-entrypoint.sh
└── README.md
```

The `dockerfiles/` folder should contain the exact same `Dockerfile` and
entrypoint script we built earlier. The panel is agnostic about their
contents — it just uploads them verbatim.

## What it detects on the remote host

After connecting, the tool runs a short probe script that reports:

- Linux kernel version and distribution (for the log only)
- Whether `docker` is installed and on the PATH
- Whether `singularity` or `apptainer` is installed
- Whether SLURM (`sbatch`) is available

The tool then picks a runtime:

- **Both present:** prefers Singularity (the HPC-friendly choice).
- **Only Docker:** uses Docker directly.
- **Only Singularity:** uses Singularity (requires the image to be on a
  public Docker Hub registry — see below).
- **Neither:** displays a clear error and does not attempt the deploy.

## Honest limitations

These are real and worth understanding before you distribute the tool:

**1. Password auth often won't work on real HPC clusters.** Most academic
clusters disable SSH password login for security. The panel supports SSH
keys as an alternative — prefer that path.

**2. Singularity needs the image in a public registry.** To pull without
root, the panel runs `singularity pull docker://<image>`. That means
**you** must have pushed the BrainCell image to Docker Hub (or another
public registry) first. Edit `cluster_session.py` — the constant
`registry_image` in `_deploy_with_singularity` — to point at your real
image location.

If you haven't pushed an image yet, the panel will display a clean error
telling the user to contact the BrainCell maintainer.

**3. No MFA / no Kerberos / no jumphost support (yet).** Many real HPC
clusters require an OTP on top of SSH auth, or force connections through
a bastion host. Paramiko supports these, but the GUI doesn't expose them.
If your users need these, that's the first feature to add.

**4. Building Docker on the remote requires permission.** Most shared
Linux servers don't let arbitrary users run `docker build` — the user
must be in the `docker` group. The panel detects this case and shows the
error, but it cannot fix it.

**5. HPC compute nodes often have no internet access.** If the user's
cluster isolates compute nodes from the outside world, the `singularity
pull` step (which downloads from Docker Hub) will fail there. It
typically works from the **login** node — which is fine, since the panel
connects to wherever you tell it to.

**6. Credentials live only in memory.** The panel never writes passwords
or keys to disk. They are lost the moment the window closes. This is by
design.

## Developer notes

- `cluster_session.py` has zero Tkinter imports and can be driven from a
  script or test harness.
- `braincell_panel.py` runs all SSH work on a background thread and pipes
  output to the GUI via a thread-safe queue. The log pane updates every
  100 ms from the main event loop.
- To add a new remote capability (e.g. Podman), extend
  `ClusterCapabilities` and add a `_deploy_with_podman` branch in
  `ClusterSession.deploy_braincell`.
- The tool does not persist any state. To add "remember last host", wire
  up a small JSON file in `~/.braincell/panel.json`.
