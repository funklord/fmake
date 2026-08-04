# fmake

A build tool for C and C++ programs that shouldn't need a build file.

```sh
$ ls
main.c
$ fmake
[1/1] CC  main.c
LD  hello
* built hello
```

One file, no dependencies beyond the Python 3.11 standard library. Copy it
into `$PATH` and run it in a directory containing source.

```sh
curl -o ~/.local/bin/fmake https://.../fmake && chmod +x ~/.local/bin/fmake
```

---

## What it works out on its own

Every translation unit defining `main()` at file scope is a program, named
after the file — or after the containing directory when the file is `main.c`.
Everything else follows from the symbols.

**The link set is not guessed.** Objects are compiled, their symbol tables read
with `nm`, and the link set is the transitive closure from the root's object:
for each undefined symbol, link whatever object defines it, and repeat. That is
the same computation the linker performs when deciding which members to pull
out of an archive, so it is exact rather than heuristic — it copes with one
header implemented across three files, with `util.h` implemented by
`util_posix.c`, and with no header at all.

**Libraries come from the symbols too.** An undefined `SDL_Init` proves SDL is
called; `#include <SDL.h>` only proves a declaration was wanted. Includes
supply the `-I` flags, symbols decide the `-l` flags, and a header whose
library nothing calls is reported and not linked.

Run `fmake --explain` to see every decision, down to the exact command line.

---

## Saying the things it cannot know

Three places, divided by what a fact *is* rather than by syntax.

### In the source file — facts about that file

Doxygen-format comments, so the same comment documents and builds. Only
Doxygen's own markers count (`//!`, `///`, `/*!`, `/**`), and unknown commands
like `@brief` are ignored.

```c
/*! @file
 *  @target  myapp
 *  @pkg     sdl2 >= 2.0.18
 *  @libs    m
 *  @std     c17
 */
```

| Directive | Means |
|---|---|
| `@target NAME` | Name of the artifact this file roots |
| `@kind exe\|shared\|static` | What to build; inferred from `main()` otherwise |
| `@pkg NAME [OP VER]` | pkg-config dependency, version constraint optional |
| `@libs NAME…` | Raw `-l`, for libraries with no `.pc` file |
| `@cflags …` | Compile flags for this file |
| `@ldflags …` | Link flags, propagated to anything containing this file |
| `@define NAME[=VAL]` | Convenience for `-D` |
| `@std c17\|c++20\|…` | Language standard |
| `@os NAME…` / `@arch NAME…` | Build this file only on matching platforms |
| `@sources GLOB…` | Force files into the link that no symbol reaches |
| `@headers PATH…` | A library's public headers, for `--install` |
| `@rule …` | A build rule, in Makefile syntax (below) |

`fmake --doxygen-aliases` emits an `ALIASES` block so Doxygen renders these
instead of warning about them.

### `fmake.mk` — rules, and flags for the whole project

Makefile syntax, deliberately a small subset: explicit rules, pattern rules,
`.PHONY`, and `$@ $< $^ $*`. No variables, no functions, no conditionals — so
it cannot grow into a program. Recipes are shell.

```make
@std    c17
@libs   m

gen/%.c: proto/%.msg
	python3 tools/gen.py $< $@

.PHONY: flash
flash: firmware
	avrdude -c usbasp -p m328p -U flash:w:$<
```

`fmake flash` builds the prerequisites and runs the recipe. A directive here
applies to the whole project; ones that describe a single file or artifact
(`@target`, `@kind`, `@os`, `@arch`, `@sources`, `@headers`) belong in the
source file or in `fmake.toml`.

The same rule can live in a source comment instead, which is what `@rule` is
for — it goes through the same parser:

```c
/*! @rule gen/table.c: data/table.txt
 *        python3 tools/mktable.py $< $@
 */
```

### `fmake.toml` — the structured things

For facts that belong to no single file and need tables.

```toml
[project]
cflags  = ["-Wall"]
exclude = ["vendor/**"]

[profile.release]
cflags  = ["-O2"]
defines = ["NDEBUG=1"]

[target.alpha]                  # two libraries from one overlapping tree
kind    = "static"
sources = ["src/alpha.c", "src/shared.c"]

[install]
prefix = "/usr/local"

[toolchain]                     # cross-compiling
cc   = "aarch64-linux-gnu-gcc"
arch = "aarch64"

[build-toolchain]               # tools that must run on *this* machine
cc = "cc"
```

Unknown keys are an error, with the valid ones named.

---

## Qt

`Q_OBJECT` in a class is all the declaration Qt needs. No `HEADERS` list, no
`AUTOMOC` switch, no build file.

```sh
$ ls
counter.h  main.cpp
$ fmake
MOC counter.h
[1/2] CXX .fmake/moc/moc_counter.cpp
[2/2] CXX main.cpp
LD  app
* built app
```

moc runs on whatever declares `Q_OBJECT`, `Q_GADGET` or `Q_NAMESPACE`, uic on
whatever a source includes a `ui_*.h` for, rcc on whatever a source opens, and
**the symbols decide what happens next** — the generated object joins the link
because something needs `Counter::staticMetaObject`, not because it is called
`moc_*`. A class no program constructs is moc'd, compiled, and then left out;
`--explain` lists it under *compiled, not linked*. That is stricter than qmake,
which links everything in `HEADERS` whether it is reachable or not.

A class declared inside a `.cpp` works too, on Qt's own terms: the output is
`foo.moc` and that file must `#include` it. If it doesn't, fmake says so rather
than letting it fail later on an undefined symbol.

All three tools are found through pkg-config, so they match the Qt being
linked rather than whatever happens to be on `$PATH` — on Debian none of them
is. Override with `[toolchain] moc` / `uic` / `rcc`, or `$MOC` / `$UIC` /
`$RCC`.

**`uic` runs on the same principle.** `#include "ui_thing.h"` naming a header
that exists nowhere, with a `thing.ui` that would produce it, is the source
asking for it.

```sh
$ ls
main.cpp  thing.ui
$ fmake
UIC thing.ui
[1/1] CXX main.cpp
LD  app
* built app
```

So a `.ui` nobody includes is not built, and a `ui_thing.h` you committed
yourself is left alone rather than overwritten. Two `thing.ui` in one tree are
refused by name: an unqualified include cannot say which you meant.

**`rcc` is decided by what you open.** A resource registers itself from a
static constructor, so no symbol ever refers to the generated object — but a
`.qrc` declares the paths it provides, and code that uses one names it:

```
resources.qrc declares  /fonts/Lato-Light.ttf
aboutdialog.cpp says    ":/fonts/Lato-Light.ttf"
```

That is per file, so each program gets the resources *it* opens and not the
other program's. Directory prefixes count, since `":/icons/" + name` is how
most code names one, and `Q_INIT_RESOURCE(foo)` counts outright. A `.qrc`
nothing opens is not built.

This is textual evidence rather than proof — a path assembled with no `":/…"`
literal at all leaves nothing to go on, and then you want `--force-link`.
QML type registration is not handled.

Tried on qView (33 TUs, 15 `Q_OBJECT` classes, 7 `.ui` files, 1 `.qrc`): it
builds and runs on two excludes and three `-D`s, with **no build file and
nothing about Qt**. fmake generated the same 15 moc files as CMake's AUTOMOC,
the same 7 ui headers, and embedded the resource. It is slower on a clean
build (39s against 27s) because CMake concatenates all moc output into one
translation unit where fmake compiles one per class.

Also run over **Qt's own widgets examples — 74 programs, 201 sources**, each
built with no configuration: 66 built. Of the rest, five share a helper in a
sibling directory (build the parent instead), two need Qt private headers, and
one is QNX-only.

The case this is best at is a tree of many small programs over one shared body
of Qt code — each TU compiled once, each program linked to its own closure.
On Qt's `painting` examples that is exactly what happens: `arthurwidgets.cpp`
is compiled once and linked into every program reaching it. The limit is a
tree whose sibling programs reuse a class name — three of those examples each
define a `Window`, which is genuinely ambiguous, and needs
`[target.*] sources`.

---

## Commands

```
fmake                    build every program in the tree
fmake myapp              build one
fmake flash              run a .PHONY rule from fmake.mk
fmake --explain          print every decision and why
fmake --install          install artifacts and @headers
fmake --eject > Makefile leave, taking the build with you
fmake --clean            remove .fmake/
```

| Flag | |
|---|---|
| `-C DIR` | build the tree rooted here |
| `-j N` | parallel compile jobs (default: cpu count) |
| `-o DIR` | where to put the artifacts |
| `-p NAME` | build profile from `[profile.NAME]` |
| `-n` | print commands, run nothing |
| `-B` | ignore the cache and rebuild |
| `--cflags 'FLAGS'` | replace the default `-O2 -g`; overrides file directives |
| `--ldflags 'FLAGS'` | extra link flags |
| `--eject [make\|ninja]` | write a standalone build file to stdout |
| `--force-link SRC` | link a file no symbol reaches |
| `--widen-all` | compile the whole tree before deciding the link set |
| `--no-libs` | resolve no libraries; pass every `-l` yourself |
| `--prefix` / `--destdir` | install paths |
| `-v` / `-q` | more / less output |

`$CC`, `$CXX`, `$AR`, `$NM`, `$CFLAGS` and `$LDFLAGS` are honoured and win over
the config file.

---

## The exit

`fmake --eject` writes a standalone Makefile — or `--eject ninja` a
`build.ninja` — containing everything fmake worked out, with nothing referring
back to fmake. The output is byte-stable, so it is safe to commit, and it
produces binaries matching fmake's symbol for symbol.

A tool this opinionated has to be leaveable.

---

## What it does not do

- **No `fmake.py`.** There is deliberately nowhere to put logic. If something
  genuinely needs code, a rule can call a script.
- **C and C++ only.** C++20 modules are not handled.
- **Qt means moc, uic and rcc**, not QML — see above. Exercised against Qt 6
  on Debian; Qt 5 is coded for and untested.
- **Static archive link order** is not solved; a cycle between two archives
  needs the flags by hand.
- **Cross-compiling** works, and library resolution answers for the target
  machine — but it has been exercised against one toolchain family on Linux.
- **macOS and Windows** are unhandled: the symbol scan is ELF-shaped.

---

## Licence

GPL-2.0-or-later. Copyright (C) 2026 Nabeel Sowan <nabeel@vibes.se>.

`fmake -V` prints the version, author and licence.

---

## Design notes

`project.md` records why it works the way it does, including the things that
were tried and rejected — the include-graph rule that fails on ordinary code,
the weak-symbol resolution that took three corrections, and the passes where
the design was checked against itself and lost.

`./selftest` runs the suite: one case per claim the design makes, each verified
to fail when the behaviour it guards is removed.
