#!/bin/bash
# Line 1: Model effort | dir@branch (diff) | session | tokens | $cost | worktree
# Line 2: 5h | 7d | cache
#
# All data comes from the JSON Claude Code pipes on stdin — effort.level is the
# live session value (incl. /effort and modelSettings), and rate_limits is
# refreshed on every API response, so no settings.json or OAuth API lookups.

set -f  # disable globbing

input=$(cat)

if [ -z "$input" ]; then
    printf "Claude"
    exit 0
fi

# ANSI colors — mid-luminance so each keeps >=3.5:1 contrast on both light and
# dark backgrounds; neutral text uses the terminal's own foreground (fg).
blue='\033[38;2;0;125;230m'
orange='\033[38;2;215;105;0m'
green='\033[38;2;0;145;0m'
cyan='\033[38;2;30;135;140m'
red='\033[38;2;220;55;55m'
yellow='\033[38;2;175;130;0m'
magenta='\033[38;2;160;75;225m'
fg='\033[39m'
dim='\033[2m'
italic='\033[3m'
reset='\033[0m'
sep=" ${dim}|${reset} "

# Format token counts (e.g., 50k / 200k)
format_tokens() {
    local num=$1
    if [ "$num" -ge 1000000 ]; then
        awk "BEGIN {printf \"%.1fm\", $num / 1000000}"
    elif [ "$num" -ge 1000 ]; then
        awk "BEGIN {printf \"%.0fk\", $num / 1000}"
    else
        printf "%d" "$num"
    fi
}

# Return color escape based on usage percentage
usage_color() {
    local pct=$1
    if [ "$pct" -ge 90 ]; then echo "$red"
    elif [ "$pct" -ge 70 ]; then echo "$orange"
    elif [ "$pct" -ge 50 ]; then echo "$yellow"
    else echo "$green"
    fi
}

# Format a unix epoch as a clock time ("time" -> 14:30, "datetime" -> Sep 28, 09:00)
format_reset_time() {
    local epoch="$1" fmt
    [ -z "$epoch" ] && return
    case "$2" in
        time)     fmt="%H:%M" ;;
        datetime) fmt="%b %-d, %H:%M" ;;
        *)        fmt="%b %-d" ;;
    esac
    date -r "$epoch" +"$fmt" 2>/dev/null || date -d "@$epoch" +"$fmt" 2>/dev/null
}

# ===== Extract data from JSON (single jq pass) =====
# Fields are joined with the ASCII unit separator so empty values keep their slot.
IFS=$'\x1f' read -r model_name cwd size current pct_used total_cost effort_level worktree_name \
    session_name five_hour_pct five_hour_reset_epoch seven_day_pct seven_day_reset_epoch \
    cache_observed cache_expires_epoch cache_hit_pct cache_misses <<< "$(
    echo "$input" | jq -r '
        def pct: if . == null then "" else floor end;
        [
            .model.display_name // "Claude",
            .workspace.current_dir // .cwd // "",
            .context_window.context_window_size // 200000,
            .context_window.total_input_tokens // 0,
            (.context_window.used_percentage // 0 | floor),
            .cost.total_cost_usd // 0,
            .effort.level // "",
            .worktree.name // "",
            (.session_name // "" | gsub("[\\\\\n\r\t\u001f]"; " ")
                | if length > 40 then .[:39] + "…" else . end),
            (.rate_limits.five_hour.used_percentage | pct),
            .rate_limits.five_hour.resets_at // "",
            (.rate_limits.seven_day.used_percentage | pct),
            .rate_limits.seven_day.resets_at // "",
            (.prompt_cache.caching_observed | if . == null then "" else . end),
            .prompt_cache.expires_at // "",
            (.prompt_cache.hit_ratio | if . == null then "" else (. * 100 | round) end),
            .prompt_cache.misses // 0
        ] | map(tostring) | join("\u001f")'
)"

# Context window
[ "$size" -eq 0 ] 2>/dev/null && size=200000
used_tokens=$(format_tokens "$current")
total_tokens=$(format_tokens "$size")

# Cost
cost_display=$(awk "BEGIN {printf \"%.2f\", $total_cost}")

# ============================================================
# LINE 1: Project identity + tokens + cost
# ============================================================
line1=""
line1+="${blue}${model_name}${reset}"

# Effort, colored by intensity (absent when the model doesn't support the effort parameter)
if [ -n "$effort_level" ]; then
    case "$effort_level" in
        low)    effort_color="$dim" ;;
        medium) effort_color="$yellow" ;;
        high)   effort_color="$orange" ;;
        xhigh)  effort_color="$magenta" ;;
        max)    effort_color="$red" ;;
        *)      effort_color="$fg" ;;
    esac
    line1+=" ${effort_color}${effort_level}${reset}"
fi

# Directory + git
if [ -n "$cwd" ]; then
    display_dir="${cwd##*/}"
    git_branch=$(git -C "${cwd}" rev-parse --abbrev-ref HEAD 2>/dev/null)
    line1+="${sep}"
    line1+="${cyan}${display_dir}${reset}"
    if [ -n "$git_branch" ]; then
        line1+="${dim}@${reset}${green}${git_branch}${reset}"
        git_stat=$(git -C "${cwd}" diff --numstat 2>/dev/null | awk '{a+=$1; d+=$2} END {if (a+d>0) printf "+%d -%d", a, d}')
        [ -n "$git_stat" ] && line1+=" ${dim}(${reset}${green}${git_stat%% *}${reset} ${red}${git_stat##* }${reset}${dim})${reset}"
    fi
fi

# Session name (custom /rename or AI-generated title)
if [ -n "$session_name" ]; then
    line1+="${sep}${italic}${fg}${session_name}${reset}"
fi

# Tokens
pct_color=$(usage_color "$pct_used")
line1+="${sep}${orange}${used_tokens}/${total_tokens}${reset} ${dim}(${reset}${pct_color}${pct_used}%${reset}${dim})${reset}"

# Cost
line1+="${sep}${fg}\$${cost_display}${reset}"

# Worktree (conditional)
if [ -n "$worktree_name" ]; then
    line1+="${sep}${orange}⎇ ${worktree_name}${reset}"
fi

# ============================================================
# LINE 2: Rate limits + prompt cache
# ============================================================
line2=""

# Rate limits (only present for Pro/Max, after the session's first API response)
append_limit() {
    local label="$1" pct="$2" reset_epoch="$3" style="$4" reset_fmt
    [ -n "$line2" ] && line2+="${sep}"
    if [ -z "$pct" ]; then
        line2+="${fg}${label}${reset} ${dim}-${reset}"
        return
    fi
    line2+="${fg}${label}${reset} $(usage_color "$pct")${pct}%${reset}"
    reset_fmt=$(format_reset_time "$reset_epoch" "$style")
    [ -n "$reset_fmt" ] && line2+=" ${dim}@${reset_fmt}${reset}"
}
append_limit "5h" "$five_hour_pct" "$five_hour_reset_epoch" time
append_limit "7d" "$seven_day_pct" "$seven_day_reset_epoch" datetime

# Prompt cache: warm/cold (judged against now, so it stays honest if the line is
# stale), expiry time, session hit ratio, misses (appears after the first API response)
line2+="${sep}${fg}cache${reset} "
if [ -z "$cache_observed" ]; then
    line2+="${dim}-${reset}"
elif [ "$cache_observed" != "true" ]; then
    line2+="${dim}off${reset}"
else
    if [ -n "$cache_expires_epoch" ] && [ "$cache_expires_epoch" -gt "$(date +%s)" ]; then
        line2+="${green}warm${reset}"
        cache_expires=$(format_reset_time "$cache_expires_epoch" time)
        [ -n "$cache_expires" ] && line2+=" ${dim}@${cache_expires}${reset}"
    else
        line2+="${red}cold${reset}"
    fi
    # Hit ratio colored inversely to usage: high hit rate is good
    [ -n "$cache_hit_pct" ] && line2+=" $(usage_color $(( 100 - cache_hit_pct )))${cache_hit_pct}%${reset} ${dim}hit${reset}"
    [ "$cache_misses" -gt 0 ] 2>/dev/null && line2+=" ${orange}${cache_misses} miss${reset}"
fi

# ============================================================
# Output
# ============================================================
printf "%b\n%b" "$line1" "$line2"

exit 0
