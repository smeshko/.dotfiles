return {
  {
    "nvim-lualine/lualine.nvim",
    opts = function(_, opts)
      -- Keep Lazy.nvim's update checks, but do not show their count here.
      opts.sections.lualine_x = vim.tbl_filter(function(component)
        return component[1] ~= require("lazy.status").updates
      end, opts.sections.lualine_x)

      -- LazyVim places the clock in this rightmost section.
      opts.sections.lualine_z = {}
    end,
  },
}
