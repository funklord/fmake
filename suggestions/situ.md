# fmake, evaluated against situ

Written 2026-08-05, from a clone rather than the working tree, per
`build-and-commit.md`'s standing instruction that projects which could adopt
fmake should say whether they would. situ is the last of the seven private
projects to run it.

## What situ is, for sizing

A schema compiler for byte-exact data layouts. The C side is small and the
shape is unusual:

- `runtime/c/` -- the runtime a generated codec links against: one `.c`, one
  public header. This is the deliverable.
- `tests/` -- 11 test programs, plus `tests/generated/`, which holds C that
  `situc` produced from `tests/schemas/*.situ` and which the tests compile
  against.
- Everything else is Python: `situc` itself, its own test suite, `tools/`.

So the C build is a small library, a pile of test binaries, and a code
generator written in another language standing between them. A 283-line
`Makefile` and a 96-line `CMakeLists.txt` cover it today.

## The trial

`fmake` in the clone, nothing configured. Four things, in order.

**1. It stopped on `situ.h`, and told us exactly what to write.**

    * situ.h: No such file or directory
      in tests/generated/codec_impl.c
      situ.h is on no include path here
      it is in this tree, at runtime/c/situ.h
      [project] include-dirs = ['runtime/c'] would find it

That is the whole diagnosis and the whole remedy, on the first run. The
generated codec includes `<situ.h>` because that is how a consumer of the
runtime includes it, and nothing had put `runtime/c` on the path. Worth
saying plainly because the equivalent message in most build tools is a
compiler error and a shrug: this one named the file, said the tree already
contained it, said where, and gave the line to paste.

**2. With that one line, the library builds.**

    [project]
    include-dirs = ['runtime/c']

`libsitu.a`, and the 11 test programs correctly held out of the default
build with `fmake test` offered. No `fmake.toml` beyond those two lines, no
annotations, no target list.

**3. The archive contains a test file.** `libsitu.a` has two members:
`situ.c.o` and `codec_impl.c.o`. The second is `tests/generated/codec_impl.c`
-- generated test material, in the shipped library.

The reasoning is visible and defensible: a tree whose only `main()`s are
tests is treated as one library, and the tests convention classifies
*programs*, not sources. `codec_impl.c` defines no `main`, so it is not a
test program; it is just a source in the tree, and the whole tree is the
library.

It is still wrong for this project, and probably for most projects with a
`tests/` directory containing helper sources. `[target.situ] sources = [...]`
fixes it. But the default puts test material in a deliverable, silently, and
the archive is the thing situ ships.

**Suggestion:** when a tree is treated as one library because only tests
define `main()`, consider excluding sources under the test directories from
it. The convention already knows where tests live; it currently uses that
knowledge only for programs.

**4. The tests need a code generator, which is where it stops.**
`fmake test` fails on `header.h`, `bmp.h` and `icmp.h` -- headers that are
in no tree, because `situc` writes them from `tests/schemas/*.situ`.

This is not a gap -- it is what `[generate.*]` rules are for -- but the
first draft of this report guessed it was "a handful of lines" without
trying it, and that was wrong. Measured:

- **One `[generate.*]` rule.** `inputs` takes globs and the command loops,
  so a single section covers all 31 schemas under `examples/*/`, `std/` and
  `tests/schemas/`. Its `outputs` list names the 62 files, which is what
  lets fmake know when the step is stale; that list is long and mechanical
  and a project would generate it. Four lines and a list.

  (Ten separate rules, one per schema, also works and was tried first. The
  glob form is better and was found by asking why the number was ten.)
- **Two `[target.*] sources` lists**, for `probe` and `test_header`. Three
  generated codecs each define `situ_header_validate`, since three schemas
  declare a type called `header`, and those objects genuinely cannot be
  linked together. fmake refuses to choose and prints the exact sections to
  paste, which is the right answer: any build system has to be told this,
  and situ's own must know it too.
- **Seven lines** in total, plus the generated outputs list, and after them
  nine of the eleven test programs build.

**`test_kernels` still does not link**, wanting `situ_base16_encode` and its
neighbours. Those are declared in the generated `kernels.h` and defined by
no schema-to-C step this trial found. That is situ's own build knowledge --
which generator, or which hand-written file, supplies the codec kernels --
and is the honest boundary: fmake builds C from an unannotated tree, and a
tree that is only complete after another program has run is annotated by
definition.

## What it got right that is worth naming

- **The include-path diagnosis.** See above. It converted a dead end into a
  one-line fix without a search.
- **Tests out of the default build**, which is what this family's
  conventions require and what situ's own `Makefile` does by hand.
- **`--eject` produces 168 lines** that build the same thing with no fmake
  present. For a project whose whole pitch is *"generated sources are
  committed, so your users need no situc"*, that bargain is familiar and
  attractive: it is the same trade in the same words.

## Verdict

**Not a switch today, and for a reason that is about situ rather than about
fmake.**

The C in this repository is one library and eleven test binaries. That is
perhaps a fifth of what the `Makefile` does; the rest is Python packaging,
`mypy` runs, the schema compiler's own test suite, a version-consistency
gate, and the `.deb`. fmake would own the small part well and leave the
Makefile in place for the rest, which is two build systems where there is
one.

**What would change the answer** is not a feature. If the C side grows --
more runtime translation units, more codecs, per-platform variants -- the
compile-and-link layer becomes worth delegating, and the answer flips
without fmake changing at all.

**What would make the trial better regardless** was the archive finding
above: a default that puts a generated test file into a shipped library is
the one thing here that could bite a project which adopted fmake without
reading the archive's member list. It has since been fixed -- a library the
closure assembles no longer takes test sources, and `libsitu.a` is
`situ.c.o` alone.

## Meta

This is the seventh evaluation and the first where the tool's diagnostics
did more work than its inference. The inference was never in question: two
objects, one archive, eleven test programs, all correct with no
configuration. Every step after that was fmake naming what it needed and
this report pasting it back -- the include directory, the two ambiguous
source lists, and, one round at a time, which schema was missing next.

It is also the first evaluation to catch itself. The paragraph about
`[generate.*]` being "a handful of lines" was written before anything was
tried, and the trying said sixty. A report that guesses at the cost of the
work it is recommending is worth less than one that stops and measures, and
this one nearly shipped the guess.
