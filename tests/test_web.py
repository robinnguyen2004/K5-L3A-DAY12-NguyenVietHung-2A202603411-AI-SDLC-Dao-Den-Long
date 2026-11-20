"""The browser build must embed exactly the current game logic."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_web  # noqa: E402


class WebBuild(unittest.TestCase):
    def test_built_html_in_sync(self):
        with open(build_web.OUT, encoding="utf-8") as f:
            built = f.read().replace("\r\n", "\n")
        self.assertEqual(built, build_web.build(),
                         "web/dao-den-long.html is stale: run python3 tools/build_web.py")
