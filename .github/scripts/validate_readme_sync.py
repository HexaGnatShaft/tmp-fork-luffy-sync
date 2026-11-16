#!/usr/bin/env python3
import re
import sys
import pathlib
from collections import Counter

old_path, new_path, repo_dir = sys.argv[1:4]
old = pathlib.Path(old_path).read_text()
new = pathlib.Path(new_path).read_text()
pat = re.compile(r"^- \[ \] \*\*(?P<path>.+?):(?P<line>\d+)\*\* - (?P<desc>.*)$", re.M)
old_entries = pat.findall(old)
new_entries = pat.findall(new)
title = "### 📝 Complete TODO List"
assert old.count(title) == 1 and new.count(title) == 1, "section title changed or missing"
assert (len(old_entries), len(new_entries)) == (226, 215), (len(old_entries), len(new_entries))

def non_entry(text):
    return [line for line in text.splitlines() if not pat.match(line)]
assert non_entry(old) == non_entry(new), "title or non-entry README content changed"

def norm(desc):
    return re.sub(r"\s+", " ", re.sub(r"^:\s*", "", desc.strip())).strip()

def keys(rows):
    return [(p, int(n)) for p, n, d in rows]
assert keys(new_entries) == sorted(keys(new_entries)), "entries are not path/line sorted"
by_file = {}
for p, n, d in new_entries:
    by_file.setdefault(p, []).append(int(n))
for p, lines in by_file.items():
    assert lines == sorted(lines) and len(lines) == len(set(lines)), p

old_keys = Counter((p, norm(d)) for p, n, d in old_entries)
new_keys = Counter((p, norm(d)) for p, n, d in new_entries)
removed = list((old_keys - new_keys).elements())
added = list((new_keys - old_keys).elements())
expected_removed = {
    ("luffy/deepscaler/utils.py", "Implement OpenAI API client initialization"),
    ("luffy/deepscaler/utils.py", "Add proper authentication handling"),
    ("luffy/deepscaler/utils.py", "Implement exponential backoff retry logic for rate limits"),
    ("luffy/deepscaler/utils.py", "Add comprehensive error handling for different API errors"),
    ("luffy/deepscaler/utils.py", "Implement response parsing and validation"),
    ("luffy/verl/verl/protocol.py", "Implement batch dimension folding for efficient processing"),
    ("luffy/verl/verl/protocol.py", "Add validation for batch size compatibility"),
    ("luffy/verl/verl/protocol.py", "Handle edge cases where batch_size is not divisible by new_batch_size"),
    ("luffy/verl/verl/protocol.py", "Implement batch dimension unfolding functionality"),
    ("luffy/verl/verl/protocol.py", "Add support for variable batch dimensions"),
    ("luffy/verl/verl/protocol.py", "Handle non-tensor batch data reshaping properly"),
}
assert len(removed) == 11 and set(removed) == expected_removed, removed
assert not added, added

expected_updates = {
    ("luffy/deepscaler/utils.py", "Add logging for API calls and errors"): (50, 45),
    ("luffy/deepscaler/utils.py", "Support batch processing for multiple prompts"): (51, 46),
    ("luffy/deepscaler/utils.py", "Add timeout configuration for API calls"): (52, 47),
    ("luffy/deepscaler/utils.py", "Implement Vertex AI initialization and authentication"): (88, 107),
    ("luffy/deepscaler/utils.py", "Configure safety settings for content generation"): (89, 108),
    ("luffy/deepscaler/utils.py", "Set up GenerativeModel with proper system instructions"): (90, 109),
    ("luffy/deepscaler/utils.py", "Implement retry logic with exponential backoff"): (91, 110),
    ("luffy/deepscaler/utils.py", "Add comprehensive error handling for API access issues"): (92, 111),
    ("luffy/deepscaler/utils.py", "Handle rate limiting and quota management"): (93, 112),
    ("luffy/deepscaler/utils.py", "Implement response validation and text extraction"): (94, 113),
    ("luffy/deepscaler/utils.py", "Add support for different generation configurations"): (95, 114),
    ("luffy/verl/verl/protocol.py", "Optimize memory usage during tensor reshaping"): (117, 114),
    ("luffy/verl/verl/protocol.py", "Add support for different tensor types and shapes"): (118, 115),
    ("luffy/verl/verl/protocol.py", "Optimize tensor view operations for performance"): (133, 136),
    ("luffy/verl/verl/protocol.py", "Add error handling for invalid batch dimensions"): (135, 137),
    ("luffy/verl/verl/protocol.py", "(zhangchi.usc1992) add consistency check"): (156, 169),
    ("luffy/verl/verl/protocol.py", "we can actually lift this restriction if needed"): (252, 265),
    ("luffy/verl/verl/protocol.py", "(zhangchi.usc1992) whether to copy"): (338, 351),
}
old_lines, new_lines = {}, {}
for p, n, d in old_entries:
    old_lines.setdefault((p, norm(d)), []).append(int(n))
for p, n, d in new_entries:
    new_lines.setdefault((p, norm(d)), []).append(int(n))
updates = {}
for key in sorted(set(old_lines) & set(new_lines)):
    if old_lines[key] != new_lines[key]:
        assert len(old_lines[key]) == len(new_lines[key]) == 1, key
        updates[key] = (old_lines[key][0], new_lines[key][0])
assert updates == expected_updates, updates

changed = {"luffy/deepscaler/utils.py", "luffy/verl/verl/protocol.py"}
old_other = [x for x in old_entries if x[0] not in changed]
new_other = [x for x in new_entries if x[0] not in changed]
assert old_other == new_other, "entries outside main-to-dev changed files were modified"

for rel in sorted(changed):
    code = []
    text = (pathlib.Path(repo_dir) / rel).read_text()
    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#") and "TODO" in line:
            match = re.search(r"#\s*TODO\b(.*)", line)
            code.append((i, norm(match.group(1))))
    readme = [(int(n), norm(d)) for p, n, d in new_entries if p == rel]
    assert code == readme, (rel, code, readme)

print("VALIDATED: %d -> %d entries; removed=11; added=0; line_updates=%d; source markers match" %
      (len(old_entries), len(new_entries), len(updates)))
