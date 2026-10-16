-- Markdown: plain text while editing; <leader>mv opens a read-only rendered view.
-- lua/mdview.lua renders the buffer (unsaved edits included) with treesitter into a
-- normal scratch buffer, so every motion works: {/} jump between blocks, ]]/[[
-- between headings, <CR> or gx follows the link under the cursor. The window is
-- zen-styled: full height, no border, line numbers. It re-renders when resized.
-- q closes it.

-- Open a link: URLs in the browser, #anchors as headings, paths relative to the file.
local function follow(dest, dir, view)
  if dest:match("^%a[%w+.-]*:") then
    vim.ui.open(dest)
  elseif dest:sub(1, 1) == "#" then
    local want = dest:sub(2):lower():gsub("[^%w]", "")
    for _, row in ipairs(view.headings) do
      local l = vim.api.nvim_buf_get_lines(view.buf, row - 1, row, false)[1] or ""
      if l:lower():gsub("[^%w]", "") == want then
        vim.cmd("normal! m'")
        vim.api.nvim_win_set_cursor(0, { row, 0 })
        return
      end
    end
  else
    local path = vim.fs.normalize(dir .. "/" .. dest:gsub("#.*$", ""))
    view.win:close()
    vim.cmd.edit(vim.fn.fnameescape(path))
  end
end

local function preview()
  local mdview = require("mdview")
  local relnum = vim.wo.relativenumber -- copy the editor window's numbering
  local src = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  local src_row = vim.api.nvim_win_get_cursor(0)[1] - 1
  local dir = vim.fn.expand("%:p:h")

  local buf = vim.api.nvim_create_buf(false, true)
  local win = Snacks.win({
    style = "zen",
    buf = buf,
    -- Same sizing as zen itself: top row to just above the command line.
    row = 0,
    height = function() return vim.o.lines - vim.o.cmdheight end,
    keys = { q = "close" },
    bo = { modifiable = false, filetype = "mdview" },
    wo = { number = true, relativenumber = relnum, cursorline = true, signcolumn = "no",
      foldcolumn = "0", list = false, wrap = true, linebreak = true, breakindent = true,
      sidescrolloff = 0, conceallevel = 0, spell = false },
  })
  local view = { buf = buf, win = win, headings = {}, links = {}, src = {} }
  local ns = vim.api.nvim_create_namespace("mdview")

  -- Render at the window's text width; keep the cursor on the same source line.
  local function draw(row)
    local info = vim.fn.getwininfo(win.win)[1]
    local width = info.width - info.textoff - 1
    mdview.highlights()
    local R = mdview.render(src, width)
    view.headings, view.links, view.src = R.headings, R.links, R.src
    vim.bo[buf].modifiable = true
    vim.api.nvim_buf_set_lines(buf, 0, -1, false, R.lines)
    vim.bo[buf].modifiable = false
    vim.api.nvim_buf_clear_namespace(buf, ns, 0, -1)
    for _, m in ipairs(R.marks) do
      vim.api.nvim_buf_set_extmark(buf, ns, m[1], m[2],
        { end_col = m[3], hl_group = m[4], strict = false })
    end
    local target = 1
    for i = 1, #R.lines do
      if (R.src[i] or 0) <= row then target = i else break end
    end
    vim.api.nvim_win_set_cursor(win.win, { target, 0 })
  end
  local ok, err = pcall(draw, src_row)
  if not ok then
    win:close()
    vim.notify("mdview: " .. tostring(err), vim.log.levels.ERROR)
    return
  end
  vim.api.nvim_create_autocmd("WinResized", {
    group = vim.api.nvim_create_augroup("mdview_resize", { clear = true }),
    callback = function()
      if not vim.api.nvim_win_is_valid(win.win) then return true end
      if not vim.tbl_contains(vim.v.event.windows or {}, win.win) then return end
      draw(view.src[vim.api.nvim_win_get_cursor(win.win)[1]] or 0)
    end,
  })

  -- ]] / [[ : next / previous heading (with a count, and into the jumplist).
  local function jump(dir_)
    local rows, target = view.headings, vim.fn.line(".")
    for _ = 1, vim.v.count1 do
      local found
      for i = dir_ > 0 and 1 or #rows, dir_ > 0 and #rows or 1, dir_ do
        if (dir_ > 0 and rows[i] > target) or (dir_ < 0 and rows[i] < target) then found = rows[i] break end
      end
      if not found then break end
      target = found
    end
    if target ~= vim.fn.line(".") then
      vim.cmd("normal! m'")
      vim.api.nvim_win_set_cursor(0, { target, 0 })
    end
  end
  vim.keymap.set({ "n", "x" }, "]]", function() jump(1) end, { buffer = buf, desc = "Next Heading" })
  vim.keymap.set({ "n", "x" }, "[[", function() jump(-1) end, { buffer = buf, desc = "Previous Heading" })

  local function open_link()
    local row, col = unpack(vim.api.nvim_win_get_cursor(0))
    for _, l in ipairs(view.links) do
      if l[1] == row - 1 and col >= l[2] and col < l[3] then return follow(l[4], dir, view) end
    end
  end
  vim.keymap.set("n", "<CR>", open_link, { buffer = buf, desc = "Follow Link" })
  vim.keymap.set("n", "gx", open_link, { buffer = buf, desc = "Follow Link" })
end

return {
  -- No in-buffer rendering (it fought with scrolling).
  { "MeanderingProgrammer/render-markdown.nvim", enabled = false },
  -- No markdownlint: diagnostics are off for markdown (see config/autocmds.lua).
  {
    "mfussenegger/nvim-lint",
    optional = true,
    opts = function(_, opts)
      opts.linters_by_ft = opts.linters_by_ft or {}
      opts.linters_by_ft.markdown = {}
    end,
  },
  {
    "folke/snacks.nvim",
    keys = {
      { "<leader>mv", preview, ft = "markdown", desc = "Markdown View (rendered)" },
    },
  },
}
