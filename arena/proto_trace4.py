"""Trace the search with progress pruning, showing the failure sequence."""
import sys
import time

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)

nested = set()
clause_of = {}
tried = set()
budget = 2000
trace = []


def attempt_error():
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


def reported_index(error, mapping):
    lineno = error.lineno or 0
    if 1 <= lineno <= len(mapping):
        return mapping[lineno - 1]
    return 0


def next_code(start):
    for i in range(start, len(lines)):
        if lines[i].is_code:
            return i
    return None


def candidates_for(index, error, mapping):
    message = error.msg
    if "expected an indented block" in message:
        reported = reported_index(error, mapping)
        if lines[reported].is_code and lines[reported].head in rp.DEFINITION_KEYWORDS:
            following = next_code(reported + 1)
            if following is not None and following in indenter.decisions:
                return [("nested", following, 0)]
            return [("nested", reported, 0)]
    if lines[index].is_code and lines[index].head in rp.CLAUSE_KEYWORDS:
        return [("clause", index, c)
                for c in rp._clause_candidates(lines, indenter, index)]
    if lines[index].is_code and lines[index].head == "try":
        return [("try", index, c)
                for c in rp._clauses_after(lines, indenter, index)]
    return [("nested", d, 0) for d in reversed(indenter.decisions)
            if index - 40 <= d <= index]


def apply(m):
    if m[0] == "clause":
        clause_of[m[1]] = m[2]
    elif m[0] == "try":
        clause_of[m[2]] = m[1]
    else:
        nested.add(m[1])


def undo(m):
    if m[0] == "clause":
        clause_of.pop(m[1], None)
    elif m[0] == "try":
        clause_of.pop(m[2], None)
    else:
        nested.discard(m[1])


def makes_progress(m, index):
    apply(m)
    try:
        levels = indenter.run(nested, clause_of)
        text, mapping = rp.render_with_map(lines, levels)
        err = rp.check_syntax(text)
    finally:
        undo(m)
    if err is None:
        return True
    return failing_index(err, mapping) > index


stack = []
t0 = time.time()
prev_index = -1
while True:
    budget -= 1
    if budget <= 0:
        print("budget exhausted")
        break
    levels, error, mapping = attempt_error()
    if error is None:
        print("SUCCESS")
        break
    index = failing_index(error, mapping)
    raw = [m for m in candidates_for(index, error, mapping) if m not in tried]
    moves = [m for m in raw if makes_progress(m, index)]
    trace.append((index, lines[index].head if lines[index].is_code else "",
                  error.msg[:50], len(raw), len(moves)))
    if not moves:
        while stack:
            frame = stack[-1]
            move, alts = frame
            if alts:
                frame[1] = alts[1:]
                undo(move)
                nxt = alts[0]
                tried.add(nxt)
                apply(nxt)
                stack[-1] = [nxt, frame[1]]
                break
            stack.pop()
            undo(move)
        else:
            print("no solution")
            break
        continue
    first = moves[0]
    tried.add(first)
    apply(first)
    stack.append([first, list(moves[1:])])

for t in trace:
    print(t)
print("t=%.1fs nested=%d clause_of=%d" % (time.time() - t0, len(nested), len(clause_of)))
