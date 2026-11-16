#!/usr/bin/env python3
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
OLD = "266cbc22215201a93c02e37200fe32be98a9e931"
ENTRY_RE = re.compile(r"^- \[ \] \*\*(?P<path>.+?):(?P<line>\d+)\*\* - (?P<desc>.*)$")
TODO_RE = re.compile(r"#\s*TODO\b(.*)")

def git(*args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def norm(s):
    s = re.sub(r"^:\s*", "", s.strip())
    return re.sub(r"\s+", " ", s).strip()

py_files = [p for p in git("ls-files", "*.py").splitlines() if p]
contains_todo = []
comment_todos = []
for rel in py_files:
    lines = (repo / rel).read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines, 1):
        if "TODO" in line:
            contains_todo.append((rel, i, line.strip()))
        m = TODO_RE.search(line)
        if m:
            comment_todos.append((rel, i, norm(m.group(1))))

readme = (repo / "README.md").read_text(encoding="utf-8")
entries = []
for i, line in enumerate(readme.splitlines(), 1):
    m = ENTRY_RE.match(line)
    if m:
        d = m.groupdict()
        entries.append({"readme_line": i, "path": d["path"], "line": int(d["line"]), "desc": norm(d["desc"])})

keys = [(e["path"], e["line"]) for e in entries]
sorted_ok = keys == sorted(keys)
strict_ok = True
by_path_lines = defaultdict(list)
for e in entries:
    by_path_lines[e["path"]].append(e["line"])
for p, ls in by_path_lines.items():
    strict_ok &= ls == sorted(ls) and len(ls) == len(set(ls))

changed = git("diff", "--name-only", OLD, "HEAD").splitlines()
diff = git("diff", "-U0", OLD, "HEAD", "--", "*.py")
added_todo = removed_todo = 0
added_samples, removed_samples = [], []
for line in diff.splitlines():
    if line.startswith("+++") or line.startswith("---"):
        continue
    if line.startswith("+") and "TODO" in line:
        added_todo += 1; added_samples.append(line[:180])
    elif line.startswith("-") and "TODO" in line:
        removed_todo += 1; removed_samples.append(line[:180])

changed_marker_check = {}
for rel in changed:
    if not rel.endswith(".py"):
        continue
    code = [(ln, desc) for p, ln, desc in comment_todos if p == rel]
    doc = [(e["line"], e["desc"]) for e in entries if e["path"] == rel]
    changed_marker_check[rel] = {"code_todos": code, "readme_entries": doc, "match": code == doc}

marker_map = {(p, ln): desc for p, ln, desc in comment_todos}
mismatches = []
for e in entries:
    actual = marker_map.get((e["path"], e["line"]))
    if actual is None or actual != e["desc"]:
        mismatches.append({
            "path": e["path"], "line": e["line"], "readme": e["desc"],
            "actual_at_line": actual,
            "file_exists": (repo / e["path"]).exists(),
        })

summary = {
    "head": git("rev-parse", "HEAD"),
    "main_sha": OLD,
    "tracked_python_files": len(py_files),
    "lines_containing_TODO": len(contains_todo),
    "todo_comment_markers": len(comment_todos),
    "readme_entries": len(entries),
    "title_count": readme.count("### 📝 Complete TODO List"),
    "sorted_by_path_then_line": sorted_ok and strict_ok,
    "files_changed_main_to_dev": changed,
    "added_todo_lines_in_py_diff": added_todo,
    "removed_todo_lines_in_py_diff": removed_todo,
    "changed_file_readme_matches_code": {k: v["match"] for k, v in changed_marker_check.items()},
    "readme_entries_not_matching_current_markers_all_files": len(mismatches),
}
print("SCAN_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))
for rel, data in changed_marker_check.items():
    print("\nCHANGED_FILE", rel, "match=", data["match"])
    for ln, desc in data["code_todos"]:
        print(f"  CODE {rel}:{ln} - {desc}")
    for ln, desc in data["readme_entries"]:
        print(f"  README {rel}:{ln} - {desc}")
print("\nREMOVED_TODO_SAMPLES")
for x in removed_samples: print(x)
print("ADDED_TODO_SAMPLES")
for x in added_samples: print(x)
print("\nMISMATCH_SAMPLES_OUTSIDE_EXPECTED_DELTA")
for x in mismatches[:30]: print(json.dumps(x, ensure_ascii=False))

assert summary["title_count"] == 1
assert summary["readme_entries"] == 215
assert summary["sorted_by_path_then_line"] is True
assert added_todo == 0 and removed_todo == 11
assert all(summary["changed_file_readme_matches_code"].values())
print("\nTREE_SCAN_ASSERTIONS_PASSED")
