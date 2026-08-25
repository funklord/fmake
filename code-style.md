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
and is signalled to the list in `claude-guidelines`' `project.md` rather
than decided in passing -- and when a conflict between the three actually
comes up, stop and ask instead of picking a winner.

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

### Prefixes, and visibility

Prefixes exist to keep this project's symbols from colliding with a
library's. So they follow **visibility**, and the choice is a matter of
judgement rather than a mechanical rule:

- **Anything with more than small visibility carries the project prefix** --
  the public API, and anything a linker or importer outside its own module
  can reach.
- **Module-private symbols are left unprefixed**, precisely so that the
  absence of a prefix reads as "this does not leave the module."

The middle case decides itself on link safety, not on taste. A symbol that
is internal by intent but still reaches the linker -- cross-file within a
library, not `static`, not part of the API -- is *not* private for this
purpose. Prefix it. A deliberate parallel copy of a function in two
libraries needs a **distinct** name, not the same name in both on the
assumption that nothing will ever link both sides; that assumption fails
later, at a call site that changed nothing, and names files you did not
touch.

Where a language enforces its own scheme, accept it rather than fight it,
and say in the project's copy that the toolchain is doing it:

- **Rust** -- `non_snake_case` and `non_camel_case_types` are on by default,
  so types are `PascalCase` and constants `SCREAMING_SNAKE_CASE`. That is
  the toolchain's, not a choice. Package systems that demand kebab-case
  (Cargo crate names, Debian package names) likewise read back with their
  own spelling; do not invent a third by naming the directory differently
  from the package.
- **Python** -- a leading underscore (`_name`) is the language's private
  marker and stands in for "unprefixed" above.

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
`tool/style_gate.py`, copied verbatim from `~/.claude/tool/style_gate.py`.
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
  file, a header, a module. `tool/style_gate.py` *is* the module
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

`tool/hooks/commit-msg` needs none of these: git dictates that name
exactly, which is rule 3's "unless a tool demands otherwise", and it is
lowercase in any case.

### Singular, unless somebody else standardised the plural

**Prefer the singular for a directory this project names itself.** `helper/`
rather than `helpers/`, `doc/` rather than `docs/`, `fixture/` rather than
`fixtures/`. The name says what kind of thing lives there, not how many;
one of them and forty of them go in the same place, and the directory
should not have to be renamed when the count changes.

There are two exceptions, and they are not equal. This is the same shape
as the lowercase rule above, which yields first to `Makefile` because make
will not read anything else, and only then to `README.md` because the world
settled it.

**First: a name a tool requires is not a name we choose.** It outranks the
singular exactly as it outranks lowercase, it needs no measurement and no
argument, and the test is whether something breaks when the name changes.
This is a *technical* fact, so it is open-ended rather than a list -- a
tool met tomorrow that demands a name gets the same answer, whether the
name it demands is plural, singular, capitalised or none of those.

Present here: **Cargo** looks for `tests/`, `examples/` and `benches/` by
those exact names, and `cargo-fuzz` for `fuzz_targets/`. **GitHub**
requires `.github/workflows/`. **git** keeps `hooks/`, which is why
`tool/hooks/` is spelled that way.

**Second: a plural an ecosystem has settled**, which is a convention rather
than a requirement -- nothing breaks, but a reader would be surprised by
the singular. Cargo workspaces conventionally keep members in `crates/`,
and that is this kind rather than the first. **These need measuring**, and
the project's copy names what it was measured against, so the next reader
does not reopen it.

Where the two are confused, the cost lands on whoever renames a directory
because it looked like a convention and finds the build no longer works.
So say which kind is being claimed.

**The settled inventory took this rule by the holder's instruction, not by
sweep.** When this section was first written, three canonical names in
`harmonization.md` were plural -- `tools/`, `docs/` and `docs/decisions/` --
and the paragraph here held them out of reach, because renaming an inventory
entry is a cross-project rewrite rather than a spelling change: the decision
records were cited by path hundreds of times, and `tools/` was named from
`sync.py`, every Makefile's hook target and the `~/.claude` symlink the
copies are spread from. The holder then said to rename all three, and they
are `tool/`, `doc/` and `doc/decision/` now, moved in a deliberate pass with
each project's gates run against the result. The history is kept because the
next inventory entry will raise the same question, and the answer stays the
same: an inventory name moves when its owner says so, at whatever cost was
measured, and not as a side effect of a style rule.

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

## Formatters

A formatter is allowed **only if it can be configured to honour the three
rules completely**. Configuration gaps are disqualifying, not something to
work around: a formatter that gets indentation right and alignment wrong
will rewrite the tree on somebody's next save.

So the decision is per tool, per project, and it is a real evaluation:

- If it can be made to comply, use it, and commit the config with a comment
  saying which setting is load-bearing and what happens without it.
- If it cannot, do not run it -- **not even ad hoc on a single file**. The
  failure mode is a silent conversion of files that were already correct,
  discovered later as a reverted commit rather than an error.
- If no existing tool fits and the rule is worth mechanising, write our
  own. A checker that only gates indentation is worth more than a formatter
  that reflows everything.

**Record the decision and the finding that produced it** in the project's
copy of this file -- which tool, what specifically failed, what would change
the answer. A verdict without its evidence gets re-litigated, and a tool
that improves later never gets reconsidered because nobody remembers what
was actually wrong with it.

Naming and filename rules are review items, not automated ones.

## Precedence

Three layers, and they are not equals:

1. **The global guidelines** (`~/.claude/CLAUDE.md` and the files it
   imports) -- the source, and they win.
2. **The project's `project.md`** -- project-specific design and conventions.
3. **The project's `code-style.md`** -- this file, copied.

A project copy that disagrees with the source is **drift, not an
override**: fix it. A project that genuinely needs to diverge needs a
technical reason, and that is not a decision to make while working on
something else -- signal it to the list in `claude-guidelines`'
`project.md` and keep following the source meanwhile.

**When a conflict between layers actually comes up, stop and ask.** Do not
silently pick a winner, even the global one.

This precedence rule lives here and in the global guidelines only. It does
not belong in a `project.md`.

## Keeping the copies in sync

Each private project keeps a copy of this file at its repo root -- except
the one this file lives in. `claude-guidelines` holds the source at
`guidelines/code-style.md`, and a copy beside it would be the same document
twice in one repository with nothing to keep the two honest; its root
`code-style.md` says so and points here. Every other private project carries
a copy, opening with a header that names the source:

```markdown
<!-- Copied from ~/.claude/guidelines/code-style.md -- the source. Keep in
     sync; fix drift the moment you notice it. -->
```

Below the copied rules, a project adds only what is genuinely its own: its
exempt paths, its formatter verdicts, its language-specific notes, its
tooling commands.

**This source is deliberately plain ASCII** -- no em dashes, no section
signs, no arrows -- so that a copy can be byte-verbatim in every project,
including one whose own rules restrict the characters its files may
contain. Keep it that way when editing: a typographic character introduced
here becomes a transliteration problem in every repository that carries a
copy.

Where a copy must still be adapted, **"do not diverge" means semantically
identical, not byte-identical**: a project transliterating to satisfy its
own character-set rule, or renumbering a heading to fit its own structure,
is that project's rule working correctly, **not drift, and not something to
reconcile back**. What must match is every rule and every exception, in
substance.

**`sync.py --check` now reports the copies that have fallen behind**, which
until 2026-08-24 nothing did. The three files spread verbatim were checked on
every run and this one -- the document that says what the rules are -- was
checked by nobody, so drift was indistinguishable from the adaptation the
section above asks for. It found real losses: four copies had dropped
*Precedence*, the section saying this source outranks them; three had dropped
*Formatters*, whose rule was paid for by a formatter rewriting committed
files; one had dropped *ASCII in source*; and seven had dropped this very
section, which is the one that would have told a reader to look.

It asks the weaker question that can actually be answered -- does the copy
still carry a section for every section here -- and it never writes this
file, because overwriting a copy would delete the part the project owns. A
heading that *extends* one of these satisfies it, since that is what
recording a project's own formatter verdict looks like.

**If you notice a copy diverging from the source, reconcile it as soon as
you notice** -- do not leave it for later and do not work around it. If the
divergence looks deliberate rather than stale, that is the conflict case
above: ask.

Noticing requires looking. **Re-read this source before writing or
reconciling any project's copy**, rather than working from what was loaded
at the start of the session -- it may have changed since, and a copy
reconciled against a stale source is drift being written rather than
fixed.

The project's `project.md` may state the three rules in brief and point
here for the detail. It does not restate the precedence rule.

## The commit-msg hook

The commit-msg hook is `tool/hooks/commit-msg`, installed with `make hooks`.
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
