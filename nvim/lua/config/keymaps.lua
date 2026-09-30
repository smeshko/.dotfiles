-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

-- ─────────────────────────────────────────────────────────────────────────────
-- VS Code muscle memory
-- Sources: ~/Library/Application Support/Code/User/keybindings.json + VS Code defaults.
-- Only chords that actually reach Neovim through Ghostty → herdr are mapped here.
--   Ghostty keeps: cmd+f/g/e/j/a/n/q, cmd+z / cmd+shift+z, cmd+enter, cmd+shift+enter,
--                  cmd+shift+p, cmd+= / cmd+- / cmd+0, cmd+alt+1..9, cmd+arrows
--   herdr keeps:   cmd+t/w/k/d, cmd+shift+d/w/g, cmd+[ ], cmd+1..9, cmd+alt+arrows, alt+up/down
-- Verified 2026-09-16 with `herdr pane send-keys`: chords arrive as <D-…> / <C-…> / <A-…>.
-- cmd+shift+f reaches nvim only because Ghostty has `keybind = cmd+shift+f=unbind`.
-- ─────────────────────────────────────────────────────────────────────────────
local map = vim.keymap.set
local nix = { "n", "i", "x" }

-- Find & search ───────────────────────────────────────────────────────────────
map(nix, "<D-S-o>", function() LazyVim.pick("files")() end, { desc = "Find Files (VS Code Quick Open)" })
map(nix, "<D-p>", function() LazyVim.pick("files")() end, { desc = "Find Files (VS Code cmd+p)" })
map(nix, "<D-S-f>", function() LazyVim.pick("grep")() end, { desc = "Search in Files (VS Code cmd+shift+f)" })
map(nix, "<D-S-e>", function() Snacks.explorer() end, { desc = "Explorer (VS Code cmd+shift+e)" })
map(nix, "<D-S-m>", "<cmd>Trouble diagnostics toggle<cr>", { desc = "Problems (VS Code cmd+shift+m)" })
-- Ghostty owns cmd+shift+p (its command palette). Unbind it there and this becomes VS Code's palette.
map(nix, "<D-S-p>", function() Snacks.picker.commands() end, { desc = "Command Palette (VS Code cmd+shift+p)" })

-- Panels ──────────────────────────────────────────────────────────────────────
map(nix, "<D-A-0>", function() Snacks.terminal(nil, { cwd = LazyVim.root() }) end, { desc = "Toggle Terminal (Ivo: cmd+alt+0)" })
map("t", "<D-A-0>", "<cmd>close<cr>", { desc = "Hide Terminal" })
map(nix, "<D-Bslash>", "<cmd>vsplit<cr>", { desc = "Split Editor Right (VS Code cmd+\\)" })

-- Save ────────────────────────────────────────────────────────────────────────
map({ "n", "i", "x", "s" }, "<D-s>", "<cmd>w<cr><esc>", { desc = "Save File (VS Code cmd+s)" })
map({ "n", "i", "x", "s" }, "<D-S-s>", "<cmd>wa<cr><esc>", { desc = "Save All (Ivo: cmd+shift+s)" })

-- Edit ────────────────────────────────────────────────────────────────────────
map("n", "<D-/>", "gcc", { desc = "Toggle Comment (VS Code cmd+/)", remap = true })
map("x", "<D-/>", "gc", { desc = "Toggle Comment (VS Code cmd+/)", remap = true })
map("i", "<D-/>", "<C-o>gcc", { desc = "Toggle Comment (VS Code cmd+/)", remap = true })
map("n", "<D-S-k>", '"_dd', { desc = "Delete Line (VS Code cmd+shift+k)" })
map("i", "<D-S-k>", '<C-o>"_dd', { desc = "Delete Line (VS Code cmd+shift+k)" })
map("x", "<D-S-k>", '"_d', { desc = "Delete Selection (VS Code cmd+shift+k)" })
-- Ghostty owns cmd+z / cmd+shift+z (undo/redo closed tabs). Unbind them there if you want these.
map("n", "<D-z>", "u", { desc = "Undo (VS Code cmd+z)" })
map("i", "<D-z>", "<C-o>u", { desc = "Undo (VS Code cmd+z)" })
map("n", "<D-S-z>", "<C-r>", { desc = "Redo (VS Code cmd+shift+z)" })
map("i", "<D-S-z>", "<C-o><C-r>", { desc = "Redo (VS Code cmd+shift+z)" })

-- Code intelligence ───────────────────────────────────────────────────────────
map({ "n", "x", "i" }, "<C-.>", function() vim.lsp.buf.code_action() end, { desc = "Quick Fix (Ivo: ctrl+.)" })
map("n", "<C-,>", function() vim.diagnostic.jump({ count = 1, float = true }) end, { desc = "Next Problem (Ivo: ctrl+,)" })
map("n", "<F2>", vim.lsp.buf.rename, { desc = "Rename Symbol (VS Code F2)" })
map("n", "<F12>", vim.lsp.buf.definition, { desc = "Go to Definition (VS Code F12)" })
map("n", "<S-F12>", vim.lsp.buf.references, { desc = "Find References (VS Code shift+F12)" })
map("n", "<A-CR>", function() vim.cmd.vsplit(); vim.lsp.buf.definition() end, { desc = "Definition to the Side (Ivo: alt+enter)" })
map("i", "<A-Space>", function() require("blink.cmp").show() end, { desc = "Trigger Suggest (Ivo: alt+space)" })

-- Git ─────────────────────────────────────────────────────────────────────────
map("n", "<D-S-r>", function() require("gitsigns").reset_hunk() end, { desc = "Revert Change (Ivo: cmd+shift+r)" })
map("x", "<D-S-r>", ":Gitsigns reset_hunk<cr>", { desc = "Revert Selection (Ivo: cmd+shift+r)" })
map("n", "<C-S-A-s>", function() require("gitsigns").stage_buffer() end, { desc = "Stage File (Ivo: ctrl+shift+alt+s)" })

-- Machine-local keymaps (untracked, lua/local/keymaps.lua) ─────────────────────
if vim.uv.fs_stat(vim.fn.stdpath("config") .. "/lua/local/keymaps.lua") then require("local.keymaps") end
