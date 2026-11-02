"""Find the change that breaks the syntax in the scope pass."""
from __future__ import annotations

import sys

sys.path.insert(0, "/home/user/formatter")

import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()

lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)

nested: set[int] = set()
sibling: set[int] = set()
escaped: set[int] = set()
clause_of: dict[int, int] = {}


def attempt():
    levels = indenter.run(nested, clause_of, sibling, escaped)
    text, mapping = rp.render_with_map(lines, levels)
    return levels, rp.check_syntax(text), mapping, text


levels, error, _mapping, text = attempt()
print("base error:", error)
if error is not None:
    raise SystemExit(1)

score = len(rp.undefined_names(text))
print("base score:", score)

# Walk through the decisions the same way the scope pass does.
for decision in list(indenter.decisions):
    was_nested = decision in nested
    if was_nested:
        nested.discard(decision)
        sibling.add(decision)
    else:
        sibling.discard(decision)
        nested.add(decision)
    trial_levels = indenter.run(nested, clause_of, sibling, escaped)
    trial_text = rp.render(lines, trial_levels)
    trial_error = rp.check_syntax(trial_text)
    if trial_error is None:
        try:
            trial_score = len(rp.undefined_names(trial_text))
        except SyntaxError:
            trial_score = None
    else:
        trial_score = None
    if trial_score is not None and trial_score < score:
        score = trial_score
        print(f"  accept {decision} -> {score}")
    else:
        if was_nested:
            nested.discard(decision)
            sibling.add(decision)
        else:
            sibling.discard(decision)
            nested.add(decision)

levels, error, _mapping, text = attempt()
print("after decision sweep, error:", error)
if error is not None:
    lineno = error.lineno or 1
    for number, line in enumerate(text.splitlines()[lineno - 4 : lineno + 3], lineno - 3):
        print(f"   {number:5d} {line!r}")
