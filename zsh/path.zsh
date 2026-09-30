# Homebrew first, then our own bins in front of it. `typeset -U path` (zshenv) drops duplicates.
if [[ -z "$HOMEBREW_PREFIX" ]]; then
  for _brew in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [[ -x "$_brew" ]] && { eval "$("$_brew" shellenv)"; break; }
  done
  unset _brew
fi

path=("$DOTFILES/bin" "$HOME/.local/bin" $path)
