# fzf key bindings and completion (only with a real terminal).
if [[ -t 0 && -t 1 ]] && (( $+commands[fzf] )); then
  source <(fzf --zsh)
fi

(( $+commands[zoxide] )) && eval "$(zoxide init zsh)"

# fnm (Fast Node Manager): switches Node on cd when a .nvmrc/.node-version is present.
(( $+commands[fnm] )) && eval "$(fnm env --use-on-cd)"
