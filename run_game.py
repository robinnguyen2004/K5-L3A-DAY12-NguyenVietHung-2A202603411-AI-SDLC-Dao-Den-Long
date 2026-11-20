#!/usr/bin/env python3
"""Start the 3D game: python run_game.py  (add --demo to watch the autopilot)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lantern_island.game import main  # noqa: E402

if __name__ == "__main__":
    main()
