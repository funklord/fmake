# From running fmake on hydra, 2026-09-21

Written from `hydra`, a Qt Widgets browser, against `fmake 1.0 (5af02348)` as
installed at `/usr/bin/fmake` — which may lag this tree; the working copy here
was at `06d2c26` when this was written. The previous report from this project
was folded in and removed in `d1928f4`.

Re-run because hydra's README carried a line saying `fmake -C src -j2` builds
the tree, and this workspace's `harmonization.md` says such a line is to be run
before it is written.

## It builds the tree now, and both earlier blockers are closed

- **Platform-conditional sources.** The last report had fmake scheduling all
  four of hydra's `android_*.cpp` and dying on `QJniEnvironment`. It excludes
  them itself now, and says so: *"4 sources named for another platform
  (android_dialogs.cpp, ...) not built for linux/x86_64"*.
- **Optional dependencies.** Answered by the six `@pkg_optional` annotations
  hydra has since added.

136 of 136 compiled, linked, `* built hydra`. With no build file.

## What stopped it was ours, and fmake had already thought of it

`hydra.pro` passes `-DHYDRA_VERSION="<the VERSION file>"`. `main.cpp` read the
macro unguarded, so the run ended with one error:

    main.cpp:91: error: 'HYDRA_VERSION' was not declared in this scope

The first draft of this report asked fmake for a way to take a define's value
from a file, on the grounds that `@define` takes a literal and putting the
number in a source is exactly what a `VERSION` file exists to prevent. **That
request was wrong and is withdrawn before sending.** `version_fallbacks`
already covers this: a macro with `VERSION` as a component of its name, guarded
by `#ifndef`, defined to a string literal. hydra carries the guard now and the
build finishes.

## The finding: that report cannot fire for this tree's layout

The check reads

    open(os.path.join(root, "VERSION"))

so it needs the `VERSION` file in the **build root**. hydra's sources are in
`src/` and its `VERSION` is at the repository root, one level up — which is the
layout the invocation `fmake -C src` describes. Measured both ways, same tree,
same commit:

    VERSION copied into src/     main.cpp defines HYDRA_VERSION itself because
                                 the build did not, so this binary reports a
                                 version it made up
                                 VERSION here says 0.1; [project] cflags =
                                 ['-DHYDRA_VERSION="0.1"'] supplies it

    VERSION where it lives       nothing

The first is exactly the right output — the finding and its remedy in two
lines. The second is what hydra actually gets, and it is why a binary that
reports a version it made up went unnoticed here until the compile error forced
the question.

**Stated as an option, its cost, and whose it is:**

- **The option.** Let the `VERSION` lookup climb above the build root — or
  take the project root separately from the directory being built.
- **The cost.** Climbing out of the build root is a new kind of reach for a
  tool whose whole claim is that it reads the tree in front of it, and a
  `VERSION` two directories up may belong to something else entirely. A
  depth limit, or stopping at a `.git`, would bound it; both are decisions
  about what "the project" means, which fmake has so far deliberately kept
  to one directory.
- **Whose decision.** fmake's. This is a measurement and a constraint, not a
  request. hydra is unblocked either way — the guard is in, the build works,
  and the README says what a binary built this way reports.

**And it may be worth nothing.** A project whose `VERSION` sits beside its
sources already gets the report, and hydra's layout may be the unusual one.
The number of trees where `fmake -C <subdir>` is the documented invocation is
the thing that decides it, and that is visible from here and not from hydra.

## Notes for re-taking it

    fmake -C src -j2        # from hydra's repository root
    fmake -C src --clean    # removes .fmake/, 12 MB here

The dry run (`-n`) exits 0 and resolves no libraries, so neither the error nor
the version report shows there; both need a real compile.
