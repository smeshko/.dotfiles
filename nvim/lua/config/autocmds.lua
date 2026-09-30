-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
--
-- Add any additional autocmds here
-- with `vim.api.nvim_create_autocmd`
--
-- Or remove existing autocmds by their group name (which is prefixed with `lazyvim_` for the defaults)
-- e.g. vim.api.nvim_del_augroup_by_name("lazyvim_wrap_spell")

-- Follow the terminal's light/dark background while nvim is running.
-- nvim already enables DEC mode 2031 (theme-change notifications; Ghostty sends
-- them and herdr forwards them) and re-queries the terminal's background colour
-- (OSC 11) 100ms after each notification. Through herdr that first re-query is
-- often answered with the *old* colour, so whenever a reply arrives we ask a
-- few more times over the next seconds to pick up the settled value. nvim's
-- built-in handler turns each reply into 'background'; tokyonight follows.
-- Nothing runs while idle.
local settling = false
vim.api.nvim_create_autocmd("TermResponse", {
  group = vim.api.nvim_create_augroup("bg_requery", { clear = true }),
  callback = function(ev)
    if settling or not ev.data.sequence:find("^\27%]11;") then return end
    settling = true
    local function ask() io.stdout:write("\27]11;?\7") end
    vim.defer_fn(ask, 700)
    vim.defer_fn(ask, 1500)
    vim.defer_fn(ask, 3000)
    vim.defer_fn(function() settling = false end, 3500)
  end,
})
