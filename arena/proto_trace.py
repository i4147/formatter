"""Trace the iterative search: which index fails, which moves are tried."""
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
budget = 300
trace = []

def attempt_error():
    levels = indenter.run(nested, clause_of)
    return levels, rp.check_syntax(rp.render(lines, levels))

def failing_index(error):
    if "except" in error.msg and "finally" in error.msg:
        for index, ll in enumerate(lines):
            if error.lineno in ll.physical:
                for j in range(index - 1, -1, -1):
                    if lines[j].is_code and lines[j].head == "try":
                        return j
                return index
    for index, ll in enumerate(lines):
        if error.lineno in ll.physical:
            return index
    return len(lines) - 1

def candidates_for(index):
    if lines[index].is_code and lines[index].head in rp.CLAUSE_KEYWORDS:
        return [("clause", index, c) for c in rp._clause_candidates(lines, indenter, index)]
    if lines[index].is_code and lines[index].head == "try":
        return [("try", index, c) for c in rp._clauses_after(lines, indenter, index)]
    return [("nested", d, 0) for d in reversed(indenter.decisions) if d <= index]

stack = []
t0 = time.time()
while True:
    budget -= 1
    if budget <= 0:
        print("budget exhausted")
        break
    levels, error = attempt_error()
    if error is None:
        print("SUCCESS")
        break
    index = failing_index(error)
    moves = [m for m in candidates_for(index) if m not in tried]
    trace.append((index, lines[index].head if lines[index].is_code else "", error.msg[:60], len(moves)))
    if len(trace) > 40:
        break
    if not moves:
        while stack:
            frame = stack[-1]
            move, alts = frame
            if alts:
                frame[1] = alts[1:]
                if move[0] == "clause":
                    clause_of.pop(move[1], None)
                elif move[0] == "try":
                    clause_of.pop(move[2], None)
                else:
                    nested.discard(move[1])
                nxt = alts[0]
                tried.add(nxt)
                if nxt[0] == "clause":
                    clause_of[nxt[1]] = nxt[2]
                elif nxt[0] == "try":
                    clause_of[nxt[2]] = nxt[1]
                else:
                    nested.add(nxt[1])
                stack[-1] = [nxt, frame[1]]
                break
            stack.pop()
            if move[0] == "clause":
                clause_of.pop(move[1], None)
            elif move[0] == "try":
                clause_of.pop(move[2], None)
            else:
                nested.discard(move[1])
        else:
            print("no solution")
            break
        continue
    first = moves[0]
    tried.add(first)
    if first[0] == "clause":
        clause_of[first[1]] = first[2]
    elif first[0] == "try":
        clause_of[first[2]] = first[1]
    else:
        nested.add(first[1])
    stack.append([first, list(moves[1:])])

for t in trace:
    print(t)
print("t=%.1fs nested=%d clause_of=%d" % (time.time()-t0, len(nested), len(clause_of)))
