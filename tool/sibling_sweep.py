#!/usr/bin/env python3
"""Plan every sibling tree with two fmakes and say where they differ.

    tool/sibling_sweep.py                      HEAD~1 against the working fmake
    tool/sibling_sweep.py --old REV            that revision instead
    tool/sibling_sweep.py --old REV TREE...    only those siblings
    tool/sibling_sweep.py --build [TREE...]    build them, not only plan

A change to how fmake plans a build reaches every tree it builds, and the
suite's own trees are the ones it was written against. The projects beside
this one are the others: each is copied from `git archive HEAD' into a
temporary directory, so neither fmake touches the real checkout, and
planned with `-n' by both fmakes, with each submodule the sibling has
checked out archived into its place. A dry run compiles nothing and
writes nothing to the tree, so the two plans are compared from one copy,
and the copy is removed before the next tree is fetched.

With --build each tree is built for real by the working fmake, and a tree
that fails is built again by the old one from a fresh copy, so a failure
the change introduced reads REGRESSION and one that was already there
reads `fails both'. A plan proves nothing about whether the compiler
accepts what it says.

What it prints is the trees whose plans differ, with the first lines of
the difference, and the ones either fmake refused. A difference is a
question, not a verdict: it is the change being reviewed, on a tree
nobody wrote for it.
"""

import argparse
import difflib
import os
import signal
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


def build(fmake, tree, timeout, jobs):
	try:
		r = subprocess.run([sys.executable, fmake, f"-j{jobs}"], cwd=tree,
		                   capture_output=True, text=True, errors="replace",
		                   timeout=timeout, stdin=subprocess.DEVNULL)
	except subprocess.TimeoutExpired:
		return None, f"timed out after {timeout}s"
	return r.returncode, r.stdout + r.stderr


def unpack(src, dest):
	"""`git archive HEAD' of `src' into `dest', and of each submodule.

    An archive carries .gitmodules and none of the contents, and fmake
    rightly refuses such a tree -- the first build sweep reported eleven
    of twenty trees failing for exactly that. Each submodule the sibling
    has checked out is archived into its place, at the commit it is at.
    """
	os.makedirs(dest, exist_ok=True)
	a = subprocess.Popen(["git", "-C", src, "archive", "HEAD"],
	                     stdout=subprocess.PIPE)
	subprocess.run(["tar", "-x", "-C", dest], stdin=a.stdout, check=True)
	a.wait()
	subs = subprocess.run(["git", "-C", src, "submodule", "--quiet",
	                       "foreach", "--recursive", "echo $displaypath"],
	                      capture_output=True, text=True).stdout.split()
	for sub in subs:
		if os.path.exists(os.path.join(src, sub, ".git")):
			unpack_one(os.path.join(src, sub), os.path.join(dest, sub))


def unpack_one(src, dest):
	"""One submodule's checkout; one that git will not archive is said.

    Its absence is then fmake's to report on that tree, which it does in
    its own words, rather than this script's to die of.
    """
	os.makedirs(dest, exist_ok=True)
	r = subprocess.run(["git", "-C", src, "archive", "HEAD"],
	                   capture_output=True)
	if r.returncode:
		print(f"     (not copied: {src}: "
		      f"{r.stderr.decode(errors='replace').strip()[:120]})")
		return
	subprocess.run(["tar", "-x", "-C", dest], input=r.stdout, check=True)


def fresh(path, work):
	copy = os.path.join(work, os.path.basename(path))
	subprocess.run(["rm", "-rf", "--", copy], check=True)
	unpack(path, copy)
	return copy


def build_sweep(trees, old, new, timeout, jobs, lines):
	worse = 0
	with tempfile.TemporaryDirectory(prefix="fmake-sweep-") as work:
		for path in trees:
			name = os.path.basename(path)
			copy = fresh(path, work)
			rc, text = build(new, copy, timeout, jobs)
			if rc == 0:
				print(f"ok   {name}")
				subprocess.run(["rm", "-rf", "--", copy], check=True)
				continue
			copy = fresh(path, work)
			rc_old, _ = build(old, copy, timeout, jobs)
			subprocess.run(["rm", "-rf", "--", copy], check=True)
			if rc_old == 0:
				worse += 1
				print(f"REGRESSION {name} (old fmake builds it)")
			else:
				print(f"fails both {name}")
			for line in text.strip().splitlines()[-lines:]:
				print("     " + line[:200])
	return worse


def _exit_on_term(signum, _frame):
	"""SIGTERM as an ordinary exit, so the temporary directory goes.

    `timeout' and a harness stopping a job both send it, and Python's
    default for it is to die where it stands, skipping every `with'
    cleanup: a killed sweep left its directory in /tmp.
    """
	sys.exit(128 + signum)


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
	ap.add_argument("--build", action="store_true",
	                help="build each tree, not only plan it")
	ap.add_argument("-j", type=int, default=4, dest="jobs",
	                help="jobs per build (default 4; the machine is shared)")
	args = ap.parse_args()
	signal.signal(signal.SIGTERM, _exit_on_term)
	sys.stdout.reconfigure(line_buffering=True)
	parent = os.path.dirname(HERE)
	trees = []
	for t in args.trees:
		# A sibling by its bare name, as well as by a path.
		path = t if os.path.isdir(t) else os.path.join(parent, t)
		if not os.path.isdir(os.path.join(path, ".git")):
			sys.exit(f"sibling_sweep: {t} is not a git checkout")
		trees.append(os.path.abspath(path))
	trees = trees or siblings(parent)

	with tempfile.TemporaryDirectory(prefix="fmake-sweep-") as work:
		old = os.path.join(work, "fmake.old")
		r = subprocess.run(["git", "-C", HERE, "show", f"{args.old}:fmake"],
		                   capture_output=True)
		if r.returncode:
			sys.exit(f"sibling_sweep: no fmake at {args.old}")
		with open(old, "wb") as fh:
			fh.write(r.stdout)
		if args.build:
			return 1 if build_sweep(trees, old, args.new, args.timeout,
			                        args.jobs, args.lines) else 0
		same = differ = refused = 0
		for path in trees:
			name = os.path.basename(path)
			copy = fresh(path, work)
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
