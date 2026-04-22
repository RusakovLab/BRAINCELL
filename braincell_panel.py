"""
BrainCell AI Agent — GUI Panel
================================
A simple desktop application that replaces the terminal workflow.
Just click buttons and type questions — no command line needed.

Requirements:
    pip install anthropic

Usage:
    python braincell_panel.py
    (or double-click the file in File Explorer)
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import json
import os
import re
import sys
from pathlib import Path

# ── Auto-detect repo root: the folder this script lives in ───────────────────
SCRIPT_DIR = Path(__file__).resolve().parent

# ── Auto-add common Anaconda user-package paths so 'anthropic' is found ──────
for _candidate in [
    Path.home() / "AppData" / "Roaming" / "Python" / "Python311" / "site-packages",
    Path.home() / "AppData" / "Roaming" / "Python" / "Python312" / "site-packages",
    Path.home() / "anaconda3" / "Lib" / "site-packages",
    Path.home() / "anaconda3" / "envs" / "base" / "Lib" / "site-packages",
]:
    if _candidate.exists() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

# ── Try to import anthropic ───────────────────────────────────────────────────
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# ── Colours & fonts ───────────────────────────────────────────────────────────
C_BG        = "#1A1D23"   # main dark background
C_PANEL     = "#22262F"   # panel / card background
C_BORDER    = "#2E75B6"   # blue accent border
C_ACCENT    = "#2E75B6"   # blue accent
C_ACCENT2   = "#1F4E79"   # dark blue
C_GREEN     = "#27AE60"   # success green
C_AMBER     = "#E67E22"   # warning amber
C_RED       = "#E74C3C"   # error red
C_TEXT      = "#ECF0F1"   # main text
C_SUBTEXT   = "#95A5A6"   # secondary text
C_INPUT_BG  = "#2C3040"   # input background
C_CODE_BG   = "#0D1117"   # code output background
C_CODE_TEXT = "#00FF88"   # code output text

FONT_TITLE  = ("Segoe UI", 15, "bold")
FONT_HEAD   = ("Segoe UI", 11, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 10)
FONT_MONO_S = ("Consolas", 9)


class BrainCellPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("BrainCell AI Agent")
        self.root.geometry("1100x780")
        self.root.minsize(900, 650)
        self.root.configure(bg=C_BG)

        # State
        self.repo_path   = tk.StringVar()
        self.api_key_var = tk.StringVar()
        self.status_var  = tk.StringVar(value="Not connected")
        self.model_var   = tk.StringVar(value="claude-sonnet-4-6")
        self.repo_map    = None
        self.client      = None
        self.busy        = False
        self.chat_history = []

        # Default repo path = folder where this script lives
        self.repo_path.set(str(SCRIPT_DIR))

        # Load saved settings (may override the default above)
        self._load_settings()

        # Build UI
        self._build_ui()

        # Auto-connect if we have everything
        self.root.after(300, self._try_autoconnect)

    # ─── Settings persistence ─────────────────────────────────────────────────

    def _settings_path(self):
        return Path.home() / ".braincell_panel_settings.json"

    def _load_settings(self):
        try:
            with open(self._settings_path()) as f:
                s = json.load(f)
            # Only override repo_path if a saved value exists
            saved_repo = s.get("repo_path", "")
            if saved_repo:
                self.repo_path.set(saved_repo)
            self.model_var.set(s.get("model", "claude-sonnet-4-6"))
            # Load API key: saved settings → environment variable
            saved_key = s.get("api_key", "")
            env_key   = os.environ.get("ANTHROPIC_API_KEY", "")
            self.api_key_var.set(saved_key or env_key)
        except Exception:
            env_key = os.environ.get("ANTHROPIC_API_KEY", "")
            self.api_key_var.set(env_key)

    def _save_settings(self):
        try:
            s = {
                "repo_path": self.repo_path.get(),
                "model":     self.model_var.get(),
                "api_key":   self.api_key_var.get(),
            }
            with open(self._settings_path(), "w") as f:
                json.dump(s, f, indent=2)
        except Exception:
            pass

    # ─── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Top bar
        top = tk.Frame(self.root, bg=C_ACCENT2, height=52)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="⬡  BrainCell AI Agent",
                 font=FONT_TITLE, bg=C_ACCENT2, fg=C_TEXT).pack(side="left", padx=18, pady=10)

        # Status indicator (top right)
        self.status_dot = tk.Label(top, text="●", font=("Segoe UI", 16),
                                   bg=C_ACCENT2, fg=C_RED)
        self.status_dot.pack(side="right", padx=6, pady=10)
        self.status_label = tk.Label(top, textvariable=self.status_var,
                                     font=FONT_SMALL, bg=C_ACCENT2, fg=C_SUBTEXT)
        self.status_label.pack(side="right", pady=10)

        # ── Main layout: left sidebar + right chat area
        main = tk.Frame(self.root, bg=C_BG)
        main.pack(fill="both", expand=True)

        # Left sidebar (settings + quick actions)
        sidebar = tk.Frame(main, bg=C_PANEL, width=290)
        sidebar.pack(side="left", fill="y", padx=(8, 4), pady=8)
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        # Right area (chat)
        right = tk.Frame(main, bg=C_BG)
        right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)
        self._build_chat(right)

    def _section(self, parent, title):
        """Styled section header inside sidebar."""
        f = tk.Frame(parent, bg=C_PANEL)
        f.pack(fill="x", padx=10, pady=(12, 2))
        tk.Label(f, text=title.upper(), font=("Segoe UI", 8, "bold"),
                 bg=C_PANEL, fg=C_ACCENT).pack(anchor="w")
        tk.Frame(parent, bg=C_BORDER, height=1).pack(fill="x", padx=10, pady=(0, 6))
        return parent

    def _build_sidebar(self, parent):
        canvas = tk.Canvas(parent, bg=C_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=C_PANEL)

        scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        # Don't show scrollbar unless needed

        sb = scroll_frame  # shorthand

        # ── 1. Repository path
        self._section(sb, "📁  Repository")

        repo_frame = tk.Frame(sb, bg=C_PANEL)
        repo_frame.pack(fill="x", padx=10, pady=2)

        self.repo_entry = tk.Entry(repo_frame, textvariable=self.repo_path,
                                   font=FONT_MONO_S, bg=C_INPUT_BG, fg=C_TEXT,
                                   insertbackground=C_TEXT, relief="flat",
                                   highlightthickness=1, highlightbackground=C_BORDER)
        self.repo_entry.pack(fill="x", pady=(0, 4))

        tk.Button(repo_frame, text="Browse...", font=FONT_SMALL,
                  bg=C_ACCENT2, fg=C_TEXT, relief="flat", cursor="hand2",
                  command=self._browse_repo).pack(fill="x")

        # ── 2. API Key
        self._section(sb, "🔑  Anthropic API Key")

        key_frame = tk.Frame(sb, bg=C_PANEL)
        key_frame.pack(fill="x", padx=10, pady=2)

        self.key_entry = tk.Entry(key_frame, textvariable=self.api_key_var,
                                  font=FONT_MONO_S, bg=C_INPUT_BG, fg=C_TEXT,
                                  insertbackground=C_TEXT, relief="flat", show="•",
                                  highlightthickness=1, highlightbackground=C_BORDER)
        self.key_entry.pack(fill="x", pady=(0, 4))

        key_btns = tk.Frame(key_frame, bg=C_PANEL)
        key_btns.pack(fill="x")
        tk.Button(key_btns, text="Show/Hide", font=FONT_SMALL,
                  bg=C_PANEL, fg=C_SUBTEXT, relief="flat", cursor="hand2",
                  command=self._toggle_key_vis).pack(side="left")
        tk.Label(key_btns, text="console.anthropic.com →",
                 font=("Segoe UI", 8), bg=C_PANEL, fg=C_ACCENT,
                 cursor="hand2").pack(side="right")

        # ── 3. Model
        self._section(sb, "🤖  Model")

        model_frame = tk.Frame(sb, bg=C_PANEL)
        model_frame.pack(fill="x", padx=10, pady=2)

        models = ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"]
        model_cb = ttk.Combobox(model_frame, textvariable=self.model_var,
                                values=models, font=FONT_SMALL, state="readonly")
        model_cb.pack(fill="x")

        # ── 4. Connect button
        tk.Frame(sb, bg=C_PANEL, height=8).pack()
        self.connect_btn = tk.Button(sb, text="⚡  Connect & Index Repository",
                                     font=FONT_HEAD, bg=C_GREEN, fg="white",
                                     relief="flat", cursor="hand2", pady=8,
                                     command=self._connect)
        self.connect_btn.pack(fill="x", padx=10, pady=4)

        # ── 5. Repository info (shown after connect)
        self._section(sb, "📊  Repository Info")

        self.info_frame = tk.Frame(sb, bg=C_PANEL)
        self.info_frame.pack(fill="x", padx=10, pady=2)

        self.info_labels = {}
        for key in ["MOD files", "HOC files", "Python files", "Status"]:
            row = tk.Frame(self.info_frame, bg=C_PANEL)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=key + ":", font=FONT_SMALL,
                     bg=C_PANEL, fg=C_SUBTEXT, width=12, anchor="w").pack(side="left")
            lbl = tk.Label(row, text="—", font=FONT_SMALL,
                           bg=C_PANEL, fg=C_TEXT, anchor="w")
            lbl.pack(side="left")
            self.info_labels[key] = lbl

        # ── 6. Quick question buttons
        self._section(sb, "⚡  Quick Questions")

        quick_qs = [
            ("GluTrans biophysics",     "How does GluTrans.mod work? Explain the biophysics in detail."),
            ("Calcium dynamics",        "What mechanisms handle calcium dynamics in astrocytes? List and explain each."),
            ("K⁺ channels",             "Find all potassium channel MOD files and explain their roles."),
            ("Gap junctions",           "Explain all gap junction mechanisms and their differences."),
            ("Architecture overview",   "Explain the overall architecture of the BrainCell codebase — folders, key files and how they connect."),
            ("KINETIC blocks",          "Which MOD files use KINETIC blocks and what reactions do they model?"),
            ("Na/K pump",               "How does nkpump.mod model the Na/K ATPase pump?"),
            ("AMPA synapse",            "Explain the AMPA synapse model in AMPASyn.mod."),
        ]

        for label, question in quick_qs:
            btn = tk.Button(sb, text=label, font=FONT_SMALL,
                            bg=C_INPUT_BG, fg=C_TEXT, relief="flat",
                            cursor="hand2", anchor="w", padx=10, pady=4,
                            command=lambda q=question: self._send_question(q))
            btn.pack(fill="x", padx=10, pady=2)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=C_ACCENT2))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=C_INPUT_BG))

        # ── 7. Bottom buttons
        tk.Frame(sb, bg=C_PANEL, height=8).pack()
        tk.Button(sb, text="🗑  Clear Chat", font=FONT_SMALL,
                  bg=C_PANEL, fg=C_SUBTEXT, relief="flat", cursor="hand2",
                  command=self._clear_chat).pack(fill="x", padx=10, pady=2)
        tk.Button(sb, text="💾  Save Chat", font=FONT_SMALL,
                  bg=C_PANEL, fg=C_SUBTEXT, relief="flat", cursor="hand2",
                  command=self._save_chat).pack(fill="x", padx=10, pady=2)

    def _build_chat(self, parent):
        # Chat display
        chat_frame = tk.Frame(parent, bg=C_CODE_BG,
                              highlightthickness=1, highlightbackground=C_BORDER)
        chat_frame.pack(fill="both", expand=True)

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, font=FONT_MONO, bg=C_CODE_BG, fg=C_TEXT,
            insertbackground=C_TEXT, relief="flat", wrap="word",
            state="disabled", padx=14, pady=10,
            selectbackground=C_ACCENT2)
        self.chat_display.pack(fill="both", expand=True)

        # Tag styles
        self.chat_display.tag_configure("user_hdr", foreground=C_ACCENT,
                                         font=("Consolas", 10, "bold"))
        self.chat_display.tag_configure("agent_hdr", foreground=C_GREEN,
                                         font=("Consolas", 10, "bold"))
        self.chat_display.tag_configure("user_msg",  foreground="#BDC3C7",
                                         font=FONT_MONO)
        self.chat_display.tag_configure("agent_msg", foreground=C_TEXT,
                                         font=FONT_MONO)
        self.chat_display.tag_configure("thinking",  foreground=C_AMBER,
                                         font=("Consolas", 10, "italic"))
        self.chat_display.tag_configure("error",     foreground=C_RED,
                                         font=FONT_MONO)
        self.chat_display.tag_configure("welcome",   foreground=C_GREEN,
                                         font=("Consolas", 10, "bold"))
        self.chat_display.tag_configure("separator", foreground="#3A3F4A",
                                         font=("Consolas", 9))

        self._print_welcome()

        # Input area
        input_frame = tk.Frame(parent, bg=C_BG)
        input_frame.pack(fill="x", pady=(6, 0))

        # Mode selector
        mode_bar = tk.Frame(input_frame, bg=C_BG)
        mode_bar.pack(fill="x", pady=(0, 4))

        self.mode_var = tk.StringVar(value="ask")
        modes = [("Ask / analyse", "ask"), ("Modify file", "modify"),
                 ("Search files", "search"), ("Explain file", "explain")]
        for label, val in modes:
            rb = tk.Radiobutton(mode_bar, text=label, variable=self.mode_var,
                                value=val, font=FONT_SMALL,
                                bg=C_BG, fg=C_SUBTEXT,
                                selectcolor=C_INPUT_BG, activebackground=C_BG,
                                activeforeground=C_TEXT,
                                indicatoron=False, padx=10, pady=4, relief="flat",
                                cursor="hand2",
                                command=self._update_placeholder)
            rb.pack(side="left", padx=2)
            rb.bind("<Enter>", lambda e, r=rb: r.configure(fg=C_TEXT))
            rb.bind("<Leave>", lambda e, r=rb: r.configure(
                fg=C_TEXT if self.mode_var.get() == r.cget("value") else C_SUBTEXT))

        # Text input + send button
        entry_row = tk.Frame(input_frame, bg=C_BG)
        entry_row.pack(fill="x")

        self.question_input = tk.Text(entry_row, font=FONT_MONO,
                                      bg=C_INPUT_BG, fg=C_TEXT,
                                      insertbackground=C_TEXT, relief="flat",
                                      height=3, padx=10, pady=8, wrap="word",
                                      highlightthickness=1,
                                      highlightbackground=C_BORDER,
                                      highlightcolor=C_ACCENT)
        self.question_input.pack(side="left", fill="x", expand=True)
        self.question_input.bind("<Return>",     self._on_enter)
        self.question_input.bind("<Shift-Return>", lambda e: None)  # allow newline
        self.question_input.bind("<Control-Return>", lambda e: self._do_send())

        send_btn = tk.Button(entry_row, text="Send\n▶",
                             font=("Segoe UI", 11, "bold"),
                             bg=C_ACCENT, fg="white", relief="flat",
                             cursor="hand2", width=7, pady=10,
                             command=self._do_send)
        send_btn.pack(side="left", padx=(6, 0), fill="y")

        hint = tk.Label(input_frame,
                        text="Enter = Send  •  Shift+Enter = New line  •  Ctrl+Enter = Send",
                        font=("Segoe UI", 8), bg=C_BG, fg=C_SUBTEXT)
        hint.pack(anchor="e", pady=(2, 0))

        self._update_placeholder()

    # ─── Chat display helpers ─────────────────────────────────────────────────

    def _chat_append(self, text, tag="agent_msg"):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", text, tag)
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def _print_welcome(self):
        banner = (
            "╔══════════════════════════════════════════════════════════════╗\n"
            "║          BrainCell AI Agent  —  Ready to use                ║\n"
            "╚══════════════════════════════════════════════════════════════╝\n\n"
        )
        self._chat_append(banner, "welcome")
        self._chat_append(
            "1. Set your repository path in the left panel\n"
            "2. Enter your Anthropic API key\n"
            "3. Click  ⚡ Connect & Index Repository\n"
            "4. Type a question below or click a Quick Question button\n\n",
            "agent_msg")
        self._chat_append("─" * 66 + "\n\n", "separator")

    # ─── Sidebar actions ──────────────────────────────────────────────────────

    def _browse_repo(self):
        folder = filedialog.askdirectory(title="Select your BrainCell repository folder")
        if folder:
            self.repo_path.set(folder.replace("/", "\\"))

    def _toggle_key_vis(self):
        current = self.key_entry.cget("show")
        self.key_entry.configure(show="" if current == "•" else "•")

    def _update_placeholder(self):
        hints = {
            "ask":     "Type any question about the BrainCell codebase...",
            "modify":  "Format:  relative\\path\\to\\file.mod   Description of change",
            "search":  "Type a keyword to search across all files...",
            "explain": "Type the relative path to a file, e.g.  Mechanisms\\Common\\MOD_files\\GluTrans.mod",
        }
        mode = self.mode_var.get()
        self.question_input.configure(fg=C_SUBTEXT)
        current = self.question_input.get("1.0", "end-1c")
        if not current or current in hints.values():
            self.question_input.delete("1.0", "end")
            self.question_input.insert("1.0", hints[mode])

        def clear_hint(e):
            txt = self.question_input.get("1.0", "end-1c")
            if txt in hints.values():
                self.question_input.delete("1.0", "end")
                self.question_input.configure(fg=C_TEXT)
        self.question_input.bind("<FocusIn>", clear_hint)

    def _set_status(self, text, color=C_SUBTEXT):
        self.status_var.set(text)
        self.status_label.configure(fg=color)
        dot_color = C_GREEN if color == C_GREEN else (C_AMBER if color == C_AMBER else C_RED)
        self.status_dot.configure(fg=dot_color)

    def _update_info(self, mod, hoc, py):
        self.info_labels["MOD files"].configure(text=str(mod), fg=C_ACCENT)
        self.info_labels["HOC files"].configure(text=str(hoc), fg=C_ACCENT)
        self.info_labels["Python files"].configure(text=str(py), fg=C_ACCENT)
        self.info_labels["Status"].configure(text="Ready ✔", fg=C_GREEN)

    # ─── Connect & index ──────────────────────────────────────────────────────

    def _try_autoconnect(self):
        if self.repo_path.get() and self.api_key_var.get():
            self._connect()

    def _connect(self):
        if self.busy:
            return

        repo = self.repo_path.get().strip()
        key  = self.api_key_var.get().strip()

        if not repo:
            messagebox.showerror("Missing path", "Please set the repository folder path.")
            return
        if not Path(repo).exists():
            messagebox.showerror("Path not found",
                                 f"Folder not found:\n{repo}\n\nPlease check the path.")
            return
        if not key:
            messagebox.showerror("Missing API key",
                                 "Please enter your Anthropic API key.\n"
                                 "Get one at console.anthropic.com")
            return
        if not ANTHROPIC_AVAILABLE:
            messagebox.showerror("Package missing",
                                 "The 'anthropic' package is not installed.\n\n"
                                 "Open Anaconda Prompt and run:\n"
                                 "pip install anthropic")
            return

        self._save_settings()
        self._set_status("Connecting...", C_AMBER)
        self.connect_btn.configure(state="disabled", text="⏳  Indexing...")
        self.busy = True

        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _connect_worker(self):
        try:
            repo = Path(self.repo_path.get().strip())
            key  = self.api_key_var.get().strip()

            # Check for existing map
            map_path = repo / "braincell_map.json"
            if map_path.exists():
                with open(map_path, encoding="utf-8") as f:
                    self.repo_map = json.load(f)
                self.root.after(0, lambda: self._chat_append(
                    f"✔  Loaded existing index: {map_path}\n\n", "agent_msg"))
            else:
                self.root.after(0, lambda: self._chat_append(
                    "⏳  No index found — scanning repository (this takes ~30 seconds)...\n\n",
                    "thinking"))
                self.repo_map = self._build_map(repo)
                with open(map_path, "w", encoding="utf-8") as f:
                    json.dump(self.repo_map, f, indent=2, ensure_ascii=False)
                self.root.after(0, lambda: self._chat_append(
                    f"✔  Repository indexed and saved to {map_path}\n\n", "agent_msg"))

            # Test API key
            self.client = anthropic.Anthropic(api_key=key)
            test = self.client.messages.create(
                model=self.model_var.get(),
                max_tokens=10,
                messages=[{"role": "user", "content": "hi"}])

            n_mod = len(self.repo_map.get("mod", []))
            n_hoc = len(self.repo_map.get("hoc", []))
            n_py  = len(self.repo_map.get("py",  []))

            self.root.after(0, lambda: self._on_connected(n_mod, n_hoc, n_py))

        except anthropic.AuthenticationError:
            self.root.after(0, lambda: self._on_error(
                "Invalid API key. Please check your key at console.anthropic.com"))
        except anthropic.BadRequestError as e:
            if "credit" in str(e).lower():
                self.root.after(0, lambda: self._on_error(
                    "No API credits. Add credits at console.anthropic.com → Billing"))
            else:
                self.root.after(0, lambda: self._on_error(str(e)))
        except Exception as e:
            self.root.after(0, lambda: self._on_error(str(e)))

    def _on_connected(self, n_mod, n_hoc, n_py):
        self.busy = False
        self.connect_btn.configure(state="normal", text="🔄  Re-index Repository")
        self._set_status(f"Connected  •  {n_mod} MOD  {n_hoc} HOC  {n_py} PY", C_GREEN)
        self._update_info(n_mod, n_hoc, n_py)
        self._chat_append(
            f"✔  Connected!  Model: {self.model_var.get()}\n"
            f"   Repository: {self.repo_path.get()}\n"
            f"   Files indexed: {n_mod} MOD  |  {n_hoc} HOC  |  {n_py} Python\n\n"
            "   Ready to answer questions. Type below or click a Quick Question button.\n\n",
            "welcome")
        self._chat_append("─" * 66 + "\n\n", "separator")

    def _on_error(self, msg):
        self.busy = False
        self.connect_btn.configure(state="normal", text="⚡  Connect & Index Repository")
        self._set_status("Error — see chat", C_RED)
        self._chat_append(f"✖  Error: {msg}\n\n", "error")

    # ─── Repository indexing (built-in mapper) ────────────────────────────────

    def _build_map(self, repo_path: Path) -> dict:
        import re

        def parse_mod(p):
            txt = p.read_text(encoding="utf-8", errors="ignore")
            def find(pat):
                m = re.search(pat, txt)
                return m.group(1).strip() if m else ""
            return {
                "file":          str(p.relative_to(repo_path)),
                "title":         find(r"TITLE\s+(.+)"),
                "suffix":        find(r"SUFFIX\s+(\w+)"),
                "point_process": find(r"POINT_PROCESS\s+(\w+)"),
                "ions":          re.findall(r"USEION\s+(\w+)", txt),
                "has_kinetics":  "KINETIC" in txt,
                "category":      str(p.parent.parent.name),
            }

        def parse_hoc(p):
            txt = p.read_text(encoding="utf-8", errors="ignore")
            return {
                "file":  str(p.relative_to(repo_path)),
                "loads": re.findall(r'load_file\s*\(\s*"([^"]+)"', txt),
                "procs": re.findall(r"^proc\s+(\w+)", txt, re.MULTILINE),
                "funcs": re.findall(r"^func\s+(\w+)",  txt, re.MULTILINE),
                "size":  len(txt),
            }

        def parse_py(p):
            txt = p.read_text(encoding="utf-8", errors="ignore")
            return {
                "file":      str(p.relative_to(repo_path)),
                "classes":   re.findall(r"^class\s+(\w+)", txt, re.MULTILINE),
                "functions": re.findall(r"^def\s+(\w+)",   txt, re.MULTILINE),
                "size":      len(txt),
            }

        return {
            "mod": [parse_mod(p) for p in repo_path.rglob("*.mod")],
            "hoc": [parse_hoc(p) for p in repo_path.rglob("*.hoc")],
            "py":  [parse_py(p)  for p in repo_path.rglob("*.py")
                    if "__pycache__" not in str(p) and
                       p.name not in ("braincell_panel.py", "braincell_agent.py",
                                      "braincell_mapper.py")],
        }

    # ─── Sending questions ────────────────────────────────────────────────────

    def _on_enter(self, event):
        if not event.state & 0x1:  # Shift not held
            self._do_send()
            return "break"

    def _do_send(self):
        if self.busy:
            return
        text = self.question_input.get("1.0", "end-1c").strip()
        if not text:
            return
        # Ignore placeholder text
        placeholders = [
            "Type any question about the BrainCell codebase...",
            "Format:  relative\\path\\to\\file.mod   Description of change",
            "Type a keyword to search across all files...",
            "Type the relative path to a file, e.g.  Mechanisms\\Common\\MOD_files\\GluTrans.mod",
        ]
        if text in placeholders:
            return
        self.question_input.delete("1.0", "end")
        self._send_question(text)

    def _send_question(self, question: str):
        if not self.client:
            messagebox.showwarning("Not connected",
                                   "Please connect first by clicking\n'⚡ Connect & Index Repository'")
            return
        if self.busy:
            return

        mode = self.mode_var.get()
        self._chat_append(f"YOU [{mode.upper()}]\n", "user_hdr")
        self._chat_append(question + "\n\n", "user_msg")
        self._chat_append("⏳  Thinking...\n", "thinking")

        self.busy = True
        self._set_status("Thinking...", C_AMBER)

        threading.Thread(
            target=self._query_worker,
            args=(question, mode),
            daemon=True
        ).start()

    def _query_worker(self, question: str, mode: str):
        try:
            if mode == "search":
                response = self._do_search(question)
            elif mode == "explain":
                response = self._do_explain(question)
            elif mode == "modify":
                response = self._do_modify_plan(question)
            else:
                response = self._do_ask(question)

            self.root.after(0, lambda: self._show_response(response))
        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))

    def _show_response(self, response: str):
        self.busy = False
        self._set_status("Ready", C_GREEN)
        # Remove the "Thinking..." line
        self.chat_display.configure(state="normal")
        content = self.chat_display.get("1.0", "end")
        idx = content.rfind("⏳  Thinking...\n")
        if idx != -1:
            line_start = "1.0 + %d chars" % idx
            line_end   = "1.0 + %d chars" % (idx + len("⏳  Thinking...\n"))
            self.chat_display.delete(line_start, line_end)
        self.chat_display.configure(state="disabled")

        self._chat_append("AGENT\n", "agent_hdr")
        self._chat_append(response + "\n\n", "agent_msg")
        self._chat_append("─" * 66 + "\n\n", "separator")

    def _show_error(self, error: str):
        self.busy = False
        self._set_status("Error", C_RED)
        self.chat_display.configure(state="normal")
        content = self.chat_display.get("1.0", "end")
        idx = content.rfind("⏳  Thinking...\n")
        if idx != -1:
            self.chat_display.delete("1.0 + %d chars" % idx,
                                     "1.0 + %d chars" % (idx + len("⏳  Thinking...\n")))
        self.chat_display.configure(state="disabled")
        self._chat_append(f"✖  Error: {error}\n\n", "error")

    # ─── Query builders ───────────────────────────────────────────────────────

    SYSTEM = """You are an expert in computational neurobiology and the NEURON simulator.
You work with BrainCell — a platform by Savtchenko/Rusakov Lab (UCL) for simulating
neurons and astrocytes with nano-scale geometry.

Repository structure:
  _Code/Managers/    — BioManager, SynManager, GapJuncManager, InhomManager, ExportManager
  _Code/Simulations/ — SimMyelinatedAxon and other ready-to-run simulations
  _Code/Extracellular/ — extracellular ion diffusion
  Mechanisms/Astrocyte/MOD_files/ — gapCa*, GAT1_Bicho, Kir, kdrglia
  Mechanisms/Neuron/MOD_files/    — AMPASyn, GABA_tonic, Na/K channels, nkpump
  Mechanisms/Common/MOD_files/    — cadifus, GluTrans, FRAP, gap*, diffusion helpers
  Biophysics/ — JSON simulation configs
  Geometry/ + Nanogeometry/ — cell morphologies

When analysing MOD files: explain KINETIC schemes, voltage dependence (Eyring theory),
state variables, ions, units (mA/cm2, mM, ms), and physiological meaning.
Always be specific: cite parameter names, rate constants, and line-level details.
When suggesting modifications: show the exact code change and explain the biophysics."""

    def _search_map(self, query: str) -> list:
        if not self.repo_map:
            return []
        q = query.lower()
        results = []
        for m in self.repo_map.get("mod", []):
            score = sum([
                q in m["file"].lower(),
                q in m.get("title", "").lower(),
                q in m.get("suffix", "").lower(),
                any(q in ion for ion in m.get("ions", [])),
                q in m.get("point_process", "").lower(),
            ])
            if score:
                results.append((score, m["file"]))
        for h in self.repo_map.get("hoc", []):
            if q in h["file"].lower():
                results.append((1, h["file"]))
        for p in self.repo_map.get("py", []):
            if q in p["file"].lower():
                results.append((1, p["file"]))
        seen = set()
        out  = []
        for score, path in sorted(results, reverse=True):
            if path not in seen:
                seen.add(path)
                out.append(path)
        return out[:8]

    def _read_file(self, filepath: str) -> str:
        try:
            full = Path(self.repo_path.get()) / filepath
            content = full.read_text(encoding="utf-8", errors="ignore")
            return content[:12000] if len(content) > 12000 else content
        except Exception as e:
            return f"[Could not read {filepath}: {e}]"

    def _build_context(self, files: list) -> str:
        m = self.repo_map or {}
        ctx = (f"Repository: {len(m.get('mod',[]))} MOD, "
               f"{len(m.get('hoc',[]))} HOC, {len(m.get('py',[]))} Python files.\n\n")
        for f in files:
            ctx += f"\n{'='*60}\nFILE: {f}\n{'='*60}\n{self._read_file(f)}\n"
        return ctx

    def _call_api(self, user_content: str) -> str:
        resp = self.client.messages.create(
            model=self.model_var.get(),
            max_tokens=4096,
            system=self.SYSTEM,
            messages=[{"role": "user", "content": user_content}]
        )
        return resp.content[0].text

    def _do_ask(self, question: str) -> str:
        files   = self._search_map(question)
        context = self._build_context(files)
        return self._call_api(f"{context}\n\nQuestion: {question}")

    def _do_search(self, query: str) -> str:
        files = self._search_map(query)
        if not files:
            return f"No files found matching '{query}'."
        result = f"Found {len(files)} file(s) matching '{query}':\n\n"
        for f in files:
            result += f"  • {f}\n"
        result += "\n"
        context = self._build_context(files[:4])
        summary = self._call_api(
            f"{context}\n\nBriefly describe what each of these files does "
            f"in the context of '{query}' (1-2 sentences per file).")
        return result + summary

    def _do_explain(self, filepath: str) -> str:
        filepath = filepath.strip()
        content  = self._read_file(filepath)
        return self._call_api(
            f"FILE: {filepath}\n\n{content}\n\n"
            "Provide a comprehensive explanation:\n"
            "1. What biological/biophysical process does this model?\n"
            "2. Key parameters and their physiological meaning\n"
            "3. State variables and their dynamics\n"
            "4. How it interacts with other BrainCell mechanisms\n"
            "5. Known limitations or potential improvements")

    def _do_modify_plan(self, text: str) -> str:
        parts = text.split(None, 1)
        if len(parts) < 2:
            return ("Please format your modify request as:\n"
                    "  relative\\path\\to\\file.mod   Description of the change\n\n"
                    "Example:\n"
                    "  Mechanisms\\Astrocyte\\MOD_files\\Kir4.mod   Add Q10=2.2 temperature dependence")
        filepath, instruction = parts[0], parts[1]
        content = self._read_file(filepath)
        response = self._call_api(
            f"FILE: {filepath}\n\n{content}\n\n"
            f"Proposed modification: {instruction}\n\n"
            "1. Explain what change you would make and why (biophysics)\n"
            "2. Show the EXACT code diff or new code block\n"
            "3. List any risks or things to check after making this change\n\n"
            "Format the code change clearly so the user can apply it manually.")
        return (response + "\n\n"
                "─── How to apply ────────────────────────────────────────\n"
                f"Open the file in your text editor:\n  {Path(self.repo_path.get()) / filepath}\n"
                "Apply the change shown above, save, then recompile your MOD files.")

    # ─── Utility ─────────────────────────────────────────────────────────────

    def _clear_chat(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        self._print_welcome()
        self.chat_history = []

    def _save_chat(self):
        content = self.chat_display.get("1.0", "end")
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="braincell_chat.txt")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Saved", f"Chat saved to:\n{path}")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()

    # App icon (simple coloured window icon)
    try:
        root.iconbitmap(default="")
    except Exception:
        pass

    # Style ttk elements
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TCombobox", fieldbackground=C_INPUT_BG, background=C_PANEL,
                    foreground=C_TEXT, selectbackground=C_ACCENT2)
    style.configure("Vertical.TScrollbar", background=C_PANEL, troughcolor=C_CODE_BG,
                    arrowcolor=C_SUBTEXT)

    app = BrainCellPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
