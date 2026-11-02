"""Trace the search with the corrected rendered-line -> logical-line map."""
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
budget = 200
trace = []


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
        if "except" in error.msg and "finally" in error.msg:
            for j in range(len(lines) - 1, -1, -1):
                if lines[j].is_code and lines[j].head == "try":
                    return j
        return len(lines) - 1
    if "except" in error.msg and "finally" in error.msg:
        for j in range(index - 1, -1, -1):
            if lines[j].is_code and lines[j].head == "try":
                return j
    return index


def candidates_for(index):
    if lines[index].is_code and lines[index].head in rp.CLAUSE_KEYWORDS:
        return [("clause", index, c)
                for c in rp._clause_candidates(lines, indenter, index)]
    if lines[index].is_code and lines[index].head == "try":
        return [("try", index, c)
                for c in rp._clauses_after(lines, indenter, index)]
    return [("nested", d, 0)
            for d in reversed(indenter.decisions) if d <= index]


stack = []
t0 = time.time()
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
    moves = [m for m in candidates_for(index) if m not in tried]
    trace.append((index,
                  lines[index].head if lines[index].is_code else "",
                  error.msg[:60],
                  len(moves)))
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
