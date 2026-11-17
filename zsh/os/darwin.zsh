# Docker Desktop CLI tools.
path+=(/Applications/Docker.app/Contents/Resources/bin)

# Secrets live in the login keychain; only their lookups are versioned here.
# Add or replace one with: security add-generic-password -U -a "$USER" -s <service> -w
_keychain_export() {
  local value
  value=$(security find-generic-password -s "$2" -w 2>/dev/null) && export "$1=$value"
}
_keychain_export LINEAR_API_KEY linear-api-key
_keychain_export TYPESAFE_API_KEY typesafe-api-key
unfunction _keychain_export

# The Claude Code token is handed to sail only. Exported globally it replaces
# the claude.ai login in every `claude` session, and its user:inference scope
# switches off Claude in Chrome and the claude.ai connectors.
sail() {
  local token
  if token=$(security find-generic-password -s claude-oauth-token -w 2>/dev/null); then
    CLAUDE_CODE_OAUTH_TOKEN=$token command sail "$@"
  else
    command sail "$@"
  fi
}
