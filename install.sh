#!/usr/bin/env bash
# Personal dotfiles installer. Safe to re-run.
#
# Machine role comes from the untracked ~/.dotfiles-profile:
#   ROLE=personal-mac | work-mac | vps
# Anything already at a target path is moved to ~/.dotfiles-backup/<timestamp>/ before linking.
set -euo pipefail

DOTFILES="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROFILE="$HOME/.dotfiles-profile"
BACKUP="$HOME/.dotfiles-backup/$(date +%Y%m%d-%H%M%S)"

say() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
note() { printf '    %s\n' "$*"; }
die() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

# --- role / OS -------------------------------------------------------------------------------
[ -f "$PROFILE" ] || die "missing $PROFILE (create it with ROLE=personal-mac|work-mac|vps)"
# shellcheck disable=SC1090
. "$PROFILE"
case "${ROLE:-}" in
  personal-mac | work-mac | vps) ;;
  *) die "invalid ROLE='${ROLE:-}' in $PROFILE" ;;
esac
case "$(uname -s)" in
  Darwin) OS=darwin ;;
  Linux) OS=linux ;;
  *) die "unsupported OS $(uname -s)" ;;
esac
say "role=$ROLE os=$OS"

# --- helpers ---------------------------------------------------------------------------------
# Move an existing path into the backup dir, keeping its $HOME-relative location.
backup() {
  local path="$1" rel dest
  rel="${path#"$HOME"/}"
  dest="$BACKUP/$rel"
  mkdir -p "$(dirname "$dest")"
  mv "$path" "$dest"
  note "backed up $path -> $dest"
}

# link <repo-relative source> <absolute target>
link() {
  local src="$DOTFILES/$1" dst="$2"
  [ -e "$src" ] || die "link source missing: $src"
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
    return 0
  fi
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    backup "$dst"
  fi
  mkdir -p "$(dirname "$dst")"
  ln -s "$src" "$dst"
  note "linked $dst -> $src"
}

# retire <absolute path>: move a file that must no longer exist (e.g. an overriding config) to backup.
retire() {
  if [ -e "$1" ] || [ -L "$1" ]; then
    backup "$1"
  fi
}

if [ "$OS" = darwin ]; then
  APP_SUPPORT="$HOME/Library/Application Support"
fi

# --- repo ------------------------------------------------------------------------------------
say "repo"
git -C "$DOTFILES" config core.hooksPath .githooks
chmod +x "$DOTFILES"/bin/* "$DOTFILES"/.githooks/*

# --- homebrew --------------------------------------------------------------------------------
# Personal Brewfile everywhere; the untracked ~/.Brewfile.local adds work-only packages.
# No upgrades and no cleanup: only installs what is missing. DOTFILES_SKIP_BREW=1 skips this.
if [ "$OS" = darwin ] && [ "${DOTFILES_SKIP_BREW:-0}" != 1 ]; then
  say "homebrew"
  BREW="$(command -v brew || true)"
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [ -n "$BREW" ] || { [ -x "$b" ] && BREW="$b"; }
  done
  [ -n "$BREW" ] || die "Homebrew missing. Install it from https://brew.sh, then re-run."
  for bf in "$DOTFILES/Brewfile" "$HOME/.Brewfile.local"; do
    [ -f "$bf" ] || continue
    if "$BREW" bundle check --no-upgrade --file="$bf" >/dev/null 2>&1; then
      note "$bf: satisfied"
    else
      "$BREW" bundle install --no-upgrade --file="$bf"
    fi
  done
fi

# --- git -------------------------------------------------------------------------------------
say "git"
link git/gitconfig "$HOME/.gitconfig"
link git/ignore "$HOME/.config/git/ignore"
retire "$HOME/.gitignore_global"
[ -f "$HOME/.gitconfig.local" ] || note "no ~/.gitconfig.local (optional machine overrides)"

# --- shells --------------------------------------------------------------------------------
say "zsh / bash"
link zsh/zshenv "$HOME/.zshenv"
link zsh/zshrc "$HOME/.zshrc"
link bash/bashrc "$HOME/.bashrc"
link bash/bash_profile "$HOME/.bash_profile"
# Old startup files, prompt themes and shells that are no longer used.
for f in .zprofile .zlogin .zshrc.backup .zshrc.bak .p10k.zsh .config/fish; do
  retire "$HOME/$f"
done
# ~/.profile is still the login file for sh; on macOS it only held version-manager hooks.
[ "$OS" = darwin ] && retire "$HOME/.profile"

# --- gh --------------------------------------------------------------------------------------
say "gh"
# config.yml only; hosts.yml holds auth tokens and stays local.
link gh/config.yml "${XDG_CONFIG_HOME:-$HOME/.config}/gh/config.yml"

# --- tmux (no longer used) -------------------------------------------------------------------
retire "$HOME/.tmux.conf"

# --- neovim ----------------------------------------------------------------------------------
say "nvim"
link nvim "${XDG_CONFIG_HOME:-$HOME/.config}/nvim"
# lua/local/ (gitignored) holds machine-only plugins/keymaps; lazy-lock.json is gitignored too.

# --- ghostty ---------------------------------------------------------------------------------
if [ "$OS" = darwin ]; then
  say "ghostty"
  link ghostty/config.ghostty "$HOME/.config/ghostty/config.ghostty"
  # The Application Support config overrides the XDG one, so it must go.
  retire "$APP_SUPPORT/com.mitchellh.ghostty/config.ghostty"
  retire "$APP_SUPPORT/com.mitchellh.ghostty/config"
fi

# --- lazygit ---------------------------------------------------------------------------------
say "lazygit"
if [ "$OS" = darwin ]; then
  link lazygit/config.yml "$APP_SUPPORT/lazygit/config.yml"
else
  link lazygit/config.yml "${XDG_CONFIG_HOME:-$HOME/.config}/lazygit/config.yml"
fi

# --- herdr -----------------------------------------------------------------------------------
say "herdr"
link herdr/config.toml "$HOME/.config/herdr/config.toml"
link herdr/plugins.json "$HOME/.config/herdr/plugins.json"
# The helper scripts now live in ~/.dotfiles/bin; drop the old ~/.local/bin copies.
for s in herdr-equalize-panes herdr-worktree-tab; do
  [ -L "$HOME/.local/bin/$s" ] || retire "$HOME/.local/bin/$s"
done

# --- vs code ---------------------------------------------------------------------------------
if [ "$OS" = darwin ]; then
  say "vscode"
  link vscode/settings.json "$APP_SUPPORT/Code/User/settings.json"
  link vscode/keybindings.json "$APP_SUPPORT/Code/User/keybindings.json"
fi

say "done"
[ -d "$BACKUP" ] && note "backups in $BACKUP"
exit 0
