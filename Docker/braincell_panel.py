"""
braincell_panel.py

Tkinter GUI for deploying the BrainCell Docker container to a remote
cluster. Built on top of `cluster_session.py` which does the actual SSH
work.

Launch:
    python braincell_panel.py

Dependencies:
    pip install paramiko
    (tkinter ships with Python on all standard installs.)

Design:
    * Two notebook tabs: Connect / Deploy.
    * A single shared "log pane" at the bottom of each tab so the user
      always sees what's happening.
    * All long-running operations (connect, detect, build, pull) run on a
      background thread so the GUI never freezes.
    * Each thread's output is funneled back to the log via a thread-safe
      queue.
"""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from cluster_session import (
    ClusterCapabilities,
    ClusterSession,
    SSHConfig,
)


APP_TITLE = "BrainCell Cluster Deployer"
DEFAULT_DOCKERFILE_DIR = str(Path(__file__).resolve().parent / "dockerfiles")


class BrainCellPanel(tk.Tk):
    """Main window. Owns the session, the worker thread, and the widgets."""

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("820x620")
        self.minsize(700, 500)

        # ----- state ----------------------------------------------------------
        self._session: ClusterSession | None = None
        self._caps: ClusterCapabilities | None = None
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._worker: threading.Thread | None = None

        # ----- build UI -------------------------------------------------------
        self._build_menu()
        self._build_notebook()
        self._build_log_pane()
        self._build_statusbar()

        # Start the log-drain loop (reads from the queue, writes to the widget)
        self.after(100, self._drain_log)

        # Ensure SSH is closed cleanly on window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # =========================================================================
    #   UI construction
    # =========================================================================

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.config(menu=menubar)

    def _build_notebook(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="x", padx=10, pady=(10, 0))

        self._build_connect_tab()
        self._build_deploy_tab()

    # ----- Tab 1: Connect -----------------------------------------------------
    def _build_connect_tab(self) -> None:
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="1. Connect")

        # Row-by-row form fields
        row = 0

        ttk.Label(frame, text="Cluster address (host or IP):").grid(
            row=row, column=0, sticky="w", pady=4
        )
        self.var_host = tk.StringVar(value="")
        ttk.Entry(frame, textvariable=self.var_host, width=40).grid(
            row=row, column=1, sticky="we", pady=4
        )
        row += 1

        ttk.Label(frame, text="SSH port:").grid(row=row, column=0, sticky="w", pady=4)
        self.var_port = tk.StringVar(value="22")
        ttk.Entry(frame, textvariable=self.var_port, width=8).grid(
            row=row, column=1, sticky="w", pady=4
        )
        row += 1

        ttk.Label(frame, text="Username:").grid(row=row, column=0, sticky="w", pady=4)
        self.var_user = tk.StringVar(value="")
        ttk.Entry(frame, textvariable=self.var_user, width=40).grid(
            row=row, column=1, sticky="we", pady=4
        )
        row += 1

        # Authentication method: password OR key file (radio selection)
        ttk.Label(frame, text="Authentication:").grid(
            row=row, column=0, sticky="w", pady=4
        )
        self.var_auth = tk.StringVar(value="password")
        auth_box = ttk.Frame(frame)
        ttk.Radiobutton(
            auth_box, text="Password", variable=self.var_auth, value="password",
            command=self._update_auth_state,
        ).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(
            auth_box, text="SSH key file", variable=self.var_auth, value="key",
            command=self._update_auth_state,
        ).pack(side="left")
        auth_box.grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        ttk.Label(frame, text="Password:").grid(row=row, column=0, sticky="w", pady=4)
        self.var_password = tk.StringVar(value="")
        self.entry_password = ttk.Entry(
            frame, textvariable=self.var_password, show="•", width=40
        )
        self.entry_password.grid(row=row, column=1, sticky="we", pady=4)
        row += 1

        ttk.Label(frame, text="Key file (if using key auth):").grid(
            row=row, column=0, sticky="w", pady=4
        )
        key_box = ttk.Frame(frame)
        self.var_keyfile = tk.StringVar(value="")
        self.entry_keyfile = ttk.Entry(
            key_box, textvariable=self.var_keyfile, width=32
        )
        self.entry_keyfile.pack(side="left", fill="x", expand=True)
        self.btn_browse = ttk.Button(
            key_box, text="Browse…", command=self._browse_keyfile
        )
        self.btn_browse.pack(side="left", padx=(6, 0))
        key_box.grid(row=row, column=1, sticky="we", pady=4)
        row += 1

        # Action buttons
        btn_box = ttk.Frame(frame)
        self.btn_connect = ttk.Button(
            btn_box, text="Connect + Detect", command=self._on_connect_clicked
        )
        self.btn_connect.pack(side="left", padx=(0, 8))
        self.btn_disconnect = ttk.Button(
            btn_box, text="Disconnect", command=self._on_disconnect_clicked,
            state="disabled",
        )
        self.btn_disconnect.pack(side="left")
        btn_box.grid(row=row, column=1, sticky="w", pady=(12, 0))
        row += 1

        # Make the entry column stretch
        frame.columnconfigure(1, weight=1)

        # Honest note to the user
        note = (
            "Notes:\n"
            "  • Your credentials are kept only in memory; nothing is saved to disk.\n"
            "  • Many HPC clusters disable password login -- use an SSH key if so.\n"
            "  • The 'Detect' step also probes what's installed on the remote\n"
            "    (Docker, Singularity/Apptainer, SLURM)."
        )
        ttk.Label(frame, text=note, foreground="#555555", justify="left").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(18, 0)
        )

        self._update_auth_state()

    # ----- Tab 2: Deploy ------------------------------------------------------
    def _build_deploy_tab(self) -> None:
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="2. Deploy BrainCell")

        # Capability summary (populated after Detect)
        self.caps_text = tk.StringVar(
            value="Not connected yet. Go to the 'Connect' tab first."
        )
        ttk.Label(
            frame, textvariable=self.caps_text, foreground="#333333",
            justify="left", wraplength=760,
        ).pack(anchor="w", pady=(0, 10))

        # Where the Dockerfile lives on the LOCAL side
        path_box = ttk.Frame(frame)
        ttk.Label(path_box, text="Local Dockerfile folder:").pack(
            side="left", padx=(0, 6)
        )
        self.var_dockerdir = tk.StringVar(value=DEFAULT_DOCKERFILE_DIR)
        ttk.Entry(path_box, textvariable=self.var_dockerdir, width=50).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(path_box, text="Browse…", command=self._browse_dockerdir).pack(
            side="left", padx=(6, 0)
        )
        path_box.pack(fill="x", pady=4)

        # Action buttons
        btn_box = ttk.Frame(frame)
        self.btn_deploy = ttk.Button(
            btn_box, text="Deploy BrainCell",
            command=self._on_deploy_clicked, state="disabled",
        )
        self.btn_deploy.pack(side="left", padx=(0, 8))
        btn_box.pack(anchor="w", pady=(12, 0))

        # Honest note
        note = (
            "What this does:\n"
            "  • Uploads the Dockerfile and entrypoint to your home directory on\n"
            "    the remote host (under ~/braincell_docker/).\n"
            "  • If Docker is present: builds the image there (~5-10 min).\n"
            "  • If Singularity/Apptainer is present: pulls a prebuilt image from\n"
            "    Docker Hub (~1 GB download).\n"
            "  • Prints the exact command you can run on the remote to start it."
        )
        ttk.Label(frame, text=note, foreground="#555555", justify="left").pack(
            anchor="w", pady=(18, 0)
        )

    # ----- Log pane (shared by both tabs) -------------------------------------
    def _build_log_pane(self) -> None:
        wrap = ttk.Labelframe(self, text="Log")
        wrap.pack(fill="both", expand=True, padx=10, pady=10)

        self.log_widget = tk.Text(
            wrap, height=14, wrap="word", state="disabled",
            font=("Menlo", 10) if os.name != "nt" else ("Consolas", 10),
            background="#111111", foreground="#dddddd", insertbackground="#ffffff",
        )
        self.log_widget.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.log_widget.yview)
        sb.pack(side="right", fill="y")
        self.log_widget.configure(yscrollcommand=sb.set)

    def _build_statusbar(self) -> None:
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(
            self, textvariable=self.status, anchor="w",
            relief="sunken", padding=(6, 2),
        ).pack(side="bottom", fill="x")

    # =========================================================================
    #   Small helpers
    # =========================================================================

    def _set_status(self, text: str) -> None:
        self.status.set(text)

    def log(self, message: str) -> None:
        """Thread-safe log. Called from both GUI and worker threads."""
        self._log_queue.put(message)

    def _drain_log(self) -> None:
        """Flush queued log messages into the Text widget. Runs on the GUI thread."""
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self.log_widget.configure(state="normal")
                self.log_widget.insert("end", msg + "\n")
                self.log_widget.see("end")
                self.log_widget.configure(state="disabled")
        except queue.Empty:
            pass
        finally:
            self.after(100, self._drain_log)

    def _update_auth_state(self) -> None:
        """Enable password or key widgets depending on radio selection."""
        if self.var_auth.get() == "password":
            self.entry_password.configure(state="normal")
            self.entry_keyfile.configure(state="disabled")
            self.btn_browse.configure(state="disabled")
        else:
            self.entry_password.configure(state="disabled")
            self.entry_keyfile.configure(state="normal")
            self.btn_browse.configure(state="normal")

    def _browse_keyfile(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose SSH private key",
            initialdir=str(Path.home() / ".ssh"),
        )
        if path:
            self.var_keyfile.set(path)

    def _browse_dockerdir(self) -> None:
        path = filedialog.askdirectory(
            title="Choose folder containing Dockerfile + docker-entrypoint.sh",
            initialdir=self.var_dockerdir.get() or str(Path.home()),
        )
        if path:
            self.var_dockerdir.set(path)

    def _validate_connect_form(self) -> SSHConfig | None:
        host = self.var_host.get().strip()
        user = self.var_user.get().strip()
        if not host or not user:
            messagebox.showerror("Missing fields", "Host and username are required.")
            return None
        try:
            port = int(self.var_port.get())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid port", "Port must be an integer between 1 and 65535.")
            return None

        if self.var_auth.get() == "password":
            password = self.var_password.get()
            if not password:
                messagebox.showerror("Missing password", "Password is required.")
                return None
            return SSHConfig(host=host, port=port, username=user, password=password)
        else:
            keyfile = self.var_keyfile.get().strip()
            if not keyfile or not os.path.isfile(keyfile):
                messagebox.showerror("Invalid key file", "Please select an existing SSH key file.")
                return None
            return SSHConfig(host=host, port=port, username=user, key_filename=keyfile)

    # =========================================================================
    #   Worker threading
    # =========================================================================

    def _run_in_worker(self, fn, on_done=None) -> None:
        """Run `fn()` on a background thread; call `on_done(exc_or_none)` on the GUI thread."""
        if self._worker is not None and self._worker.is_alive():
            messagebox.showinfo("Busy", "Another operation is still running.")
            return

        def wrapper():
            exc: BaseException | None = None
            try:
                fn()
            except BaseException as e:  # noqa: BLE001 -- we want to surface everything
                exc = e
                self.log(f"[error] {type(e).__name__}: {e}")
            finally:
                if on_done is not None:
                    self.after(0, lambda: on_done(exc))

        self._worker = threading.Thread(target=wrapper, daemon=True)
        self._worker.start()

    # =========================================================================
    #   Button handlers
    # =========================================================================

    def _on_connect_clicked(self) -> None:
        cfg = self._validate_connect_form()
        if cfg is None:
            return

        # Close any previous session first
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
            self._caps = None

        self._set_status("Connecting ...")
        self.btn_connect.configure(state="disabled")

        def work():
            self._session = ClusterSession(cfg, log=self.log)
            self._session.connect()
            self._caps = self._session.detect_capabilities()

        def done(exc):
            self.btn_connect.configure(state="normal")
            if exc is not None:
                self._set_status("Connection failed.")
                messagebox.showerror("Connection failed", str(exc))
                return

            self._set_status(f"Connected to {cfg.host}.")
            self.btn_disconnect.configure(state="normal")

            # Update the Deploy tab
            assert self._caps is not None
            runtime = self._caps.recommended_runtime
            if runtime == "none":
                self.caps_text.set(
                    f"Connected to {cfg.host}, but neither Docker nor Singularity "
                    f"is installed there. Ask your cluster administrator which "
                    f"container runtime is available."
                )
                self.btn_deploy.configure(state="disabled")
            else:
                self.caps_text.set(
                    f"Connected to {cfg.host} ({self._caps.distro or self._caps.kernel}).\n"
                    f"  Docker:      {'yes' if self._caps.has_docker else 'no'}\n"
                    f"  Singularity: {'yes ('+self._caps.singularity_cmd+')' if self._caps.has_singularity else 'no'}\n"
                    f"  SLURM:       {'yes' if self._caps.has_slurm else 'no'}\n"
                    f"  -> Will use: {runtime}"
                )
                self.btn_deploy.configure(state="normal")
                self.notebook.select(1)  # auto-switch to the Deploy tab

        self._run_in_worker(work, done)

    def _on_disconnect_clicked(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None
            self._caps = None
        self.btn_disconnect.configure(state="disabled")
        self.btn_deploy.configure(state="disabled")
        self.caps_text.set("Disconnected. Reconnect on the 'Connect' tab.")
        self._set_status("Disconnected.")

    def _on_deploy_clicked(self) -> None:
        if self._session is None or self._caps is None:
            messagebox.showerror("Not connected", "Connect first.")
            return
        dockerdir = self.var_dockerdir.get().strip()
        if not dockerdir or not os.path.isdir(dockerdir):
            messagebox.showerror(
                "Invalid folder",
                "Please point to a folder containing Dockerfile and docker-entrypoint.sh.",
            )
            return
        required = ("Dockerfile", "docker-entrypoint.sh")
        missing = [n for n in required if not os.path.isfile(os.path.join(dockerdir, n))]
        if missing:
            messagebox.showerror(
                "Missing files",
                "These files are missing in the selected folder:\n  " + "\n  ".join(missing),
            )
            return

        self._set_status("Deploying ...")
        self.btn_deploy.configure(state="disabled")

        def work():
            assert self._session is not None and self._caps is not None
            self._session.deploy_braincell(self._caps, dockerdir)

        def done(exc):
            if exc is not None:
                self._set_status("Deployment failed.")
                messagebox.showerror("Deployment failed", str(exc))
            else:
                self._set_status("Deployment complete.")
                messagebox.showinfo(
                    "Done",
                    "BrainCell has been deployed.\n"
                    "See the log pane for the exact command to start it on the cluster.",
                )
            self.btn_deploy.configure(state="normal")

        self._run_in_worker(work, done)

    # =========================================================================
    #   Misc
    # =========================================================================

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About",
            f"{APP_TITLE}\n\n"
            "Deploys the BrainCell Docker/Singularity container to a remote\n"
            "Linux host over SSH.\n\n"
            "This tool does not itself run simulations -- it sets up the\n"
            "container on your cluster. After deployment, follow the log's\n"
            "instructions to launch BrainCell.",
        )

    def _on_close(self) -> None:
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
        self.destroy()


def main() -> None:
    app = BrainCellPanel()
    app.mainloop()


if __name__ == "__main__":
    main()
