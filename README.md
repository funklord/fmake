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
- **Static archive link order** is not solved; a cycle between two archives
  needs the flags by hand.
- **Cross-compiling** works, and library resolution answers for the target
  machine — but it has been exercised against one toolchain family on Linux.
- **macOS and Windows** are unhandled: the symbol scan is ELF-shaped.

---

## Design notes

`project.md` records why it works the way it does, including the things that
were tried and rejected — the include-graph rule that fails on ordinary code,
the weak-symbol resolution that took three corrections, and the passes where
the design was checked against itself and lost.

`./selftest` runs the suite: one case per claim the design makes, each verified
to fail when the behaviour it guards is removed.
