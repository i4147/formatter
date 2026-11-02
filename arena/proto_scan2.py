"""Trace the internals of _chain_is_continued."""
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

src = open("/home/user/formatter/broken.py").read()
lines = rp._logical_lines(src)
ind = rp.Indenter(lines)

# Re-implement the scanner with prints, mirroring the current source.
def scan(index):
    stack = []
    owner = None
    for j in range(index, len(lines)):
        ll = lines[j]
        if not ll.is_code:
            continue
        head = ll.head
        if head in rp.CLAUSE_KEYWORDS:
            print(f"  j={j} CLAUSE {head!r} stack={stack} owner={owner}")
            if not stack:
                continue
            barrier = None
            for position in range(len(stack) - 1, -1, -1):
                if stack[position].rstrip("*!") in rp.DEFINITION_KEYWORDS:
                    barrier = position
                    break
            start = owner if owner is not None else len(stack) - 1
            while stack:
                position = min(start, len(stack) - 1)
                innermost = stack[position]
                closed = innermost.endswith("!")
                marked = innermost.endswith("*")
                keyword = innermost.rstrip("*!")
                inside_definition = barrier is not None and position > barrier
                if (not closed and not inside_definition
                        and rp._accepts_clause(keyword, head)):
                    print(f"      -> match at pos {position} kw={keyword!r}")
                    if marked:
                        return True
                    del stack[position + 1:]
                    stack[position] = keyword
                    if head in ("else", "finally"):
                        stack[position] += "!"
                    owner = position
                    break
                print(f"      -> pop pos {position} kw={keyword!r} closed={closed} "
                      f"inside_def={inside_definition}")
                if position < len(stack) - 1:
                    del stack[position + 1:]
                stack.pop()
                owner = None
                if marked:
                    return False
                start = min(start, len(stack) - 1)
            continue
        keyword = ind._keyword_of(ll)
        if ll.opens_block and not ll.inline_suite:
            if keyword in rp.DEFINITION_KEYWORDS:
                while stack:
                    innermost = stack[-1]
                    marked = innermost.endswith("*")
                    if innermost.rstrip("*!") in rp.DEFINITION_KEYWORDS:
                        break
                    if marked:
                        break
                    stack.pop()
            stack.append(keyword + ("*" if j == index else ""))
            owner = len(stack) - 1
        elif ll.opens_block:
            owner = len(stack) - 1
        else:
            owner = len(stack) - 1
            if keyword in rp.TERMINATORS and stack:
                innermost = stack[-1]
                if innermost.endswith("*"):
                    return False
                stack.pop()
                owner = len(stack) - 1
    return False


print("scan(738) =", scan(738))
