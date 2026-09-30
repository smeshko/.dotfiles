-- Pick tokyonight's style from the background nvim detected from the terminal,
-- instead of LazyVim's fixed "moon" (which forces background=dark on first load).
return {
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = function()
        require("tokyonight").load({ style = vim.o.background == "light" and "day" or "moon" })
      end,
    },
  },
}
