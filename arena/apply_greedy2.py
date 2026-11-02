"""Replace the greedy pass with a cursor based, single pass version."""
import re

PATH = "/home/user/formatter/reformat_python.py"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

start_marker = "    def greedy_pass() -> bool:"
end_marker = "\n    levels, error, _mapping = attempt_error()"

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
        file wins.  When neither possibility does, the more likely one --
        the nested suite -- is kept.

        Working through the file from the front keeps the number of parses
        small: an ambiguity that comes after the first error cannot change
        it, so it is not tried at all.  The whole file is parsed after
        every step, which makes the procedure quadratic in the number of
        ambiguities -- but with a very small constant, because only the
        *first* error is looked at.
        """
        # The decisions that have been looked at already.  The cursor
        # makes sure that every decision is tried at most once per round.
        cursor = 0

        while True:
            levels, error, mapping = attempt_error()
            if error is None:
                return True
            baseline = failing_index(error, mapping)

            changed = False

            # -- a try that misses its except/finally -------------------
            # "expected 'except' or 'finally' block" points at the
            # statement behind the ``try``; the construct that misses its
            # clause is the ``try`` in front of it.
            if "except" in error.msg and "finally" in error.msg:
                try_index = None
                for j in range(baseline - 1, -1, -1):
                    if lines[j].is_code and lines[j].head == "try":
                        try_index = j
                        break
                if try_index is not None:
                    for clause in _clauses_after(lines, indenter, try_index):
                        previous = clause_of.get(clause)
                        clause_of[clause] = try_index
                        trial_levels = indenter.run(
                            nested, clause_of, sibling
                        )
                        text, trial_mapping = render_with_map(lines, trial_levels)
                        trial_error = check_syntax(text)
                        if trial_error is None:
                            return True
                        trial_index = error_position(trial_error, trial_mapping)
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

            # -- the clause that could not be attached ------------------
            ll = lines[baseline]
            if ll.is_code and ll.head in CLAUSE_KEYWORDS:
                # The construct the clause belongs to is normally found by
                # the rules of the language: the innermost open construct
                # that accepts the clause.  That choice is tried first --
                # it is the one that reproduces the original indentation
                # in the overwhelming majority of the cases.
                candidates = _clause_candidates(lines, indenter, baseline)
                default = indenter.clause_targets.get(baseline)
                if default is not None and default in candidates:
                    candidates.remove(default)
                    candidates.insert(0, default)
                for candidate in candidates:
                    previous = clause_of.get(baseline)
                    clause_of[baseline] = candidate
                    trial_levels = indenter.run(nested, clause_of, sibling)
                    text, trial_mapping = render_with_map(lines, trial_levels)
                    trial_error = check_syntax(text)
                    if trial_error is None:
                        return True
                    trial_index = error_position(trial_error, trial_mapping)
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

            # -- a block header on the wrong level ----------------------
            # The header either opens a nested suite or starts a new suite
            # next to the enclosing one.  The nested suite is the default;
            # it is only given up when the sibling suite brings the first
            # error further into the file.
            decisions = indenter.decisions
            while cursor < len(decisions):
                decision = decisions[cursor]
                cursor += 1
                if decision > baseline:
                    # The header comes after the error; it cannot help
                    # yet.  It is looked at again in the next round.
                    cursor -= 1
                    break
                if decision in sibling:
                    # The sibling suite is already chosen; try the nested
                    # one instead.
                    sibling.discard(decision)
                    nested.add(decision)
                    trial_levels = indenter.run(nested, clause_of, sibling)
                    text, trial_mapping = render_with_map(lines, trial_levels)
                    trial_error = check_syntax(text)
                    if trial_error is None:
                        return True
                    trial_index = error_position(trial_error, trial_mapping)
                    nested.discard(decision)
                    if trial_index > baseline:
                        nested.add(decision)
                        baseline = trial_index
                        changed = True
                        break
                    sibling.add(decision)
                    continue

                # The nested suite is in place; try the sibling suite.
                sibling.add(decision)
                trial_levels = indenter.run(nested, clause_of, sibling)
                text, trial_mapping = render_with_map(lines, trial_levels)
                trial_error = check_syntax(text)
                if trial_error is None:
                    return True
                trial_index = error_position(trial_error, trial_mapping)
                sibling.discard(decision)
                if trial_index > baseline:
                    # The sibling suite moves the error forward: keep it.
                    sibling.add(decision)
                    baseline = trial_index
                    changed = True
                    break

            if changed:
                continue

            if cursor >= len(decisions):
                # Every decision has been looked at and none of them
                # brings the file closer to a valid program.
                return False
'''

text = text[:start] + NEW + text[end:]

with open(PATH, "w", encoding="utf-8") as fh:
    fh.write(text)

print("replaced", end - start, "characters")
