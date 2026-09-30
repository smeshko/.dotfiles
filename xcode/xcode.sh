#!/usr/bin/env bash
# Xcode editor preferences. Safe to re-run. Xcode rewrites its prefs on quit, so quit it first.
set -euo pipefail
d=com.apple.dt.Xcode

if pgrep -xq Xcode; then
  echo "    xcode.sh: Xcode is running; quit it and re-run install.sh to apply the preferences" >&2
  exit 0
fi

defaults write $d DVTTextShowMinimap -bool false                 # no minimap
defaults write $d IDEFileExtensionDisplayMode -int 2             # always show file extensions
defaults write $d ShowBuildOperationDuration -bool true          # build time in the activity view
defaults write $d DVTTextEditorTrimTrailingWhitespace -bool true # trim trailing whitespace
defaults write $d DVTTextShowPageGuide -bool true                # page guide ...
defaults write $d DVTTextPageGuideLocation -int 120              # ... at column 120
