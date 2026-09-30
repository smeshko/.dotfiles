return {
  "folke/snacks.nvim",
  opts = {
    -- Show dot-files and git-ignored files in the file explorer by default
    explorer = {
      hidden = true,
      ignored = true, -- show .agents/brainstorms/ and other git-ignored folders
    },
    -- Include dot-files and git-ignored files in file/grep searches
    picker = {
      sources = {
        files = {
          hidden = true,
          ignored = true,
        },
        grep = {
          hidden = true,
          ignored = true,
        },
        explorer = {
          hidden = true,
          ignored = true,
        },
      },
    },
  },
}
