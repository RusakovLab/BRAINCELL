# Platform dependencies - internal engineering inventory

Status: internal scoping note, not user-facing documentation.
Scope: every place in the BrainCell repository that assumes Microsoft Windows.
Purpose: the starting point for any future macOS or Linux port of the
graphical environment. Line numbers are as of the commit that introduced this
file; they will drift.

Nothing in this file was changed by the documentation pass that produced it.
It is an inventory only.

## 1. Hard platform guard (blocks startup outright)

| File | Line | What it does |
|---|---|---|
| `_Code/InterModular/UtilsAndHelpers/PrerequisitesCheck.hoc` | 4-7 | `if (unix_mac_pc() != 3) printMsgAndRaiseError("Sorry, BrainCell works only on Windows.")` |
| `_Code/InterModular/InterModularLoads.hoc` | 3-4 | Loads `PrerequisitesCheck.hoc` and calls `checkPrerequisites()` before anything else |

The comment in `PrerequisitesCheck.hoc` already names the two blockers:
"To support other operating systems, get rid of NLMorphologyConverter.exe and
use `/` everywhere". This guard is the single switch that has to be relaxed
last, after items 2 to 6 below are addressed.

## 2. DLL path resolution (nrnmech.dll assumed by name and separator)

| File | Line | What it does |
|---|---|---|
| `_Code/InterModular/UtilsAndHelpers/InterModularMechsDllUtils.hoc` | 80 | `sprint(dllFilePathName, "%s\\nrnmech.dll", dllDirPath)` - hardcoded name and backslash |
| `_Code/InterModular/UtilsAndHelpers/InterModularMechsDllUtils.hoc` | 52, 85 | User-facing messages that name `nrnmech.dll` |
| `_Code/InterModular/PythonCode/OtherInterModularUtils.py` | 95 | `return dirPath + sepChar + 'nrnmech.dll'` |
| `_Code/Export/PythonCode/Framework.py` | 98-101 | `dllFileName = 'nrnmech.dll'`; source path built with a literal `'\\'` |
| `_Code/Managers/MechManager/BiophysExportImport/PythonCode/BiophysJsonFileHelper.py` | 63 | Error text refers to the local library `nrnmech.dll` |
| `_Code/Export/SaveNanoHocFile.hoc` | 63 | Export warning text names `nrnmech.dll` |
| `_Code/RoadmapWidget.hoc` | 70, 85 | GUI help text names `nrnmech.dll` |

Prior art in the repository: the export generator already emits both
platforms. `_Code/Export/PythonCode/GeneratorsForMainHocFile/GeneratorsForMainHocFile.py`
lines 384-402 select `nrnmech.dll` or `x86_64/.libs/libnrnmech.so` at export
time, and the vendored `hoc2swc.py` line 184 does the same
(`"nrnmech.dll" if platform.system() == "Windows" else "libnrnmech.so"`).
That selection logic should be lifted into a shared helper and reused by the
five sites above.

Prebuilt Windows DLLs are committed at:
`Mechanisms/Astrocyte/`, `Mechanisms/Neuron/`, `Nanogeometry/Astrocyte/`,
`Nanogeometry/Neuron/`, `External simulations/Neuron/boosting/`,
`External simulations/Neuron/modeldb_ventralAD/`.

## 3. NLMorphologyConverter invocation (Windows 32-bit binary)

| File | Line | What it does |
|---|---|---|
| `_Code/Import/ImportBaseGeometry/BatchUtils.hoc` | 11, 36 | `appPathNameTempl = "%s_Code/Import/3rdParty/NLMorphologyConverter/NLMorphologyConverter.exe"` |
| `_Code/Import/ImportExtraCells/BatchUtils.hoc` | 12 | Same path template for SWC conversion |
| `_Code/Import/ImportBaseGeometry/CheckUtils.hoc` | 47-56 | Calls `createReportFileWithNLMorphologyConverter()` during import validation |
| `_Code/Import/CommonUtils.hoc` | 11-30 | `checkNLMorphologyConverterPrereqs()`: runs `if not exist %SystemRoot%\SysWOW64\msvcp100.dll exit /b 1` through `system()` - cmd.exe syntax, `SysWOW64`, and a dependency on the Microsoft Visual C++ 2010 x86 redistributable |
| `_Code/Import/3rdParty/NLMorphologyConverter/convert_hoc_to_swc.bat` | whole file | Batch wrapper around the same binary |

The `system()` calls also use `call "..."`, which is cmd.exe syntax.
There is no macOS or Linux build of NLMorphologyConverter, and its licence
forbids modification, so morphology import needs a replacement converter (or
a per-format Python importer) on those platforms.

## 4. Hardcoded python.exe in subprocess helpers

| File | Line | What it does |
|---|---|---|
| `_Code/Extracellular/Common/RangeVarHistory/PythonCode/RangeVarAnimationPlayer.py` | 151 | `subprocess.Popen([sys.exec_prefix + '/python.exe', scriptFileName], cwd=thisFileDirPath)` |
| `_Code/Simulations/Sims/Common/SimUserTemplate/SimUserTemplate.py` | 278 | `[sys.exec_prefix + '/python.exe', plotScript, pickleFile]` |

Both should use `sys.executable`, or `sys.exec_prefix + '/bin/python'` on
POSIX. This is the cheapest item on the list.

## 5. Batch and PowerShell build and launch scripts

There is no `.sh` equivalent for any of these. `Docker/docker-entrypoint.sh`
is the only shell script in the repository and belongs to the container path,
not to the desktop workflow.

| File | Purpose |
|---|---|
| `init.bat` | Launch script. Also sets `NRN_PYLIB` to a user-specific absolute path (see section 8). |
| `build_mechs.bat`, `build_mechs.ps1` | Top-level mechanism build |
| `Mechanisms/Common/build_astrocyte_&_neuron_mechs.bat` / `.ps1` | Real build logic; copies and moves `nrnmech.dll` with `copy` / `move` / `Copy-Item` |
| `Mechanisms/Astrocyte/build_astrocyte_mechs.bat` / `.ps1` | Per-tree build |
| `Mechanisms/Neuron/build_neuron_mechs.bat` / `.ps1` | Per-tree build |
| `Nanogeometry/Astrocyte/drag_&_drop_init.bat` | Drag-and-drop launcher |
| `Nanogeometry/Neuron/drag_&_drop_init.bat` | Drag-and-drop launcher |
| `_Testing/drag_&_drop_init.bat` | Drag-and-drop launcher for tests |
| `Examples/01_CA1_SingleNeuron/Run.bat` | Demo launcher |
| `Examples/02_init_InsideOutDiffManager/Run.bat` | Demo launcher |
| `_Code/Import/3rdParty/NLMorphologyConverter/convert_hoc_to_swc.bat` | Converter wrapper |
| `_RestartApp/build.bat` | `dotnet msbuild` build of the restart helper |

The `&` in three of these file names also has to survive whatever shell
replaces cmd.exe.

## 6. WPF RestartApp (Windows-only .NET desktop app)

| File | Note |
|---|---|
| `_RestartApp/RestartApp/RestartApp.csproj` | Targets `net8.0-windows` with WPF (`UseWPF`) |
| `_RestartApp/RestartApp/MainWindow.xaml`, `MainWindow.xaml.cs`, `App.xaml`, `App.xaml.cs`, `AssemblyInfo.cs` | WPF application source |
| `_RestartApp/RestartApp/bin/Release/net8.0-windows/RestartApp.exe`, `RestartApp.dll` | Prebuilt binaries committed to the repository |
| `_RestartApp/RestartApp/bin/Release/net8.0-windows/last_file_path.txt` | Committed build-time state, contains a developer-specific absolute path |
| `RestartApp.lnk` | Windows shortcut in the repository root |

WPF has no macOS or Linux runtime. A port needs a different restart mechanism
(a small Python or shell relauncher would do).

## 7. Windows-only assumptions in the GUI and helpers

| File | Line | Note |
|---|---|---|
| `_Code/InterModular/PythonCode/XpuUtils.py` | 10 | Comment on the Windows Display-settings scaling parameter affecting the GUI |
| `_Code/InterModular/PythonCode/FileDialogUtils.py` | 54 | Tk file-dialog filter list; cross-platform in principle, but the format list is tied to NLMorphologyConverter's supported inputs |
| `_Code/Import/CommonUtils.hoc` | 60 onwards | Unzip path for NeuroMorpho.org archives goes through `system()` |

## 8. Adjacent findings (not platform guards, but blockers for a clean install)

- `init.bat` line 2 hardcodes one developer's Python:
  `set NRN_PYLIB=C:\Users\savtc\anaconda3\python311.dll`. This will not work on
  any other machine.
- `_Code/Import/3rdParty/NLMorphologyConverter/convert_hoc_to_swc.bat` line 13
  hardcodes `set "PYTHON=C:\Users\****\anaconda3\python.exe"` (redacted user
  name), which is not a working default either.
- `Docker/README-Docker.md` documents a `docker build` from a `Dockerfile`,
  but no `Dockerfile` exists in `Docker/`. The container path is therefore
  incomplete - and even if the image were built, `PrerequisitesCheck.hoc`
  (section 1) would refuse to start the GUI inside a Linux container.
- The repository has no `.gitignore`. Build products (`nrnmech.dll`,
  `__pycache__/`, `_RestartApp/.../bin/`) are already tracked as a result.

## Suggested order of work for a port

1. `sys.executable` fix (section 4) - isolated, no behaviour change on Windows.
2. Shared DLL/SO resolution helper (section 2), reusing the logic that already
   exists in `GeneratorsForMainHocFile.py`.
3. Replace or wrap NLMorphologyConverter (section 3) - the largest item.
4. Shell equivalents of the build and launch scripts (section 5).
5. Replace RestartApp (section 6).
6. Relax the guard in `PrerequisitesCheck.hoc` (section 1) last, per platform.
