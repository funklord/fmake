# fmake, from a project that evaluated it and did not adopt it

Written 2026-08-04 from `netcfgd`, which has two C/C++ directories that are
exactly what fmake is for: `client/` (a C library plus a test binary, built by
an 89-line hand-written Makefile) and `gui/` (Qt Widgets, qmake).

fmake was run, not read about. The verdict was **no**, and the reason is one
missing capability rather than anything wrong with the tool. This file is what
that looked like from outside.

## What worked, with nothing configured

Copied `client/` to a scratch directory, deleted the Makefile, ran `fmake`:

```
[1/3] CC  ncfg_client.c
[2/3] CC  ncfg_json.c
[3/3] CC  tests/client_test.c
LD  client_test
* built client_test
```

It found the sources, found `main()` in the test, compiled and linked. That is
the promise on the README and it is kept. No annotation, no file, no flags.

## The one thing that decided it: no static library

`client/` exists to produce `libncfg_client.a`. `gui/` links it. That archive
*is* the deliverable — the C directory is a library with a test beside it, not
a program.

fmake linked the library sources **into the test binary** and produced no
archive. `--help` offers `--no-libs`, which is about resolving external symbols
to system libraries, and nothing that says "these translation units are a
library others link".

This is not a small gap for the projects most likely to try fmake. A tree with
one `main()` is already served by a two-line Makefile; the trees where a build
system is genuinely annoying are the ones with **a library, one or more
programs, and tests linking the library**. That shape is where fmake would earn
its place, and it is the shape it currently cannot express.

The symbol analysis fmake already does looks like most of the way there: a
translation unit that defines `main()` is a program, and the set of units *no*
program's symbols reach — or the units reached by more than one — is a
recognisable archive. A `--lib NAME` flag would also do, at the cost of the
annotation-free promise.

**Suggestion:** treat "library plus consumers" as a first-class inferred
output, or say plainly in the README that fmake builds programs. Either is
fine; the current position is that a reader infers library support from "builds
C and C++ from an unannotated tree" and finds out by running it.

## Three project-specific facts a zero-config builder cannot know

None of these is a defect. They are the reason a *correct* hand-written
Makefile survives contact with a good generator, and they might be worth a
paragraph in the README, because they are the honest answer to "why would
anyone keep their Makefile".

1. **A flag-stamp file.** `client/` has `.build-flags`, a file containing the
   compiler and flags, which every object depends on. It exists because
   `make SANITIZE=1 test` followed by a plain build in `gui/` linked a
   sanitized archive into a binary with no sanitizer runtime — forty lines of
   `__asan_report_store1` at link time and no clue why. Changing flags is not
   changing a source file, and nothing in the file tree records that it
   happened.

   This is a general problem, not a local one: **any** builder that caches
   objects has it. If fmake keys its object cache on flags already, say so —
   it is a real advantage over a naive Makefile and nobody would guess it. If
   it does not, that is a stale-object bug waiting in every project that
   switches compilers or adds a sanitizer.

2. **Build toggles with agreed semantics.** `DEBUG` and `SANITIZE` are tested
   for being *set*, never for a value, and are given no default anywhere,
   because a default would make them permanently set and impossible to turn
   off. That convention is shared across a family of sibling projects so that
   moving between trees costs nothing. A generator has no way to know that, and
   `CFLAGS=...` on the command line is not the same affordance.

3. **A test that takes an argument.** `make test` runs
   `./tests/client_test ../docs/schema/socket.json` — the test reads the
   daemon's frozen protocol witness, which is the entire reason it exists. A
   test runner that can only invoke a binary bare cannot express it.

   This one may be worth acting on: "the test binary needs arguments, a working
   directory, or an environment variable" is common enough that a project with
   real tests will hit it immediately, and it is a smaller feature than the
   library one.

## Qt

`gui/` was not evaluated in any depth: Qt Widgets needs `moc` run over headers
carrying `Q_OBJECT` before anything compiles, and fmake makes no claim there. If
Qt is ever in scope, `moc`/`uic`/`rcc` are a source-generation step whose outputs
then re-enter the normal graph — worth knowing that a project can be 90% plain
C++ and still be out of reach for that one reason.

## What the evaluation was worth even though the answer was no

It sent someone to read `client/Makefile` against the dependency-tracking rules
this family treats as load-bearing, and to *test* them rather than read them.
They hold — but the first measurement said they did not, because `stat` reports
whole seconds and the rebuild had landed inside one. Nanosecond timestamps
settled it.

That is the argument for running an evaluation you expect to decline: the
comparison is what makes anybody look hard at the thing they already have.

## Meta

If more of these accumulate here, the useful shape is probably one file per
evaluating project rather than per author — what a real tree needed, and which
of its needs were structural rather than habit. The three facts above look like
excuses for keeping a Makefile until you notice that two of them (flag
staleness, test invocation) are things fmake could own outright.

---


---

# Addendum: `--eject`, which the evaluation above should have started with

The evaluation above ran `fmake` and stopped. It never tried `--eject`, which
was a mistake worth naming, because ejecting is probably **the adoption path
for exactly the projects most likely to say no**.

`netcfgd` has a small, deliberate dependency budget and already uses this shape
elsewhere: its sibling `situ` is a schema compiler whose *generated sources are
committed*, so a person building netcfgd needs no `situc`. `fmake --eject`
offers the same bargain in the same words — the header it emits says *"This
file is yours: fmake is not needed to build it, and nothing here refers back to
fmake."* That sentence answers the objection this project would otherwise
raise, and it is not what the README leads with.

**Suggestion:** pitch `--eject` earlier and as a *mode*, not a convenience.
"Use fmake as a generator, commit the output, and your users need nothing" is a
different and much easier sell than "adopt a build tool", and it costs the
project nothing it does not already have.

## What the ejected Makefile gets right, and is not credited for

Two things in the output are better than the hand-written Makefile they would
replace, and better than most hand-written Makefiles anywhere:

- **Every depfile is `-include`d, the test object's included.** This family
  treats that as a load-bearing rule with a named failure: a test object whose
  `.d` is never read back does not rebuild when a header changes, so a struct
  that gains a field ends up with one layout in the library and another in the
  test binary linked against it — surfacing as a pile of nonsense assertion
  failures rather than a build error. fmake emits `-MD -MP -MF` per object and
  `-include`s the lot. That is the single most commonly botched thing in
  hand-written C build systems, and it is right here by construction.
- **The build directory is `OBJDIR`.** That is the canonical name in this
  family's conventions, chosen over inventing a synonym. Agreement arrived at
  independently is worth more than agreement by instruction.

Neither is mentioned anywhere a prospective user would see. They are the
strongest argument in the tool for a project that has been bitten.

## One thing in the ejected output that should change

```make
clean:
	rm -rf $(OBJDIR) client_test
```

`OBJDIR` is a variable, so `make clean OBJDIR=<anything>` removes that instead —
and an unset or mistyped one is the classic way a clean target eats something it
should not. This family's rule is that `clean` removes the files it names and
lists them; clearing a directory wholesale is acceptable **only** when the build
created it — which is true here, `fmake` does `mkdir -p` — and **even then the
path is verified: non-empty, relative, and not something that could resolve to a
source tree, a home directory, or `/`.**

Two reasons this matters more in generated output than in a hand-written file:

1. **A generated Makefile is one nobody reads.** The header says so proudly. An
   unguarded `rm -rf $(VAR)` is worst precisely where no reviewer will look.
2. **It is emitted into every project that ejects**, so one guard here is a
   guard everywhere, and one omission is an omission everywhere.

This is not a hypothetical objection from a style guide. The same defect was
written into `netcfgd`'s own Makefile earlier the same day this file was
written, and fixed the same day, which is why it is recognisable:

```make
	@case "$(OBJDIR)" in \
	"") echo "clean: OBJDIR is empty, refusing to remove anything"; exit 1 ;; \
	/*) echo "clean: OBJDIR is absolute ($(OBJDIR)), refusing"; exit 1 ;; \
	*..*) echo "clean: OBJDIR escapes the tree ($(OBJDIR)), refusing"; exit 1 ;; \
	esac
```

Five lines, emitted once, in a file nobody reads. It is the cheapest safety
property in the tool.

## Test programs and shipped programs are not distinguished

`all: client_test` — the default target builds the test binary, because
`tests/client_test.c` defines `main()` and that is fmake's whole rule for what a
program is.

This family goes the other way deliberately: **the default target does not
build tests**, and a separate `test` target builds and runs them. That buys a
fast default build, and it is *paid for* by the dependency rules above being
correct — which, as noted, fmake already gets right. So fmake has already paid
the cost of the convention and does not take the benefit.

There is no annotation-free way to know that `tests/` means tests, and inventing
one would break the promise. But a directory-name convention (`tests/`, `test/`,
`*_test.c`) put behind a flag — `--tests-dir`, or a `test` target in ejected
output that is not in `all` — would let a project keep both.

## Eject is a starting point, not a translation

The ejected `CFLAGS` were `-O2 -g -I.`. The Makefile it would replace had
`-std=c11 -Os` plus nine warning flags described in its own comments as *"not
decoration: this code parses bytes from a socket into indices, and every one of
them has caught something in code shaped like this."*

fmake cannot be blamed for that — the Makefile had been deleted before the run,
so there was nothing to read. The point is for the documentation: a project that
ejects and commits the result **silently changes its language standard and drops
its warning set**, and neither shows up as an error. The first diff to review
after ejecting is the flags, and saying so next to `--eject` would cost one
sentence.

## What was not tested, so nothing above is claimed about it

- `--eject ninja`.
- `gui/`, or anything needing `moc`/`uic`/`rcc`.
- Whether the object cache keys on flags — the question in the main note above
  is still open, and matters more now that `--eject` looks like the headline.
- Any tree with more than one program, which is where the library inference
  question actually gets interesting.
