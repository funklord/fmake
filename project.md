# fmake

A build tool for normal desktop programs, where the common case needs no build
file at all and the uncommon case needs a short one.

This is a living design document. It is updated as decisions are made, and it
records the reasoning, not just the conclusion — including the options rejected,
so they don't get relitigated.

**For using the tool, read `README.md`.** This file is the record of how the
design was arrived at, which is a different thing and much longer.

Status: **phases 1–6 implemented, plus two passes over the invariants.**

`fmake` builds C and C++ programs and libraries from an unannotated tree,
resolves their dependencies, accepts in-source directives for what cannot be
inferred, reads an optional `fmake.toml` for what belongs to no single file,
cross-compiles, and can eject a standalone Makefile or `build.ninja` and get
out of the way.

`./selftest` covers the design claims below, one case per claim, and every fix
in §14 is mutation-checked: the case is confirmed to fail when the bug is put
back. Phase 7 (`fmake.py`) is **declined** rather than pending — see §11.

---

## Contents

**The design.** [1. The premise](#1-the-premise) ·
[2. Design principles](#2-design-principles) ·
[3. The core rule](#3-the-core-rule) — how the link set is decided, and why the
obvious answer is wrong ·
[4. Annotations](#4-annotations) ·
[5. Dependency inference](#5-dependency-inference) ·
[6. Precedence](#6-precedence) ·
[7. Configuration files](#7-configuration-files) ·
[8. Speed and caching](#8-speed-and-caching) ·
[9. Implementation](#9-implementation) ·
[10. `--explain`](#10---explain) ·
[12. The exit](#12-the-exit) ·
[17. Qt and moc](#17-qt-and-what-moc-costs) — the one framework named in the
source, and why it fits §3 rather than fighting it

**Picking it up.** [16. Working on this](#16-working-on-this) — the
conventions, how the verification is reproduced, and where the reference
projects come from.

**What happened when it met reality.**
[11. Build order](#11-build-order) — what was built, in what order, and what
each phase turned up ·
[13. What real projects showed](#13-what-real-projects-showed) — four
codebases, and the four things a 6-file project could not have exposed ·
[14. The chains, checked](#14-the-chains-checked) — the same question asked of
the design rather than of a sample, and the silent wrongness it found ·
[15. Open questions](#15-open-questions)

If you read one section, read §3: everything else follows from it. If you read
two, read §14, which is where the design was checked against itself and lost
several times.

---

## 1. The premise

Make and its descendants ask you to describe a build that is, for most desktop
programs, entirely predictable from the source tree itself. A directory with a
`main.c` in it wants to become a program called after the directory. A file that
does `#include <SDL2/SDL.h>` wants `sdl2` linked. A `foo.c` next to a `foo.h`
that somebody includes wants to be compiled and linked in.

fmake's goal is **fewer keystrokes between "I have source" and "I have a binary"**.
Not faster compilation — the compiler dominates that, and fmake cannot help. The
speed being optimised is the speed of *expressing* a build.

It achieves this by making a lot of assumptions, showing you every one of them on
request, and letting you override any of them from inside the source file that
motivated the override.

Target audience: desktop applications and tools. System and embedded work is
supported but is not what the defaults are tuned for.

---

## 2. Design principles

1. **Zero files for the common case.** `fmake` in a directory with `main.c`
   produces a binary. No init, no scaffold, no generated file.
2. **Locality.** A build fact belongs in the file it is about. The file that
   includes SDL declares the SDL dependency; it survives being moved, copied into
   another project, or deleted.
3. **Inference first, annotation as escape hatch.** Every annotation the user has
   to write is a small failure. `@libs` should be rare, not routine.
4. **No magic without an audit trail.** Every inference is explainable with
   `--explain`, down to the exact argv. Aggressive assumptions are only tolerable
   if they're inspectable.
5. **Always an exit.** `--eject` writes a standalone Makefile or ninja file. You
   can leave fmake at any time, taking your build with you.
6. **No dependencies.** One script, stdlib only. See §9.

---

## 3. The core rule

### The rejected version

The obvious rule, and the first one written here, was:

> A TU is linked into a binary if it is reachable from the root by following
> `#include "local.h"` where a sibling `local.c` exists.

**This is wrong, and it fails on ordinary code, not exotic code.** Headers are
not implementations, and C projects routinely break the 1:1 correspondence:

- `shapes.h` declaring an API implemented across `circle.c`, `square.c`,
  `triangle.c` — one header, many implementations, none name-matching.
- `util.h` implemented by `util_posix.c` — name mismatch.
- A single `common.h` that everything includes, with implementations scattered.
- No header at all: a bare `extern void helper(void);` at the top of a TU.

Every one of these produces undefined references. The include graph describes
*declaration* dependencies. The link set is a question about *definitions*, and
those are a different graph.

Make knows the link set because you typed it out. fmake needs a real answer.

### The actual rule

The answer is that the object files already contain the link set. A compiled TU
carries a symbol table: which symbols it defines, which it leaves undefined.
Closure over that relation *is* the link set — the same computation a linker
performs when deciding which members to pull out of a static archive.

> Every TU defining `main()` at file scope is a **binary root**. Compile the
> candidate set, then take the transitive closure from the root's object: for
> each undefined symbol, link the object that defines it, and repeat. What the
> closure reaches is the link set. What it doesn't reach is not built into that
> binary. Undefined symbols nothing in the tree defines are **external**, and are
> the input to library resolution (§5).

Verified against the failure cases above: from `main.o` needing
`banner circle_area square_area`, closure returns exactly
`circle.o main.o square.o util_posix.o`, correctly ignores an unreferenced
`scratch.o`, and reports `printf puts` as external — despite two name mismatches
and a one-header-three-implementations split that defeat the include-graph rule.

### Where the include graph still earns its place

Symbol closure needs objects, and objects need compilation. Compiling the entire
tree to discover that most of it was irrelevant is the cost Make avoids by making
you type the answer. So the include graph survives, demoted to what it's actually
good for — **a cheap first guess at what's worth compiling**:

1. **Candidate set** from the include graph (fast, no compiler runs).
2. **Compile** the candidates.
3. **Close** over symbols. Resolved from within the candidate set → done.
4. **Widen** on failure: undefined symbols nothing in the candidate set defines
   trigger compilation of more TUs from the tree, then retry the closure.
5. **External** is what survives a closure over the whole tree.

When the project is tidy, step 3 closes and the extra files are never compiled.
When it isn't, step 4 finds the answer instead of failing. Either way the result
is exact — the guess only affects how much work is done, never what gets linked.

**Two rules decide what the include graph can see, and both were too narrow.**
They only showed up on a project big enough to have a conventional layout:

- *A header's implementation need not be its sibling.* `include/Bullet.h`
  implemented by `src/Bullet.cpp` is one of the commonest C++ layouts there is,
  and a strict sibling rule finds nothing in it. Measured on a 292-file game: 5
  headers had a sibling, 256 had a same-stem source elsewhere. A same-stem
  match anywhere in the tree is used when there is exactly one; several
  candidates say nothing about which is meant, so those are left to widening.
- *Angle brackets do not mean "not mine".* Putting `include/` on the `-I` path
  and writing `<Bullet.h>` is standard practice and what CMake encourages. The
  same game used `<>` for its own headers 2342 times against 425 quoted. What
  decides is whether the name resolves inside the tree, not the punctuation —
  and a name that resolves to nothing local still falls through to library
  resolution untouched.

Together those took that project from **3 candidates out of 292 sources to
248**. The remainder — tests, a vendored maths library, platform files — are
exactly what widening is for.

**The widening filter must match definitions, not mentions.** Filtering on any
occurrence of a symbol name matches every file that merely *calls* `printf`, so
chasing one unresolvable libc symbol drags in most of the tree. Candidates are
therefore files that appear to *define* the symbol — a name followed by a
parameter list and a brace, or a file-scope data definition at column zero.
Definitions this cannot see (generated by macros, or living in a header, as
template instantiations do) need `--widen-all` or `--force-link`.

### Consequences

- **Two `main()`s means two binaries**, sharing whatever both closures reach.
  Compiled once, linked twice.
- **Duplicate definitions are a hard error**, naming both TUs. Two files defining
  `sys_init` (say `win32_sys.c` and `posix_sys.c`) is ambiguity, not a choice for
  fmake to make silently. `@os`/`@arch` removes one from the candidate set and
  resolves it. This is a concrete advantage over the tempting shortcut of
  building everything into a `.a` and letting the linker close: the linker
  resolves duplicates by archive order, silently and arbitrarily.
- **Unreferenced TUs are not built into the binary.** Reported by `--explain`.
- **Symbol-invisible TUs must be asserted.** A plugin registering itself via
  `__attribute__((constructor))` is referenced by nothing, so closure never
  reaches it. This is the one case with no automatic answer — it is also exactly
  the case where a static library drops the member and the constructor never
  runs, so C has this problem independently of fmake. Make requires you to list
  the file; so does fmake. Not worse, just not better. Such files **seed** the
  closure alongside the root rather than merely joining the compiled set: once
  asserted, their own dependencies resolve normally — `@sources`, or
  `--force-link` from the command line.
- **A target's name must not be a directory.** `main.c` is named after its
  directory, since "main" names nothing — but `src/main.cpp` must not produce a
  binary called `src`, which is not a name and collides with the directory it
  came from. Conventional source-directory names (`src`, `source`, `app`, …)
  are skipped in favour of whatever encloses them, ending at the project's own
  name, and writing over a directory is refused outright.
- **One target failing must not sink the others.** Targets are discovered, not
  requested, so a repo whose test binaries need a library fmake cannot resolve
  yet should still produce its programs. Failures are reported per target, with
  that target's unresolved externals, and the exit status is non-zero. This
  covers compilation as well as linking: a test binary whose library is not
  installed must not stop the program beside it from building. A file that
  fails to compile simply has no symbols, so nothing can close over it, and
  whichever target needed it is dropped by name.
- **The binary is named after the root TU**, unless that TU is `main.*`, in which
  case it takes the containing directory's name. `@target` overrides.
- **A tree with no `main()` builds as a library**, and the closure runs from the
  set of `@headers`-declared public symbols instead of from a root object.

### Detecting `main()`

Not a regex for `main` — that hits `int mainloop()`, `// main entry`, and string
literals. The scanner strips comments and string literals first (needed anyway
for correct `#include` scanning), then matches a function *definition* at file
scope. Declarations and calls don't count. Cheap cross-check available once
objects exist: `main.o` defines the symbol `main`.

### Reading symbol tables

`nm --format=posix` on each object. Portable across GNU binutils and LLVM
(`llvm-nm` takes the same flags); located once at startup with a clear error if
absent. Per-object symbol tables are cached by object content hash, so `nm` runs
once per compile, not once per build (§8).

The classification is not simply "U versus everything else":

- **`U`** — undefined, drives the closure.
- **`T` `D` `B` `R`** — strong definitions. These make an object a *provider*,
  and duplicates between two objects are the ambiguity error above.
- **`W` `V` `w` `v`** — weak / vague-linkage definitions, and **`C`** commons.
  These are **providers of last resort**: used only when no strong definition
  exists anywhere, and several of them offering the same symbol is normal
  rather than ambiguous.

The weak rule took three corrections to get right. Two directions are wrong in
ways that only show up in real C++, and the third was wrong in a way that shows
up nowhere at all until you look for it:

- **Weak treated as strong** — templates, inline functions and vtables emit a
  weak definition into *every* object that uses them, so a symbol legitimately
  has many providers. Reporting that as a duplicate refuses to build correct
  programs. Verified: an ordinary template and an inline function each produce
  identical `W` symbols in every object that touches them.
- **Weak ignored entirely** — `extern template` leaves a plain `U` reference
  that *only* a vague-linkage definition satisfies. Skipping weak providers
  compiles the instantiating file, leaves it out of the link set, and fails at
  the linker with an undefined reference to something that is right there.
- **Weak accepted as satisfaction** — the rule was applied when *choosing* a
  provider but not when deciding whether to look for one, so a weak definition
  in an object linked for an unrelated reason ended the search and a strong
  definition elsewhere was never found. This is the weak-override pattern, and
  it failed silently and non-deterministically. §14 has the demonstration.

So: strong wins if one exists, weak is used if none does, multiple strong is an
error, multiple weak is fine — pick deterministically. And *strong wins* has to
hold at every point the rule is consulted, not just where it is written down.
This mirrors what the linker does, which is the point: the closure is only
correct if it reproduces the linker's own resolution rules.

Reading ELF/Mach-O symbol tables directly in Python was considered and rejected:
it's a few hundred lines of format handling per platform to save one cheap
subprocess per changed file, and it would need redoing for every object format.

---

## 4. Annotations

Doxygen-format comments, in any of Doxygen's comment styles (`//!`, `///`,
`/*! */`, `/** */`), using `@cmd` or `\cmd`.

A directive applies to the TU it appears in, wherever in the file it appears.
Placement inside a `/*! @file */` block at the top is the documented convention
and is what Doxygen wants, but fmake does not enforce it — the guiding rule is
that the annotation lives next to the code that motivated it.

```c
/*! @file
 *  @target  myapp
 *  @pkg     sdl2 >= 2.0.18
 *  @libs    m
 *  @std     c17
 */
```

### The directive set

Deliberately small. The failure mode of this design is directive sprawl until
there is a config language living in comments. Anything needing real logic goes
in `fmake.toml`, or `fmake.py` if it truly needs code.

| Directive | Meaning |
|---|---|
| `@target NAME` | Name of the artifact this TU roots. |
| `@kind exe\|shared\|static` | What to build. Inferred from `main()` presence otherwise. |
| `@pkg NAME [OP VER]` | pkg-config dependency. Version constraint optional. |
| `@libs NAME...` | Raw `-l` links, for libraries with no `.pc` file. |
| `@headers PATH...` | Public headers of a library — the installable API surface. |
| `@cflags ...` | Extra compile flags for this TU. |
| `@ldflags ...` | Extra link flags, propagated to any binary this TU reaches. |
| `@define NAME[=VAL]` | Convenience for `-D`. |
| `@std c17\|c++20\|...` | Language standard. |
| `@os NAME...` / `@arch NAME...` | This TU only participates on matching platforms. |
| `@sources GLOB...` | Force TUs into the link set that reachability missed. |

Scalar directives — `@target`, `@kind`, `@std` — replace; last one wins.
Everything else accumulates, across every comment in a file and every file in
the link set. Arguments are split shell-style, so quoting works and
`@define LABEL=\"text\"` needs the backslashes a shell would need.

Notes on specific choices:

- **`@pkg` vs `@libs` are separate on purpose.** They resolve differently:
  `@pkg` runs `pkg-config --cflags --libs` and can carry a version constraint;
  `@libs` is a literal `-lfoo`. Collapsing them into one directive would mean
  guessing which was meant, and guessing wrong is a link error the user can't
  easily attribute.
- **Both are assertions, not proposals.** A header only proposes a package,
  and §5 may decide against it. A directive says the library is needed, so it
  is linked whether or not a symbol happens to require it. The author knows
  something the symbols do not — `dlopen`, a linker script, a constructor.
- **`@pkg` constraints are checked before anything compiles.** Failing at
  pkg-config with `@pkg sdl2 >= 2.0.18 is not satisfied (installed: 2.0.14)`
  is a far better error than the compiler's "no such file or directory" forty
  lines later.
- **`@headers` is not for build inputs.** Headers used by a TU come from the
  `#include` scan; declaring them again would be redundant and would rot. The
  directive is repurposed for the one header question that *isn't* inferable:
  which headers form a library's public interface. `--install` (§7) is what
  consumes it; `--eject` still does not emit an install rule.
- **`@ldflags` propagates, `@cflags` does not.** Compile flags are a property of
  the TU. Link flags are a property of anything the TU ends up inside. This
  asymmetry is the thing that makes locality work for dependencies.
- **`@os`/`@arch` remove a TU from the build entirely** — not from the link
  set, from existence. This is the answer to §3's duplicate-definition error:
  `win32_sys.c` and `posix_sys.c` both defining `sys_init` is an ambiguity
  fmake refuses to resolve, and refusing is the right answer to the wrong
  question, because only one of them was ever meant to be built here. The
  error message says so and names the directive.
- **`@sources` is `--force-link` declared where it belongs**, and `--explain`
  attributes the file to the directive rather than to the flag.

### One word per fact, wherever it is written

The premise was that a directive and a build script should say a thing the
same way. Measured rather than assumed: **ten of twelve directives already
used the identical word** in a comment and in `fmake.toml` — `arch cflags
headers kind ldflags libs os pkg sources std`. Two had drifted, `@define`
against `defines` and `@target` against `name`, and both spellings now work in
both places. A fact should not need a different word for living somewhere
else.

### `@rule` — a build rule beside the code that needs it

The larger gap was that a *rule* could only ever live in a separate file. A
file needing a generated companion had no way to say so, which is precisely
the thing annotations exist to fix.

```c
/*! @file
 *  @rule gen/table.c: data/table.txt
 *        python3 tools/mktable.py $< $@
 */
```

Recipe lines are the ones indented beneath it, exactly as in a Makefile, and
the text goes through **the same parser `fmake.mk` uses**. That is the point:
the two are the same language because they are the same code, not because two
parsers are being kept in step — which is a thing that stops being true.
Errors are reported against the source file and line the rule was written in.

This is what made the two-pass scan necessary after all. §7 recorded that
generated sources needed no second pass, because running the generators before
the tree was walked made their output ordinary. A rule living in a comment
cannot be read without scanning first, so the tree is scanned, generated, and
scanned again. **The prediction was right for the design as it stood and wrong
for the design once rules could live in source** — the cost was not in
generating, it was in where the rules are allowed to live.

### Both formats, either file

A source comment already took both kinds of statement — `@libs m` beside
`@rule gen/n.c: data/n.txt`. `fmake.mk` took only rules, so a project wanting
a pattern rule *and* a project-wide flag needed two files for no reason anyone
could name. It now takes directives too, in the same spelling:

```make
@std    c17
@define SCALE=4
@libs   m

gen/%.c: data/%.txt
	python3 mk.py $< $@
```

**Scope is the thing that has to be explicit.** A directive in a comment is a
fact about that translation unit; `fmake.mk` has no translation unit, so a
directive there is a fact about the project — the same level as `[project]`.
Directives that cannot mean anything without a file or an artifact —
`@target`, `@kind`, `@os`, `@arch`, `@sources`, `@headers` — are refused there
and told where they belong, rather than being given an invented scope.

So the three places now divide by what a fact *is*, not by syntax: a comment
for facts about one file, `fmake.mk` for rules and project-wide flags,
`fmake.toml` for the structured things that need tables — target membership,
profiles, toolchains.

### `conf or default` was a trap

Wiring that up hit the sentinel class again in a new disguise. `Config` did:

```python
conf = conf or Conf({})
```

`Conf.__bool__` answers "is anything configured", which is a reasonable thing
for it to mean and fatal here: a `Conf` carrying directives folded in from
`fmake.mk` is falsy when there is no `fmake.toml`, so `or` discarded it and
every flag vanished silently. **A `__bool__` with a domain meaning defeats
every `x or y` in the file.** The call site now tests `is None`; `__bool__`
also counts what has been folded in, which is defence in depth rather than the
fix — reverting only the latter leaves the case passing.

### What counts as a directive

Only Doxygen's own comment markers — `//!`, `///`, `/*!`, `/**`. An `@` in an
ordinary comment is never a directive, so an email address in a header banner
cannot rename the program. This is enforced twice over, by the comment-opener
test and again by the marker-stripping that runs before a line is examined;
relaxing either alone changes nothing.

Unknown commands are **ignored in silence**, because `@brief`, `@param` and
`@author` are not fmake's business and warning about them would make the
Doxygen integration unusable. The cost is real: `@lib` instead of `@libs` is
silently inert. The mitigation is that `--explain` lists every directive it
recognised, per file and with line numbers, so a typo shows up as an absence.

### Doxygen interoperability

Honest assessment: Doxygen does not know these commands and will emit "unknown
command" warnings for each one. Reuse is not free, but it is cheap:

- `fmake --doxygen-aliases` emits an `ALIASES += ...` block. Users add
  `@INCLUDE = fmake.doxygen-aliases` to their Doxyfile and the directives render
  as documentation instead of warnings.
- The `/*! @file */` placement convention matters here. Doxygen binds a `//!`
  block to the *next declaration*; a bare `//! @libs m` above a function attaches
  the metadata to that function in the generated docs. fmake doesn't care, but
  the rendered output will look wrong. Documented, not enforced.
- One wart with no good fix: a glob containing `/*` inside a block comment —
  `@sources plugins/*.c` — makes the compiler warn about `"/*" within comment`.
  Use a `//!` line comment for globs.

### Building libraries

`@kind` needs artifacts that are not programs, so it brings library building
with it. A tree with no `main()` anywhere is a static library named after its
directory, which is the only thing it could sensibly be.

**The closure does not apply to a library, and this is not a shortcut.** A
library exists to be linked against code that has not been written yet, so
which of its symbols matter is not knowable at the time it is built. Pruning
would be guessing. So a library is every TU in the tree except other programs'
roots — an archive with two `main()`s in it is no use to anyone. The consumer's
linker prunes a static archive at its own link, which is where the information
to do so finally exists, and a shared object keeps everything by design.

Two mechanical details: `-fPIC` is applied to the whole tree when any target is
shared, since mixing PIC objects into an executable is harmless and tracking
per-target object variants is not worth it; and the archive is removed before
`ar rcs`, because `ar` appends and a stale member would otherwise survive a
source file being deleted.

---

## 5. Dependency inference

The point of principle 3: most projects should need no `@pkg` at all.

There are two signals, and §3 makes the second one available for free.

### Signal 1 — includes (cheap, available before compiling)

For a system include like `<SDL2/SDL.h>`:

1. **Builtin table** — a hardcoded map of common headers to pkg-config names,
   covering roughly the top 200 libraries (zlib, sqlite3, curl, openssl, SDL2,
   GTK, Qt, ffmpeg, ncurses, …). Fast, deterministic, no I/O, and handles the
   cases where reverse lookup is ambiguous.
2. **pkg-config reverse lookup** — scan installed `.pc` files, resolve their
   `includedir`, check which contains the header. Cached, invalidated by mtime
   of the `.pc` directories.

This runs first because it produces `-I` flags, which the compile needs. But it
is a guess: including a header proves a declaration was wanted, not that anything
from that library is actually called.

### Signal 2 — undefined symbols (exact, available after compiling)

The external set falling out of §3's closure is a direct statement of what the
binary needs from outside the tree. `SDL_Init` undefined means `SDL_Init` is
genuinely called — not merely that a header was included.

Resolution: match each external symbol against the dynamic symbol tables of
installed shared libraries (`nm -D --defined-only`). A hit names the library,
which gives the `-l` flag directly.

Three things learned building it:

- **Only the development symlink counts.** A machine can carry
  `libSDL2-2.0.so.0` for programs that already exist while having no
  `libSDL2.so` at all, and offering `-lSDL2` there is a link error. Indexing
  only `libNAME.so`/`libNAME.a` cuts the sweep from ~2350 libraries to ~520
  *and* is more correct — and if the dev package is missing, the headers are
  missing too, so the compile failed first anyway.
- **`libc.so` and `libm.so` are GNU ld scripts, not ELF.** They name the real
  runtime libraries in a `GROUP(...)`, and `nm` cannot read them directly.
- **Dynamic symbol tables do not follow the lowercase-is-local rule.**
  Everything `nm -D --defined-only` reports is exported — glibc exports `cos`
  as an ifunc, type `i`. Version suffixes (`cos@@GLIBC_2.2.5`) need stripping.

No persistent index. The whole sweep is about a second, only the wanted symbols
are retained, and the result is cached against the union of every target's
external set plus a stamp of the library directories — so an ordinary
incremental build never scans at all. No index means no staleness.

The sweep is shared across targets rather than run per target, which is worth
more than it sounds: on a repo with four programs it is the difference between
3.9s and 1.1s for a cold build, because the sweep is the only expensive part of
resolution.

### Cross-compiling: the architecture has to be checked, not assumed

Resolution originally scanned a hardcoded list of host directories, which is
wrong in both directions on a cross build: the target's libraries are somewhere
else entirely, and the host's are full of symbols that must not be offered. The
first real cross build found nothing at all — `0 in libc`, every symbol
unresolved — and failed at the linker on `sqrt`.

Two things fix it.

**Ask the compiler where it looks.** `cc -print-search-dirs` is authoritative
and already correct for a cross compiler; on the toolchain used here it names
`/usr/aarch64-linux-gnu/lib`, a directory no hardcoded list would have guessed.
A configured sysroot's directories go ahead of it, and the native defaults stay
behind it.

**Then reject by ELF header, not by path.** This is the part that matters: a
cross compiler's own search path contains `/usr/lib` — the host's — so *no
arrangement of directory names separates the target's libraries from the
host's*. The ELF header does, exactly. fmake reads `(class, byte order,
machine)` from one of the objects it just compiled and requires every candidate
library to match, which needs no knowledge of triplets and works for any
architecture. A 20-byte read also comes in far cheaper than the `nm` it avoids.

Naming the compiler is enough for the rest: `aarch64-linux-gnu-gcc` implies
`aarch64-linux-gnu-nm`, `-ar` and `-pkg-config`. A host `nm` can often read
foreign objects, but relying on that is luck rather than design. With a sysroot,
`PKG_CONFIG_SYSROOT_DIR` and `PKG_CONFIG_LIBDIR` are set too, since pkg-config
otherwise answers for the build machine.

Verified end to end: a cross-built aarch64 binary that runs under qemu and
prints the same result as the native build, `-lm` resolved from the target's
libraries, and the host's zlib correctly refused with *"no aarch64/64le library
exports zlibVersion"* rather than an incomprehensible linker error.

### `--wrap`, for free

A symbol named `__wrap_socket` exists for exactly one reason: GNU ld's
`--wrap`, which redirects calls to `socket` into it. So a link set defining
`__wrap_X` where `X` is undefined somewhere in that same link set is an
unambiguous request for `-Wl,--wrap=X`, inferable from the symbol name alone.

This is worth calling out because it is the clearest case of the model paying
off. Include-scanning cannot reach it — there is no header involved. Only the
closure knows which objects are in the link, and therefore which wrappers
apply. And the failure mode it prevents is nasty: without the flag the program
links perfectly and silently calls the real function, which is how a mocked
unit test comes to pass against the live syscall.

This is strictly better evidence than signal 1 and catches what it misses:

- **Header included but unused** — signal 1 links a library nothing calls,
  dragging in a runtime dependency the program doesn't have. Signal 2 doesn't.
- **Library used with no distinctive header** — anything reached via a
  project-local wrapper header. Signal 1 sees nothing; signal 2 sees the symbol.
- **Wrong package for a shared header name** — signal 2 disambiguates by which
  library actually exports the symbol.

The two are combined rather than ranked: signal 1 proposes and supplies `-I`
flags, signal 2 confirms or contradicts. Disagreement is worth surfacing — a
library proposed by headers but contributing no resolved symbol is a link
fmake should drop and mention under `--explain`.

### Failure

Externals matching nothing installed are reported by symbol name, with the
including TU and line, and a suggested `@pkg`/`@libs`. This is a much better
error than the linker's bare `undefined reference to 'SDL_Init'`, because fmake
knows which source line pulled in the header and what it searched.

### Ambiguity

Two `.pc` files providing the same header is a hard stop naming both.

Two libraries exporting the same symbol is **not**, and the original plan to
refuse there was wrong. It is ordinary: glibc merged libm into libc, glibc also
ships `libm-2.41.a` beside `libm.so`, and distributions ship `libcmocka`
alongside `libcmockery`. Refusing would reject correct programs constantly.

So the choice is a greedy minimum cover over the unresolved symbols, tie-broken
by: a library the headers already proposed, then the shorter name, then
alphabetically. `--explain` names the alternatives it passed over. The
shorter-name rule is load-bearing rather than cosmetic — without it `libm-2.41`
beats `libm`, and linking glibc's private static half drags in internals like
`_dl_x86_cpu_features` that nothing can resolve. Shared libraries are also
preferred over archives outright, for the same reason.

---

## 6. Precedence

Two chains, because they govern different kinds of fact — see §14, where
assuming one chain covered both turned out to be the bug.

**Artifact identity** — name, kind, membership — is a project-level decision,
so the outer level wins:

```
inference  <  source annotations  <  fmake.toml  <  CLI / env
```

**Compile flags** are a property of one file, so they run general to specific,
and then the command line overrides everything as an override should:

```
defaults / [project] / [profile]  <  source annotations  <  CLI / env
```

Additive directives (`@libs`, `@cflags`, `@define`) accumulate across levels
rather than replacing; scalar ones (`@target`, `@kind`) replace. Both are
printed by `--explain` when levels disagree.

Concrete cases these govern: `[target.*] name` overrides `@target`; `$CC` beats
`[toolchain] cc`, so a one-off cross build needs no edit to a tracked file;
`--ldflags` is appended after every resolved and declared library, so an
explicit flag always has the last word; and `--no-libs` disables §5 entirely
without touching annotations, so `@libs` still applies.

Within `fmake.toml`, `[profile.*]` is applied after `[project]`, so a profile
overrides the defaults it sits beside.

---

## 7. Configuration files

Both are optional and neither exists in the common case.

### `fmake.toml` — declarative, no logic

For the facts that are neither inferable nor properties of a single file: what
a target is called when no file roots it, which files belong to which of two
libraries, where things install, and what toolchain to build with.

`tomllib` is stdlib as of Python 3.11, which is part of why 3.11 is the floor.

```toml
[project]
cflags  = ["-Wall"]
exclude = ["vendor/**"]

[profile.release]
cflags  = ["-O2"]
defines = ["NDEBUG=1"]

[target.alpha]
kind    = "static"
sources = ["src/alpha.c", "src/shared.c"]

[install]
prefix = "/usr/local"

[toolchain]
cc   = "aarch64-linux-gnu-gcc"
arch = "aarch64"
```

**`[target.*]` carries link-side keys only** — `name`, `kind`, `root`,
`sources`, `libs`, `pkg`, `ldflags`, `headers`. No `cflags`, no `defines`, no
`std`. This follows the same line as `@cflags` versus `@ldflags` in §4: the
compile side is a property of a file, the link side is a property of an
artifact. A per-target compile flag would mean the same source compiled two
ways, which means per-target object directories, which nothing has asked for.

**`sources` is the answer, not a starting point.** It closes the seam §4 left
open: two static libraries built from one overlapping tree. Nothing in the
source can say which library a shared file belongs to, because that is a fact
about the project rather than about any file in it — so when membership is
declared, the closure is not consulted at all, and `--explain` says so.

**`[toolchain] os`/`arch` fix a real bug.** `@os`/`@arch` were tested against
the host, which is silently wrong for every cross build: the host's files are
kept and the target's are dropped, with no error. The platform tested is now
the one being built *for*, and `--explain` prints it whenever it differs from
the host.

**Unknown keys are an error**, unlike unknown directives, which are ignored.
The difference is not inconsistency: a comment is shared with Doxygen and may
legitimately contain commands that are not fmake's, whereas this file belongs
to fmake alone — so a key it does not recognise is a typo, every time. The
error names the valid keys for that section.

### Generated sources

A `.c` produced by flex, bison or protoc does not exist when the tree is
scanned, so nothing downstream can see it: not the include graph, not the
closure, not the symbol tables.

The fix is just to run the generators first. This was expected to need a second
scanning pass and does not — once the files exist before `walk_tree`, they are
ordinary sources everywhere after, with no special case in the closure or the
symbol handling.

```toml
[generate.parser]
command = "bison -d -o $out $in"
inputs  = ["src/parser.y"]
outputs = ["src/parser.c", "src/parser.h"]

[generate.lexer]
command = "flex -o $out $in"
inputs  = ["src/lexer.l"]
depends = ["src/parser.h"]      # needed, but not an argument
outputs = ["src/lexer.c"]
```

Declared rather than inferred, because the command is not recoverable from the
file: a `.y` could be bison or byacc, with or without a header, and guessing
wrong produces a failure nobody can read.

**The generator is not always something you can install.** NetHack compiles
`makedefs` from its own source tree and runs it to produce `onames.h` and
`pm.h`; sqlite does the same with `lemon`. A command that must be on `$PATH`
before anything has been compiled cannot express that at all — the first
attempt reported *"needs 'makedefs', which is not installed"*, which is true
and useless.

```toml
[generate.names]
uses    = "makedefs"        # a target in this tree
command = "$tool -o $out"
outputs = ["include/onames.h"]
```

`uses` triggers a nested build restricted to that one target, into a scratch
directory under `.fmake/`. The tool is an ordinary program as far as fmake is
concerned — closure, libraries and all — it just gets built first and consumed
rather than shipped. A tool that needs its own output is a cycle and is
refused by name.

Four things this turned out to need:

- **`depends` separate from `inputs`.** The first attempt expressed "the lexer
  needs the parser's header" by listing it as an input — which also handed it
  to flex as a second source file to lex. Ordering and command arguments are
  different things, and conflating them silently produces a working-looking
  build from garbage.
- **Rules ordered by what they consume**, not alphabetically. One generator
  feeding another is ordinary.
- **Generated files join the candidate set outright.** Not forced into the link
  — the closure still decides — but their symbols have to exist to be closed
  over. Without this, flex output goes unbuilt: `yylex` arrives through a macro,
  which is precisely what the definition-scanning widening filter (§3) cannot
  see. This is the known limitation showing up in the most ordinary place it
  could.
- **No shell**, matching §8. The command is split once and executed directly,
  so there is no quoting to get wrong. A rule needing a pipe should call a
  script, which is also the point at which it has stopped being declarative.

Staleness is content-hashed like everything else, so touching a grammar
regenerates nothing. `--eject` emits the rules too, in both backends, or the
exit would not be one.

Verified with a real flex + bison calculator: correct generation order, the
parser rebuilt alone when the grammar changes, and the ejected Makefile and
`build.ninja` both running the generators from a clean tree.

### Install

`fmake --install [--prefix P] [--destdir D]` builds, then places executables
in `bindir`, libraries in `libdir`, and `@headers` in `includedir`.

This is what `@headers` is for, and the only thing it is for. Which headers
form a library's public interface is the header question that genuinely is not
inferable — the `#include` scan knows what a TU *consumes*, not what the
project means to *publish*.

Gathered for libraries only. A program publishes no API, and the file carrying
the directive is usually linked into one of the tree's programs as well, so
gathering there would install the same header under two owners. An explicit
`headers` list in `fmake.toml` is honoured for any kind, since naming it
outright is a decision rather than an inference.

### `fmake.mk` — the escape hatch, in Makefile syntax

`[generate.*]` is a Makefile rule wearing TOML, and it cannot say the one
thing Make says best: a pattern. Twenty `.proto` files need twenty sections,
or one section that hands every input to a single command — which is not what
anyone means, and which silently overwrote a source file the first time it was
tried.

```make
gen/%.c: proto/%.msg
	python3 gen.py $< $@

.PHONY: flash
flash: firmware
	avrdude -c usbasp -p m328p -U flash:w:$<
```

A deliberate subset, and the narrowness is the argument. Full Make is
Turing-complete — `$(shell)`, `$(foreach)`, `$(call)` — and adopting it whole
would rebuild the thing `fmake.py` was declined for. What is here has no
variables, no functions, no conditionals: explicit rules, pattern rules,
`.PHONY`, and the automatic variables everyone knows. **It cannot grow into a
program**, which Python could not promise.

It also costs nothing to learn. `inputs`/`outputs`/`depends`/`uses` are four
names invented for this document; `target: prerequisite` is universal.

**Recipes are shell.** This corrects an over-reach: §8's "no shell" was
written for the commands fmake *constructs* — a compile, where fmake knows the
exact argv and a shell buys a fork per file and a quoting hazard. A recipe is
the user's own text, where a pipe or a redirect is ordinary. And fmake was
being inconsistent about it: the Makefile `--eject` emits runs recipes through
`/bin/sh` regardless, so refusing them meant fmake declining to do what its own
output does. `@` and `-` are honoured, automatic variables are substituted
shell-quoted, and the exit escapes `$` for whichever backend it is writing —
without that, Make reads `$(x)` as its own function call and a recipe runs,
succeeds, and writes an empty file.

**`.PHONY` answers something no generator can.** A generator runs because its
output is needed. Flashing an eeprom, packaging, deploying — these are things a
tree needs to do that nothing depends on, so they have to be asked for by name.
`fmake flash` builds the prerequisites and runs the recipe, with prerequisites
naming an fmake target arriving as paths.

### `fmake.py` — declined

Loaded only if present. Gets an injected namespace of fmake primitives. For
genuine code generation and custom rules — the role `fmake.mk` now fills, in a
language that cannot become a program.

This is the SCons/Waf lineage, and it is a real risk: SCons builds have a
well-earned reputation for becoming unmaintainable programs. Meson went the other
way with a deliberately non-Turing-complete DSL. The tension is sharper here than
for either of them, because fmake *also* accepts metadata from comments — three
places a fact can live is already a lot.

**Not built, and that is the decision rather than the backlog.** Every project
met so far — four real codebases, two of which build and run — has been
expressible without it. The reasoning below is why it was designed in, and it
is also why it was left out: everything that makes it useful is what makes it
dangerous.

The original resolution was to keep `fmake.py` present but unattractive: TOML covers the
normal escapes, `fmake.py` is documented as the thing you shouldn't need, and
`--explain` always shows which level a fact came from so a `fmake.py` that
quietly overrides a source annotation is visible rather than mysterious.

The rejected alternative — drop TOML, make `fmake.py` the single escape hatch —
is less code and simpler to explain, but it means the first time you need
anything at all, you're writing a program. That contradicts the premise.

---

## 8. Speed and caching

Compilation dominates wall time; fmake's job is to not add to it and to never
rebuild anything it doesn't have to.

- **Content hashing, not mtimes.** `git checkout` between branches must not
  rebuild the world, and a comment-only edit must not relink. `hashlib.blake2b`
  is stdlib and fast enough. mtime+size is used as a cheap first-pass filter;
  the hash is only computed when that changes.
- **Scan results are cached per content hash.** The regex scan is the one
  genuinely Python-slow pass. Caching it keyed by file hash amortises it to
  approximately zero on incremental builds, which is ~99% of invocations. This
  is the main reason an interpreted language is fine here.
- **Symbol tables are cached per object hash.** `nm` runs once per compile, not
  once per build, so §3's closure on an incremental build is a pure in-memory
  graph walk over cached data with no subprocesses at all.
- **A finished build is a fixed point.** Building twice compiles nothing the
  second time — checked in the selftest and on both reference projects, which
  go from 6 and 152 files cold to zero. This is a stronger property than it
  sounds: it fails the moment any input to a cache key is computed from
  something that is still changing while the build runs.
- **The link set is cached, and it is stable.** Symbol closure only changes when
  a symbol is added, removed or renamed — not when a function body changes. So
  the common edit-compile cycle reuses the previous link set outright and the
  closure never runs. Candidate-set widening (§3) is rarer still: it happens on
  the first build and then only when an edit introduces a symbol no compiled
  object defines.
- **Free exact dependencies.** Don't shell out to `gcc -MM`. The in-process
  approximate `#include` scan is used for the first build; the real compile
  passes `-MD -MF`, and the compiler emits an exact depfile as a side effect at
  no cost. Subsequent builds use the exact data.
- **Parallel by default.** `ThreadPoolExecutor` at `nproc`. The GIL is a non-issue
  — the work is `subprocess` waiting, which releases it.
- **No shell.** `subprocess` with an argv list, never `shell=True`. No `/bin/sh`
  fork per compile, and no quoting bugs.
- **Everything that reaches a command line is in the key.** The compiler and
  its version, the target platform, every band of compile flags, the include
  flags, and each file's own directives feed a configuration hash. §14 records
  what happens when something is left out: `-fPIC` was added *after* the key it
  should have been part of, so a program-only build and a build with a shared
  library shared one set of objects. The rule has two halves, and the second is
  easier to miss — a flag that belongs in the key must also be **settled before
  the thing it keys is built**, or the key is computed from a moving value.
- **Linking is keyed the same way.** The whole command plus the contents of
  every object it consumes. Object timestamps alone miss a different library
  resolved, a `--wrap` added, or an explicit `--ldflags`, none of which touch an
  object — and the binary is then left as it was, with the build reporting
  success.

Interpreter startup is ~25-35ms versus ~3ms for a native binary. Real, and it is
the one thing an interpreted implementation genuinely costs — visible only on
no-op builds, and noise next to a single compiler invocation. Not worth choosing
a language over.

Build state lives in `.fmake/` in the project root: `.fmake/obj/<config>/` mirrors
the source tree for objects, `.fmake/cache.json` holds hashes and scan results.
fmake adds `.fmake/` to `.gitignore` if a `.git` directory exists and the entry
is missing.

---

## 9. Implementation

**Language: Python 3.11+.** One file, `fmake`, no extension, `#!/usr/bin/env python3`.

**Zero third-party dependencies, hard constraint.** A build tool that requires
pip to install is asking you to solve a dependency problem in order to solve your
dependency problem. Stdlib provides everything needed: `re`, `hashlib`,
`concurrent.futures`, `subprocess`, `tomllib`, `argparse`, `pathlib`, `shutil`.
Installation is `curl > ~/.local/bin/fmake && chmod +x`.

Modelled on `~/src/apt-emerge` (one 1900-line executable): module docstring with
usage examples at the top, `# ---- section ----` banners, aligned constant blocks,
terse functions, `try/except ImportError` for optional stdlib pieces.

Rejected alternatives, briefly:

- **Rust** — genuinely faster, single static binary, but the wrong optimisation.
  The scan is cached to near-zero anyway (§8), and a compiled implementation
  makes the tool harder to hack on, which matters more for something whose entire
  value is the assumptions it makes.
- **Perl** — better technical fit than Python for a scan-heavy tool (faster
  startup, better regex ergonomics). Loses on contributor pool and on stdlib
  breadth for the non-text parts.
- **C/C++ self-hosting** — elegant (fmake builds fmake) and removes the bootstrap
  dependency, but the daily friction is exactly what fmake exists to remove.
  "fmake builds itself" can still be a test-suite goal via `--eject`.

---

## 10. `--explain`

Not a debugging afterthought. A tool built on aggressive assumptions lives or
dies on whether its users can see what it decided, so this ships with the first
working build. Provenance is per *symbol*, not per file — under §3 that is what
the link set is actually made of, and it is what makes a surprising inclusion
diagnosable. Sketch:

```
$ fmake --explain
target myapp (exe)                      [dir name; no @target]
  link set                              [symbol closure from main.o]
    main.c                              root: defines main()
    render.c                            <- render_frame, render_init (main.c)
    util.c                              <- xstrdup                   (render.c)
    util_posix.c                        <- banner                    (main.c)
  compiled, not linked
    legacy.c                            defines nothing reachable
  external symbols                      [unresolved within the tree]
    SDL_Init, SDL_CreateWindow, ...     -> sdl2   [@pkg main.c:4; confirmed]
    compress2, uncompress               -> zlib   [<zlib.h> util.c:12; confirmed]
    sqrt, pow                           -> m      [@libs util.c:9]
    printf, puts, malloc                -> libc   [implicit]
  flags
    -std=c17                            [@std in main.c:6]
    -O2 -g                              [default profile: debug]
  argv
    cc -std=c17 -O2 -g -I/usr/include/SDL2 -D_REENTRANT -MD -MF ... -c main.c
    ...
    cc -o myapp main.o render.o util.o util_posix.o -lSDL2 -lz -lm

notices
  scratch.c   not compiled              [no path from any main(); use @sources]
  <curl/curl.h> included in net.c, but no external symbol resolves to
  libcurl -- not linked
```

That last notice is the signal-1/signal-2 disagreement from §5, and it is the
kind of thing no other build system can see: a header included out of habit,
silently adding a runtime dependency that nothing actually calls.

---

## 11. Build order

Each phase is a usable tool, not a milestone toward one.

1. **Scanner.** *Done.* Comment/string stripping, `#include` graph, `main()`
   detection, candidate sets. Not a usable tool on its own — under §3 the
   scanner only proposes what to compile, so it cannot produce a link set alone.
2. **Compile, close, link.** *Done.* Parallel execution, content-hash cache,
   `-MD` depfiles, `nm` parsing, symbol closure with weak-symbol handling,
   widening, `.fmake/` layout, `--explain`.
3. **Annotations.** *Done.* The directive set, precedence, `--doxygen-aliases`,
   and — because `@kind` demands artifacts that are not programs — building
   static and shared libraries.
4. **Dependency inference.** *Done, out of order* — `--explain` already had the
   external symbols, so turning them into `-l` flags removed the last reason to
   pass anything by hand. Header table and pkg-config reverse lookup (signal 1),
   shared-library symbol scan (signal 2), and `--wrap` inference.
5. **`fmake.toml`.** *Done.* Named configurations, install paths, per-target
   overrides, toolchain selection, and `--install`.
6. **`--eject`.** *Done.* Makefile and `build.ninja` output, both verified by
   building with fmake absent.
7. ~~**`fmake.py`.**~~ **Declined.** Every real project met so far has been
   expressible without it, and §7 already argues it should stay unattractive.
   Building it for completeness would add the one thing the premise is against:
   a place to put logic. Recorded as a decision, not a gap.

Phases 1-4 cover the entire target audience. Everything after is for the projects
that outgrow the premise.

### Phase 2 results

The milestone was fmake building §3's failure cases — one header implemented
across two files, a name-mismatched `util_posix.c`, an unreferenced orphan —
with no annotations. It does, and `./selftest` keeps it that way; the two
subtlest cases were checked by mutating fmake to reintroduce the bug and
confirming the suite catches it.

Validated against a real project too: `xplore-c-example/udp-echo`, whose
hand-written Makefile declares `udp-echo-server: server.o server_lib.o` and
`udp-echo-client: client.o client_lib.o`. fmake derived both link sets exactly,
from nothing but the source, and separately built and ran its cmocka test
binaries once cmocka was named in `LDFLAGS`. It could not name the binaries
`udp-echo-*` — that needs `@target`, which is phase 3.

The premise holds.

### Phase 4 results

The same project now builds **all four** of its targets with no flags at all,
and its 13 cmocka tests pass. fmake resolved `-lcmocka` from the symbols, and
inferred every `-Wl,--wrap=` flag — `socket`, `bind`, `close`, `epoll_ctl`,
`setsockopt`, `signalfd`, `sigprocmask` — which the Makefile lists by hand under
twenty lines of comments explaining why they are needed.

Also verified: `libxml-2.0`, which needs both an `-I/usr/include/libxml2` before
anything compiles and an `-lxml2` at link time, and which is not in the builtin
header table, so it exercises the `.pc` reverse lookup end to end.

Still missing versus the Makefile: the binaries are named `server` and `client`
rather than `udp-echo-server` and `udp-echo-client`. That needs `@target`.

### Phase 5 results

`fmake.toml` closes the `@kind` seam and the cross-platform filtering bug, and
`--install` finally gives `@headers` something to do. Verified: two static
libraries built from one overlapping tree with `shared.c` in both and neither
one's private file leaking into the other; a target declared only in the config
with no file rooting it; profiles selecting flags and getting their own object
directories; `exclude` removing a vendored tree before target discovery, so its
stray `main()` never becomes a program; `[toolchain] os` flipping which
platform-specific file is built; and every class of malformed config being
refused with the valid keys named.

Four claims were mutation-tested; three were caught. The fourth — that
`@headers` is gathered for libraries only — was masked by the
install-deduplication, exactly as the Doxygen-marker check was masked by
marker-stripping in phase 3. Both defences produce the same output when a
library and a program publish the same header. A second case covering a header
reachable *only* through a program does discriminate, and now exists.

### Phase 3 results

Two `@target` lines — six lines of comment in total — and fmake now reproduces
that Makefile exactly: `udp-echo-server`, `udp-echo-client`, and two test
binaries, all with correct link sets, libraries and `--wrap` flags, from a
Makefile of roughly 90 lines.

That is the whole thesis of the project in one comparison, so it is worth being
precise about what the remaining six lines buy: nothing that could have been
inferred. A binary's name is a naming decision, not a fact about the code.

Verified separately: `@kind static` producing an archive that links into a
consumer, `@kind shared` producing a working `.so`, a `main()`-free tree
becoming a library on its own, `@os` resolving the platform-duplicate case,
`@sources` reaching a constructor-registered plugin, and `@std`/`@define`/
`@cflags` reaching the compiler.

Four claims were mutation-tested. Three were caught immediately. The fourth —
that directives only count in Doxygen comments — needed the test rewritten:
`@target` is scalar and last-wins, and the Doxygen comment happened to come
last, so the case passed for the wrong reason. It also revealed that the
restriction is enforced twice, by the opener test *and* by marker-stripping, so
only relaxing both makes the test fail.

---

## 12. The exit

`fmake --eject` writes a standalone Makefile to stdout; `--eject ninja` writes
a `build.ninja`. Everything fmake worked out goes in — link sets, per-file
flags, resolved libraries, `--wrap` flags — and nothing in the output refers
back to fmake.

Principle 5 says a tool this opinionated has to be leaveable. A promise to be
leaveable is worth nothing unless it is exercised, so the selftest ejects a
build, deletes `.fmake/`, and runs `make` and `ninja` on trees that fail unless
the emitted flags are genuinely applied.

**It is also the cheapest independent check on the whole model.** If the emitted
build produces working binaries, then the link sets and flags were right —
verified by a second code path that shares nothing with the builder but the
plan. On the reference project it produces four targets whose 13 cmocka tests
pass, does nothing on a second `make`, and rebuilds exactly the three dependents
of a touched header.

That check earned its keep immediately: it found `$(CCFLAGS)` where `$(CFLAGS)`
belonged. Make expands an undefined variable to nothing, so every compile
silently lost its flags, and the reference project still built and passed —
because nothing in it actually needed the `-I`. Only a tree that needs its flags
catches this, which is what the selftest tree is now built to be.

### Stdout, not a file

Writing `Makefile` by default would clobber the hand-written Makefile that fmake
was very likely run beside — the project used to develop this has exactly that —
and a build tool that eats build files is not a good neighbour. So the build
file goes to stdout and progress goes to stderr, which is also what makes
`fmake --eject > Makefile` safe to run twice.

Routing progress to stderr was not optional: the first attempt emitted compile
progress onto stdout and produced a Makefile whose first line was
`[1/6] CC client.c`.

---

## 13. What real projects showed

Everything above was developed against a 6-file reference project. Pointing
fmake at *dunelegacy* — a 292-source, 124k-line C++ SDL game — changed four
things, none of which the small project could have exposed:

1. **The include graph found 3 candidates out of 292.** Both causes are in §3:
   sibling-only header matching, and ignoring angle-bracket project headers.
   Fixed, and the same project now yields 248.
2. **`src/main.cpp` named the target `src`**, whose output path is the source
   directory. Fixed in §3, and writing over a directory is now refused.
3. **A compile failure killed every target.** Per-target resilience had been
   built for link failures only, though the argument is identical — its test
   binary needs cppunit, which is not installed, and that stopped the game
   itself from building.
4. **One missing header produced 248 identical diagnostics.** Compiler errors
   are now grouped by message rather than by file, which turned that wall into
   five distinct problems: two absent libraries, a `std::filesystem` use
   needing a newer `-std`, a generated header, and cppunit.

The build still does not complete, because none of its dependencies — SDL2,
fmt, gsl, cppunit — are installed here and this environment cannot install
them. What was exercised is everything up to and including compilation: target
discovery, the include graph, candidate selection, per-file flags, and error
reporting. Linking and library resolution against a project of that size remain
unverified.

Worth noting what did *not* need changing: the symbol closure, the widening
filter, the caching, and the annotation layer all behaved as designed at 50x
the size. The things that broke were all in the cheap first-guess layer, which
is the part that is allowed to be wrong — it just should not be wrong this
often.

### NetHack: the generator that has to be built first

NetHack does not build here either — 3.7 vendors Lua as a separate download
that a shallow clone does not fetch — but it exposed a structural gap before
getting anywhere near that. Its 303 sources need `onames.h` and `pm.h`, which
are produced by `makedefs`, which is compiled from `util/makedefs.c` in the
same tree.

`[generate.*]` ran commands that had to be installed already, so this was
inexpressible: generators run before anything is compiled, by design, and that
design has no room for a generator that *is* compiled. `uses` (§7) closes it
with a nested build. The gap was worth finding on a project that has it for
real rather than inventing the case.

Also visible from NetHack, without building it: 22 targets discovered across
`util/`, `sys/unix/`, `sys/vms/`, `sys/amiga/`, `sys/msdos/` and an
`outdated/` tree. Per-target compile resilience meant the VMS and Mac
frontends failing did not stop the rest, which is the behaviour the previous
game asked for, working unprompted on the next one.

### Angband: the first one that actually built

dunelegacy needs SDL3, whose mixer is not packaged for Debian at all, so it
could not be linked here. *Angband* — 327 C files, 345k lines, curses only —
needs nothing that was not already installed, and **it builds and runs**:

```toml
[project]
defines = ["USE_GCU"]
exclude = ["src/tests/**", "src/main-nds*.c", "src/main-win.c",
           "src/main-sdl*.c", "src/main-ibm.c", "src/main-xxx.c",
           "src/main-stats.c", "src/win/**"]
```

Ten lines, and `./ang -v` prints its usage. 152 files in the link set,
`-lncursesw` resolved from the symbols, and the optional Borg AI module
correctly left out because nothing reaches it.

Getting there found three more things, two of them real bugs in library
resolution that only a curses program could expose:

- **`libncurses.so` is a linker script whose contents are
  `INPUT(libncurses.so.6 -ltinfo)`** — a bare relative name and a `-l` flag.
  §5's script parser handled only absolute paths, because that is the form
  glibc uses and glibc was the only example to hand. The result was that
  ncurses contributed no symbols at all, the greedy cover picked `-ltinfo`
  alone, and 46 curses symbols went unresolved. All three forms occur on one
  machine.
- **`_GLOBAL_OFFSET_TABLE_` was reported as a missing dependency.** It is
  provided by the linker. On the first Angband build it was the *only* thing
  listed as unresolved, which made a working build read as a failure.
- **The unused-package report contradicted itself**, announcing that ncurses
  was not needed while linking it. pkg-config lists `-lncursesw -ltinfo` and
  only tinfo went unused; a package is now reported as unused only when none
  of its libraries were needed, since linking less than pkg-config asks for is
  the entire point.

Angband also produced the best demonstration of the ambiguity rule working as
intended. It has **84 files each defining `setup_tests`** — every test is its
own program sharing one `main()` — and fmake refused to guess, correctly. The
message was improved to match: dozens of providers means separate programs
rather than one library, and the hint now says so instead of suggesting `@os`.

---

## 14. The chains, checked

Sections 3-7 describe a pipeline: **source → candidate → object → symbol →
link set → library**, with a precedence chain and a cache-key chain running
alongside it. Everything until now was found by pointing fmake at real code,
which only finds what those particular projects happen to do. This section is
the other pass: asking of each chain whether it is *sound* — does it agree
with what the linker would do — and *confluent* — is the answer independent of
arbitrary ordering.

Three of the four properties held. The fourth did not, and neither did two
invariants alongside it.

### Widening terminates and is confluent — holds

`tried` grows monotonically and is bounded by the symbol universe; `units`
grows monotonically and is bounded by the source list; the candidate pool only
shrinks. So the loop terminates, and because `widen_candidates` reads a static
per-file property, no ordering of iterations can produce a different fixpoint.

### The closure was **not** confluent — fixed

The rule established in §3 is *strong wins if one exists, weak is the provider
of last resort*. That was enforced when **choosing** a provider but not when
deciding whether to look for one, which asked only "is this symbol defined by
anything already linked?" — weak or strong alike.

So a weak definition in an object linked for some unrelated reason ends the
search, and a strong definition elsewhere is never found. Which happens
depends on which object was popped first, which depends on the alphabetical
order of an unrelated symbol:

```c
/* hooks.c */   __attribute__((weak)) int hook(void){ return 1; }
                int driver(void){ return 10; }
/* override.c */ int hook(void){ return 2; }   /* the real one */
```

`driver` sorts before `hook`, so hooks.c is linked first and its weak default
silently wins: the program prints 11. Rename `driver` to `zdriver` and the
same program prints 12. That is the weak-override pattern — the single most
common reason to write a weak symbol — resolved by a coin flip, in a design
whose stated rule is that there are none.

The satisfaction test now accepts only a *strong* definition. A weak one
stands only when no strong provider exists anywhere in the pool, which is a
global property and therefore order-independent.

### The cache key was incomplete — fixed

`-fPIC` is added by fmake itself when any target is shared. It was appended to
`cfg.cflags` *after* the configuration key was computed, so it named no object
directory and invalidated nothing. Building only the program and then building
the shared library as well reused the non-PIC objects, and the `.so` was linked
from them. Debian's default `-fPIE` masks the consequence; with PIE disabled it
is a relocation error.

The rule this violated is worth stating on its own: **anything that changes a
compiler invocation must be in the configuration identity, including flags
fmake adds for itself.** The key is now recomputed whenever flags change.

### Precedence was documented backwards — fixed

The chain says `inference < annotations < fmake.toml < CLI`. The compile line
was `(CLI or defaults) + toml + annotations`, and later wins at the compiler —
so the real order was the exact inverse, and `--cflags -O0` could not override
a file that asked for `-O2`. Forcing a debug build, which is the entire purpose
of the flag, did not work.

Fixing it required deciding what the rule actually should be, because both
orderings are defensible. The answer is that they govern different kinds of
fact:

- **Artifact identity** — name, kind, membership — is a project-level
  decision: `inference < annotations < fmake.toml < CLI`. `[target.*] name`
  beating `@target` is right, and already was.
- **Compile flags** are a property of a file, so they run general to specific
  and then override: `defaults / [project] / [profile] < annotations < CLI`.

That is the same line §4 draws between `@cflags` and `@ldflags`, applied to
precedence rather than to scope. `--eject` emits the command-line band as a
separate variable so the ordering survives ejection.

### The link step was still on mtimes — fixed

Everything else in fmake is content-hashed. The link was not: it compared the
output's timestamp against the newest object and skipped if it won. That misses
every change that is not a recompile — a different library resolved, a `--wrap`
added, an explicit `--ldflags` — because none of them touch an object.

`fmake --ldflags '-Wl,--build-id=none'` was accepted, reported success, and did
nothing at all. The link now keys on the whole command plus the contents of
everything it consumes, which is the same rule objects already used.

### A library could hold two definitions — fixed

§3 makes duplicate strong definitions a hard error for programs, on the grounds
that fmake does not guess. `close_over_library` took every member without
looking. Two files defining `compute` produced an archive containing both, `ar`
resolved it by member order, and the consumer inherited the coin flip with
nothing anywhere to say so. Libraries are now held to the same rule, weak
definitions excepted as always.

### `--explain` rendered its own link command — fixed

The command shown and the command run were built by two pieces of code that
happened to agree. Principle 4 is that every decision is inspectable, which is
only true if what is shown is what is executed, so there is now one function
and both callers use it. The test runs the command `--explain` prints and
requires a working binary out of it.

That also exposed something worth stating outright: **`fmake -n` prints link
lines with no `-l` flags.** A dry run compiles nothing, so there are no symbols
to resolve, so resolution is skipped — and the commands printed would not work.
That is inherent rather than fixable, so the dry run now says so.

### The directive table was decorative — fixed

`DIRECTIVE_SCALAR` and `DIRECTIVE_LIST` declared which directives replace and
which accumulate, but every reader picked an accessor by hand, so nothing
enforced the declaration. `Ann` now asserts against the table.

It found existing drift immediately: `--explain` was reading *every* directive
with the list accessor, including `@kind` and `@target`. That worked by
accident, and would have kept working until a scalar directive needed to behave
like one.

### The build was not idempotent — fixed

Include flags were derived from the candidate pool and recomputed on every
widening pass. That looks thriftier than doing it once, and it is wrong twice
over: a file widened in late can contribute an `-I`, so everything compiled
before it was built with a different include path than fmake records, and
because the flags are part of the cache key, the *next* build recompiles those
files for no reason.

So a complete build did not reach a fixed point. Build, build again, and
something compiles.

Include flags are now computed once, over every source in the tree, before
anything is compiled. Stable inputs, stable keys, idempotent builds — verified
on both reference projects, which now compile 6 and 152 files cold and zero
thereafter.

The general rule is the one from `-fPIC`, seen from the other side: if a flag
belongs in the cache key, then it has to be *known* before the thing it keys is
built. A key computed from a value that is still moving is not a key.

### Cross builds need two toolchains, not one

A generator named by `uses` is compiled in order to be *run*, here, on the
machine doing the building. Compiling it with `[toolchain]` — which describes
the machine being built *for* — produces something that cannot be executed.
This is the classic build-versus-host distinction, and generators are the only
place fmake meets it.

`[build-toolchain]` is the answer, and its default is the plain host compiler,
so a cross build with a generator works without declaring anything. It carries
its own flags too, and inherits none of the target's — not a small inaccuracy
to get wrong: `-march=armv8-a` handed to the build machine's compiler does not
compile at all, and neither does a `--sysroot` pointing at the target's
filesystem. What
matters more is that the result is **checked rather than trusted**: whatever
comes out of the nested build has its ELF header compared against this machine,
and a tool that cannot run here is refused by name with the fix in the message.

Verified end to end: an x86-64 generator producing a source file, compiled by
an aarch64 toolchain into a binary that runs under qemu and prints what the
generator wrote.

### One fmake at a time per tree

Two runs in one tree shared `.fmake/cache.json` with no locking. The loser's
writes were simply lost — scan results, symbol tables, resolved libraries, all
recomputed next time — and one run could be reading objects the other was
replacing. An advisory lock on `.fmake/lock`, taken for the whole build and
only at the outermost level so the nested bootstrap does not wait on its own
parent. Waiting costs less than either failure mode, and the second run now
finds the first one's work.

### Some libraries intercept rather than implement

`--explain` offered `-lasan` and `-ltsan` as alternatives to `-lm`. They are
not wrong by symbol evidence: a sanitiser runtime really does export `lgamma`,
`memcpy` and `malloc`, because it interposes on them. But that makes them
candidates in a cover that ranks by coverage, and a program calling enough
intercepted functions could have had one *chosen* — which would link a
sanitiser into an ordinary build.

Interposers are now excluded from resolution outright. You get them by asking
for `-fsanitize`, which is a `--cflags` away, and never by fmake deciding they
looked like the best fit.

The general shape is one §5 did not anticipate: **exporting a symbol is not the
same as implementing it.** Symbol evidence is better than header evidence, but
it is still evidence about names, not about meaning.

### What the exit cannot express, it refuses

fmake itself copes with a space in a path, because it never goes through a
shell — every command is an argv list. The build files it emits are another
matter, and the two backends differ in what they can say.

Ninja escapes a space, colon or dollar in a path with `$`. Make splits
prerequisites on whitespace and has no escaping that survives every position
one can appear in; the emitted Makefile looked like a build file and meant
something else entirely — `all: space test` naming two targets, and a
prerequisite list silently splitting in half.

So `--eject` refuses for Make, names the offending paths, and says that
`--eject ninja` can express them. That is the same stance as §3's
duplicate-symbol error, applied to output rather than input: producing
something that looks right and is not is worse than declining.

### The exit is byte-stable

An ejected build file is something you commit, so it has to be the same file
every time. If it churned — because a set iterated differently, or the closure
discovered files by a different path — every rebuild would show as a diff and
the file would stop being trustworthy.

Checked cold as well as warm, since the cache changes how much widening has to
happen and therefore the order in which files are found: identical across
repeated runs on the reference project, and identical on a 152-file closure
cold versus warm.

### The exit is equivalent, not merely functional

`--eject` was verified by building with `make` and running the result. That
shows the emitted build works, not that it is the same build. Comparing symbol
tables closes the gap: fmake's binaries and the ejected build's are identical
symbol for symbol, on the reference project's three programs and in the
selftest. Dropping the per-file flags from the emitted rules makes the
comparison fail, so it is checking something.

### What this says about the method

All of these were reachable from the design alone; none needed a project to
stumble over them. Most were silent — a wrong link set, a stale object, a stale
binary, an archive with two answers in it — and silent wrongness is exactly
what pointing the tool at more code does not find, because a build that
succeeds looks the same either way.

The general shape of every one: **a decision made in two places, or a fact
declared in one place and used in another.** Strong-versus-weak was enforced
when choosing but not when checking. `-fPIC` was added after the identity that
was supposed to cover it. The precedence chain was written in the document and
inverted in the code. The link command was rendered twice. The directive table
was declared and then ignored. Each was found by asking what the invariant was
supposed to be and then checking that one thing enforced it, which is a
different question from whether any particular project builds.

---

### Writing the tests found the bugs

Auditing what §1–§13 assert against what the suite actually checked was worth
as much as either earlier pass. Five claims had no case behind them at all —
`@ldflags` propagating while `@cflags` does not, `$CC` beating
`[toolchain] cc`, archives not keeping stale members, `@kind exe` requiring a
`main()`, `.fmake/` being gitignored exactly once — and one flag turned out to
be simply broken:

**`fmake -o dist` failed with "cannot open output file."** `-o` names somewhere
to *put* the artifacts, not somewhere that must already exist, and the linker's
message says nothing about the directory being the problem. Nothing had ever
run it.

Two more paths had no coverage: `--eject`'s archive and shared-object branches
— only the program branch had ever executed, in a backend that branches on kind
in both emitters — and `--widen-all` on the macro-generated definition it exists
for.

**An unreadable source file produced a traceback.** One stray file nobody can
read should not stop a tree from building, and if it *is* needed the closure
already has a way to say so: an undefined symbol naming what is missing. Both
now happen, with the file reported either way.

A dangling symlink got through that fix, by a route worth naming because it is
the same shape as several §14 findings: the hash function returns `None` when
it cannot stat a file *and leaves no cache entry behind*, so the scanner
indexed a dict that had never been written to and raised `KeyError` — which is
not an `OSError`, so the handler written for exactly this situation did not
catch it. **An error path that reports failure by returning a sentinel needs
every caller to check it; an error path that raises needs none.** It raises
now.

Empty files, binary files named `.c`, and symlinked directory loops were all
already fine — `os.walk` does not follow symlinked directories, and the
compiler has opinions about the rest.

---

## 15. Open questions

Struck-through entries were closed by later work and are kept because the
reasoning that closed them is part of the record. What remains divides into
three kinds: things nobody has needed yet, things that need a design decision
rather than code, and one lesson about testing.

- **Cost of widening.** Less pressing than it looked: with §3's two fixes the
  include graph identifies 248 of 292 files on a real project, so widening
  covers a remainder rather than doing all the work. Still unmeasured on a tree
  where the guess genuinely fails.
  A project whose include graph is a poor guide pays for
  compiling TUs that turn out to be irrelevant. Bounded by the size of the tree
  and paid once thanks to caching — and the resolved unit set is now cached, so
  later builds start from what widening found rather than re-deriving it. The
  pathological case — a large repo of loosely-coupled files with a small binary
  — still compiles more than Make would on the first build. Worth measuring on
  something big before assuming it is acceptable.
- **The widening filter cannot see header definitions.** It looks for a
  definition in a `.c`/`.cpp`, so a symbol whose definition lives in a header
  (any template instantiation) is invisible to it. Such files are found only if
  something else pulls them in, or via `--widen-all`. Whether that matters in
  practice for C++ projects is untested.
- **The widening filter cannot see a vtable either**, and this one is no
  longer theoretical: §17 found that `_ZTV4Base` is not a string any source
  spells, so nothing scanning for apparent definitions will ever propose the
  file that defines it. moc output sidesteps this by joining the candidate set
  outright. Any other generator whose sole contribution to a program is a
  vtable would need the same treatment, and there is no general mechanism for
  saying so.
- **Static libraries and prebuilt objects as inputs.** A vendored `.a` in the
  tree is a provider of symbols like any other object, and closure should read
  it. Not yet designed, but it looks like it falls out naturally, which is a good
  sign for the model.
- **LTO and `-ffunction-sections`.** Both change what the linker does with the
  object set. Closure should still be correct (it computes what to *offer* the
  linker, which then discards more), but untested.
- **C++ modules.** `import std;` breaks the include-graph candidate heuristic,
  and module dependency scanning needs a real compiler pass
  (`clang-scan-deps`). Note that the *closure* is unaffected — symbols are
  symbols — so this degrades the guess, not the answer, and worst case it falls
  back to compiling the whole tree. Less fatal than it looked before §3 changed.
- ~~**Generated sources.**~~ Closed; see §7. The prediction that it would need a
  two-pass scan was wrong — running the generators before the tree is walked
  makes their output an ordinary source, with no special case downstream.
- ~~**Cross-compilation is started, not finished.**~~ Closed; see §5. Library
  resolution answers for the target machine, verified end to end against a real
  aarch64 toolchain.
- **A tree whose sibling programs reuse class names cannot be built at
  once.** Three of Qt's painting examples each define a class `Window`, so the
  symbol has three strong providers and §3 refuses. Correct, and a real limit
  of one-project-per-tree: `[target.*] sources` is the escape. Whether the
  include graph should break such a tie -- it proposed the right file in every
  case -- is a change to §3 and has not been made.
- **Cross builds are verified on one toolchain, on Linux.** The architecture
  check is architecture-agnostic by construction, but sysroot handling, the
  pkg-config variables and the tool-prefix derivation have only been exercised
  against `aarch64-linux-gnu-*`. A toolchain that names its tools differently,
  or a bare-metal one with no libc at all, is untried.
- **Header-only libraries.** Correctly need no link, and signal 2 naturally
  produces no external symbols for them, so this mostly resolves itself. The
  remaining case is a header-only library that needs `-I` pointing somewhere
  non-standard.
- **Library resolution has no notion of link order.** The chosen `-l` flags are
  emitted in cover order. That is fine for shared libraries but wrong for static
  archives, where the linker is order-sensitive and a cyclic dependency between
  two archives needs one repeated. Untested and probably broken.
- **`-L` is emitted from where the library was found**, compared against
  `cc -print-search-dirs`, rather than from pkg-config's `-L`. That covers
  libraries found by symbol alone as well as by package, but it is only as
  good as the directory list fmake scans — a prefix it never looks in cannot
  be resolved at all, and still needs `--ldflags`.
- **Linker scripts are parsed, not executed.** `INPUT`, `GROUP` and
  `AS_NEEDED` are read for filenames and `-l` flags; anything else in the ld
  script language is ignored. That covers glibc and ncurses, which is what
  exists in practice, but it is pattern-matching rather than understanding.
- **The linker-symbol list is hand-written.** `_GLOBAL_OFFSET_TABLE_`, `_end`
  and friends are filtered by name. A toolchain providing something not on the
  list would report it as a missing dependency.
- **The symbol scan is Linux/ELF-shaped.** `libNAME.so`, ld scripts, and
  `ldconfig`-style layout. macOS (`.dylib`, two-level namespaces) and Windows
  are unhandled.
- **Ejected builds are a snapshot, not a translation.** They contain the plan
  fmake computed for the tree as it stood, with one explicit rule per object.
  Adding a source file means ejecting again — there is no pattern rule, and
  there cannot be one, because per-file `@cflags` is the whole point. Nor does
  the ejected build know how to re-run the closure, so a new symbol dependency
  is invisible to it.
- **`--eject` emits no install rule**, and the `clean` rule removes only what
  it knows about.
- **Install is minimal.** No uninstall, no manifest, no pkg-config `.pc`
  generation, no shared-library versioning or `SONAME`, no symlink chain
  (`libfoo.so.1.2` → `libfoo.so`). A `.so` installs under its plain name, which
  is right for a private library and wrong for a published one.
- **Per-TU flags are per TU, not per target.** Two binaries sharing 90% of their
  TUs compile those once, and `@cflags`/`@define` belong to the *file*, so there
  is exactly one object per file and no conflict. What is impossible is the same
  file compiled two ways for two targets — that needs per-target object
  directories, and nothing asks for it yet. `-fPIC` sidesteps the question by
  being applied tree-wide whenever any target is shared.
- **A library ignores `@sources` and the closure alike.** It contains everything,
  so neither has anything to do. That is right for now, but a large tree with one
  small shared object in it would want the closure back, seeded from `@headers`.
  That was the original §3 design for libraries and it is still the better answer
  for that case; it needs matching header declarations to mangled symbols, which
  is why it is not built.
- ~~**`@kind` is per TU but describes an artifact.**~~ Closed by
  `[target.*] sources` in §7: membership is declared where it is known, and the
  closure is not consulted for those targets.
- **Directive typos are silently inert.** `@lib` for `@libs` does nothing and
  says nothing, because unknown commands must be ignored for the Doxygen
  integration to work at all. `--explain` listing what was recognised is the only
  mitigation, and it requires the user to go looking.
- **Symbol-invisible dependencies generally.** §3 lists the constructor-plugin
  case, but the family is larger: anything reached only through `dlopen`, a
  linker script, or a function pointer table built at runtime. All need
  `@sources`. Whether that one directive is a sufficient answer for all of them
  is unproven.
- **Generated outputs are not cleaned.** `--clean` removes `.fmake/`; files a
  generator wrote into the tree stay, because fmake did not create the
  directory and will not guess what else is in it. The ejected Makefile does
  remove them, which is an inconsistency.
- **A generator's own dependencies are not tracked.** A `.y` that `%include`s
  another file re-runs only when the `.y` itself changes; the rest must be
  listed in `depends` by hand. There is no depfile equivalent for generators.
- **A build with a permanently broken file never reaches a fixed point.**
  A file that failed to compile is retried on every build, because the fix
  might be outside it — an installed header, a corrected include path — and a
  cached failure would hide that. Correct, but it means §8's
  build-twice-compiles-nothing property holds only for trees that build.
- **A fixture that quietly tests nothing is the hardest kind of wrong.** The
  library-signature case took three attempts, and both failures were the
  fixture rather than the tool: first the library's source sat inside the
  scanned tree, so widening compiled it directly and the resolver was never
  consulted; then the fixture recreated that source on its second call,
  reintroducing the same problem after it had been fixed. In between, the
  change looked unverifiable and was nearly reverted. A test that passes
  because it exercises nothing is indistinguishable from one that passes
  because the code is right — which is the entire argument for mutating the
  code and requiring the test to fail.
- **Two hand-written lists are load-bearing**, soon three: linker-provided
  symbols (§14), interposer libraries (§14), and the builtin header table (§5).
  All are "things that look like providers but are not, or are not but are."
  A fourth would be the signal that the provider model wants a real predicate
  rather than another list, and the threshold is stated here so it is agreed in
  advance rather than argued about at the time.
  **§17 did not trip it.** `Q_OBJECT` and the Qt `.pc` module names are a
  *generator trigger* — what to run and where to find it — not another class of
  thing that looks like a provider and is not. The provider model was untouched
  by moc, and needed no new `HEADER_PKG` entry to resolve Qt. The threshold
  stands where it was.
- ~~**`uic` is out of scope on a premise the sample contradicts.**~~ Closed;
  see §17. The answer to "what proposes a `.ui` file" was that the source
  already does — `#include "ui_thing.h"` — so it is an inference after all,
  just from the include graph rather than from a symbol.
- ~~**`rcc` is the one piece of Qt tooling that must be told.**~~ Closed; see
  §17. One of the two signals really is absent — a resource registers itself
  from a static constructor, so no symbol refers to the generated object —
  but the other is not, and a resource path in the source turned out to be
  enough to decide which program opens it.
- **Resource evidence is textual, and that is a real limit.** A path built
  with no `":/..."` literal anywhere, and no `Q_INIT_RESOURCE`, leaves nothing
  to go on. `--force-link` still covers it, but unlike the symbol closure
  there is no guarantee here, only good evidence.
- **`[build-toolchain]` is only consulted for generator tools.** Nothing else
  in fmake distinguishes the build machine from the target, because nothing
  else needs to yet. A test binary meant to run during the build would.
- **A test that split on a substring hid a working feature.** The `--explain`
  libraries header reads `[from the external symbols above]`, so
  `split("external symbols")[0]` truncated the output above the very lines it
  was meant to check, and the case failed while fmake was right. The diagnostic
  `sed` range used to investigate had the identical flaw, which is what made it
  slow to find. Assertions on `--explain` now split on a line-anchored pattern.

---

## 16. Working on this

The sections above record how the design was arrived at. This one records how
the work was done, because that lived only in commit messages and would not
survive being picked up cold.

### The files

| | |
|---|---|
| `fmake` | the tool; one file, stdlib only, Python 3.11+ |
| `selftest` | the suite; one case per claim this document makes |
| `README.md` | how to use it |
| `project.md` | this: why it works the way it does |
| `LICENSE` | GPL-2.0-or-later, matching the SPDX headers |

Version is a literal in `fmake` (`VERSION`), currently 0.1.0. `fmake -V` prints
it with the author and licence.

### The rule that produced most of the findings

**Every fix gets a case, and the case must fail when the fix is reverted.**
Not "the tests pass" — the test is only evidence if removing the behaviour
makes it fail. Mutate the code, run the case, confirm it goes red, restore.

This caught more than it prevented. Twice a case that appeared to pass was
exercising nothing at all: once because a library's source sat inside the
scanned tree so widening compiled it directly, once because the fixture
recreated a file it had deliberately deleted. Both looked green. Neither was
testing anything. A test that passes because the code is right and one that
passes because it tests nothing are indistinguishable without this step.

It also found drift the other way. Adding assertions to `Ann` — so the
scalar/list table would be enforced rather than decorative — failed
immediately on existing code that had been reading every directive as a list.

### Running it

```sh
./selftest            # ~3 minutes, one case per core
./selftest closure    # cases whose name contains "closure"
./selftest -j1 -k     # serially, keeping the scratch trees
```

It was ~50s at 79 cases and is ~3 minutes at 130, because the cases added
since are the expensive kind: cross compiles, ejecting a build and running
`make` or `ninja` over it, and the Qt cases, which compile C++ against Qt
headers. Filtering by name is the way to work — `./selftest rcc` is seven
cases and a few seconds — and the full run is for before a commit.

Cases needing something absent from the machine skip rather than fail — a
cross toolchain, `ninja`, a library, Qt. A skip is not a pass; check the
count.

Mutations go through a script reading before-and-after text from files, not
through a shell heredoc. Three separate incidents came from `\n` collapsing or
a multi-line anchor breaking while being quoted through nested layers, each
costing more than the bug being fixed. **Edit `selftest` with an editor, not a
generated patch.**

### Commits

Bodies are prose: what broke, why, what changed, what was verified, and an
explicit "not implemented / known limits" list for anything substantial. The
limits sections are where most of §15 came from. No AI attribution or
trailers of any kind.

### The reference projects

None are vendored; they are fetched into scratch directories and are not part
of this repository.

| | |
|---|---|
| `xplore-c-example/udp-echo` | 6 files, cmocka tests. The working reference: builds, links, 13 tests pass. |
| **Angband** | `github.com/angband/angband`. 327 files, 345k lines, curses only. Builds and runs with ten lines of `fmake.toml` — needs `@define USE_GCU` and an exclude list for `src/tests/**` and the non-Linux frontends. |
| **dunelegacy** | `github.com/henricj/dunelegacy`. 292 files, C++/SDL3. **Cannot be linked here**: SDL3_mixer is not packaged for Debian at all. Everything up to and including compilation was exercised. |
| **NetHack** | `github.com/NetHack/NetHack`. **Cannot be built here**: 3.7 vendors Lua as a separate download a shallow clone does not fetch. It is what motivated `uses`. |

A cross toolchain (`aarch64-linux-gnu-*`) and `qemu-aarch64` are installed and
the cross cases depend on them.

### What a fresh start should read first

§3, then §14. The first is the whole design; the second is where it was
checked against itself and lost, which is the better guide to where the next
bug will be.

---

## 17. Qt, and what moc costs

Added on request, after an assessment written from outside the project argued
that moc was the whole blocker for Qt and that fmake's model made it cheap.
That turned out to be right, and the measurements below are the check rather
than the claim.

### Why moc fits §3 instead of fighting it

moc reads a class carrying `Q_OBJECT` and writes the signals, the
introspection and the `QObject` plumbing that class promised. The reason this
is painful in an include-graph build is that **nothing includes the output** —
somebody has to list it, which is what `HEADERS` in a `.pro` file and
`AUTOMOC` in CMake exist to do.

fmake does not decide link sets from the include graph, and the relationship
here is exactly a symbol relationship. Compiling a `Q_OBJECT` class without
moc leaves undefined:

```
_ZN7Counter7changedEi            Counter::changed(int)    the signal body
_ZTV7Counter                     vtable for Counter       key-function rule
_ZN7Counter16staticMetaObjectE   from the calling TU
```

and `moc_counter.o` defines all three. Measured on that program, the set moc
provides minus the set the class leaves undefined is **empty**. So the closure
links a moc object for the same reason it links anything, and there is no
Qt-shaped special case anywhere in the link step. Two consequences fall out:

- **It is more correct than qmake**, which mocs and links everything in
  `HEADERS` whether the class is reachable from that binary or not. Here a
  class no program constructs is moc'd, compiled, and then dropped by the
  closure — `--explain` lists it under *compiled, not linked*.
- **The payoff is highest for a tree of many small programs over one shared
  body of Qt code**, which is the case existing tools handle worst. The
  assessment measured a real project whose 21 test drivers each listed the app
  sources, so CMake compiled all 58 into 21 object directories — about 1200
  compilations of the same files, 19m17s wall against 6m57s once they shared
  one archive. fmake would never have compiled it twice, because "compile each
  TU once, link the closure per program" is what it does by construction.

The honest framing is therefore not *fmake builds Qt* but **fmake builds trees
of Qt programs without a build file**.

### Two signals, same division as library resolution

The scan proposes: `Q_OBJECT`, `Q_GADGET` or `Q_NAMESPACE` in a file means run
moc on it, matched against the comment-stripped text for the same reason
`main()` is. The symbols decide: output nothing refers to is compiled and then
dropped. A `Q_OBJECT` behind an `#if 0` therefore costs one moc run and can
never reach a binary.

### What the assessment did not cover

Two shapes it missed, both real and both in the suite now.

- **`Q_OBJECT` inside a `.cpp`.** The output is `foo.moc`, and Qt requires
  that file to `#include` it — so it is text pulled into an existing TU, not a
  TU of its own. It must land on that file's include path and must never be
  compiled separately. A source declaring such a class without the include is
  a project bug, and is named as one rather than left to fail later on an
  undefined symbol that mentions none of this.
- **The `#include "moc_foo.cpp"` idiom.** An older habit ends `foo.cpp` with
  the moc output to save a translation unit. Compiling it as well defines
  every meta-object twice, and §3 would report that as an ambiguous provider —
  a baffling way to say a file is already in the build.

### What the mutation pass found

Reverting each behaviour in turn caught everything except one line, and the
escape was the most interesting result of the exercise.

**Widening cannot be relied on to discover moc output.** Removing the line
that puts moc output into the candidate set broke nothing, because widening
found it anyway — widening picks extra files by scanning for apparent
*definitions*, and `Foo::staticMetaObject` looks like a data definition to the
regex. So every fixture that emitted a signal was rescued by accident. A class
whose only debt to moc is its **vtable** is not: no regex sees a vtable,
`_ZTV4Base` is not a string any source spells, and the build fails to link
having compiled everything it was asked to. The case now pins exactly that
shape.

The other finding was smaller and would have been permanent. Told to write to
a real path, **moc creates the output file and then leaves it empty** when it
finds no relevant classes — it only says "No output generated" when writing to
a device. Treating absence as the signal is therefore not enough: an empty
translation unit was being compiled, listed in every report, and re-moc'd on
every build for want of a remembered negative result.

### Decisions worth keeping

**Output lives in `.fmake/moc/`, mirroring the tree.** It is a build artifact,
so `--clean` should take it and git should never see it. Mirroring rather than
flattening is what stops `a/thing.h` and `b/thing.h` both wanting to be
`moc_thing.cpp`.

**moc is located through pkg-config, not `$PATH`.** Debian ships no `moc` on
`$PATH` at all — it lives in Qt's libexec — and where a distribution does
provide one, qtchooser makes which Qt it belongs to a property of the
environment rather than of the build, so a tree resolving to Qt 6 can be moc'd
by Qt 5 and fail on a mangling that never matched. `pkg-config
--variable=libexecdir Qt6Core` already knows. Nothing in a source
distinguishes Qt 5 from Qt 6 — the include spellings are identical — so the
newer is tried first and `[toolchain] moc` exists for when that is wrong.

**`--eject` learned moc rules rather than shipping the generated files.** The
assessment suggested emitting already-generated sources as ordinary ones and
called it the cheaper contract; it is cheaper and it is wrong. It would leave
a standalone Makefile reading out of `.fmake`, which `fmake --clean` deletes
and git never sees. Ejected builds therefore carry `MOC`/`MOCFLAGS` and one
rule per output, relocated under the ejected object directory, and both
backends were verified to build and run from a clean tree with no `.fmake`
present.

### Flags: two predictions that did not hold here

The assessment expected Qt to need `-fPIC` and `-std=c++17` as special cases.
Neither was necessary on this machine, and both were checked rather than
assumed: Debian's gcc defaults to PIE, so the no-PIC build linked and ran, and
gcc 14 defaults to `gnu++17`, so Qt 6's C++17 minimum is met without asking.
Both would matter on a distribution that defaults differently, and neither has
been special-cased on the grounds that an unnecessary flag in the
configuration identity is a silent cause of rebuilt objects. This is a limit,
not a claim that the flags never matter.

Include paths and `-l` flags needed nothing new: `#include <QObject>` resolved
to `Qt6Core` through the existing header-to-package machinery, with no entry
added to `HEADER_PKG`.

### What was deliberately left out

- ~~**`uic`.**~~ Implemented; see "uic, and what the include already says"
  below. It was left out on the assessment's view that Qt Widgets code
  frequently has no `.ui` at all, which did not survive contact with a
  sample.
- ~~**`rcc`.**~~ Implemented; see "rcc, and the resource nobody references"
  below. The claim that nothing in the source says which program a `.qrc`
  belongs to was wrong: the paths it opens do.
- **QML and Qt Quick.** `qmltyperegistrar`, `qmldir` generation and
  `qmlcachegen` are a protocol, not a rule, and deeply CMake-coupled in Qt 6.
  Out of scope, and said so rather than half-supported.
- **Feature probing.** A project whose optional dependencies are `-D` before
  they are `-l` — where the code does not *exist* when the library is absent —
  needs a probe-then-define step. Symbol inference answers *what do I link*;
  it cannot answer *what do I compile*. Outside fmake's core rule, and not a
  Qt problem.

### Limits

- Exercised against Qt 6.8 on Debian only. Qt 5 is coded for and untested.
- On a cross build the moc that pkg-config names may be a target binary that
  cannot execute here; `[toolchain] moc` is the answer and the failure is
  reported with that pointer, but the case is untested.
- moc's include path is best effort. It runs its own preprocessor but does not
  fail on an include it cannot resolve, so a missing `-I` costs an unexpanded
  macro rather than an error — which is what makes it safe to settle these
  flags before the include graph exists.
- `#if 0` is the tested case for scan-and-preprocessor disagreement. Other
  conditional shapes are handled by the same negative-result path but were not
  enumerated.

### Tried on a real project: qView

`github.com/jurplel/qView`, a Qt 6 Widgets image viewer: 33 translation units
after excludes, 15 classes declaring `Q_OBJECT`, 7 `.ui` files and one `.qrc`.
It builds and runs.

**What it needed**, which is the honest measure:

```make
# fmake.mk -- Qt's other two generators, which fmake does not run itself
src/ui_%.h: src/%.ui
	/usr/lib/qt6/libexec/uic $< -o $@

resources/qrc_resources.cpp: resources/resources.qrc
	/usr/lib/qt6/libexec/rcc --name resources $< -o $@
```

plus three `defines` that `target_compile_definitions` supplies, two excludes
(`tests/**` wants QtTest, and a win32 file), and `--force-link` for the
resource — nothing references it, because it registers itself from a static
constructor, exactly as predicted above. About eight lines in total, and
**moc needed none of them**.

**What was confirmed.** fmake found precisely the same 15 `Q_OBJECT` classes
as CMake's AUTOMOC — same set, discovered from the source rather than from a
list. The two binaries have identical direct Qt dependencies
(`Core Gui Network Widgets`) and both run. Worth being exact about the Svg
case: CMake *asks* for `Qt6::Svg` and the linker's `--as-needed` throws it
away, while fmake never asks, having found no symbol that needs it — the
binaries agree, and fmake reached the answer by reasoning rather than by the
linker discarding the mistake. SVG files still load, because that support is
a runtime image-format plugin which links Qt6Svg itself.

**Where it is slower.** Clean build 33.9s against CMake's 27.4s including
configure; incremental with nothing changed, 0.45s. The gap is structural and
not a defect: CMake concatenates every moc output into one
`mocs_compilation.cpp`, so it compiles 19 TUs where fmake compiles 33. Fewer,
larger TUs win for a single binary. One TU per class is what makes the
closure able to drop a class no program reaches — which paid nothing here,
since all 15 were reachable, and would pay on the many-small-programs tree
this is supposed to be good at. That case is still unmeasured.

**An accident worth recording.** qView's own CMake build *fails* on this
machine. `find_package(Qt6 QUIET COMPONENTS LinguistTools)` sits inside the
`if(Qt6_FOUND)` branch and clears `Qt6_FOUND` when the optional tool is
absent, so a later test appends the **Qt5** `X11Extras` target to a Qt 6 build
and generation dies. Installing the translation tools would hide it. It is a
bug in that file rather than a limitation of CMake, and the comparison above
was made after patching it — but it is a fair illustration of the premise:
fmake had nothing to get wrong there, because it has no configure step and
takes its facts from the source.

### uic, and what the include already says

Left out at first, on the assessment's view that a generated header is an
include-graph dependency rather than a symbol one and that Qt Widgets code
frequently has no `.ui` anyway. The first half is true and turned out not to
matter; the second half is false. Every project examined uses Designer —
qView 7 files, smplayer 43, KeePassXC 72 — so a tree needing uic is the
common case rather than the exception, which made "write two pattern rules
yourself" a poor answer.

**The trigger is the include, not the file extension.** `#include
"ui_thing.h"` naming a header that exists nowhere in the tree, with a
`thing.ui` that would produce it, is the source asking for uic in as many
words. It is the same thing CMake's AUTOUIC keys on, and it keeps the feature
inside the premise: the source says what it needs, and fmake does not go
looking for work nobody asked for. Three consequences, all wanted:

- a `.ui` nobody includes is not built, so a directory of unused designs or a
  stray file in a vendored subtree costs nothing;
- a `ui_thing.h` someone committed is left alone rather than overwritten or
  shadowed — projects do commit generated headers, and replacing what the
  tree says with what fmake would have said is not fmake's call;
- a tree with no `.ui` files never looks for uic at all.

Where moc could fall back on symbols, uic cannot: nothing is undefined if the
header is missing, the compile simply fails. So the include has to be
believed, and the one thing that cannot be resolved is refused rather than
guessed. **Output is flat**, in `.fmake/ui/`, because `#include "ui_thing.h"`
is unqualified: two `thing.ui` in one tree are ambiguous in the C++ itself,
not merely awkward on disk. Mirroring the tree would hide that; instead both
candidates are named and the build stops.

### Two bugs this turned up

Neither was about uic, and one was not about Qt at all.

**Per-TU flags were dropped on anything widening found.** They were computed
once, over the candidate set, before the widening loop had run — so a file the
include graph missed was compiled with no `@define`, `@cflags`, `@std` or
`@pkg` at all. Nothing downstream reads the annotations again, so there was no
error: the program built cleanly and answered differently. Demonstrated in
plain C with a `@define SCALE=7` that a widened file never received, printing
1 instead of 7. The flags are now computed wherever a unit enters the pool.
This is the §14 pattern exactly — a chain that is right at every step except
the one nobody asked about.

**An included moc output was found through a global include path.** `#include
"foo.moc"` is unqualified and the file is not in the including directory, so
two `local.cpp` in different directories each resolved to whichever `.moc`
sorted first. It goes on the include path of the files that actually include
it and nowhere else — which needs the *includers* rather than the input,
because the `#include "moc_foo.cpp"` idiom has moc read `foo.h` while
`foo.cpp` does the including. Getting that distinction wrong broke the idiom
case, and the case caught it.

A third thing was wrong and is now fixed: **the generators ran before the
exclusion filter**, so a subtree named in `[project] exclude` still had its
classes moc'd and its designs generated — and moc output for an excluded
header would then have been compiled, which is the work the exclude existed
to prevent.

### qView again, with both generators

The whole configuration is now four lines of `fmake.toml` and one `fmake.mk`
rule:

```toml
[project]
exclude = ["tests/**", "src/qvwin32functions.cpp"]
defines = ["VERSION=7.0", "QT_DEPRECATED_WARNINGS", "QT_NO_FOREACH"]
```

```make
resources/qrc_resources.cpp: resources/resources.qrc
	/usr/lib/qt6/libexec/rcc --name resources $< -o $@
```

plus `--force-link` on the resource. moc found the same 15 classes as before,
uic the same 7 headers CMake generates, and the binary runs. Clean build 34.4s
against CMake's 27.4s, unchanged — uic was never the expensive part.

What was left at that point was `rcc`, which the next section takes up.

### rcc, and the resource nobody references

Left out twice, on the reasoning that both signals were missing. Half of that
was right and half was not, and the half that was wrong is the interesting
one.

**The symbol really is absent.** In Qt 5 and 6 a resource registers itself
from a static constructor — the generated source has an `.init_array` entry —
so `Q_INIT_RESOURCE` is only needed for static libraries, and in the common
case no object refers to `qInitResources_foo` at all. §3 alone will therefore
always drop it: the closure is exactly right and the answer is exactly wrong,
which is the same shape as the constructor-registered plugins `--force-link`
already exists for.

**The other signal was there all along.** A `.qrc` declares the paths it
provides, and code that uses a resource names one:

```
resources.qrc declares  /fonts/Lato-Light.ttf
qvaboutdialog.cpp says  ":/fonts/Lato-Light.ttf"
```

That is the same division as library resolution and as moc — one side
proposes, the other decides — and it is *per file*, which is what makes it a
per-program answer rather than "link every resource into every binary". The
literal is matched against the whole declared path **and as a directory
prefix**, because most real code assembles the name at runtime and the only
literal that survives is `":/icons/"`. String literals are kept by the comment
scan, so a path mentioned in a comment is correctly not a use.

`Q_INIT_RESOURCE(name)` is taken as evidence too, and it is the exact kind:
it compiles to an undefined `qInitResources_name`, so once rcc has run the
closure links the object for the ordinary reason with nothing asserted. It is
read textually only to decide that rcc must run at all.

**How the link decision is made.** The closure is computed, then asked whether
any file in it opened a resource, then recomputed with those objects seeded.
One extra pass, and it cannot loop: rcc output refers to Qt and to nothing in
the tree, so it can never widen anything. `--explain` reports the evidence
rather than the conclusion:

```
  resources
    resources/resources.qrc         "/fonts/Lato-Light.ttf" in src/qvaboutdialog.cpp
```

**Freshness includes the embedded files**, not just the `.qrc`. rcc copies
their contents into the generated source, so keying on the `.qrc` alone would
bake a stale icon into every binary and never mention it.

**The limit worth stating**: this is textual evidence, not a proof. A resource
path assembled with no `":/..."` literal anywhere and no `Q_INIT_RESOURCE`
leaves nothing to go on, and the resource will be missing at runtime rather
than at the link — measured: the program builds and exits 2 asking for a file
that is not there. The remedy is `Q_INIT_RESOURCE(name)`, one line and Qt's
own mechanism. `--force-link` does **not** cover it, which was written here
first and is wrong: with no evidence rcc never runs, so there is no generated
source to force, and naming one is refused with *is not a source file in this
tree*. Everywhere else in fmake the
answer is derived from what the compiler and linker actually produced; here it
is derived from what the source appears to say, and that difference should not
be blurred.

### qView, finally, with no build file

The whole configuration is now:

```toml
[project]
exclude = ["tests/**", "src/qvwin32functions.cpp"]
defines = ["VERSION=7.0", "QT_DEPRECATED_WARNINGS", "QT_NO_FOREACH"]
```

Two excludes for files that are not for this platform or this build, and
three defines `target_compile_definitions` supplies. **No `fmake.mk`, no
`--force-link`, and nothing about Qt.** 15 classes moc'd, 7 designs generated,
one resource embedded — verified by finding the font data inside the binary —
and it runs. Clean build 39s against CMake's 27s, the gap still being one moc
TU per class against CMake's single concatenated one.

Both remaining lines are the kind §17 said they would be: exclusions and
feature defines, which symbol inference answers nothing about because they
decide *what is compiled* rather than what is linked.

### A sweep: Qt's own examples

qView is one program. The claim that matters is the other one — many small
programs over shared code — so the next test was Qt's own widgets examples,
which have no dependency but Qt: **74 programs, 201 sources**, built one at a
time with no configuration at all.

**66 of 74 built.** The eight that did not divide as follows, and only the
first was fmake's fault:

- **6 — `#include <QtWidgets>` did not resolve.** A real bug, below.
- **5 — `painting/*` share a helper library** in a sibling directory, so
  pointing fmake at one example puts the shared code outside the tree. Not a
  defect; the wrong invocation. Covered separately below.
- **2 — `rhi/*` need `rhi/qrhi.h`**, a Qt private header that is not on the
  public include path.
- **1 — `qnx/foreignwindows`** needs `screen/screen.h`, which exists only on
  QNX.

(An earlier run scored 54 of 73 against the `dev` branch, where a dozen
examples use Qt 6.10 APIs that Qt 6.8 does not have. That number measured my
choice of branch, not fmake, and is recorded here only so the improvement is
not mistaken for a larger one than it was.)

### The bug the sweep found

`#include <QtWidgets>` — the module umbrella header, which six of Qt's own
examples use — did not resolve, and the reason was one word.

Header-to-package resolution walks the include directories every `.pc` file
declares and asks whether the header is there. It asked with `os.path.exists`.
Qt keeps every module under one parent directory with a *directory* per
module, so `<qt6>/QtWidgets` exists — as a directory. The parent is listed by
every Qt `.pc` file, and the first one to claim it wins, which alphabetically
is `Qt6Concurrent`. So `<QtWidgets>` was attributed to Qt6Concurrent, whose
flags carry `-I<qt6>` and `-I<qt6>/QtConcurrent` but not
`-I<qt6>/QtWidgets` — and the header then did not resolve at all. A
misidentified package that announces itself as a missing file.

The fix is `os.path.isfile`: a directory is not a header.

**Two other changes were tried and removed**, which is the more useful part of
the record. Iterating the include directories longest-first, and a rule giving
a qualified include to the module whose directory it names, both looked
reasonable and both turned out to be redundant — with `isfile` in place
neither changed any observable behaviour, so no mutation could make their
tests fail. A test that cannot fail is worse than no test, and §16 already
records two of those. They came out, and the one line that carries the fix is
mutation-checked on its own.

### Shared code across many programs, on real code

`examples/widgets/painting` is the shape the whole feature was argued for:
nine programs over one `shared/` helper. Pointed at that directory, fmake
compiles `shared/arthurwidgets.cpp` **once** and links it into every program
that reaches it — verified by counting objects on disk (one) against link sets
(four targets, six shared files each, including the shared moc output and
`shared.qrc`). The programs run.

Two things had to be said to get there, and both are honest:

- `-o out`, because a program named after its directory cannot be written
  where a directory of that name already is. fmake refuses rather than
  clobbering it, which is the right answer and a good message.
- The nine cannot all be built at once. `basicdrawing`, `painterpaths` and
  `transformations` each define a class called `Window`, so `Window::Window()`
  has three strong providers and §3 refuses to guess. That is correct — the
  tree really is ambiguous — but it is a real limit of treating a tree as one
  project, and `[target.*] sources` is the answer.

### The two projects that could not be tried here

- **smplayer** — 194 sources. fmake's discovery was exactly right:
  **126 moc, 43 uic, 3 rcc**, matching the project's own counts. It cannot
  compile here because 32 files use `QRegExp`, which needs the
  `Qt6Core5Compat` headers (`qt6-5compat-dev`, not installed).
- **KeePassXC** — 390 sources, 252 `Q_OBJECT` headers, 72 `.ui`. Needs
  botan-3, argon2, qrencode and minizip, none of which are installed.

Both are packaging gaps rather than findings, but the smplayer number is worth
keeping: the generator discovery scales to a 194-file project and agrees with
qmake exactly.
