"""Repository-wide pytest bootstrap.

PyQt defaults to the XCB platform plugin on Linux. CI and sandbox runners have no
X display, so select Qt's offscreen backend before pytest imports a module that
loads PyQt. A local developer with DISPLAY keeps the normal visible backend.
"""
from __future__ import annotations

import os
import sys


# Some managed runners expose a stale DISPLAY value without an X server. Tests never
# require a visible window, so use offscreen by default; a developer can explicitly
# set DATASENSE_QT_TEST_PLATFORM=xcb (or another Qt platform) when diagnosing UI.
if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", os.environ.get("DATASENSE_QT_TEST_PLATFORM", "offscreen"))
