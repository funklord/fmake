# fmake does not need a build system, and this is not one. It exists so that
# `make install` and `make deb` mean what everyone expects them to, and so
# debhelper has the target it looks for. The program is a single script; all
# `install` does is copy it and its manual page into place.
#
# TARGETS
#   make               -- write the manual page and the bash completion, both
#                         produced by fmake itself so neither can go stale
#   make test          -- ./selftest: build real trees and check what fmake
#                         decided about them
#   make check         -- the three checks, the style gate and the suite;
#                         the one to run before a commit
#   make style         -- the shared source gate, plus project.md held to the
#                         tree it describes
#   make version-check -- VERSION, the literal in the script and
#                         debian/changelog all state one number; hold them to
#                         each other
#   make install-check -- install and uninstall name the same three files,
#                         and each arrives with contents: install into a
#                         scratch DESTDIR and fail if uninstall leaves
#                         anything
#   make hooks-check   -- `hooks' installs a hook, and says so only when it
#                         did: run it against a scratch repository both ways
#   make install       -- install the script, its manual page and its
#                         completion under PREFIX
#   make uninstall     -- remove what install put there
#   make deb           -- build the .deb into BUILD_DIR
#   make lint          -- build it, then run lintian over it where lintian
#                         is installed
#   make hooks         -- install the git hooks from tool/hooks/
#   make clean         -- remove the generated files and the package
#   make veryclean     -- clean, plus the build directory
#   make distclean     -- veryclean, plus stray editor files
#   make help          -- this list
#

PREFIX  ?= /usr/local
DESTDIR ?=

# Where build products land. dpkg-buildpackage writes to the parent
# directory, which is not this build's to write to: with two of these
# projects side by side in ~/src, `make deb` in one drops files into the
# directory holding the other. They are moved here afterwards, which also
# lets clean name them.
BUILD_DIR  ?= build

# Where the finished packages land. `dpkg-buildpackage` writes to the PARENT
# directory, so they have to be moved somewhere regardless; this names it.
#
# A `deb/` subdirectory of the build tree rather than the build tree itself,
# which is what five of the ten packaging projects already did and is now the
# settled answer. Two reasons beyond consistency: it keeps a set of artifacts
# separable from object files, so `ls` and `clean` can both speak about them
# by name; and it is the only spelling that still works when BUILD_DIR is `.`,
# as openmlx4 sets it, where the build tree and the source tree are one.
DEB_DIR ?= $(BUILD_DIR)/deb

# Read rather than restated. Two hand-edited copies of a version number
# drift, and the symptom is a package whose reported version disagrees with
# the one that installed it.
# The one place the version is stated. The script carries a literal rather
# than reading this file: fmake is one file and stdlib only, so it cannot
# depend on something beside it at runtime. version-check holds the three in
# step instead.
VERSION     = $(shell cat VERSION)
DEB_VERSION = $(shell sed -n '1s/^[^(]*(\([^)]*\)).*/\1/p' debian/changelog)
DEB_ARCH    = $(shell dpkg-architecture -qDEB_HOST_ARCH 2>/dev/null)

DEB         = $(DEB_DIR)/fmake_$(VERSION)_all.deb
DEB_EXTRA   = $(BUILD_DIR)/fmake_$(VERSION)_$(DEB_ARCH).buildinfo \
              $(BUILD_DIR)/fmake_$(VERSION)_$(DEB_ARCH).changes

# The interpreter written into the installed copy. Debian Policy 10.4 wants
# an absolute path, and every packaged Python script on a Debian system has
# one. The file in the repository keeps /usr/bin/env, because copying it
# into $PATH and running it anywhere is the other half of what fmake is, and
# that half wants the lookup.
PYTHON  ?= /usr/bin/env python3

BINDIR  = $(DESTDIR)$(PREFIX)/bin
COMPDIR = $(DESTDIR)$(PREFIX)/share/bash-completion/completions
MANDIR  = $(DESTDIR)$(PREFIX)/share/man/man1

# A recipe that redirects into its own target has already created the file
# by the time it fails: the shell opens `> $@' before the program runs. Both
# generated files are written that way, and without this line make leaves
# the truncated output in place -- which is NEWER than the script that
# makes it, so the next `make' reports nothing to do.
#
# Measured, with the script left unexecutable so the generation fails and
# its mtime does not move: `Error 126', a zero-byte `fmake.1', and then a
# second `make' that built only the completion and exited 0. `make install'
# would have shipped the empty manual page. Not `make deb', which cleans
# first -- measured too, and the reason install-check runs in the package
# build is a different one, stated in debian/rules.
#
# One declaration rather than a `mv' dance in each recipe, because it also
# covers the next rule somebody writes.
.DELETE_ON_ERROR:

.PHONY: all install uninstall check version-check install-check hooks-check deb lint clean test veryclean distclean style style-source style-docs hooks help

all: fmake.1 fmake.bash

# Generated by fmake itself, so the option list cannot drift from the one
# argparse accepts.
fmake.1: fmake
	./fmake --man > $@

# Generated for the same reason the manual page is: a second list of flags
# is one that goes stale, and a completion is where nobody would notice --
# a stale one offers a flag that no longer exists and omits the one you
# wanted, and neither is an error.
fmake.bash: fmake
	./fmake --completion bash > $@

install: fmake.1 fmake.bash
	install -d $(BINDIR) $(MANDIR) $(COMPDIR)
	sed '1s|^#!.*|#!$(PYTHON)|' fmake > $(BINDIR)/fmake
	chmod 755 $(BINDIR)/fmake
	install -m 644 fmake.1 $(MANDIR)/fmake.1
	install -m 644 fmake.bash $(COMPDIR)/fmake

uninstall:
	rm -f $(BINDIR)/fmake $(MANDIR)/fmake.1 $(COMPDIR)/fmake

# `install' names three files and `uninstall' names them again, and until
# this target nothing compared the two lists. The failure that argues for
# it is in the suite already, about the trees fmake builds rather than
# about fmake: hydra's icons went unseen for eleven days when a rename
# pass spelled `icons' singular, because the install line and the rm line
# are two statements of one fact kept in step by hand.
#
# Behavioural rather than textual: install into a scratch DESTDIR, run
# uninstall over the same one, and fail if anything is left. A fourth file
# added to `install' and forgotten in `uninstall' is then a red `make
# check' rather than a file that outlives the package. Parsing the recipes
# would be a second thing to be wrong.
#
# All three installed files are required to be non-empty, not just the
# program. A zero-byte manual page is what a failed `./fmake --man > $@'
# used to leave behind -- see .DELETE_ON_ERROR above, which stops it being
# produced; this is the artifact check that catches it however it arose.
#
# The directory is this tree's own `build/' so that `clean' already owns
# it, and it is removed here on both paths rather than left for a reader.
# It is set as DESTDIR for this target only, so BINDIR, MANDIR and COMPDIR
# name the scratch tree and the three paths are not spelled a second time
# in the check that exists to catch two spellings drifting apart. A
# target-specific variable does not reach a sub-make by itself, so each is
# passed it.
install-check: DESTDIR = build/install-check
install-check:
	@rm -rf $(DESTDIR)
	@$(MAKE) --no-print-directory install DESTDIR=$(DESTDIR) >/dev/null
	@for f in $(BINDIR)/fmake $(MANDIR)/fmake.1 $(COMPDIR)/fmake; do \
		test -s "$$f" || { \
			echo "install-check: install put nothing at $$f" >&2; \
			rm -rf $(DESTDIR); exit 1; }; \
	done
	@$(MAKE) --no-print-directory uninstall DESTDIR=$(DESTDIR) >/dev/null
	@left=$$(find $(DESTDIR) -type f 2>/dev/null); \
	 rm -rf $(DESTDIR); \
	 test -z "$$left" || { \
		echo "install-check: uninstall left files behind:" >&2; \
		printf '  %s\n' $$left >&2; exit 1; }
	@echo "install-check: three files with contents, and uninstall names them"

check: version-check install-check hooks-check style test

# `hooks' is the one target whose whole purpose is that a hook ends up
# installed, and until this check nothing asked whether its success line
# meant anything. The recipe is one continued shell -- it has to be, since
# `dir' is computed in it -- so make sees only the last command's status,
# and a semicolon before the echo turned a failed install into a printed
# success and exit 0. Measured before the fix: `install: cannot stat' on
# stderr, "commit-msg installed" on stdout, status 0, no hook.
#
# Behavioural, like install-check, and for the same reason: reading the
# recipe for a semicolon would be a second thing to be wrong. GIT_DIR is
# what makes it safe -- `hooks' asks git where the hooks live, so a scratch
# repository redirects the whole target and this tree's own hook is never
# touched. Measured rather than assumed: `GIT_DIR=<dir> git rev-parse
# --git-common-dir' prints <dir>.
#
# The sabotage is a regular file where `hooks/' must be a directory, so
# `mkdir -p' fails. That is deterministic and needs no permission games,
# and it fails a non-final command, which is the property under test.
#
# `make -n check' is not a dry run of this target. make runs a recipe line
# containing $(MAKE) even under -n, the sub-make inherits the flag and so
# compiles nothing and exits 0 -- which is the arm this check reads as a
# failure. Nothing is written, because every other line is only printed;
# the verdict is wrong. Named here rather than worked around, as ossacli
# did with the same hazard.
hooks-check:
	@rm -rf build/hooks-check
	@git init -q build/hooks-check
	@rm -rf build/hooks-check/.git/hooks && : > build/hooks-check/.git/hooks
	@if out=$$(GIT_DIR=build/hooks-check/.git $(MAKE) \
		--no-print-directory hooks 2>/dev/null); then \
		echo "hooks-check: hooks exited 0 with no hook installed" >&2; \
		rm -rf build/hooks-check; exit 1; \
	 elif [ -n "$$out" ]; then \
		echo "hooks-check: hooks announced an install that failed:" >&2; \
		printf '  %s\n' "$$out" >&2; \
		rm -rf build/hooks-check; exit 1; \
	 fi
	@rm -f build/hooks-check/.git/hooks
	@GIT_DIR=build/hooks-check/.git $(MAKE) --no-print-directory hooks \
		>/dev/null || { \
		echo "hooks-check: hooks failed on a repository it can write to" >&2; \
		rm -rf build/hooks-check; exit 1; }
	@test -x build/hooks-check/.git/hooks/commit-msg || { \
		echo "hooks-check: hooks installed no executable hook" >&2; \
		rm -rf build/hooks-check; exit 1; }
	@rm -rf build/hooks-check
	@echo "hooks-check: hooks installs, and fails when it cannot"

# The version is written in two files and nothing else compares them. This
# is what debian/rules runs in place of the suite: it needs no compiler, so
# the package build itself refuses to produce a mismatched pair.
# Three statements of one number: the VERSION file, which is the source; the
# literal in the script, which cannot read a file because fmake ships as one
# file; and debian/changelog, which dpkg reads and nothing else can supply.
version-check:
	@test -n "$(VERSION)" || { echo "VERSION file is empty or missing" >&2; exit 1; }
	@test -n "$(DEB_VERSION)" || { echo "no version in debian/changelog" >&2; exit 1; }
	@script=$$(sed -n 's/^VERSION *= *"\(.*\)"/\1/p' fmake); \
	 test "$(VERSION)" = "$$script" || { \
		echo "version-check: VERSION says $(VERSION), fmake says $$script" >&2; exit 1; }
	@test "$(VERSION)" = "$(DEB_VERSION)" || { \
		echo "version-check: VERSION says $(VERSION), debian/changelog says $(DEB_VERSION)" >&2; \
		exit 1; }
	@echo "version-check: $(VERSION), in step"

# Builds ../fmake_<version>_all.deb. -b because there is no upstream tarball
# to sign or ship: the packaging is native and the source is this directory.

# Separated so `make lint` works on a package already built, and skipped
# rather than fatal when lintian is absent -- it is a checker, not a
# dependency of producing the thing.
# The package. dpkg-buildpackage drives debian/rules, which is three lines
# of dh; everything the package declares is in debian/control.
deb: version-check
	@test -n "$(DEB_DIR)" || { echo "deb: DEB_DIR is empty, refusing" >&2; exit 1; }
	dpkg-buildpackage -b -us -uc
	@mkdir -p $(DEB_DIR)
	@for f in fmake_$(VERSION)_all.deb \
	          fmake_$(VERSION)_$(DEB_ARCH).buildinfo \
	          fmake_$(VERSION)_$(DEB_ARCH).changes; do \
		if [ -e "../$$f" ]; then mv -f "../$$f" $(DEB_DIR)/; fi; \
	done
	@test -f $(DEB) || { echo "deb: $(DEB) was not produced" >&2; exit 1; }
	@echo $(DEB)

# Lint the package, having built it. These were the other way round: `lint`
# built the .deb and `deb` merely depended on it, so the target that says it
# checks was the one doing the work.
lint: deb
	@if command -v lintian >/dev/null; then \
		lintian --pedantic $(DEB) && echo "lintian: clean"; \
	else \
		echo "lintian: not installed; package not checked"; \
	fi

# Named targets only, and no wildcard sweeps: a clean target is the one
# thing everybody runs without reading. The two directories are debhelper's
# own staging trees -- created by the build, relative, and named outright.
clean:
	rm -f fmake.1 fmake.bash debian/files debian/debhelper-build-stamp \
	      debian/fmake.substvars debian/fmake.debhelper.log \
	      $(DEB) $(DEB_EXTRA)
	rm -rf debian/fmake debian/.debhelper
	@rmdir $(BUILD_DIR) 2>/dev/null || :

# The shared style gate: one tool, copied verbatim from
# ~/.claude/tool/style_gate.py into every private project. It refuses to
# run against a collapsed file list, so a pass means it actually looked.
style: style-source style-docs

style-source:
	$(PYTHON) tool/style_gate.py check

# project.md is authoritative, so it is held to the tree: a heading
# that appears twice means whichever one you find, the other is the
# one with the answer.
style-docs:
	$(PYTHON) tool/style_gate.py docs

# `test` is the suite alone; `check` is everything that must pass first.
test:
	./selftest

# The clean ladder, matching the sibling projects.
veryclean: clean
	rm -rf $(BUILD_DIR)

# **`distclean` no longer sweeps the tree for editor droppings.** `*~`,
# `*.swp` and `*.orig` are not build output: they belong to somebody's
# editor, and a `.orig` belongs to a merge they may be in the middle of.
# The sweep was also unbounded -- `find .` walks `.git`, and it was measured
# deleting files in there. `git clean -xdn` lists that class and is the
# person's call rather than the build system's.
#
# What is left is what the tooling here really wrote. The search is a
# wildcard because a `__pycache__` appears beside whatever Python ran, but
# the thing removed is named exactly and is disposable by construction;
# `.git` is pruned and every removal is printed, because a clean target that
# deletes silently is one nobody can check.
distclean: veryclean
	@find . -name .git -prune -o \
	        -name __pycache__ -type d -prune -print -exec rm -rf {} +

# The commit-msg hook lives in the tree so it is reviewable, survives a
# clone, and can be kept in sync. .git/hooks is untracked, so a hook that
# exists only there enforces a rule nobody can see and vanishes silently on
# a fresh clone.
# **Where the hooks live is git's question, not the filesystem's.** This
# asked `test -d .git`, which is false in a linked worktree and in a
# submodule checkout: there `.git` is a regular FILE naming the real
# gitdir, and both are git repositories. So `make hooks` refused with
# "not a git repository" inside one that is.
#
# Testing -e instead would only move the failure one line down, because
# the install writes into `.git/hooks/`, which is not a directory there
# either. Asking git answers both halves at once, and from a worktree it
# returns the MAIN repository's hooks directory -- which is the one git
# actually runs.
#
# git's absence is reported as its own thing rather than as "not a git
# repository", which would be a message naming a cause nothing tested.
#
# **The `&&` before the message is load-bearing.** The recipe is one
# continued shell line, because `dir` is computed in it, so make sees only
# the last command's status -- and with a semicolon there, an install that
# fails still reaches an echo that succeeds. Measured in a scratch clone
# with the source file removed: `install: cannot stat` on stderr, "hooks:
# commit-msg installed" on stdout, exit 0, and no hook in `.git/hooks`. A
# tree could be told to run this, run it, read the success line, and still
# have no hook -- which is the one failure this target exists to prevent.
hooks:
	@if ! command -v git >/dev/null 2>&1; then \
		echo "hooks: git is not installed, so there is nowhere to install to." >&2; \
		exit 1; \
	fi; \
	dir=$$(git rev-parse --git-common-dir 2>/dev/null); \
	if [ -z "$$dir" ]; then \
		echo "hooks: not a git repository, so there is nowhere to install to." >&2; \
		exit 1; \
	fi; \
	mkdir -p "$$dir/hooks" && \
	install -m 0755 tool/hooks/commit-msg "$$dir/hooks/commit-msg" && \
	echo "hooks: commit-msg installed from tool/hooks/ into $$dir/hooks/"

# The TARGETS block in the header is the one statement of what the targets
# are, and `help` reads it back rather than repeating it: a list written
# twice is a list that disagrees with itself eventually.
#
# Defined last on purpose. Make takes the first non-special target in the
# file as the default goal, so a `help` rule placed above `all` makes plain
# `make` print the help instead of building -- which is exactly what
# happened when this was first added here.
help:
	@sed -n '/^# TARGETS/,/^#$$/p' $(firstword $(MAKEFILE_LIST)) | sed 's/^# \{0,1\}//'
