#!/usr/bin/env python3
"""A real Windows in a virtual machine, for testing fmake hosted there.

    tool/windows_vm.py list                 the versions this knows, and which have a source
    tool/windows_vm.py install [VERSION]    fetch, install unattended, power off
    tool/windows_vm.py run [VERSION] -- CMD boot the installed disk, run CMD over ssh, power off
    tool/windows_vm.py ssh [VERSION]        boot it and give an interactive ssh
    tool/windows_vm.py check [VERSION]      boot it, build fmake's checks in it, power off
    tool/windows_vm.py build [VERSION] -- TREE [FMAKE ARGS]
                                            build a sibling project hosted on Windows,
                                            with Qt's MinGW kit on hand
    tool/windows_vm.py remove [VERSION]     delete that machine (keeps the downloaded image)

Section 632: hull's pc class is the way to a real Windows here, and
hardware never is. Until that class has a TPM, Secure Boot and a CPU
model of its own, this drives qemu and swtpm directly, and its command
line is the reproduction hull was sent. The holder's rule (2026-11-12):
**the TPM is fully emulated, never bypassed** -- software that uses it
has to be tested against one -- so the machine is a q35 with SMM,
OVMF built for Secure Boot with Microsoft's keys enrolled, and swtpm's
TPM 2.0 on the CRB interface. Windows 11's own checks then pass on
their merits, and the answer file carries no LabConfig bypass.

Nothing here ships a Windows image. `list` names every version worth
testing; a version with a source is fetched from Microsoft by that
source, under Microsoft's evaluation licence, which the holder accepted
for this use on 2026-11-12. Sources for the rest are to be added.

Everything lives in `vm/` (git-ignored): `vm/iso/` the downloaded images,
`vm/VERSION/` a machine -- its disk (qcow2, sparse), its UEFI variables,
its TPM state, its ssh key and password. Remove a machine with `remove`;
the images stay until deleted by hand, being slow to fetch again.

Needs qemu-system-x86_64 with KVM, qemu-img, swtpm, OVMF (Debian's
`ovmf`), mtools (the answer file goes on a FAT image as a USB stick,
which Windows Setup searches), and ssh.
"""

import argparse
import hashlib
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VM = os.path.join(HERE, "vm")

# Every Windows worth testing fmake on. A version with no `url' is listed
# so the gap is visible; its source is to be added (holder, 2026-11-12).
# `sha256' is pinned from the first download, Microsoft publishing none
# for its evaluation images; None until then, and said so.
VERSIONS = {
	"win11-26h2-enterprise-eval": {
		"title": "Windows 11 Enterprise Evaluation 26H2 x64 en-US (90 days)",
		"url": ("https://go.microsoft.com/fwlink/?LinkId=2382600"
		        "&clcid=0x409&culture=en-us&country=us"),
		"size": 8225329152,
		# Measured 2026-11-12 from the link above; the file it redirected
		# to is 26300.9457.260913-1737.26h2_ge_release_svc_refresh.
		"sha256": "bc3f24086ebadc94489066b5ad78089e2cf5c3491e90e790bb81a2b199c10e38",
	},
	"win11-ltsc-2024-enterprise-eval": {
		"title": "Windows 11 Enterprise LTSC 2024 Evaluation x64 en-US",
		"url": ("https://go.microsoft.com/fwlink/?linkid=2289029"
		        "&clcid=0x409&culture=en-us&country=us"),
		"size": None,
		"sha256": None,
	},
	"win11-25h2": {"title": "Windows 11 25H2", "url": None},
	"win11-24h2": {"title": "Windows 11 24H2", "url": None},
	"win11-23h2": {"title": "Windows 11 23H2", "url": None},
	"win10-22h2": {"title": "Windows 10 22H2", "url": None},
	"win10-ltsc-2021": {"title": "Windows 10 Enterprise LTSC 2021", "url": None},
	"server-2025": {"title": "Windows Server 2025", "url": None},
	"server-2022": {"title": "Windows Server 2022", "url": None},
}
DEFAULT = "win11-26h2-enterprise-eval"

OVMF_CODE = "/usr/share/OVMF/OVMF_CODE_4M.secboot.fd"
OVMF_VARS = "/usr/share/OVMF/OVMF_VARS_4M.ms.fd"   # Microsoft's keys enrolled
USER = "fmake"
DISK = "64G"            # Windows 11's own minimum; qcow2, so sparse
MEMORY = "8G"
CPUS = "4"
INSTALL_TIMEOUT = 3 * 3600
SSH_TIMEOUT = 900


def say(text):
	print(f"windows_vm: {text}", flush=True)


def die(text):
	sys.exit(f"windows_vm: {text}")


def sha256_of(path):
	h = hashlib.sha256()
	with open(path, "rb") as fh:
		for block in iter(lambda: fh.read(1 << 20), b""):
			h.update(block)
	return h.hexdigest()


def fetch_image(name):
	v = VERSIONS[name]
	if not v.get("url"):
		die(f"{name} has no source yet: {v['title']}")
	os.makedirs(os.path.join(VM, "iso"), exist_ok=True)
	path = os.path.join(VM, "iso", name + ".iso")
	if not os.path.exists(path):
		part = path + ".part"
		say(f"fetching {v['title']}")
		req = urllib.request.Request(v["url"], headers={"User-Agent": "fmake"})
		with urllib.request.urlopen(req, timeout=120) as r, \
		        open(part, "wb") as fh:
			shutil.copyfileobj(r, fh, 1 << 20)
		os.replace(part, path)
	size = os.path.getsize(path)
	if v.get("size") and size != v["size"]:
		die(f"{path} is {size} bytes, not {v['size']}: delete it and fetch again")
	got = sha256_of(path)
	if v.get("sha256") is None:
		say(f"{name}: sha256 {got} (not pinned yet; pin it in VERSIONS)")
	elif got != v["sha256"]:
		die(f"{path}: sha256 {got}, not the pinned {v['sha256']}")
	return path


# The answer file. Nothing in it bypasses a check: TPM 2.0 and Secure
# Boot are real in this machine, and the CPU and memory meet Windows 11's
# minimum. GPT for UEFI; a local administrator; first logon runs the
# setup script from the same stick, which turns on sshd and powers off.
UNATTEND = """<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend"
          xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
 <settings pass="windowsPE">
  <component name="Microsoft-Windows-International-Core-WinPE" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
   <SetupUILanguage><UILanguage>en-US</UILanguage></SetupUILanguage>
   <InputLocale>en-US</InputLocale><SystemLocale>en-US</SystemLocale>
   <UILanguage>en-US</UILanguage><UserLocale>en-US</UserLocale>
  </component>
  <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
   <DiskConfiguration>
    <Disk wcm:action="add">
     <DiskID>0</DiskID><WillWipeDisk>true</WillWipeDisk>
     <CreatePartitions>
      <CreatePartition wcm:action="add"><Order>1</Order><Type>EFI</Type><Size>260</Size></CreatePartition>
      <CreatePartition wcm:action="add"><Order>2</Order><Type>MSR</Type><Size>16</Size></CreatePartition>
      <CreatePartition wcm:action="add"><Order>3</Order><Type>Primary</Type><Extend>true</Extend></CreatePartition>
     </CreatePartitions>
     <ModifyPartitions>
      <ModifyPartition wcm:action="add"><Order>1</Order><PartitionID>1</PartitionID><Format>FAT32</Format><Label>System</Label></ModifyPartition>
      <ModifyPartition wcm:action="add"><Order>2</Order><PartitionID>3</PartitionID><Format>NTFS</Format><Label>Windows</Label><Letter>C</Letter></ModifyPartition>
     </ModifyPartitions>
    </Disk>
   </DiskConfiguration>
   <ImageInstall><OSImage>
    <InstallTo><DiskID>0</DiskID><PartitionID>3</PartitionID></InstallTo>
    <InstallFrom><MetaData wcm:action="add"><Key>/IMAGE/INDEX</Key><Value>1</Value></MetaData></InstallFrom>
   </OSImage></ImageInstall>
   <UserData><AcceptEula>true</AcceptEula><FullName>fmake</FullName><Organization>fmake</Organization></UserData>
  </component>
 </settings>
 <settings pass="specialize">
  <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
   <ComputerName>FMAKE-WIN</ComputerName><TimeZone>UTC</TimeZone>
  </component>
 </settings>
 <settings pass="oobeSystem">
  <component name="Microsoft-Windows-International-Core" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
   <InputLocale>en-US</InputLocale><SystemLocale>en-US</SystemLocale>
   <UILanguage>en-US</UILanguage><UserLocale>en-US</UserLocale>
  </component>
  <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
   <OOBE>
    <HideEULAPage>true</HideEULAPage><HideOEMRegistrationScreen>true</HideOEMRegistrationScreen>
    <HideOnlineAccountScreens>true</HideOnlineAccountScreens><HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE>
    <ProtectYourPC>3</ProtectYourPC>
   </OOBE>
   <UserAccounts><LocalAccounts><LocalAccount wcm:action="add">
    <Name>{user}</Name><Group>Administrators</Group>
    <Password><Value>{password}</Value><PlainText>true</PlainText></Password>
   </LocalAccount></LocalAccounts></UserAccounts>
   <AutoLogon><Enabled>true</Enabled><Username>{user}</Username><LogonCount>1</LogonCount>
    <Password><Value>{password}</Value><PlainText>true</PlainText></Password></AutoLogon>
   <FirstLogonCommands><SynchronousCommand wcm:action="add"><Order>1</Order>
    <CommandLine>cmd /c for %d in (D E F G H I J) do if exist %d:\\fmake-setup.ps1 powershell -NoProfile -ExecutionPolicy Bypass -File %d:\\fmake-setup.ps1</CommandLine>
   </SynchronousCommand></FirstLogonCommands>
  </component>
 </settings>
</unattend>
"""

# First logon. sshd from Windows' own optional feature, the key this
# script made as the only way in, and a record of the TPM and Secure Boot
# as Windows sees them, so `run' can show they are real. Powering off is
# how `install' knows it finished.
SETUP = r"""$ErrorActionPreference = 'Continue'
Start-Transcript -Path C:\fmake-setup.log
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Get-WindowsCapability -Online -Name OpenSSH.Server* | Add-WindowsCapability -Online
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd
if (-not (Get-NetFirewallRule -Name OpenSSH-Server-In-TCP -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -Name OpenSSH-Server-In-TCP -DisplayName 'OpenSSH Server' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
}
# The feature's own rule allows the Private profile only, and qemu's user
# network is classed Public: sshd listened and the firewall dropped every
# connection, found from the console 2026-11-12.
Set-NetFirewallRule -Name OpenSSH-Server-In-TCP -Profile Any
$keys = 'C:\ProgramData\ssh\administrators_authorized_keys'
Copy-Item (Join-Path $here 'fmake.pub') $keys
icacls $keys /inheritance:r /grant 'Administrators:F' /grant 'SYSTEM:F'
Get-Tpm | Out-File C:\fmake-tpm.txt
Confirm-SecureBootUEFI | Out-File C:\fmake-secureboot.txt
Stop-Transcript
Stop-Computer -Force
"""


def machine_dir(name):
	return os.path.join(VM, name)


def make_answer_stick(d, password):
	"""A FAT image holding the answer file, the setup script and the key."""
	img = os.path.join(d, "answer.img")
	stage = os.path.join(d, "answer")
	os.makedirs(stage, exist_ok=True)
	with open(os.path.join(stage, "autounattend.xml"), "w", newline="\r\n") as fh:
		fh.write(UNATTEND.replace("{user}", USER).replace("{password}", password))
	with open(os.path.join(stage, "fmake-setup.ps1"), "w", newline="\r\n") as fh:
		fh.write(SETUP)
	shutil.copyfile(os.path.join(d, "key.pub"), os.path.join(stage, "fmake.pub"))
	with open(img, "wb") as fh:
		fh.truncate(64 << 20)
	subprocess.run(["mformat", "-i", img, "-v", "FMAKEANS", "-F", "::"],
	               check=True)
	for f in sorted(os.listdir(stage)):
		subprocess.run(["mcopy", "-i", img, os.path.join(stage, f), "::"],
		               check=True)
	return img


def free_port():
	with socket.socket() as s:
		s.bind(("127.0.0.1", 0))
		return s.getsockname()[1]


class Machine:
	"""swtpm and qemu for one machine directory, stopped however we leave."""

	def __init__(self, d, install_iso=None, answer=None):
		self.d = d
		self.install_iso = install_iso
		self.answer = answer
		self.port = free_port()
		self.host = "127.0.0.1"
		self.procs = []

	def qemu_argv(self):
		d = self.d
		argv = [
		    "qemu-system-x86_64", "-nodefaults", "-no-user-config",
		    "-name", "fmake-windows",
		    "-machine", "q35,smm=on,accel=kvm", "-cpu", "host",
		    "-smp", CPUS, "-m", MEMORY,
		    "-global", "driver=cfi.pflash01,property=secure,value=on",
		    "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={OVMF_CODE}",
		    "-drive", f"if=pflash,format=raw,unit=1,file={d}/OVMF_VARS.fd",
		    "-chardev", f"socket,id=chrtpm,path={d}/tpm/sock",
		    "-tpmdev", "emulator,id=tpm0,chardev=chrtpm",
		    "-device", "tpm-crb,tpmdev=tpm0",
		    "-device", "ahci,id=ahci",
		    "-drive", f"if=none,id=disk,format=qcow2,file={d}/disk.qcow2",
		    "-device", "ide-hd,drive=disk,bus=ahci.0,bootindex=1",
		    "-nic", f"user,model=e1000e,hostfwd=tcp:127.0.0.1:{self.port}-:22",
		    "-vga", "std", "-display", "none",
		    "-qmp", f"unix:{d}/qmp.sock,server=on,wait=off",
		    "-device", "qemu-xhci,id=xhci",
		]
		if self.install_iso:
			argv += ["-drive", f"if=none,id=cd,media=cdrom,readonly=on,"
			                   f"file={self.install_iso}",
			         "-device", "ide-cd,drive=cd,bus=ahci.1,bootindex=0"]
		if self.answer:
			argv += ["-drive", f"if=none,id=ans,format=raw,file={self.answer}",
			         "-device", "usb-storage,drive=ans,bus=xhci.0,removable=on"]
		return argv

	def start(self):
		d = self.d
		os.makedirs(os.path.join(d, "tpm"), exist_ok=True)
		for sock in ("tpm/sock", "qmp.sock"):
			if os.path.exists(os.path.join(d, sock)):
				os.unlink(os.path.join(d, sock))
		tpm = subprocess.Popen(
		    ["swtpm", "socket", "--tpm2",
		     "--tpmstate", f"dir={d}/tpm",
		     "--ctrl", f"type=unixio,path={d}/tpm/sock",
		     "--terminate", "--log", f"file={d}/tpm.log,level=1"])
		self.procs.append(tpm)
		for _ in range(50):
			if os.path.exists(os.path.join(d, "tpm/sock")):
				break
			time.sleep(0.1)
		with open(os.path.join(d, "command"), "w") as fh:
			fh.write(" ".join(self.qemu_argv()) + "\n")
		qemu = subprocess.Popen(self.qemu_argv(),
		                        stdout=open(os.path.join(d, "qemu.log"), "w"),
		                        stderr=subprocess.STDOUT)
		self.procs.append(qemu)
		self.qemu = qemu
		return qemu

	def qmp(self, *commands):
		"""Each command in turn on a fresh QMP connection; replies discarded."""
		path = os.path.join(self.d, "qmp.sock")
		with socket.socket(socket.AF_UNIX) as s:
			s.settimeout(10)
			s.connect(path)
			f = s.makefile("rw")
			f.readline()
			for cmd in ({"execute": "qmp_capabilities"},) + commands:
				f.write(json.dumps(cmd) + "\n")
				f.flush()
				f.readline()

	def press_any_key(self, seconds=40):
		"""Get past "Press any key to boot from CD or DVD" under UEFI."""
		end = time.time() + seconds
		while time.time() < end and self.qemu.poll() is None:
			try:
				self.qmp({"execute": "send-key",
				          "arguments": {"keys": [{"type": "qcode",
				                                  "data": "ret"}]}})
			except OSError:
				pass
			time.sleep(1)

	def screen(self, name="screen.png"):
		"""A picture of the display, for a run that stalls."""
		out = os.path.join(self.d, name)
		try:
			self.qmp({"execute": "screendump",
			          "arguments": {"filename": out, "format": "png"}})
		except OSError:
			return None
		return out

	def stop(self):
		for p in reversed(self.procs):
			if p.poll() is None:
				p.terminate()
				try:
					p.wait(30)
				except subprocess.TimeoutExpired:
					p.kill()


def ssh_argv(m, *cmd, interactive=False):
	d = m.d
	return (["ssh", "-i", os.path.join(d, "key"), "-p", str(m.port),
	         "-o", "StrictHostKeyChecking=no",
	         "-o", f"UserKnownHostsFile={d}/known_hosts",
	         "-o", "ConnectTimeout=10"]
	        + (["-t"] if interactive else ["-o", "BatchMode=yes"])
	        + [f"{USER}@{m.host}", *cmd])


def wait_for_ssh(m):
	end = time.time() + SSH_TIMEOUT
	while time.time() < end:
		if m.qemu.poll() is not None:
			die(f"the machine stopped before sshd answered: {m.d}/qemu.log")
		r = subprocess.run(ssh_argv(m, "echo", "ready"),
		                   capture_output=True, text=True)
		if r.returncode == 0:
			return
		time.sleep(10)
	m.screen()
	die(f"no ssh after {SSH_TIMEOUT}s; the screen is {m.d}/screen.png")


def install(name):
	for tool in ("qemu-system-x86_64", "qemu-img", "swtpm", "mformat",
	             "mcopy", "ssh-keygen"):
		if not shutil.which(tool):
			die(f"needs {tool}")
	for f in (OVMF_CODE, OVMF_VARS):
		if not os.path.exists(f):
			die(f"needs {f} (Debian: ovmf)")
	if not os.access("/dev/kvm", os.R_OK | os.W_OK):
		die("needs /dev/kvm")
	iso = fetch_image(name)
	d = machine_dir(name)
	if os.path.exists(os.path.join(d, "installed")):
		say(f"{name} is installed already; `remove' it to install again")
		return 0
	os.makedirs(d, exist_ok=True)
	disk = os.path.join(d, "disk.qcow2")
	if os.path.exists(disk):
		os.unlink(disk)
	subprocess.run(["qemu-img", "create", "-q", "-f", "qcow2", disk, DISK],
	               check=True)
	shutil.copyfile(OVMF_VARS, os.path.join(d, "OVMF_VARS.fd"))
	if not os.path.exists(os.path.join(d, "key")):
		subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "",
		                "-C", "fmake-windows-vm", "-f", os.path.join(d, "key")],
		               check=True)
	password = secrets.token_urlsafe(18)
	with open(os.path.join(d, "password"), "w") as fh:
		os.fchmod(fh.fileno(), 0o600)
		fh.write(password + "\n")
	answer = make_answer_stick(d, password)
	m = Machine(d, install_iso=iso, answer=answer)
	try:
		say(f"installing {VERSIONS[name]['title']} (unattended, up to "
		    f"{INSTALL_TIMEOUT // 60} min); the command is in {d}/command")
		m.start()
		m.press_any_key()
		end = time.time() + INSTALL_TIMEOUT
		while m.qemu.poll() is None and time.time() < end:
			time.sleep(30)
			m.screen()
		if m.qemu.poll() is None:
			die(f"install did not finish; the last screen is {d}/screen.png")
		if m.qemu.returncode != 0:
			die(f"qemu exited {m.qemu.returncode}: {d}/qemu.log")
	finally:
		m.stop()
	open(os.path.join(d, "installed"), "w").close()
	say(f"{name} installed; `run {name} -- CMD' boots it")
	return 0


def find_hull():
	"""hull, from $FMAKE_HULL, PATH, or a sibling checkout's build.

    FMAKE_HULL=none boots by qemu and swtpm directly, the stand-in, which
    can take a picture of the screen where hull's pc class cannot.
    """
	if os.environ.get("FMAKE_HULL") == "none":
		return None
	for cand in (os.environ.get("FMAKE_HULL"), shutil.which("hull"),
	             os.path.join(os.path.dirname(HERE), "hull", "build", "hull")):
		if cand and os.access(cand, os.X_OK):
			return cand
	return None


# A booted machine under hull's pc class (hull a1ae527: cpu, tpm,
# uefi-secure and state). Its state directory is the machine directory,
# whose OVMF_VARS.fd and tpm/ are the names hull keeps them under, so the
# machine install made boots with the TPM and variables it was installed
# with -- a new TPM would be a different machine to Windows.
HULL_CONF = """(machine
  (backend pc)
  (hostname "fmake-win")
  (source "image:./disk.qcow2")
  (mutable direct)
  (memory "{memory}")
  (cpus {cpus})
  (network nat)
  (ports (port (host {port}) (guest 22)))
  (tuning (pc (machine q35) (cpu host) (tpm true) (firmware uefi-secure)
              (state "./") (nic e1000e))))
"""


class HullMachine:
	"""The installed disk, booted by `hull run'."""

	def __init__(self, d, hull):
		self.d = d
		self.hull = hull
		self.port = free_port()
		self.host = None

	def start(self):
		conf = os.path.join(self.d, "hull.conf")
		with open(conf, "w") as fh:
			fh.write(HULL_CONF.format(memory=MEMORY, cpus=CPUS, port=self.port))
		self.qemu = subprocess.Popen(
		    [self.hull, "run", "-f", conf],
		    stdout=open(os.path.join(self.d, "hull.log"), "w"),
		    stderr=subprocess.STDOUT, cwd=self.d)
		end = time.time() + 60
		while time.time() < end and self.qemu.poll() is None:
			r = subprocess.run([self.hull, "ps"], capture_output=True, text=True)
			for line in r.stdout.splitlines():
				f = line.split()
				if len(f) >= 5 and f[4] == "running" and "fmake-win" in line:
					self.host = f[1]
			if self.host:
				return self.qemu
			time.sleep(1)
		die(f"hull did not start the machine: {self.d}/hull.log")

	def screen(self, name="screen.png"):
		return None

	def stop(self):
		if self.qemu.poll() is None:
			self.qemu.terminate()
			try:
				self.qemu.wait(60)
			except subprocess.TimeoutExpired:
				self.qemu.kill()


def boot(name):
	d = machine_dir(name)
	if not os.path.exists(os.path.join(d, "installed")):
		die(f"{name} is not installed: `install {name}' first")
	hull = find_hull()
	m = HullMachine(d, hull) if hull else Machine(d)
	if hull:
		say(f"booting {name} under {hull}")
	m.start()
	wait_for_ssh(m)
	return m


def run(name, cmd, interactive=False):
	m = boot(name)
	try:
		return subprocess.run(ssh_argv(m, *cmd,
		                               interactive=interactive)).returncode
	finally:
		subprocess.run(ssh_argv(m, "shutdown", "/s", "/t", "0"),
		               capture_output=True)
		try:
			m.qemu.wait(300)
		except subprocess.TimeoutExpired:
			pass
		m.stop()


# What `check' builds inside Windows, hosted: each tree is written into
# the guest, built by fmake with the MinGW and ninja windows_kit fetches,
# and the result run. A failing line prints FAIL and the script goes on,
# so one run reports every step.
CHECK_TREES = {
	"hello/main.c": '#include <stdio.h>\nint main(void){ puts("hello from windows"); return 0; }\n',
	"lib/greet.h": "int greet(void);\n",
	"lib/greet.c": '#include "greet.h"\nint greet(void){ return 42; }\n',
	"lib/main.c": '#include "greet.h"\nint main(void){ return greet() == 42 ? 0 : 1; }\n',
	"lib/test/greet_test.c": '#include "../greet.h"\nint main(void){ return greet() == 42 ? 0 : 1; }\n',
	"probes/p/one/probe.c": "int main(void){ return 0; }\n",
	"probes/p/two/probe.c": "int main(void){ return 0; }\n",
	# Rust, which sections 614-615 tested hosted only under wine, where a
	# stub findstr forced the ejected ninja rule onto deps = gcc.
	"rs/main.rs": 'mod helper;\nfn main() { println!("rust says {}", helper::seven()); }\n',
	"rs/helper.rs": "pub fn seven() -> i32 { 7 }\n",
	"mix/main.c": '#include <stdio.h>\nint rust_seven(void);\nint main(void){ printf("%d\\n", rust_seven()); return 0; }\n',
	"mix/lib.rs": 'mod helper;\n#[no_mangle]\npub extern "C" fn rust_seven() -> i32 { helper::seven() }\n',
	"mix/helper.rs": "pub fn seven() -> i32 { 7 }\n",
}

CHECK_SCRIPT = r"""@echo off
set K=C:\fmake-check
set PATH=%K%\mingw\Tools\mingw1310_64\bin;%K%\ninja;%K%\rust\bin;%PATH%
set PY=%K%\python\python.exe
echo == TPM and Secure Boot, as Windows saw them at install
type C:\fmake-tpm.txt
type C:\fmake-secureboot.txt
echo == hello
cd /d %K%\trees\hello && %PY% %K%\fmake && hello.exe || echo FAIL hello
echo == library and its test
cd /d %K%\trees\lib && %PY% %K%\fmake && lib.exe && %PY% %K%\fmake test || echo FAIL lib
echo == ejected Makefile under mingw32-make
cd /d %K%\trees\hello && %PY% %K%\fmake --eject > Makefile && mingw32-make && hello.exe || echo FAIL make
echo == ejected build.ninja under ninja
cd /d %K%\trees\lib && %PY% %K%\fmake --eject ninja > build.ninja && ninja && lib.exe || echo FAIL ninja
echo == two probe.c named after their directories
cd /d %K%\trees\probes && %PY% %K%\fmake && one.exe && two.exe || echo FAIL probes
echo == rust program, then its ejected build.ninja
cd /d %K%\trees\rs && %PY% %K%\fmake && rs.exe && %PY% %K%\fmake --eject ninja > build.ninja && ninja -t clean >nul && ninja && rs.exe || echo FAIL rust
echo == a C program linking a Rust crate
cd /d %K%\trees\mix && %PY% %K%\fmake && mix.exe || echo FAIL mix
echo == install to a prefix
cd /d %K%\trees\lib && %PY% %K%\fmake --install --prefix %K%\prefix && dir /s /b %K%\prefix || echo FAIL install
echo == done
"""


def rust_kit_tar():
	"""rustc and std for x86_64-pc-windows-gnu, as windows_kit pins them."""
	tar = os.path.join(VM, "rust.tar")
	if os.path.exists(tar):
		return tar
	sys.path.insert(0, os.path.join(HERE, "tool"))
	import windows_kit  # noqa: E402
	top = os.path.join(VM, "rustkit")
	if os.path.isdir(top) and os.path.dirname(top) == VM:
		shutil.rmtree(top)
	os.makedirs(os.path.join(top, "download"))
	try:
		windows_kit.get_rust(top, os.path.join(top, "download"))
		os.rmdir(os.path.join(top, "download"))
		subprocess.run(["tar", "-C", top, "-cf", tar + ".part", "rust"],
		               check=True)
		os.replace(tar + ".part", tar)
	finally:
		shutil.rmtree(top)
	return tar


def windows_kit_tar():
	"""Python, MinGW and ninja for Windows, fetched once, as one tar."""
	tar = os.path.join(VM, "kit.tar")
	if os.path.exists(tar):
		return tar
	sys.path.insert(0, os.path.join(HERE, "tool"))
	import windows_kit  # noqa: E402  the same pinned fetchers
	top = os.path.join(VM, "kit")
	if os.path.isdir(top) and os.path.dirname(top) == VM:
		shutil.rmtree(top)
	os.makedirs(top)
	try:
		windows_kit.prepare(top, qt=False, rust=False)
		subprocess.run(["tar", "-C", top, "-cf", tar + ".part",
		                "python", "ninja", "mingw"], check=True)
		os.replace(tar + ".part", tar)
	finally:
		shutil.rmtree(top)
	return tar


QT_ADDONS = ("qtpositioning",)


def qt_kit_tar():
	"""Qt's Windows kit for MinGW (qtbase and its runtime), as one tar."""
	tar = os.path.join(VM, "qt.tar")
	if os.path.exists(tar):
		return tar
	sys.path.insert(0, os.path.join(HERE, "tool"))
	import windows_kit  # noqa: E402
	top = os.path.join(VM, "qtkit")
	if os.path.isdir(top) and os.path.dirname(top) == VM:
		shutil.rmtree(top)
	os.makedirs(os.path.join(top, "download"))
	try:
		work = os.path.join(top, "download")
		windows_kit.get_qt(top, work)
		# The add-on modules a sibling uses beyond qtbase: bbq-predictor's
		# locator is QtPositioning, and without it the applet stopped on
		# QGeoPositionInfo, which fmake named as a missing package.
		for addon in QT_ADDONS:
			name = f"qt.qt6.682.addons.{addon}.win64_mingw"
			version, archives = windows_kit.qt_package(windows_kit.QT_DIR, name)
			for a in archives:
				windows_kit.qt_archive(windows_kit.QT_DIR, name, version, a,
				                       work, os.path.join(top, "qt"))
		os.rmdir(work)
		subprocess.run(["tar", "-C", top, "-cf", tar + ".part", "qt"],
		               check=True)
		os.replace(tar + ".part", tar)
	finally:
		shutil.rmtree(top)
	return tar


def build_tree(name, args):
	"""A sibling project from `git archive', built hosted on Windows.

    Section 616's method -- building a real sibling finds what fixtures
    miss -- on a real Windows rather than under wine. The tree is the
    sibling's committed state with its submodules, as tool/sibling_sweep.py
    copies it, so nothing of the real checkout is touched.
    """
	if not args:
		die("build needs a sibling tree after --")
	tree, fmake_args = args[0], args[1:]
	src = tree if os.path.isdir(tree) else os.path.join(os.path.dirname(HERE), tree)
	if not os.path.isdir(os.path.join(src, ".git")):
		die(f"{tree} is not a git checkout")
	tree = os.path.basename(os.path.abspath(src))
	d = machine_dir(name)
	stage = os.path.join(d, "tree")
	if os.path.isdir(stage):
		shutil.rmtree(stage)
	sys.path.insert(0, os.path.join(HERE, "tool"))
	import sibling_sweep  # noqa: E402
	sibling_sweep.unpack(src, os.path.join(stage, tree))
	shutil.copyfile(os.path.join(HERE, "fmake"), os.path.join(stage, "fmake"))
	subprocess.run(["tar", "-C", stage, "-cf", os.path.join(d, "tree.tar"),
	                tree, "fmake"], check=True)
	shutil.rmtree(stage)
	kit, qt = windows_kit_tar(), qt_kit_tar()
	m = boot(name)
	try:
		scp = ["scp", "-q", "-i", os.path.join(d, "key"), "-P", str(m.port),
		       "-o", "StrictHostKeyChecking=no",
		       "-o", f"UserKnownHostsFile={d}/known_hosts", "-o", "BatchMode=yes"]
		guest = f"{USER}@{m.host}:/C:/fmake-build/"
		for argv in (
		    ssh_argv(m, "if exist C:\\fmake-build rmdir /s /q C:\\fmake-build & mkdir C:\\fmake-build"),
		    scp + [kit, qt, os.path.join(d, "tree.tar"), guest],
		    ssh_argv(m, "cd /d C:\\fmake-build && tar -xf kit.tar && tar -xf qt.tar && tar -xf tree.tar"),
		):
			if subprocess.run(argv).returncode:
				die(f"provisioning failed at: {' '.join(argv[-2:])}")
		k = "C:\\fmake-build"
		# `set "X=v"': unquoted, the space before && is part of the value.
		line = (f'set "PATH={k}\\mingw\\Tools\\mingw1310_64\\bin;{k}\\ninja;'
		        f'{k}\\qt\\bin;%PATH%" && set "PKG_CONFIG_PATH={k}\\qt\\lib\\pkgconfig"'
		        f' && set "QT_PLUGIN_PATH={k}\\qt\\plugins" && cd /d {k}\\{tree}'
		        f" && {k}\\python\\python.exe {k}\\fmake {' '.join(fmake_args)}")
		r = subprocess.run(ssh_argv(m, line), capture_output=True, text=True,
		                   errors="replace")
		out = (r.stdout + r.stderr).replace("\r", "")
		print(out)
		with open(os.path.join(d, f"build-{tree}.log"), "w") as fh:
			fh.write(out)
		return r.returncode
	finally:
		subprocess.run(ssh_argv(m, "shutdown", "/s", "/t", "0"),
		               capture_output=True)
		try:
			m.qemu.wait(300)
		except subprocess.TimeoutExpired:
			pass
		m.stop()


def check(name):
	tar, rust = windows_kit_tar(), rust_kit_tar()
	stage = os.path.join(machine_dir(name), "check")
	if os.path.isdir(stage):
		shutil.rmtree(stage)
	for rel, text in CHECK_TREES.items():
		path = os.path.join(stage, "trees", rel)
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, "w") as fh:
			fh.write(text)
	with open(os.path.join(stage, "check.cmd"), "w", newline="\r\n") as fh:
		fh.write(CHECK_SCRIPT)
	shutil.copyfile(os.path.join(HERE, "fmake"), os.path.join(stage, "fmake"))
	subprocess.run(["tar", "-C", stage, "-cf", os.path.join(stage, "..",
	                "check.tar"), "trees", "check.cmd", "fmake"], check=True)
	m = boot(name)
	try:
		d = m.d
		scp = ["scp", "-q", "-i", os.path.join(d, "key"), "-P", str(m.port),
		       "-o", "StrictHostKeyChecking=no",
		       "-o", f"UserKnownHostsFile={d}/known_hosts", "-o", "BatchMode=yes"]
		# SFTP, which scp speaks by default, names a Windows drive /C:/;
		# `C:/' put the files somewhere else and reported success.
		guest = f"{USER}@{m.host}:/C:/fmake-check/"
		steps = [
		    ssh_argv(m, "cmd /c if exist C:\\fmake-check rmdir /s /q C:\\fmake-check & mkdir C:\\fmake-check"),
		    scp + [tar, rust, os.path.join(d, "check.tar"), guest],
		    # sshd hands this to cmd.exe already; a `cmd /c' inside it
		    # ran the `cd' in a shell of its own and the tars in $HOME.
		    ssh_argv(m, "cd /d C:\\fmake-check && tar -xf kit.tar && tar -xf rust.tar && tar -xf check.tar"),
		]
		for argv in steps:
			if subprocess.run(argv).returncode:
				die(f"provisioning failed at: {' '.join(argv[-2:])}")
		r = subprocess.run(ssh_argv(m, "C:\\fmake-check\\check.cmd"),
		                   capture_output=True, text=True, errors="replace")
		out = r.stdout + r.stderr
		print(out)
		with open(os.path.join(d, "check.log"), "w") as fh:
			fh.write(out)
		return 1 if "FAIL" in out else 0
	finally:
		subprocess.run(ssh_argv(m, "shutdown", "/s", "/t", "0"),
		               capture_output=True)
		try:
			m.qemu.wait(300)
		except subprocess.TimeoutExpired:
			pass
		m.stop()


def _exit_on_term(signum, _frame):
	"""SIGTERM as an ordinary exit, so swtpm and qemu are stopped."""
	sys.exit(128 + signum)


def main():
	ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
	ap.add_argument("action", choices=("list", "install", "run", "ssh",
	                                   "check", "build", "remove"))
	ap.add_argument("version", nargs="?", default=DEFAULT)
	argv = sys.argv[1:]
	cmd = argv[argv.index("--") + 1:] if "--" in argv else []
	args = ap.parse_args(argv[:argv.index("--")] if "--" in argv else argv)
	signal.signal(signal.SIGTERM, _exit_on_term)
	if args.action == "list":
		for name, v in VERSIONS.items():
			where = "source known" if v.get("url") else "no source yet"
			have = (" installed" if os.path.exists(
			    os.path.join(machine_dir(name), "installed")) else "")
			print(f"{name:34} {where:14}{have}  {v['title']}")
		return 0
	if args.version not in VERSIONS:
		die(f"no version {args.version!r}; `list' names them")
	if args.action == "install":
		return install(args.version)
	if args.action == "check":
		return check(args.version)
	if args.action == "build":
		return build_tree(args.version, cmd)
	if args.action == "remove":
		d = machine_dir(args.version)
		if os.path.isdir(d) and os.path.dirname(d) == VM:
			shutil.rmtree(d)
			say(f"removed {d}")
		return 0
	if args.action == "ssh":
		return run(args.version, cmd, interactive=True)
	if not cmd:
		die("run needs a command after --")
	return run(args.version, cmd)


if __name__ == "__main__":
	sys.exit(main())
