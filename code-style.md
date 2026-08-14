<!-- The three rules and their detail are copied from
     ~/.claude/guidelines/code-style.md -- the source. Keep in sync; fix
     drift the moment you notice it. -->

# code-style.md

Code style for this project -- `fmake` itself, `selftest`, the `Makefile`
and the packaging, **and the build files `fmake` ejects**.

`project.md` section 16 records how the work is done and points here for the
style; where the two disagree, `project.md` wins. **Above both sits the
global source**, `~/.claude/guidelines/code-style.md`, which applies to
every private project. Where either disagrees with it, that is **drift to
fix, not a local override**. A genuine divergence needs a technical reason and is signalled to the list in `claude-guidelines`' `project.md` rather
than decided in passing -- and when a conflict between
the three actually comes up, stop and ask instead of picking a winner.

Nothing is vendored. The reference projects in section 16 are fetched into scratch
directories and are not part of this repository, so their style is their
own and never ours to correct.

## The three rules

1. **`snake_case`, not `camelCase`,** for identifiers this project defines.
2. **Tabs for indentation, spaces for alignment.**
3. **Lowercase filenames,** unless a tool demands otherwise.

Everything below is those three rules in detail, plus the exceptions that
are already settled. An exception not listed is not yet settled: signal it
to the list in `claude-guidelines`' `project.md` rather than deciding it in
passing.

## 1. Naming

`snake_case` for functions, variables and attributes; the tool is one file
of stdlib-only Python, so there is no library surface to prefix and no
prefix is used.

- **No abbreviations that are not already vocabulary.** This has teeth
  here: a name invented inside the tool escapes into directive spellings,
  `fmake.toml` keys and `--explain` output, where it can no longer be
  renamed without breaking somebody's build file.
- **One word per fact, wherever it is written** -- section 4 already states this
  for the directive set, and it is the same rule. The word in the directive
  is the word in the config key is the word in the diagnostic.
- Prefer the plain descriptive name over the decorated one.
- **A leading underscore is the private marker.** Python's `_name` is what
  stands in for the source's "module-private symbols are left unprefixed",
  since there is no linker here to collide with and therefore no prefix.

Naming and filename rules are review items rather than automated ones; the
gate checks indentation and text, not what things are called.

## 2. Indentation and alignment

Tabs carry structural indent level; spaces carry alignment within a level.
Continuation lines use tabs to the structural level, then spaces to the
alignment column. Never a space before a tab in leading whitespace.

No tab width is prescribed anywhere. The viewer decides.

Python accepts this: the language's only hard rule is that indentation must
not be *ambiguous* across tab widths, and tabs-then-spaces is unambiguous
at every width. Continuation lines inside brackets are not
indentation-significant at all.

### Settled exceptions

Every one of these exists in this tree, and each has a technical reason
rather than a preference behind it:

- **Markdown** -- list continuation and code fences are space-indented by
  specification. Exempt.
- **YAML** -- the spec forbids tabs for indentation outright, so
  `.github/workflows/ci.yml` is space-indented. `.style-gate.toml` puts
  `.yml` in `text_suffixes` and leaves it out of the indent check for that
  reason, which widens what is checked without demanding what the format
  forbids.
- **Debian packaging files** -- exempt, and the two halves for different
  reasons. `debian/changelog` has a fixed layout that a tab is not part of:
  `dpkg-parsechangelog` calls a tab-indented change line "unrecognized" and
  loses the trailer outright if a tab precedes `--`. A deb822 continuation
  in `control` or `copyright` is the opposite case -- `deb822(5)` allows a
  leading space *or* tab and dpkg round-trips either, but that leading
  whitespace is field syntax rather than indentation, so the rule has
  nothing to say about it and everything past it is alignment. Both
  measured against dpkg rather than read off the manual.
- **Makefile recipe lines** -- `make` requires a literal tab, so they are
  compliant by construction. Where that matters here is the ejected output,
  below.

Anything else that seems to need spaces: signal it to the list in
`claude-guidelines`' `project.md`, follow the rule meanwhile, and it gets
settled and added here in a pass rather than in whichever project met it
first.

### Ejected build files

An ejected `Makefile` or `build.ninja` is somebody's build system from the
moment it lands, and it follows the same rule. Make's recipe lines require
a literal tab in any case, so that half is compliant by construction; the
rest of the emitted text should be too.

The Make conventions in the global
`~/.claude/guidelines/build-and-commit.md` -- `.d` files actually
`-include`d, sibling-library rules carrying `FORCE`, `.SECONDARY` named
rather than bare -- **apply to ejected Makefiles as well**. An ejected
Makefile is a Makefile someone will edit, and every one of those rules
fails silently rather than loudly.

### No autoformatter

`black` and `ruff format` rewrite tabs to spaces unconditionally and cannot
be configured out of it. **Do not run either, not even ad hoc on a single
file.**

This project runs the shared gate: `make style`, which is
`tools/style_gate.py`, copied verbatim from `~/.claude/tools/style_gate.py`.
`.style-gate.toml` says which files here it applies to, and the floor it
carries makes it fail rather than pass when that file list collapses.

It reaches `fmake` and `selftest` even though neither has a suffix: a
shebang is the file saying it is a program, and scoping by suffix alone
excluded precisely the two files that matter here.

The conversion from spaces was mechanical, and is worth describing because
the same job is waiting in the sibling projects. It is not a search and
replace. A continuation line aligned under an open paren has no structural
indent of its own, so it takes the tabs of the logical line it belongs to
and expresses the remaining columns in spaces; a line at module level keeps
pure spaces, because at level zero there are no tabs to align against. Lines
inside a triple-quoted string are data -- C fixtures, Makefile snippets,
expected output -- and are left alone entirely.

What made it safe to believe was not the diff. `ast.dump(ast.parse(...))`
was identical before and after for both files, which proves every string
literal survived byte for byte -- and string literals are exactly where this
conversion could have done real damage, in a place a whitespace-insensitive
diff would never have shown it.

## 3. Filenames

**Lowercase, always**, for everything this project names itself. The tool is
`fmake`, extensionless and executable; the suite is `selftest`, the same.

**The separator follows what the name binds to**, and the two cases are a
technical difference rather than a matter of taste:

- **`snake_case` where the filename becomes an identifier** -- a source
  file, a header, a module. `tools/style_gate.py` *is* the module
  `style_gate`, and `style-gate.py` could not be imported under any name,
  because a hyphen is not legal in a Python one. That is the language's
  requirement wearing a convention's clothes, and it is not negotiable
  where it applies.
- **`kebab-case` for prose** -- documentation, design notes, decision
  records. Nothing imports `code-style.md`, so no identifier is at stake,
  and kebab-case is what markdown and URLs settled on long ago.

The rule used to say `snake_case` for prose as well, and was rewritten
against a count of what the private projects actually do -- the source
carries the numbers. The distinction had never come up here: the two
programs this project names are one word each, with no separator to argue
about, and every document it names was kebab-case or a single word already.

Settled exceptions:

- **Names a tool will not accept lowercased** -- `Makefile`, and the
  `debian/` files native packaging dictates.
- **Root files with an established convention** -- `README.md`, `LICENSE`
  and `VERSION`.
- **Package-system spellings** -- kebab-case where Debian requires it. That
  is now the same spelling prose uses, so the packaging and the documents
  beside it agree by construction rather than by coincidence.

`tools/hooks/commit-msg` needs none of these: git dictates that name
exactly, which is rule 3's "unless a tool demands otherwise", and it is
lowercase in any case.

## 4. Editing `selftest`

Not style, but it lives with the style rules because it is a formatting
hazard: **edit `selftest` with an editor, not a generated patch.** Three
separate incidents came from `\n` collapsing or a multi-line anchor
breaking while being quoted through nested layers, each costing more than
the bug being fixed. Mutations go through a script reading before-and-after
text from files, never through a shell heredoc.

## ASCII in source

Source and comments are ASCII. Write `--` where prose would use an em dash,
and "section" for a section sign.

This governs the text the repository writes about itself, not the data the
software handles. Documentation may use typographic punctuation; so may
user-facing text in UI software, and anything that genuinely requires
Unicode.

Enabled here (`ascii_only` in `.style-gate.toml`): this is a build tool with
no user-facing Unicode and nothing that needs it.

The check is not a byte scan. fmake is Python, so it means ASCII *outside
string literals* -- the gate reads the file with `tokenize` -- and Unicode
inside a literal passes. C and C++ get the same shape from a scanner written
for the purpose, nothing in the standard library lexing them; that half does
not arise here, since this project has no C or C++ of its own, but the gate
is carried verbatim and it is what a sibling's copy will be describing.
Every other language gets a whole-file byte check, having no lexer, and so
does a file in either of those two that will not lex: a file nobody can
parse is not a file that has been cleared.

It was the whole file for everyone until a project that prints two status
ticks had to switch the check off to keep them, which switched it off for
its comments as well, and an em dash arrived in one. **An exception wider
than its reason is how a rule stops being enforced.** Nothing here needs
the allowance today, but the gate is carried verbatim and behaves this way.

## The commit-msg hook

The commit-msg hook is `tools/hooks/commit-msg`, installed with `make hooks`.
It rejects generator attribution, a subject over 75 columns, and body prose
over 75 columns. It lives in the tree rather than only in `.git/hooks` so
that it is reviewable and survives a clone; the copy that runs is installed
from it.

The body limit was stated long before anything checked it, and only the
subject was checked -- so a body line at 76 columns went through while a
subject at 76 was refused.

What it deliberately does not reject, in three groups.

**Three names are spared**, so a message may say where the shared tooling
comes from: the directory `.claude`, the file `CLAUDE.md`, and
`claude-guidelines`, the repository the guidelines live in. The ban is on
crediting a generator and none of the three is a spelling of that. Only the
names are neutralised, never the token around them -- a vendor word at the
end of a path under the tree is still refused.

**What git is about to discard**: comment lines, and the diff that
`git commit -v` puts below the scissors line. Reading those refused commits
over text that never reaches the message -- the hook's own diff contains its
own pattern list, so it rejected every commit that edited it.

**Three shapes the length check exempts**, each because wrapping it is the
actual mistake rather than a concession: a *trailer*, since git parses the
block a line at a time and a broken `Link:` stops being a trailer at all; a
line holding a *url*, which no longer works once it is split; and an
*indented* line, which is how a message quotes a compiler error or a stack
trace, where reflowing what you are quoting corrupts the one thing it was
included for. It cannot tell prose opening `Note:` from a trailer, so it
forgives that -- the wrong way round would refuse a real trailer, and that
is the expensive error.

## See also

- **`~/.claude/guidelines/code-style.md`** -- the source this file copies.
- **`~/.claude/guidelines/build-and-commit.md`** -- the Make conventions the
  ejected output has to satisfy.
- **`project.md` section 16** -- how the work is done, and the rule that every fix
  gets a case that must fail when the fix is reverted.
