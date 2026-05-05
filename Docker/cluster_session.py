"""
cluster_session.py

SSH connection and cluster capability detection for the BrainCell deployment
panel. Decoupled from the GUI so it can be tested on its own.

Responsibilities:
    * Connect to a remote machine over SSH (password or key-file auth).
    * Detect what's available there: Docker? Singularity? Neither?
    * Run commands and stream stdout/stderr back to a callback (the GUI uses
      this to populate its live log).
    * Transfer the Dockerfile + entrypoint to the remote host.
    * Orchestrate a simple "build or pull, then run" workflow for BrainCell.

Architectural notes:
    * Nothing in this module imports tkinter -- the GUI layer lives separately.
    * The log callback is a plain callable `log(text: str)`; the caller decides
      whether that writes to a file, stdout, or a Tk widget.
    * All long-running operations are blocking. The GUI is responsible for
      running them on a background thread to keep the UI responsive.
"""

from __future__ import annotations

import io
import posixpath
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

try:
    import paramiko
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency 'paramiko'. Install it with:\n"
        "    pip install paramiko"
    ) from exc


# Log callback signature: a function that accepts a line of text.
LogFn = Callable[[str], None]


def _noop_log(_msg: str) -> None:
    pass


@dataclass
class ClusterCapabilities:
    """What the remote machine can actually do."""
    has_docker: bool = False
    has_singularity: bool = False       # covers both `singularity` and `apptainer`
    singularity_cmd: str = ""           # the binary name to use ("singularity" or "apptainer")
    has_slurm: bool = False
    kernel: str = ""
    distro: str = ""

    @property
    def recommended_runtime(self) -> str:
        """Which runtime should we use on this host?"""
        if self.has_singularity:
            return "singularity"        # preferred on HPC even if Docker also exists
        if self.has_docker:
            return "docker"
        return "none"


@dataclass
class SSHConfig:
    """Everything needed to open an SSH connection."""
    host: str
    port: int = 22
    username: str = ""
    password: str = ""                   # empty if using key auth
    key_filename: str = ""               # empty if using password auth
    # Timeout for each command (seconds). Builds can be slow, so this is generous.
    command_timeout: int = 3600


class ClusterSession:
    """
    A live SSH session to the user's cluster.

    Typical lifecycle:
        session = ClusterSession(cfg, log=print)
        session.connect()
        caps = session.detect_capabilities()
        session.deploy_braincell(...)
        session.close()

    The `log` callback receives every line of stdout/stderr from remote
    commands, plus high-level progress messages from this class.
    """

    # Remote working directory. We intentionally use $HOME-relative paths so
    # this works on HPC clusters where /opt or /tmp may be read-only or purged.
    REMOTE_WORKDIR = "braincell_docker"

    def __init__(self, cfg: SSHConfig, log: Optional[LogFn] = None) -> None:
        self.cfg = cfg
        self.log: LogFn = log or _noop_log
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
        self._lock = threading.Lock()    # serialize command execution

    # ----- connection lifecycle ------------------------------------------------

    def connect(self) -> None:
        """Open the SSH connection. Raises on failure."""
        self.log(f"Connecting to {self.cfg.username}@{self.cfg.host}:{self.cfg.port} ...")

        client = paramiko.SSHClient()
        # AutoAddPolicy: accept unknown host keys. This is a usability choice;
        # a stricter tool would prompt the user. For a scientific helper tool
        # used against the user's own cluster, AutoAdd is the standard trade-off.
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs = {
            "hostname": self.cfg.host,
            "port": self.cfg.port,
            "username": self.cfg.username,
            "timeout": 15,
            "allow_agent": False,
            "look_for_keys": False,
        }
        if self.cfg.key_filename:
            kwargs["key_filename"] = self.cfg.key_filename
            self.log(f"  Using key file: {self.cfg.key_filename}")
        elif self.cfg.password:
            kwargs["password"] = self.cfg.password
            self.log("  Using password authentication")
        else:
            raise ValueError("No password and no key file provided")

        client.connect(**kwargs)
        self._client = client
        self._sftp = client.open_sftp()
        self.log("  Connected.")

    def close(self) -> None:
        """Close SFTP + SSH. Safe to call multiple times."""
        if self._sftp is not None:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self.log("Connection closed.")

    @property
    def connected(self) -> bool:
        if self._client is None:
            return False
        transport = self._client.get_transport()
        return transport is not None and transport.is_active()

    # ----- command execution ---------------------------------------------------

    def run(self, command: str, check: bool = False) -> tuple[int, str, str]:
        """
        Run a command on the remote host. Stream stdout/stderr to the log
        callback line-by-line; return (exit_code, full_stdout, full_stderr).

        If `check` is True, raise RuntimeError on non-zero exit.
        """
        if not self.connected:
            raise RuntimeError("Not connected")

        # Use a lock so concurrent GUI buttons don't interleave commands.
        with self._lock:
            self.log(f"$ {command}")
            assert self._client is not None
            _stdin, stdout, stderr = self._client.exec_command(
                command, timeout=self.cfg.command_timeout, get_pty=False
            )

            out_buf = io.StringIO()
            err_buf = io.StringIO()

            # Stream line-by-line. paramiko's channel exposes stdout and stderr
            # as separate file-like objects; we read from whichever has data.
            channel = stdout.channel
            stdout_done = False
            stderr_done = False
            while not (stdout_done and stderr_done):
                if channel.recv_ready():
                    chunk = channel.recv(4096).decode("utf-8", errors="replace")
                    out_buf.write(chunk)
                    for line in chunk.splitlines():
                        self.log(line)
                if channel.recv_stderr_ready():
                    chunk = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                    err_buf.write(chunk)
                    for line in chunk.splitlines():
                        self.log(f"[stderr] {line}")
                if channel.exit_status_ready():
                    # Drain any remaining data
                    while channel.recv_ready():
                        chunk = channel.recv(4096).decode("utf-8", errors="replace")
                        out_buf.write(chunk)
                        for line in chunk.splitlines():
                            self.log(line)
                    while channel.recv_stderr_ready():
                        chunk = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                        err_buf.write(chunk)
                        for line in chunk.splitlines():
                            self.log(f"[stderr] {line}")
                    stdout_done = True
                    stderr_done = True

            exit_code = channel.recv_exit_status()
            self.log(f"  (exit code: {exit_code})")

        if check and exit_code != 0:
            raise RuntimeError(
                f"Command failed (exit {exit_code}): {command}\n{err_buf.getvalue()}"
            )
        return exit_code, out_buf.getvalue(), err_buf.getvalue()

    # ----- capability detection ------------------------------------------------

    def detect_capabilities(self) -> ClusterCapabilities:
        """
        Figure out what we can do on this cluster. This drives every later
        decision (which Dockerfile variant to use, which commands to run).
        """
        self.log("Detecting cluster capabilities ...")
        caps = ClusterCapabilities()

        # Kernel + distro -- useful for the log and for later error messages.
        _, out, _ = self.run("uname -sr")
        caps.kernel = out.strip()
        _, out, _ = self.run(
            "cat /etc/os-release 2>/dev/null | grep ^PRETTY_NAME= | cut -d= -f2"
        )
        caps.distro = out.strip().strip('"')

        # Docker
        code, _, _ = self.run("command -v docker >/dev/null 2>&1 && docker --version")
        caps.has_docker = (code == 0)

        # Singularity (modern: apptainer; older: singularity). Try both.
        for binary in ("apptainer", "singularity"):
            code, _, _ = self.run(
                f"command -v {binary} >/dev/null 2>&1 && {binary} --version"
            )
            if code == 0:
                caps.has_singularity = True
                caps.singularity_cmd = binary
                break

        # SLURM -- not required, but nice to know
        code, _, _ = self.run("command -v sbatch >/dev/null 2>&1")
        caps.has_slurm = (code == 0)

        self.log("")
        self.log(f"Detection result:")
        self.log(f"  Kernel:      {caps.kernel}")
        self.log(f"  Distro:      {caps.distro}")
        self.log(f"  Docker:      {'yes' if caps.has_docker else 'no'}")
        self.log(
            f"  Singularity: "
            f"{'yes (' + caps.singularity_cmd + ')' if caps.has_singularity else 'no'}"
        )
        self.log(f"  SLURM:       {'yes' if caps.has_slurm else 'no'}")
        self.log(f"  Recommended runtime: {caps.recommended_runtime}")

        return caps

    # ----- file transfer -------------------------------------------------------

    def ensure_remote_dir(self, path: str) -> None:
        """mkdir -p on the remote."""
        self.run(f"mkdir -p {path}", check=True)

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """SFTP a single file to the remote host."""
        assert self._sftp is not None
        self.log(f"Uploading {local_path}  ->  {remote_path}")
        self._sftp.put(local_path, remote_path)

    def upload_string(self, content: str, remote_path: str) -> None:
        """Write a string to a remote file (useful for small config files)."""
        assert self._sftp is not None
        self.log(f"Writing  ->  {remote_path}")
        with self._sftp.open(remote_path, "w") as fh:
            fh.write(content)

    # ----- the deployment itself -----------------------------------------------

    def deploy_braincell(
        self,
        caps: ClusterCapabilities,
        local_dockerfile_dir: str,
        image_tag: str = "braincell:8.2.2",
    ) -> None:
        """
        End-to-end: make the BrainCell container available on the remote host.
        Behaviour depends on what capabilities the host has.
        """
        if caps.recommended_runtime == "none":
            raise RuntimeError(
                "Neither Docker nor Singularity is available on this host.\n"
                "Please ask your cluster administrator which one is installed,\n"
                "or try connecting to a different node."
            )

        # 1. Make the remote workdir and upload the Dockerfile bundle
        remote_dir = posixpath.join(".", self.REMOTE_WORKDIR)
        self.ensure_remote_dir(remote_dir)

        files_to_upload = ["Dockerfile", "docker-entrypoint.sh"]
        for fname in files_to_upload:
            local = posixpath.join(local_dockerfile_dir, fname)
            remote = posixpath.join(remote_dir, fname)
            self.upload_file(local, remote)

        # Make the entrypoint executable on the remote side
        self.run(f"chmod +x {posixpath.join(remote_dir, 'docker-entrypoint.sh')}")

        # 2. Branch on runtime
        if caps.recommended_runtime == "docker":
            self._deploy_with_docker(remote_dir, image_tag)
        elif caps.recommended_runtime == "singularity":
            self._deploy_with_singularity(caps, remote_dir, image_tag)
        else:
            raise RuntimeError(f"Unknown runtime: {caps.recommended_runtime}")

    def _deploy_with_docker(self, remote_dir: str, image_tag: str) -> None:
        self.log("")
        self.log("=== Building Docker image on remote host ===")
        self.log("This will take roughly 5-10 minutes on the first run.")
        self.log("")
        code, _, _ = self.run(
            f"cd {remote_dir} && docker build -t {image_tag} .",
            check=False,
        )
        if code != 0:
            raise RuntimeError(
                "docker build failed. Common causes:\n"
                "  * You don't have permission to run Docker on this host.\n"
                "    (Ask sysadmin to add you to the 'docker' group, or use\n"
                "    Singularity instead if this is an HPC cluster.)\n"
                "  * The host has no internet access and cannot pull Ubuntu.\n"
                "  * Disk quota exceeded in your home directory."
            )
        self.log("")
        self.log(f"Docker image '{image_tag}' is ready on {self.cfg.host}.")
        self.log("")
        self.log("To launch BrainCell interactively, run (on the remote host):")
        self.log(f"  docker run --rm -it -p 6080:6080 {image_tag}")

    def _deploy_with_singularity(
        self,
        caps: ClusterCapabilities,
        remote_dir: str,
        image_tag: str,
    ) -> None:
        """
        On HPC: we can't run `docker build` (no root). Instead we pull a
        pre-built image from a registry. For that to work, YOU must have
        pushed the image to Docker Hub (or another registry) first.

        If the user hasn't done that yet, this function falls back to a
        clear error message explaining what's needed.
        """
        sif_path = posixpath.join(remote_dir, "braincell.sif")
        registry_image = "docker://leonidsavtchenko/braincell:8.2.2"  # <-- EDIT ME

        self.log("")
        self.log("=== Pulling BrainCell image via Singularity ===")
        self.log(f"Source: {registry_image}")
        self.log("This will take a few minutes (downloads ~1 GB).")
        self.log("")

        cmd = caps.singularity_cmd
        code, _, err = self.run(
            f"cd {remote_dir} && {cmd} pull --force braincell.sif {registry_image}",
            check=False,
        )
        if code != 0:
            raise RuntimeError(
                "Singularity pull failed. Possible reasons:\n"
                "  * The compute node has no internet access (common on HPC).\n"
                "    Try running this on the login node instead.\n"
                "  * The image hasn't been pushed to a public registry yet.\n"
                "    Contact the BrainCell maintainer.\n"
                f"Error detail: {err.strip()[:300]}"
            )

        self.log("")
        self.log(f"Image ready: {sif_path}")
        self.log("")
        self.log("To launch BrainCell interactively, run (on the remote host):")
        self.log(f"  {cmd} run --bind $HOME/braincell_results:/workspace/results \\")
        self.log(f"       {sif_path}")
        if caps.has_slurm:
            self.log("")
            self.log("Or submit it as a SLURM job:")
            self.log("  srun --pty --time=02:00:00 --mem=8G \\")
            self.log(f"       {cmd} run {sif_path}")
