# fmake, from a project it correctly refused

Written 2026-08-04 from `apt-emerge`, a single-file Python program with a
hand-written 140-line `Makefile`. fmake was run, not read about.

The verdict is **not applicable**, and there is nothing to fix: the tree has
no C or C++ in it. That is a boring result, so this file is about everything
around it that is not boring — starting with a bug found while running it.

## fmake does not run on the Python its own package requires

`debian/control` says `python3 (>= 3.11)`. It needs 3.12.

```
$ python3.11 fmake --version
  File "fmake", line 3730
    f"{DIM(cfg.os + '/' + cfg.arch + '  (host is '
    ^
SyntaxError: unterminated string literal (detected at line 3730)
```

Two f-strings put a replacement field across a line break — lines 3730 and
3813. That is PEP 701, new in **3.12**. Before it, a replacement field could
not contain a newline.

This matters more than a wrong number in a control file, because of where it
lands. Debian bookworm ships python3.11. Installing the `.deb` there
**succeeds** — the dependency is satisfied, `dpkg` is happy, the package is
configured — and then every invocation dies with a `SyntaxError` before
reaching `main`. The failure is at the far end of the chain from the thing
that caused it.

Either raise the dependency to `python3 (>= 3.12)` or rewrite the two
strings; they are cosmetic uses in progress output and the rewrite is a
couple of lines.

**And this is worth a gate, because it cannot be caught by reading.** The
identical bug hit this project in its first CI run. What made it expensive
was that the obvious local check proves nothing: `ast.parse(...,
feature_version=(3, 11))` **accepts** these f-strings, because the change is
in the tokeniser rather than the grammar. A local `--version` run on a
current interpreter passes too. Only a real old interpreter, or a token-level
check, sees it. The detector that works:

```python
import tokenize
with open("fmake", "rb") as f:
	start = None
	for tok in tokenize.tokenize(f.readline):
		if tok.type == tokenize.FSTRING_START:
			start = tok.start[0]
		elif tok.type == tokenize.FSTRING_END and tok.end[0] != start:
			raise SystemExit(f"PEP 701 f-string at line {start}: needs 3.12")
```

It has to run *on* 3.12+ — `FSTRING_START` does not exist as a token type
before then — which is the right way round: the new interpreter is the one
that can see what the old one will reject.

## The refusal is the right one, and worth keeping

```
$ fmake
!!! no C or C++ source files found here
$ echo $?
1
```

`--explain` says the same and also stops. No traceback, no partially created
`.fmake/`, nothing written to the tree, and a non-zero exit so a script
notices.

That deserves saying out loud because of how fmake will actually be met: the
standing instruction in these projects is to evaluate it against whatever
tree you are in, which means it gets run speculatively in repositories that
were never candidates. A tool judged that way is judged on how it declines,
and this declines cleanly. Nothing here would have to be undone.

## "Maintains a hand-written build system" is the wrong trigger

`project.md` for these projects phrases the fmake prompt as *any project
maintaining a hand-written build system is a candidate*. That heuristic fires
here and is wrong.

`apt-emerge` has a real hand-written `Makefile` — `install`, `check`,
`deb`, `clean`, `uninstall`, a settable `OBJDIR`, a version-consistency
target — and it is annoying enough to maintain that the prompt is doing its
job. But it contains **no compilation at all**. It orchestrates packaging and
tests around one Python file. fmake could not take a single line of it, and
the overlap with what fmake replaces is zero.

The distinguishing question is not "is there a hand-written build system"
but "does that build system compile C or C++". Suggest phrasing the
invitation that way; it is the difference between an evaluation that takes
thirty seconds and one that takes an hour before reaching the same answer.

## The feature we noticed and then wanted

Not a complaint — the opposite. `fmake --man` prints the manual as roff, and
fmake's own `make deb` generates the packaged man page from it *so it cannot
drift from the options*.

`apt-emerge` hand-writes `emerge.1`, and during this session that drift
happened immediately: an option documented in `--help` had no man page entry.
The fix was two unit tests comparing the two in both directions — every
option in `--help` must have a `.TP` entry, and every option the man page
gives an entry must exist in the program.

That is a worse solution than fmake's. Tests detect drift; generation makes
it impossible. It is worth advertising `--man` more prominently than an
option-list entry, because it solves a problem every packaged CLI has and
most solve badly or not at all. It is the reason this evaluation ended with
something copied back rather than nothing.

## Packaging notes, from having just built one

Three small things, all from doing the same job in this project this week.

**Build products land in the parent directory.** The README says it outright:

```sh
make deb && sudo dpkg -i ../fmake_*_all.deb
```

`../` is outside the tree and not the build's to write to. When two of these
projects sit side by side in `~/src`, `make deb` in one drops files into the
directory that contains the other. Collecting them into a build directory —
`OBJDIR` is the canonical name across these projects — costs four lines after
`dpkg-buildpackage` and makes `clean` able to name what it removes.

**`dpkg -i` is the wrong verb to recommend.** It does not resolve
dependencies: on a box without the required python3 it leaves the package
unpacked-but-unconfigured and prints an error about it, and the user then has
to know to run `apt-get -f install`. `sudo apt install ./fmake_*_all.deb`
takes a local file path and does the right thing. Given the version problem
above, this is the difference between a clear message and a confusing one.

**The version is written twice with nothing comparing the two.**
`VERSION = "0.1.0"` in `fmake`, `fmake (0.1.0)` in `debian/changelog`. Both
are hand-edited, so they will drift, and the symptom is a package whose
reported version disagrees with the one that installed it. A make target
comparing them is about six lines, and it can hang off `dh_auto_test` so the
package build itself refuses to produce a mismatched pair.

## No CI, and the one job that would have caught the above

Neither this project nor `situ` has `.github/workflows/`. That is a choice
rather than an oversight, and a small tool does not need a matrix. But one
job would have paid for itself already:

**Build the package, install it, and run the installed binary.** Building
proves very little — a `.deb` with entirely wrong paths builds perfectly, and
so does one that will not start on the Python it declares. The job is short:
`make deb`, `apt-get install ./dist/*.deb`, then `fmake --version` and
`fmake --help` on a `debian:bookworm` container. That container is the whole
point: the interpreter it ships is the one the bug is about.

The same job in this project checks that `argv[0]` dispatch works through the
installed symlinks, that the man pages render, and that removing the package
leaves nothing behind. All of those are things that only break at install
time, and none of them can be caught by a unit test.

## What would change the answer

A C or C++ component. There is no plan for one: hard rule 1 of the project is
a single stdlib-only Python file, because the deploy story for a box with no
`apt-get` is one `scp` and a text editor. So this is a permanent no rather
than a "not yet", and re-evaluating it periodically is wasted motion unless
that rule changes.
