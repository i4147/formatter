"""Replace the search block of reformat_python.py with the greedy pass."""
import re
import sys

PATH = "/home/user/formatter/reformat_python.py"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

start_marker = "    def greedy_pass() -> bool:"
end_marker = "\n\ndef main(argv: Sequence[str] | None = None) -> int:"

start = text.index(start_marker)
end = text.index(end_marker)

NEW = '''    def greedy_pass() -> bool:
        """Repair the file by deciding one ambiguity after the other.

        The ambiguities are visited in the order in which they appear in
        the file.  For every one of them both possibilities are tried: the
        block header either opens a *nested* suite or starts a new suite
        *next to* the enclosing one; a clause keyword either continues the
        construct in front of it or one of the constructs further up.

        The possibility that moves the first syntax error further into the
        file wins.  When neither possibility does, the more common one --
        the sibling suite -- is kept.

        Working through the file from the front keeps the number of parses
        small: an ambiguity that comes after the first error cannot change
        it, so it is not tried at all.  The whole file is parsed after
        every step, which makes the procedure quadratic in the number of
        ambiguities -- but with a very small constant, because only the
        *first* error is looked at.
        """
        while True:
            levels, error, mapping = attempt_error()
            if error is None:
                return True
            baseline = failing_index(error, mapping)

            changed = False

            # -- the clause that could not be attached ------------------
            ll = lines[baseline]
            if ll.is_code and ll.head in CLAUSE_KEYWORDS:
                for candidate in _clause_candidates(lines, indenter, baseline):
                    previous = clause_of.get(baseline)
                    clause_of[baseline] = candidate
                    trial_levels = indenter.run(nested, clause_of)
                    text, trial_mapping = render_with_map(lines, trial_levels)
                    trial_error = check_syntax(text)
                    if trial_error is None:
                        return True
                    trial_index = failing_index(trial_error, trial_mapping)
                    if trial_index > baseline:
                        changed = True
                        baseline = trial_index
                        break
                    if previous is None:
                        clause_of.pop(baseline, None)
                    else:
                        clause_of[baseline] = previous

            if changed:
                continue

            # -- a try that misses its except/finally -------------------
            ll = lines[baseline]
            if ll.is_code and ll.head == "try":
                for clause in _clauses_after(lines, indenter, baseline):
                    previous = clause_of.get(clause)
                    clause_of[clause] = baseline
                    trial_levels = indenter.run(nested, clause_of)
                    text, trial_mapping = render_with_map(lines, trial_levels)
                    trial_error = check_syntax(text)
                    if trial_error is None:
                        return True
                    trial_index = failing_index(trial_error, trial_mapping)
                    if trial_index > baseline:
                        changed = True
                        baseline = trial_index
                        break
                    if previous is None:
                        clause_of.pop(clause, None)
                    else:
                        clause_of[clause] = previous

            if changed:
                continue

            # -- a block header on the wrong level ----------------------
            for decision in list(indenter.decisions):
                if decision in nested or decision > baseline:
                    continue
                nested.add(decision)
                trial_levels = indenter.run(nested, clause_of)
                text, trial_mapping = render_with_map(lines, trial_levels)
                trial_error = check_syntax(text)
                if trial_error is None:
                    return True
                trial_index = failing_index(trial_error, trial_mapping)
                nested.discard(decision)
                if trial_index > baseline:
                    # The nested suite moves the error forward: keep it.
                    nested.add(decision)
                    baseline = trial_index
                    changed = True
                    break

            if not changed:
                return False

    levels, error, _mapping = attempt_error()
    if error is not None and not greedy_pass():
        # The greedy pass got stuck: fall back to the exhaustive search,
        # which explores the remaining possibilities.
        if not _exhaustive_search():
            raise ReformatError(
                "could not find an indentation that produces valid Python"
            )

    levels, error, _mapping = attempt_error()
    if error is not None:
        raise ReformatError(
            "could not find an indentation that produces valid Python"
        )
    return render(lines, levels)

    def _exhaustive_search() -> bool:
        """Try every remaining combination of decisions.

        The search is iterative on purpose: a recursive version keeps one
        rendered copy of the file per level on the Python stack, which
        runs out of memory on a file of this size.  The explicit stack
        below only stores the small move lists.
        """
        tried: set[tuple] = set()

        def candidates_for(index: int) -> list[tuple]:
            """The moves that could repair the failure at *index*."""
            if lines[index].is_code and lines[index].head in CLAUSE_KEYWORDS:
                return [
                    ("clause", index, candidate)
                    for candidate in _clause_candidates(lines, indenter, index)
                ]
            if lines[index].is_code and lines[index].head == "try":
                return [
                    ("try", index, clause)
                    for clause in _clauses_after(lines, indenter, index)
                ]
            return [
                ("nested", decision, 0)
                for decision in reversed(indenter.decisions)
                if decision <= index
            ]

        def apply_move(move: tuple) -> bool:
            """Perform *move*; return ``False`` when it does not help."""
            kind, first, second = move
            if kind == "clause":
                clause, construct = first, second
                previous = clause_of.get(clause)
                clause_of[clause] = construct
                trial_levels = indenter.run(nested, clause_of)
                if _clause_region_ok(lines, indenter, trial_levels, clause, construct):
                    return True
                if previous is None:
                    clause_of.pop(clause, None)
                else:
                    clause_of[clause] = previous
                return False
            if kind == "try":
                try_index, clause = first, second
                previous = clause_of.get(clause)
                clause_of[clause] = try_index
                trial_levels = indenter.run(nested, clause_of)
                if _region_parses(lines, trial_levels, try_index, clause):
                    return True
                if previous is None:
                    clause_of.pop(clause, None)
                else:
                    clause_of[clause] = previous
                return False
            nested.add(first)
            return True

        def undo_move(move: tuple) -> None:
            kind, first, second = move
            if kind == "clause":
                clause_of.pop(first, None)
            elif kind == "try":
                clause_of.pop(second, None)
            else:
                nested.discard(first)

        # Each stack frame is a two element list: the move that led here
        # and the moves that have not been tried yet.
        stack: list[list] = []

        while True:
            levels, error, mapping = attempt_error()
            if error is None:
                return True
            index = failing_index(error, mapping)
            moves = [
                move
                for move in candidates_for(index)
                if move not in tried
            ]

            if not moves:
                # This state is a dead end: undo the move that led here
                # and continue with the next alternative of the parent.
                while stack:
                    frame = stack[-1]
                    move = frame[0]
                    alternatives = frame[1]
                    if alternatives:
                        frame[1] = alternatives[1:]
                        undo_move(move)
                        next_move = alternatives[0]
                        tried.add(next_move)
                        if apply_move(next_move):
                            stack[-1] = [next_move, frame[1]]
                        break
                    stack.pop()
                    undo_move(move)
                else:
                    return False
                continue

            first = moves[0]
            tried.add(first)
            if not apply_move(first):
                continue
            stack.append([first, list(moves[1:])])
'''

text = text[:start] + NEW + text[end:]

with open(PATH, "w", encoding="utf-8") as fh:
    fh.write(text)

print("replaced", end - start, "characters")
