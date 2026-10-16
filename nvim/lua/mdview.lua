-- Markdown -> styled plain text, for the read-only <leader>mv view.
-- Treesitter parses the source (block + inline grammars); we write text lines and
-- highlight spans ourselves, so spacing is ours: blank lines in the source stay
-- blank lines (collapsed to one), list items and quotes wrap with a hanging indent.
--
-- M.render(src_lines, width) -> {
--   lines = { string },            -- text, already wrapped to width
--   marks = { {row, col, end_col, hl} },  -- 0-based rows, byte columns
--   links = { {row, col, end_col, dest} },
--   headings = { row },             -- 1-based rows of headings
--   src = { [row1] = src_row0 },     -- source row each rendered line comes from
-- }

local M = {}

local strw = vim.fn.strdisplaywidth

-- Highlight groups; `default` so a colorscheme or the user can override them.
function M.highlights()
  local function link(name, to, extra)
    vim.api.nvim_set_hl(0, name, vim.tbl_extend("force", { link = to, default = true }, extra or {}))
  end
  for i = 1, 6 do
    link("MdViewH" .. i, "@markup.heading." .. i .. ".markdown")
  end
  link("MdViewStrong", "@markup.strong")
  link("MdViewEm", "@markup.italic")
  link("MdViewStrike", "@markup.strikethrough")
  link("MdViewCode", "@markup.raw.markdown_inline")
  link("MdViewCodeBlock", "ColorColumn")
  link("MdViewCodeLang", "Comment")
  link("MdViewLink", "@markup.link.label.markdown_inline")
  link("MdViewQuote", "@markup.list")
  link("MdViewMarker", "@markup.list")
  link("MdViewChecked", "@markup.list.checked")
  link("MdViewUnchecked", "@markup.list.unchecked")
  link("MdViewDim", "Comment")
  link("MdViewMetaKey", "@property")
  link("MdViewBorder", "Comment")
end

-- Heading styles (prefix, upper-case) (H1 and H2 upper-case).
local HEADING = {
  { prefix = "", upper = true },
  { prefix = "▌ ", upper = true },
  { prefix = "▎ " },
  { prefix = "› " },
  { prefix = "› " },
  { prefix = "› " },
}
local BULLETS = { "• ", "◦ ", "▪ " }

---------------------------------------------------------------------------
-- Inline: one logical line of markdown -> text + marks (+ links)
---------------------------------------------------------------------------

local function inline(text)
  local out, marks, links, len = {}, {}, {}, 0
  local function put(s)
    if s ~= "" then
      out[#out + 1] = s
      len = len + #s
    end
  end
  local ok, parser = pcall(vim.treesitter.get_string_parser, text, "markdown_inline")
  if not ok then return text, {}, {} end
  local root = parser:parse()[1]:root()

  local walk
  local function children(node)
    local _, pos = node:start()
    for child in node:iter_children() do
      local _, cs, _, ce = child:range()
      put(text:sub(pos + 1, cs))
      walk(child)
      pos = ce
    end
    local _, _, _, ec = node:range()
    put(text:sub(pos + 1, ec))
  end
  local function styled(node, hl, fn)
    local s = len
    fn()
    if len > s then marks[#marks + 1] = { s, len, hl } end
  end
  local function find(node, ...)
    local want = {}
    for _, t in ipairs({ ... }) do want[t] = true end
    for child in node:iter_children() do
      if want[child:type()] then return child end
    end
  end
  local function raw(node) return vim.treesitter.get_node_text(node, text) end

  walk = function(node)
    local t = node:type()
    if t == "emphasis_delimiter" or t == "code_span_delimiter" then
      return
    elseif t == "code_span" then
      local s = raw(node):gsub("^`+", ""):gsub("`+$", "")
      if s:match("^ .* $") and s:match("%S") then s = s:sub(2, -2) end
      styled(node, "MdViewCode", function() put(s) end)
    elseif t == "backslash_escape" then
      put(raw(node):sub(2))
    elseif t == "emphasis" then
      styled(node, "MdViewEm", function() children(node) end)
    elseif t == "strong_emphasis" then
      styled(node, "MdViewStrong", function() children(node) end)
    elseif t == "strikethrough" then
      styled(node, "MdViewStrike", function() children(node) end)
    elseif t == "inline_link" or t == "full_reference_link" or t == "collapsed_reference_link"
      or t == "shortcut_link" or t == "image" then
      local label = find(node, "link_text", "image_description")
      local dest = find(node, "link_destination")
      local s = len
      styled(node, "MdViewLink", function()
        if t == "image" then put("🖼 ") end
        if label then children(label) else put(raw(node)) end
      end)
      if dest then links[#links + 1] = { s, len, raw(dest) } end
    elseif t == "uri_autolink" or t == "email_autolink" then
      local s = len
      local url = raw(node):gsub("^<", ""):gsub(">$", "")
      styled(node, "MdViewLink", function() put(url) end)
      links[#links + 1] = { s, len, url }
    elseif t == "html_tag" then
      styled(node, "MdViewDim", function() put(raw(node)) end)
    elseif t == "entity_reference" or t == "numeric_character_reference" then
      local s = raw(node)
      local n = s:match("^&#[xX](%x+);$")
      n = n and tonumber(n, 16) or tonumber(s:match("^&#(%d+);$") or "")
      local named = { amp = "&", lt = "<", gt = ">", quot = '"', apos = "'", nbsp = " ", mdash = "—", ndash = "–", hellip = "…", copy = "©" }
      put(n and vim.fn.nr2char(n) or named[s:match("^&(%w+);$") or ""] or s)
    elseif node:child_count() > 0 then
      children(node)
    else
      put(raw(node))
    end
  end
  walk(root)
  return table.concat(out), marks, links
end

-- Word-wrap `text` to `width` cells. Returns byte ranges {from, to} (1-based, inclusive).
local function wrap(text, width)
  local ranges, ls, le, w = {}, nil, nil, 0
  for s, word, e in text:gmatch("()(%S+)()") do
    local ww = strw(word)
    if ls and w + 1 + ww > width then
      ranges[#ranges + 1] = { ls, le }
      ls = nil
    end
    if not ls then
      ls, w = s, ww
    else
      w = w + (s - le - 1) + ww
    end
    le = e - 1
  end
  if ls then ranges[#ranges + 1] = { ls, le } end
  if #ranges == 0 then ranges[1] = { 1, 0 } end
  return ranges
end

---------------------------------------------------------------------------
-- Blocks
---------------------------------------------------------------------------

function M.render(src, width)
  local text = table.concat(src, "\n") .. "\n"
  local parser = vim.treesitter.get_string_parser(text, "markdown")
  local root = parser:parse()[1]:root()
  local R = { lines = {}, marks = {}, links = {}, headings = {}, src = {} }

  -- A context is a prefix chain: each level has a first-line prefix and a
  -- rest prefix (lists of {text, hl}); taking a prefix uses `first` once.
  local function ctx(parent, first, rest)
    return { parent = parent, first = first, rest = rest or first, used = false }
  end
  local function take(c)
    if not c then return {} end
    local p = vim.list_extend({}, take(c.parent))
    vim.list_extend(p, c.used and c.rest or c.first)
    c.used = true
    return p
  end
  local function prefix_width(c)
    local w = 0
    while c do
      for _, seg in ipairs(c.rest) do w = w + strw(seg[1]) end
      c = c.parent
    end
    return w
  end

  -- Append one line: prefix + body. `marks` are byte ranges into body.
  local function emit(c, body, marks, src_row, links)
    local row = #R.lines
    local parts, col = {}, 0
    for _, seg in ipairs(take(c)) do
      parts[#parts + 1] = seg[1]
      if seg[2] then R.marks[#R.marks + 1] = { row, col, col + #seg[1], seg[2] } end
      col = col + #seg[1]
    end
    local line = table.concat(parts) .. body
    if body == "" then
      line = line:gsub("%s+$", "")
      for i = #R.marks, 1, -1 do
        local m = R.marks[i]
        if m[1] ~= row then break end
        m[3] = math.min(m[3], #line)
      end
    end
    R.lines[#R.lines + 1] = line
    R.src[#R.lines] = src_row
    for _, m in ipairs(marks or {}) do
      R.marks[#R.marks + 1] = { row, col + m[1], col + m[2], m[3] }
    end
    for _, l in ipairs(links or {}) do
      R.links[#R.links + 1] = { row, col + l[1], col + l[2], l[3] }
    end
    return row
  end

  -- Emit inline-rendered text, word-wrapped; `hl` styles the whole text.
  local function emit_text(c, s, src_row, hl)
    local body, marks, links = inline(s)
    if hl then table.insert(marks, 1, { 0, #body, hl }) end
    local avail = math.max(20, width - prefix_width(c))
    local first
    for _, r in ipairs(wrap(body, avail)) do
      local from, to = r[1] - 1, r[2] -- 0-based [from, to)
      local function clip(list)
        local res = {}
        for _, m in ipairs(list) do
          local s0, e0 = math.max(m[1], from), math.min(m[2], to)
          if e0 > s0 then res[#res + 1] = { s0 - from, e0 - from, m[3] } end
        end
        return res
      end
      local row = emit(c, body:sub(from + 1, to), clip(marks), src_row, clip(links))
      first = first or row
    end
    return first
  end

  -- Source text helpers.
  local function line(row) return src[row + 1] or "" end
  local function strip_quote(s, depth)
    for _ = 1, depth do
      local ns = s:gsub("^%s*>%s?", "", 1)
      if ns == s then break end
      s = ns
    end
    return s
  end
  local function is_blank(row, depth) return strip_quote(line(row), depth):match("^%s*>?%s*$") ~= nil end
  local function last_row(node)
    local sr, _, er, ec = node:range()
    -- Nodes often end inside the next line's indentation (block continuation).
    if er > sr and line(er):sub(1, ec):match("^[%s>]*$") then er = er - 1 end
    return er
  end
  local function last_content_row(node, depth)
    local sr, er = node:start(), last_row(node)
    while er > sr and is_blank(er, depth) do er = er - 1 end
    return er
  end

  -- Text of an inline node, its lines joined with spaces.
  local function inline_text(node, depth)
    local sr, sc, er, ec = node:range()
    local parts = {}
    for row = sr, er do
      local l = line(row)
      if row == er then l = l:sub(1, ec) end
      if row == sr then
        l = l:sub(sc + 1)
      else
        l = strip_quote(l, depth):gsub("^%s+", "")
      end
      parts[#parts + 1] = l:gsub("%s+$", "")
    end
    return table.concat(parts, " ")
  end

  local block

  -- Children blocks of a container, with the source's blank lines between them.
  local skip = {
    block_continuation = true, block_quote_marker = true,
    task_list_marker_checked = true, task_list_marker_unchecked = true,
    list_marker_minus = true, list_marker_plus = true, list_marker_star = true,
    list_marker_dot = true, list_marker_parenthesis = true, link_reference_definition = true,
  }
  local function blocks(node, c, depth, lvl)
    local prev
    for child in node:iter_children() do
      if child:named() and not skip[child:type()]
        and not (child:type() == "section" and child:named_child_count() == 0) then
        if prev and child:start() > last_content_row(prev, depth) + 1 then
          emit(c, "", nil, (child:start()))
        end
        block(child, c, depth, lvl)
        prev = child
      end
    end
  end

  -- Lines of a code block, indentation (list nesting) and quote markers removed.
  local function code_lines(sr, er, depth, indent)
    local out = {}
    for row = sr, er do
      local l = strip_quote(line(row), depth)
      local lead = #l:match("^ *")
      out[#out + 1] = l:sub(math.min(lead, indent) + 1)
    end
    return out
  end

  local function emit_code(c, lines, lang, src_row)
    while #lines > 0 and lines[#lines] == "" do lines[#lines] = nil end
    local w = 0
    for _, l in ipairs(lines) do w = math.max(w, strw(l)) end
    if lang and lang ~= "" then w = math.max(w, strw(lines[1] or "") + #lang + 2) end
    w = math.min(w, math.max(20, width - prefix_width(c) - 2))
    local rows = {}
    for i, l in ipairs(lines) do
      local body = " " .. l .. string.rep(" ", math.max(0, w - strw(l)) + 1)
      local row = emit(c, body, { { 0, #body, "MdViewCodeBlock" } }, src_row + i)
      rows[i] = { row = row, col = #R.lines[row + 1] - #body + 1 }
    end
    -- Language name, dim, at the right end of the first line.
    if lang and lang ~= "" and rows[1] then
      local r = rows[1]
      local l = R.lines[r.row + 1]
      local tail = l:sub(-(#lang + 1))
      if tail:match("^%s+$") then
        R.lines[r.row + 1] = l:sub(1, #l - #lang - 1) .. lang .. " "
        R.marks[#R.marks + 1] = { r.row, #l - #lang - 1, #l - 1, "MdViewCodeLang" }
      end
    end
    -- Syntax highlighting with the language's treesitter highlights.
    if not lang or lang == "" then return end
    local tslang = vim.treesitter.language.get_lang(lang) or lang
    pcall(function()
      local code = table.concat(lines, "\n")
      local p = vim.treesitter.get_string_parser(code, tslang)
      local tree = p:parse()[1]
      local query = vim.treesitter.query.get(tslang, "highlights")
      if not query then return end
      for id, node in query:iter_captures(tree:root(), code, 0, -1) do
        local name = query.captures[id]
        if name ~= "spell" and name ~= "nospell" and not name:match("^_") then
          local sr, sc, er, ec = node:range()
          for row = sr, er do
            local r = rows[row + 1]
            if r then
              local s = row == sr and sc or 0
              local e = row == er and ec or #lines[row + 1]
              if e > s then
                R.marks[#R.marks + 1] = { r.row, r.col + s, r.col + e, "@" .. name .. "." .. tslang }
              end
            end
          end
        end
      end
    end)
  end

  local function emit_table(node, c, depth)
    local rows, align = {}, {}
    for child in node:iter_children() do
      local t = child:type()
      if t == "pipe_table_header" or t == "pipe_table_row" then
        local cells = {}
        for cell in child:iter_children() do
          if cell:type() == "pipe_table_cell" then
            local body, marks = inline((vim.treesitter.get_node_text(cell, text):gsub("^%s+", ""):gsub("%s+$", "")))
            cells[#cells + 1] = { body = body, marks = marks }
          end
        end
        rows[#rows + 1] = { cells = cells, header = t == "pipe_table_header", src = child:start() }
      elseif t == "pipe_table_delimiter_row" then
        for cell in child:iter_children() do
          if cell:type() == "pipe_table_delimiter_cell" then
            local s = vim.treesitter.get_node_text(cell, text)
            local l, r = s:match("^%s*:") ~= nil, s:match(":%s*$") ~= nil
            align[#align + 1] = (l and r) and "center" or r and "right" or "left"
          end
        end
      end
    end
    local ncol, widths = 0, {}
    for _, r in ipairs(rows) do ncol = math.max(ncol, #r.cells) end
    for i = 1, ncol do
      widths[i] = 1
      for _, r in ipairs(rows) do
        if r.cells[i] then widths[i] = math.max(widths[i], strw(r.cells[i].body)) end
      end
    end
    local function rule(l, m, r)
      local parts = {}
      for i = 1, ncol do parts[i] = string.rep("─", widths[i] + 2) end
      local s = l .. table.concat(parts, m) .. r
      emit(c, s, { { 0, #s, "MdViewBorder" } }, (node:start()))
    end
    rule("┌", "┬", "┐")
    for _, r in ipairs(rows) do
      local parts, marks, len = {}, {}, 0
      local function put(s, hl)
        if hl then marks[#marks + 1] = { len, len + #s, hl } end
        parts[#parts + 1] = s
        len = len + #s
      end
      put("│", "MdViewBorder")
      for i = 1, ncol do
        local cell = r.cells[i] or { body = "", marks = {} }
        local pad = widths[i] - strw(cell.body)
        local lp = align[i] == "right" and pad or align[i] == "center" and math.floor(pad / 2) or 0
        put(" " .. string.rep(" ", lp))
        local start = len
        put(cell.body, r.header and "MdViewStrong" or nil)
        for _, m in ipairs(cell.marks) do marks[#marks + 1] = { start + m[1], start + m[2], m[3] } end
        put(string.rep(" ", pad - lp) .. " ")
        put("│", "MdViewBorder")
      end
      emit(c, table.concat(parts), marks, r.src)
      if r.header then rule("├", "┼", "┤") end
    end
    rule("└", "┴", "┘")
  end

  block = function(node, c, depth, lvl)
    local t = node:type()
    local sr = node:start()
    if t == "section" or t == "document" then
      blocks(node, c, depth, lvl)
    elseif t == "atx_heading" or t == "setext_heading" then
      local level = 1
      local content
      for child in node:iter_children() do
        local ct = child:type()
        local n = ct:match("^atx_h(%d)_marker$")
        if n then level = tonumber(n) end
        if ct == "setext_h2_underline" then level = 2 end
        if ct == "inline" then content = child end
        if ct == "paragraph" then
          for g in child:iter_children() do
            if g:type() == "inline" then content = g end
          end
        end
      end
      local s = content and inline_text(content, depth):gsub("%s+#+$", "") or ""
      local style = HEADING[level]
      if style.upper then s = s:upper() end
      local hl = "MdViewH" .. level
      local row = emit_text(c, style.prefix .. s, sr, hl)
      R.headings[#R.headings + 1] = row + 1
    elseif t == "paragraph" then
      local content
      for child in node:iter_children() do
        if child:type() == "inline" then content = child end
      end
      emit_text(c, inline_text(content or node, depth), sr)
    elseif t == "fenced_code_block" then
      local lang, first, last
      for child in node:iter_children() do
        local ct = child:type()
        if ct == "info_string" then
          lang = vim.treesitter.get_node_text(child, text):match("^%s*([%w_+#.-]+)")
        elseif ct == "code_fence_content" then
          first, last = child:start(), last_row(child)
        end
      end
      local indent = #strip_quote(line(sr), depth):match("^ *")
      local lines = first and code_lines(first, last, depth, indent) or {}
      emit_code(c, lines, lang, sr)
    elseif t == "indented_code_block" then
      local indent = #strip_quote(line(sr), depth):match("^ *")
      emit_code(c, code_lines(sr, last_content_row(node, depth), depth, indent), nil, sr - 1)
    elseif t == "block_quote" then
      local q = { { "│ ", "MdViewQuote" } }
      blocks(node, ctx(c, q), depth + 1, lvl)
    elseif t == "list" then
      -- Ordered markers are right-aligned to the widest number.
      local items, numw, ordered = {}, 0, false
      for item in node:iter_children() do
        if item:type() == "list_item" then
          local marker, task
          for child in item:iter_children() do
            local ct = child:type()
            if ct:match("^list_marker") then
              marker = vim.treesitter.get_node_text(child, text):gsub("%s+", "")
            elseif ct == "task_list_marker_checked" then
              task = "checked"
            elseif ct == "task_list_marker_unchecked" then
              task = "unchecked"
            end
          end
          items[#items + 1] = { node = item, marker = marker or "-", task = task }
          if marker and marker:match("^%d") then numw, ordered = math.max(numw, #marker), true end
        end
      end
      local prev
      for _, it in ipairs(items) do
        if prev and it.node:start() > last_content_row(prev, depth) + 1 then
          emit(c, "", nil, (it.node:start()))
        end
        local first
        if it.task == "checked" then
          first = { { "☑ ", "MdViewChecked" } }
        elseif it.task == "unchecked" then
          first = { { "☐ ", "MdViewUnchecked" } }
        elseif it.marker:match("^%d") then
          first = { { string.rep(" ", numw - #it.marker) .. it.marker .. " ", "MdViewMarker" } }
        else
          first = { { BULLETS[lvl % #BULLETS + 1], "MdViewMarker" } }
        end
        local rest = { { string.rep(" ", strw(first[1][1])) } }
        local ic = ctx(c, first, rest)
        blocks(it.node, ic, depth, ordered and lvl or lvl + 1)
        if not ic.used then emit(ic, "", nil, (it.node:start())) end -- empty item
        prev = it.node
      end
    elseif t == "pipe_table" then
      emit_table(node, c, depth)
    elseif t == "thematic_break" then
      local s = string.rep("─", math.max(3, math.min(width, 80) - prefix_width(c)))
      emit(c, s, { { 0, #s, "MdViewBorder" } }, sr)
    elseif t == "minus_metadata" or t == "plus_metadata" then
      -- Front matter: `key: value` lines, values wrapped under themselves.
      for row = sr + 1, last_row(node) - 1 do
        local key, val = line(row):match("^([%w_.-]+%s*[:=]%s*)(.*)$")
        if key then
          local kc = ctx(c, { { key, "MdViewMetaKey" } }, { { string.rep(" ", strw(key)) } })
          local body = val:gsub("^[\"']", ""):gsub("[\"']$", "")
          local avail = math.max(20, width - prefix_width(kc))
          for _, r in ipairs(wrap(body, avail)) do
            local s = body:sub(r[1], r[2])
            emit(kc, s, { { 0, #s, "MdViewDim" } }, row)
          end
        else
          local s = line(row)
          emit(c, s, { { 0, #s, "MdViewDim" } }, row)
        end
      end
    elseif t == "link_reference_definition" then
      return
    else -- html_block and anything unknown: the source, dimmed
      for row = sr, last_content_row(node, depth) do
        local s = strip_quote(line(row), depth)
        emit(c, s, { { 0, #s, "MdViewDim" } }, row)
      end
    end
  end

  block(root, nil, 0, 0)
  while #R.lines > 0 and R.lines[#R.lines] == "" do
    R.lines[#R.lines] = nil
  end
  return R
end

return M
