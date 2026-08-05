# fmake, evaluated against fuzzypickles

Written 2026-08-04, from a trial against a copy of the tree. Per
`build-and-commit.md`'s standing instruction that projects which could adopt
fmake should say whether they would.

## What fuzzypickles is, for sizing

An encrypted peer-to-peer messaging platform. Roughly:

- Four static archives built from separate directories: `common/`, `core/`,
  `client/`, plus `flog` vendored.
- Three programs (`fzpd`, `fzp`, `fzptui`) and a Qt Widgets client
  (`fzp-gui`), each in its own directory.
- Five vendored submodules: monocypher, iniparser, flog, miniz, thorvg.
- ~35 unit test binaries, plus an end-to-end suite of shell scenarios.
- Cross-compiled for Android (arm64-v8a, x86_64) *in the same checkout* as
  the host build, via `OBJDIR`.
- Packaged as a `.deb` (CPack) and an `.apk` (qmake + androiddeployqt).

Six hand-written Makefiles, and a `CMakeLists.txt` that drifts from them.

## The trial

`fmake --explain` against a copy of `common core client daemon cli` plus the
vendored submodules. Four things stopped it, each with a good error message
that named the files and the remedy:

**1. Two vendored submodules both produce a program called `test`.**
`flog/test.c` and `monocypher/tests/test.c`. The suggested fixes are `@target`
in the source or a name in `fmake.toml` — but the first means editing vendored
code, which this project treats as exempt and does not touch. So it has to be
`fmake.toml`, for a collision between two files we do not own and did not
write.

**2. `cli/main.c` wants to be a program named `cli`, which is a directory.**
This tree names each program's directory after the program: `cli/main.c`,
`daemon/main.c`, `tui/main.c`. All three collide with their own directory when
output goes to the project root. `-o` moves the output; the real binaries live
at `cli/fzp` and `daemon/fzpd`, so the names have to be given anyway.

**3. Tests are built by the default build.** fmake compiled all ~35 test
binaries along with everything else. `build-and-commit.md` is explicit that the
default target does *not* build tests, and that the convention is paid for by
the dependency rules being correct — it exists to buy a fast default build.
This is the one finding that is a genuine conflict rather than a configuration
gap, and I could not see a way to express "these `main()`s are tests" other
than enumerating them.

**4. Ten vendored fuzzers all define `LLVMFuzzerTestOneInput`.** miniz ships
them; two do not even compile against the miniz configuration this project
uses (`MINIZ_NO_DEFLATE_APIS` removes `tdefl_compress_level`). They need
`[project] exclude`.

So a working `fmake.toml` here excludes four vendored subtrees, names three or
more programs, and separates tests from the default build. That is a build
file — the thing fmake exists to avoid — though a far shorter one than six
Makefiles.

## What it gets right, and it is not small

**The object directory is keyed by configuration.** `objdir =
.fmake/obj/<cfg.key>`, where the key covers `cc`, `cxx`, both versions, os,
arch, cflags and overrides, with the comment "a flag that is not in it is a
flag that silently reuses objects built without it."

That is exactly the failure this project hit and had to fix by hand: `flog` is
a submodule with no `OBJDIR` support, so it always wrote `libflog.a` beside its
own sources, and the host build and the Android cross build overwrote each
other's archive — surfacing at the far end as `incompatible with aarch64linux`
in a build that had changed nothing. `daemon/Makefile` now compiles flog's
sources into `OBJDIR` itself to work around it. fmake would not have had the
bug.

The same applies to the three dependency-tracking rules in
`build-and-commit.md` — `.d` files actually `-include`d, `FORCE` on
sibling-library rules, `.SECONDARY` named rather than bare. **Every one of
those has already failed in practice here**, each producing a stale artifact
and a confusing symptom elsewhere. They are hand-maintained in six Makefiles.
fmake makes that whole failure class someone else's problem, which is
material rather than cosmetic.

## Verdict

**Not a switch today, and the reason is scope rather than quality.**

fmake would own the compile-and-link layer well. But this build's difficulty is
mostly not compile-and-link: CPack for the `.deb`, qmake and androiddeployqt
for the `.apk`, five submodules with their own build systems, and a `make apk`
target that sequences all of it. Those stay whatever they are, so adoption
means fmake plus a Makefile that still does the hard parts — two build systems
where there was one.

**What would change the answer**, roughly in order of how much it would move
it:

1. **A way to say "this `main()` is a test"** that is not an enumeration —
   a directory convention (`tests/`, which this project already uses
   everywhere), or a `[tests]` section. That would settle finding 3, which is
   the only genuine conflict.
2. **Ignoring vendored subtrees by default.** A directory containing its own
   `Makefile`/`CMakeLists.txt`, or listed as a git submodule, is almost never
   something the outer tree wants fmake to build. `SKIP_DIRS` already encodes
   this instinct for `build` and `node_modules`; submodules are the same
   category and would have removed findings 1 and 4 without configuration.
3. **Ejecting a Makefile that a hand-written one can include.** `--eject` is
   listed; if the ejected file can be a *fragment* that an existing Makefile
   includes for the compile rules while keeping its own packaging targets,
   that is an incremental adoption path rather than a switch. That would make
   the verdict above obsolete, because scope stops being the objection.

Worth re-evaluating when any of those land.

---

## The ejected Makefile, checked against the rules it will be judged by

`build-and-commit.md` is explicit that its three dependency-tracking rules
apply to **an ejected Makefile too** — "an ejected Makefile is a Makefile
someone will edit." So the ejected output was checked against them directly.
This matters more than it sounds: `--eject` is the most plausible adoption
path for this project (see *What would change the answer*, item 3), so the
quality of that output is the quality of the switch.

**Rule 1, `.d` files must actually be `-include`d: satisfied**, and with a
comment saying why:

    # Depfiles the compiler writes as a side effect, so a changed header
    # rebuilds what includes it.
    -include $(patsubst %.o,%.d,$(OBJDIR)/main.c.o $(OBJDIR)/src/util.c.o)

**Rules 2 and 3 largely do not arise, which is a virtue rather than a gap.**
The `FORCE`-prerequisite rule exists because a recursive sibling-library
sub-make with no prerequisites fires only when its target is missing; the
`.SECONDARY` rule exists because a bare one silently covers the object
pattern. The ejected Makefile is *flat* — explicit object rules, no recursion,
no pattern rules — so neither failure mode has anywhere to live. Two of the
three hardest-won rules in this project's build system are answered by not
having the structure that needs them. That is worth saying out loud in
fmake's own documentation.

(Not fairly tested: `.SECONDARY` on a tree that genuinely has intermediates.
The trial tree had none.)

### One real defect: the ejected `clean` target

    clean:
            rm -rf $(OBJDIR) fmej

`OBJDIR` is a normal Make variable and overriding it is expected usage. So:

    $ make -f ejected.mk -n clean OBJDIR=
    rm -rf  fmej

    $ make -f ejected.mk -n clean OBJDIR=/
    rm -rf / fmej

`build-and-commit.md` names this exact shape — "An unset or mistyped variable
in an `rm -rf $(VAR)` is precisely how a clean target eats something it should
not" — and it is worse in generated code, because the person running it did
not write it and has no reason to read it.

The fix is cheap and does not need the surrounding rule adopted: refuse rather
than guess. This project's Makefile now routes every directory removal through
a guard that rejects an empty path, anything containing `..`, and any absolute
path outside the tree:

    fzp_rm_build_dir() {
            case "$1" in
              "" | *..*) echo "refusing to remove '$1'" >&2; return 1;;
              $(CURDIR)/?*) ;;
              /*)        echo "refusing to remove '$1'" >&2; return 1;;
              ?*) ;;
            esac
            rm -rf -- "$1"
    }

Emitting something like that into the ejected Makefile would make the
generated clean target safe by construction. Alternatively, name the objects
instead of the directory — the ejected file already knows every object path,
since it lists them for `-include`.

## On the error messages

Worth recording as a positive, because this project's `project.md` §14 is
largely a catalogue of diagnostics that named the wrong cause. Every one of
the four failures above printed **both** colliding files and **both** remedies,
and the `LLVMFuzzerTestOneInput` one added the diagnosis:

> 10 files define it, which usually means they are separate programs sharing
> an entry point rather than one library.

That is a message that tells someone what is true about their tree, not just
what the tool could not do. It is the standard, and fmake meets it.
