#!/usr/bin/env python3
"""Fetch what Windows-hosted testing needs, run the cases, delete it all.

    tool/windows_kit.py                       the Windows cases, then clean up
    tool/windows_kit.py CASE...               those selftest cases instead
    tool/windows_kit.py --keep DIR [CASE...]  fetch into DIR and leave it
    tool/windows_kit.py --keep DIR --env      fetch, print the exports, run nothing
    tool/windows_kit.py --no-qt --no-rust     skip the Qt kit or Rust

fmake cannot be tested on Windows from Linux without Windows programs, and
those are a gigabyte and more unpacked. Kept between runs they filled the
shared disk (project.md section 618), so this fetches them into a
temporary directory, checks every download against a published or pinned
hash, runs the cases under wine, and removes the directory -- wine prefix
included -- however the run ends. What it fetches:

    Python 3.12 (python.org's embeddable zip)  FMAKE_WINDOWS_PYTHON
    Qt's MinGW 13.1 (gcc, mingw32-make)        FMAKE_WINDOWS_MINGW
    ninja 1.12.1 (the official ninja-win.zip)  FMAKE_WINDOWS_NINJA
    Qt 6.8.2 for MinGW: qtbase and runtime     FMAKE_QT_WINDOWS
    Rust stable for x86_64-pc-windows-gnu      FMAKE_WINDOWS_RUSTC

Needs wine and 7z (Qt's archives are 7z, which the standard library cannot
read). Each download is bounded by a timeout and the selftest run by one
too, so nothing here waits for ever.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Pinned, because python.org and the ninja release publish no hash beside
# the file in a form worth parsing; recomputed and checked 2026-11-09.
PYTHON_URL = ("https://www.python.org/ftp/python/3.12.10/"
              "python-3.12.10-embed-amd64.zip")
PYTHON_SHA256 = "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"
NINJA_URL = ("https://github.com/ninja-build/ninja/releases/download/"
             "v1.12.1/ninja-win.zip")
NINJA_SHA256 = "f550fec705b6d6ff58f2db3c374c2277a37691678d6aba463adcbb129108467a"

QT_REPO = "https://download.qt.io/online/qtsdkrepository/windows_x86/desktop"
MINGW_DIR = QT_REPO + "/tools_mingw1310"
MINGW_PACKAGE = "qt.tools.win64_mingw1310"
QT_DIR = QT_REPO + "/qt6_682/qt6_682"
QT_PACKAGE = "qt.qt6.682.win64_mingw"
# The archives a Widgets program with a form and a resource needs, and the
# runtime its .exe loads; the rest of the kit is QML, SVG and translations.
QT_ARCHIVES = ("qtbase-", "MinGW-w64-x86_64-")

RUST_CHANNEL = "https://static.rust-lang.org/dist/channel-rust-stable.toml"
RUST_TARGET = "x86_64-pc-windows-gnu"
RUST_COMPONENTS = ("rustc", "rust-std", "rust-mingw")

TIMEOUT = 120


def say(text):
	print(f"windows_kit: {text}", flush=True)


def fetch(url, dest):
	"""Download `url' to `dest' and return its sha256 and sha1."""
	h256, h1 = hashlib.sha256(), hashlib.sha1()
	with urllib.request.urlopen(url, timeout=TIMEOUT) as r, \
	     open(dest, "wb") as fh:
		while True:
			block = r.read(1 << 20)
			if not block:
				break
			h256.update(block)
			h1.update(block)
			fh.write(block)
	return h256.hexdigest(), h1.hexdigest()


def read(url):
	with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
		return r.read()


def check(name, got, want):
	if got != want:
		sys.exit(f"windows_kit: {name}: hash {got}, published {want}; "
		         f"refusing to run it")


def unzip(path, dest):
	with zipfile.ZipFile(path) as z:
		z.extractall(dest)


def un7z(path, dest):
	r = subprocess.run(["7z", "x", "-y", "-bd", f"-o{dest}", path],
	                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
	                   text=True, timeout=600)
	if r.returncode:
		sys.exit(f"windows_kit: 7z could not unpack {path}: {r.stderr}")


def qt_package(base, name):
	"""(version, [archive names]) of one package in a Qt repository."""
	root = ET.fromstring(read(base + "/Updates.xml"))
	for p in root.findall("PackageUpdate"):
		if p.findtext("Name") == name:
			names = [a.strip() for a in
			         (p.findtext("DownloadableArchives") or "").split(",")
			         if a.strip()]
			return p.findtext("Version"), names
	sys.exit(f"windows_kit: {name} is not in {base}/Updates.xml")


def qt_archive(base, name, version, archive, work, dest):
	"""Fetch one archive, check it against the .sha1 Qt publishes, unpack."""
	url = f"{base}/{name}/{version}{archive}"
	path = os.path.join(work, archive)
	_, sha1 = fetch(url, path)
	check(archive, sha1, read(url + ".sha1").decode().split()[0])
	un7z(path, dest)
	os.unlink(path)


def get_python(top, work):
	path = os.path.join(work, "python.zip")
	check("python", fetch(PYTHON_URL, path)[0], PYTHON_SHA256)
	unzip(path, os.path.join(top, "python"))
	os.unlink(path)
	return os.path.join(top, "python", "python.exe")


def get_ninja(top, work):
	path = os.path.join(work, "ninja.zip")
	check("ninja", fetch(NINJA_URL, path)[0], NINJA_SHA256)
	unzip(path, os.path.join(top, "ninja"))
	os.unlink(path)
	return os.path.join(top, "ninja", "ninja.exe")


def get_mingw(top, work):
	version, names = qt_package(MINGW_DIR, MINGW_PACKAGE)
	for a in names:
		qt_archive(MINGW_DIR, MINGW_PACKAGE, version, a, work,
		           os.path.join(top, "mingw"))
	return os.path.join(top, "mingw", "Tools", "mingw1310_64", "bin")


def get_qt(top, work):
	version, names = qt_package(QT_DIR, QT_PACKAGE)
	dest = os.path.join(top, "qt")
	for a in names:
		if a.startswith(QT_ARCHIVES):
			qt_archive(QT_DIR, QT_PACKAGE, version, a, work, dest)
	# The archives carry no version directory: what the installer would
	# put under 6.8.2/mingw_64 is at the top of each, so that is the kit.
	kit = dest
	if not os.path.isfile(os.path.join(kit, "lib", "pkgconfig",
	                                   "Qt6Core.pc")):
		sys.exit(f"windows_kit: no lib/pkgconfig/Qt6Core.pc under {kit}")
	# The runtime archive puts its DLLs at the kit's root, where nothing
	# on a program's search path looks; the programs are in bin.
	for f in os.listdir(kit):
		if f.lower().endswith(".dll"):
			shutil.copy(os.path.join(kit, f), os.path.join(kit, "bin"))
	return kit


def get_rust(top, work):
	"""rustc, std and the self-contained MinGW bits, merged into one root."""
	channel = tomllib.loads(read(RUST_CHANNEL).decode())
	dest = os.path.join(top, "rust")
	for comp in RUST_COMPONENTS:
		got = channel["pkg"][comp]["target"][RUST_TARGET]
		path = os.path.join(work, comp + ".tar.xz")
		check(comp, fetch(got["xz_url"], path)[0], got["xz_hash"])
		unpacked = os.path.join(work, comp)
		with tarfile.open(path) as tf:
			tf.extractall(unpacked, filter="data")
		os.unlink(path)
		# Each tarball is `<name>-<version>-<target>/<component>/...'
		# beside an installer script; the component directories are what
		# an install merges, so this merges them.
		(top_dir,) = os.listdir(unpacked)
		inner = os.path.join(unpacked, top_dir)
		for part in os.listdir(inner):
			src = os.path.join(inner, part)
			if os.path.isdir(src):
				shutil.copytree(src, dest, dirs_exist_ok=True)
		shutil.rmtree(unpacked)
	say(f"rust {channel['pkg']['rustc']['version'].split()[0]}")
	return os.path.join(dest, "bin", "rustc.exe")


def prepare(top, qt, rust):
	"""Everything fetched and checked under `top'; the variables to set."""
	work = os.path.join(top, "download")
	os.makedirs(work, exist_ok=True)
	env = {"WINEPREFIX": os.path.join(top, "wine"), "WINEDEBUG": "-all"}
	say("python")
	env["FMAKE_WINDOWS_PYTHON"] = get_python(top, work)
	say("ninja")
	env["FMAKE_WINDOWS_NINJA"] = get_ninja(top, work)
	say("Qt's MinGW")
	env["FMAKE_WINDOWS_MINGW"] = get_mingw(top, work)
	if qt:
		say("Qt kit")
		env["FMAKE_QT_WINDOWS"] = get_qt(top, work)
	if rust:
		say("rust")
		env["FMAKE_WINDOWS_RUSTC"] = get_rust(top, work)
	os.rmdir(work)
	return env


def stop_wine(env):
	"""The wineserver outlives the programs it ran, holding the prefix."""
	try:
		subprocess.run(["wineserver", "-k"], env=dict(os.environ, **env),
		               timeout=60, stdout=subprocess.DEVNULL,
		               stderr=subprocess.DEVNULL)
	except (OSError, subprocess.TimeoutExpired):
		pass


def main():
	ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
	# Every case that reads what this fetches: the hosted one, and the
	# cross build against the Qt kit with the system's mingw-w64.
	ap.add_argument("cases", nargs="*",
	                default=["fmake_runs_hosted_on_windows",
	                         "a_real_qt_kit_builds_what_runs_on_windows"])
	ap.add_argument("--keep", metavar="DIR",
	                help="fetch into DIR and leave it there")
	ap.add_argument("--env", action="store_true",
	                help="print the exports and run nothing (needs --keep)")
	ap.add_argument("--no-qt", action="store_true")
	ap.add_argument("--no-rust", action="store_true")
	ap.add_argument("--timeout", type=int, default=3600,
	                help="seconds the selftest run may take (default 3600)")
	args = ap.parse_args()
	for tool in ("wine", "7z"):
		if not shutil.which(tool):
			sys.exit(f"windows_kit: needs {tool}")
	if args.env and not args.keep:
		sys.exit("windows_kit: --env prints paths, so it needs --keep DIR")

	if args.keep:
		top = os.path.abspath(args.keep)
		os.makedirs(top, exist_ok=True)
		owned = None
	else:
		owned = tempfile.TemporaryDirectory(prefix="fmake-windows-kit-")
		top = owned.name
	env = {}
	try:
		env = prepare(top, not args.no_qt, not args.no_rust)
		if args.env:
			for k, v in env.items():
				print(f"export {k}='{v}'")
			return 0
		say(f"running {' '.join(args.cases)}")
		r = subprocess.run([sys.executable, os.path.join(HERE, "selftest"),
		                    "-j1", *args.cases],
		                   cwd=HERE, env=dict(os.environ, **env),
		                   timeout=args.timeout)
		return r.returncode
	finally:
		if env:
			stop_wine(env)
		if owned:
			owned.cleanup()
			say(f"removed {top}")


if __name__ == "__main__":
	sys.exit(main())
