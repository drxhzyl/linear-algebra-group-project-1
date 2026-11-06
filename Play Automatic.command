#!/bin/zsh
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv/bin/python ]]; then
  print 'First install the game following DIGITAL_README.md.'
  read '?Press Enter to close.'
  exit 1
fi
.venv/bin/python run_auto.py
if [[ $? -ne 0 ]]; then read '?The game stopped. Press Enter to close.'; fi
