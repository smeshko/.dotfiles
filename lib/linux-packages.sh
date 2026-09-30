# Linux (Ubuntu/Debian) packages. Sourced by install.sh, so it uses its helpers (say, note, die).
# Only installs what is missing: no upgrades. User-level tools go to ~/.local/bin.
#   apt:      zsh, git, git-lfs, ripgrep, fd, jq, bat, zoxide, just (when the release has it)
#   gh:       GitHub's apt repository
#   releases: neovim, lazygit, fzf, git-delta, gitleaks, fnm (GitHub releases), uv, herdr (installers)

command -v apt-get >/dev/null 2>&1 || die "linux-packages: only apt-based distros are supported"
SUDO=""
[ "$(id -u)" = 0 ] || SUDO="sudo"
LOCAL_BIN="$HOME/.local/bin"
LOCAL_OPT="$HOME/.local/opt"
mkdir -p "$LOCAL_BIN" "$LOCAL_OPT"

case "$(uname -m)" in
  x86_64 | amd64) ARCH=x86_64 ;;
  aarch64 | arm64) ARCH=arm64 ;;
  *) die "linux-packages: unsupported CPU $(uname -m)" ;;
esac

# --- apt ---------------------------------------------------------------------------------------
apt_missing=()
for p in ca-certificates curl gpg unzip python3 zsh git git-lfs ripgrep fd-find jq bat zoxide just; do
  dpkg -s "$p" >/dev/null 2>&1 && continue
  # `just` only exists in newer releases (Ubuntu 24.04+); skip it quietly elsewhere.
  if [ "$p" = just ] && ! apt-cache show just >/dev/null 2>&1; then continue; fi
  apt_missing+=("$p")
done
if [ ${#apt_missing[@]} -gt 0 ]; then
  note "apt: installing ${apt_missing[*]}"
  $SUDO apt-get update -qq
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq "${apt_missing[@]}" >/dev/null
fi
# Debian/Ubuntu rename these two binaries.
if [ ! -e "$LOCAL_BIN/fd" ] && command -v fdfind >/dev/null 2>&1; then ln -s "$(command -v fdfind)" "$LOCAL_BIN/fd"; fi
if [ ! -e "$LOCAL_BIN/bat" ] && command -v batcat >/dev/null 2>&1; then ln -s "$(command -v batcat)" "$LOCAL_BIN/bat"; fi
git lfs install --skip-repo >/dev/null 2>&1 || true

# --- gh (GitHub's apt repository) --------------------------------------------------------------
if ! command -v gh >/dev/null 2>&1; then
  note "gh: adding GitHub CLI apt repository"
  keyring=/etc/apt/keyrings/githubcli-archive-keyring.gpg
  $SUDO mkdir -p -m 755 /etc/apt/keyrings
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | $SUDO tee "$keyring" >/dev/null
  $SUDO chmod go+r "$keyring"
  echo "deb [arch=$(dpkg --print-architecture) signed-by=$keyring] https://cli.github.com/packages stable main" |
    $SUDO tee /etc/apt/sources.list.d/github-cli.list >/dev/null
  $SUDO apt-get update -qq
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq gh >/dev/null
fi

# --- GitHub release binaries -------------------------------------------------------------------
# gh_asset <owner/repo> <regex>: download URL of the latest release asset whose name matches.
gh_asset() {
  curl -fsSL "https://api.github.com/repos/$1/releases/latest" | python3 -c '
import json, re, sys
pattern = re.compile(sys.argv[1])
for asset in json.load(sys.stdin)["assets"]:
    if pattern.search(asset["name"]):
        print(asset["browser_download_url"])
        break
' "$2"
}

# install_release <cmd> <owner/repo> <asset regex for x86_64> <asset regex for arm64>
# Extracts the archive and puts the <cmd> binary it contains into ~/.local/bin.
install_release() {
  local cmd="$1" repo="$2" re url tmp bin
  command -v "$cmd" >/dev/null 2>&1 && return 0
  if [ "$ARCH" = x86_64 ]; then re="$3"; else re="$4"; fi
  url="$(gh_asset "$repo" "$re")"
  [ -n "$url" ] || { note "$cmd: no release asset matching /$re/ in $repo, skipped"; return 0; }
  note "$cmd: installing $(basename "$url")"
  tmp="$(mktemp -d)"
  curl -fsSL "$url" -o "$tmp/asset"
  case "$url" in
    *.zip) unzip -q "$tmp/asset" -d "$tmp/x" ;;
    *) mkdir -p "$tmp/x" && tar -xzf "$tmp/asset" -C "$tmp/x" ;;
  esac
  bin="$(find "$tmp/x" -type f -name "$cmd" | head -1)"
  [ -n "$bin" ] || { rm -rf "$tmp"; die "$cmd: binary not found in $(basename "$url")"; }
  install -m 755 "$bin" "$LOCAL_BIN/$cmd"
  rm -rf "$tmp"
}

install_release lazygit jesseduffield/lazygit '_[Ll]inux_x86_64\.tar\.gz$' '_[Ll]inux_arm64\.tar\.gz$'
install_release fzf junegunn/fzf 'linux_amd64\.tar\.gz$' 'linux_arm64\.tar\.gz$'
install_release delta dandavison/delta 'x86_64-unknown-linux-gnu\.tar\.gz$' 'aarch64-unknown-linux-gnu\.tar\.gz$'
install_release gitleaks gitleaks/gitleaks 'linux_x64\.tar\.gz$' 'linux_arm64\.tar\.gz$'
install_release fnm Schniz/fnm '^fnm-linux\.zip$' '^fnm-arm64\.zip$'

# Neovim ships a whole tree (runtime files), so it goes to ~/.local/opt with a link in ~/.local/bin.
if ! command -v nvim >/dev/null 2>&1; then
  if [ "$ARCH" = x86_64 ]; then nv=nvim-linux-x86_64; else nv=nvim-linux-arm64; fi
  note "nvim: installing $nv"
  rm -rf "${LOCAL_OPT:?}/$nv"
  curl -fsSL "https://github.com/neovim/neovim/releases/latest/download/$nv.tar.gz" | tar -xz -C "$LOCAL_OPT"
  ln -sf "$LOCAL_OPT/$nv/bin/nvim" "$LOCAL_BIN/nvim"
fi

# --- installers ----------------------------------------------------------------------------------
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
command -v herdr >/dev/null 2>&1 || curl -fsSL https://herdr.dev/install.sh | sh

# --- login shell ---------------------------------------------------------------------------------
zsh_path="$(command -v zsh)"
if [ "$(getent passwd "$(id -un)" | cut -d: -f7)" != "$zsh_path" ]; then
  note "login shell: switching to $zsh_path"
  $SUDO chsh -s "$zsh_path" "$(id -un)" || note "chsh failed; run: chsh -s $zsh_path"
fi
