# fmake

A build tool for normal desktop programs, where the common case needs no build
file at all and the uncommon case needs a short one.

This is a living design document. It is updated as decisions are made, and it
records the reasoning, not just the conclusion — including the options rejected,
so they don't get relitigated.

**For using the tool, read `README.md`.** This file is the record of how the
design was arrived at, which is a different thing and much longer.

Status: **phases 1–6 implemented, plus three passes over the invariants** —
the chains (§14), the tooling's own claims (§77 onward), and a sweep of what
was recorded as unverifiable or left unasserted (§112 onward).

`fmake` builds C and C++ programs and libraries from an unannotated tree,
resolves their dependencies, accepts in-source directives for what cannot be
inferred, reads an optional `fmake.toml` for what belongs to no single file,
cross-compiles, and can eject a standalone Makefile or `build.ninja` and get
out of the way.

`./selftest` covers the design claims below, one case per claim, and every fix
in §14 is mutation-checked: the case is confirmed to fail when the bug is put
back. Phase 7 (`fmake.py`) is **declined** rather than pending — see §11.

**Mutation is the standard, not a habit of §14.** A case that cannot be made
to fail has not been shown to check anything, and §112–§116 are largely the
record of what that turns up: a passing check whose fixture was too easy, a
claim argued for in prose with no assertion under it, a guard that swallowed
the case beside the one it was written for.

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

**Picking it up.** [16. Working on this](#16-working-on-this) — the conventions,
how the verification is reproduced, and where the reference projects come from

**What happened when it met reality.** [11. Build order](#11-build-order) — what
was built, in what order, and what each phase turned up ·
[13. What real projects showed](#13-what-real-projects-showed) — four codebases,
and the four things a 6-file project could not have exposed ·
[14. The chains, checked](#14-the-chains-checked) — the same question asked of
the design rather than of a sample, and the silent wrongness it found ·
[15. Open questions](#15-open-questions) ·
[18. Vendored archives](#18-vendored-archives) ·
[19. The instantiation widening could not see](#19-the-instantiation-widening-could-not-see) ·
[20. Declared membership](#20-declared-membership-and-the-dead-end-before-it) ·
[21. What widening costs](#21-what-widening-actually-costs) ·
[22. A shared library that did not say its own name](#22-a-shared-library-that-did-not-say-its-own-name) ·
[23. The wrong-architecture archive](#23-the-archive-that-was-the-wrong-architecture) ·
[24. Checking the exit](#24-checking-the-exit-actually-is-one) ·
[25. The cache remembered failures](#25-the-cache-remembered-the-failures-too) ·
[26. An optimisation that was not](#26-an-optimisation-that-was-not-one) ·
[27. Symlinks](#27-symlinks-and-a-count-that-named-the-wrong-reason) ·
[28. The main that was not there](#28-the-main-that-was-not-there) ·
[29. A test that only tests sometimes](#29-a-test-that-only-tests-when-it-feels-like-it) ·
[30. The library in an unusual place](#30-the-library-in-an-unusual-place) ·
[31. Advice that pointed the wrong way](#31-advice-that-pointed-the-wrong-way) ·
[32. Two tracebacks from the command line](#32-two-tracebacks-reachable-from-the-command-line) ·
[33. The file that was told to leave](#33-the-file-that-was-told-to-leave) ·
[34. Packaging](#34-packaging) ·
[35. What the ejected Makefile owed the conventions](#35-what-the-ejected-makefile-owed-the-conventions)

**What five sibling projects reported, and what it fixed.**
[36. What five projects said](#36-what-five-projects-said-when-they-ran-it) —
five private projects were asked whether they would adopt it ·
[37. Where an include actually points](#37-where-an-include-actually-points) ·
[38. A test that passed on the crash](#38-a-test-that-passed-on-the-crash-it-was-looking-for) ·
[39. Whose program is it](#39-whose-program-is-it) ·
[40. The step where every part was right](#40-the-step-where-every-part-was-right) ·
[41. Found means defined](#41-found-means-defined) ·
[42. The feature that was there](#42-the-feature-that-was-there) ·
[43. The blocker that was a comment, again](#43-the-blocker-that-was-a-comment-again) ·
[44. The gate that could not see its own subject](#44-the-gate-that-could-not-see-what-it-was-built-for) ·
[45. A way in, not only a way out](#45-a-way-in-not-only-a-way-out) ·
[46. The first thing two projects hit](#46-the-first-thing-two-projects-hit) ·
[47. The entry point that was a macro](#47-the-entry-point-that-was-a-macro) ·
[48. A guarantee nobody had asserted](#48-a-guarantee-nobody-had-asserted) ·
[49. Tests are built by the test target](#49-tests-are-built-by-the-test-target)
— the convention that pays for a fast default build ·
[50. A file named for a platform](#50-a-file-named-for-a-platform)

**Building them: hydra, beerssh, netcfgd, situ.**
[51. What the hydra trial found](#51-what-the-hydra-trial-found) ·
[52. `BUILD_DIR`, and a table aligned once](#52-build_dir-and-a-table-that-was-aligned-once) ·
[53. hydra, built](#53-hydra-built) ·
[54. A deadline for each test](#54-a-deadline-for-each-test) ·
[55. Built and run are different sets](#55-what-is-built-and-what-is-run-are-different-sets) ·
[56. Groups, for tests that differ in what they need](#56-groups-for-tests-that-differ-in-what-they-need) ·
[57. hydra's suite, finished](#57-hydras-suite-finished) ·
[58. The live group, and a claim that would not stay proved](#58-the-live-group-and-a-claim-that-would-not-stay-proved) ·
[59. hydra's report, folded in](#59-hydras-report-folded-in) ·
[60. The word in front](#60-the-word-in-front) ·
[61. The other four reports, folded in](#61-the-other-four-reports-folded-in) ·
[62. What the reports left that is not fixed](#62-what-the-reports-left-that-is-not-fixed) ·
[63. The job that found something before it ran](#63-the-job-that-found-something-before-it-ran) ·
[64. The half of the job that had not been run](#64-the-half-of-the-job-that-had-not-been-run) ·
[65. Two groups, one variable](#65-two-groups-one-variable) ·
[66. The flake, six clean runs later](#66-the-flake-six-clean-runs-later) ·
[67. The audit the last two findings suggested](#67-the-audit-the-last-two-findings-suggested) ·
[68. beerssh, built](#68-beerssh-built) ·
[69. One vendored file redefined a standard header](#69-one-vendored-file-redefined-a-standard-header) ·
[70. netcfgd's client, and a regression the convention introduced](#70-netcfgds-client-and-a-regression-the-convention-introduced) ·
[71. A C file as a script](#71-a-c-file-as-a-script) ·
[72. What a test runner owes its machine](#72-what-a-test-runner-owes-the-machine-it-runs-on) ·
[73. situ, and three defects behind one archive](#73-situ-and-three-defects-behind-one-archive) ·
[74. Ten lines that were one answer](#74-ten-lines-that-were-one-answer) ·
[75. The rule anyone would write](#75-the-rule-anyone-would-write) ·
[76. A generator that writes more than it declared](#76-a-generator-that-writes-more-than-it-declared)

**The same questions, turned on the tooling itself.**
[77. The gate that stopped running](#77-the-gate-that-stopped-running) — a gate
that had been green about nothing for five commits ·
[78. A completion, and a paragraph that went missing](#78-a-completion-and-a-paragraph-that-went-missing) ·
[79. A performance check that found nothing](#79-a-performance-check-that-found-nothing) ·
[80. A check that depended on how it was started](#80-a-check-that-depended-on-how-it-was-started) ·
[81. Reformatting the whole log](#81-reformatting-the-whole-log-and-what-the-proofs-caught) ·
[82. The README is a third copy](#82-the-readme-is-a-third-copy-of-the-option-list) ·
[83. The index that stopped at 38](#83-the-index-that-stopped-at-38) ·
[84. situ's report, folded in](#84-situs-report-folded-in) ·
[85. Leaving with the install as well](#85-leaving-with-the-install-as-well) ·
[86. `-g` was in the default and should not have been](#86--g-was-in-the-default-and-should-not-have-been) ·
[87. `SANITIZE`, and a variable that means two things](#87-sanitize-and-a-variable-that-means-two-things) ·
[88. The switches had to survive the exit too](#88-the-switches-had-to-survive-the-exit-too) ·
[89. The flags that have to be on both lines](#89-the-flags-that-have-to-be-on-both-lines) ·
[90. Two directives that were read and then discarded quietly](#90-two-directives-that-were-read-and-then-discarded-quietly) ·
[91. Sweeping the two paths that had not been swept](#91-sweeping-the-two-paths-that-had-not-been-swept) ·
[92. Auditing every remedy the tool offers](#92-auditing-every-remedy-the-tool-offers) ·
[93. Uninstall, and the manifest that was not written](#93-uninstall-and-the-manifest-that-was-not-written) ·
[94. `-MD` for generators, and a check that answered two ways](#94--md-for-generators-and-a-check-that-answered-two-ways) ·
[95. CI was red, and the tool was the reason](#95-ci-was-red-and-the-tool-was-the-reason) ·
[96. The byte-stability check was passing by luck](#96-the-byte-stability-check-was-passing-by-luck) ·
[97. The clean that left a build behind](#97-the-clean-that-left-a-build-behind) ·
[98. The Qt flag every other build system supplies](#98-the-qt-flag-every-other-build-system-supplies) ·
[99. The typo that could be named after all](#99-the-typo-that-could-be-named-after-all) ·
[100. The archives the cover put in the wrong order](#100-the-archives-the-cover-put-in-the-wrong-order) ·
[101. The prebuilt object, and the version of it that would have been wrong](#101-the-prebuilt-object-and-the-version-of-it-that-would-have-been-wrong) ·
[102. The library fmake could install and then not find](#102-the-library-fmake-could-install-and-then-not-find) ·
[103. The soname chain, for the price of a rule](#103-the-soname-chain-for-the-price-of-a-rule) ·
[104. The hand-written list nobody had checked](#104-the-hand-written-list-nobody-had-checked) ·
[105. The other two lists, and a check that checked nothing](#105-the-other-two-lists-and-a-check-that-checked-nothing) ·
[106. Section 76's claim, enumerated](#106-section-76s-claim-enumerated) ·
[107. Running the five projects again, and three defects in one message](#107-running-the-five-projects-again-and-three-defects-in-one-message) ·
[108. Asking git the question it had already answered](#108-asking-git-the-question-it-had-already-answered) ·
[109. The packaging report, folded in and removed](#109-the-packaging-report-folded-in-and-removed) ·
[110. The same question as §79, and a method that answered the order](#110-the-same-question-as-79-and-a-method-that-answered-the-order) ·
[111. The second list in the same file](#111-the-second-list-in-the-same-file) ·
[112. Conditions recorded as untestable, and what that cost](#112-conditions-recorded-as-untestable-and-what-that-cost) ·
[113. Advice that names the wrong fix](#113-advice-that-names-the-wrong-fix) ·
[114. The lead §79 declined to act on was real](#114-the-lead-79-declined-to-act-on-was-real) ·
[115. What deliberately stupid input found](#115-what-deliberately-stupid-input-found) ·
[116. Claims that nothing was checking](#116-claims-that-nothing-was-checking)

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

[profile.debug]
cflags  = ["-Og", "-pg"] # -Os is the default; DEBUG=1 gives -Og -g

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

- ~~**Cost of widening.**~~ Measured; see §21. On Angband — 168 sources, a
  real C project — the include graph proposes 122, widening adds 29, 151 are
  compiled and 150 are linked. **The waste is one file.** The pathological
  shape this entry named, a large tree of loosely-coupled files with a small
  binary, turns out to be the *best* case rather than the worst: 201 sources,
  two compiled. Guarded by a case, since a change loosening the filter to
  mentions would pass every other test here.
- **The widening filter cannot see header definitions.** It looks for a
  definition in a `.c`/`.cpp`, so a symbol whose definition lives in a header
  is invisible to it. Such files are found only if something else pulls them
  in, or via `--widen-all`. Mostly harmless, because a definition in a header
  is emitted weakly into every TU that uses one and needs no provider at all.
  **The case where it did matter is closed** — see §19. What remains untested
  is whether any other C++ shape reaches it.
- **The widening filter cannot see a vtable either**, and this one is no
  longer theoretical: §17 found that `_ZTV4Base` is not a string any source
  spells, so nothing scanning for apparent definitions will ever propose the
  file that defines it. moc output sidesteps this by joining the candidate set
  outright. Any other generator whose sole contribution to a program is a
  vtable would need the same treatment, and there is no general mechanism for
  saying so.
- ~~**Static libraries and prebuilt objects as inputs.**~~ Closed for `.a`
  by §18 and for loose `.o` by §101 — **named rather than discovered**, and
  that distinction is the whole finding. The guess that it would fall out
  naturally was right for the symbols and wrong about where such a file
  comes from.
- ~~**LTO and `-ffunction-sections`.**~~ Closed; see §112. GCC's `-flto`
  was already checked by hand. Clang was called untested "because clang is
  not installed here" — it is, just not on `$PATH`, and the entry is what
  a wrong reason for not checking something looks like. It works: the
  objects really are bitcode, `nm` reads them via the LLVM BFD plugin, and
  the closure is unaffected. Guarded by two cases, one of which needs no
  clang. `-ffunction-sections` only changes what the linker discards,
  which is downstream of everything fmake decides.
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
  of one-project-per-tree. Whether the include graph should *decide* such a
  tie is still a change to §3 and still has not been made — but it now
  **suggests**, and prints the `[target.*]` stanza that ends it; see §20.
- **Cross builds are verified on one toolchain, on Linux.** The architecture
  check is architecture-agnostic by construction, but sysroot handling, the
  pkg-config variables and the tool-prefix derivation have only been exercised
  against `aarch64-linux-gnu-*`. ~~A toolchain that names its tools
  differently~~ is tried now and works -- clang targets by flag and prefixes
  nothing; see §112. A bare-metal one with no libc at all is still untried.
- ~~**Header-only libraries.**~~ Correctly need no link, and signal 2
  naturally produces no external symbols for them. The remaining case — one
  needing `-I` somewhere non-standard — was closed by §30 as a side effect:
  a header-only package in a hand-made prefix now resolves, verified with a
  `.pc` carrying `Cflags` and an empty `Libs`.
- ~~**Library resolution has no notion of link order.**~~ Closed; see §100.
  Archives in the tree were grouped by §18, and two or more *resolved*
  archives are grouped now for the same reason. One archive still needs no
  group, since a shared library is not order-sensitive as a provider and
  libc is last regardless.
- **`-L` is emitted from where the library was found**, compared against
  `cc -print-search-dirs`, rather than from pkg-config's `-L`. That covers
  libraries found by symbol alone as well as by package, and it is only as
  good as the directory list fmake scans — but that list now includes the
  directories resolved packages name, so a prefix pkg-config knows about is
  no longer invisible. See §30. A library in a directory *nothing* names
  still needs `--ldflags`.
- **Linker scripts are parsed, not executed.** `INPUT`, `GROUP` and
  `AS_NEEDED` are read for filenames and `-l` flags; anything else in the ld
  script language is ignored. That covers glibc and ncurses, which is what
  exists in practice, but it is pattern-matching rather than understanding.
- **The linker-symbol list is hand-written**, and now checked: §104 has the
  suite derive what `ld` actually provides and requires the list to cover
  it. It found six gaps the first time it ran. Still a list -- a toolchain
  whose `ld` prints no default script is unexamined -- but no longer an
  unexamined one.
- **The symbol scan is Linux/ELF-shaped.** `libNAME.so`, ld scripts, and
  `ldconfig`-style layout. macOS (`.dylib`, two-level namespaces) and Windows
  are unhandled.
- ~~**The default build builds tests too.**~~ Closed; see §49. The directory
  convention is `test`/`tests` and the two filename shapes, nothing else, and
  it decides only what the *default* target builds rather than what exists —
  so the promise the tool is named for survives. Guarded by
  `the_default_build_does_not_build_tests`.
- ~~**No library-plus-consumers inference.**~~ Closed; see §42, where the
  premise turned out to be wrong — the shape already worked, and what was
  missing was any way to find that out. `netcfgd`'s own tree builds from one
  `@kind static` comment, and its client was built here in §70. §73 added the
  rule that keeps test material out of the archive and the archive out of the
  tests. Guarded by `a_library_and_its_consumers_coexist`.
- ~~**Vendored subtrees are built like any other source.**~~ Closed. A
  subtree carrying its own build file, or named in `.gitmodules`, keeps its
  own programs; guarded by `a_submodules_own_programs_are_left_to_it` and
  `gitmodules_marks_a_subtree_as_vendored_too`.
- ~~**The include path lacks the common parent of the source directories.**~~
  Closed; see §37. The answer was not the common parent but the include text
  itself.
- ~~**A file the build system excludes, rather than the file itself, cannot
  be expressed**, and neither can an optional feature whose macro the build
  system defines.~~ Closed, both halves. The platform word is read from the
  filename, at either end and beaten by an explicit annotation — see §50 and
  §60, guarded by five cases. The second half is `@pkg_optional NAME defines
  MACRO` from §41, which defines the macro when pkg-config finds the package
  and says so out loud when it does not, so a feature can no longer vanish in
  silence. Guarded by `a_missing_optional_package_is_said_out_loud`.
- **Ejected builds are a snapshot, not a translation.** They contain the plan
  fmake computed for the tree as it stood, with one explicit rule per object.
  Adding a source file means ejecting again — there is no pattern rule, and
  there cannot be one, because per-file `@cflags` is the whole point. Nor does
  the ejected build know how to re-run the closure, so a new symbol dependency
  is invisible to it.
- ~~**`--eject` emits no install rule.**~~ Closed; see §85. It emits one for
  both Make forms, from the same plan `--install` uses, guarded by a case
  that compares the two staged trees rather than the presence of a rule.
  Still true that the ejected `clean` removes only what it knows about, and
  that is deliberate rather than pending — see the `CLEAN` comment. `--eject
  ninja` still has no install rule, since ninja has no convention for one.
- **Install is minimal.** ~~No uninstall~~ (§93), ~~no pkg-config `.pc`
  generation~~ (§102), ~~no shared-library versioning or symlink chain~~
  (§103, and `SONAME` itself was §22). What is left is a manifest, which
  §93 argues is a much larger promise than the rest and is declined rather
  than pending.
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
- ~~**Directive typos are silently inert.**~~ Closed; see §99. An unknown
  command is still ignored -- that constraint was real -- but one that is a
  single edit from a directive *and* shares its first three characters is
  named. `--explain` still lists what was recognised, for the cases the
  rule declines to guess at.
- **Symbol-invisible dependencies generally.** §3 lists the constructor-plugin
  case, but the family is larger: anything reached only through `dlopen`, a
  linker script, or a function pointer table built at runtime. All need
  `@sources`. Whether that one directive is a sufficient answer for all of them
  is unproven.
- ~~**Generated outputs are not cleaned.**~~ Closed; see §97. `--clean`
  removes them by name, from what the generators actually wrote rather than
  from a pattern, which is the rule `--uninstall` and the ejected clean rule
  already follow. The directories they were written into are still left
  alone, and deliberately: a directory was never named.
- ~~**A generator's own dependencies are not tracked.**~~ Closed for
  generators that can write a depfile; see §94. `[generate.*] depfile` is
  read back into the freshness key, the same bargain the compile side
  makes. `depends` stays for the ones that cannot -- flex cannot, and a
  shell script only can if somebody makes it.
- **Object directories are never reclaimed.** One is kept per
  configuration on purpose, so switching profiles, toolchains or `$DEBUG`
  costs nothing the second time -- and nothing removes the ones that fall
  out of use. A real project held 274M and 14M side by side after a single
  change of default flags. `--clean` is the only reclamation and it now
  says how much it freed, which is the one moment the trade is visible.
  Pruning by age or by size is a policy nobody has asked for.
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
  **All three are checked against the machine now** — §104 and §105 — which
  does not make them predicates, only examined lists.
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
- **A program's root file can be pulled into another program.** Still true
  and still deliberate — a function defined next to a `main()` is a function,
  and refusing to link it would be its own guess — but it is now *reported*
  rather than left to the linker; see §31. What has not been decided is
  whether §3 should exclude other roots outright, as it already does when
  assembling a library.
- **`[build-toolchain]` is only consulted for generator tools.** Nothing else
  in fmake distinguishes the build machine from the target, because nothing
  else needs to yet. A test binary meant to run during the build would.
- **A test that split on a substring hid a working feature.** The `--explain`
  libraries header reads `[from the external symbols above]`, so
  `split("external symbols")[0]` truncated the output above the very lines it
  was meant to check, and the case failed while fmake was right. The diagnostic
  `sed` range used to investigate had the identical flaw, which is what made it
  slow to find. Assertions on `--explain` now split on a line-anchored pattern.
- **The Qt tool and the Qt flags are chosen by different rules, and on a
  machine with two Qts they disagree.** `find_qt_tool` walks
  `QT_CORE_MODULES` newest-first and takes Qt 6's moc, which §17 argues for
  and which is right. Header-to-package resolution has no such preference:
  it takes whichever `.pc` sorts first, which is Qt 5. Qt 6's moc then emits
  `<QtCore/qtmochelpers.h>` and `<QtCore/qxptype_traits.h>`, both Qt 6 only,
  so a Qt 6 `-I` joins a command line already carrying Qt 5's and the
  compile dies on Qt's own `#error Qt major version not 6 or 7`. Thirteen
  cases fail this way where both are installed; twelve of the thirteen pass
  with `MOC` pinned to Qt 5, which is what identifies the disagreement as
  the whole cause. `[toolchain] moc` is the documented escape hatch and it
  moves only the tool, so the two can still part company. **This needs a
  decision rather than code**: whether resolving any Qt module should pin
  the major for every later Qt header, or whether the flag side should
  follow the tool that was chosen. It is invisible wherever one Qt is
  installed, which is why the suite has always passed elsewhere.

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
| `code-style.md` | the style rules, and what the ejected build files owe them |
| `LICENSE` | GPL-3.0-or-later, matching the SPDX headers |
| `Makefile` | not a build system: `install`, `deb`, `check`, `clean` |
| `debian/` | native packaging; see §34 |

Version is a literal in `fmake` (`VERSION`), currently 0.1.0. `fmake -V` prints
it with the author and licence, and a case checks it against
`debian/changelog`, which is the one number that exists twice.

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

It was ~50s at 79 cases and is ~3 minutes at 173, because the cases added
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

Subjects carry a subsystem prefix, imperative, at 75 columns, as
`build-and-commit.md` requires. The whole history was reformatted to that
shape in one pass, so the vocabulary below is what the log actually uses and
a synonym introduced now reads as a second concept:

| prefix | what it covers |
|---|---|
| `core` | the scan, `main()` detection, the symbol closure, widening, the link step |
| `libs` | library resolution: symbols to `-l`, pkg-config, vendored archives, search prefixes |
| `annotations` | the `@` directives of §4, including the platform-suffix rule |
| `config` | `fmake.toml` and `fmake.mk` |
| `cross` | the two toolchains and everything that follows from having a target |
| `cache` | what is remembered between builds, and what keys it |
| `gen` | generated sources and the rules that produce them |
| `qt` | moc, uic, rcc |
| `eject` | the exit, both backends |
| `diag` | what fmake says when it refuses or cannot decide |
| `run` | `--run`, the script mode |
| `test` | fmake building and running a tree's tests |
| `cli` | the command-line surface itself: `-V`, `--man`, the completion |
| `selftest` | the suite in this repository |
| `build` | this project's own Makefile and CI |
| `tools` | `tools/`, the shared style gate and hooks |
| `packaging` | `debian/`, and the version |
| `docs` | `README.md`, `project.md`, `code-style.md` |

`test` and `selftest` are the pair worth being careful with: the first is a
feature of the tool, the second is this repository's own suite, and the log
was ambiguous about it until the reformatting pass separated them. A change
that genuinely spans the tree -- a reindent, a release of three unrelated
fixes -- takes no prefix rather than an invented one.

### The reference projects

None are vendored; they are fetched into scratch directories and are not part
of this repository.

| | |
|---|---|
| `xplore-c-example/udp-echo` | 6 files, cmocka tests. The working reference: builds, links, 13 tests pass. |
| **Angband** | `github.com/angband/angband`. 327 files, 345k lines, curses only. Builds and runs from `src/` with a `fmake.toml` that is one `exclude` list for the frontends and extras this configure run turned off. It needs `./configure` run first, for `autoconf.h` — the plainest example there is of the thing §17 calls feature probing, which fmake does not do. The excludes must match what configure chose or the link fails on the frontends it enabled. It is the tree §21 was measured on. |
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
  reported with that pointer. ~~The case is untested.~~ Tested; see §112,
  which also found the pointer was given to readers who had already
  followed it.
- moc's include path is best effort. It runs its own preprocessor but does not
  fail on an include it cannot resolve, so a missing `-I` costs an unexpanded
  macro rather than an error — which is what makes it safe to settle these
  flags before the include graph exists.
- `#if 0` is the tested case for scan-and-preprocessor disagreement. ~~Other
  conditional shapes ... were not enumerated.~~ Enumerated in §113, and the
  claim held for all of them. The same section found the disagreement in
  the *other* direction, which this limit did not consider and which is
  the dangerous one.

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

**The second of the two was needed after all.** That conclusion was right
about every header it was tried against and wrong about a shape nobody
tried, which the subsection below records. It is left standing above rather
than corrected in place, because the reasoning was sound and the gap was in
the evidence, and that is the part worth being able to recognise again.

### The half of that bug that `isfile` did not reach

`isfile` fixes the umbrella header and cannot fix a qualified one, and the
difference is why no mutation could find the rules that came out.
`<QtWidgets>` is a *directory* under the shared parent and a *file* under
`<qt5>/QtWidgets`, so once a directory stopped counting it resolved against
its own module and the parent's arbitrary claimant never came up.
`QtCore/qmetatype.h` is the other shape: a real file under the shared
parent, and not a file under `<qt5>/QtCore`, because the header's own
prefix makes up the difference. It resolved against the parent exactly as
before, and the parent still belongs to whichever `.pc` sorts first —
`Qt5Concurrent`, ahead of `Qt5Core`.

**Every qualified Qt include therefore came back as a module the tree never
mentioned**, carrying that module's `-D` and its proposed `-l`, and never
carrying the `-D` of the module that owns the header.

It stayed invisible because the misattribution still *builds*. Qt's `.pc`
files all advertise the shared parent, so the parent's `-I` comes along and
the include resolves anyway; only the define and the proposed library are
wrong. `<QtCore/QObject>` in §17's own moc case compiled for exactly that
reason. The symptom is a package in the link that nothing asked for, which
is not what anybody greps for.

The fix is `_deepest_owner`: having found the file, attribute it to the
module owning the deepest claimed directory that contains it, rather than
to the directory the search happened to stop at.

**The measurement is the argument**, since a rule this quiet cannot be
judged by reading a diff. Old and new were run side by side over every
package installed on the machine that found it — 148 include directories,
9283 header spellings. 6453 answers are unchanged; 2830 move, and every one
of the 2830 lands on a module whose own include directory really holds the
header. That check is what makes it a fix rather than a different guess.

**It is not a Qt bug**, and the same measurement is what showed it. Two of
the 2830 are elsewhere, and they are what the shape costs where nobody
thought to look: `<nouveau/nouveau.h>` answered `libdrm` rather than
`libdrm_nouveau`, so a build took `-ldrm` and never `-ldrm_nouveau`; and
`<python3.13/pyconfig.h>` answered `caf-openmpi`, a Fortran MPI package
whose `.pc` claims `/usr/include/x86_64-linux-gnu` and so claims everything
underneath it.

The case is `a_header_is_owned_by_the_deepest_include_directory`, and it
needs no Qt — two `.pc` files shaped the way Qt's are, with each module's
header refusing to compile without its own module's define, which is what
turns a silent misattribution into a failing build. It exercises both
modules rather than only the one that was wrong: the cheap over-correction
is to prefer depth so eagerly that a module whose header sits at the top of
its own directory stops resolving.

**How it was found is worth keeping too.** Nothing in this tree writes a
qualified Qt include by hand often enough to notice, and moc's output does
— Qt 6's moc emits `<QtCore/qtmochelpers.h>` and `<QtCore/qxptype_traits.h>`
— so it surfaced while chasing a different defect entirely, in which the
tool chosen for a Qt and the flags chosen for it disagree about the major
version. That one is still open and is §15's, not this section's.

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

---

## 18. Vendored archives

§15 predicted that a prebuilt `.a` shipped in the tree would fall out of the
model, and it did. The prediction was worth checking rather than assuming,
because two things did *not* fall out, and both would have been wrong in ways
that only show up later.

**Symbols needed nothing new.** `nm --format=posix` reads an archive exactly
as it reads an object; it prefixes each member with a `path[member.o]:` header
line, which has one field and is already skipped by the parser. So an archive
is a provider like any other: one defining a symbol nothing else does is
linked, one nothing needs is never mentioned again, and `--explain` attributes
it to the symbol that pulled it in — transitively, so an archive pulled in by
another archive says so.

### What did not fall out

**It must not be compiled.** A unit with no source has no object directory, no
depfile and no compile command. Three places assumed otherwise, and the one
that got through to a crash was `--explain`, which printed the compile command
for every unit in the link set and met a `None` depfile.

**Where it goes on the link line is the whole thing.** `ld` resolves left to
right and searches an archive only for what is undefined at the point it
reaches it, so an archive listed with the objects — or before them —
contributes nothing at all. They go after every object.

### The cycle, and getting the test right twice

More than one archive gets `-Wl,--start-group ... -Wl,--end-group`, which makes
the order among them irrelevant and is the only thing that resolves a genuine
cycle without naming an archive twice.

The first test written for this proved nothing, and the mutation pass is what
said so. Two archives that merely call each other are not a hard case: the
closure discovers them in the order the symbols were needed, which is already
a working order, so removing the group changed no outcome. Measured directly,
`main.c libping.a libpong.a` fails and `main.c libpong.a libping.a` succeeds —
and the closure produces the second.

A cycle that defeats *every* linear order needs the crossing to run both ways,
into members not yet pulled in:

```
libA: a1() -> b2()      libB: b1() -> a2()
      a2()                    b2()
main: a1() and b1()
```

Whichever archive the linker reaches first, the other raises a symbol back in
the first, which it has already walked past. Both orders leave exactly one
undefined reference; the group leaves none. That is now the case, and
reverting the group turns it red.

This closes §15's "untested and probably broken" for archives in the tree.
Resolved `-l` flags are still emitted in cover order, so a cycle between two
*installed* static libraries is unchanged and still wants the flags by hand.

### Generated output must not outlive its input

Found by asking what happens when things are *deleted*, which is the question
that turns up staleness bugs and the one a feature is never tested against
when it is written.

Delete a `.ui` and its generated header stays on disk. For moc and rcc that
is only untidy: their output reaches the build by being listed as a source,
and a stale one is never listed. For uic it is not, because a `ui_*.h` is
reached through an **include path**. A surviving sibling `.ui` keeps that
`-I` alive, the orphaned header goes on answering `#include "ui_gone.h"`, and
since nothing that object depends on changed, the build reports itself **up
to date**. The result is a tree that builds here and fails on a fresh
checkout, which is the worst shape this class of bug takes.

Every generated directory is now swept against the jobs planned this run —
uniformly, including moc and rcc where it is merely tidy, because the rule is
easier to trust with no exceptions. The sweep runs before the "does this tree
use Qt at all" guard, since a tree that has *stopped* using Qt is exactly the
case where everything is stale and the guard is the one thing that would skip
it.

A related check came out clean: the contents of a vendored archive are
already in the link's cache key, because `link_target` hashes everything in
the link set and an archive is in it. Changing an archive relinks; leaving it
alone does not. Verified rather than assumed, and now guarded, since keying
on objects alone would leave the binary as it was with no recompile to notice
and nothing said.

### Deliberate limits

- **Only `.a`.** A loose prebuilt `.o` in the tree is not picked up.
- **Identity is the first ELF member's.** An archive holding objects for two
  architectures — which `ar rcs` will cheerfully produce, since it appends
  rather than replaces — is judged by whichever went in first.
- **An archive fmake built is not vendored.** A static target writes
  `lib<name>.a` into the output directory, which is the tree root unless `-o`
  says otherwise, so without excluding it the second build would find the
  first build's output and offer it back as a dependency of itself.
- **A static target leaves them out** rather than nesting them. `ar` would
  happily put one archive inside another and no linker would then understand
  the result; an archive is assembled, not linked, so what it leaves undefined
  is the consumer's problem.
- **The whole archive's undefined symbols are reported**, including those of
  members the linker will never pull in, so a vendored archive can propose
  libraries the build does not strictly need. Conservative rather than wrong,
  and `--as-needed` discards the surplus.
- **The driver is not chosen by the archive.** A C++ archive linked into an
  otherwise-C program will not by itself select `c++`; the tree's own sources
  decide, and `@ldflags -lstdc++` covers the rest.

---

## 19. The instantiation widening could not see

§15 recorded that the widening filter cannot see a definition living in a
header, and that whether this mattered for real C++ was untested. It was, and
it did.

**The shape.** A header declares `extern template struct Box<int>;`, which
leaves users with a plain undefined reference rather than the weak definition
a template would normally emit into every translation unit. Exactly one file
satisfies it, conventionally a `instantiations.cpp` that instantiates for the
whole project — with no header of its own, so `sibling_source` never proposes
it and the include graph never reaches it. Widening is the only route left.

**Why widening missed it.** The filter matches symbol tokens against *apparent
definitions*, deliberately, so that a file merely mentioning a name is not
compiled on suspicion. Both definition shapes it knows are a name followed by
a parameter list and a brace, or a name followed by `=` or `;`. An explicit
instantiation is neither:

```cpp
template struct Box<int>;              // no parameter list, no initialiser
template int Box<int>::twice() const;  // and no brace
```

Measured on that file, the scan reported it as defining **nothing at all**, so
widening had nothing to match and the link failed on a symbol sitting in a
file it had chosen not to compile.

**The fix** is to recognise the shape, because it genuinely is a definition —
not to loosen the filter to mentions, which would compile half a tree on
suspicion and is the thing the filter exists to prevent. The negative
lookahead is what separates an instantiation from the primary template
(`template <class T> struct Box {` declares; `template struct Box<int>;`
defines), and anchoring at the start of a line excludes `extern template`,
which also only declares.

Both spellings have a case, which is the point: a regex written for the class
form passes its own test and silently misses instantiated member functions,
and that is the kind of half-fix this suite exists to catch.

Identifiers are taken from the whole instantiation and filtered against a
list of declaration keywords, so `template struct Box<int>;` contributes
`Box` rather than `struct` and `int`. Over-proposing here is cheap by
construction — §5's rule is that being wrong about candidates costs a compile,
never a wrong link set — so the list only has to catch the common noise.

---

## 20. Declared membership, and the dead end before it

Building Qt's `painting` examples stops on three classes called `Window`,
which §15 records as a correct refusal and a real limit. It was also a dead
end: the message named the problem and left the reader to work out the
answer. Trying to remove that friction turned up something worse underneath.

### The suggestion

§3 must not let the include graph *decide* an ambiguity — it exists because
the include graph is not good enough to. It is good enough to **suggest**, and
a suggestion costs nothing when it is labelled as one. Where the graph reaches
exactly one of the providers from a target's own root, that is almost always
the right answer, so the report now says so and prints the stanza that would
settle it:

```
The include graph reaches exactly one of them from each program's own root:
    basicdrawing         basicdrawing/window.cpp
    painterpaths         painterpaths/window.cpp
    transformations      transformations/window.cpp

which is a guess, not a decision. To make it the answer, put this in
fmake.toml -- the source lists are that same guess and are worth checking:

    [target.basicdrawing]
    sources = ["basicdrawing/main.cpp", "basicdrawing/renderarea.cpp", ...]
```

Every affected target at once, rather than the first and then exit. Nine
sibling programs meant nine builds to discover nine instances of one problem.

### What that exposed

Pasting fmake's own suggestion did not work. Three targets still failed, on
`RenderArea::staticMetaObject`, vtables and typeinfo — all moc's.

`[target.*] sources` switches the closure off, which is the point of it. But
it was switching off more than membership: **a moc output cannot appear in any
list a user writes**, because it lives under the state directory and is named
after an implementation detail. So `sources` was unusable for every Qt target
there has ever been, and nothing said so — the symbols simply went missing.

The distinction that fixes it is that a declared list answers *which of the
tree's own files belong*. It is not an answer about generated ones, and it was
never a choice: a class's meta-object is part of that class, not a second
opinion about it. Declared members therefore bring their generated companions
with them.

### Provenance, not symbols

The first version chose companions by symbol — anything generated that defined
something the members left undefined. That is the rule §3 uses everywhere else
and it is wrong here, which took a second real failure to notice: three
sibling programs each with a `RenderArea` produce three moc outputs defining
the same names, and a symbol match hands all three to whichever target asks
first. The build then fails on an ambiguous provider, reported against
generated files the user never wrote.

What settles it is **which file moc read** — a member, or a header a member
includes. Ownership by provenance rather than by symbol, which is the one
place in fmake where the symbols are not the better evidence, because the
question is not *what does this need* but *whose is it*.

With that, all nine painting examples build from the configuration fmake
suggested, and run.

---

## 21. What widening actually costs

§15 carried this from the beginning: a tree whose include graph is a poor
guide pays for compiling translation units it turns out not to need, the
pathological case is a large repo of loosely-coupled files with a small
binary, and it was **worth measuring before assuming it is acceptable**.
Measured now, on three trees.

| | sources | include graph proposes | compiled | linked | wasted |
|---|---|---|---|---|---|
| **Angband** (C) | 168 | 122 | 151 | 150 | **1** |
| **qView** (C++/Qt) | 33 | 33 | 33 | 32 | 1 |
| **loose tree** (C) | 201 | 1 | 2 | 2 | **0** |

Angband is the real answer: 327 `.c` files in the repository, 168 after the
platform excludes, a clean `-j8` build in 67s and a no-op rebuild of about
0.3s (min 314ms, mean 431ms over fifteen runs — this machine is noisy enough
that a single sample is not worth quoting). That figure was first recorded
here as 3.5s, which was measuring §25's bug rather than the build: the
"no-op" was recompiling eleven files that could never compile.
The include graph finds 122 of the 150 files that end up linked — 81% — and
widening supplies the remaining 28, overshooting by exactly one. `--widen-all`
compiles 157 and takes 70s, so the whole apparatus buys about 4% of the build
and, more importantly, does not need to be right to be safe.

**The pathological case is the opposite of pathological.** 201 unrelated
files with a `main` calling one of them: the include graph proposes 1,
widening proposes 1, two files are compiled, one second. The reason is the
thing that looked like a weakness — widening filters on apparent
*definitions* rather than on mentions, so an undefined `helper_7` proposes the
one file that defines `helper_7` and nothing else. A tree that is loosely
coupled is a tree where that filter is at its most precise.

Where the cost would actually appear is the reverse shape: many files
defining similarly-named things, so that the tokens of one undefined symbol
match many candidates. C symbols are one-to-one with their tokens, so this
needs C++, where a mangled `Foo::bar` yields `{Foo, bar}` and any file
defining a `bar` matches. qView shows nothing of it at 33 files. Unmeasured
at scale, and now the only part of this entry still open.

The entry also predicted that caching would make this a first-build cost
only, and that holds: the resolved unit set is remembered, so later builds
start from what widening found rather than re-deriving it.

---

## 22. A shared library that did not say its own name

Found by running `--install` end to end and then asking the question the
feature exists for: is the installed library actually usable?

fmake linked shared libraries with `-shared` and nothing else, so they
carried no `DT_SONAME`. What that costs depends entirely on how the consumer
links, which is the problem:

```
cc use.c -L<dir> -lgreet          NEEDED  libgreet.so          works
cc use.c <dir>/libgreet.so        NEEDED  /abs/<dir>/libgreet.so
```

The second is not a corner case. It is what CMake does by default, and it is
what falls out of every `DESTDIR` staging flow, where the path linked against
is a temporary directory that will not exist on the machine that runs the
program. Measured: the consumer built that way fails with *cannot open shared
object file* the moment the library is installed where it belongs, and
`LD_LIBRARY_PATH` cannot repair it, because an absolute `DT_NEEDED` is not
searched for.

Without a soname the *consumer* decides what the library is called. With one
the library decides, which is the right way round and is the entire purpose
of the field. `-Wl,-soname,<filename>` is now passed whenever a shared
library is linked, in `link_cmd` and in both ejected backends.

No versioning is implied by this and none is offered: fmake builds
`libfoo.so` and the soname is that same name. A project needing
`libfoo.so.1.2.3` with the usual symlinks needs a real answer, and this is
not it — but it is no longer the case that the plain one is broken for
anybody who links by path.

**Why `--lgreet` hid it.** The bare-name case works, and it is the one a
person testing their own library reaches for. That is worth remembering as a
shape: a defect that only appears through the *other* way of using the
output, and so survives every test written by the person who built it.

---

## 23. The archive that was the wrong architecture

§18 added vendored archives without asking what architecture they were. Found
by taking the same approach that turned up §22 — exercise a feature from the
outside — and pointing a cross build at a tree with a host `.a` in it.

Nothing about it looks wrong on the way in. **binutils `nm` reads a foreign
object perfectly well**, so `aarch64-linux-gnu-nm` lists the symbols of an
x86-64 archive without complaint, the closure takes them as evidence, and the
archive is chosen. The refusal comes from the linker, several steps later:

```
ld: vendor/libhelper.a: error adding symbols: file in wrong format
```

which names neither architecture, nor which of the two is wrong, nor that
fmake chose the file.

fmake already asks the ELF header this question — it is what §5 calls the
thing that makes cross builds honest, because a cross compiler's own search
path contains the host's `/usr/lib` and no arrangement of directory names
separates them. `elf_identity` even handles archives already, finding the
first ELF member. Vendored archives were simply the one input that never got
asked:

```
* vendor/libhelper.a is x86_64/64le, but this build is aarch64/64le
  not using it; anything it defines will be reported as missing
...
* crossarc did not link
  no aarch64/64le library exports: helper
```

The archive is dropped rather than fatal, and the symbol it would have
provided is then reported missing in the ordinary way — two messages that
agree with each other, where before there was one that explained nothing.

**The architecture is asked of the objects, not the configuration.** That was
already true for libraries and is right by construction: whatever fmake just
compiled is what an archive has to match, with no knowledge of triplets
anywhere. It does mean the question cannot be asked until something has been
compiled, which is why the check lives in the compile loop rather than where
the archives are found.

Both directions have a case. A check that refused every archive would pass
the negative one and be useless, which is the failure this pair is really
guarding against — and the positive case cross-builds an aarch64 archive and
runs the result under qemu.

While writing the test I appended an aarch64 object to an archive that
already held an x86-64 one, since `ar rcs` appends rather than replaces, and
fmake judged the result by the first member. That is a real limit and now
recorded as one, though a mixed-architecture archive is not a thing anyone
should be able to produce by accident twice.

---

## 24. Checking the exit actually is one

§12 claims an ejected build "produces binaries matching fmake's symbol for
symbol". That was asserted rather than tested, and every ejection case in the
suite checked something weaker: that the emitted build **works**. A build file
can lose a flag, an archive, or the order of the link line and still produce a
program that runs and prints the right number.

The claim held, checked by hand across everything added since it was written:

| | symbols | differing |
|---|---|---|
| qView — moc, uic, rcc | 2562 | **0** |
| two vendored archives in a cycle | 34 | **0** |
| shared library | 20 | **0**, `SONAME` present in both |

But holding is not the same as being guarded, and the two nearest misses say
why this needed a case. Vendored archives and the shared-library soname were
both added to `link_cmd` and to *one* ejection backend before the other — each
a change where fmake's own build stays perfectly correct and only the exit
drifts. Nothing in the suite could have noticed.

There is now a case that builds a tree both ways and compares the two binaries'
symbol tables. The tree is chosen so that a plain hello world would not do: a
per-file `@define`, an `-I` only the config supplies, and a prebuilt archive
that has to land after the objects. Both of the obvious drifts — dropping the
archive from the ejected link line, dropping `@cflags`/`@define` from the
ejected object rule — turn it red while leaving every other test in the suite
green, which is exactly the property wanted.

The narrower point is worth keeping separately: **"it works" is a weaker test
than "it is the same"**, and for a feature whose whole purpose is
equivalence, only the second one is the feature.

---

## 25. The cache remembered the failures too

Found while profiling the no-op build on Angband, which took 3.5 seconds and
should have taken almost none. The profile never got far enough to be
interesting: the "no-op" was compiling eleven files, every one of which
failed.

The resolved unit set is cached so a later build starts from what widening
found rather than re-deriving it, which §8 argues for and §21 measured the
benefit of. It was caching **everything in the pool**, including the files
that failed to compile. Those define nothing — that is what failing means
here — so they can never be why anything links, and remembering them
guarantees compiling them again, and failing again, on every future build
until the tree is cleaned.

Angband has such files by construction: `nds/`, `sdl2/`, `stats/db.c` and
`snd-sdl.c` want headers this configuration does not have. One build reported
them, which is right. Every subsequent build re-reported them, which is not.

```
no-op rebuild:  3.5s  ->  ~0.3s
```

**Forgetting is not hiding**, and the distinction is what makes this safe. A
file the include graph reaches is proposed afresh every build regardless of
the cache, so a genuine error keeps being reported. Only a file reachable
*solely* through the remembered set stops being retried — and it was put
there by a widening pass that has since been shown to be pointless.

### And a flag that would not switch off

`--widen-all` compiles the whole tree before deciding, which is an override
rather than something learned. Its unit set was being remembered like any
other, so a single `--widen-all` left every later build starting from every
file in the tree — the flag still in effect, by a route nobody would think to
look for when wondering why an incremental build had got slow. It is no
longer written to the cache at all.

Both have a case. The first needed three attempts at a fixture, and the two
failures are the useful part: a file that nothing proposes is never tried, so
proving it is not *retried* proves nothing; and a file the include graph
reaches is retried correctly, so it cannot demonstrate the bug either. The
shape that does is a file reachable only by widening, alongside another that
supplies the same symbol and actually compiles.

---

## 26. An optimisation that was not one

After §25 the no-op build was down to about 0.3s on a 168-file project, and
the obvious next step was to find out where that went. The answer is worth
recording because it is *nowhere in particular*, and because getting there
took two wrong measurements.

`cProfile` was unambiguous: `os.path.relpath` was the single largest cost,
30,165 calls for 0.25s cumulative — the same system headers resolved once per
depfile. Memoising it is a pure-function change with no staleness risk, so it
went in.

It made no difference. Nine runs each way, minimum taken, repeated three
times: 338ms with, 400ms without, 465ms with. The ordering does not even hold
across repetitions. The second candidate the profile suggested, the 660 KB
JSON cache written on every build, was tested by removing the write
altogether: 244ms against 247ms.

**The profiler was measuring itself.** `cProfile` charges per-call overhead,
so a cheap function called thirty thousand times looks like a bottleneck and
an expensive one called once does not. For ranking *where time goes* in a
program dominated by many tiny calls, it is the wrong instrument, and the
right one is a stopwatch around the whole thing with enough repetitions to
see past the noise.

The memo came out again. It was harmless and it was unjustified, and this
file already records two other cases — the redundant include-directory
ordering in §19's neighbourhood, and rcc's dead prefix branch — where code
that could not be shown to matter was removed rather than kept on the grounds
that it might. An optimisation with no measurable effect is the same thing as
a test that cannot fail.

**Two measurement mistakes, both mine, both worth naming.** The benchmark
loop was initialised with `best=99` in milliseconds rather than a large
number, so every timing was greater than the initial value, `best` never
updated, and three different builds all reported exactly 99ms — a number that
should have been obviously impossible and was briefly believed. And the
0.44s in §21 was a single sample of a noisy machine. Minimum-of-N is the only
figure quoted here now.

The conclusion for §8: at 168 sources the no-op costs a few hundred
milliseconds, spread thinly across stat calls, hashing, JSON and the closure,
with no single item worth attacking. If it ever needs to be faster the answer
is to do less work rather than to do the same work quicker — which is what
§25 turned out to be.

---

## 27. Symlinks, and a count that named the wrong reason

Found by asking what fmake does with inputs it has never been shown: CRLF
line endings, a UTF-8 BOM, and symlinks. The first two turned out fine and
are worth recording as such — a Windows-authored tree with `\r\n` throughout
and a BOM on `main.c` builds correctly, with `@target` and `@define` parsed
through both. The regex scanner survives them because it never anchors on a
bare `\n` where `\r` could intervene.

Symlinks did not fare as well.

**A symlinked directory was silently invisible.** `os.walk` does not follow
them by default, so a tree laid out as `src/common -> ../shared` — which is
how a pair of sibling projects usually share code — was missing that whole
subtree. Nothing said so. The build failed much later on an undefined symbol,
with no hint that a directory had been skipped, which is the worst kind of
omission: the tool behaved as though the files did not exist.

They are followed now, which needs a cycle guard, because a link pointing at
its own ancestor makes `os.walk` descend forever — and that is precisely why
the default is not to follow. The guard is keyed on the **real** path rather
than the walked one, which matters for a case that is not a cycle at all: two
links to one directory. Keyed on the walked path, every file in it would have
two names and therefore two definitions of every symbol, and §3 would refuse
to choose. Keyed on the real path, it is walked once.

All three shapes have a case, including the one that hangs — the mutation run
treats a timeout as a caught failure, since a build that never finishes is
not a passing build.

**And a count that named the wrong reason.** The summary line read
`N excluded by platform`, but that set also holds the files `[project]
exclude` named and the ones that could not be read. A dangling symlink was
reported correctly as *unreadable* on one line and then counted as a platform
exclusion on the next, which sends anyone looking for the cause to `@os`
first. It now says `N excluded`, and `--explain` gives the reason per file,
which it always did.

---

## 28. The main() that was not there

Every build of Angband said this, and had done since Angband was first built
here:

```
* randname.c looked like it defined main() but the object does not export it; skipping
```

It is true, and it is right to say once. `randname.c` really does contain
`int main(int argc, char *argv[])`, behind an `#ifdef` this configuration does
not enable. The scan reads text and cannot evaluate `#if`, so it proposes a
target; the object settles it; the target is dropped.

Saying it on *every* build is the problem, and it is the same shape as the
`Q_OBJECT` behind an `#if 0` that §17 already solved for moc: a disagreement
between what the text says and what the preprocessor does, which is settled
by evidence and then worth remembering. The answer is now stamped against the
file's contents and the configuration — the only two things that decide
whether the `#ifdef` is on — so the file is not proposed, compiled and linked
again to reach the same conclusion.

Remembering must not become refusing to look. Adding `-DWANT_TOOL` to a tree
where that is what the `#ifdef` wants builds the program, because the stamp
covers the configuration; editing the file re-reports, because it covers the
contents. Both are cases. Getting this wrong would leave a program
permanently unbuildable with no way to discover why, which is much worse than
the message it replaces.

### Two mistakes worth keeping

**The stamp was computed in two places.** The mutation that removed the
configuration from it was written against the *check* and not the *store*, so
the two simply never matched — which reads as the feature being switched off
rather than broken, and the test passed. It is one function now, and the
mutation bites.

**The fixture found a real limitation, by being wrong.** The first version
put `helper()` in the same file as the conditional `main`, so with the define
on, the other program's closure pulled that file in and got a second `main`.
That is not the feature under test, but it is a real shape: §3 excludes other
programs' roots when assembling a *library* and does not when closing over a
program. The linker says `multiple definition of main` plainly, so it is loud
rather than silent, and it is recorded in §15 rather than changed here.

---

## 29. A test that only tests when it feels like it

The build lock had a case, and I wrote a second one because I could not find
the first. Both facts are worth recording.

**Why it was not found.** The existing case is called
`one_fmake_at_a_time_per_tree`, and neither its name nor its docstring
contains the word *lock* — searching for one matched only a comment inside
its own body. A test named after the property rather than the mechanism reads
better and is harder to find when the mechanism is what you are holding in
your head.

**Why the second one earns its place anyway.** The original starts two builds
in threads and checks the result is right. That is the thing that actually
matters, but it only exercises anything if the two overlap, and nothing makes
them: no barrier, no wait, just the hope that starting them close together is
enough. Removing the lock does turn it red today. Whether it still would on a
faster machine, or with a smaller tree, or under a loaded runner, is exactly
the question a timing-dependent test cannot answer about itself.

The new one takes the lock from the test process, checks that fmake blocks on
it, releases it, and checks the build then completes and says why it paused.
There is no timing assumption in it, so there is no machine on which it
quietly stops testing anything.

Both are kept. One checks that concurrent builds produce a correct binary,
which is the promise; the other checks that they are serialised, which is how.
Measured beforehand rather than assumed: four fmakes launched at once on a
cold 31-file tree all exited 0, three of them reported waiting, the binary was
correct and the cache was still valid JSON.

---

## 30. The library in an unusual place

A library built and installed into `/opt`, `~/.local`, or any hand-made
prefix, with a perfectly good `.pc` file, could not be used at all. Three
separate faults, each hiding the next.

**The `.pc` file was invisible.** `PkgConfig._search_path` asked
`pkg-config --variable=pc_path`, which reports the **built-in** search path
and deliberately excludes `$PKG_CONFIG_PATH`. So the header-to-package map
never saw the package. The symptom was not a missing library but a missing
*include*: `mylib.h: No such file or directory` for a library that is plainly
installed and that `pkg-config --cflags mylib` answers correctly — because
that call inherits the environment, while the directory scan does not.
`$PKG_CONFIG_PATH` is now searched first and `$PKG_CONFIG_LIBDIR` replaces
the default, which is what the two variables mean.

**The `-L` was parsed and thrown away.** §5 recovers library paths from where
a library was actually found rather than from pkg-config, which is what makes
libraries found by symbol alone work at all. But it can only find one in a
directory it looks in, and a hand-made prefix is in none of them. The
directories a resolved package names are now added to the scan set — which is
pkg-config *proposing*, exactly as it proposes the `-I`, with the symbols
still deciding.

**And then it worked once.** Collecting those directories as a side effect of
running pkg-config meant collecting them on the first build and never again:
the package answer is cached across builds, so the second build resolved the
header from the cache without ever calling `pkg-config`, and lost the
directory. `--explain` on a warm tree said `no symbol needs it` and
`(unresolved) mylib_answer` about a program that had just linked — two runs
of the same tool disagreeing, which is worse than either answer alone. The
directories are part of the cached entry now.

That third fault is the one worth remembering. The first two were found by
trying the feature; the third only appeared on the *second* build, and would
have looked like an unrelated intermittent failure to anyone who met it
later. A cache turns "computed as a side effect" into "computed once, then
wrong" — and the fix is to make the side effect part of what is stored.

---

## 31. Advice that pointed the wrong way

Two programs, one of which defines a function the other calls, in the file
that holds its `main()`. The closure reaches the function, links the file it
lives in, and the program gets a second `main()`. What fmake said:

```
ld: .../tool.c.o: in function `main':
    multiple definition of `main'; .../app.c.o: first defined here
* app did not link
  name the missing libraries with --ldflags, or build only the targets you want
```

The linker's half is accurate and unhelpful — object paths under `.fmake`,
several steps from the cause. fmake's own half is worse than unhelpful: it
offers to name the **missing** libraries when nothing is missing at all. The
advice points at the opposite of the problem, and following it cannot lead
anywhere.

fmake can see this before linking, and now does. Every exe root defines
`main()`, so a closure that reaches a second root is exactly this situation:

```
!!! a program's own file was pulled into another program:
    app links tool.c, which roots tool
        <- shared_bit  (app.c)

Both define main(), so this cannot link. What is shared belongs in a file of
its own: move it out of tool.c and both programs can reach it.
Naming each program's sources in fmake.toml settles it too.
```

**Reported, not resolved.** §3 excludes other programs' roots when assembling
a library and does not when closing over a program, and that asymmetry is
deliberate: a function defined next to a `main()` is still a function, and
declining to link it because of what shares its file would be its own kind of
guess. Whether the rule should change is still open in §15; that it should be
explained is not.

The case checks the fix as well as the message — moving the shared function
into a file of its own, which is what the message recommends, and then that
both programs build and run. A recommendation nobody has followed through is
a guess with a confident tone.

---

## 32. Two tracebacks reachable from the command line

Found by a sweep of the error paths — malformed `fmake.toml`, a rule with no
recipe, an invalid `--eject` backend, a bad `-j`, an unknown target name. Most
were already good: a named file and line, or argparse's own usage. Two were
not, and both ended in a Python stack trace.

**`-C` naming a file, or nothing.** `build()` checks that the tree exists and
is a directory, and the lock is taken *before* `build()` runs — so creating
`.fmake` under a path that is a file raised `NotADirectoryError` from
`os.makedirs`, and a missing path raised `PermissionError` from trying to
create it. The check now happens before the lock, and distinguishes the two
cases, since *no such directory* and *not a directory* are different mistakes.

**A tree fmake cannot write to.** A read-only checkout, a mounted source
directory, someone else's copy. fmake keeps its cache and objects beside the
source, so this is a genuine refusal rather than something to work around —
but `Permission denied` from `os.makedirs` with a stack trace above it names
neither the directory nor the way out. It now names both.

The sweep is the point rather than the two fixes. Every one of these is
reachable by typing something slightly wrong, which is how anyone meets a
tool for the first time, and a traceback at that moment says the program did
not expect to exist in the world it is running in. The rest of the paths
checked out, which is worth recording too: this is the first time they have
all been tried on purpose rather than met by accident.

Both fixes have a case, and the read-only one skips under `root`, who can
write anywhere and would see the test quietly pass while testing nothing.

---

## 33. The file that was told to leave

A sweep of the directives, in the same spirit as §32's sweep of the error
paths: every one given a bad value on purpose, to see what it says.

Most were already right. `@kind shard` names the three valid values.
`@std zzz9` reaches the compiler, which rejects it by name. `@pkg
totally-not-installed` is refused up front with the file and line. `@target`
on a file that roots nothing says so and carries on.

**`@os` is the exception, and it is a different kind of wrong.** §4 accepts
that an unknown *directive* is silently inert — the cost of sharing comments
with Doxygen — and that is fine, because inert is harmless. A typo in the
*value* of a known directive is not inert: `@os windwos` matches no platform,
so the file is excluded everywhere, on every machine, permanently. The only
sign is an undefined symbol at the link, and nothing on that path mentions
exclusion at all.

`--explain` has always had it right:

```
  excluded here
    util.c                          @os windwos (building for linux)
```

but a person whose build just failed is reading the failure, not asking for
an explanation of a build that did not happen. So the failure now says it,
cross-referencing the missing symbols against what the excluded files appear
to define:

```
* os did not link
  no x86_64/64le library exports: util
  util.c is excluded (@os windwos (building for linux)) and appears to define one of them
```

The same route covers a `[project] exclude` pattern that matched more than it
meant to, which is the commoner mistake of the two and reads identically. It
needs no list of valid platform names — which §15 would have counted against
it — because it does not check the value at all. It notices that something
this tree defines has nowhere to come from, and that a file which appears to
define it was told to leave.

---

## 34. Packaging

A `.deb`, so the thing can be installed and tried rather than copied about.
`make deb` builds it; `make install` does the same job without dpkg.

```
/usr/bin/fmake
/usr/share/man/man1/fmake.1.gz
/usr/share/doc/fmake/{copyright,changelog.gz}
```

Native format, `Architecture: all`, and one dependency: `python3 (>= 3.11)`,
which is where `tomllib` arrives. `pkgconf` and `binutils` are Recommends
rather than Depends — fmake runs without them and says what it cannot do,
and a build tool that refuses to install because `nm` is absent would be
worse than one that explains itself. `ninja-build` and `make` are Suggests,
for `--eject`.

**The manual page is generated by `fmake --man`.** A hand-written option list
is a second copy of something argparse already knows, and a manual is the one
piece of documentation nobody re-reads, so it goes stale in exactly the place
a stranger looks first. There was already a precedent for a program emitting
input for another tool — `--doxygen-aliases` — so this is the same idea
pointed at roff. A case checks the generated page against `--help`, and
`man --warnings` against the result, because generating it is only worth
doing if it is actually right.

**Two numbers had to agree**, `VERSION` in `fmake` and the version in
`debian/changelog`, and nothing enforced it. That failure is quiet in the
worst way: a package that installs cleanly and reports a version it is not.
There is a case for that too.

### What was checked

Not just that the package builds. It was unpacked to a staging root and the
installed binary used to build two real trees — a plain C program, and a Qt
one whose `Q_OBJECT` had to reach moc — because a package that produces a
`fmake` which cannot find its own way is a package that only looks finished.
The manual renders from the installed, gzipped copy.

### The interpreter is rewritten on the way in

The repository copy starts `#!/usr/bin/env python3`, because copying the file
into `$PATH` and running it anywhere is half of what fmake is, and that half
wants the lookup. Debian Policy 10.4 wants the other thing — an absolute
interpreter path — and every packaged Python script on a Debian system has
one. So `make install` rewrites the line, and `debian/rules` passes
`PYTHON=/usr/bin/python3`.

That leaves two spellings and a way for the rewrite to quietly stop
happening, so there is a case: it installs to a staging root, checks the
shebang is the absolute one, and runs the installed copy.

Found by looking at what every other packaged Python script on this machine
does, before lintian was available. It is the kind of thing a policy checker
exists to catch and the kind of thing a convention survey catches just as
well — and lintian, once installed, confirmed there was nothing left to find
there.

### What lintian said

Clean at every level it reports — no errors, no warnings, no info, nothing
pedantic — on both the `.deb` and the `.changes`. `make deb` runs it now, and
says so, rather than leaving it as something to remember.

It found exactly one thing the hand-checks had not:

```
I: fmake: ored-depends-on-obsolete-package Recommends: pkg-config => pkgconf
```

`Recommends: pkgconf | pkg-config` was written to be generous to older
systems. It is the wrong kind of generous: `pkg-config` on Debian is now a
transitional package whose only content is `Depends: pkgconf (>= 1.8.1-4)`,
so anybody who has it already has `pkgconf`, and naming both only preserves
an alternative that resolves to the same thing. `Recommends: pkgconf`.

Worth recording that the fifteen hand-checks agreed with the tool on
everything else — the value was in the one tag nobody would think to check
by hand, which is a fact about a *package archive's* history rather than
about this package.

### Two things worth knowing

`PREFIX` defaults to `/usr/local`, which is right for `make install` by hand
and forbidden inside a package; `debian/rules` overrides it to `/usr`.
Without that, `dh_usrlocal` fails the build, which is Debian policy doing its
job and took a moment to recognise.

`dh_auto_test` is disabled. The suite needs a compiler, a linker, Qt, a cross
toolchain and several optional libraries; it is the right thing to run before
a commit and the wrong thing to make a package build depend on. `make check`
runs it.

---

## 35. What the ejected Makefile owed the conventions

`code-style.md` holds an ejected `Makefile` to the same Make conventions as a
hand-written one, on the grounds that it is a Makefile somebody will edit.
Checked against them, one was not met.

**`-MP` was missing.** The depfile names every header an object depended on,
so deleting one — which is what a refactor that inlines a declaration does —
leaves make with a prerequisite that has no rule:

```
make: *** No rule to make target 'util.h', needed by 'build/main.c.o'.  Stop.
```

It stops there, before reaching the compiler, over a file nothing needs any
more. `-MP` emits a phony target for each header so a vanished one is simply
absent. Measured both ways: without it the build stalls, with it the same
tree rebuilds and runs.

fmake's own compiles keep `-MD` alone, deliberately. It reads its own
depfiles and skips a prerequisite that has gone, so it does not need the
phony targets — and `parse_depfile` splits on the first colon, which `-MP`'s
extra stanzas would feed bogus paths. The convention is about Makefiles, and
that is where the flag goes.

The other two rules in that group did not apply: nothing ejected recurses
into a sibling library, so there is no `FORCE` prerequisite to get wrong, and
nothing emits `.SECONDARY` at all. Both are recorded here as checked rather
than left to look like oversights.

### And the clean target

`clean` had `rm -rf` over a wildcard, which the same conventions forbid
outright: a clean target is the one thing everybody runs without reading. It
now names every file it deletes. The two directories it still removes
wholesale are debhelper's staging trees, created by the build, relative, and
named outright rather than matched — which is the one shape the rule allows.

---

## 36. What five projects said when they ran it

`build-and-commit.md` carries a standing instruction that projects which
could adopt fmake should say whether they would. Five did, in `suggestions/`,
and the files are worth reading whole: `hydra`, `netcfgd`, `fuzzypickles`,
`beerssh` and `apt-emerge`. Only one adopted anything, and the value was not
in the verdicts.

Three fixes came straight out of them and are in this commit.

### The package installs and then never starts

`apt-emerge` found it, on a tree fmake correctly refused for having no C in
it. `debian/control` declares `python3 (>= 3.11)` — where `tomllib` arrives —
and two f-strings put a replacement field across a line break, which is
PEP 701 and needs **3.12**. On Debian bookworm the package installs, satisfies
its dependency, configures, and then every invocation dies with a
`SyntaxError` before reaching `main`.

**It cannot be caught by reading, and the obvious check is worse than
useless.** `ast.parse(..., feature_version=(3, 11))` *accepts* these, because
the change is in the tokeniser rather than the grammar — verified here, it
accepts. Running fmake locally passes too. Only an old interpreter or a
token-level check sees it, and the check must run on 3.12+, since
`FSTRING_START` does not exist as a token type before then.

Both strings are rewritten and there is a gate, keyed to the version
`debian/control` actually declares, so raising the floor to 3.12 relaxes it
automatically. It checks `fmake` alone: that is the file the package installs
and therefore the only one the declaration promises anything about.

### The ejected clean target, reported by three projects independently

`netcfgd`, `fuzzypickles` and `beerssh` all named it, and two of them had
written the same bug into their own Makefiles and fixed it the same week —
which is why they recognised it.

```make
clean:
	rm -rf $(BUILD_DIR) prog
```

`BUILD_DIR` is an ordinary Make variable and overriding it is expected usage, so
`make clean BUILD_DIR=` or a mistyped one removes something else. §34 fixed
fmake's *own* Makefile after reading the same rule and did not think to look
at the one fmake writes — which is the sharper version of the lesson: the
output is where a guard is worth most, because its header tells the reader
fmake is not needed to understand it, so nobody reviews it. It now refuses an
empty, absolute or `..`-containing `BUILD_DIR`, and every refusal has a case.

### A column that stopped separating

`beerssh` counted **547** lines of `--explain` where a generated moc path
overflowed the column and ran into its own explanation with no space:

```
.fmake/moc/src/input/moc_input_router.cppdefines nothing reachable
```

I had seen this myself on qView, in this document's own §30 transcript, and
filed it as cosmetic and pre-existing. It is neither: it is most of the report
on any Qt tree, and the report is what fmake is judged by. Every padded column
now goes through one function that never lets the two touch.

### What they said that is not fixed here

These are design questions rather than defects, and are recorded in §15
rather than answered in passing:

- **Tests are built by the default build** — `netcfgd`, `fuzzypickles` and
  `beerssh` all raise it, and `build-and-commit.md` is explicit that the
  default target must not build tests. There is no annotation-free way to know
  that `tests/` means tests; a directory convention behind a flag is the
  obvious shape.
- **No library-plus-consumers inference** — `netcfgd` declined on this alone.
  A tree with one `main()` is already served by a two-line Makefile; the shape
  where a build system is genuinely annoying is a library, some programs, and
  tests linking the library.
- **Vendored subtrees are built** — `fuzzypickles` (two submodules each with a
  `test.c`, ten fuzzers sharing `LLVMFuzzerTestOneInput`) and `beerssh`
  (libvterm's own tools). A directory carrying its own build system, or listed
  as a submodule, is almost never something the outer tree wants built.
- **The include path lacks the common parent** — `beerssh` failed 84 files on
  it. The tree includes its own headers subdirectory-qualified from the source
  root, which is ordinary C++, and fmake adds an `-I` for every directory that
  *contains* sources but not for their shared parent.
- **Platform-conditional and optional-feature sources** — `hydra` cannot build
  at all, because four Android sources have no self-guard and CMake is what
  excludes them; and two optional features vanish silently because the macros
  that enable them are defined by the build system fmake replaced. Its own
  summary is the sharpest sentence in the five files: *"it builds, and quietly
  does less than it should — which is worse than refusing."*

### What they said that was already true

Worth recording, because agreement arrived at independently is evidence too.
`fuzzypickles` and `beerssh` both checked the ejected Makefile against the
three dependency rules and found the first satisfied and the other two
inapplicable *by construction* — the emitted file is flat, so there is no
recursion to need `FORCE` and no intermediate to need `.SECONDARY`.
`netcfgd` noticed `BUILD_DIR` was the canonical name without being told, and
`fuzzypickles` recognised the configuration-keyed object directory as the fix
for a bug it had hit and worked around by hand.

---

## 37. Where an include actually points

`beerssh` lost 84 files in one build to this, every one a plain missing
include, and called it the single highest-value change for that tree.

It includes its own headers subdirectory-qualified from the source root --
`#include "model/profile.h"`, not `#include "profile.h"` -- which is ordinary
C++ and is what stops `session.h` being ambiguous across six directories.
fmake added an `-I` for every directory that *contains* sources:

```
-I. -Isrc/input -Isrc/model -Isrc/platform -Isrc/ssh -Isrc/term -Isrc/ui
```

The file is in `src/model`, so `-Isrc/model` is what got added, and the
include is written relative to `src`, so none of them helped.

The suggestion was to add the common parent of the source directories. The
answer turned out to be smaller and exact: **the directory is whatever is
left of the resolved path once the include name is taken off the end of it.**
`model/profile.h` resolving to `src/model/profile.h` leaves `src`. A bare
`profile.h` resolving to `src/model/profile.h` leaves `src/model`, which is
the containing directory -- so this reads as a generalisation of what was
there rather than a new rule, and the flat case is untouched by construction.

The reproduction went from seven `-I` flags to two, `-I.` and `-Isrc`, and
the tree builds.

## 38. A test that passed on the crash it was looking for

`--clean` removes a whole directory. That is the one shape a wholesale
removal is allowed to take -- a directory the tool created, holding nothing
else -- and even then the rule is to verify the path rather than trust it, so
a symlinked state directory is now refused instead of followed.

The case for it asserted three things: a non-zero exit, that the output said
`symlink`, and that what the link pointed at survived. It passed. Removing
the guard, it **still passed**, and finding out why took six attempts.

Without the guard, `shutil.rmtree` refuses a symlink and raises, so the exit
is non-zero and the target does survive -- both assertions satisfied by the
crash. And the third:

```
stderr contains symlink: True
```

Python's traceback quotes the source line of every frame, and `shutil.py`'s
own code mentions `symlink`. **The assertion was satisfied by the text of the
failure it was meant to detect.** Every check passed, none checked anything,
and the only reason it came to light is that the mutation run said MISSED and
the number was not believed.

The case now matches fmake's own wording and requires that there was no
traceback at all. `working-practice.md` states the principle -- a passing
check is not evidence until you know it checked something -- and this is what
it looks like from the inside: not a gate that inspected an empty file list,
but an assertion whose substring appeared, for the first time, in the
diagnostic of the bug.

## 39. Whose program is it

Two of the five evaluations reported the same thing from opposite ends of a
tree. beerssh: *"The vendored submodule's own programs get built. `unterm`,
`vterm-ctrl`, `vterm-dump` and `harness` all linked successfully -- they are
libvterm's upstream tools. This project treats vendored code as exempt and
builds only the library from it. They were the only four things that did
link."* fuzzypickles: two submodules each producing a program called `test`,
and ten vendored fuzzers all defining `LLVMFuzzerTestOneInput`.

fuzzypickles proposed the obvious fix -- *"ignoring vendored subtrees by
default"* -- and it is wrong, which beerssh's report shows in the same
paragraph as the complaint. Both projects **build a library out of the
subtree**: libvterm is a static archive in one, `flog` is one of four
archives in the other. Skipping the directory would break both as surely as
building all of it does.

The two reports agree on something narrower than either states. What is
unwanted is not the vendored *code* but the vendored *decisions*: upstream
decided that `t/harness.c` is a program, and that decision was about
upstream's build, not this one. So the rule touches exactly one thing -- a
`main()` in a vendored subtree does not root a target. The file stays in the
pool, the library sources beside it link as before, and `[target.x] root =`
still builds it for anyone who wants it. That last part is not a courtesy:
`@target` in the source is the usual way to settle what a file is, and it is
unavailable here for precisely the reason the feature exists.

The signal is `.gitmodules`, or a `.git` that git put inside a subdirectory.
Neither is a heuristic -- one is this repository stating that a path belongs
to someone else, the other is git having placed a checkout there. Both are
needed and the cases prove it: a fresh clone before `git submodule init` has
the entry and no `.git`, which is the state about half of CI is in.

A subtree merely copied in carries neither, and is then indistinguishable
from the project's own code. That is the right answer rather than a gap:
nobody recorded it as separate, so nothing says it is.

### The half of the change that is not the feature

Removing a file from the roots removes it from `other_roots`, and
`other_roots` is what keeps an entry point out of an archive. So the fix
walked §28 back in through the door it had just opened -- a tree whose only
`main()`s are vendored builds as one library, and that library would carry
one of them, surfacing much later as a duplicate symbol in whatever links it.

The guard is one line and the case for it fails without it. Worth recording
because the shape recurs: a change that narrows what a thing *means* has to
be checked against everything that was keyed on the old meaning, and here the
two were four hundred lines apart with nothing naming the connection.

Mutation testing found it, but only because the alternative design was
mutated too. Four cases, four mutations, each caught by a different one --
and the fifth mutation, the wholesale-ignore design fuzzypickles asked for,
is what proves the escape-hatch case is testing anything at all. A case that
no mutation fails is not a case yet.

## 40. The step where every part was right

hydra's report, on a browser fmake built successfully:

> `credential_store.cpp` is `#ifdef HYDRA_HAVE_SECRET` from top to bottom.
> Both macros are defined by CMake *after* `pkg_check_modules` finds the
> library. fmake does not know they exist, so it compiled both files with
> them undefined, so the bodies vanished, so no symbol needed the libraries,
> so fmake **correctly** declined to link them.
>
> Every step is right and the result is wrong: a browser with no keyring
> integration and no desktop colour-scheme detection, built without a
> warning [...] which is worse than refusing.

That is the worst failure shape a build tool has, because there is nothing
to notice: no error, no missing symbol, no unresolved reference. The
program is built, is smaller than it should be, and says so nowhere.

The two reasons a proposal gets declined had been reported with one
sentence. They are different findings. *This header suggested a library the
code does not call into* is §3 working -- the symbol evidence disagreed with
the include and won. *This header sits behind a conditional the preprocessor
did not take* means the code that would have called into it was removed
before the compiler saw it, so there was no symbol to find and never could
have been.

Telling them apart needs no new machinery and no guessing. `-MD` is already
passed, and a depfile lists every file the preprocessor actually opened,
system headers included. A header the scan saw and the depfile does not name
was inside a false conditional. That is the compiler's own answer to the
question, not an inference about it -- the same shape as everything else
here: the text proposes, the build decides.

So the note stays a note, and the compiled-away case becomes a warning
outside `--explain`, which is what hydra asked for. The build that needs to
hear it is the one nobody is inspecting.

### What mutation said about the first attempt

Four cases were written; three of them were wrong in a way that reading
would not have found.

The first tried to be careful and returned three values -- yes, no, and
"there was no depfile to read" -- with a case asserting that a dry run
stays quiet. It does, and **not for that reason**: `-n` never resolves
libraries at all, so the code was not reached. Deleting a depfile does not
reach it either, because a missing depfile makes fmake recompile and the
file comes back. The distinction was untestable through every route tried,
so it is gone; what is left is a dict that simply lacks an entry for a
source with no depfile, guarded by one `.get()`. That guard is the single
branch here no case covers, and it is a guard rather than a claim: reaching
it would otherwise be a crash, not a wrong answer.

The second was the separator. Matching an include text against resolved
depfile paths is a suffix test, and it is only correct if the match starts
at a path component -- otherwise a local `xzlib.h` answers for `<zlib.h>`,
the guarded include looks like it was read, and the silent build comes back
by a second route. None of the three cases written first failed when the
separator was removed, because none of them had a header that could collide.
The mutation run named it, a case now covers it, and it is the same lesson
as §39 and §38 from a third direction: **a case that no mutation fails is
not a case yet.**

The third is smaller and worth naming because it is §38 inverted. A case
asserted that the word `conditional` was absent from the output, and it
failed on a correct build -- because the scratch directory is named after
the case, the case was called `a_dry_run_does_not_guess_about_conditionals`,
and the path appears in the output. §38 was an assertion satisfied by the
text of the failure it was looking for; this is one defeated by the text of
its own name. The fix is the same both times: match the whole sentence the
program prints, never a word that could arrive from anywhere else.

### And one the existing cases caught

Reading depfiles crashed on the one unit that has none by design. A vendored
archive in the tree is a `Unit` like any other -- it provides symbols, it
goes on the link line -- but it is never compiled, so §18 sets its `dep` to
None deliberately. `os.path.isfile(None)` is a `TypeError`, and it took out
eight cases at once, including the ejected-build comparison.

Nothing about the new feature was wrong; it assumed every member of a link
set went through a compiler, which had been true until §18 stopped being
true and nothing recorded the connection. Same shape as the `other_roots`
half of §39, one commit earlier, which is why it is worth writing down
twice: **a change that reads a property of every element has to be checked
against every kind of element**, and the kinds are not enumerated anywhere.

The suite named it in one run. That is what the eight cases were for.

## 41. Found means defined

§40 made fmake say when a feature had been compiled away. It did not make
the feature buildable, and hydra's request had a second half:

> **A form for "found means defined".** Something like
> `@pkg_optional libsecret-1 defines HYDRA_HAVE_SECRET`: one annotation
> covering the pattern that every optional dependency in every C project
> uses, and it stays a comment rather than becoming a build file.

That is the whole directive, spelled as asked. What it adds is the **macro,
not the library**. Once the macro is defined the guarded code is present and
its symbols ask for the library on their own, so §3 still decides the link
and the directive stays a statement about compilation. A package that is not
installed adds nothing, which is the answer a configure step would have
given.

The keyword `defines` is required rather than inferred from the argument
count. `@pkg_optional libsecret-1 HAVE_SECRET` reads as two packages to
anyone who has not memorised the order, and a directive whose entire purpose
is to stop a feature vanishing quietly must not have a spelling that makes
it vanish quietly. So a missing package is tolerated and a malformed
directive is fatal.

Both answers are printed. "Built without keyring support" is the sentence
hydra's browser needed and did not get -- but printing it only in the
negative case makes its absence meaningless, so the affirmative goes out
under `--verbose`. A reader who sees neither knows the file has no optional
dependency, rather than guessing which of two silences this one is.

The diagnostic from §40 now names this directive as the remedy, and the
directive removes the diagnostic. That is the loop closing: fmake reports
the thing it cannot see, and names the way to tell it.

### The advice that pointed at a door that was not there

`@pkg_optional` in `fmake.mk` is refused, correctly -- it is a fact about
one file. The refusal said:

    Put it in the source file it is about, or in fmake.toml under [target.*].

There is no `[target.*]` key for it. The sentence was a fixed string shared
by every directive that reaches that branch, and it had been right often
enough that nobody checked. Following it produces a `fmake.toml` fmake then
rejects, which is §31 exactly: a diagnostic whose remedy costs more than the
error did.

The message now consults the schema. And the case covering that branch
**asserted the wrong version**: it required `fmake.toml` in the output for
`@target`, `@os` and `@kind` alike, and `[target.*]` has keys for two of the
three. The test had written §31 down as a requirement. It now asserts the
distinction rather than the sentence, which is a better case than the one it
replaced -- and it was found by the fix failing it, not by reading it.

## 42. The feature that was there

netcfgd declined, and named one reason:

> `client/` exists to produce `libncfg_client.a`. `gui/` links it. That
> archive *is* the deliverable [...] fmake linked the library sources
> **into the test binary** and produced no archive. `--help` offers
> `--no-libs`, which is about resolving external symbols to system
> libraries, and nothing that says "these translation units are a library
> others link".
>
> **Suggestion:** treat "library plus consumers" as a first-class inferred
> output, or say plainly in the README that fmake builds programs.

Neither, because the premise is wrong. Their tree builds today, with one
comment and no build file:

```
/**
 * @kind static
 * @target ncfg_client
 */
```

That produces `libncfg_client.a` holding exactly `ncfg_client.c.o` and
`ncfg_json.c.o`, and `client_test` beside it, unaffected. §3 decides the
archive's membership the same way it decides a program's.

So this was a **discoverability** failure, not a missing feature, and that
is worth more attention than a missing feature would have been. A gap is
found by the person who needs it; a feature nobody can find is declined by
someone who then reports the tool cannot do it, and the report is
convincing because they did the work. They read `--help`, they read the
README, and they ran it. Three surfaces, and the answer was in none of
them: the README's directive table said `@kind` "inferred from `main()`
otherwise", which describes the mechanism and not the thing anybody wants
it for.

The fix is in the place the question is asked. `--explain` printed the kind
and never said what decided it:

    target client_test (exe)  [no @target]

and now says:

    kind    exe: tests/client_test.c defines main(); @kind static builds
            an archive instead

Three provenances -- declared in `fmake.toml`, declared with `@kind`, or
inferred -- and only the inferred one names the alternative, because that is
the only case where the reader might not know there is one. The README grew
the worked example: the same tree twice, once producing a program and once
producing both.

### What this says about the other four reports

Every one of them was written by someone who ran fmake rather than read
about it, which is the only reason this surfaced at all. It also means the
rest of their findings deserve the same question before any of them is
built: **is this missing, or is it unfindable?** For hydra's two it was
genuinely missing, and §40 and §41 built it. For this one the answer was a
comment nobody could have guessed was there.

## 43. The blocker that was a comment, again

hydra's first finding, and the only one in five reports called a hard
blocker:

> `src/` holds `android_view.cpp`, `android_downloads.cpp`,
> `android_intents.cpp` and `android_dialogs.cpp`. CMake adds them only
> inside `if(ANDROID)`. They carry no self-guard, because the build system
> is what excludes them. [...] So it does not merely link something odd --
> it fails. **fmake cannot build hydra's `src/` today**, and no flag fixes
> it, because the question is which files belong in this build rather than
> how to compile them.

Right about the question. The answer is `@os android`, four comments, and
the build goes through. §42 asked whether a finding is missing or
unfindable, and this is the second one running to be unfindable.

Worth understanding *why* those files get compiled at all, because it is
§40's mechanism from the other side. Nothing links them: the app does not
reference them on Linux. But `main.cpp` includes `android_view.h` behind an
`#ifdef ANDROID`, and the scan reads text and cannot evaluate a conditional,
so the header is proposed, its implementation becomes a candidate, and the
candidate is compiled before any symbol has a chance to say it is not
needed. The proposal being wrong is by design -- being wrong there costs a
compile and never a wrong link set -- and here the compile is the thing that
fails.

So a file that cannot compile is not evidence that the tree cannot be built.
Reproduced as a case, and in the reproduction fmake **still produced the
program**: the failed file was not reachable, so nothing needed it. That is
the design working, and it is also why the diagnostic matters more than the
failure does -- somebody reading it decides whether the tree is broken.

### Two causes, one symptom, and no way to tell

A header on no include path is equally the symptom of a package nobody
installed and of a file belonging to another platform. fmake cannot tell
them apart, so the failure names both and lets the reader choose:

    * QJniEnvironment: No such file or directory
      in android_view.c
      QJniEnvironment is on no include path here
      if it comes from a package, install it or name it with @pkg
      if android_view.c belongs to another platform, @os NAME or @arch NAME
      keeps it out of this build

Naming the likelier cause would have been worse than naming neither. This
is §31's rule with the sign flipped: there, advice was wrong because it
pointed at a `[target.*]` key that did not exist; here it would be wrong by
being confident. A guess dressed as a diagnosis is how somebody spends an
afternoon installing a package they do not need.

The advice is gated on the message actually being a not-found, so a type
error gets none -- that is the case that would otherwise rot, since the
cheapest wrong implementation prints the note on every failure and every
existing case still passes.

### What hydra asked for instead, and why it is not here

They proposed a filename convention: ignore `*_<platform>.cpp` unless
building for that platform, since it is "the one a tool can act on without
being told". It would work, and it is a **default change** -- a file called
`net_win32.c` would stop being built by a tool that built it yesterday, in a
project that never opted in. That is a convention change and belongs to
whoever owns the convention, not to whoever is in the file. Recorded here,
unbuilt, with the same standing as the tests question in §36.

## 44. The gate that could not see what it was built for

apt-emerge's evaluation ended in *not applicable* -- no C or C++ in the tree
-- and found a bug anyway. `debian/control` declared `python3 (>= 3.11)`;
two f-strings used PEP 701, which is 3.12. On bookworm the package installs,
satisfies its dependency, configures, and then dies with a `SyntaxError`
before reaching `main`. They also supplied the detector, because the obvious
check is worse than useless: `ast.parse(..., feature_version=(3, 11))`
*accepts* these, the change being in the tokeniser rather than the grammar.

That became a case. This section is about the case being wrong.

A third such f-string was written after it -- in `--explain`'s external
symbol tally -- and **the gate passed on a file `python3.11` refuses to
parse**. The suite was green at 188 while the declared interpreter could not
read the program.

The reason is one variable:

```python
if tok.type == tokenize.FSTRING_START:
    start = tok.start[0]
elif tok.type == tokenize.FSTRING_END and tok.end[0] != start:
    bad.append(start)
```

f-strings **nest**: a replacement field can contain another f-string. The
inner one's `FSTRING_START` overwrites `start`, so when the outer one's
`FSTRING_END` arrives, its span is measured from the inner one's opening
quote. The outer f-string spanned lines 4053 to 4054; the inner opened on
4054; `4054 != 4054` is false; the file passed. A stack fixes it, and the
mutation confirms the single variable misses exactly this shape.

Nesting is not an exotic case here -- it is what `DIM(f'...')` inside an
f-string is, and that is the house style for every coloured line in
`--explain`. The gate was blind to the most common way this file writes
f-strings.

### Two checks, and the second is the one that is evidence

The token check is an *inference* about what an old interpreter would say.
Where the declared interpreter is actually installed, the case now runs it:
`--version` and `--help` under `python3.11`. That covers every syntax added
since 3.11 rather than the one that bit us, and it needs no cleverness to
stay correct.

This is `working-practice.md`'s rule with a concrete face. A passing check
is not evidence until you know it checked something -- and here the check
was not vacuous, not misconfigured, not skipped. It ran, it examined the
right file, it used the right token type, and it was wrong about a case
nobody had thought of. The only thing that would have caught it earlier is
the thing that caught it now: running the old interpreter.

It surfaced by accident, while correcting a README sentence about which
Python version the package requires.

## 45. A way in, not only a way out

`--eject` was built as an exit: a tool this opinionated has to be leaveable.
Two of the five evaluations independently pointed out that it is also the
adoption path, and that nothing says so.

netcfgd, in an addendum correcting their own evaluation for never having
tried it:

> Ejecting is probably **the adoption path for exactly the projects most
> likely to say no**. [...] "Use fmake as a generator, commit the output, and
> your users need nothing" is a different and much easier sell than "adopt a
> build tool", and it costs the project nothing it does not already have.

fuzzypickles went further and named the missing piece:

> Ejecting a Makefile that a hand-written one can **include**. If the
> ejected file can be a *fragment* that an existing Makefile includes for
> the compile rules while keeping its own packaging targets, that is an
> incremental adoption path rather than a switch. **That would make the
> verdict above obsolete, because scope stops being the objection.**

Their verdict was "not a switch today, and the reason is scope rather than
quality": fmake would own compile-and-link well, but their build is mostly
not compile-and-link -- CPack, qmake, androiddeployqt, five submodules, and
a `make apk` sequencing all of it. Adoption meant two build systems where
there was one. A fragment removes that objection without answering it.

`--eject make-fragment` is the same emitter with three differences, and only
one of them is about taste:

- **No default goal.** The parent keeps `all`, and the fragment's aggregate
  rules are `fmake-all` and `fmake-clean` so they cannot collide. If it is
  included before the parent defines anything, `fmake-all` is the first rule
  and therefore what Make lands on -- deliberately, so the accident builds
  everything rather than one object file.
- **`FM_` on every variable it owns.** This is the one that matters. A
  parent Makefile setting `CFLAGS` is the most ordinary thing a Makefile
  does, and with unprefixed names it would replace every flag fmake worked
  out -- silently, since the build still runs. The case sets
  `CFLAGS = -this-would-break-everything` in the parent and requires the
  program to build and print the right answer.
- **`CC`, `CXX` and `AR` unprefixed and `?=`.** Those the parent *should*
  control, and a cross build is the obvious reason.

### Three smaller things in the same file

All from beerssh and netcfgd reading the ejected output against the rules
they would judge it by, which is the review nobody else was going to do.

- **The `-include` line spelled out every object.** It worked. It was also
  unpleasant to hand-edit, in a file whose header invites hand-editing.
  There is an `OBJS` list now and the line reads `-include $(OBJS:.o=.d)`.
- **`.SECONDARY` is absent and should say so.** beerssh worked out that none
  is needed -- the output is flat, one explicit rule per object, so nothing
  is an intermediate and the hazard has nowhere to live -- and observed that
  somebody adding a bare `.SECONDARY:` later to be helpful would reintroduce
  it. The header now says why there is none.
- **Ejecting silently changes the flags.** netcfgd ejected over a Makefile
  carrying `-std=c11 -Os` and nine warning flags its own comments called
  *"not decoration: this code parses bytes from a socket into indices, and
  every one of them has caught something in code shaped like this."* The
  ejected `CFLAGS` was `-O2 -g -I.`. fmake cannot be blamed -- the Makefile
  had been deleted before the run -- but the header can say it, and now
  does: diff the flags first, a dropped `-W` set is silent and shows up as
  behaviour.

That last one is the same failure as §40 in a different place: a build that
succeeds while doing less than it should, with nothing to notice.

## 46. The first thing two projects hit

fuzzypickles' finding 2 and beerssh's finding 1 are the same one, and it is
the very first thing each of them ran into:

> `cli/main.c` wants to be a program named `cli`, which is a directory. This
> tree names each program's directory after the program: `cli/main.c`,
> `daemon/main.c`, `tui/main.c`. All three collide with their own directory
> when output goes to the project root.

> `tests/main.cpp` wants a target called `tests`, which is a directory. Same
> collision fuzzypickles reported.

`src/main.cpp` does not have this problem, because `src` is already skipped
as a directory name that names nothing -- the target takes the project's
name instead. `tests` is not skipped, and cannot be: skipping it lands on
the project name too, which is what the app is already called.

So the name is genuinely undecidable and the refusal was right. What was
wrong is that it refused a shape common enough that two of five projects met
it before anything else, and both had to write a config file to get past the
first run of a tool whose premise is not needing one.

A name **nobody chose** is now qualified with the project's: `tests` becomes
`beerssh_tests`. A name somebody chose -- `@target`, or `name` in
`fmake.toml` -- is still refused, because renaming what an author asked for
gives them a binary under a name they did not pick and no reason to look.

This cannot break a build that works. The only trees it affects are the ones
that stopped with an error, and it says what it did rather than doing it
quietly.

### The section key is not the directory, and the error did not say so

Reproducing beerssh's tree, the obvious `fmake.toml` was:

```toml
[target.src]
name = "beerssh"
```

which is wrong, and the error said only *"declares no root and no sources,
so fmake cannot tell what is in it"* -- which reads as an instruction to add
a root. The real problem is the key: a `[target.*]` section is keyed by the
name the target **already has**, and `src/main.cpp`'s target is called after
the project precisely because `src` names nothing. `[target.src]` matches
nothing and never could.

The message now lists the target names that exist. It was found by making
the mistake, which is the only way this one was going to be found -- the
behaviour is correct, documented, and still surprising, and no test would
have been written for a message nobody suspected.

That is three findings in a row (§42, §43, this) where the tool was right
and the way it said so was not.

## 47. The entry point that was a macro

beerssh's finding 5, and the one that sounded most like a design flaw:

> **Symbol reachability does not work for a Qt program.** `--explain`
> reported **547** sources as "defines nothing reachable", including every
> `moc_*.cpp`. That is correct as far as symbols go and wrong about the
> program: a `QObject`'s slots are reached through the meta-object system,
> and a QtTest class is reached by `qExec` walking its metadata, so nothing
> references them directly.

Their suggested heuristic -- *a translation unit generated by `moc`, or one
whose header carries `Q_OBJECT`, is always reachable* -- would have been
wrong, and building it would have papered over the real cause with something
that also breaks §3. A moc output **is** reached by symbols: it defines
`Counter::staticMetaObject`, which the class's vtable in `counter.cpp`
refers to. Reproduced on a Qt tree, moc output links because a symbol needs
it, exactly as designed.

The real cause is one line of Qt API. `QTEST_MAIN(CounterTest)` is how every
QtTest translation unit declares its entry point, and it is a **macro** --
so the scan, which reads text and looks for `main(`, finds nothing. The file
roots no target. Nothing else references it. So it is not compiled, and
`--explain` says it defines nothing reachable, which is true and useless.

Their 547 was two findings stacked: the include-path failure of §37 stopped
84 files compiling, and every QtTest file was invisible on top of that.

The fix is not an exception to the two-signal design, it is the design.
`QTEST_MAIN` and its `APPLESS`/`GUILESS` variants are a **proposal** that
the file is a program; the object settles it, the same way a textual
`main()` is settled. That machinery already existed for the opposite case --
a `main()` behind a false `#if`, §28's mirage cache -- and it covers this one
unchanged: `QTEST_MAIN` inside `#if 0` compiles, exports no `main`, gets
dropped, and is remembered so the disagreement is reported once.

Everything downstream is untouched. Qt6Test is linked because `QTest::qExec`
is undefined in the object, not because the file looked like a test.

### Three assertions, three lessons, one of them for the third time

Mutation testing rejected the first version of all three checks.

The variants had no coverage: removing `APPLESS` and `GUILESS` from the
pattern failed nothing, because the case only used plain `QTEST_MAIN`. A
family named in a regex needs a case per member, or the regex is a guess
wearing a test.

The cache assertion was about the wrong thing. It checked that the mirage
was not *recompiled* on the second build -- which passes with the memory
removed, because the object cache prevents the recompile anyway. What the
memory buys is **silence**: the disagreement reported once rather than every
build. The assertion says that now.

And the first attempt at that check asserted `"maybe_test.cpp" not in
output`, which failed on a correct build, because §40's conditional-include
note names the file for an unrelated and entirely correct reason. That is
the third time in this session -- §38, §43, here -- that an over-broad
substring has cost a diagnosis. The rule has earned promotion from
observation to practice: **assert the sentence the program prints, never a
token that can arrive from somewhere else.**

## 48. A guarantee nobody had asserted

netcfgd asked a question rather than reporting a defect:

> **A flag-stamp file.** `client/` has `.build-flags`, a file containing the
> compiler and flags, which every object depends on. It exists because
> `make SANITIZE=1 test` followed by a plain build in `gui/` linked a
> sanitized archive into a binary with no sanitizer runtime -- forty lines
> of `__asan_report_store1` at link time and no clue why. Changing flags is
> not changing a source file, and nothing in the file tree records that it
> happened.
>
> This is a general problem, not a local one: **any** builder that caches
> objects has it. If fmake keys its object cache on flags already, say so --
> it is a real advantage over a naive Makefile and nobody would guess it. If
> it does not, that is a stale-object bug waiting in every project that
> switches compilers or adds a sanitizer.

It does, and the comment on the key says why: *"a flag that is not in it is
a flag that silently reuses objects built without it."* Their incident
cannot happen here.

**It was not asserted anywhere.** The nearest case wiped `.fmake` between
its two builds -- which is precisely the thing that must not be necessary,
so the case was passing over the top of the guarantee rather than through
it. A property documented and untested is a property that will be true until
someone tidies the key.

### Four components, and the first three probes were weak

Writing the case was easy and writing a case that *tests* it took four
attempts, each found by mutation rather than by thought.

- **Plain build vs `--cflags` does not test the override.** Passing
  `--cflags` at all replaces the default flags, so the two builds differ in
  the key for that reason alone. Removing the override from the key entirely
  left the case passing. The probe that works is two *different* `--cflags`
  values, which are identical in every other component.
- **`--cflags` on both sides does not test the configured flags.**
  `[project] cflags` is a different field reached by a different route, and
  with a command-line override in play it is empty on both sides. Editing
  `fmake.toml` between two builds is what exercises it.
- **The compiler was untestable as written, and then was not.** One
  toolchain on the machine looked like the end of it -- until `cc` and
  `gcc`, the same binary under two names, turned out to be exactly the
  check: two different answers to "what built this", and a wrapper under a
  different name is not obliged to behave like the thing it wraps. The
  assertion is on the object directories rather than on behaviour, because
  behaviour is identical and that is the point.

The sanitizer half is its own case, at the size the bug actually occurs:
build instrumented, rebuild plain, and require that `__asan` is gone. That
one needed no cleverness and is the one somebody will read.

The pattern across all four: **a case for a guarantee has to vary exactly
the thing the guarantee is about**, and the natural way to write it varies
two things at once. Mutation is the only reason any of that surfaced.

## 49. Tests are built by the test target

Three of the five evaluations reported this, and it was the only finding any
of them called a genuine conflict rather than a configuration gap.
fuzzypickles: *"fmake compiled all ~35 test binaries along with everything
else [...] this is the one finding that is a genuine conflict, and I could
not see a way to express 'these `main()`s are tests' other than enumerating
them."* netcfgd and beerssh said the same, and `build-and-commit.md` is
explicit: the default target does not build tests, and a separate one builds
and runs them.

It was left unbuilt for several rounds because it is a **default change** --
a tree that builds a test binary today stops doing so -- and that is a
convention decision rather than one to make while working on something else.
Approved, so: built.

**Two conventions, both named by the projects that asked**: a directory
called `test` or `tests`, and a file called `foo_test.c` or `test_foo.c`.
Nothing else. The net is deliberately narrow because a wrong guess here
costs a program its place in the default build, which is a worse failure
than the one this fixes -- so the reason is reported (`--explain` names it)
rather than assumed, and `@test` / `@test no` in the source and
`test = true` / `false` under `[target.NAME]` decide it outright.

**A role, not a kind.** A test is still an ordinary `exe`; what changes is
only whether a plain build produces it. Naming one on the command line still
builds it: the rule is about what a bare `fmake` does, not about permission.

**`fmake test` builds and runs.** Running is half the convention -- the rule
it is paired with is never to conclude a test passed from a binary the build
step did not rebuild -- and a failed assertion and a crash are reported as
the different things they are, since Python renders both as a number.
`test-args` under `[target.NAME]` covers netcfgd's
`./tests/client_test ../docs/schema/socket.json`, which was their third
finding and is a test whose whole purpose is the file it is handed.

**Ejected build files get it too**, because an ejected Makefile is a
Makefile someone will edit, and these projects would judge it by the same
rule. `all` does not depend on `test`; `test` builds and runs. Ejecting also
had to stop honouring the hold-back: a build file that cannot build the
tests *at all* is a worse answer than the one the convention is about.

### Not compiling them is most of the point

Holding a test back from the *link* is easy and buys almost nothing. A
static target with no declared membership takes the whole tree as
candidates, so all thirty-five test binaries' objects were still built and
merely never used -- which is most of the cost the convention was traded
for. Held-back roots are subtracted from the candidate set, and it has to
happen **after** the library branch resets that set to everything, which is
the sort of ordering that looks arbitrary until it is wrong.

The subtraction is safe by construction rather than by care: an exe root is
already excluded from every library closure, so nothing wanted could have
used it.

### What the suite said about the change

Nine cases failed, and eight of them were fixtures using `tests/` or a
`_test` name for reasons that had nothing to do with tests -- the per-target
compile-failure case, the kind-explanation case, the macro-main case. Each
was passing for a new and wrong reason, or failing for one. That is what a
convention change looks like from inside a suite: the convention is now
*meaningful*, so every incidental use of it became a statement.

Four of them got stronger for it. The two-binaries case now asserts that
`tests/` means two things at once -- the target's name is qualified because
`tests` is a directory, and the program is held back because `tests` is
where tests live -- and that both hold together.

The ninth was mine: a multi-line f-string in the new `--explain` line, PEP
701, caught by the gate repaired in §44 two commits earlier. It would have
shipped a package that installs on bookworm and dies on startup. The repair
paid for itself within the session.

### And three mutations the first cases missed

- **A fixture in `tests/foo_test.c` satisfies both conventions**, so
  deleting either rule failed nothing. They are one file each now:
  `tests/runner.c` and `smoke_test.c`.
- **The candidate subtraction needs a library in the tree to exist at all.**
  Without one the candidate set comes from the program's include graph and
  never reaches the tests, so the case passed whether the rule was there or
  not -- the same shape as §48's weak probes, and found the same way.

## 50. A file named for a platform

hydra's finding 1, the only thing across five reports called a hard blocker,
and the second half of its answer. §43 made the failure say `@os NAME`
excludes it; this is the rule that means nobody has to.

> `src/` holds `android_view.cpp`, `android_downloads.cpp`,
> `android_intents.cpp` and `android_dialogs.cpp`. CMake adds them only
> inside `if(ANDROID)`. They carry no self-guard, because the build system
> is what excludes them. [...] A documented suffix rule -- ignore
> `*_<platform>.cpp` unless building for that platform -- would cover the
> common case and stay inside the "no build file" premise. **Hydra would
> rename four files to adopt it, cheerfully.**

The rule feeds the machinery that already existed rather than duplicating
it: a suffix is read as an implicit `@os` or `@arch`, and `platform_excludes`
decides as before. So the name proposes and the existing matcher disposes,
which is the same split as everywhere else here.

### The narrowness is the design

A naming convention is dangerous in a way an annotation is not: it acts on
files whose authors never opted in, and the failure is a symbol that stops
existing. So the table holds only spellings that cannot mean anything else.

- `_win32`, `_windows`, `_android`, `_darwin`, `_aarch64` -- unambiguous.
- **`_win` is not in it**, because that could be a window. Nor `_mac`,
  because that could be a MAC address.
- **`_posix` and `_unix` are not in it**, because a family is not a
  platform -- and fmake's own README uses `util_posix.c` as an example of a
  file it copes with, which would have made the feature contradict the
  documentation on its first line.

There is a case for exactly this, and it is the one that keeps the net
narrow: four files named `util_posix.c`, `main_win.c`, `mac_address.c` and
`frame_unix.c`, all of which must build. The cheapest wrong implementation
accepts all four, and every other case here still passes under it.

**Directories were considered and left out.** `platform/win32/foo.c` is a
real convention, and nobody asked for it. Doubling the surface of a rule
whose whole safety argument is narrowness, for a case no report mentioned,
is how a convention stops being predictable.

### Both directions, and only excluding

`@os` and `@arch` override the name outright, **including when they name the
platform being built for**: the name is a convention and the annotation is a
statement, and a file carrying both means the second. Without that the rule
would be inescapable for anyone whose filenames it reads wrongly, which is
what separates an opinionated default from a trap.

And the rule only ever *excludes*, and only a file naming somewhere else. A
file named for the platform being built for is untouched -- `platform_linux.c`
on Linux is simply compiled -- so on any given machine most trees see no
change at all. That is what makes a default change of this kind survivable:
the blast radius is exactly the files that could not have been building
usefully anyway.

It is said out loud, because a file that stops being compiled is a file
whose symbols stop existing, and the link error that follows names neither
the file nor the reason.

### One thing not covered, said plainly

The suffix table is searched longest-first so a shorter spelling can never
win. No pair in it currently collides -- `_x86_64` does not end with any
other entry -- so removing the sort fails nothing today. It stays as a guard
against the next entry rather than as a claim, and the case says so instead
of inventing a fixture that pretends otherwise. Same honesty as §40's
unreachable `.get()`: a branch no case covers should be labelled, not
decorated with a test that does not test it.

## 51. What the hydra trial found

hydra was the tree that produced §17, §40, §41 and §43, always at second
hand -- from a report. Running fmake on it settles three things and finds a
fourth.

**It builds.** hydra's report said *"fmake cannot build hydra's `src/`
today, and no flag fixes it"*. 112 sources, 47 headers moc'd, no
configuration, no annotation, no `fmake.toml`: one binary, and `ldd -r`
reports zero undefined symbols. The Android sources compile and are left out
of the link because nothing reaches them, which is §3 rather than anything
platform-specific -- the `_android` suffix rule of §50 never fires, because
hydra's files are named `android_view.cpp` with the platform in *front*.
That is worth knowing: the convention they asked for and the names they
already have do not meet, and the rename they offered is still a rename.

**The link set is smaller than CMake's and complete.** CMake names
`liblz4`, `libsodium` and `libxxhash`; fmake links none of them, because no
symbol in hydra needs them -- they are libtorrent's own dependencies, and
the dynamic linker finds them through it. Zero undefined symbols is the
proof, and it is the same result hydra reported the first time.

**The two silent features are now loud**, by file and line, and two
`@pkg_optional` comments turn both back on. That is §40 and §41 verified on
the tree that motivated them rather than on a fixture.

### And the fourth thing, which is why trials are run

There were never two silent features. There are **five**.

`torrent_download_source.cpp`, `session_import.cpp` and `box_crypto.cpp`
guard libtorrent, lz4 and libsodium the same way, and **fmake said nothing
about any of them.** The browser built without torrent support, without
compressed session import, and without box crypto, exactly as before §40 --
which is the failure §40 exists to prevent, arriving by a route §40 cannot
see.

The reason is structural. §40 keyed the finding on a *proposal*, and a
proposal comes from pkg-config attributing a header to a module. That
attribution works by matching include directories -- so a package whose
headers sit in a default include directory emits no `-I`, is attributed to
nothing, proposes nothing, and cannot be reported. `pkg-config --cflags
libtorrent-rasterbar` prints eight `-D` flags and not one `-I`.

So the report is no longer keyed on the proposal. Any `<>` include the scan
saw, the depfile shows the preprocessor never opened, **and the machine
actually has** is reported -- with the module named where one is known, and
without where it is not.

Three details, each of which the trial or a mutation forced:

- **Existence is what keeps it quiet.** `#ifdef _WIN32` guarding
  `<windows.h>` names a header this machine does not have, so nothing was
  lost and nothing is said. Without that check every portable C file
  produces a warning.
- **`<>` only.** `#ifdef DEBUG` guarding `"debug_helpers.h"` is the project
  deciding about its own code; there is no package and nothing missing.
- **One line per file.** hydra's guarded block opens with fourteen
  libtorrent headers, and fourteen identical lines is how a real finding
  gets skimmed past. A file already named with its package is not named
  again without one -- `theme.cpp` was reported twice, once each way, which
  reads as two problems.

The general lesson is the one §42 started: **a diagnostic keyed on a
mechanism only sees what that mechanism sees.** §40 was keyed on
pkg-config's view of the world and inherited its blind spot silently,
because a report that does not fire looks exactly like a tree with nothing
to report.

## 52. BUILD_DIR, and a table that was aligned once

The canonical name for a build output directory moved from `OBJDIR` to
`BUILD_DIR`, chosen across the workspace by counting spellings rather than
by taste. Two projects had praised fmake for emitting `OBJDIR` -- it was the
canonical name when they looked -- so the rename costs that agreement and
buys the current one.

`OBJDIR` survives in one place and deliberately: fmake's own Python
variable for `.fmake/obj/<key>`, which holds object files and nothing else.
The two names are not synonyms -- object files versus the whole build tree
-- and the convention governs the variable a build script exposes, not an
internal identifier for a directory of `.o` files.

**It is emitted in four places and one was missed.** The standalone
Makefile, the fragment's `FM_` copy, ninja's declaration, and ninja's
*rules*, which reference `$objdir` a hundred lines below where it is
declared. Renaming the first three produces a `build.ninja` that parses
perfectly and cannot build anything. There is a case for all four now.

### The alignment the rename broke

The variable block was hand-spaced to a column that fitted `OBJDIR`:

    CC       = cc
    CFLAGS_LAST =
    BUILD_DIR   = build

Three columns, from a table that had one. That is what a hand-counted
column does the first time a name changes, and the fix is to compute the
width from the longest name the file actually emits.

Then mutation found a second alignment fault the first fix did not: `?=` is
two characters and `=` is one, so a fragment -- which uses both -- had every
plain assignment a column left of every conditional one. The operator is
right-aligned in two columns now. Neither fault is visible in a file that
uses one spelling or the other, which is why the fragment was where it
showed.

Alignment is rule 2 of `code-style.md` applied to the file fmake *writes*
rather than the file it is. A generator that emits misaligned tables is
teaching its own convention to everyone who ejects.

### Two sessions, one repository

This work was mostly already done when it was started. A concurrent session
had installed `tools/style_gate.py`, `tools/hooks/commit-msg`,
`.style-gate.toml`, `make style` and `make hooks`, and renamed the
Makefile's own variable -- and had committed four times on top of this
session's last commit.

Copying `style_gate.py` from `~/.claude/tools/` over the project's copy
removed the two-line provenance header the project copy carries and the
source does not, which `git diff` caught before it was committed. The lesson
is the one the global guidelines already state and this session had to learn
by doing: **look at what is there before writing, because another session
may have been here since the file was last read.** `git status` before a
commit is not paperwork.

The style gate then found two `section` signs in comments -- introduced by
this session, hours before the ASCII rule that forbids them existed. A rule
written down after the fact still applies to what is in the tree, and a gate
is how that stops being a matter of memory.

## 53. hydra, built

The second hydra trial, on the whole tree rather than `src/` alone. Three
things that were open are now measured, and two are new.

**The ejected Makefile builds hydra, and produces the same binary.** 1126
lines, moc rules driven by `Q_OBJECT` rather than a list, `make -j8` in 36
seconds with no fmake on the machine -- and 17,314 defined symbols against
fmake's own build, **none differing**. The equivalence claim had been
checked on qView at 2,562 symbols; this is the same claim on a tree with 47
moc'd headers and Qt WebEngine in the link.

**The tests convention holds at scale.** Pointed at `src/` and `tests/`
together, a plain build produces the browser and holds back **66 test
programs**; `fmake test` builds all 66 and runs them. That is the step
hydra's report listed as *what would finish it* -- "point fmake at the tests
and compare its closure against the 28 binaries CMake builds" -- and it is
answered.

**And the crash/exit distinction earns itself immediately.** Of 47 that ran,
nine failed: six `exit 1`, one `exit 2`, and **two killed by SIGSEGV**.
Those two are a different finding from the other seven, and a runner that
printed "failed" for all nine would have buried them.

### Two findings, both about running rather than building

**`fmake test` has no timeout, and hydra has 26 live drivers.** The run
stopped at 47 of 66 because a test binary was still fetching a real website
several minutes in. Nothing is wrong with the test -- it is a live driver
and doing what it says -- but a runner with no timeout means one network
test suspends the suite indefinitely, and the useful signal is the 47
results already collected. A per-test timeout is the obvious answer and it
is a design decision: what the default should be, whether it is per test or
per suite, and whether a project can raise it.

**`tests/` cannot distinguish a unit test from a live driver.** hydra
separates them; the convention does not, so `fmake test` runs both. The
convention is doing exactly what it was asked to and the tree wants a
finer cut than a directory name -- which is the same shape as the
`_platform` suffix rule, and the same answer applies: an annotation states
what a name can only suggest.

Both are recorded rather than built. Neither is a defect in what exists.

### The flag list that was one line

Ejecting hydra prints a `CXXFLAGS` of about eighteen hundred characters,
because Qt WebEngine contributes some thirty `-I` and `-D` flags. The file's
header invites hand-editing, which is the argument beerssh made about the
`-include` line naming every object; it applies with more force here. Long
values wrap now, at continuations aligned under the value with spaces --
alignment rather than indentation, rule 2.

Make joins a continuation with a space, so the value is unchanged, and the
proof is not the wrapping case: it is the symbol-for-symbol comparison,
which was re-run afterwards and still reports zero differing symbols out of
17,314.

Mutation caught the wrapping case twice. Asserting "some line ends with a
backslash" passes with the continuation removed, because `CLEAN` and `OBJS`
are backslash-continued lists elsewhere in the file. And the fixture used
`--cflags`, which is an *override* and lands in `CFLAGS_LAST`, so it never
exercised the line the finding is about. Both are the same error as the
three before them: assert the thing, not something the thing resembles.

## 54. A deadline for each test

hydra's suite stopped at 47 of 66 because one live driver was still fetching
a real website several minutes in. Nothing was wrong with that test -- it is
a live driver doing what it says -- but a runner with no limit lets one of
them suspend the suite and throw away the 47 results already collected.

**Per test, not per suite.** A shared budget makes one slow test steal from
the others and makes the outcome depend on the order they run in, which is
the property a test runner exists to remove.

**Sixty seconds by default**, `test-timeout` under `[project]` or
`[target.NAME]` to change it, and `0` to remove the limit rather than a
number large enough to look like one.

**Timing out is its own finding.** Not "failed", which is what a test that
returned 1 did, and not a crash -- the same argument as the SIGSEGV
distinction, which hydra's real suite had already justified twice over.

### The deadline has to reach what the test started

A test that hangs on the network usually hangs with a helper alive, and
killing only the process fmake launched leaves that helper holding the
terminal. So the test is given its own session and the signal goes to the
group: SIGTERM first, because a test with a handler may want to unlink a
temporary file, then SIGKILL, because one that ignores TERM is exactly the
kind that needed a deadline.

Two of the seven mutations here were caught by the **suite hanging** rather
than by an assertion -- removing `start_new_session`, and signalling the
process instead of the group. That is a legitimate catch and an awkward one:
it needs the mutation runner to bound its own subprocess, or the run that
proves the feature works is the run that never ends.

### Two things this cost, both worth writing down

**A mutation script that dies leaves the mutation in place.** The first
attempt at this batch used one `pkill -f` pattern broad enough to kill the
script running it, so the `finally` that restores `fmake` never ran and the
tree was left carrying "a timeout does not fail the command". `git diff`
found it. The batch runner now takes one mutation per invocation, bounds the
suite with its own timeout, and never signals by pattern.

**One full-suite failure was observed and has not reproduced.**
`environment_beats_the_config_file` failed once in a run immediately after
this feature landed, and passed in three subsequent full runs and in
isolation. The mechanism is not understood. The plausible story -- that
`killpg` on a recycled pid signals an unrelated group -- does not hold up:
`Popen` has not reaped the leader at that point, so the pid is a zombie, and
a zombie's pid is not reissued.

It is recorded rather than explained, and rather than quietly forgotten.
Section 29 is in this document because a flake dismissed once cost a session
later; the honest state of this one is *seen once, cause unknown, three
clean runs since*.

## 55. What is built and what is run are different sets

`fmake test myapp` built the program and then **ran it as a test**, printed
its output among the test output, and counted its exit status in the total.
Found by asking what happens when `test` is named alongside something else,
which is an ordinary thing to type and which no case covered.

The cause is one line: the runner was handed `wanted`, the set that was
*built*. Building the program was right -- it was asked for. Running it was
not. The runner takes the tests out of that set now.

This is the same shape as the `other_roots` half of section 39 and the
vendored-archive crash of section 40: a set that was correct for the
question it was assembled to answer, reused for a different question a few
hundred lines away. Three times in this document now, which makes it a
pattern rather than an accident: **when a set crosses a boundary, say which
question it answers.**

### And the thing it made obvious

Naming a test only ever built it, while `fmake test` ran all of them, so
there was no way to run one. On hydra that means sixty-six tests to re-run
one, and six of them fail in this environment for reasons having nothing to
do with the code. `fmake test NAME...` runs those and no others.

Naming something that is not a test alongside `test` still builds it and
still does not make it a test, which is the case above and the reason both
changes belong together.

### Still open, and deliberately not built

`tests/` cannot separate a unit test from a live driver. hydra keeps them
apart -- 26 of its 66 -- and a directory name cannot say which is which.
`fmake test NAME...` makes the split *expressible* by hand, and a timeout
stops a live driver suspending the suite, so neither remaining cost is
severe.

A real answer means test groups: `@test live` putting a target in a group
that `fmake test` does not run, and `fmake live` running it. That is a
fourth convention in a tool that has just gained three, and
`harmonization.md` is explicit that a change setting a pattern the other
projects should follow is raised rather than made in passing. Raised here,
not built.

## 56. Groups, for tests that differ in what they need

hydra has 66 test programs and 26 of them are live drivers. `tests/` holds
both and is right to: both are tests. What separates them is not what they
check but **what they need** -- a network, a display, a tool that may not be
installed -- and no directory name says that, because it is a fact about the
test rather than about where it lives.

So `@test live` puts a target in a group, `fmake live` runs that group, and
`fmake test` does not. The default group is `test`, which is why everything
written before this still works: a bare `@test`, or a name the conventions
recognised, means the default group.

The mechanism is the one already there. A group name is a word you can ask
for, exactly like a target name, and it resolves after phony rules and after
real targets -- so a project with its own `live` target keeps it. Ejected
Makefiles get a rule per group and `all` depends on none of them; ninja gets
a phony per group.

### One word, and a name

`@test Live Drivers` would have become the group `live`, because the scalar
form takes the first argument and drops the rest. A directive whose whole
purpose is to classify must not classify differently from how it reads, so
more than one word is refused -- the same reasoning as `@pkg_optional`'s
required keyword in section 41, and the same failure it prevents.

The name is checked too, because a group becomes a command-line word and a
Make target and has to be spellable as both. Refusing it early beats
emitting a Makefile that will not parse.

### Two filters, each hiding the other

Between a group name and a test running there are two of them: which
targets get **built**, and which of those get **run**. Removing either one
left every case passing, because the other still did the job.

That is a new shape in this document. The earlier misses were assertions
that matched something they resembled; this is two correct filters where one
would do, and a test suite cannot see the difference from the outside
without asking a question that separates them. Two now do:

- `fmake test` must not **build** the live binary at all -- which only the
  build-side filter can achieve.
- Naming a live test alongside `test` builds it and does not run it --
  which only the run-side filter can achieve.

Writing the first of those exposed a third thing: it passed on a leftover.
An earlier step in the same case had built `fetch_test`, and a rebuild does
not unlink what it does not make, so the file was there for reasons that had
nothing to do with the assertion. Section 38 in miniature, and the reason
every one of these cases now removes what it is about to prove absent.

## 57. hydra's suite, finished

The third hydra trial, and the one that closes the loop opened in section
53. Then, `fmake test` on hydra stopped at 47 of 66 with a live driver still
fetching a website. Now, with `@test live` on the 31 drivers under
`tests/live/`:

- a plain build produces the browser and holds back **69 test programs**,
  naming both groups: *`fmake live` or `fmake test` builds and runs them*;
- `fmake test` builds **38 unit binaries and runs all 38**, and exits.

Nine failed, and the four outcomes are all distinct in the output: five
`exit 1`, one `exit 2`, **two killed by SIGSEGV**, and **one timed out after
60s**. Every distinction in the runner was earned by a real result on this
tree rather than by an argument about what might happen.

The timeout is the one that mattered. `test_live_model` is the test that
suspended the previous run; it is cut off at sixty seconds now, the message
names the key that would raise it, and the suite goes on to the remaining
nineteen.

### What the tree said about the convention

`test_live_model` and `test_helpers_live` are live drivers that are **not**
under `tests/live/`. hydra's own layout does not put all of them in the
directory that names them -- which is the argument for the group being an
annotation rather than a third naming rule, made by the tree rather than by
me. A directory says where a file is. Only the file can say what it needs.

### One thing this trial found in fmake

The failure summary was the only list in the program with no cap. Nine names
already wrap a terminal; a suite where forty fail would print the one line
nobody can read, and the count is the part that matters. It caps at six and
says how many it dropped, like everything else here.

### One thing it found in me

Two checks thirty seconds apart showed the compile count frozen at 125, and
I reached for an explanation -- Python block-buffering a redirected stream --
that fitted, was plausible, and was **not tested**. The reproduction written
to confirm it proved nothing: the build finished inside four tenths of a
second, so the flush at exit hid the question entirely.

A plausible mechanism is not a finding. The rule this document keeps
restating for tests applies to diagnosis too: **a check that could not have
failed has not confirmed anything.**

(The guess at a duller explanation that stood here -- a few slow Qt template
files -- was itself untested, and section 58 is what happened when the
question was pursued properly.)

## 58. The live group, and a claim that would not stay proved

`fmake live` on hydra: **31 drivers built, 31 run, and the command
returned.** Seven failed -- three timed out at sixty seconds, three exited
1, one exited 2 -- and the run ended on its own. Before the deadline existed
this suite could not finish at all: one driver waiting on a website held the
rest indefinitely, which is how the first trial stopped at 47 of 66.

Together with section 57 that is the whole convention demonstrated on the
tree that asked for it. A plain build gives the browser. `fmake test` gives
38 unit binaries and 38 results. `fmake live` gives 31 drivers and 31
results, bounded. Nothing in the tree needed changing except 31 comments.

### The buffering claim, three times

Section 57 recorded a guess about why a redirected log sat still, and
recorded that the guess was untested. Pursuing it properly is worth
recording, because the answer changed direction twice and landed on
nothing.

1. **Evidence that looked conclusive.** The live build's log held **0 bytes
   for fifty seconds** with nine compilers running, then 9820 at once --
   just past Python's 8192-byte block. That reads as block buffering, and it
   was written up as such.
2. **A direct test that contradicted it.** Reading fmake's stdout through a
   pipe, the first line arrived after 0.24 seconds *with the fix removed*.
   Whatever the log was doing, output was not being withheld. The sampling
   in (1) could not tell "produced but buffered" from "not produced yet" --
   fmake scans before it compiles, and a scan prints nothing.
3. **The test that should have decided it decided against the fix.**
   Killing a redirected build after six seconds leaves the same log either
   way: 10 lines, 788 bytes. Whatever justification line-buffering has, it
   is not one this tree can show.

So the change was reverted. Python does block-buffer a redirected stream --
`line_buffering` is False, which was verified -- and no measurement here
finds any behaviour that changes when it is turned off. **A fix that cannot
be shown to fix anything does not ship**, which is the same rule that
removed the two redundant include-resolution fixes and the tri-state in
section 40, applied to a change of my own that I wanted to be right.

What went wrong twice was the same thing: reading a *symptom consistent with*
a mechanism as evidence *of* it. Zero bytes is consistent with buffering and
equally consistent with silence. The distinguishing experiment is never the
one that reproduces the symptom; it is the one that separates the two
explanations, and it is worth finding before writing the paragraph rather
than after.

## 59. hydra's report, folded in

`suggestions/hydra.md` was written from the tree rather than about it, and
every claim in it has now been measured. This section takes its substance
into the record so the report itself is no longer the only place it lives.

Their findings, and what the trials found:

**1. Platform-conditional sources -- called a hard blocker.** Four Android
sources CMake adds only inside `if(ANDROID)`, carrying no self-guard,
failing on `QJniEnvironment`. Their words: *"fmake cannot build hydra's
`src/` today, and no flag fixes it."*

Answered three times, the third because the first two missed. Section 43
made the failure name `@os` as the remedy; section 50 read a `_platform`
suffix so nothing need be written -- and **hydra's own names put the
platform in front**, `android_view.cpp`, so the rule written from their
report did not fire on their tree. It reads a leading word now, and their
four files are excluded unrenamed. And it turned out not to be a blocker at all: the files compile
here, and section 3 leaves them out of the link because nothing reaches
them. What blocked the build was the include-path defect of section 37,
found from a different report entirely.

**2. Optional features vanish silently.** `credential_store.cpp` and
`theme.cpp` guarded by macros CMake defines after `pkg_check_modules`.
Their verdict: *"it builds, and quietly does less than it should -- which is
worse than refusing."*

Sections 40 and 41 answered it, and the trial found the answer incomplete.
There were never two silent features: there are **five**. libtorrent, lz4
and libsodium are guarded the same way, and the first version of the
diagnostic could not see any of them, because it was keyed on a pkg-config
proposal and those packages ship headers in a default include directory.
Keyed on the include instead, all five are reported; five comments turn all
five on.

**3. The binary is named after the directory.** Section 46, from two other
projects reporting the same thing, and now a name nobody chose is qualified
rather than refused.

**And the question they said was open.** Section 17 claimed fmake would make
hydra's static library unnecessary -- compile each translation unit once,
link the closure per program -- and their report said flatly that the claim
was **unverified**, since the build failed before reaching a link.

It is verified now, and it holds. Building the app and 38 unit binaries from
one tree costs **172 compiles**. Recompiling the app sources per binary
would have cost about 2546. `theme.cpp.o` exists once and is linked into
everything that reaches it. The archive is unnecessary.

Their step 3 -- *"point fmake at the tests and compare its closure against
the 28 binaries CMake builds"* -- is done, and the tree has moved since they
counted: 38 unit binaries and 31 live drivers, all 69 built, all 69 run,
both groups bounded.

### What the report was worth

Two of its three findings were real and are now features. The third was
already answered and unfindable, which is section 42's lesson and the reason
three separate diagnostics were rewritten rather than three features built.

The part that mattered most was not a finding at all. It was the sentence
about a browser built without keyring integration and no warning -- *worse
than refusing* -- which is the standard the whole optional-feature diagnosis
was written against, and which found three more instances than the report
knew about.

## 60. The word in front

Section 50 read a platform out of a filename suffix, because that is what
hydra's report asked for: *ignore `*_<platform>.cpp` unless building for
that platform*. hydra's four files are `android_view.cpp`,
`android_downloads.cpp`, `android_intents.cpp`, `android_dialogs.cpp`.

**The rule written from their report did not fire on their tree.** Only
running it on the tree found that, which is the argument for running it on
the tree.

The same words in front now, with one word held back. `ios_utils.cpp` about
C++ iostreams is an ordinary file to write, and a rule whose entire safety
argument is that a word cannot mean anything else does not get to keep a
word that can -- so `ios` stays a suffix. Everything else is unambiguous
leading a filename: `android_`, `win32_`, `windows_`, `darwin_`, `linux_`,
`aarch64_`.

### What it broke, and both were right to break

**A case whose fixture was the convention.** `duplicate_definitions_are_refused`
used `win32_sys.c` and `posix_sys.c` -- two implementations of one symbol,
which fmake refuses to choose between. On Linux the Windows half is now
excluded by its name, one definition is left, and there is nothing to
refuse. The case picks names claiming no platform now, because what it tests
is the refusal.

That is a **capability**, not a casualty: a tree with `win32_sys.c` and
`posix_sys.c` used to need `@os` on one of them and now builds unaided. The
case that exists for the `@os` remedy still passes, so the older answer is
intact for the trees whose names say nothing.

**A case whose fixture was named `android_view.c`.** Section 43's, about a
missing header naming `@os` as an escape. Its file is excluded by name
before it can fail to compile, so the case stopped testing anything --
loudly, which is the only reason it was noticed. Its fixture is
`jni_bridge.c` now: the case is about a header that is not there, and the
filename should not be doing half the work.

### And a summary that read its own wording

The line reporting how many sources were skipped by name decided whether to
print by looking for `"named _"` **inside the message it was about to
print**. Rewording the message one commit later -- `named _android` became
`named for android only` -- silently stopped it printing, and the build
skipped four files without a word.

It records which branch decided, now. A message is for the reader; using it
as a control signal makes every rewording a behaviour change, and this one
was found only because a case asserted the summary rather than the exclusion.

## 61. The other four reports, folded in

Same treatment as section 59, and shorter because most of what these four
found already has a section of its own. What follows is where each finding
landed, so the reports themselves are no longer the only record.

### netcfgd

Declined over one thing, and the thing was there. `@kind static` on the
source that heads the library produces `libncfg_client.a` beside the test
binary, from one comment and no build file -- section 42, and the first of
three findings where fmake was right and the way it said so was not.

Their remaining four are all built: `test-args` for a test that takes the
daemon's frozen protocol witness as an argument (section 49); the object
cache keyed on the whole configuration, which they asked about rather than
reported, now asserted rather than merely true (section 48); the ejected
`clean` naming what it removes; tests out of the default build.

Their addendum was the most useful part of any of the five reports:
**`--eject` is the adoption path for the projects most likely to say no**,
and nothing said so. That became section 45 and a README section.

### beerssh

Six findings, five fixed and one dissolved. The include-path defect that
cost them 84 files is section 37. The `tests` name collision is section 46.
The vendored submodule's four programs are section 39. Tests in the default
build is section 49. The `--explain` column that ran into its own text was
routed through one padding helper.

The dissolved one is their finding 3, *two binaries over one source tree
minus one file cannot be expressed*. It can: `src/main.cpp` and
`tests/main.cpp` build as two programs with no configuration at all, which
section 46 shows. What made it look impossible was findings 1 and 2 -- the
name collision stopped the app being built, and 84 files failed to compile
-- so the shape was never reached. **Two defects can make a third thing look
like a design limit.**

Their fifth, *symbol reachability does not work for a Qt program*, was
right about the symptom and wrong about the cause, and the cause was one
line of Qt API. Section 47.

### fuzzypickles

Four findings, all fixed, and one of them by not doing what they asked.
They proposed ignoring vendored subtrees wholesale; beerssh's report
disproves it in the same paragraph as its own complaint, since both projects
*build a library* out of the subtree they vendor. What is unwanted is the
vendored **decisions**, not the vendored code -- section 39.

Their third suggestion is the one that mattered: an ejected file a
hand-written Makefile can `include`, which they said would make their
verdict obsolete because scope stops being the objection. Section 45.

### apt-emerge

The only report from a project fmake correctly refused -- no C or C++ in
the tree -- and it found more than some that could use it.

The PEP 701 bug is section 44, and the detector they supplied is the case
that caught the same bug again, twice, in this session. Their three
packaging findings are all fixed: products in `../`, `dpkg -i` where
`apt install` is meant, and a version written in two files with nothing
comparing them. `--man` is advertised properly now, which they asked for
after their own hand-written manual drifted the same week.

## 62. What the reports left that is not fixed

Two things, both decisions rather than defects, recorded here because the
files that held them are gone.

**A CI job that installs the package and runs it.** apt-emerge's case is
exact: *"Building proves very little -- a `.deb` with entirely wrong paths
builds perfectly, and so does one that will not start on the Python it
declares."* One job -- `make deb`, install it in a `debian:bookworm`
container, run `fmake --version` and `--help` -- would have caught the bug
that report is mostly about. It would have caught it **again** in this
session, when a multi-line f-string was reintroduced and only a repaired
gate found it.

**Built, one section later.** It was recorded here as not built, on the
grounds that adding the first CI job sets a pattern the sibling projects
would follow, which `harmonization.md` says is raised rather than done in
passing. It was raised, and then done: §63 is that job, and it found
something before it ever ran. What stands is the reasoning about why it was
worth having, which is why the entry is kept rather than deleted.

**A per-target source exclusion.** beerssh asked for a way to say "this
target takes everything except `src/main.cpp`". The shape they needed works
without it now, so this is no longer blocking anything; it would still be
the honest answer for a target whose membership is declared by glob and
needs one file out. Nothing has asked for it twice, which is the usual bar.

## 63. The job that found something before it ran

apt-emerge's argument for CI was exact: *"Building proves very little -- a
`.deb` with entirely wrong paths builds perfectly, and so does one that will
not start on the Python it declares."* One job, on `debian:bookworm`,
because the interpreter that image ships is the one their bug was about.

Writing it found a defect in ninety seconds, which is the argument
restated. **`debian/control` did not declare `python3` as a build
dependency**, and the build needs it: `make deb` generates the manual page
with `./fmake --man`. Nothing local ever noticed, because every machine that
builds this package has python3 installed for other reasons.

The fix earns its place by a test rather than by argument. Without the
declaration `dpkg-checkbuilddeps` **passes**, the build proceeds, and it
fails later at `./fmake --man` -- so a builder resolving dependencies
properly would install too little and be told so at the wrong moment. With
it, the problem is named up front.

Every step of the job was run in a real container before it was written
down: the package builds, `apt-get install ./build/fmake_*_all.deb` works
from a local path, the installed binary runs, the shebang is
`/usr/bin/python3` as Policy 10.4 wants while the repository copy keeps
`/usr/bin/env`, the manual page is where it belongs, the installed fmake
builds a C program, and purging leaves nothing. The YAML asserts what was
observed rather than what ought to happen.

Two things it does not do. It does not run the suite inside the package
build -- `debian/rules` declines that deliberately, since the suite wants a
compiler and several optional libraries -- so a second job runs `make check`
and the style gate on an ordinary runner. And the container is pinned to
bookworm on purpose: moving it to trixie without leaving a job on the
declared floor would delete the only thing this job is for.

### The gate's floor, doing exactly what it says

Adding `.yml` to the gate's `text_suffixes` so the new file is checked at
all, the list was written without leading dots. Every `.md` stopped
matching, the file count fell from nine to five, and the gate refused:
*"this reads as a clean tree but is a collapsed file list."*

That is the one failure mode a style gate cannot afford, and the shared tool
carries a floor because someone had already been bitten by it. It caught a
config edit made while adding a job whose whole purpose is catching things
locally invisible, which is a tidy demonstration of why the floor is not
paranoia.

## 64. The half of the job that had not been run

Section 63 verified the package job in a real bookworm container before
writing it down. The second job -- suite and style gate on an ordinary
runner -- was not verified at all, and a dependency list nobody has run is a
guess with YAML around it. Running it the same way found three things.

**Ubuntu's base image ships no python3**, so `make check` died before the
suite started. On a GitHub runner it would have worked, because that image
preinstalls one -- which is the same implicit dependency that left `python3`
out of `debian/control`, where every local machine had it for other
reasons. It is named now. Relying on what a runner happens to preinstall is
relying on something nobody declared.

**A case called `file` and nothing installs it.** `eject_handles_libraries_too`
verified `libgreet.so` really is a shared object by shelling out to `file`,
which turned a missing utility into an **error** rather than a skip -- the
one case in 231 that could not degrade. `readelf -h` answers the same
question and binutils is already required, since fmake reads symbol tables
with `nm`. No new dependency, and the check still happens.

**The green run was skipping 49 cases, 32 of them Qt.** A job that passes
while silent about moc, uic and rcc is testing the easy half of the tool.
Adding the libraries those cases want takes the run from 182 passed and 49
skipped to **227 and 4**.

### The entry that had to be measured

`gcc-aarch64-linux-gnu` alone makes it worse. The cross cases skip cleanly
when there is no cross compiler; install one without a target libc and ten
skips become **seven failures**, because a cross build needs
`libc6-dev-arm64-cross` to link anything. A dependency list assembled by
reading names would have stopped at the compiler and produced a permanently
red job.

Every entry in that list was chosen by running the suite in a container and
watching what stopped being skipped. That is the same rule the suite holds
its own cases to: **a green run is only worth what it actually exercised**,
and the number of skips is part of the result rather than a footnote to it.

## 65. Two groups, one variable

`@test slow-net` and `@test slow_net` are two groups by every rule this tool
applies, and one Make variable by the rule Make applies: `-` is not legal in
an identifier, so it is replaced, and both become `SLOW_NET_TARGETS`.

The ejected Makefile assigned that variable twice. Both rules then expanded
to whichever group came last, so one group's tests were built by nothing --
and it said so nowhere, which is the part that matters. A Makefile with two
assignments to one name is valid; Make simply takes the second.

It is refused now, naming both spellings and the variable they share. fmake
refuses two targets with one name and two definitions of one symbol, and
this is that shape a third time: **two things a user distinguishes and a
downstream format does not.**

Found by asking what the sanitising in `_mk_ident` could collide, rather
than by anything failing. The sentence that stood here said it would happen
again the moment a name met a narrower alphabet -- and asking the same
question of the *other* caller found it had already happened. Target names
become `{IDENT}_OBJS`, so `my-app` and `my_app` shared `MY_APP_OBJS`, the
ejected file assigned it twice, and one program linked the other's objects.
Older than the groups code, and never noticed.

So one function refuses both, rather than two copies of a check that will
be wanted a third time. The rule generalises and the code should: **any
name rewritten to suit a consumer can collide, and the rewriting is where
to look.**

## 66. The flake, six clean runs later

Section 54 recorded a single failure of `environment_beats_the_config_file`
that never reproduced, and said plainly that the mechanism was not
understood. The container built for CI is a better place to ask: clean,
identical every time, and nothing else running in it.

Six full runs: **227 passed, 4 skipped, six times.** Together with the runs
on this machine that is ten clean full suites since the one failure.

That is not an explanation and is not recorded as one. What it is worth is
a bound: whatever it was, it is rare enough that ten runs do not show it,
and it is not something the clean environment reproduces. The entry stays
open. A flake dismissed because it stopped happening is how section 29 got
written, and the difference between that and this is that this one has a
number attached.

## 67. The audit the last two findings suggested

Sections 65 and 66 were both the same shape -- two names a user
distinguishes and a consumer does not -- and both were found by asking what
a rewriting could collide rather than by anything failing. That question is
worth asking everywhere a name is rewritten, so it was.

Most of the answers were reassuring, which is worth recording as much as
the failure was:

- **uic already refuses it**, and says so well: two `settings.ui` in
  different directories would both produce `ui_settings.h`, an unqualified
  include cannot say which, and fmake names both files and stops.
- **moc and rcc namespace their output by directory**, so
  `.fmake/qrc/a/qrc_res.cpp` and `.fmake/qrc/b/qrc_res.cpp` do not collide
  as files.

### The one that was not reassuring

rcc namespaces the file it writes and **not the symbols inside it**. Both
of those generated files define `qInitResources_res()`, because rcc derives
the symbol from the stem, so a program using both fails to link with a
multiple definition naming paths under the state directory -- and fmake's
summary then offered to name the missing libraries, when nothing was
missing. That is the misleading advice of section 31, and the block
directly above the fix in the source exists for the identical reason with a
comment saying so.

It is reported per program rather than per tree, because two resources with
one stem in two different programs is fine and refusing it would be wrong.

The general form is now three deep: **a name is safe only in the namespace
you can see, and a generator hands names to namespaces you cannot.** rcc's
file names are namespaced by fmake and its symbol names are namespaced by
nobody.

### Two fixtures wrong in one case

Writing the case for it went wrong twice, both times by resembling the
thing rather than being it.

The helper was called `_qrc`, and `selftest` already had a `_qrc` with a
different signature two thousand lines further down, which silently won.
The same collision as the finding, in Python's module scope, while writing
the test for it.

Then the fixture opened only one of the two resources. A `.qrc` is compiled
only when a source opens a path in it -- which is fmake being right -- so
the second was never built, there was no second object, and the case
asserted a collision that could not occur. It opens both now, and the
positive half runs the program to prove both resources are really there.

## 68. beerssh, built

beerssh's verdict was *"Not viable for beerssh today, and (2) is most of the
reason"*, with *"worth re-testing if the include-path rule changes."* It
changed, so it was re-tested -- on their tree rather than on a
reproduction.

Four of their findings are handled with no configuration at all, and the
run says so in four lines: the two Android sources excluded by name, the
vendored `vterm` submodule's four programs left to it, `tests/main.cpp`
qualified to `bs_tests` rather than refused, and the test binary held back
from the default build.

It builds. What it needs is three lines of `fmake.toml`, and both entries
are things fmake cannot know rather than things it gets wrong: a version
string their Makefile computes, and which directory holds the vendored
library's headers.

### The advice that was wrong about a header in the tree

`emulator_vterm.cpp` has `#include <vterm.h>`, and the file is at
`vterm/include/vterm.h` -- inside the tree fmake had just walked. The
failure said the header was on no include path, then offered to install a
package or exclude the file by platform. **Being told to install something
that is already present is worse than being told nothing**, and it is the
misleading-advice failure of section 31 arriving in the message written to
avoid it.

fmake knows every header in the tree, so when the missing one is among them
it now says where, and what would find it. That is exact rather than a
guess, which is why it replaces the two speculative remedies instead of
joining them -- and following it builds the tree.

### What is understood about the cause, and what is not

A dry run offers `-Ivterm/include`, so the directory is discoverable; the
compile that needs it happens first. The including file is reached by
widening rather than through the root's include graph, which is what the
case reproduces deterministically.

**Why the ordering falls that way is not pinned down**, and it is not
claimed here. Resolving `<>` includes against the tree earlier would make
this build with no `include-dirs` line at all, and it would also let a
tree header shadow a system one of the same name, which is a real risk and
not one to take late in a session on a hunch. Section 57 is in this
document because a plausible mechanism was written up as a finding; the
mechanism here stays an open question with a reproduction attached.

### Two fixtures, again

The first fixture put the include in `main.c`, where fmake resolves it --
so it built, and the case had nothing to test. The second omitted any
header that could falsely match, so dropping the separator from the
whole-component rule failed nothing. Both were caught by mutation, both are
the same error, and the count for this session is now high enough that the
rule is worth stating as a habit rather than a lesson: **write the fixture
that fails first, then the fix.**

## 69. One vendored file redefined a standard header

Cloning fuzzypickles and running fmake on it found the worst defect of the
session, and it was invisible on every tree tried before because it needs a
particular thing to be present.

fuzzypickles vendors thorvg, which vendors rapidjson, which ships an
**MSVC-only `stdint.h`** four directories down. It was the only file named
`stdint.h` in the tree, so it won fmake's basename fallback -- the rule that
resolves an include fmake cannot otherwise place when exactly one file in
the tree has that name. Its directory went on the include path for *every*
compile, and **54 files failed** on the `#error` inside it, including moc
output with no connection to thorvg.

A vendored file four levels down redefined a standard header for the whole
build. The failure named a Microsoft compiler on a Linux tree, which is a
long way from the cause.

The basename fallback is worth keeping: it is what finds a vendored
`<vterm.h>`, which is the beerssh case of section 68. What it must never do
is make that guess about a name the toolchain owns, so the C standard
headers are excluded from it by name.

This is the shadowing hazard flagged one section earlier as a reason not to
resolve `<>` includes sooner -- and it was already reachable through the
rule that existed. **A risk identified while declining to add one thing is
worth checking against what is already there**, which is not what happened;
it was found by running the tool on a real tree, and the tree was cloned
rather than copied so nothing local hid it.

### The rest of fuzzypickles

Their four findings are handled with no configuration. Six vendored
submodules keep their 51 programs -- their findings 1 and 4, which had
needed `[project] exclude` and a name in `fmake.toml`. Four directory-name
collisions are qualified rather than refused: `fp_cli`, `fp_daemon`,
`fp_gui`, `fp_tui`, which is their finding 2 and had needed three names in
a config file.

It still does not link. thorvg and quirc are large vendored C++ libraries
whose own sources are not reached, so their symbols are unresolved, and
fmake asks for `--ldflags` because that is what an unresolved symbol usually
means. That is their verdict standing: adoption needs a build file for the
parts that are not compile-and-link. It is a smaller build file than the one
their report described.

## 70. netcfgd's client, and a regression the convention introduced

`client/` is library sources and a test. Running fmake there produced **no
target could be built** -- because holding tests back left nothing, and the
library was never a target at all. Before the tests convention the test
binary was the only target and got built, so nothing noticed.

A tree whose only programs are tests is a library with tests beside it, and
a plain build should produce the library. It does now: `libclient.a` by
default, `fmake test` builds and runs the test, which passes.

Two details the fix needed. Whatever roots the library is taken from the
sources in order, so a test sorting first would root it and put its own
object in the archive -- the case names its test `aa_client_test.c` for
exactly that reason, because the first fixture sorted the test last and the
guard could be removed without failing anything.

This is a regression introduced by section 49 and found by running fmake on
the project whose report was about this shape. It had a case, the case
passed, and the case was about a tree with a program in it. **A convention
changes what an absent thing means, and the trees that have nothing else
are where that shows.**

## 71. A C file as a script

`--run FILE [ARGS...]` builds a C or C++ file and becomes it, and the
mechanism is a shebang: `#!/usr/bin/env -S fmake --run`. `env -S` is needed
because Linux passes everything after the interpreter as a single argument,
so the plain form hands `env` one argument called `fmake --run` and fails.

**`binfmt_misc` was written up here as the better form and it is not one.**
Registering `.c` with the kernel makes every C file on the system
executable, and almost none of them are programs -- a project has hundreds
of translation units and one `main`. The shebang marks the few files that
are meant to be run, which is exactly what a shebang is for, and it marks
them one at a time in the file itself rather than globally in the kernel.

### Three things that had to be got right

**A shebang is not C.** gcc rejects `#!` on line 1 as an invalid
preprocessing directive, and so does g++ -- established by trying it rather
than assumed. So a file carrying one is compiled from a copy, and what
replaces that line matters: a blank keeps the line numbering and loses the
filename; deleting it loses both; `#line 2 "<original>"` keeps both, and an
error in such a script names the file the author wrote and the line they
wrote it on. The case asserts that, and mutation confirms a blank fails it.

**The output goes under the state directory.** The question in the request
was whether it cleans up, and the better answer is that it never dirties:
nothing appears beside the script. The same choice is what makes a second
run a cache hit rather than a rebuild -- 0.19s against a compile -- which is
the property that makes a compiled language usable as a scripting one at
all.

**It execs rather than waits.** The program's exit status is the command's,
its signals are its own, and its stdin and terminal are not filtered through
a parent. A script reading from a pipe works because fmake is no longer
there by the time it runs.

"A collection of them" needed no work: the script is a program like any
other, so the closure reaches the siblings defining what it calls. The
feature is `--run`; the behaviour is section 3.

### What it changed elsewhere

`-q` gated one summary line and left every compile and link line printing,
which is not what a quiet flag means and mattered here: a script's first run
must not narrate a build to a terminal expecting output. It now suppresses
progress, and `--run` sets it unless `-v`. fmake's own output goes to stderr
for a run, so a script's stdout stays the script's even when something is
said.

### The shebang is the mechanism, and there is no other

`binfmt_misc` was written up in the first draft of this section as the
better form. It is not one, and the correction is worth keeping: registering
`.c` with the kernel makes **every C file on the system executable**, and
almost none of them are programs -- a project has hundreds of translation
units and one `main`. A shebang marks the few files meant to be run, in the
file itself, one at a time. That is what a shebang is for.

The alternatives all fail for reasons worth recording so they are not
retried:

- **No compiler flag overlooks the line.** gcc and g++ both reject `#!` as
  an invalid preprocessing directive and neither has an option to skip it.
- **The `//usr/bin/env` comment trick** -- a first line that is both a C++
  comment and a shell command -- depends on the *shell* executing the file,
  not the kernel, so it works only when invoked from a shell that falls
  back to `sh`.
- **Stripping to a pipe** would compile from stdin and lose the per-file
  depfile and object path the cache is keyed on.

So a copy with `#line` it is, and the honest position is that this is a
workaround for something the language does not provide. If C front ends
ever learn to ignore a first line beginning `#!`, as several other
ecosystems' do, the copy becomes unnecessary and the feature gets simpler.
Until then the copy is where the cost is paid, and `#line` is what keeps
the user from paying it in confusing diagnostics.

### A script nobody may write next to

fmake keeps its cache beside the source, which is right for a project and
impossible for a script installed in `/usr/local/bin` or living in a
read-only checkout: the first version refused to run at all. It falls back
to a cache of its own, keyed on the script's path, and builds the file
alone.

The fallback is covered by a case. The *copy* it makes is not, and mutation
says so: with a shebang the copy happens anyway, and with none the escaping
`../..` path to the original happens to compile. It stays because it keeps
the invariant that every source fmake builds is inside the build root, which
nothing else in the tool breaks, and "it worked once" is not a reason to
start. Recorded here rather than defended by a test that does not exist.

## 72. What a test runner owes the machine it runs on

Running hydra's suite, and then its 31 live drivers, left processes behind
on this machine -- and one of them was found six and a half hours later,
still fetching a website. It was orphaned by a `kill -9` sent to the *shell*
that started it: killing a parent does not kill its child, it reparents it
to init.

That is a lesson about running things, and fmake now runs things by design,
so the same question applies to the tool. Two answers, one already right and
one not.

**Right already.** A test gets its own session and the deadline signals the
**group**, so a driver that hangs with a helper alive takes the helper with
it. Mutation confirms it: signalling the process instead of the group leaves
the suite hanging, which is the defect wearing a green run's clothes.

**Not right.** After SIGTERM and then SIGKILL, `_kill_group` returned
without reaping if both waits timed out. A child nobody waits on is a
zombie for the rest of the run, and the loop simply fell out of the bottom
and moved to the next test. It reaps whatever can be reaped now, and says
so when a process genuinely cannot be stopped -- after SIGKILL that means
stuck in the kernel, and a test in that state is worth a line rather than a
silent abandonment.

The path is not reachable by a test written here: a process that ignores
SIGTERM and forks is killed within the grace period, so the case asserts
the reaping that does happen and the branch beyond it is labelled rather
than covered. Same treatment as the guards in sections 40 and 50.

### And the habit

The orphan was mine, not fmake's. The rule that would have prevented it is
the one fmake already follows for tests: **kill the group, not the parent,
and wait for what you killed.** A background job whose child is doing the
work is not stopped by stopping the job.

## 73. situ, and three defects behind one archive

The seventh private project, and the last to run fmake. Its report is in
the history, one commit before §84 folded it in. The trial itself was short
-- one line of configuration builds the library -- and pulling on what it
found took three fixes.

**A generated test file was in the shipped archive.** `libsitu.a` held
`situ.c.o` and `tests/generated/codec_impl.c.o`. The reasoning was visible
and wrong: a tree whose only `main()`s are tests is built as one library,
and the tests convention classifies *programs*. `codec_impl.c` defines no
`main`, so it was not a test; it was a source, and the whole tree is the
library. Test sources are out of a library computed from the tree now.

The guard on that started as "only the whole-tree library", which failed no
mutation, so it went: test material does not belong in any library the
closure assembles, and a library declared with `sources` never reaches that
branch anyway.

**A library was held back as a test, and then run.** Probing what the
mutation had left uncovered meant writing `@kind static` on a file under
`tests/` -- a support library for test binaries, an ordinary thing to have.
It was classified as a test by its directory, kept out of the default build,
and then **executed**: `Permission denied` on the archive, an errno blaming
a file for not being executable when it never claimed to be. Only a program
can be a test now, asked after `fmake.toml` has settled `kind`.

**And the fixture that found it was itself misread.** The archive came out
as `libsupport.a` rather than `libtestsupport.a`, because
`@kind static @target testsupport` was written on one line -- and the parser
hands a scalar directive the rest of the line, so `@target` became an
argument of `@kind` and vanished. Silently. A scalar directive with more
than one word is refused now, which is the rule `@test` and `@pkg_optional`
already had, generalised.

That third one broke an existing case, written the same way months of
habit made natural. Nothing had caught it because nothing had needed the
second directive to take effect.

### The shape of the afternoon

One trial, on a small tree, with one visible symptom. Behind it: a
convention that classified the wrong noun, a role that should never have
applied to a library, and a parser that reads a line more greedily than
anyone writing one expects. None was reachable from the others by reasoning
-- each appeared only because the previous fix made the next thing possible
to write.

## 74. Ten lines that were one answer

Re-running the five projects after section 73 found no regressions -- the
one new-looking failure was checked against the previous commit and was
identical, 48 files either way, which is the sort of thing worth measuring
rather than reasoning about. But fuzzypickles showed something the earlier
runs had not, because they had never got far enough to see it.

thorvg vendors its own include layout, so a missing header failed a group at
a time: ten groups, each naming one directory, each requiring the reader to
note it down and run again. fmake knew all ten when it printed the first.

It offers them together now. Following the combined line takes that tree
from **48 files failing to 11**, in one step rather than three, and the next
line names what the new directories then exposed. Some rounds are inherent
-- a new `-I` reveals includes nothing could see before -- but the round
trip per *directory* was not.

The dedup in that list needed its own fixture. Two headers in two
directories never exercises it; the case has a third header in a directory
already named, because a list that repeats an entry is the obvious failure
and the obvious fixture misses it.

### What the re-run was actually for

Today's strictest change refuses a scalar directive given more than one
word, turning a silent misread into a hard stop. That can only break a tree
that was relying on the misread, so the question was whether any exists:
none of the six private projects contains the pattern. A rule that costs
nothing to enforce is worth enforcing, and the way to know is to look rather
than to argue about likelihood.

## 75. The rule anyone would write

situ needs ten near-identical `[generate.*]` rules, one per schema, because
its schemas live one to a directory: `examples/bmp/bmp.situ`,
`examples/icmp/icmp.situ`, and so on. Asking why one rule could not cover
them found a defect rather than a missing feature.

The rule anyone writes for that shape is

    gen/%.c: schemas/*/%.msg

and fmake accepted it, globbed correctly, and then computed the stem wrong.
The stem is the text between the fixed halves of the prerequisite, taken
**by position** -- so a `*` beside the `%` makes those halves a pattern
rather than literal text, the slice lands in the wrong place, and the stem
came out as `p/bmp`. The failure that followed said
`schemas/*/p/bmp.msg` matched nothing: a path nobody had written, blaming
the input for the tool's arithmetic.

It refuses the form now and says which two things cannot share a
prerequisite. Not silent corruption -- it failed loudly before -- but a
loud failure about the wrong thing costs the same afternoon as a quiet one.

The underlying limitation of `fmake.mk` stands: one `%` per rule, and no
way to say "the stem appears twice in the path". A second wildcard is a
language change in a file whose whole premise is being a small subset of
Make, so it is recorded rather than added.

**But the sentence that stood here -- "that is why situ needs ten rules" --
was wrong, and was written without trying the alternative.** A single
`[generate.*]` in `fmake.toml` takes a glob in `inputs` and a command that
loops, so situ needs *one* rule naming 31 schemas and 62 outputs, not ten.
Seven lines. It reaches exactly where ten rules reached: the
`situ_header_validate` ambiguity, which needs two `[target.*] sources`
sections because three schemas declare a type of the same name.

The defect above is real either way -- `%` beside a `*` computed a stem by
slicing at the wrong offset -- and the fix stands. What was wrong was the
justification attached to it, which reached for a limitation to explain a
number nobody had checked.

### Where it came from

Nothing failed. The trial had already finished, the report was written, and
the question was only *why does this tree need ten of something*. The answer
was a defect in the thing that would have reduced it to one.

**A number that looks larger than it should be is worth one question**, and
the question is not always answered by the feature you expected to be
missing.

## 76. A generator that writes more than it declared

A `[generate.*]` rule names its outputs, and fmake keys the rule's freshness
on them. A generator that writes a file it did not name is invisible: the
re-walk picks the file up and compiles it, so the first build is right.

Then delete that file. The rule's declared outputs are all present, so
nothing re-runs it, and the build fails with an undefined symbol -- and
fmake, seeing an unresolved symbol, offers to name the missing library with
`--ldflags`. The wrong end of the problem entirely, on a tree where the
answer was that a generator had not run.

That is the failure class `build-and-commit.md` names first: a rule that
quietly does not run, producing a stale artifact and a confusing symptom
somewhere else. It is warned about now -- the file is named, and the reason
given is the one that matters, that a missing one will not re-run the rule.

### Two mutations, and why the disk mattered

The first attempt at the case declared the outputs and rebuilt, and the
subtraction of declared outputs could be removed without failing it. The
files already existed from the run before, so nothing was *new* and the
comparison was empty either way. The case removes the directory first now.

The other mutation stands: the check runs only when a generator actually
ran, and no case fails without that condition, because a cached build
creates no files to compare. It is an optimisation -- not walking the tree
on every no-op build -- and is labelled as one rather than defended.

Both were first reported as MISSED during a run where the disk was full,
which produced five unrelated failures at the same time. **A mutation result
from a broken environment is not a result**, and both were re-run once there
was room; one changed its answer.

## 77. The gate that stopped running

`make deb` used to build the package and lint it, because `deb` depended on
`lint` and `lint` did the building. That is backwards as a name -- the
target that says it checks was the one doing the work -- and it was
inverted: `lint: deb`, so `deb` builds and `lint` checks what `deb` built.

The rename is right. What it changed is that **`make deb` no longer lints**,
and the CI job written before the rename runs `make deb`. So the job that
exists to prove the package is sound stopped checking it, silently, fifteen
commits ago. Every run since has been green about something it was not
looking at.

Nothing failed. It was found by running the package job in a container and
noticing that **no lintian line was printed at all** -- neither "clean" nor
"not installed", when the recipe has a branch for each. A missing line is
weaker evidence than a wrong one and easy to read past; what made it
suspicious was that both branches print something, so silence was
impossible.

The workflow runs `make lint` now, verified in a bookworm container to
print `lintian: clean`.

This is the same failure as section 76 one level up: a rule that quietly
does not run. There it was a generator whose output nobody had declared;
here it is a gate whose caller was never updated. **A dependency edge
reversed for a good reason still changes what every caller gets**, and the
callers are not all in the file being edited.

The workflow was one caller. The README was the other, promising that
`make deb` "runs `lintian` if you have it, and passes clean" -- a sentence
that was true when written and false the moment the edge turned round. Both
were found by asking the same question twice, which is the argument for
asking it about every caller rather than the one that broke.

## 78. A completion, and a paragraph that went missing

fmake is packaged, versioned 1.0, with a manual page and a CI job. What it
lacked was a shell completion, which for a tool whose options have grown to
twenty-odd is the difference between remembering `--eject make-fragment` and
looking it up.

`--completion bash` writes one, generated from the parser for the same
reason `--man` is. The edge is sharper here: a stale manual is read by
someone who can see it is old, while **a stale completion offers a flag the
program no longer accepts and omits the one you wanted, and neither is an
error.** It is wrong in the one place a user trusts without checking.

Options carrying a fixed set of values complete to those values -- `--eject`
offers `make make-fragment ninja` -- and everything else falls back to
filenames, which is right for a tool whose arguments are targets,
directories and source files. The package installs it at the standard path,
and the case checks three things: every option `--help` lists appears in the
script, `bash -n` accepts it, and sourcing it really does complete `--eject`.

### The paragraph the restructure lost

Adding this found that the README's `--man` paragraph -- added because
apt-emerge asked for that flag to be advertised more prominently -- **was no
longer there.** It went missing in the restructure of section "the README",
in a block that was cut and reassembled.

The check made at the time was a diff of every code-formatted token before
and after, and it reported nothing dropped. It was satisfied because
`` `fmake --man` `` still appeared elsewhere, in the packaging paragraph. A
token that survives somewhere is not a paragraph that survives, and the
check could not tell the difference.

Both paragraphs now live together under a heading that says what they have
in common. The lesson is the session's oldest one arriving in a new place:
**a check that cannot fail for the reason you care about has not checked
it**, and comparing sets of tokens across a document restructure is exactly
such a check.

---

## 79. A performance check that found nothing

This session added work to every build: test classification, platform-suffix
naming, a tree walk for undeclared generator outputs, ident-collision checks
across targets and test groups, and several header lookups. All of it is
per-build, none of it was measured when it went in, and the accumulation is
exactly the shape that makes a tool slowly get slower without any single
commit being to blame.

Measured on hydra -- 112 sources, Qt, a warm cache -- a no-op rebuild across
three points 35 commits apart:

```
0648010 (35 back)   2374 ms
8c623ef (5 back)    2322 ms
HEAD                2361 ms
```

**Flat.** The 2% spread is noise, and it does not even order consistently
with age. Every addition above is either off the no-op path or too cheap to
see. That is a negative result and it is worth the same amount as a positive
one: the question "did this session make it slower" now has an answer, and
the answer is no.

Worth naming that 2.4s is not fast in absolute terms -- section 26 got a
168-file tree to 0.3s, and hydra is smaller than that and takes eight times
longer, because Qt means moc scanning and a much larger symbol closure. That
is a real gap and this measurement did not attempt to explain it.

### A lead, deliberately left unverified

`cProfile` points at `close_over_symbols`: 2.85s cumulative, of which 2.64s
is 76,010 calls to `builtins.any` -- the shape of a linear scan per symbol
that could be a dict lookup. `object_key` is second, 2.30s over 166 calls.

**That is recorded as a suspicion, not a finding**, because section 26 is
about this precise instrument pointing this precisely at the wrong thing.
`cProfile` charges per-call overhead, so a cheap function called 76,010
times is what it is built to over-report. The memo it justified last time
made no difference at all and was taken out again.

So the lead is written down and nothing has been changed on the strength of
it. Confirming it means short-circuiting the suspected work and timing the
whole program with a stopwatch and enough repetitions to see past the noise
-- the instrument section 26 concluded was the right one. Until that is
done, the honest statement is that nobody knows where the 2.4s goes.

**Confirmed in §114, by that method, and the suspicion was right.** Which
does not make the caution wrong: the reason to distrust it was sound, and
the way it was settled is the reason it can now be believed.

---

## 80. A check that depended on how it was started

Folding section 79 in meant running the suite, and it failed -- one case of
250, `an_ejected_clean_names_what_it_removes`. Nothing in that commit could
reach it: the working tree held a `.gitignore` line and a documentation
section. The case had been passing all session.

It failed because of how it was run. `make` exports `MAKEFLAGS` and
`MAKELEVEL` to every process it starts, so the suite's own `make` is a
*sub*-make of whichever `make` launched the suite. Inheriting `-w` that way
makes it announce the directory before its first recipe:

```
make[1]: Entering directory '/tmp/fmake-an_ejected_...'
rm -f //main.c.o //sub/util.c.o
```

The case asserts `stdout` *starts with* `rm -f`, because the point is that
`clean` names its files rather than sweeping a directory. It got make's
bookkeeping instead.

**So the case passed as `./selftest` and failed as `make check`**, and that
is the worst way for a check to be wrong. It is not a flake -- both results
are perfectly reproducible -- it is a check whose answer depends on how it
was invoked, with no indication that the two invocations differ. Anyone
seeing it fail would reach for the case, the ejected Makefile, or the clean
rule, and all three are correct.

The fix belongs in `_run_in`, not in the case: the suite should not behave
differently for having been started by a build system, and any future case
reading a recipe line would have inherited the same trap. It now strips
`MAKEFLAGS`, `MAKELEVEL` and `MFLAGS` before running anything.

### Guarding it took a second case

The bug's own reproduction is not a regression test, because it only fails
when the suite happens to be run from make -- which is exactly the condition
that let it through in the first place. A guard that requires the harness to
be launched a particular way is the same defect wearing a different hat.

`a_case_reading_make_output_is_not_a_sub_make` therefore sets `MAKEFLAGS`
itself and asserts the scrubbing directly, so it fails whenever `_run_in`
stops stripping, regardless of how the suite was started. Reverting the
scrub was checked against it: it fails, printing make's leaked line.

The near-miss is worth naming. The suite was reported as passing several
times this session on the strength of `./selftest` runs, and one of those
250 was answering a different question than the one `make check` asks.

---

## 81. Reformatting the whole log, and what the proofs caught

The history was written before this tree adopted the commit format in
`build-and-commit.md`, and it showed: of 125 commits, **82 carried no
subsystem prefix at all**, and the 42 that did were not drawn from one set.
`fix:` and `feature:` say what a change *does* rather than where it lands,
and `test:` was serving both fmake's test running and this repository's own
suite, which are different things that a log filter cannot tell apart. All
125 were reformatted in one pass -- prefix, imperative, 75-column subject,
bodies rewrapped to the same width. The vocabulary that settled is in §16
rather than here, because it is a convention rather than a finding.

### The method, and why it is safe

Every commit was recreated with `git commit-tree` over **the same tree
object the original pointed at**. That is the whole safety argument: a
commit object names a tree, and reusing the name means no blob, no subtree
and no mode can have moved, whatever the script did with the message. The
check afterwards is one line per commit -- old tree equals new tree -- and
it came back 124 of 124, with the final tree equal to the one before.

Rewrapping the bodies needed its own proof, since that text really is
rewritten. The tool refuses to write a block whose whitespace-separated
tokens are not exactly the tokens it read, in the same order. Author and
committer identity and dates are carried across verbatim, and every
resulting message was put through this tree's own `tools/hooks/commit-msg`
rather than through a checker invented for the occasion.

### Two defects, and only one of them was caught by the proof aimed at it

**A list can be swallowed without losing a word.** Bodies here often
introduce a list on the line above it, with no blank line between:

```
Not implemented / known limits:
  * One % per rule, and a pattern target needs a pattern prerequisite
```

The rewrapper split blocks on blank lines, so it read that as one
paragraph, and reflowed the bullets into running prose in 17 commits. **The
token check passed on every one of them**, because merging a list into the
paragraph above it moves no word and loses none -- the invariant was chosen
to catch text being changed, and structure is not text. It was found by
reading the output. That is the same lesson as §78 arriving somewhere new:
a check that cannot fail for the reason you care about has not checked it.

**`commit-tree` stores exactly the bytes it is handed**, including the
absence of a trailing newline, and the first pass handed it a message built
by concatenation with none. All 124 rewritten commits ended without one,
where all 125 originals had ended with exactly one. Nothing complained:
`git log` renders both identically, and the message is well-formed either
way. It surfaced only because a *later* pass compared messages byte for
byte and reported 0 of 125 matching -- a check aimed at something else
entirely, failing loudly enough to be worth reading rather than silencing.
Both the normalisation and a census of the three possible shapes are in the
verification now.

### One squash, and the four that were deliberately left

A report was committed under the reviewing tool's name and renamed to the
evaluating project's three minutes later. That is a slip rather than a
change, the rename was pure, and the pair is now one commit.

**The add-then-remove pairs were left alone, and the reason is in their own
messages.** Each commits an evaluation report, folds its findings into this
document, and deletes it in a later commit that says the report *stays in
the history, one commit back*. Squashing those would make that sentence
false and throw away the primary source the pair exists to preserve -- the
document quotes those reports rather than replacing them. `--no-docs-only`
is a judgement in `build-and-commit.md`, not a gate, and this is what
judging it looks like.

**Squashing is allowed; splitting is not.** Stated directly during the pass
that reformatted all 125 messages, and it is why the question above was
only ever which commits to fold together. Reformat messages freely, squash
a genuine slip -- a commit renamed or corrected minutes later, exactly the
case above -- and leave every commit's content boundaries where the author
put them, even where a change looks like two things wearing one hat.

The asymmetry is not arbitrary. Squashing a slip removes something that was
never a decision; splitting invents boundaries after the fact and asserts
an intent nobody recorded, in a history whose whole value is that it says
what was actually done.

### A swap file, removed from four trees

`.project.md.swp` was committed by accident and deleted four commits later,
so it sat in four historical trees and in no working copy. It is a
root-level entry, which is what made it cheap: each affected tree was
listed, that one entry dropped, and the list written back with `mktree`, so
every other blob and subtree object is the original rather than a copy. The
check is the same shape as the one above -- for all 125 commits, the old
listing minus that path equals the new listing -- plus the count of trees
that changed, which had to be 4 and was.

---

## 82. The README is a third copy of the option list

`--man` and `--completion` are generated from the parser, and §16 of the
README explains why: a hand-kept copy of the option list goes stale in the
one place a user trusts without checking. Two cases guard exactly that.

**The README's own Commands table is a third copy, and nothing guarded it.**
It had drifted: `--run`, `--man`, `--completion`, `--doxygen-aliases`, `-V`
and `-h` were all absent. Four of the six are discussed in prose elsewhere
in the file, which is how it went unnoticed -- the flag is *documented*, so
searching finds it, while the table a reader consults as the reference does
not have it. The other two, `-V` and `-h`, appeared nowhere in the file at
all.

**This matters more here than it would in most trees**, because of what the
manual page is. `fmake.1` is generated at build time and git-ignored, so it
does not exist in a checkout -- and `project.md` opens by saying that for
using the tool you read `README.md`. There is no separate manual to be the
reference. The README is it, and a reference missing a quarter of its
subject is a reference that sends the reader to `--help` and teaches them
not to come back.

`the_readme_documents_every_option` closes it, alongside the two cases that
already do this for the generated page and the completion. It reads the
table out of `README.md`, compares it against what argparse advertises, and
refuses to pass when the table cannot be found at all -- the vacuous case
being the one that matters, since a check that silently stops locating its
input reports success exactly as loudly as a real pass. Checked three ways:
dropping a long flag's row, dropping `-h`, and renaming the table's header
so the split misses it, each of which fails the case with the right reason
named.

Section 78 is the same defect from the other side, where a `--man`
paragraph went missing in a README restructure and nothing noticed. The
pattern is worth stating plainly: **the README is documentation of record
in this project, not a summary**, and anything it lists that the program
also knows needs a case holding the two together.

**That rule was stated and then half-applied.** The option table was
guarded here; the *directive* table, twenty lines further up the same file,
was not -- and `@version` went undocumented within a few commits of the
rule being written. §111 guards it. A rule that names a class of list and
then covers one member of the class is a rule that has been agreed with
rather than followed.

---

## 83. The index that stopped at 38

The Contents block covered 34 of 82 sections. It had last been extended
somewhere around §38 and then simply stopped, and it had skipped §35 inside
the range it did cover -- so it was neither complete nor complete-up-to-a-
point, which is the shape that misleads rather than merely omits.

**An index that stops is worse than no index**, because it reads as a
complete list. A reader looking for what fmake did with `netcfgd` finds
nothing under N or under 70, and concludes the document does not cover it
rather than scrolling for §70. The sections were all there; the way in was
not.

Rebuilt from the headings rather than by hand, since hand-maintaining 82
links is the defect being fixed. The grouping and the short link text are
editorial and stayed that way -- a generator cannot decide that §§51 to 76
are the era of building the sibling projects -- but every anchor is
computed from the heading it points at, and the tool refuses to write
unless each section appears exactly once and every anchor resolves. The
slug rule was calibrated against the 34 anchors already in the file, all of
which it reproduces, which is what makes it trustworthy for the other 48.

`the_contents_index_lists_every_section` guards both halves. The one that
rots quietly is the second: a heading reworded without its anchor updated
leaves a link that looks right and goes nowhere, and nothing short of
clicking it would say so. Checked by mutation three ways -- add a section
and do not index it, reword a heading, and truncate the index back to §38
the way it actually was -- each failing with the right sections named.

This is §82's rule applied to this document instead of the README: **a
hand-kept list of what something contains needs a case holding the two
together.** There are now four such lists -- the manual page, the shell
completion, the README's option table and this index -- and all four are
guarded.

---

## 84. situ's report, folded in

The seventh evaluation, and the last. Its three defects are §73 and its
generator findings are §§75 and 76; what is left is the verdict, what the
trial got right, and two observations about the report itself that are
worth more than either.

### The verdict, and why it is not about fmake

**Not a switch today, for a reason about situ rather than about fmake.**
The C here is one library and eleven test binaries, which is perhaps a
fifth of what situ's `Makefile` does; the rest is Python packaging, `mypy`
runs, the schema compiler's own test suite, a version-consistency gate and
the `.deb`. fmake would own the small part well and leave the Makefile in
place for the rest, which is two build systems where there is one.

That is the same objection fuzzypickles raised in §45 and it has the same
answer available -- `--eject make-fragment`, which §45 built for exactly
this. Worth stating plainly that **the fragment was not offered here**: the
trial predates nothing, the option existed, and the report reached its
verdict without it. Whether it changes the answer for situ is untested, and
guessing would repeat the mistake the report itself records below.

**What would change the answer is not a feature.** If the C side grows --
more runtime translation units, more codecs, per-platform variants -- the
compile-and-link layer becomes worth delegating and the verdict flips with
fmake unchanged. That is the honest shape of a "no" and it is worth
distinguishing from the kind that names a missing capability.

### The boundary, named exactly

`test_kernels` does not link, wanting `situ_base16_encode` and its
neighbours: declared in a generated `kernels.h`, defined by no
schema-to-C step the trial found. That is situ's own build knowledge --
which generator or which hand-written file supplies the codec kernels --
and it is the boundary rather than a defect. **A tree that is only complete
after another program has run is annotated by definition**, which is what
`[generate.*]` exists to say and what nothing can infer.

### What it got right

- **The include-path diagnosis**, which is §68's message doing the whole
  job: it named the missing header, said the tree already contained it,
  said where, and printed the line to paste. A dead end became a one-line
  fix with no search.
- **Tests out of the default build**, which is what this family's
  conventions require and what situ's `Makefile` does by hand.
- **`--eject` produced 168 lines** that build the same thing with no fmake
  present. For a project whose own pitch is that generated sources are
  committed so its users need no `situc`, that is the same bargain in the
  same words -- which is the most useful thing an evaluation can find,
  because it is an argument the reader already accepts.

### Two things about the report rather than the tool

**The first evaluation where the diagnostics did more work than the
inference.** The inference was never in question: two objects, one archive,
eleven test programs, all correct with nothing configured. Every step after
that was fmake naming what it needed and the report pasting it back -- the
include directory, the two ambiguous source lists, and one at a time, which
schema was missing next. Six evaluations found things fmake could not do;
this one mostly found things it said clearly, and that is a different kind
of result.

**And the first to catch itself.** The paragraph recommending `[generate.*]`
called it "a handful of lines", written before anything was tried; trying it
said sixty. The report says so about itself rather than quietly correcting
the number. That is the same rule §14 is built on, arriving from outside:
**a report that guesses at the cost of the work it recommends is worth less
than one that stops and measures**, and this one nearly shipped the guess.
It is also why §75 exists -- asking why the number was ten found the defect
behind it.

### Removed, and where it went

The file is deleted for the reason the other six were: a report is a
snapshot of one run against a tree that has since changed, and this one is
already wrong in one place -- it records the archive defect as open in the
body and fixed in the verdict, because it was fixed while being written.
Leaving it beside a corrected account invites reading the stale one. It
stays in the history, one commit back.

---

## 85. Leaving with the install as well

`--eject` is the promise in principle 5 made good: a tool this opinionated
has to be leaveable, so it writes a build file that owes fmake nothing. It
wrote one that could build the tree and not put it anywhere. Every project
that left had to hand-write the one rule that turns a built tree into an
installed one, which is the step a packager cares about most and the step
fmake already knew the whole answer to.

`suggestions/packaging.md` named it exactly, under a heading that is its
own argument: **the real gap is that an ejected Makefile has no `install`
target**. That evaluation was otherwise a "no" -- packaging metadata is not
in the tree, `dpkg-shlibdeps` has better evidence than fmake does, and
`debian/rules` is three lines -- and it was right about all of it. This was
the one thing it asked for.

### One plan, two callers

The obvious implementation is a second walk over the targets, emitting
`install` lines. That is the version that rots. `--install` and the ejected
rule would each carry their own idea of what a project publishes, and the
day they diverged nothing would look wrong: the ejected build still builds,
still installs, still succeeds. The difference surfaces much later as a
package missing a header, in a project that has by then stopped using
fmake and cannot be told.

So `install_plan` is one function and both callers read it. It answers
which files go to which of the three directories, with what mode,
deduplicated on where each lands. **What it deliberately does not answer is
the path**, because that is the one thing the two callers must disagree
about: fmake resolves `bindir` against the prefix and `DESTDIR`, while the
Makefile leaves `$(DESTDIR)$(BINDIR)` standing, since a build file with its
install paths baked in is not one a distribution can package.

The variables follow `CC` and `AR` rather than the `FM_` rule: `PREFIX`,
`BINDIR`, `LIBDIR`, `INCLUDEDIR` and `DESTDIR` are unprefixed and `?=` in
both forms, including the fragment, because they are exactly the knobs a
parent Makefile or a packaging run *should* own. Whatever `[install]` says
becomes the default they start from, so a tree that configured its layout
keeps it after ejecting. An absolute `libdir` stays absolute rather than
being glued under `$(PREFIX)`, which is the same rule `install_paths`
applies and the reason it is read from one place.

### What the case checks, and what it refuses to check

`an_ejected_build_installs_what_fmake_installs` does not check that an
install rule exists. It installs the tree both ways into two staging roots
and compares **the set of paths and their modes**, having deleted `.fmake/`
first so the ejected build genuinely rebuilds rather than installing what
fmake left behind.

Two guards against the comparison being vacuous, which is the failure mode
of every equality check: it refuses to pass if fmake installed nothing, and
it requires all three kinds -- a program, an archive and a header -- to be
present, since two empty halves agree perfectly. Checked by mutation three
ways: dropping headers from the emitted rule, emitting the wrong mode, and
removing the rule's dependency on the build.

Byte equality is deliberately *not* checked. The two builds compile into
different object directories and `ar` is not deterministic without `D`, so
the artifacts differ in bytes while defining the same symbols -- which is
the standard §24 already set for the ejected build, and this case installs
under it rather than inventing a stricter one it would have to weaken later.

### What is still open

`--eject ninja` emits no install rule. Ninja has no convention for one --
no phony `install`, no `DESTDIR` -- and every project that wants it wraps
ninja in something else. **That reasoning was wrong and §89 has it**: ninja
passes the environment through to a command, which is all a `DESTDIR` needs,
and the rule exists now.

Uninstall, a manifest, generated `.pc` files and the shared-library symlink
chain are all still missing from both callers, and they are one item in §15
rather than four: `--install` is minimal, and the ejected rule is now
exactly as minimal, which is the right relationship between them.

---

## 86. `-g` was in the default and should not have been

The default compile flags were `-Os -g`. Half of that is the shared build
convention and right: size is the property these projects care about, and
it is the instruction cache that is scarce rather than the arithmetic. The
other half was never argued for. **`-g` is paid by everybody** -- a fatter
object, a fatter binary, a slower link, on every build anyone ever runs --
**to serve the run in a hundred that is under a debugger**, and nothing in
the tool or the documentation had ever said why it was there.

It is now `-Os`, with `$DEBUG` asking for the other build.

### A debug build is a different build, not a release with symbols

`DEBUG` gives `-Og -g`, and the `-Os` goes away with it. That is not a
flourish: `build-and-commit.md` says `-Og` is the right answer while
debugging and that `-Os` gets in the way, which is the same reason `-g`
should not have been in the default. Adding symbols to a size-optimised
build produces the artifact nobody wanted -- big, and still stepping
through code the optimiser rearranged.

`DEBUG=0` is off. Make's `ifdef` would call it set, which is a real
convention and a well-known footgun, and this is a variable a person types
on a command line rather than one a Makefile computes; **the reading that
matters is the one the person typing it has**. Empty is off for the same
reason. Any other value is on.

### Measured rather than deferred to

`-Og` is what `build-and-commit.md` prescribes, which is a reason to use it
and not evidence that it works. On this machine, gcc 14.2, one deliberately
small C function with a loop and three locals:

| flags | line-table rows | entities with `DW_AT_location` | object |
|---|---|---|---|
| `-O0 -g` | 16 | 6 | 4264 |
| `-Og -g` | 27 | 8 | 4976 |
| `-Os -g` | 7 | 2 | 4328 |
| `-O2 -g` | 7 | 2 | 4344 |

The column that answers the question is the middle one, because a variable
with no location is the one a debugger prints as `<optimized out>`. **`-Os`
keeps a quarter of what `-Og` does**, which is the concrete cost of
debugging a size build and the reason a debug build has to stop being one.

The line-row column is the one not to read too quickly: `-Og` has *more*
rows than `-O0`, and more rows is not automatically better -- it can mean
one source line maps to several scattered instruction ranges, which is what
makes stepping jump about. It is offered as a measurement, not as a second
argument, and the program is seven lines, so the numbers show the shape
rather than what a real tree would give.

Two things this did not establish, named rather than assumed. `-O0` was not
chosen despite tying on the column that matters, on the strength of the
convention rather than of anything measured here; it remains available as
`--cflags -O0` or a `[profile.debug]`. ~~And **clang is not installed on
this machine**, so the fact that it treats `-Og` as roughly `-O1` is
untested here rather than confirmed.~~

Clang is installed, at `/usr/lib/llvm-19/bin/clang` -- the same wrong
reason §112 found, reached independently in a second section, which is
what a false premise does once it is written down. Measured on a
non-degenerate function, `-Og` and `-O1` are not roughly the same on
clang, they are **byte-identical objects**:

```
clang    -Og.o and -O1.o  same md5; -O0, -Os, -O2 all differ
gcc      all five differ, -Og included
```

So `DEBUG=1` buys a real debug level on gcc and exactly `-O1` on clang.
That is clang's documented behaviour and not a defect, but it means the
band's value depends on the compiler, which the table above does not say
and now does.

### The cache is the half worth guarding

Debug and non-debug objects must never be interchangeable. Handing a `-Os`
object to a build that asked for `-Og -g` is the stale-object failure §48
is about, arriving through a variable nothing else in the tree mentions --
and it would look like a debugger that cannot find line numbers rather than
like a build bug.

It works already, and by construction rather than by luck: §76 keys the
object cache on the whole configuration including the compile flags, so two
sets of flags are two object directories without anything being added here.
The case asserts it anyway, because "it falls out of the design" is exactly
the claim §14 exists to distrust.

### The suite was reading the environment it was launched from

`t.fmake()` scrubbed `CFLAGS` and `LDFLAGS` and now scrubs `DEBUG` too.
Without it a suite run by someone with `DEBUG` exported would build every
case differently from one run without, and no case would say so -- which is
§80 exactly, a check whose answer depends on how it was started. Found
while writing the case rather than by it, which is the cheaper of the two
ways.

---

## 87. `SANITIZE`, and a variable that means two things

`$SANITIZE` adds `-fsanitize=address,undefined -fno-omit-frame-pointer`.
The name, the flag list and the independence from `DEBUG` are all taken
from fuzzypickles rather than invented: it has them in six Makefiles, with
the reasoning written down, and **the point of harmonizing is that a habit
learned in one project is correct in the next**.

Their note on the name is worth keeping: there is no agreed variable for
this across the C ecosystem, and `SANITIZE` was chosen to name what it
does. Their note on independence is worth keeping too -- `SANITIZE=1` alone
sanitizes a *release* build, which is the build being shipped, so tying it
to `DEBUG` would remove the case most worth having.

### The link is the half that matters

A sanitizer is a runtime as well as an instrumentation. Compiling with it
and linking without leaves every `__asan_report_*` undefined, which is
exactly what netcfgd reported in §76 -- forty lines of link errors that
mention no flag anyone set. So the flags go to `cflags` and `ldflags` both,
and the case does not check that a flag was passed: it builds a program
that writes past the end of a heap allocation and requires the sanitized
binary to say so and the plain one not to. That is the only evidence the
whole chain works.

`--cflags` cannot drop it, because replacing the defaults is what that flag
is for and this is not a default. A file's own `@cflags` still can, which
is deliberate: a `-fno-sanitize=` written beside the code is somebody
saying they know about that file.

### What fmake gets for free that the Makefiles warn about

fuzzypickles' `common/Makefile` carries this, and it is the honest kind of
documentation:

> In the default in-place layout, object files are not segregated by these
> flags -- run `make clean` when changing DEBUG/SANITIZE, or build into a
> per-flavour BUILD_DIR [...] or you'll silently relink against whichever
> flavour's `.o` happens to be lying around.

**That failure cannot happen here**, and not because anything was added for
it: §76 keys the object cache on the whole configuration including the
compile flags, so each flavour lands in its own directory and switching is
a rebuild rather than a hazard. It is the clearest example so far of the
model paying for itself somewhere nobody designed it to -- the same
property that makes a cross build and a profile safe to interleave.

### A deliberate divergence, recorded because it is one

The sibling Makefiles use Make's `ifdef`, so `DEBUG=0` **enables** the
debug build. Their comment says why they cannot avoid it: `ifdef` cannot
distinguish `0` from on, which is also why those variables are never given
a `?=` default anywhere in that tree.

fmake reads `0` and empty as off. Nothing here forces the `ifdef`
behaviour, and the reading that matters for a variable a person types on a
command line is the one that person has. **This was raised rather than
decided in passing**, and the answer was to keep it -- so the divergence is
known, is one row of a table, and is written here rather than discovered by
someone whose `DEBUG=0` did the opposite of what they meant.

| | `DEBUG=1` | `DEBUG=0` | `DEBUG=` | unset |
|---|---|---|---|---|
| fmake | on | **off** | off | off |
| the sibling Makefiles | on | **on** | off | off |

---

## 88. The switches had to survive the exit too

`--eject` baked `DEBUG` and `SANITIZE` into the flags it wrote. So a
project could adopt fmake, gain both switches, eject -- and get a Makefile
that answers `make DEBUG=1` by building a release and saying nothing.

That is worse than never having offered the switch. It is also a
*regression against what the project left behind*, since the hand-written
Makefiles being replaced all carry these -- fuzzypickles in six files. The
exit is supposed to hand back everything fmake worked out; here it handed
back less than the thing it displaced, and silently, which is the shape
§85 had just fixed for install.

### Why this is not the snapshot limit

§15 says ejected builds are a snapshot rather than a translation, and that
adding a source file means ejecting again. That is right and it does not
cover this. **These two change no part of the plan** -- not which files are
compiled, not the link sets, not the libraries, not a single rule -- they
change flags, and Make switches flags without re-deriving anything. The
snapshot argument applies to what fmake computed; it does not apply to a
knob that was never computed.

The evidence is that the emitted file is now *identical* whether or not
`SANITIZE` was set when it ran. Before, ejecting while sanitizing wrote a
Makefile that was permanently sanitized with nothing saying so, which is
the same silent-wrongness from the other direction.

### `filter-out`, not `ifdef`

The idiom everyone reaches for is `ifdef DEBUG`, and it is wrong here for
the reason §87 records: `ifdef` calls `DEBUG=0` set, so the emitted file
would contradict the tool that emitted it. One row of that table would
differ depending on whether you ran fmake or the Makefile fmake wrote,
which is the worst possible place for a divergence.

    ifeq ($(filter-out 0,$(DEBUG)),)

is empty for unset, for empty and for exactly `0`, and non-empty for
anything else -- fmake's rule exactly, in one line, with no nested
conditionals. The sibling Makefiles cannot use it because they never gave
those variables a `?=` default and rely on `ifdef` for that reason; nothing
here has that constraint.

`:=` rather than `=` on the assignments that prepend, because a recursive
variable referring to itself is an error Make reports rather than a loop it
runs -- found by writing it the obvious way first and having Make refuse.

### What is still baked

`--cflags` still bakes. Somebody who forced the flags gets them frozen,
which is what forcing them means, and the `DEBUG` block is simply not
emitted in that case -- there is no default left for it to switch between.

`--eject ninja` bakes both, because ninja has no conditionals -- and unlike
the install rule, which §89 found a way to do after all, there is no
environment trick here: these change the compile line of every object, and
a ninja file's whole premise is that those are already decided. The honest
place for that switch is the generator.

---

## 89. The flags that have to be on both lines

`--coverage` in `[project] cflags` did not link:

```
undefined reference to `__gcov_exit'
```

and that is the *lucky* case, because it says something. `-pg` linked, ran,
and wrote no `gmon.out` at all -- a profiler that silently does nothing.
`-fopenmp` would go the same way the moment a pragma appeared. `-flto`
survives only because GCC's fat objects let the linker plugin cope.

**A whole family of flags is an instrumentation and a runtime**, and the
compiler links the runtime half only if it sees the flag again at link
time. fmake put the project's compile flags on the compile line only.

### Why the special case was the wrong shape

The sanitizers were already handled -- §87 added them to `ldflags`
explicitly, after netcfgd hit exactly this in §76. That fix was right about
the symptom and wrong about the class. Adding `-fsanitize` by name, then
`--coverage` by name, then `-pg` by name, builds a fourth of the
hand-written lists §15 already warns about three of, and each entry arrives
only after somebody has been bitten.

The sibling Makefiles answer it in one line, `LDFLAGS ?= $(CFLAGS)`, and
that answer needs no list. `link_flags()` is that: the project-wide compile
flags, plus the link-only ones. The sanitizer special case is gone, because
it is now an instance rather than an exception.

**The asymmetry is the whole argument.** `-I`, `-std=` and `-Wall` on a
link line are accepted and do nothing; passing too much costs a longer
command. Passing too little costs a binary that is wrong in a way nothing
reports. Those are not comparable, so the default should not be the one
that fails quietly.

Per-file `@cflags` stay off the link line, and that is not an oversight:
they belong to one translation unit, which is §4's asymmetry and the reason
`@ldflags` exists as a separate directive. The case checks both halves,
because a fix that put *everything* on the link line would pass a test that
only checked the first.

### `--coverage` rather than `-pg` in the case

`-pg` is the more interesting failure and the worse test: it *passes*
before the fix, because the link succeeds. Only running the binary and
finding no `gmon.out` shows anything, and a case that has to notice an
absent file is a case that can quietly stop noticing. `--coverage` fails
the link outright, so the case fails for the reason it is about.

### Ninja got the install rule after all

§85 recorded that `--eject ninja` would not get one, on the grounds that
ninja has no `install` convention and no way to set a variable on the
command line. The first half is true and the second was the wrong thing to
look at. **Ninja passes the environment through to a command**, so the
recipe reads `PREFIX`, `BINDIR`, `LIBDIR`, `INCLUDEDIR` and `DESTDIR` from
there with the same defaults, and

    DESTDIR=$PWD/stage PREFIX=/usr ninja install

means what the Makefile means by the same words. `${VAR:=default}` supplies
the default only when the caller left it unset.

So there are three callers of `install_plan` now and they are checked
against each other rather than against a description. The ninja case is its
own rather than a second half of the Makefile one, so a machine without
ninja skips it and still checks the Makefile -- the first version returned
early instead, which is a silent reduction in coverage wearing a pass.

---

## 90. Two directives that were read and then discarded quietly

A sweep for the failure class §89 closed -- something accepted, doing
nothing, saying nothing -- found no more of that kind. What it did turn up
was two directives that are handled correctly and reported badly, which is
a different failure and a cheaper one to fix.

Worth stating what the sweep covered, since a sweep is not a proof: twelve
shapes across the directive surface, the config surface and eject fidelity.
Four things suspected and cleared -- `--explain` does still list the
directives it recognised, which is the only mitigation §15 claims for a
typo; per-file `@ldflags` reach both ejected backends, the Makefile on the
link line and ninja in the per-edge `libs`; per-file `@cflags` stay
per-file after ejection; `$CFLAGS` reaches the link. The cross-compile
paths, the Qt generators and the cache-invalidation edges were not swept
and could hold one.

### An exclusion that empties the tree

`@os windwos` produced:

```
!!! every source file is excluded when building for linux/x86_64
```

True, and it sends the reader to `[toolchain]` and to the machine they are
on -- everywhere except the spelling, which is the one thing that can be
wrong. **This is §31's pattern arriving inside the message written to avoid
it**, and it is the third time that has happened, after §68's header and
§72's include directory.

The fix is the same one both times: fmake had already recorded the reason
per file while excluding it, so it prints what it knows.

```
!!! every source file is excluded when building for linux/x86_64
    lib.c: @arch riscv (building for x86_64)
    prog.c: @os windwos (building for linux)
```

Exact rather than a guess, which is what lets it replace the bare sentence
rather than joining it. Capped at the same width the linker output is,
because a tree excluded by a bad `[project] exclude` glob can be every file
in it.

### `@headers` next to a program

Gathering `@headers` for libraries only is right and stays -- §7 argues it,
and a program does not publish an API. But being right is not being
understood. Somebody who writes `@headers api.h` beside a program's source
runs `--install`, is told it installed one file, and gets no header and no
word: the directive was read, understood, and dropped in silence, which is
indistinguishable from a typo that did nothing.

It is reported now, with both remedies named -- move it to the library's
source, or say `[target.NAME] headers` to publish it anyway.

**The negative case is what decides whether this is a diagnostic or a
nuisance**, and it is the half worth the effort. The file carrying the
directive is *usually* linked into one of the tree's programs as well, so
the test cannot be "this source reaches a program". It is "this header is
published by nothing", computed against the plan §85 already builds -- so
the normal shape of a library, a consumer and one header stays silent, and
the case asserts that as hard as it asserts the report.

---

## 91. Sweeping the two paths that had not been swept

§90 named cross-compilation and Qt as unswept. Qt came back clean. Cross
came back with the worst-shaped defect this tree has produced.

### The C++ compiler that was not derived

`aarch64-linux-gnu-gcc` already implied the matching `nm` and `ar`, and the
rule was written in a comment right beside them: *naming the compiler
should be enough*. **The C++ compiler was chosen one line above the prefix
that would have derived it**, so it never did, and no `[toolchain] cxx`
meant the host `c++`.

What that produced is the shape a build tool should never have:

```
$ cat fmake.toml
[toolchain]
os = "linux"
arch = "aarch64"
cc = "aarch64-linux-gnu-gcc"

$ fmake
[1/1] CXX prog.cpp
LD  prog
* built prog
$ file prog
prog: ELF 64-bit LSB pie executable, x86-64
```

Compiled with the host compiler, linked with the host compiler, an x86-64
binary for a tree declaring aarch64, and `built prog` as the only output.
Nothing was wrong anywhere a person would look, and `aarch64-linux-gnu-g++`
was installed the whole time.

It is derived now, from the same prefix as `nm` and `ar`, tried as `g++`
then `c++`.

### Closing the class rather than the instance

Deriving it fixes that case and no other. The next one is a compiler named
by hand, an `arch` that disagrees with the `cc`, or a `$CXX` left in a
shell -- none of which a derivation reaches, all of which produce an
artifact for the wrong machine and report success.

So the objects are checked. The evidence is the ELF header, exactly what
§23 already reads off a vendored archive: precise for any architecture and
needing no knowledge of triplets. Once per architecture per run, so the
cost is one twenty-byte read.

```
!!! prog.cpp compiled for x86_64/64le, but this tree is being built for
    linux/aarch64
    the compiler used was 'c++'
    name the right one with [toolchain] cxx, or $CXX
```

**It is silent whenever it cannot be certain** -- an architecture missing
from `ELF_MACHINES`, a non-ELF object, an unreadable file. A guard that
guesses is worse than no guard, and the case asserts the quiet direction as
hard as the loud one.

### The guard's first act was to break a better message

`cross_rejects_an_unrunnable_generator` failed immediately. That case
mis-declares `[build-toolchain]` on purpose, so the generator's objects
*are* foreign -- deliberately, because a generator is built for the machine
doing the building. The guard fired on them and replaced a message that
says `cannot run here` and names `[build-toolchain]` with one that says the
target architecture disagrees.

Both statements were true and the older one is far more useful. `Config`
now knows whether it is the build-machine toolchain, and the guard steps
aside when it is. **Worth recording as the general point**: a check added
to catch silence can take the place of a better diagnostic, and the suite
is what noticed within a minute.

### What Qt came back with

Nothing, and the checks are worth naming so the next sweep can skip them.
The ejected Makefile and the ejected ninja both carry the moc rules and
produce a working binary. A header that *gains* `Q_OBJECT` after a build is
re-moc'd, because headers are hash-cached. The `#include "moc_x.cpp"` idiom
builds without compiling the output twice. A cross build uses the host's
moc, which is correct -- moc is a build-machine tool and the target's could
not run.

One false alarm, and it was mine: a `Q_OBJECT` class in a `.cpp` with no
`#include "app.moc"` appeared undiagnosed, contradicting §17. It is
diagnosed, on the first line of the output, and the probe had truncated to
the last four.

What the false alarm did turn up is real, and it is §31's shape again. The
warning is printed, then ten lines of linker noise, and then a summary
offering `--ldflags` -- **advice about a missing library, for a meta-object
this tree was supposed to generate**. The first line diagnoses it and the
last line, which is the one a reader acts on, contradicts that. Fixed:

```
* app did not link
  no x86_64/64le library exports: _ZTV5Local
  app.cpp declares a Q_OBJECT class and does not #include "app.moc", so its
  meta-object was never generated
  add the missing #include of the .moc file above; if that is not it, name
  the missing libraries with --ldflags
```

**Matched on the link set, not on the symbol.** Tying `_ZTV5Local` back to
a class means demangling, and the connection is exact without it: this
program links a source that declares a `Q_OBJECT` class whose moc output
was never generated. That is a fact fmake already had and was throwing
away between the warning and the failure.

The negative direction is what keeps it a diagnosis rather than a guess,
and the case asserts it: an ordinary unresolved symbol in a C program with
no Qt anywhere still gets the ordinary advice, and a mutation that blames
every file in the link set fails on exactly that.

---

## 92. Auditing every remedy the tool offers

§91 ended by naming the shape rather than just the instance: §31's failure
-- advice that points the wrong way -- kept arriving in *summaries*. The
code that knows the answer runs early, the code that prints the last line
does not ask it, and the reader acts on the last line.

So the remedies were enumerated rather than waited for. Twenty-five
messages in the tool offer one: a flag, a config key, a directive. Most are
exact, naming the file, the line and the key. Two were not.

### One situation, two messages, only one of them warned

```
!!! fmake.toml: [target.app] sources 'net_win32.c' matched no source file
    (excluded ones do not count)
!!! main.c: @sources 'net_win32.c' matched no source file
```

The same situation and the same file, and the second reads as a typo --
which sends somebody looking for a misspelling in a name that is spelled
correctly and sitting in the directory. **The glob already knew**: what the
pattern matched on disk, and what survived the platform rules, are two
lists it computes one after the other and then throws the first away.

It says which file matched and did not make it. Better than the sibling's
parenthetical, which is a general warning where this is a specific fact, so
the note now names the file rather than hinting at a category.

The half worth the work is the negative one. A pattern matching nothing at
all must stay a plain "matched no source file", or the fix trades one
misreading for another -- and the case asserts that as hard as the rest.

### `--run` answered a question nobody asked

```
$ fmake --run nomain.c
!!! no target 'nomain'. Available: adv
```

The reader asked to run one file. They were told about targets, given a
list containing something else entirely, and never told the thing fmake
knew: the file defines no `main()`, so it is not a program. `--run` names
its target after the file, so a file that is not a program arrives at
target selection as a name nobody declared, and the general message for
that case is the wrong conversation.

**This is the front end a newcomer meets first** -- the shebang, the C file
as a script -- which makes it the worst place in the tool to answer a
question with a list.

```
!!! --run: nomain.c defines no main() at file scope, so there is nothing
    to run.
    A file used as a script has to be a program.
```

### What the audit says about the shape

Three of the four instances found this session were in code that prints a
*conclusion*: the link failure's closing advice, the exclusion summary, and
this. The pattern is not that fmake lacks the fact -- it had it every time,
computed a few hundred lines earlier and dropped on the way to the
sentence. Worth remembering when adding a message: **the question is not
"what do I know here", it is "what did something already know".**

---

## 93. Uninstall, and the manifest that was not written

`--install` had no inverse, and neither did the two build files it emits.
That is half a promise in the same shape §85 fixed: everything needed to
put a project in place, and nothing to take it out again.

`fmake --uninstall`, `make uninstall` and `ninja uninstall` all exist now,
and all four callers -- those three plus `--install` -- read `install_plan`.
A fourth caller rather than a fifth idea of what this project publishes.

### Named files, because that is what `clean` does

The obvious implementation removes the install directories, or globs them.
Both are the thing this tree refuses everywhere else: **a target everybody
runs without reading must not be able to remove something it did not put
there.** `clean` names its files one by one for that reason and says so in
a comment longer than the rule; uninstall is the same rule with higher
stakes, because it operates on a prefix somebody else's software lives in.

So it removes exactly the paths the plan names, and the case checks the
property that distinguishes the two implementations rather than the one
they share: a neighbour's file dropped into `bin` **survives**, and the
directories survive. "The staging tree is empty afterwards" would pass for
a version that removed the prefix, which is precisely the version being
avoided.

`rm -f` in the emitted rules and a swallowed `FileNotFoundError` in fmake:
uninstalling twice, or after a partial install, is an ordinary thing to do
and the end state is the one asked for either way. It reports how many were
already gone rather than staying silent about it.

### The manifest, declined for now and not quietly

There is a real limit, and stating it is better than discovering it. This
removes **what the tree says today**. Rename a target, uninstall, and the
old name stays behind, because nothing in the tree names it any more.

A manifest -- a file recording what a previous run actually placed -- fixes
that, and it is a much larger promise than it looks: it has to live
somewhere, survive the source tree moving, be found again from a different
checkout, and be trusted when it disagrees with the plan. §15 lists it
separately from uninstall, and it stays listed. What is built here is the
thing that needs no new state and cannot be wrong about the present.

### `--uninstall -n` reaches the plan

The dry-run gate returns before the install step unless `--install` was
asked for, and the same would have made `--uninstall -n` print the compile
lines and stop -- silently doing nothing where a person was checking what
was about to be deleted. That is the one dry run in this tool that somebody
should always do first, so it is the one that most had to work.

---

## 94. `-MD` for generators, and a check that answered two ways

§15 has carried this since the beginning: *a generator's own dependencies
are not tracked. A `.y` that `%include`s another file re-runs only when the
`.y` itself changes; the rest must be listed in `depends` by hand. There is
no depfile equivalent for generators.*

There is now, for generators that can write one. `[generate.*] depfile`
names a Make-style depfile, and what it lists joins the rule's freshness
key -- the same bargain the compile side has made since phase 1, and for
the same reason: **the tool that did the reading is the only thing that
knows what it read.** `depends` stays for the ones that cannot; flex cannot,
and a shell script only can if somebody makes it.

A declared depfile the command never wrote is an error rather than an empty
list. Treating it as "read nothing" would leave a rule that looks tracked
and behaves exactly as it did before, which is the failure the feature
exists to remove.

### Two defects found by writing the case, not by the case

**The key was order-sensitive.** The first version appended the depfile's
contents to a list already built from `inputs` and `depends`. The run that
*recorded* the deps therefore ordered them differently from the run that
*checked* them, so the stored key never matched the computed one and the
rule regenerated on every build, saying `GEN` each time, for ever. It is a
sorted set of paths now, so collection order cannot reach the hash.

**A generator's own script was not found from outside its tree.** The check
that catches a command naming an uninstalled program asked `shutil.which`,
which resolves a relative path against *this process's* directory. Recipes
run with `cwd` set to the tree, so `./mk.sh` means the script in the
project -- and `cd tree && fmake` accepted a build that `fmake -C tree`
refused, telling the reader their own script was not installed and pointing
at `uses`. §80's shape exactly: a check whose answer depends on how it was
invoked, and the two answers disagree. The case builds the same tree both
ways and requires them to agree, which is the property rather than either
answer.

### A case that pinned a wording

`generated_missing_tool_is_reported` checked for the words "not installed"
and broke when the message learned to say "neither installed nor an
executable file in this tree" -- which says strictly more. **A case that
pins phrasing fails on an improvement and passes on a message that says the
right words about the wrong thing.** It checks that the program is named
and that `uses` is offered, which is what it was always about.

The same trap is recorded at §50 from the other direction, where sniffing a
message for "named _" tied a summary to a wording and rewording it silently
stopped the summary being printed. Twice now, in opposite directions, which
is enough to call it a rule: **assert the property, never the sentence.**

### The control that copied live state

The case proves the feature does something by building the same tree
*without* `depfile` and requiring it to stay stale. That control originally
copied its files out of the tree above -- which by then had been edited
three times, including one edit that added an include the control never
received. It writes its own content now. **Copying live state into a
control is how a control stops testing what it was built to test.**

---

## 95. CI was red, and the tool was the reason

The suite passed here and failed on GitHub, on two cases, for eleven hours
before anybody looked -- across the history rewrite, so the first instinct
was that the rewrite had done it. It had not: the same two cases failed on
the run *before* it, on the original tip.

```
FAIL a_symlinked_directory_is_part_of_the_tree
FAIL two_links_to_one_directory_are_walked_once
2 of 251 failed
```

### The tie-break nobody chose

`_walk` follows symlinked directories and guards against walking one twice
by remembering real paths -- §27. When a directory is reachable both
directly and through a link, the guard keeps **whichever the walk reached
first**, and `os.walk` descends in `readdir` order, which is the
filesystem's hash order.

So the same tree gave its files *different names on different machines*.
Both cases were built with the real directory excluded and the link not,
and they passed exactly when the link happened to be reached first. Here it
was; on the runner it was not.

**The consequence is much larger than two cases.** Which name a file gets
decides whether `[project] exclude` matches it, which `@sources` globs
reach it, what its object path is, and what the ejected build file
contains. §12 claims that file is byte-stable; for any tree with a linked
directory in it, that was true only per-machine.

`dirnames` is sorted now. That does not make the choice *principled* -- it
is still whichever name comes first -- but it makes it the same everywhere,
which is the part anybody can build on.

### Both cases were asserting the tie-break

Sorting alone would have left them failing, deterministically, which is
what made it worth looking at what they were actually for.

- **The symlinked directory case** describes `src/common -> ../shared`,
  "how a pair of sibling projects share code" -- and a sibling project is
  *outside* the tree. The fixture had put it inside and excluded it, which
  invents a second path and a tie-break the real scenario does not have.
  It links to a directory outside the tree now: one path, one answer, no
  order to depend on.
- **The two-links case** is about a diamond being walked once. It asserted
  that by excluding the real directory and requiring the build to succeed,
  which is true only if the winner is one of the links. It counts the
  compilations of `thing.c` now and requires exactly one -- the property
  itself, whichever of the three names it ends up with.

That is §94's rule again, one section later and from a third direction:
**assert the property, never a side effect that happens to correlate with
it.** A fixture that arranges for one arbitrary outcome and checks a
consequence of it is a fixture that passes on the machine it was written on.

### What CI was worth

This is the first defect the CI job has caught that the suite could not,
and it caught it by being a second machine rather than by testing anything
extra. §63 recorded that the job found something before it ever ran; this
is it finding something only a different filesystem could show.

---

## 96. The byte-stability check was passing by luck

§95 was readdir order reaching the output. The same class has a bigger
cousin in Python: **set iteration order, which is randomised per process**,
so a set reaching an emitted file makes that file churn between runs on one
machine rather than between machines.

`eject_is_byte_stable` exists for exactly that -- its docstring names "a set
iterated in a different order" as the thing it guards. It compared two
subprocess runs, which do have different hash seeds, so the guard was real.
It was also **a coin toss**: two random orders of a short list coincide
often, and for a list of one they always do.

The seeds are forced now, three of them, so the check fails on the first
run rather than the fifteenth.

### No leak found, which is worth recording as a measurement

Probed before changing anything: `--eject make`, `--eject ninja` and
`--explain`, over a tree with a static library, a `-lm` resolution, six
programs and three tests, under five hash seeds. Byte-identical every time.
The property held; only the check for it did not.

### Two fixtures that could not fail

Widening the check to the Qt path took three attempts, and the first two
are the interesting part.

**A set of one.** `moc_survives_ejection` builds one class, so the moc plan
has one entry and iterates identically under any seed. A mutation replacing
`sorted(hdrs)` with `set(hdrs)` passed it.

**Three classes nobody constructs.** Adding three more `Q_OBJECT` headers
did not help either, and the reason is §17 working correctly: a class no
program reaches is moc'd, compiled, and then dropped by the closure, so
none of the three reached the ejected file. The plan had four entries and
the *output* still had one.

They are constructed now, by a source the program actually calls, and both
mutations fail. **The shape to remember: a check over a collection is only
as good as the collection reaching the output.** Counting inputs to the
plan says nothing; what matters is how many survive to the thing being
compared.

That is the third variant in three sections of one idea -- §94's property
over phrasing, §95's property over a correlated side effect, and now
coverage over apparent coverage.

---

## 97. The clean that left a build behind

`fmake --clean` removed `.fmake/` and nothing else, so a source a generator
had written into the tree stayed there. **The ejected Makefile has removed
those since it first had a clean rule**, so the two disagreed -- and in the
worse direction, leaving a checkout containing files a fresh clone does not.

§15 recorded the reason: fmake did not create the directory and will not
guess what else is in it. That reasoning is right about *directories* and
was being applied to *files*, which fmake knows precisely.

### Recorded, not declared, and not matched

Three lists were available and only one of them is honest.

- **A pattern** -- `gen/**` or the like. Refused everywhere else in this
  tree and refused here: this is deleting from somebody's source tree.
- **The declared `outputs`** -- correct, but reaching them means scanning
  the whole tree, because a rule can live in a source comment (§27's
  `@rule`). A `--clean` that has to compile nothing should not have to read
  everything.
- **What the generators actually wrote**, recorded in the cache as they
  ran. No scan, no guess, and it is a record of what happened rather than
  of what was declared -- which is the same distinction `--uninstall`
  draws, and the same one that makes both of them refuse to remove
  something they did not put there.

It is read out of the cache before the cache is removed, which is the only
ordering that works and the only interesting line in the implementation.

A tree that never generated anything has nothing recorded and is
untouched -- the case checks that too, because "removed 0 generated files"
appearing on every plain build would be noise, and because a clean that
says something happened when nothing did is a clean nobody reads.

### The directories stay

`gen/` is left behind, exactly as `bin/` is by `--uninstall` and as the
object directory is by the ejected clean rule. Removing a directory means
removing something no list named, and the fact that fmake put a file in it
does not make it fmake's.

---

## 98. The Qt flag every other build system supplies

Reported from a build of hydra on a different machine: 113 moc outputs
failed at once, all with the same #error.

```
#error "You must build your code with position independent code if Qt was
        configured with -reduce-relocations. Compile your code with -fPIC
        (and not with -fPIE)."
```

The guard behind it is in `qcompilerdetection.h` and is worth reading,
because it explains why nobody had seen this before:

```c
#if defined(QT_BOOTSTRAPPED) || ... || defined(__PIC__)
// this is fine
#elif defined(QT_REDUCE_RELOCATIONS)
#  error ...
#endif
```

**It passes whenever `__PIC__` is defined, and `-fPIE` defines it too.** So
on any distribution whose gcc defaults to PIE -- Debian, which is this
machine -- the whole thing is invisible. On one whose gcc does not, it
fires on every Qt translation unit in the tree. Nothing else about that
machine was different.

### Nothing to discover from

The instinct is to detect it: read `QT_REDUCE_RELOCATIONS` out of Qt's
headers, or compile a probe and see. Both are feature probing, which §17
says fmake does not do -- and the second is a configure step in all but
name.

The stronger argument is that **there is nothing to discover from**. Qt's
`.pc` files carry `-I` and `-D` and nothing else; the flag appears in no
file pkg-config will hand over. What CMake's Qt6 does is put
`POSITION_INDEPENDENT_CODE` on its consumers, and what qmake's mkspec does
is add it for libraries. Neither detects anything. **Every Qt build system
supplies this flag rather than discovering it**, because Qt does not say.

So fmake supplies it: a module whose name begins with `Qt` contributes
`-fPIC` to whatever includes it.

### In one place, because there are two routes to a module

`@pkg Qt6Core` and an `#include <QObject>` that pkg-config attributes to
Qt6Core are two ways of reaching one module, and they had separate code
paths for turning it into flags. A flag the module needs is a property of
the module, not of how it was named, so it goes where both paths meet --
and the case checks both, because putting it in one of them looks exactly
like putting it in both until somebody uses the other.

### What the case cannot check -- or so this said; §112 shows it can

That this fixes the #error was left unverified, on the grounds that it
needs a Qt configured with `-reduce-relocations` and this machine's is not
-- checked rather than assumed, by compiling a probe against
`QT_REDUCE_RELOCATIONS`. So the case here checks the flag is passed, on
both routes, into the ejected build as well, and **not** to a non-Qt
module. §112 supplies the missing condition instead of accepting it.

That last one took a second attempt. The first negative case was a plain C
program, which resolves no package at all, so the code deciding this was
never reached and a version handing `-fPIC` to *every* module passed
against it. It resolves zlib now. **A negative case has to reach the code
it is negating**, which is §96 one section later and in a smaller room.

### The second error in that report

`QWebEngineUrlRequestInterceptor: No such file or directory` is a package
that machine does not have, and the diagnostic was right about it. What was
wrong was the sentence after:

```
if .fmake/moc/src/moc_qtwebengine_interceptor.cpp belongs to another
platform, @os NAME or @arch NAME keeps it out of this build
```

**That is an instruction to edit a file fmake wrote and will overwrite**,
and the file to act on -- `src/qtwebengine_interceptor.cpp` -- was listed
further down among the others, unremarked. §31's shape in its sharpest
form: the advice is not merely unhelpful, it cannot be followed.

fmake knows where every generated file came from, because the moc, uic and
rcc plans are built from exactly that. The map is taken from the plans
rather than derived from the paths, since "`moc_x.cpp` came from `x.h`" is
wrong for a `Q_OBJECT` declared in a `.cpp`. The failure now says
`generated from src/thing.h` and blames that file.

The negative half is that a file nobody generated must keep its own name
and gain no "generated from" line -- a mutation claiming every failure came
from somewhere fails on it.

---

## 99. The typo that could be named after all

§15 carried this as unfixable, and the reasoning was sound as far as it
went: `@lib` for `@libs` does nothing and says nothing, because an unknown
command has to be ignored -- the comment is shared with Doxygen, and
warning about `@brief` would make the integration unusable.

**The question was never "is this unknown".** It is "is this unknown *and*
almost one of ours", and that is answerable without knowing anything about
Doxygen at all. Two conditions: one edit away, and the same first three
characters.

```
* main.c:4: @lib is not a directive; did you mean @libs?
* main.c:5: @cflag is not a directive; did you mean @cflags?
```

### A justification that was invented

The first version of this said the prefix rule was what kept Doxygen quiet,
with `@par` being one edit from `@pkg` as the example. **`@par` is two
edits from `@pkg`, and the example was made up rather than checked.**

Measuring it says something better and different. Against Doxygen's 161
documented commands, **the edit distance alone already suffices** -- not
one of them is a single edit from any directive here. The prefix rule keeps
nothing quiet that would otherwise have spoken.

What it actually buys is the suggestion being *useful*. Doxygen is not the
only thing that writes `@word` in a comment, and one edit is a wide net over
arbitrary words: `@bind` is one edit from `@kind`, and answering it with
"did you mean @kind?" is worse than silence, because it is confident and
wrong. The case pins that with `@bind` -- and nothing else in it reaches
that half of the rule, which is why the mutation dropping the prefix
survived until it was added.

### Warned from the record, not from the scan

A scan is cached. A warning printed while scanning appears on the first
build and never again, which is worse than not printing it -- the reader
sees it once, in the noise of a first build, and every build afterwards is
silent about a directive that is still doing nothing.

So the near misses are stored in the scan record and reported at build time
from there. The case builds twice for exactly this, and a mutation that
warns at scan time instead fails on the second build.

One consequence, named rather than left: a file scanned into an existing
cache before this change has no near misses recorded, so it stays quiet
until something makes it rescan. Bumping the cache version would fix that
and cost every user a full rebuild for a warning, which is the wrong trade.

---

## 100. The archives the cover put in the wrong order

`ld` searches an archive only for what is undefined at the moment it
reaches it. An archive listed before the thing that needs it contributes
nothing at all, and the link fails on a symbol neither the program nor
fmake ever mentioned.

§18 grouped the archives **in the tree** for exactly this. The `-l` flags
the cover resolves were never grouped, and the cover has no reason to have
ordered them usefully -- it ranks by coverage, not by who needs whom. Two
or more resolved archives are grouped now.

One archive still gets none. A shared library is not order-sensitive as a
provider, and libc is implicit and last regardless, so a single archive has
nothing it could be on the wrong side of -- and a group is linker syntax on
every ordinary link line for a problem that line does not have. The case
for that is separate and a mutation grouping unconditionally fails it.

### The fixture that proved nothing

The first version had two archives with a mutual dependency and it linked
either way, with the fix reverted, on the first try. The reason is worth
keeping: **both of the second archive's functions were in one object**, so
pulling either brought the other along and the order stopped mattering.
An archive is searched per *member*, not per archive, and a fixture that
forgets that is testing nothing.

Separate objects now -- and the case establishes the fixture is
order-sensitive by running `cc` directly, both ways, before it asks fmake
anything:

```
cc main.c -L... -lzzbeta -lzzalpha    undefined reference to `zzbeta_helper'
cc main.c -L... -lzzalpha -lzzbeta    links
```

Only then is it worth checking that fmake picks an order and survives it.
Which it does, and it picks the failing one: `-lzzbeta -lzzalpha`, grouped.

**A test for an ordering bug has to contain an ordering the linker can
actually get wrong**, and that is not the same as containing two things
that depend on each other.

### A stale line in §15, while here

That entry also said there was no `SONAME`. §22 added one, and the entry
had not been told. Corrected rather than left, since it is the list people
read to find out what is missing.

---

## 101. The prebuilt object, and the version of it that would have been wrong

§18 closed this question for `.a` and guessed the rest would follow. The
symbols do: `nm` reads a loose object exactly as it reads an archive, so a
`.o` joins the link set by symbol with nothing new asked of the closure.

**What does not follow is discovering them**, and the obvious
implementation -- walk the tree, treat every `.o` as a provider -- turns
working trees into broken ones.

```
$ ls
helper.c  helper.o  main.c        # helper.o is what `cc -c helper.c` left
```

That is not a vendored blob, it is litter, and it is everywhere: a kernel
checkout in this workspace has dozens sitting beside their sources.
Discovering it means two providers for every symbol `helper.c` defines, and
§3 refusing to choose -- a build that works today failing on a stale object
nobody meant to keep. **Naming the file is the entire difference between a
vendored blob and a leftover**, so a prebuilt object is declared, in
`@sources` or `[target.*] sources`, which are already the two ways of
saying "link this whatever the symbols think".

Both halves have a case. The second one -- a stale `helper.o` beside
`helper.c`, deliberately returning a different value -- is what says the
discovery version stays unbuilt, and it fails the moment anything picks up
a loose object.

### Two facts that had been one

`Unit.archive` meant two things at once and nothing had noticed, because
until now they were never different:

- **where it goes on the link line** -- an archive goes after every object,
  inside a group;
- **whether fmake compiled it** -- an archive has no compile step, no
  object directory and no depfile.

A prebuilt `.o` is the first thing that is the second without being the
first: fmake did not build it, and it is an ordinary object rather than
something the linker searches member by member. Five places read
`u.archive` to mean "nothing to compile" and got the wrong answer, one of
them by tracebacking out of `--explain`. `prebuilt` is its own field now,
and `archive` means only what it says.

That is the shape worth remembering rather than the feature: **a flag
carrying two facts is correct until the first case where they differ**, and
the case where they differ is the one that arrives long after everybody has
stopped thinking about it.

---

## 102. The library fmake could install and then not find

fmake resolves libraries through pkg-config: a header proposes a module,
the module's `.pc` supplies the flags. That is §5, and it is most of what
makes a tree build with nothing said.

**A library fmake installed was findable by none of it.** Headers in
`includedir`, an archive in `libdir`, and nothing tying the two together --
so the next project had to be told with `@pkg` or `@libs` exactly what
fmake would otherwise have worked out. The consumer that most obviously
suffers is fmake.

Declaring a `version` writes one. There is no default, and that is the
whole of the opt-in: a `.pc` without a `Version` is a file pkg-config
refuses to read, and inventing `0.0.0` would publish a number nobody chose
into a file other projects then depend on.

### An ordinary built file

The `.pc` is written beside the artifacts at build time, which is the only
interesting design decision in it. From that moment it is a built file like
any other: `install_plan` picks it up with no special case, `--uninstall`
removes it because the plan names it, `--clean` names it, and both ejected
builds emit a rule for it. Four callers, no fourth idea.

Rewritten only when its content changes, for the same reason the ejected
build file is byte-stable: it is a file somebody may commit.

### `${prefix}` belongs to two languages

The ejected Makefile writes the `.pc` itself, because a clean checkout of a
project that committed that Makefile has no `.pc` in it and an install rule
naming a file nothing produces fails on the one machine that matters.

The first version of that rule was wrong in a way that looked right:

```make
greet.pc:
	printf '%s\n' 'libdir=${prefix}/lib' ... > $@
```

**`${prefix}` is a pkg-config variable and a Make variable reference, and
Make wins.** The recipe ran, succeeded, and wrote a `.pc` with empty paths
-- §26's trap, in a new file, twenty-odd sections later.

It was caught because the case compares the ejected output **byte for byte
against fmake's own** rather than checking that a `.pc` exists. A
`pkg-config --modversion` check would also have passed: the Version line
was fine. It was the paths that were empty, and only the comparison saw it.

### What the checks actually ask

`pkg-config` is asked to read the file, rather than the file being searched
for substrings -- it is the reader, and a file it will not parse is not a
pkg-config file however much it looks like one. And the paths are required
to be relative to `${prefix}`, because a package built with one prefix and
installed under another is what staging and every distribution do; baked
paths pass a substring check and are wrong the moment they are relocated.

---

## 103. The soname chain, for the price of a rule

§22 gave shared libraries a soname. §15 recorded the rest as missing: a
`.so` installed under its plain name, which is right for a library shipping
beside the thing that uses it and wrong for one anybody else links against.

The `version` §102 added for pkg-config is the same declaration, so this
cost a rule rather than a concept:

```
libgreet.so        -> libgreet.so.1        what -lgreet finds
libgreet.so.1      -> libgreet.so.1.2.3    what NEEDED records
libgreet.so.1.2.3                          the file
```

**The soname is the major alone**, which is the promise a soname makes --
"anything with this number will do" -- and the reason a distribution can
put 1.2.4 under a program linked years ago.

### Built plain, installed versioned

The artifact in the tree stays `libgreet.so`. Renaming it would mean
teaching `clean`, the link rules and both emitters a second name for one
thing, and the tree has no use for a chain: nothing there resolves a
soname. Only the install grows.

The symlink targets are **bare names**. An absolute one points into
whichever tree happened to build the library, which is gone by the time
anybody installs the package -- and a staged install has a different prefix
from the final one by definition. The case checks that specifically,
because an absolute link works perfectly on the machine that made it.

### One new idea in the plan, and it earns its place

`install_plan` grew a third origin: `built`, `tree`, and now `symlink`,
whose "source" is what the link points at rather than a file to copy. That
is the first thing in the plan that is not a copy, and it goes through all
four callers unchanged in shape -- fmake, `--uninstall`, the ejected
Makefile and the ejected ninja each learned one line. The chain is
identical from all three that produce it, which is the property §85's case
already checks.

### What the case asks

Not that three files exist. It links a **consumer** against the installed
library and reads what that program recorded:

```
0x0000000000000001 (NEEDED)   Shared library: [libgreet.so.1]
```

That is the whole point of the exercise, and it is the one thing a
directory listing cannot show. An unversioned library still installs one
plain `libq.so` and no chain -- checked too, since giving every shared
library a chain would be the same feature done wrong.

---

## 104. The hand-written list nobody had checked

§15 names three lists as load-bearing, and says a fourth would be the
signal that the provider model wants a real predicate. It says nothing
about whether the three are *right*, and one of them was not.

`LINKER_SYMBOLS` is the set of names the linker supplies -- undefined in
every object, exported by no library, and not missing dependencies. It had
twenty-two entries and had never been compared with a linker.

```
$ ld --verbose | grep PROVIDE
```

says this one provides six that fmake did not know: `end` and `edata` --
the oldest names on the list and still referenced by real code -- plus
`__etext`, `__tdata_start`, and the two `__rela_iplt_*` bounds a static PIE
walks.

The symptom is the one §15 predicted, and it is §31's shape:

```
no x86_64/64le library exports: __rela_iplt_start, end, genuinely_missing
```

**Two of those three are not missing at all.** The reader is sent looking
for packages that do not exist, and the one symbol that is actually the
problem is a third of a list. Afterwards the same build says
`genuinely_missing` and nothing else.

### The suite probes; the tool does not

The obvious repair is to have fmake read the default linker script. That is
a subprocess on every build for a question whose answer changes when
binutils does, and §17 is explicit that fmake does not probe features --
which is a rule about the *tool*, not about its tests.

So the check lives in the suite. `ld --verbose` is parsed there, and the
list must cover what it names. A toolchain that provides something new
fails the suite rather than somebody's build, and the failure says which
symbol.

**That is the general move for a hand-written list**: not "replace it with
detection", which trades a stale list for a slow build, but "make something
that runs regularly compare it against reality". The list stays a list. It
stops being unexamined.

### What it still does not cover

An `ld` that prints no default script -- lld, or a cross toolchain that
answers differently -- skips the case rather than failing it, so the list
is checked against the linker the suite happens to run on. The other two
lists are §105.

---

## 105. The other two lists, and a check that checked nothing

§104 left the other two of §15's load-bearing lists untouched. Both are
checked now, and neither was wrong -- which is worth as much as finding a
bug, because until this ran nobody knew.

### Interposers: the failure that is silent

A sanitiser runtime exports the symbols it interposes on, so by symbol
evidence it is a perfectly good provider and the cover can pick one because
it happens to intercept more of what a program calls. §14 caught `-lasan`
being offered as an alternative to `-lm`.

**The danger runs the opposite way from §104's list.** There, a missing
entry produces a false alarm -- noisy and self-correcting, because somebody
reads it. Here it produces a sanitiser linked into an ordinary build, and
nothing says so.

So the machine is asked which of its libraries look like interposers --
exporting `malloc`, `free` and `memcpy` without being libc -- and every one
must be named. Three are here: `asan`, `hwasan`, `tsan`. All three are on
the list, and removing one fails the case.

A first version searched `/usr/lib` and the usual places and found **zero**,
which would have passed for ever. The sanitiser runtimes live in the
compiler's own directory, which is where fmake looks and where the case
looks now. A check that finds nothing is not a check that found nothing
wrong.

### The header table, and two attempts at evidence

`HEADER_PKG` maps a system header to the pkg-config module that owns it.
The obvious test -- is the header under one of the module's `-I`
directories? -- **checks almost nothing**, and the mutation proved it:
mapping `zlib.h` to `libpng` passed. pkg-config emits no `-I` for a header
in a default directory, which is 11 of the 12 installed entries here, so
the check fell back to `/usr/include` and passed for any module at all.

What actually ties a header to a module is the package manager: they ship
in the same package, or the mapping is wrong. Twelve entries verified that
way, zero disagreements, and mapping `zlib.h` to `expat` now fails.

**Two things that mutation taught, both about mutations rather than about
the code.** The first attempt at breaking it -- `zlib.h` to `libpng` --
also passed against the *fixed* check, because libpng is not installed here
and the entry simply skipped. A mutation has to change something the check
can see, and "the check passed" is evidence about the mutation until you
know it did. The second is that a fallback added for robustness is exactly
what made the check vacuous: `/usr/include` was in the list so that a
header in a default place would still be found, and it meant every header
was found regardless of the module.

---

## 106. Section 76's claim, enumerated

"Objects are keyed by the whole configuration" is what stops a sanitized
object being linked into a plain build -- netcfgd's incident, and the whole
of §76. It is also a claim that decays every time a knob is added, and this
session added four: `$DEBUG`, `$SANITIZE`, the Qt `-fPIC`, and a
generator's depfile.

So the knobs were turned, one at a time, and the key watched. **Nothing was
wrong**, which is the same kind of result as §79 and worth the same
recording: the property was believed rather than known, and now it is
known.

Two mechanisms carry it, and both count:

- a knob in the **configuration** changes the object directory, so two
  configurations keep separate object trees and switching costs nothing;
- a knob in **one file** leaves the directory alone and changes that
  file's key, so it recompiles in place.

What must never happen is neither, and a case now turns eight configuration
knobs and requires each to land somewhere new.

### The one that looks wrong and is not

`[project] include-dirs` shares an object directory with the unset case.
The include flags are in the *key* without being in the *path*, so
switching forces a recompile and can never hand back a stale object -- it
costs a rebuild when alternating rather than keeping two cached sets. A
trade, not an oversight, and the case checks the rebuild rather than the
directory so it cannot be "fixed" into a false alarm.

### Two things the mutations taught, both about tests

**A message that indexes what it is checking.** The first version wrote
`check(got not in seen, f"...{seen[got]}...")`, and Python builds the
message whether or not the condition holds -- so the *passing* path raised
`KeyError`. A check whose failure text cannot be evaluated on the success
path is a check that fails when it should pass.

**Two knobs may legitimately agree.** Asserting that no two of them key
alike failed immediately: `--cflags -O3` and `CFLAGS=-O3` are two
spellings of one input -- the help says so -- and identical flags *should*
produce identical objects. The values are distinct now, which is what makes
the pairwise check mean "this knob was ignored" rather than "these two
knobs agree".

### And one term that is not load-bearing

Removing `u.own` -- the per-file flags -- from the object key survives the
case, and no fixture can catch it: a per-file flag lives *in* the file, so
changing it changes the content hash, which is already in the key. The term
is belt and braces.

That is worth writing down rather than deleting. It is the only term that
would still work if a per-file flag ever arrived from somewhere other than
the file, and "no test covers it" is a much weaker statement than "nothing
depends on it".

---

## 107. Running the five projects again, and three defects in one message

Thirty-odd commits into a session that changed the default flags, put the
project's compile flags on the link line, sorted the tree walk and added
`-fPIC` for Qt, nobody had asked whether a real project still built. So all
five were run again, from copies rather than from anybody's working tree.

**Four were fine.** netcfgd builds its GUI and its client. situ builds
`libsitu.a` from one line of configuration, and the archive holds
`situ.c.o` alone -- §73's fix, still holding. hydra builds its 57 files,
now with `-fPIC` on every Qt compile, and ejects a 6252-line Makefile.

beerssh found three defects, each hiding the next.

### One symbol, two archives, and a traceback

beerssh ships a prebuilt `libcrypto.a` for two Android ABIs beside its
desktop sources. Both define the same symbols, §3 refuses to choose --
which is right -- and the code explaining the refusal looked every provider
up with `scans[p]`.

**An archive has no scan**: it was never a source, and §18 gives those
units an empty one outside the scan map. `KeyError`, and a traceback out of
the command line. §32's class, arriving in the code written to explain a
failure rather than in the failure itself.

### Advice an archive cannot take

With the traceback fixed, the message offered `@os` or `@arch` on the
platform-specific one. Those go in a source file, and an archive has none
-- §101 again, two sections later, in a message that had been correct for
sources since it was written.

### And the remedy that did nothing

So the advice became `[project] exclude`, which names paths rather than
files and is exactly right for a vendored archive. Following it changed
nothing: **`exclude` had never reached archives.** `find_archives` walks
the tree and the only filters applied afterwards were "something this tree
builds" and "something in the output directory".

That is the one lever a project has for "this subtree is not for this
build", and the thing it could not move was the only kind of file that had
no other way of being excluded.

### fuzzypickles: 252 lines, nearly all identical

The fifth project stops on an ambiguity and offers a `[target.*]` stanza
per program -- the thing the reader would otherwise write by hand. It built
that list by looping over one entry per *(target, symbol)*, and **a file
that collides with another collides on everything it defines**: eight
meta-objects there, so the same block eight times, and the advice line
above it sixteen.

Said once each now: the stanza depends only on the target, the advice line
on the target and the file. Neither was a new fact, and a message nobody
can read is a message not doing its job -- particularly this one, which
exists because the situation is confusing.

The ambiguity itself was the fixture again: `gui/moc_main_window.cpp` is a
qmake leftover, git-ignored in their tree and copied by `tar`. Third time
in one sweep, which is a rate worth naming.

### What the sweep says about sweeps

Each of the three was hidden behind the one before it: the traceback hid
the bad advice, the bad advice hid the ineffective remedy. A fix that
stopped at the traceback would have left a message that reads perfectly and
sends the reader nowhere.

Worth recording too: the sweep nearly reported a regression that was its
own fault. `git archive` does not include submodule contents, so the first
beerssh copy had an empty `vterm/` -- 80 files missing -- and failed to
link on symbols that were simply not there. **A fixture built by a
convenient command is a fixture worth checking before believing what it
says about the tool.**

---

## 108. Asking git the question it had already answered

§107's sweep hit the same collision twice, in two different projects: a
build output left in the tree, colliding with the file it was generated
from. Both times the reader would have been shown two files defining one
symbol and given no reason to prefer either -- while `.gitignore` had said
for years that one of them is not source.

```
!!! symbol 'shared' is defined by more than one file:
    generated_copy.c
    real.c
fmake will not guess which one belongs in app.

git is told to ignore generated_copy.c, so it is probably build output
rather than source. [project] exclude in fmake.toml keeps it out.
```

### Explaining, not deciding

**This is not a signal fmake builds with**, and the distinction is the
whole of why it is safe. What to compile is decided from the source; adding
`.gitignore` as a second authority for that would be a design change, and a
tree whose ignore rules are wrong would silently build something different.

It is consulted only while explaining a failure, on a path that is about to
exit, so it costs one subprocess and can be wrong without costing anything.
A `git` that cannot answer -- no repository, not installed, an exit status
that is neither 0 nor 1 -- says nothing rather than guessing.

The same fact used the other way round is what hydra's `fmake.toml` already
does by hand: its exclude list exists to restate `.gitignore`. That
duplication is still there, and turning it into inference is the design
change this deliberately is not.

### The half that had to stay quiet

Nothing is said when git ignores **neither** provider, and nothing when it
ignores **both** -- naming both explains nothing, and this message is
already the hardest one fmake prints. Two of the three mutations are those
directions, because a diagnostic that fires when it has nothing to add is
how a useful message becomes one people skim past.

---

## 109. The packaging report, folded in and removed

`suggestions/packaging.md` is the last of the seven evaluations still in
the tree. Its closing note asked for this outright: *"If the folding was
the point, this belongs in project.md section 16 instead and the directory
should go again."*

### What it said, and where it landed

**Packaging itself: no, and the design already says so.** It compares the
Debian stack -- `dpkg-deb`, `dpkg-buildpackage`, `dh`, `debuild`, `cpack`
-- and concludes fmake should build none of it. The metadata is not in the
tree: a maintainer, a distribution, a changelog and a licence are
declarations nobody can infer from source. `dpkg-shlibdeps` has better
evidence than fmake does, because it reads the finished binary against the
installed package database. And `debian/rules` driving a Makefile is three
lines. **That verdict stands and is why fmake has no packaging feature.**

**The real gap: an ejected Makefile had no `install` target.** Closed by
§85, in both emitted forms, and by §93's `uninstall` beside it.

**"Say what an ejected build installs."** Its own words are the argument:
*"which files are products, which are intermediates, which are meant to
ship -- that is knowledge fmake has and currently keeps."* `--explain` has
an `installs` block now, read out of `install_plan` rather than described,
so it cannot drift from what installing does:

```
  installs
    libgreet.so.1.2.3                   -> $LIBDIR
    libgreet.so.1                       ->(link) $LIBDIR   [libgreet.so.1.2.3]
    libgreet.so                         ->(link) $LIBDIR   [libgreet.so.1]
    greet.h                             -> $INCLUDEDIR
    greet.pc                            -> $PKGCONFIGDIR
```

The directories are the variables rather than resolved paths. A packager
stages under a different prefix than a plain build uses, and `$LIBDIR` is
what a `debian/rules` is written against; a resolved `/usr/local/lib` in
that listing would be wrong for the only reader who wants it.

### Removed for the reason the other six were

A report is a snapshot of one run against a tree that has since changed.
Every ask in this one is either implemented or recorded above, and the
`suggestions/` directory goes with it -- for the second time, which is what
its own note predicted. It stays in the history, one commit back.

---

## 110. The same question as §79, and a method that answered the order

§79 asked whether a session's additions had made fmake slower and found it
flat. Forty-one commits later the same question was worth re-asking, and
this time several of the additions are on the build path rather than off
it: a sorted walk, an architecture check on the first object, a `.pc`
written beside the artifacts, a depfile read back per generator rule.

**Still flat.** On the same hydra tree, no-op rebuilds:

```
rev        min   median   max
0648010   1412     1722  1968
8c623ef   1199     1450  1598
5ce1544   1232     1813  2103
HEAD      1155     1812  2076
```

Each version's own spread is 600 to 900 ms, which is wider than any
difference between versions. Nothing here orders with age.

### The first two attempts measured the order, not the versions

Running the four versions one after another in one tree gave a clean,
confident answer: **HEAD fastest, by 18% on the median.** Running them in
the reverse order gave the opposite answer, equally cleanly: HEAD slowest,
by about the same margin.

The cause is that switching fmake versions in a tree makes the next run
re-resolve, so every measurement was dominated by which version had gone
before it. The maxima said so out loud and were nearly missed: **80 to 97
seconds** against medians of 1.7, exactly once per version, on whichever
version had just been displaced.

Each version has its own copy of the tree now, warmed with itself, and the
outliers vanish.

**What they were is not what this first said.** They were called an
artifact of the experiment that nobody building a project meets, and that
was wrong: the expensive run is a *full recompile*, because this session
changed the default flags -- `-Os -g` became `-Os`, and Qt gained `-fPIC`
-- and different flags are a different object key. Anybody upgrading fmake
across that change rebuilds once, exactly as the experiment did. Correct
behaviour, and met by every user rather than by none.

**A measurement whose answer reverses when you reverse the order is
measuring the order.** It is worth running the second direction before
believing the first, and that costs one repetition of something already
written -- against a result that would otherwise have been recorded here as
a fact.

---

## 111. The second list in the same file

§82 guarded the README's option table and stated the rule that made it
worth doing: the README is documentation of record here, so anything it
lists that the program also knows needs a case holding the two together.

The directive table is the second such list, twenty lines further up the
same file, and it was left unguarded. `@version` -- added by §102 a few
commits after the rule was written -- was missing from it, which is the
drift the rule exists to catch, in the one place the rule had not been
applied.

Guarded now, against `DIRECTIVE_SCALAR` and `DIRECTIVE_LIST`, with the
alias table folded in so `@defines` does not read as undocumented: it is
the plural spelling of `@define`, accepted so that a fact does not need a
different word for living in a config file, and documenting both would
suggest they are two things.

### The check found its own bug first

The alias table is read out of the source, and the first version sliced
from `DIRECTIVE_ALIAS = {` to `src.index("DIRECTIVES = ")`. That second
string matches `MK_PROJECT_DIRECTIVES = ` **twelve hundred lines earlier**,
so the slice ran backwards, came out empty, and `@defines` was reported as
missing from the README.

The fix is to anchor at a line start and search forward from where the
alias table actually is. The lesson is smaller and more reusable: **a
substring is not an anchor**, and a check that reads its own program's
source is the easiest place to forget it -- the string that identifies a
definition usually also appears inside three longer names.

A `check` that the alias map is non-empty is in the case now, so a slice
that silently reads nothing fails rather than producing a confident wrong
answer about the README.

### And the list that is deliberately not guarded

Applying the rule a third time would have been wrong, which is worth
recording so the next application stops in the right place.

The README's `fmake.toml` block looks like the same kind of list and is
not. Measured against `CONF_SCHEMA` it is missing fifteen keys --
`include-dirs`, `test-group`, `cxx`, `sysroot`, `lib-dirs`, both
`description`s -- and none of that is drift, because **the block is an
example and the program is the reference**:

```
[target.x]: unknown key 'nosuchkey' (expected one of: description, headers,
kind, ldflags, libs, name, pkg, root, sources, target, test, test-args,
test-group, test-timeout, version)
```

Every section answers like that, `version` and `depfile` among them,
without anybody having maintained a second copy. The README says so in one
line -- *"Unknown keys are an error, with the valid ones named"* -- and
that sentence is the thing worth guarding, not the example beneath it.

This is the same distinction the documentation gate draws between a path in
prose and a path in a table (§44): **an inventory has to be complete and an
illustration does not**, and forcing fifteen keys into a snippet would make
it useless at the job it actually does.

---

## 112. Conditions recorded as untestable, and what that cost

Four places in this document had recorded a property as unverifiable and
moved on. All four were wrong, in the same way, and the method that
unstuck them is one sentence:

> **An untestable condition is worth restating as a list of differences
> before it is accepted**, because the differences are usually smaller
> than the label.

Not "we need a Qt built the other way", which is true and ends the
conversation, but "what does that machine do that this one does not".

### Qt's `-fPIC`, which §98 said needed a different Qt

§98 fixed the `-fPIC` reported from another machine, checked the flag was
passed on both routes to a module and into the ejected build, and recorded
that whether it *silences Qt's #error* could not be checked here, because
it needs a Qt configured with `-reduce-relocations` and this one is not.
Two differences, both arrangeable:

- **`QT_REDUCE_RELOCATIONS` is an ordinary macro**, so `@define` sets it
  and Qt's guard behaves exactly as on a Qt built that way. The guard
  reads the macro, not the build.
- **A compiler that does not default to PIE is a three-line shim**
  (`exec c++ -fno-pie "$@"`). Faithful rather than approximate: the
  reporting machine's gcc puts `-fno-pie` first too, and fmake's `-fPIC`
  comes later and wins.

With both, the reported failure reproduces exactly, and removing fmake's
`-fPIC` is what produces it.

**The flag order is the mechanism, and it corrects §98:**

```
-fPIC            __PIC__=2
-fno-pie         neither
-fPIC -fno-pie   neither      <- cancelled
-fno-pie -fPIC   __PIC__=2
```

§98 said `--cflags` could not drop the flag. What `--cflags` cannot do is
remove it from the *list*, and it is emitted last by design, so
`--cflags -fno-pie` leaves `-fPIC` in the command and cancels it.
**Surviving in a flag list is not the same as taking effect** -- the
distinction this document spends most of its length insisting on, got
wrong in the section that introduced the flag, by a check that looked for
`-fPIC` in a string.

### Clang, and a wrong reason repeated twice

§15 recorded a good fear about LTO: `clang -flto` emits **pure bitcode**
where GCC emits an ELF object with extra sections, an object `nm` reads
nothing from defines nothing, and a file that defines nothing is invisible
to the closure -- so every file would look like it provides nothing and
the link set would be empty. Untested, "because clang is not installed
here".

**Clang is installed here**, at `/usr/lib/llvm-19/bin/clang`, which is not
on `$PATH`. `which clang` was the whole investigation. The same false
premise had been written down independently in §86, where it left the
claim that clang treats `-Og` as roughly `-O1` unchecked -- measured, they
are **byte-identical objects**, while gcc's five levels all differ.

The LTO fear does not materialise. The objects really are bitcode (the
fixture checks the `BC c0 de` magic rather than trusting the flag), the
closure is exactly right, and the binary runs. `nm` reads bitcode because
**`LLVMgold.so` is installed as a BFD plugin**, in
`/usr/lib/bfd-plugins` -- a property of the machine, not of the tree or
the compiler, so the feared failure is real elsewhere. Mutating `read_symbols` to return nothing for bitcode produces
it, and fmake reports rather than silently linking an empty program:

```
* main.c looked like it defined main() but the object does not export it
!!! no target could be built
```

### A moc that cannot run, where the obvious fixture is the wrong one

§17 listed this as handled-but-untested: on a cross build the moc
pkg-config names may be a target binary that cannot execute here. Reaching
it needs no cross toolchain at all -- and the obvious fixture is actively
wrong on this machine:

```
qemu-aarch64 is registered in /proc/sys/fs/binfmt_misc
    an aarch64 binary RUNS here; no OSError at all
```

**Bytes that are no executable format** are refused by every kernel with
`ENOEXEC`, which is what the code reacts to. Four junk bytes and a
`chmod`: smaller than the toolchain, and true everywhere.

### A toolchain with no prefix to derive anything from

§15 records cross builds as verified against `aarch64-linux-gnu-*` and
notes that a toolchain naming its tools differently is untried. Clang is
that toolchain, and it is the interesting case rather than an exotic one:
one binary for every target, chosen with `--target`, no triplet for
`_prefixed()` to derive from, the host's binutils reading the objects.

It works end to end. The case checks the **artifact** -- `e_machine` 183,
a real aarch64 ELF -- because "the build succeeded" is what a cross build
says when it has quietly produced a host binary, which is the failure §5
was written about.

**What does not work is how everyone spells it.** Autotools and make treat
`CC` as a word list, so `CC="clang --target=aarch64-linux-gnu"` is the
ordinary idiom, and it produced `C compiler '...' not found` -- which
reads as a missing program and says nothing about the space.

`cc` stays a program, and this is a decision rather than an oversight.
`self.cc` is invoked on its own in eight places, three of which are
questions whose answers `--target` changes:

```
cc -print-multiarch        the triplet
cc -print-search-dirs      where libraries are
cc -E -Wp,-v               the builtin include path
```

A compiler that is really a command line has to be a **list** everywhere,
including those probes, or it answers for the host while compiling for the
target -- the exact class of silent wrongness this tool exists to refuse.
**That design change is raised, not made.** What is fixed is the message:
the space is recognised and `[project] cflags` named, which reaches the
compile *and* the link as a `--target` needs. A plain typo keeps the plain
message, checked, because trading one misleading answer for another is not
a fix.

### The shape of the four

Each was blocked by a label rather than by a condition, and in three of
the four the fixture that finally worked was **smaller than the toolchain
that produces the condition** -- a macro, a three-line shim, four junk
bytes. A test that needs the whole environment reproduced is usually a
test that has not yet been reduced.

---

## 113. Advice that names the wrong fix

§31 named the pattern: the code that knows the answer runs early, the code
printing the last line never asks it. Six more instances collected here,
all in *advice* rather than in a summary. The first four turned up
alongside other work; the last two came from asking the question
deliberately, once it was clear they were one shape rather than four
coincidences.

Two rules cover them, and the second is the sharper:

> **Where two fixes are possible, naming one is not brevity. It is a guess
> presented as a diagnosis.**
>
> **Where the tool refuses to choose, the advice must not choose either.**

The common cause is duplication rather than carelessness: a message that
*echoes* a path cannot drift, and every one of these **computed** an
answer the deciding code had already computed differently.

### An object `nm` could not read

`read_symbols` dies when `nm` exits non-zero, and said: set `[toolchain]
nm` to one that understands **unknown** objects. `elf_identity` returns
`None` for a file that is not ELF and `describe_identity(None)` is
`"unknown"`, so a clang LTO build on a machine without the BFD plugin was
sent looking for a cross-toolchain problem it did not have -- when the
first four bytes say LLVM bitcode and the fix is `llvm-nm`, verified to
build the tree rather than assumed. `bitcode_object()` reads the magic;
the message names the format, the reader that handles it, and the plugin
that would let the existing one handle it.

### A moc that cannot run

Three routes to a moc, and the message was right for one:

```
named by [toolchain] moc  -- advice: set [toolchain] moc
named by $MOC             -- advice: set [toolchain] moc
found by pkg-config       -- advice: set [toolchain] moc
```

Two of those tell the reader to do what they have already done.
`run_moc` was handed the path and not who chose it, so the line printing
the instruction could not ask; `tool_origin()` answers it once, and
`find_qt_tool`'s not-found message uses it too, having previously carried
its own copy of the same logic.

**The branch nothing would otherwise reach** is the one a real cross build
hits -- pkg-config naming the broken tool -- and a `.pc` on
`PKG_CONFIG_PATH` whose `libexecdir` points at the junk file arranges it.
All three are checked rather than two plus an assumption: *the branch left
unexercised is the one a change is most likely to break, because it is the
one that was already correct.*

### A meta-object the tree was supposed to generate

§17 recorded `#if 0` as the tested case for the scan and moc's
preprocessor disagreeing, and left other conditional shapes unenumerated.
Enumerated, the claim holds -- moc writes a zero-byte file for all of
them:

```
#if 0 · #ifdef NEVER_DEFINED · an untaken #else · a block comment ·
a string literal          all 0 bytes
```

(Against a real output file. Told to write to `/dev/stdout` moc emits a
60-odd byte preamble for all five, which would have read as five failures
of the fixture's own making.)

**But the limit considered only one direction**, and the harmless one. A
class reaching the macro through *another* macro carries no token at all:

```cpp
#define MY_OBJ Q_OBJECT              // macros.h
class G : public QObject { MY_OBJ };  // g.h -- zero occurrences of Q_OBJECT
```

moc's preprocessor expands it and generates 2670 bytes; the scan sees
nothing, plans no job, and the link fails on `undefined reference to
vtable for G` -- `no x86_64/64le library exports: _ZTV1G`, which mentions
no Qt anything -- with **`--ldflags`** offered -- sending the reader to
install a library for a meta-object their own tree makes.

Recognising the shape by inspection means understanding macro expansion,
which fmake declines to do everywhere else. **Asking moc answers it
exactly**, and is affordable only where it now runs: after a link has
already failed, when Qt is being linked, over the headers that link set
includes. The advice grew a third ending, because there are three causes
and one of them is a missing library.

**Not done, and declined rather than pending:** falling back to running
moc on every header. Correct, slow, and a token search turned into a
compiler pass for a shape Qt's own documentation does not use. Reporting
precisely where it fails is the smaller answer, and the one `@sources`
already takes for symbol-invisible dependencies.

### An architecture mismatch

Leave `[toolchain] arch` out of a clang cross build and the architecture
check catches it, correctly -- from where that check stands, a compiler
cross-compiling by flag is indistinguishable from the wrong compiler. It
offered `name the right one with [toolchain] cc`, which is the one fix
that does not apply when the compiler is right and the *declaration* is
missing. It offers both now, with the architecture filled in from what was
read out of the object.

### The advice that named the wrong directory

Trying fmake against ordinary project layouts rather than against its own
fixtures found one more, and it is §31's shape in its most expensive form:
advice a reader can follow exactly and still be stuck.

The classic `src/` plus `include/proj/` split builds correctly -- the
include path comes from the include *text*, per §37, so
`#include "proj/geometry.h"` found at `include/proj/geometry.h` yields
`-Iinclude`. That logic is `incdir_for`, whose docstring says plainly that
the containing directory "is the obvious answer and wrong whenever an
include carries a path", and cites a project that lost 84 files to exactly
that.

**The diagnostic had its own copy of the question, and got it wrong.**
Where the resolver *declines* to guess, it offers a remedy:

```
proj/math.h is on no include path here
it is in this tree, at include/proj/math.h
[project] include-dirs = ['include/proj'] would find it     <- does nothing
```

`-Iinclude/proj` resolves `math.h`, not `proj/math.h`. Following that line
verbatim leaves the build failing in exactly the same way. The two share
one function now.

**Reaching it needs no contrivance.** The resolver refuses to guess from a
basename the toolchain owns, so a project carrying its own `math.h` -- or
`time.h`, or `error.h` -- lands here rather than being resolved. The guard
is working correctly and handing the reader a wrong answer.

The case that already covered this diagnostic could not have caught it:
every include in it was unqualified, and for those the containing
directory and the resolving directory are **the same string**. The fixture
was too easy in precisely the way §116 describes, and the assertion passed
whichever answer the advice named.

### The sweep the last three findings suggested

§92 enumerated the twenty-five messages that offer a remedy and asked
whether each pointed at the right *kind* of thing. Three later findings --
the `nm` identity, who chose a moc, the include directory -- were a
different question it did not ask: **which messages compute a value rather
than echo one**, and does that computation agree with the code that
actually decides? A message quoting a path cannot drift. A message
deriving an answer has a second copy of a rule.

Two came out of asking it deliberately.

**The `[target.*]` stanza was never pasted back.** §20's dead-end remedy
hands over a whole config section with computed membership -- the richest
advice in the tool -- and the case checked that it was *printed* and named
the right files. Nothing checked that pasting it ends the ambiguity. It
does; the case now takes the text fmake actually emitted, writes it to
`fmake.toml`, and requires both programs to build **and to return 0**,
which each does only when it linked its own `win()`. A stanza that
resolved the ambiguity to one file for both targets would build happily
and fail that.

Using what fmake printed rather than a hand-written copy of what it ought
to print matters: the other way tests the case's opinion of the rule
instead of the tool's.

**The missing-header advice guessed where the resolver had refused to.**
The resolver declines a basename that more than one file answers -- which
is *why* the compile failed -- and the advice then picked the shortest
path and stated it as the location:

```
gizmo.h is on no include path here
it is in this tree, at beta/gizmo.h        <- one of two, silently chosen
```

Two `gizmo.h` in a tree is an ordinary shape, and a reader following that
lands on `beta` when they may have wanted `alpha/deep`, with nothing
saying a choice was made. It names every candidate now, each with the `-I`
that would find *it*, and says that having more than one is why nothing
resolved:

```
2 files in this tree could be it, which is why it was not resolved:
    beta/gizmo.h         [project] include-dirs = ['beta']
    alpha/deep/gizmo.h   [project] include-dirs = ['alpha/deep']
```

The single-candidate message is untouched, which the case asserts -- the
fix must not cost the exact answer in the common case.

**The rule this leaves behind.** Where the tool refuses to choose, the
advice must not choose either. Refusing and then quietly guessing in the
sentence that explains the refusal is worse than either, because it reads
as a fact and is a coin toss.

### What the cases had to do

Two of these fixes are refusals or additions that a lazy version would
satisfy. The mutation that makes the moc probe answer *yes* to everything
passes every positive assertion and is caught only by the requirement that
an ordinary Qt failure still gets the ordinary advice. **When the change
is a refusal, the test that earns its keep is the one that checks what
still gets through.**

---

## 114. The lead §79 declined to act on was real

§79 profiled a slow build on hydra, found `cProfile` pointing at
`close_over_symbols` -- 2.64s across 76,010 calls to `builtins.any` -- and
**deliberately did not act on it**. The reasoning was good: §26 is about
that instrument pointing precisely at the wrong thing, `cProfile` charges
per-call overhead, and a cheap function called 76,010 times is what it is
built to over-report. It also wrote down how to settle the question:
short-circuit the suspected work and time the whole program with a
stopwatch, with enough repetitions to see past the noise.

Done, and the suspicion was right.

### What the scan was

Three linear scans over the link set, not the two §79 named:

```python
if any(sym in o.strong for o in linked)                       # per symbol
if any(sym in o.weak for o in linked)                         # per symbol
if not any(sym in o.strong or sym in o.weak for o in linked)  # per external
```

`linked` is the thing that grows, so the work is quadratic in exactly the
dimension that gets bigger. Two sets kept in step with it answer the same
questions by lookup. The third scan is the one §79 did not mention, and it
runs over every undefined symbol in the whole link set.

### Measured, not asserted

hydra, 121 translation units, warm cache, `--explain` so nothing compiles;
21 runs each, **with the order of the pair reversed every round** so a
systematic drift cannot land on one version:

| | min | p25 | median |
|---|---|---|---|
| scan | 0.921s | 1.065s | 1.211s |
| sets | 0.604s | 0.730s | 0.812s |
| | **-34%** | **-31%** | **-33%** |

The machine carried unrelated load, so the ranges overlap and no single
run proves anything -- which is why all three statistics are here rather
than the flattering one. They agree on a third. **The alternation matters
more than the repetitions**: §77 measured the *order* rather than the
versions and got an answer that reversed when the order did.

### The proof that it is the same closure

A speedup that changes what gets linked is not a speedup. The invariant is
that the plan is unchanged, checked rather than sampled: `--explain` on
hydra is **byte-identical** between the two versions -- 299 lines covering
the link set, the externals and the install plan, over a tree with real
ambiguity and real weak symbols in it.

### The risk it moved, and the gap already there

The invariant used to be recomputed on demand and is now maintained in
three places. Breaking it deliberately -- dropping the seeds' symbols from
the set -- **passed all 297 cases**, so the suite was not holding the rule
up. Neither was it before the change. The shape that distinguishes them is
specific enough to have been missed: the root defines a symbol, a *second*
file defines it too, and a *third* file that does get linked refers to it.
Only then does the short-circuit decide anything -- and without it the
closure reports an ambiguity that is not one and refuses to build a tree
that is fine. A correct message about a false problem, which is the
expensive kind. A case pins it now.

### The same method again, on what was left

With the scans gone, a warm `--explain` on hydra profiles to something
else entirely: `object_key`, and inside it 93,478 calls to
`os.path.relpath` and 97,797 to `os.stat` across 183 objects. A depfile
names every header its object saw, so the same Qt header is turned into a
relative path once **per object that includes it** -- a few thousand
distinct paths, ninety-three thousand calls.

`relpath` is pure and `root` is fixed for a run, so one dict answers it:

| | min | p25 | median |
|---|---|---|---|
| plain | 0.560s | 0.733s | 0.738s |
| memoised | 0.422s | 0.561s | 0.580s |
| | **-25%** | **-23%** | **-21%** |

Byte-identical `--explain`, same alternating stopwatch, and the memo keyed
on `(root, dep)` rather than `dep` -- measured as costing nothing over the
faster string key, so the assumption that a process only ever has one root
is removed rather than relied on.

**`hash_of` was left alone, and that is the interesting half.** It is the
same shape -- 97,797 stats for the same few thousand files -- and a
per-run memo would be wrong: generators write moc and uic output *during*
a build, so a file hashed before and after would return the stale answer.
The cheap win and the wrong win look identical in a profile, and the only
thing separating them is knowing when the tree changes under you.

### What this says about §79's caution

Nothing bad. The reason to distrust the profiler was sound and remains
sound; what changed is that the claim was settled with the instrument that
can settle it. **A suspicion recorded honestly as a suspicion is what made
this cheap to finish** -- the alternative is not "act on the profiler", it
is "the lead is lost".

---

## 115. What deliberately stupid input found

A sweep: empty trees, binary sources, broken TOML, symlink loops, absurd
filenames, paths where a name was documented, things that are not files.
Twelve shapes to start with, asking only whether fmake *reported* rather
than tracebacked. **Four bugs, none of which came from thinking about the
code**, and a list of things now known to be fine.

### A traceback on any source that is not UTF-8

Every file fmake reads is opened with `errors="replace"`, in five places,
because a tree is allowed to contain whatever it contains. Every
subprocess it ran decoded strictly. **gcc quotes the offending source line
back at you**, so a diagnostic about a line that is not UTF-8 is not UTF-8
either -- and Python raises `UnicodeDecodeError` from inside
`communicate()`, killing fmake with a traceback naming subprocess
internals while it holds the compile error it was about to print.

```
int main(void){ int caf<e9>_count = 0; return caf<e9>_count; }
```

Latin-1 is not exotic; it is most C written before about 2005 with a
person's name in it. Random bytes named `.c` fail identically, because the
cause is the decode rather than the file.

**The rule was known and applied on one side only.** Fourteen call sites,
one substitution -- and since the change is mechanical it carries a proof
rather than a reading: undoing the substitution must reproduce the
original byte for byte. A reviewer reading a sample of fourteen
near-identical hunks proves nothing about the fifteenth.

The case checks more than the absence of a traceback, because a fix that
discarded the compiler's output would satisfy that: the diagnostic itself
has to survive `-v`. **The obvious assertions here are all satisfiable by
making things worse.**

### A name in a comment that was a path

`@target NAME` is documented as a name in both README and §7, and `-o` is
how output moves elsewhere. Nothing checked it:

```
@target ../../ESCAPED        built outside the tree
@target /tmp/ABSOLUTE        built at an absolute path, tree ignored
```

Surprising, and no worse than surprising until the install side, where the
name is joined onto the destination exactly as written:

```make
install -m 755 ../../ESCAPED $(DESTDIR)$(BINDIR)/../../ESCAPED
```

That leaves the prefix and **leaves a staging root** -- `DESTDIR` being
the mechanism every Debian build depends on to keep an install inside the
package being built.

**Not a security boundary**, and claiming one would be theatre: `@rule`
runs recipes exactly as make does, so a tree you build is a tree you have
already trusted to run commands. The property is smaller and worth having
anyway: what a comment says is a name is a name. fmake already refused a
target that would overwrite a directory, from the same instinct, and this
guard goes beside it. Both routes to the field are covered.

### Two ways to never return

`os.walk` lists everything that is not a directory, and `walk_tree`
filtered on the extension alone:

```
a FIFO named blocks.c        open() blocks until somebody writes
/dev/zero as endless.c       read() never stops producing
```

Neither of these fails. fmake **never returned** -- no output, no error,
no exit status, nothing to act on, which is the worst shape a build tool
has, and it took a named pipe in a directory to reach.

`isfile()` alone was the wrong fix, and **the suite said so**: a dangling
symlink is not a file either, and `odd_trees_do_not_crash` exists because
one of those once raised `KeyError`, carrying the report that replaced the
crash as its assertion. A broken link is somebody's mistake and gets
named; a FIFO is not a source at all and does not:

```
dangling.c   -> exists() is False -> passes through, reported by name
blocks.c     -> exists() is True  -> skipped, named under -v
```

A guard written for one shape swallowed a neighbouring one, and only a
case that already knew the difference caught it -- on the last full run
before the commit, not on any of the targeted ones.

**The suite could not have caught the hang, because it would have hung
too.** `Tree.fmake()` ran `subprocess.run` with no timeout, so a case
reaching either shape stopped the whole run: no result, no name, and in CI
a job burning until the runner's limit with nothing saying which case did
it. The bound belongs inside, which is what
`~/.claude/guidelines/running-code.md` requires -- a wrapper only guards
the way somebody happened to run it. `FMAKE_TIMEOUT = 300` turns a hang
into a failing case that names itself -- `FAIL
something_that_is_not_a_file_is_not_a_source / fmake did not return within
300s` -- verified by removing the guard and watching it come out. No invocation legitimately approaches it; the
slowest *whole case* measured 77s with the pool saturated.

### A clean rule that left its own tree

After `@target`, the question was whether any other field naming a path
could escape. Three were sound, and are recorded so nobody re-derives
them:

| | |
|---|---|
| `@headers ../outside.h` | installs by **basename**, so nothing leaves `$INCLUDEDIR`. Staged into a `DESTDIR` and listed: five files, all inside it. |
| a generator writing outside | arbitrary shell, exactly as a Makefile recipe is. Same trust class as make, by design. |
| `fmake --clean` | already refuses anything above the root, and refuses to follow a symlink out. |
| an interrupted build | the cache entry is written only after a compile succeeds *and* `nm` reads it, so a kill leaves none and the next build recompiles. Checked with `SIGTERM` mid-compile. |
| two builds at once | `.fmake/lock`; one waits, then reports up to date, cache consistent. |
| `--uninstall` | removes exactly the files its own plan named, leaving foreign files in the same directories alone -- and removes a *symlink* rather than what it points at, so an installed path replaced by a link out of the prefix costs the link and nothing else. |

**The ejected Makefile was the odd one out**, removing a file two
directories up that `fmake --clean` would not touch. Both halves had been
true for a while and nobody had put them side by side -- and the comment
on fmake's own clean *asserts* the two are consistent, which is what made
it worth going to look rather than reasoning about. **A comment claiming
two things agree is a place to test, not a place to trust.** This one had
been true when written.

What is guarded is deleting, not building: a generate rule naming an
outside output is an instruction and its build rule stays. Dropping it
from `CLEAN` *silently* would then be the shape a stale artifact hides in,
so the eject names the file — and an ordinary tree is required to stay
silent, since a note printed unconditionally satisfies every assertion
that it was printed.

**ninja is the same question with a different answer.** `ninja -t clean`
removes the file too, but that is ninja's own tool over the outputs the
build file declares, and an output *has* to be declared to be built. There
is no rule of fmake's to withhold, so the backends genuinely differ and
the difference is stated at eject time. Making them agree would mean
either not building the file or not declaring it, and both are worse than
a sentence.

### Why it was worth doing

Three bugs, one hang class, and five negative results in an afternoon --
and **the negative results are half the value**, because the next person
to wonder about `@headers` and `DESTDIR` has the answer and the command
that produced it.

It also found two things that are not about hostile input at all, and they
are in §113 with the rest of their family: pointing the tool at ordinary
project layouts, and then at its own advice, turned up the same defect the
sweep kept finding by accident.

---

## 116. Claims that nothing was checking

The last of the sweep turned inward, on properties this project had
already decided were important and left unasserted. Three levels of the
same defect, in increasing order of how well hidden they are.

### A promise the packaging makes

§44 checks that fmake runs on the Python it declares. The same line of
`debian/control` makes a second promise:

```
Depends: ${misc:Depends}, python3 (>= 3.11)
```

python3 **and nothing else**, so an `import yaml` fails in exactly the
shape the PEP 701 bug did -- installs, satisfies its dependency,
configures, dies at the first line on a machine that happens not to have
it. It is also the README's first claim about the tool.

`sys.stdlib_module_names` settles it **with no list to maintain**, which
matters here: §15 counts three hand-written lists as load-bearing and says
a fourth would be the signal that the model wants a predicate. This needed
none. Where the declared interpreter is installed it is asked for its own
set, since the running one would accept a module added to the stdlib after
3.11 -- the same preference §44 states, the old interpreter saying so
beating an inference about what it would say.

### A claim the case's own docstring makes

`--run` was swept the same way and holds up: exit status forwarded,
arguments reaching the program, stdin its own, a compile error under a
shebang still naming line 3, an unwritable directory building in a cache
elsewhere, a script calling a second file getting it from the closure.
Two of those were asserted **in the prose explaining why the case exists**
and checked by nothing.

**Arguments only matter when they are fmake's.**
`a_c_file_runs_as_a_script` passed `one two`, which would survive any
parser ever written. The interesting
ones are `--help`, `--explain`, `-v` -- and a regression there does not
fail, it prints fmake's own help and exits 0, a plausible thing for a
build tool to do and completely wrong for an interpreter.

**The exit status cannot tell exec from wait.** The docstring says fmake
execs rather than waits, so it is not sitting between the program and the
shell; the assertion under it was the exit status, which
`sys.exit(subprocess.run(...).returncode)` forwards identically. What
differs is everything else: a signal kills fmake and orphans the program,
job control addresses the wrong process. The kernel settles it -- after
exec the pid is unchanged, so `/proc/<pid>/cmdline` is evidence rather
than inference:

```
['/tmp/.../ready.c']                      exec'd -- the pid is the program
['python3', '.../fmake', '--run', ...]    the mutation, waiting on a child
```

### A test whose inputs were too easy

The third level, and the quietest: not an unchecked claim but a checked
one whose fixture could not exercise it. `one two` as arguments, a
`DW_AT_location` count on a seven-line function, a gate over an empty file
list. All report success exactly as loudly as a real pass.

**A docstring that argues for a property is the best place to look for an
untested one**, because somebody has already decided it matters and then
written the easy assertion instead of the hard one.
