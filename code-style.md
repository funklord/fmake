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
fix, not a local override**. A genuine divergence needs a technical reason
and is raised rather than decided in passing -- and when a conflict between
the three actually comes up, stop and ask instead of picking a winner.

Nothing is vendored. The reference projects in section 16 are fetched into scratch
directories and are not part of this repository, so their style is their
own and never ours to correct.

## The three rules

1. **`snake_case`, not `camelCase`,** for identifiers this project defines.
2. **Tabs for indentation, spaces for alignment.**
3. **Lowercase filenames,** unless a tool demands otherwise.

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

## 2. Indentation and alignment

Tabs carry structural indent level; spaces carry alignment within a level.
Continuation lines use tabs to the structural level, then spaces to the
alignment column. Never a space before a tab in leading whitespace.

No tab width is prescribed anywhere. The viewer decides.

Python accepts this: the language's only hard rule is that indentation must
not be *ambiguous* across tab widths, and tabs-then-spaces is unambiguous
at every width. Continuation lines inside brackets are not
indentation-significant at all.

**Markdown is exempt** -- list continuation and code fences are
space-indented by specification.

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

Lowercase for everything this project names itself. The tool is `fmake`,
extensionless and executable; the suite is `selftest`, the same.

The exception is a name a tool will not accept lowercased: `Makefile`,
`README.md`, `LICENSE`, and the `debian/` files native packaging dictates.

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

## See also

- **`~/.claude/guidelines/code-style.md`** -- the source this file copies.
- **`~/.claude/guidelines/build-and-commit.md`** -- the Make conventions the
  ejected output has to satisfy.
- **`project.md` section 16** -- how the work is done, and the rule that every fix
  gets a case that must fail when the fix is reverted.
