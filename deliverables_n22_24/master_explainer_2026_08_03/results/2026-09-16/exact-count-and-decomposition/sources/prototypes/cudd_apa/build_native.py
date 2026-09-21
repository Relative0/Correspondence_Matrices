"""Build in the prototype directory, without changing any shared installation."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "build/dd-0.6.0"


def run(command, directory, log, env=None):
    print("Running", command, flush=True)
    with (BASE / "results" / log).open("w") as output:
        subprocess.run(command, cwd=directory, env=env, stdout=output,
                       stderr=subprocess.STDOUT, check=True)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("phase", choices=["unpack-debs", "cudd", "extension"])
args = parser.parse_args()
if args.phase == "unpack-debs":
    for package in (BASE / "build/downloads").glob("*.deb"):
        subprocess.run(["dpkg-deb", "-x", str(package), str(BASE / "build/deps")], check=True)
elif args.phase == "cudd":
    run(["./configure", "CFLAGS=-fPIC -std=c99 -O3"], SOURCE / "cudd-3.0.0", "cudd-configure.log")
    run(["make", "-j4"], SOURCE / "cudd-3.0.0", "cudd-build.log")
else:
    from patch_dd import patch
    if "def count_double(" not in (SOURCE / "dd/cudd.pyx").read_text():
        patch(SOURCE, BASE / "dd-0.6.0-apa.patch")
    environment = os.environ.copy()
    include = BASE / "build/deps/usr/include"
    environment["CFLAGS"] = f"-I{include} -I{include}/python3.12"
    run([sys.executable, "setup.py", "build_ext", "--inplace", "--cudd"],
        SOURCE, "extension-build.log", environment)
