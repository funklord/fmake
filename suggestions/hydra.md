# Suggestions from re-evaluating fmake against hydra

Written while re-evaluating fmake for `hydra`, a Qt Widgets browser. An
earlier assessment from the same project argued that moc was the whole blocker
and that fmake's model made it cheap; that became section 17 of `project.md`
and is done. This is what is left, from the same project a while later.

**Read the honesty note first**: unlike the sibling situ evaluation, which was
done by writing schemas and compiling them, **this one is documentation-based.
fmake was not run against hydra.** Everything below is therefore a question or
a suggestion rather than a measurement, and the last section says what it
would take to turn it into one.

## What hydra looks like now

Relevant because section 17's payoff argument was measured against an earlier
shape of this tree, and the shape moved:

- 58 app sources built into a **static library** that the app and every test
  driver link. That change was made partly on the strength of section 17's
  own reasoning and cut `make drivers` from 19m17s to 6m57s. The 1200-
  compilations figure quoted there is therefore historical -- the waste it
  describes was real and is now gone by other means.
- **28 test binaries and 26 live drivers**, globbed rather than listed.
- Four optional dependencies discovered by pkg-config -- libsecret, libsodium,
  liblz4, libtorrent -- each of which changes what compiles.
- A generated `.qrc` (`configure_file` writes it into the build directory),
  Qt WebEngine, and an Android build that produces a shared library loaded by
  a Java launcher rather than an executable.

## Suggestions

### 1. The optional-dependency case deserves a worked example

`@pkg NAME [OP VER]` exists and handles the ordinary case. What hydra does is
one step past it: **a dependency that is optional changes the source**, via

    if(PkgConfig_FOUND AND NOT ANDROID)
        pkg_check_modules(SECRET libsecret-1)
    endif()
    ...
    target_compile_definitions(hydra PRIVATE HYDRA_HAVE_SECRET)

and the code is `#ifdef HYDRA_HAVE_SECRET`. So the question is not "can fmake
find libsecret" but "can fmake define a macro *because* it found libsecret, and
leave it undefined otherwise, without a build file". That is the pattern every
optional dependency in every C project uses, and I could not tell from
`project.md` whether `@pkg` covers it or only the found case.

If it does, an example would sell it. If it does not, something like
`@pkg_optional libsecret-1 defines HYDRA_HAVE_SECRET` is the smallest form
that would cover it, and it stays inside the "annotation in a comment" model
rather than becoming a build file by another name.

### 2. Say what happens to a generated source

Hydra's CMake writes a `.qrc` into the build directory and compiles it. fmake
builds from "an unannotated tree", and a tree with a file that does not exist
until something generates it is the boundary of that idea. Two things worth
stating outright in `project.md`:

- whether a source appearing in the build directory rather than the source
  tree is picked up at all;
- and whether fmake will *run* a generator, or whether the answer is "generate
  first, then run fmake", which is a perfectly good answer and cheaper to
  document than to implement.

The moc work already crossed this line once -- fmake runs moc and links the
output -- so the question is really where the line now sits, and a reader of
section 17 will assume it sits further out than it does.

### 3. Android is where "no build file" stops, and that should be said

Hydra's Android build is `qt-cmake` plus `androiddeployqt` plus Gradle,
producing an `.apk` from a shared library, a manifest, three Java sources and
a version code fed in from the project version. None of that is a compile-and-
link problem and none of it is fmake's business.

That is not a gap, but it does mean **fmake cannot be hydra's only build
system**, and a project weighing adoption needs to know that early rather than
after porting the desktop half. A sentence in the Qt section -- "moc and Qt
libraries on the desktop; Android packaging is androiddeployqt's and stays
that way" -- sets the expectation correctly and costs nothing.

### 4. The deb machinery is better than the one I wrote this week, and it is invisible

`fmake`'s own `make deb` runs `lintian`. Hydra's, written this week, does not,
because lintian is not installed on the machine and I did not notice fmake had
already solved the problem next door. Hydra's version computes `Depends:` from
the binary with `dpkg-shlibdeps`, which fmake may or may not do.

Two projects in the same tree now have hand-written Debian packaging with
different amounts of rigour. That is exactly the duplication the harmonization
guidelines describe, and it is not for either project to resolve alone -- but
fmake is the natural place for it to end up, since it is the one that already
builds and installs other people's programs.

Worth raising as its own cross-project question: **should fmake package, as
well as build?** Not a feature request. If the answer is no, hydra and the
others should copy fmake's `debian/` shape deliberately rather than each
inventing one.

### 5. What would turn this into a measurement

The honest way to finish this evaluation is to run fmake on hydra's `src/` with
Qt found, and compare:

- what it decides to compile against the 58 files CMake compiles;
- whether the static-library shape survives, or whether "compile each TU once,
  link the closure per program" makes the archive unnecessary -- section 17
  claims it would, and hydra is now the tree that could check it;
- and what `--explain` says about the test drivers, which are the case section
  17 says existing tools handle worst.

That is a bounded afternoon and it is the thing that would either retire the
question or make the case properly. It was not done here, and this file should
not be read as though it had been.
