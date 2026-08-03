# Qt in fmake — an assessment

Written from the outside, after trying to answer whether hydra (a Qt 6 Widgets
browser, 61 sources, 54 executables) could be built by fmake. It cannot today.
The interesting part is *why not*, because the missing piece is small and the
piece that would normally be hard is already built.

**What this is not.** fmake was never run. Everything below about fmake comes
from reading `fmake` and `project.md`; everything about Qt comes from hydra,
where the numbers were measured. Where a claim is inference rather than
observation it says so.

---

## 1. The blocker is moc, and it is the whole blocker

Qt's meta-object compiler reads a header, finds `Q_OBJECT` in a class body, and
writes a `moc_foo.cpp` implementing the signals, the introspection and the
`QObject` plumbing that class promised. Without it, every class that declares
`Q_OBJECT` fails to link on `staticMetaObject`, `qt_metacall` and `metaObject`.

Hydra has **43 headers** with `Q_OBJECT` and two `.qrc` resource files. So the
gap is not "some Qt projects need this" — it is every Qt project that defines a
class of its own.

`[generate.*]` can drive moc today, and that is not a real answer: it takes
explicit `inputs`/`outputs`, so it means 43 hand-maintained stanzas, and worse,
adding `Q_OBJECT` to a header fails at *link* with an undefined symbol until
somebody remembers to add the 44th. That is a discovery problem solved by
remembering, which is the kind of thing this tool exists to abolish.

---

## 2. Why `Q_OBJECT` is fmake's kind of fact

Every other build system makes Qt-ness a *declaration*: qmake wants `QT +=` and
a `HEADERS` list, CMake wants `AUTOMOC ON` and a target to hang it on. fmake's
premise is that the source already says what it needs — `main()` at file scope
means a program, an undefined `SDL_Init` means SDL is called.

`Q_OBJECT` is exactly that: an unambiguous, machine-readable token in the source
saying *this class needs a generated companion*. It is not a hint, not a
heuristic, and not ambiguous the way `#include <SDL.h>` is ambiguous. It sits in
the same category as the facts `scan_source` already collects.

The trigger is also cheap in the place it belongs. `scan_source` (fmake:294)
already strips comments and string literals, then asks
`"has_main": bool(RE_MAIN.search(code))`. `has_qobject` is the same line against
the same stripped text — and stripping first gets you, free, that a `Q_OBJECT`
in a comment or a string does not count, which is the same reason §3's
`main()` detection strips first.

Headers are already walked (`HDR_EXTS`, fmake:136) and already scanned through
the same hash-keyed cache (`Cache.scan`, fmake:1544), so a header that *gains*
`Q_OBJECT` re-scans on its next build without anything being told.

---

## 3. The part that would be hard elsewhere is already done

This is the argument, and it is worth being precise about.

**moc output is a file that nothing `#include`s.** No source names
`moc_foo.cpp`. That is exactly why moc is painful in hand-written Makefiles and
why fuzzypickles' own `gui/Makefile` gives up and delegates to qmake6: an
include-graph-driven build cannot see the file, so somebody has to list it.

**fmake does not decide link sets from the include graph.** It compiles, reads
symbol tables with `nm`, and takes the transitive closure over undefined
symbols (§3). And the relationship here is a *symbol* relationship:
`foo.o` has `Foo::staticMetaObject` **undefined**, because the class's vtable
references it. `moc_foo.o` **defines** it.

So the existing closure links the moc object for exactly the classes that are
actually reachable, with no new mechanism, no new metadata, and no special case.
Two consequences worth stating:

- **It is more correct than qmake.** qmake mocs and links everything listed in
  `HEADERS` whether the class is reachable from that binary or not. The closure
  links what is used. For a tree of many small programs over one shared body of
  Qt code that difference is the whole ballgame — see §7.
- **A `Q_OBJECT` class nothing constructs costs nothing.** Its moc object is
  generated and never linked, which is the right answer and falls out.

*Inference, not observation:* I did not confirm against fmake's symbol
classifier that C++ mangled names round-trip cleanly through
`nm --format=posix` here. The closure is described as exact for C; mangled
symbols are still just strings, so I expect it holds, but that is the one link
in this chain I did not check.

---

## 4. What it would take

Roughly, and in fmake's own terms:

1. **`scan_source` gains one field.** `RE_QOBJECT` matching `Q_OBJECT` or
   `Q_GADGET` in the stripped code; `"has_qobject": bool(...)` in the returned
   record beside `has_main`.
2. **An implicit generate rule per flagged header.** `moc $in -o moc_$name.cpp`,
   emitted into the object directory. §"Generated sources" says the generators
   run before `walk_tree` and that this needed no second scanning pass — moc
   fits that shape exactly, since its output is an ordinary C++ source
   afterwards.
3. **Nothing else.** The closure, the symbol handling and the caching are
   unchanged. This is the claim I would want to falsify first, because it is the
   one that makes the feature cheap.

The rebuild story also falls out of what exists: moc output is keyed by the
header's content hash like every other scan, so touching a header re-mocs it and
recompiles only the objects whose symbols moved.

---

## 5. `rcc` rides the same rail; `uic` does not

**`.qrc` → `rcc`** works for the same reason moc does. `rcc` emits a source
defining an initialiser that `Q_INIT_RESOURCE(name)` references, so the
undefined symbol is in the object that uses the resource and the closure pulls
the generated object in. Trigger: a `.qrc` file in the tree.

**`.ui` → `uic` is different, and should probably be left out.** `ui_foo.h` *is*
`#include`d by the code that uses it, so it is an include-graph dependency
rather than a symbol one — a header that must exist before scanning, not an
object discovered after compiling. That is a different mechanism for a much
smaller reward: hand-written Qt Widgets code frequently has no `.ui` at all, and
hydra has none. Supporting moc and rcc while saying plainly that `.ui` is out of
scope is a more honest position than half-supporting all three.

---

## 6. Where symbol inference stops

Two walls, and both are the same wall from different sides. Worth writing down
because they bound the feature rather than block it.

**Compiler flags are not implied by symbols.** Qt needs `-fPIC`, `-std=c++17`
and per-module include directories, and it spreads its symbols over a dozen
`Qt6*` libraries. No undefined symbol implies `-I/usr/include/qt6/QtWidgets`.
This is a `pkg-config Qt6Widgets` question, and I would take the flags from
there rather than try to infer them — the same way `cmocka.h → cmocka`
(fmake:2007) is a table rather than a deduction.

**Conditional compilation is not a link question at all.** Hydra has three
optional dependencies, and each is a `-D` before it is a `-l`:
`HYDRA_HAVE_SODIUM` decides whether the KeePassXC code *exists*, so when
libsodium is absent there is no undefined `crypto_box_easy` to infer from —
there is no call, because the call was never compiled. Symbol inference answers
*what do I link*; it cannot answer *what do I compile*. Any project with a
"feature present or absent" axis needs a probe-then-define step that is outside
fmake's core rule.

Neither of these is an argument against moc. They are an argument for scoping
the Qt story as "fmake generates what Qt's tooling generates" and not "fmake
configures Qt".

---

## 7. Where the payoff actually is

**Highest** for a tree of many small programs sharing one large body of Qt code.
Hydra's tests are the archetype: 21 live drivers, each a single `.cpp` with
`main()`, each linking most of a 61-source Qt shell. fmake would discover all 21
programs with no build file, compile each source once, and link each program's
closure.

**Lowest** for a single Qt application with a `.pro`-shaped layout — one target,
one source list. qmake is already fine there and fmake would not be a win.

That is a real niche rather than a general Qt story, and I would say so in the
README. *"fmake builds Qt"* sets the wrong expectation; **"fmake builds trees of
Qt programs without a build file"** is both true and the more interesting
claim — because it is the case the existing tools handle worst.

---

## 8. The measurement that prompted this

From hydra, and the reason the point above is not theoretical. Its 21 live
drivers each listed the app sources, so CMake gave each its own object directory
and compiled all 58 into it — about **1200 compilations of the same files**:

| | wall | CPU |
|---|---|---|
| a target per driver, sources listed per target | 19m 17s | 41m 15s |
| one shared static library, drivers link it | **6m 57s** | **13m 30s** |

2.8× on the clock and 3.1× on the machine, and the fix was to stop compiling the
same source 21 times. **fmake would never have compiled it twice**, because
"compile each translation unit once, link the closure per program" is what it
does by construction — the same reason a static archive was the right answer
here and an OBJECT library was not.

That is the strongest practical argument for the feature: this was a real
inefficiency in a real project, it survived a long time because nothing made it
visible, and fmake's model makes it structurally impossible rather than merely
findable.

---

## 9. What I did not check

- fmake was never run, on hydra or anything else.
- Whether `nm --format=posix` output for C++ mangled names flows through the
  symbol classifier as cleanly as C does (§3).
- Whether moc's generated source has any include-order requirement that would
  break "generate first, then it is an ordinary source" — I believe not, since
  `moc_foo.cpp` includes `foo.h` itself, but I did not verify it against a real
  moc invocation.
- Whether `--eject` would need to learn moc rules, or whether emitting the
  already-generated sources as ordinary ones is enough. The second seems likely
  and is the cheaper contract.
