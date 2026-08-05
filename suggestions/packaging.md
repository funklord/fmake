# Packaging: what fmake should and should not do

Written while converting seven sibling projects from hand-rolled `.deb`
assembly to native Debian packaging. The question that came up: should fmake
build packages?

## No, and the design already says so

Section 16's fragment mode exists for exactly this. Its docstring:

> A project whose Makefile also patches a submodule, cross-builds for two
> Android ABIs and produces two .debs does not want fmake to own any of
> that -- and the compile step, which is the part fmake is actually better
> at, is a small share of what that Makefile does.

That is the right line and it should stay drawn where it is. Three reasons
the conversion confirmed rather than contradicted it:

**The metadata is not in the tree.** A package declares a maintainer, a
section, a priority, a description, `Recommends`, `Suggests`, and which
binary package each file belongs to. None of that is a fact about source
that any amount of reading can recover. hydra's package suggests
`keepassxc, yt-dlp, gnome-keyring | kwalletmanager`; nothing in its sources
says so, and nothing could.

**`dpkg-shlibdeps` has better evidence than fmake does.** fmake reasons from
symbols in objects, which is what makes it good at deciding a link set. A
packager needs the reverse question -- which installed *packages* provide
the libraries the finished binary actually records -- and dpkg answers that
from the ELF and the shlibs database. On beerssh it produced thirteen
versioned dependencies, on hydra twenty. Reimplementing that would mean
reimplementing the shlibs database.

**debhelper is three lines.** A `debian/rules` that drives a Makefile is
`%: dh $@` plus an override. There is no burden here worth removing.

## The real gap: an ejected Makefile has no `install` target

This one is worth fixing, and it is small.

`dh_auto_install` runs `make install DESTDIR=debian/tmp`. That is how every
native Debian package built from a Makefile stages its files, and it is what
made the seven conversions possible at all -- the prerequisite was already
met everywhere, by accident.

`eject_make` emits compile, link and clean rules and no `install` rule. So a
project that adopts fmake *fully* -- eject rather than fragment -- loses the
ability to be packaged by the standard flow, and gets it back only by
hand-writing the target fmake just replaced. Fragment mode does not have
this problem, because the parent Makefile kept its own.

fmake already knows how to install. There is an `install` key in the config
(line 433), `install_paths` and `do_install` implement it, and `--install`
drives it. The suggestion is only that the ejected Makefile carry the same
knowledge:

    install:
    	install -Dm755 $(FM_BIN) $(DESTDIR)$(PREFIX)/bin/<name>

derived from the `install` config already read, honouring `DESTDIR` and
`PREFIX` because those are the two variables debhelper sets. `uninstall`
naming the same files would follow for free, and the sibling projects all
have one.

## What would genuinely help, beyond that

**Say what an ejected build installs.** `--explain` already reports how the
link set was decided. A packager needs the same for artifacts: which files
are products, which are intermediates, which are meant to ship. That is
knowledge fmake has and currently keeps.

Nothing else. Packaging is declarations, and fmake's premise is that the
common case needs none.

---

Note on where this lives: `suggestions/` was removed deliberately in
f9f615d, its four reports folded into `project.md`. This file re-creates the
directory because it was asked for by name. If the folding was the point,
this belongs in `project.md` section 16 instead and the directory should go
again.
