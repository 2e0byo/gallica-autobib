#!/usr/bin/env python

import re
from subprocess import Popen
from sys import argv

VIEWER = "zathura"
# argv = "AssertionError: Pdf files /tmp/pytest-of-john/pytest-255/test_process_pdf_no_preserve0/test_process/test_process_pdf_no_preserve.obtained.pdf and /tmp/pytest-of-john/pytest-255/test_process_pdf_no_preserve0/test_process/test_process_pdf_no_preserve.pdf differ"

inp = " ".join(argv[1:])
a, b = re.search(r"Pdf files (.+) and (.+) differ", inp).groups()
Popen(["zathura", a])
Popen(["zathura", b])
