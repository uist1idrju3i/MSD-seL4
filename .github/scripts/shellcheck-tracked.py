#!/usr/bin/env python3
import os
import re
import subprocess

paths = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
scripts = []
for raw_path in paths:
    if not raw_path:
        continue
    path = os.fsdecode(raw_path)
    if path.startswith("vendor/") or not os.path.isfile(path):
        continue
    with open(path, "rb") as source:
        first_line = source.readline()
    if path.endswith(".sh") or re.match(
        rb"^#!.*(?:/|\s)(?:sh|bash)(?:\s|$)", first_line
    ):
        scripts.append(path)

if scripts:
    subprocess.run(["shellcheck", *scripts], check=True)
