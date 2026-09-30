-- Snacks zen mode (<leader>uz) tweaks: wider window, darker backdrop, and a
-- dim scope that lights up whole logical blocks instead of paragraphs.
return {
  {
    "folke/snacks.nvim",
    opts = function(_, opts)
      -- Treesitter nodes like markdown `list_item`/`section` end at column 0 of the
      -- *next* item's line, and Snacks counts that line as part of the scope, so the
      -- first line of the next bullet/heading stayed bright. Drop that line.
      local TSScope = require("snacks.scope").TSScope
      local fix = TSScope.fix
      function TSScope:fix()
        fix(self)
        local _, _, end_row, end_col = self.node:range()
        if end_col == 0 and self.to == end_row + 1 and self.to > self.from then
          self.to = self.to - 1
        end
        return self
      end

      return vim.tbl_deep_extend("force", opts, {
        -- What stays bright while zen dims the rest: the innermost enclosing block.
        -- markdown: `list_item` = the bullet incl. nested code blocks, up to the next
        --   bullet; `section` = heading + content, used outside lists.
        -- dart: `function_body` = the whole method/function (closures use
        --   `function_expression_body`, so they don't count); `class_definition` is
        --   used when the cursor is outside any method.
        -- max_size = 1 stops the lit area from growing to the parent block.
        -- injections = false: otherwise markdown's inline injection hides the block nodes.
        dim = {
          scope = {
            min_size = 1,
            max_size = 1,
            siblings = false,
            cursor = false, -- pick the scope by line only; otherwise column 0 selects the outer class
            treesitter = {
              injections = false,
              blocks = { enabled = true, "list_item", "section", "function_body", "class_definition" },
            },
          },
        },
        styles = {
          zen = {
            width = 160, -- >= 1 is columns; < 1 is a fraction of the screen
            -- blend: 0 = solid black, 100 = no dimming. Snacks default is 40.
            backdrop = { transparent = true, blend = 20 },
          },
        },
      })
    end,
  },
}
