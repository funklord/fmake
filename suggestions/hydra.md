# Suggestions from running fmake on hydra

Written from `hydra`, a Qt Widgets browser. An earlier assessment from the same
project argued that moc was the whole blocker and that fmake's model made it
cheap; that became section 17 of `project.md` and is done.

**This file was speculation until fmake was actually run on the tree.** It is
now a measurement, and the measurement moved two of its conclusions. What
follows is what `fmake -C src --explain` produced against hydra's sources, and
where it stopped.

## What it got right, with no configuration at all

- **45 moc invocations**, one per `Q_OBJECT` header, matching what CMake's
  `AUTOMOC` does on the same tree. It also found `network_fetcher.cpp` -- a
  `Q_OBJECT` in a *source* file, which needs the include-the-output form rather
  than the compile-it-separately form, and it was not missed.
- **Qt's include and define set** discovered without being told: `QT_CORE_LIB`,
  `QT_WEBENGINECORE_LIB`, the mkspecs path, all of it.
- **A link set derived from symbols**, and it is *smaller* than the one hydra's
  CMakeLists names:

      -lQt6Core -lQt6Widgets -lQt6Gui -lQt6WebEngineCore -lstdc++
      -lQt6Network -lQt6Qml -lQt6WebEngineWidgets -lQt6WebChannel -lgcc_s

  with three declined, each declination naming the header that suggested it:

      (not linked)  ... suggests Qt6Concurrent, but no symbol needs it
      (not linked)  QDBusConnection at theme.cpp:14 suggests Qt6DBus, ...
      (not linked)  libsecret/secret.h at credential_store.cpp:9 suggests libsecret-1, ...

That output is the tool at its best: it names what suggested the library, and
says why it disagreed.

## Where it stops, and the second one is the interesting failure

### 1. Platform-conditional sources -- a hard blocker

`src/` holds `android_view.cpp`, `android_downloads.cpp`, `android_intents.cpp`
and `android_dialogs.cpp`. CMake adds them only inside `if(ANDROID)`. They carry
no self-guard, because the build system is what excludes them. fmake builds the
tree, so it schedules all four, and:

    android_view.cpp:12:10: fatal error: QJniEnvironment: No such file or directory

So it does not merely link something odd -- it fails. **fmake cannot build
hydra's `src/` today**, and no flag fixes it, because the question is which
files belong in this build rather than how to compile them.

The shape is not Qt-specific: every portable C project has files belonging to
one target. `#ifdef` inside the file is one answer and many projects use it; a
filename convention (`*_android.cpp`, `*_win32.cpp`) is another, and is the one
a tool can act on without being told. fmake already infers a great deal from
names. A documented suffix rule -- ignore `*_<platform>.cpp` unless building
for that platform -- would cover the common case and stay inside the "no build
file" premise. Hydra would rename four files to adopt it, cheerfully.

### 2. Optional features vanish silently, and the linker agrees

This is the one guessed at before, and only half right.

`credential_store.cpp` is `#ifdef HYDRA_HAVE_SECRET` from top to bottom.
`theme.cpp` guards its portal query with `#ifdef HYDRA_HAVE_DBUS`. Both macros
are defined by CMake *after* `pkg_check_modules` finds the library. fmake does
not know they exist, so it compiled both files with them undefined, so the
bodies vanished, so no symbol needed the libraries, so fmake **correctly**
declined to link them.

Every step is right and the result is wrong: a browser with no keyring
integration and no desktop colour-scheme detection, built without a warning,
because the evidence fmake reasons from -- symbols in objects -- is downstream
of the decision it could not see.

The `(not linked) ... but no symbol needs it` line is the only trace. Two
things would help, in increasing order of ambition:

- **Distinguish the two reasons a discovered library gets dropped.** "This
  header suggested a library the code does not use" and "this header sits
  behind a preprocessor conditional that was false" are different findings.
  fmake can tell them apart cheaply -- it has the include, and it knows whether
  the include survived preprocessing. The second deserves a warning, not a note
  inside `--explain`.
- **A form for "found means defined".** Something like
  `@pkg_optional libsecret-1 defines HYDRA_HAVE_SECRET`: one annotation
  covering the pattern that every optional dependency in every C project uses,
  and it stays a comment rather than becoming a build file.

Without one of these, fmake's answer for any project with optional features is
"it builds, and quietly does less than it should" -- which is worse than
refusing.

### 3. A trivial one: the binary is named after the directory

`fmake -C src` produced a program called `src`. `-p NAME` fixes it and the
default is defensible. Worth noting only because running it on a subdirectory
is the first thing anyone does.

## What the measurement did not settle

Section 17 claims fmake would make hydra's static library unnecessary --
"compile each TU once, link the closure per program" -- and hydra is the tree
that could check it, with 28 test binaries and 26 live drivers that each want
the app sources. **That claim is still unverified**: the build fails at (1)
before reaching a link, and the tests live outside `src/` in a layout fmake was
not pointed at.

It stays the most interesting open question between fmake and this project, and
the honest position is that the 19m17s-to-6m57s figure quoted in section 17 was
hydra solving that problem with an archive, not fmake solving it.

## What would finish it

1. Guard or rename the four Android sources -- hydra's side, cheap.
2. Pass the feature macros by hand via `--cflags` and confirm the link set then
   picks up libsecret and Qt6DBus. That would prove the mechanism is sound and
   the *inference* is the only gap.
3. Point fmake at the tests and compare its closure against the 28 binaries
   CMake builds.

Steps 2 and 3 are an afternoon, and they are what turns "fmake can read this
tree" into "fmake can build it".
