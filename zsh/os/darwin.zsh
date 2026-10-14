# Docker Desktop CLI tools.
path+=(/Applications/Docker.app/Contents/Resources/bin)

# Secrets live in the login keychain; only their lookups are versioned here.
# Add or replace one with: security add-generic-password -U -a "$USER" -s <service> -w
_keychain_export() {
  local value
  value=$(security find-generic-password -s "$2" -w 2>/dev/null) && export "$1=$value"
}
_keychain_export LINEAR_API_KEY linear-api-key
_keychain_export CLAUDE_CODE_OAUTH_TOKEN claude-oauth-token
unfunction _keychain_export
