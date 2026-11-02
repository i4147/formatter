# Helper scripts

The scripts in this folder are the tools that were used while
`reformat_python.py` was written.  They are not needed to run the
formatter; they document how the reconstruction was checked.

## The checks that matter

* `proto_check.py` -- the main check.  It verifies that the result is
  parsable Python, that the token stream is unchanged (the formatter may
  only move the indentation) and it reports the names that are read
  before they are bound.

      python3 arena/proto_check.py broken.py /tmp/result.py

* `proto_validate.py` -- a syntax check that also works for Python 3.12
  syntax on an older interpreter.  The `type X = ...` syntax is rewritten
  before the file is parsed.

* `proto_scope.py` -- the scope oracle.  It walks the syntax tree with a
  scope stack and reports every name that is read before it is bound.
  Of the many readings of a flattened file the one that leaves no name
  unbound is the right one.

* `proto_regions.py` -- groups the unbound names of a result by the
  function they appear in.  It shows where a reading went wrong.

## The diagnostics

The `proto_*.py` scripts that are not mentioned above are the
experiments that led to the rules in the formatter:

* `proto_frames*.py`, `proto_clause.py`, `proto_struct.py` -- show the
  stack of open suites while the file is reconstructed.
* `proto_greedy*.py` -- the greedy pass that decides one ambiguity after
  the other.
* `proto_scope_pass.py`, `proto_scope_bug.py`, `proto_scope_debug.py` --
  the scope pass and the search for the change that broke the syntax.
* `proto_3109.py`, `proto_levels.py`, `proto_inspect*.py` -- look at
  single regions of the file.
* `apply_greedy.py`, `apply_greedy2.py` -- patches that replaced the
  search in `reformat_python.py` while it was written.

## A note on the runtime

Reconstructing the indentation of `broken.py` takes a few minutes: the
search parses the whole file thousands of times, because every reading
of the file has to be checked.
