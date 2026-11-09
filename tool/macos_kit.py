#!/usr/bin/env python3
"""Fetch what the macOS cases need, run them, delete it all.

    tool/macos_kit.py                       the macOS cases, then clean up
    tool/macos_kit.py CASE...               those selftest cases instead
    tool/macos_kit.py --keep DIR [CASE...]  fetch into DIR and leave it
    tool/macos_kit.py --keep DIR --env      fetch, print the exports, run nothing

No Mac is reachable from here, and Apple's SDK may not be redistributed, so
this assembles what section 604 found to stand in for one: Qt's own macOS
kit (`qtbase', its frameworks universal binaries), and macOS's C headers,
`libSystem.tbd' and libc++'s headers taken as data from zig's release
tarball -- zig itself is never run. Two things are made by hand, as that
section records: a `__config_site', with `#include <__config_site>'
restored to libc++'s `__config' where zig patches it out, and a
`libc++.tbd' exporting what Qt's frameworks bind from libc++, read from
their dyld info, plus the new/delete and C++ ABI family a program's own
objects reach. A driver around the host's clang and `ld64.lld' puts it
together. Every download is checked against the hash its publisher gives,
and the directory is removed however the run ends. What it sets:

    FMAKE_QT_MACOS     the kit, of the host Qt's version (moc is the host's)
    FMAKE_MACOS_CXX    the driver

Needs clang++, ld64.lld, llvm-objdump, llvm-nm, llvm-ar, 7z and a host
Qt 6 that pkg-config can name.
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windows_kit as kit_common  # noqa: E402  fetch, check, 7z, Qt index

HERE = kit_common.HERE
ZIG_INDEX = "https://ziglang.org/download/index.json"
ZIG_VERSION = "0.13.0"
QT_MAC = "https://download.qt.io/online/qtsdkrepository/mac_x64/desktop"
TARGET = "x86_64-apple-macos12"     # Qt 6.8's own minimum
CASES = ["a_real_qt_kit_links_for_macos"]

CXX_RUNTIME = (
	"__Znwm", "__Znam", "__ZdlPv", "__ZdaPv", "__ZdlPvm", "__ZdaPvm",
	"__ZnwmRKSt9nothrow_t", "__ZnamRKSt9nothrow_t",
	"__ZnwmSt11align_val_t", "__ZdlPvSt11align_val_t",
	"___cxa_allocate_exception", "___cxa_throw", "___cxa_begin_catch",
	"___cxa_end_catch", "___cxa_rethrow", "___gxx_personality_v0",
	"___cxa_free_exception", "___cxa_guard_acquire", "___cxa_guard_release",
	"___cxa_guard_abort", "___cxa_pure_virtual",
)

CONFIG_SITE = """#ifndef _LIBCPP___CONFIG_SITE
#define _LIBCPP___CONFIG_SITE
#define _LIBCPP_ABI_VERSION 1
#define _LIBCPP_ABI_NAMESPACE __1
#define _LIBCPP_PSTL_CPU_BACKEND_SERIAL
#define _LIBCPP_HARDENING_MODE_DEFAULT _LIBCPP_HARDENING_MODE_NONE
#endif
"""


def say(text):
	print(f"macos_kit: {text}", flush=True)


def ld64():
	return (shutil.which("ld64.lld")
	        or next(iter(sorted(glob.glob("/usr/lib/llvm-*/bin/ld64.lld"),
	                            reverse=True)), None))


def host_qt():
	"""`6.8.2' from the host's Qt, which the kit has to match."""
	r = subprocess.run(["pkg-config", "--modversion", "Qt6Core"],
	                   capture_output=True, text=True)
	if r.returncode:
		sys.exit("macos_kit: no host Qt 6 (pkg-config Qt6Core); moc is "
		         "the host's, so the kit has to be its version")
	return r.stdout.strip()


def get_kit(top, work, version):
	tag = "qt6_" + version.replace(".", "")
	base = f"{QT_MAC}/{tag}/{tag}"
	package = f"qt.qt6.{version.replace('.', '')}.clang_64"
	ver, names = kit_common.qt_package(base, package)
	dest = os.path.join(top, "kit")
	for a in names:
		if a.startswith("qtbase-"):
			kit_common.qt_archive(base, package, ver, a, work, dest)
	if not os.path.isdir(os.path.join(dest, "lib", "QtCore.framework")):
		sys.exit(f"macos_kit: no QtCore.framework under {dest}/lib")
	return dest


def get_headers(top, work):
	"""macOS's headers and libc++'s, from zig's tarball, as data."""
	index = json.loads(kit_common.read(ZIG_INDEX))
	got = index[ZIG_VERSION]["x86_64-linux"]
	path = os.path.join(work, "zig.tar.xz")
	kit_common.check("zig", kit_common.fetch(got["tarball"], path)[0],
	                 got["shasum"])
	sdk = os.path.join(top, "sdk")
	inc = os.path.join(sdk, "usr", "include")
	cxx = os.path.join(inc, "c++", "v1")
	want = {"lib/libc/include/any-macos-any/": inc,
	        "lib/libcxx/include/": cxx,
	        "lib/libcxxabi/include/": cxx,
	        "lib/libc/darwin/libSystem.tbd": os.path.join(sdk, "usr", "lib")}
	with tarfile.open(path) as tf:
		for m in tf:
			_, _, rel = m.name.partition("/")
			for prefix, dest in want.items():
				if not rel.startswith(prefix) or not m.isfile():
					continue
				sub = rel[len(prefix):] or os.path.basename(rel)
				out = os.path.join(dest, sub)
				os.makedirs(os.path.dirname(out), exist_ok=True)
				with tf.extractfile(m) as src, open(out, "wb") as fh:
					shutil.copyfileobj(src, fh)
	os.unlink(path)
	# zig passes these as -D flags rather than shipping the file, and
	# patches the include out; a driver that is not zig needs both back.
	config = os.path.join(cxx, "__config")
	text = open(config).read()
	marker = "/* zig patch: instead of including __config_site"
	line = next((l for l in text.splitlines() if l.startswith(marker)), None)
	if line is None:
		sys.exit("macos_kit: libc++'s __config no longer carries zig's "
		         "patch; look at what replaced it")
	open(config, "w").write(text.replace(line, "#include <__config_site>"))
	open(os.path.join(cxx, "__config_site"), "w").write(CONFIG_SITE)
	return sdk


def write_libcxx_stub(sdk, kit):
	"""A libc++.tbd exporting what Qt's frameworks bind from it."""
	syms = set(CXX_RUNTIME)
	for fw in ("QtCore", "QtGui", "QtWidgets"):
		out = subprocess.run(
		    ["llvm-objdump", "--macho", "--arch=x86_64", "--dyld-info",
		     os.path.join(kit, "lib", f"{fw}.framework", fw)],
		    capture_output=True, text=True, timeout=300).stdout
		for line in out.splitlines():
			f = line.split()
			# segment section address pointer type addend dylib symbol
			if len(f) >= 8 and f[6] in ("libc++", "libc++abi"):
				syms.add(f[-1])
	with open(os.path.join(sdk, "usr", "lib", "libc++.tbd"), "w") as fh:
		fh.write("--- !tapi-tbd\ntbd-version: 4\n"
		         "targets: [ x86_64-macos ]\n"
		         "install-name: '/usr/lib/libc++.1.dylib'\n"
		         "exports:\n  - targets: [ x86_64-macos ]\n    symbols: [ "
		         + ", ".join(f"'{s}'" for s in sorted(syms)) + " ]\n...\n")
	return len(syms)


def write_driver(top, sdk, linker):
	path = os.path.join(top, "tc", "x86_64-apple-darwin21-clang++")
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "w") as fh:
		fh.write("#!/bin/sh\n"
		         f'link="-fuse-ld={linker} '
		         '-Wl,-platform_version,macos,12.0,12.0 -Wl,-arch,x86_64"\n'
		         'for a in "$@"; do case "$a" in\n'
		         "-dumpmachine) echo x86_64-apple-darwin21; exit 0;;\n"
		         "-print-multiarch) exit 0;;\n"
		         "-c|-E|-M|-MM) link=;;\n"
		         "esac; done\n"
		         f"exec clang++ -target {TARGET} -isysroot {sdk} "
		         '-stdlib=libc++ $link "$@"\n')
	os.chmod(path, 0o755)
	return path


def prepare(top):
	work = os.path.join(top, "download")
	os.makedirs(work, exist_ok=True)
	version = host_qt()
	say(f"Qt {version} for macOS")
	kit = get_kit(top, work, version)
	say(f"zig {ZIG_VERSION}'s headers, as data")
	sdk = get_headers(top, work)
	say(f"libc++.tbd, {write_libcxx_stub(sdk, kit)} symbols")
	os.rmdir(work)
	return {"FMAKE_QT_MACOS": kit,
	        "FMAKE_MACOS_CXX": write_driver(top, sdk, ld64())}


def main():
	ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
	ap.add_argument("cases", nargs="*", default=CASES)
	ap.add_argument("--keep", metavar="DIR",
	                help="fetch into DIR and leave it there")
	ap.add_argument("--env", action="store_true",
	                help="print the exports and run nothing (needs --keep)")
	ap.add_argument("--timeout", type=int, default=1800,
	                help="seconds the selftest run may take (default 1800)")
	args = ap.parse_args()
	for tool in ("clang++", "llvm-objdump", "llvm-nm", "llvm-ar", "7z",
	             "pkg-config"):
		if not shutil.which(tool):
			sys.exit(f"macos_kit: needs {tool}")
	if not ld64():
		sys.exit("macos_kit: needs ld64.lld")
	if args.env and not args.keep:
		sys.exit("macos_kit: --env prints paths, so it needs --keep DIR")

	if args.keep:
		top = os.path.abspath(args.keep)
		os.makedirs(top, exist_ok=True)
		owned = None
	else:
		owned = tempfile.TemporaryDirectory(prefix="fmake-macos-kit-")
		top = owned.name
	try:
		env = prepare(top)
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
		if owned:
			owned.cleanup()
			say(f"removed {top}")


if __name__ == "__main__":
	sys.exit(main())
