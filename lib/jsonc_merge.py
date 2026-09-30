#!/usr/bin/env python3
"""Merge a tracked JSONC file with a machine-local one (used for VS Code on the work Mac).

Usage: jsonc_merge.py <base.json> <local.json> <header-comment>
Prints the merged JSON to stdout.
  objects: deep merge, local wins
  arrays:  local entries appended (keybindings.json)
Comments and trailing commas (JSONC) are accepted in both inputs.
"""
import json
import sys


def strip_jsonc(text):
    out, i, n = [], 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
        elif c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
        else:
            out.append(c)
            i += 1
    # Drop trailing commas before } or ] (outside strings: strings were copied verbatim,
    # so re-scan with the same string awareness).
    s, res, in_str, i = "".join(out), [], False, 0
    while i < len(s):
        c = s[i]
        if in_str:
            res.append(c)
            if c == "\\" and i + 1 < len(s):
                res.append(s[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            res.append(c)
        elif c == ",":
            j = i + 1
            while j < len(s) and s[j] in " \t\r\n":
                j += 1
            if j < len(s) and s[j] in "}]":
                i += 1
                continue
            res.append(c)
        else:
            res.append(c)
        i += 1
    return "".join(res)


def load(path):
    with open(path, encoding="utf-8") as f:
        text = strip_jsonc(f.read()).strip()
    return json.loads(text) if text else None


def merge(base, extra):
    if isinstance(base, dict) and isinstance(extra, dict):
        out = dict(base)
        for k, v in extra.items():
            out[k] = merge(out[k], v) if k in out else v
        return out
    if isinstance(base, list) and isinstance(extra, list):
        return base + extra
    return extra


def main():
    base_path, local_path, header = sys.argv[1], sys.argv[2], sys.argv[3]
    merged = merge(load(base_path), load(local_path))
    sys.stdout.write("".join(f"// {line}\n" for line in header.splitlines()))
    sys.stdout.write(json.dumps(merged, indent=4, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
