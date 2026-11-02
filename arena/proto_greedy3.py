"""Trace the greedy pass: print every step."""
import sys
import time

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)

nested = set()
clause_of = {}


def attempt():
    levels = indenter.run(nested, clause_of)
    text, mapping = rp.render_with_map(lines, levels)
    return levels, rp.check_syntax(text), mapping


def failing_index(error, mapping):
    lineno = error.lineno or 0
    index = None
    if 1 <= lineno <= len(mapping):
        c = mapping[lineno - 1]
        if c >= 0:
            index = c
    if index is None:
        return len(lines) - 1
    if "except" in error.msg and "finally" in error.msg:
        for j in range(index - 1, -1, -1):
            if lines[j].is_code and lines[j].head == "try":
                return j
    return index


t0 = time.time()
steps = 0
while True:
    levels, error, mapping = attempt()
    if error is None:
        print("SOLVED")
        break
    baseline = failing_index(error, mapping)
    changed = False

    ll = lines[baseline]
    if ll.is_code and ll.head in rp.CLAUSE_KEYWORDS:
        for candidate in rp._clause_candidates(lines, indenter, baseline):
            clause_of[baseline] = candidate
            lv = indenter.run(nested, clause_of)
            text, m = rp.render_with_map(lines, lv)
            err = rp.check_syntax(text)
            if err is None:
                print("SOLVED")
                sys.exit(0)
            idx = failing_index(err, m)
            if idx > baseline:
                print(f"clause {baseline} -> owner {candidate} : baseline {baseline} -> {idx}")
                baseline = idx
                changed = True
                break
            clause_of.pop(baseline, None)
    if changed:
        continue

    ll = lines[baseline]
    if ll.is_code and ll.head == "try":
        for clause in rp._clauses_after(lines, indenter, baseline):
            clause_of[clause] = baseline
            lv = indenter.run(nested, clause_of)
            text, m = rp.render_with_map(lines, lv)
            err = rp.check_syntax(text)
            if err is None:
                print("SOLVED")
                sys.exit(0)
            idx = failing_index(err, m)
            if idx > baseline:
                print(f"try {baseline} -> clause {clause} : baseline -> {idx}")
                baseline = idx
                changed = True
                break
            clause_of.pop(clause, None)
    if changed:
        continue

    for decision in list(indenter.decisions):
        if decision in nested or decision > baseline:
            continue
        nested.add(decision)
        lv = indenter.run(nested, clause_of)
        text, m = rp.render_with_map(lines, lv)
        err = rp.check_syntax(text)
        if err is None:
            print("SOLVED")
            sys.exit(0)
        idx = failing_index(err, m)
        nested.discard(decision)
        if idx > baseline:
            nested.add(decision)
            baseline = idx
            changed = True
            print(f"nested {decision} : baseline -> {idx}")
            break
    if not changed:
        print(f"STUCK at baseline {baseline}, err={error}")
        break
    steps += 1

print("t=%.1fs steps=%d nested=%s clauses=%s" % (
    time.time() - t0, steps, sorted(nested), clause_of))
if error is not None:
    for i in range(max(0, baseline - 14), min(len(lines), baseline + 8)):
        print(f"{i:5d} L{indenter.levels[i]:2d} {lines[i].head!r:12s} {lines[i].texts[0][:62]}")
