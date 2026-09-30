-- render-markdown tweaks (on top of LazyVim's lang.markdown extra).
-- Goals: no text jumping, code blocks that stand out, calmer inline code.

-- Mix two #rrggbb colours; t = 0 -> a, t = 1 -> b.
local function blend(a, b, t)
  local function ch(c, i) return tonumber(c:sub(i, i + 1), 16) end
  local out = "#"
  for _, i in ipairs({ 2, 4, 6 }) do
    out = out .. string.format("%02x", math.floor(ch(a, i) * (1 - t) + ch(b, i) * t + 0.5))
  end
  return out
end

local function hex(n) return n and string.format("#%06x", n) or nil end

-- Derive colours from the active theme, so they work for light and dark themes alike.
local function set_highlights()
  local normal = vim.api.nvim_get_hl(0, { name = "Normal", link = false })
  local bg, fg = hex(normal.bg), hex(normal.fg)
  if not (bg and fg) then return end
  local accent = hex(vim.api.nvim_get_hl(0, { name = "Constant", link = false }).fg) or fg

  -- Code blocks: a clearly distinct panel (blend toward the text colour, so it's
  -- lighter on dark themes and darker on light themes).
  local block = blend(bg, fg, 0.08)
  vim.api.nvim_set_hl(0, "RenderMarkdownCode", { bg = block })
  vim.api.nvim_set_hl(0, "RenderMarkdownCodeBorder", { bg = blend(bg, fg, 0.14) })
  vim.api.nvim_set_hl(0, "RenderMarkdownCodeInfo", { fg = blend(bg, fg, 0.6), bg = blend(bg, fg, 0.14) })

  -- Inline code: coloured text on a faint chip instead of a selection-like blue box.
  vim.api.nvim_set_hl(0, "RenderMarkdownCodeInline", { fg = accent, bg = blend(bg, fg, 0.07) })
end

return {
  {
    "MeanderingProgrammer/render-markdown.nvim",
    -- Replaces LazyVim's config (same setup + <leader>um toggle), then applies our
    -- highlights after the plugin's own defaults, and again after every theme change.
    config = function(_, opts)
      require("render-markdown").setup(opts)
      Snacks.toggle({
        name = "Render Markdown",
        get = require("render-markdown").get,
        set = require("render-markdown").set,
      }):map("<leader>um")
      set_highlights()
      vim.api.nvim_create_autocmd("ColorScheme", {
        group = vim.api.nvim_create_augroup("render_markdown_hl", { clear = true }),
        callback = function() vim.schedule(set_highlights) end,
      })
    end,
    opts = {
      -- Never swap the cursor line back to raw markdown (the horizontal jump).
      anti_conceal = { enabled = false },
      -- Keep rendering in insert mode too, so entering insert doesn't reflow the buffer.
      render_modes = true,
      code = {
        -- Keep the ``` fence lines as real rows (the header and footer bars of the block)
        -- instead of hiding them, which caused the vertical jump.
        border = "thick",
        width = "block",
        left_pad = 2,
        right_pad = 4,
        min_width = 60,
        inline_pad = 1,
      },
    },
  },
}
