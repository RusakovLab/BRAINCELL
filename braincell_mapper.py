# braincell_mapper.py
# Run from: C:\Leonid\GitHub\XiaolanWu\BrainCell
# Creates braincell_map.json — the repository index used by braincell_agent.py

import re
import json
from pathlib import Path
from collections import defaultdict

# Auto-detect repo root: the folder this script lives in
REPO = Path(__file__).resolve().parent


def parse_mod(path: Path) -> dict:
    """Extract key information from a NEURON MOD file."""
    text = path.read_text(encoding="utf-8", errors="ignore")

    def find(pattern):
        m = re.search(pattern, text)
        return m.group(1).strip() if m else ""

    return {
        "file":          str(path.relative_to(REPO)),
        "title":         find(r"TITLE\s+(.+)"),
        "suffix":        find(r"SUFFIX\s+(\w+)"),
        "point_process": find(r"POINT_PROCESS\s+(\w+)"),
        "ions":          re.findall(r"USEION\s+(\w+)", text),
        "states":        re.findall(r"STATE\s*\{([^}]+)\}", text, re.DOTALL),
        "has_kinetics":  "KINETIC"  in text,
        "has_reaction":  "REACTION" in text,
        "category":      str(path.parent.parent.name),
    }


def parse_hoc(path: Path) -> dict:
    """Extract procedures, functions and dependencies from a HOC file."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "file":    str(path.relative_to(REPO)),
        "loads":   re.findall(r'load_file\s*\(\s*"([^"]+)"', text),
        "procs":   re.findall(r"^proc\s+(\w+)",   text, re.MULTILINE),
        "funcs":   re.findall(r"^func\s+(\w+)",   text, re.MULTILINE),
        "obfuncs": re.findall(r"^obfunc\s+(\w+)", text, re.MULTILINE),
        "size":    len(text),
    }


def parse_py(path: Path) -> dict:
    """Extract classes, functions and imports from a Python file."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "file":      str(path.relative_to(REPO)),
        "classes":   re.findall(r"^class\s+(\w+)",             text, re.MULTILINE),
        "functions": re.findall(r"^def\s+(\w+)",               text, re.MULTILINE),
        "imports":   re.findall(r"^(?:import|from)\s+([\w.]+)", text, re.MULTILINE),
        "size":      len(text),
    }


def main():
    print("Scanning BrainCell repository...")

    result = {
        "mod": [parse_mod(p) for p in REPO.rglob("*.mod")],
        "hoc": [parse_hoc(p) for p in REPO.rglob("*.hoc")],
        "py":  [parse_py(p)  for p in REPO.rglob("*.py")
                if "__pycache__" not in str(p) and
                   p.name not in ("braincell_panel.py", "braincell_agent.py",
                                  "braincell_mapper.py")],
    }

    output = REPO / "braincell_map.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # --- Summary ---
    ions = defaultdict(int)
    for m in result["mod"]:
        for ion in m["ions"]:
            ions[ion] += 1

    print(f"\n{'='*50}")
    print(f"  BRAINCELL REPOSITORY MAP")
    print(f"{'='*50}")
    print(f"  MOD files:    {len(result['mod'])}")
    print(f"  HOC files:    {len(result['hoc'])}")
    print(f"  Python files: {len(result['py'])}")

    print(f"\n  Ion channels by ion type:")
    for ion, count in sorted(ions.items(), key=lambda x: -x[1]):
        print(f"    {ion:12s}: {count} mechanisms")

    print(f"\n  10 largest HOC files:")
    for h in sorted(result["hoc"], key=lambda x: -x["size"])[:10]:
        fname = h["file"].split("\\")[-1]
        print(f"    {h['size']:8d} chars   {fname}")

    print(f"\n  Map saved to: {output}")


if __name__ == "__main__":
    main()
