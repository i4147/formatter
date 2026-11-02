"""Greedy forward pass over both nesting decisions and clause ownership."""
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


def clause_candidates(index):
    ll = lines[index]
    if not ll.is_code:
        return []
    if ll.head in rp.CLAUSE_KEYWORDS:
        return rp._clause_candidates(lines, indenter, index)
    if ll.head == "try":
        return rp._clauses_after(lines, indenter, index)
    return []


t0 = time.time()
levels, error, mapping = attempt()
baseline = failing_index(error, mapping)
print("start error idx:", baseline, error)

rounds = 0
while error is not None and rounds < 30:
    rounds += 1
    changed = False

    # 1. Clause ownership for the failing clause / try.
    ll = lines[baseline]
    if ll.is_code and (ll.head in rp.CLAUSE_KEYWORDS or ll.head == "try"):
        if ll.head in rp.CLAUSE_KEYWORDS:
            cands = rp._clause_candidates(lines, indenter, baseline)
        else:
            cands = rp._clauses_after(lines, indenter, baseline)
        print(f"  round {rounds}: clause {baseline} ({ll.head}) candidates {cands[:8]}")
        for cand in cands:
            clause_of[baseline] = cand
            lv = indenter.run(nested, clause_of)
            text, m = rp.render_with_map(lines, lv)
            err = rp.check_syntax(text)
            if err is None:
                error = None
                print("SOLVED")
                break
            idx = failing_index(err, m)
            if idx > baseline:
                print(f"    -> owner {cand} advances to {idx}")
                baseline = idx
                changed = True
                break
            del clause_of[baseline]
        if error is None:
            break

    # 2. Nesting decisions.
    for decision in list(indenter.decisions):
        if decision in nested or decision > baseline:
            continue
        nested.add(decision)
        lv = indenter.run(nested, clause_of)
        text, m = rp.render_with_map(lines, lv)
        err = rp.check_syntax(text)
        if err is None:
            error = None
            print("SOLVED")
            break
        idx = failing_index(err, m)
        nested.discard(decision)
        if idx > baseline:
            nested.add(decision)
            baseline = idx
            changed = True
            print(f"  round {rounds}: nested {decision} -> baseline {baseline}")
    if error is None:
        break
    if not changed:
        print(f"  round {rounds}: no progress, baseline {baseline}, err {error}")
        break

print("t=%.1fs nested=%d clauses=%s" % (time.time() - t0, len(nested), clause_of))
if error is not None:
    print("final error:", error, "idx", baseline)
    for i in range(max(0, baseline - 8), min(len(lines), baseline + 6)):
        print(f"{i:5d} L{indenter.levels[i]:2d} {lines[i].head!r:12s} {lines[i].texts[0][:60]}")
