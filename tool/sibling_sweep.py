#!/usr/bin/env python3
"""Plan every sibling tree with two fmakes and say where they differ.

    tool/sibling_sweep.py                      HEAD~1 against the working fmake
    tool/sibling_sweep.py --old REV            that revision instead
    tool/sibling_sweep.py --old REV TREE...    only those siblings

A change to how fmake plans a build reaches every tree it builds, and the
suite's own trees are the ones it was written against. The projects beside
this one are the others: each is copied from `git archive HEAD' into a
temporary directory, so neither fmake touches the real checkout, and
planned with `-n' by both fmakes. A dry run compiles nothing and writes
nothing to the tree, so the two plans are compared from one copy, and the
copy is removed before the next tree is fetched. A submodule arrives
empty; both fmakes see the same, which is what a comparison needs.

What it prints is the trees whose plans differ, with the first lines of
the difference, and the ones either fmake refused. A difference is a
question, not a verdict: it is the change being reviewed, on a tree
nobody wrote for it.
"""

import argparse
import difflib
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = ("*.c", "*.cc", "*.cpp", "*.cxx", "*.rs", "*.S")


def siblings(parent):
	out = []
	for name in sorted(os.listdir(parent)):
		path = os.path.join(parent, name)
		if path == HERE or not os.path.isdir(os.path.join(path, ".git")):
			continue
		r = subprocess.run(["git", "-C", path, "ls-files", *SOURCES],
		                   capture_output=True, text=True)
		if r.returncode == 0 and r.stdout.strip():
			out.append(path)
	return out


def plan(fmake, tree, timeout):
	try:
		r = subprocess.run([sys.executable, fmake, "-n"], cwd=tree,
		                   capture_output=True, text=True, errors="replace",
		                   timeout=timeout, stdin=subprocess.DEVNULL)
	except subprocess.TimeoutExpired:
		return None, f"timed out after {timeout}s"
	# Paths name the copy, which is the same directory for both runs.
	return r.returncode, r.stdout + r.stderr


def main():
	ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
	ap.add_argument("trees", nargs="*",
	                help="sibling directories (default: every one with sources)")
	ap.add_argument("--old", default="HEAD~1",
	                help="the fmake revision to compare against")
	ap.add_argument("--new", default=os.path.join(HERE, "fmake"),
	                help="the fmake file to compare (default: the working one)")
	ap.add_argument("--timeout", type=int, default=600)
	ap.add_argument("--lines", type=int, default=12,
	                help="diff lines to show per tree")
	args = ap.parse_args()
	trees = ([os.path.abspath(t) for t in args.trees]
	         or siblings(os.path.dirname(HERE)))

	with tempfile.TemporaryDirectory(prefix="fmake-sweep-") as work:
		old = os.path.join(work, "fmake.old")
		r = subprocess.run(["git", "-C", HERE, "show", f"{args.old}:fmake"],
		                   capture_output=True)
		if r.returncode:
			sys.exit(f"sibling_sweep: no fmake at {args.old}")
		with open(old, "wb") as fh:
			fh.write(r.stdout)
		same = differ = refused = 0
		for path in trees:
			name = os.path.basename(path)
			copy = os.path.join(work, name)
			os.makedirs(copy)
			a = subprocess.Popen(["git", "-C", path, "archive", "HEAD"],
			                     stdout=subprocess.PIPE)
			subprocess.run(["tar", "-x", "-C", copy], stdin=a.stdout,
			               check=True)
			a.wait()
			rc_old, text_old = plan(old, copy, args.timeout)
			rc_new, text_new = plan(args.new, copy, args.timeout)
			subprocess.run(["rm", "-rf", "--", copy], check=True)
			if rc_old != rc_new:
				refused += 1
				print(f"EXIT {name}: {rc_old} -> {rc_new}")
			if text_old == text_new:
				if rc_old == rc_new:
					same += 1
					print(f"same {name}")
				continue
			# Dry-run lines come in the order the scheduler would start
			# them, which is not a property of the plan.
			if sorted(text_old.splitlines()) == sorted(text_new.splitlines()):
				same += 1
				print(f"same {name} (order only)")
				continue
			differ += 1
			print(f"DIFF {name}")
			diff = list(difflib.unified_diff(
			    sorted(text_old.splitlines()), sorted(text_new.splitlines()),
			    "old", "new", lineterm="", n=0))[2:]
			for line in diff[:args.lines]:
				print("     " + line[:200])
			if len(diff) > args.lines:
				print(f"     ... {len(diff) - args.lines} more lines")
		print(f"{len(trees)} tree(s): {same} the same, {differ} differ, "
		      f"{refused} changed exit")
	return 1 if differ or refused else 0


if __name__ == "__main__":
	sys.exit(main())
