export BAT_THEME="TwoDark"
export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
export FZF_DEFAULT_OPTS='--height 40% --layout=reverse --border --cycle'

# Treat path separators as word boundaries so Option+Backspace deletes
# one path component at a time instead of the entire path.
WORDCHARS=${WORDCHARS//\//}
