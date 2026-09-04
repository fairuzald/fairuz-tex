#!/usr/bin/env python3
"""Convert the report's TikZ diagram sources to Mermaid flowcharts.

The source diagrams use a deliberately small visual vocabulary (named nodes,
directed links, and style classes).  This converter keeps the node text and
the directed relationships while mapping the visual classes to Mermaid
classes.  It is used once for the migration and remains in the repository so
new legacy TikZ diagrams can be converted reproducibly.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


STYLE_TO_CLASS = (
    (("owned", "core", "strategy", "branch"), "owned"),
    (("local",), "local"),
    (("external", "reject", "fail", "stop"), "danger"),
    (("store", "entity", "privacy", "refbox", "artifact", "data"), "store"),
    (("actor", "source"), "neutral"),
)


def command_chunks(text: str, command: str):
    """Yield complete LaTeX commands ending at a top-level semicolon."""
    start = 0
    while True:
        match = re.search(rf"\\{command}\b", text[start:])
        if not match:
            return
        begin = start + match.start()
        depth = 0
        end = begin
        while end < len(text):
            char = text[end]
            if char == "{":
                depth += 1
            elif char == "}":
                depth = max(0, depth - 1)
            elif char == ";" and depth == 0:
                yield text[begin : end + 1]
                start = end + 1
                break
            end += 1
        else:
            return


def last_braced_value(command: str) -> str:
    """Return the final balanced brace group, which is a node body."""
    close = command.rfind("}")
    if close < 0:
        return ""
    depth = 0
    for index in range(close, -1, -1):
        if command[index] == "}":
            depth += 1
        elif command[index] == "{":
            depth -= 1
            if depth == 0:
                return command[index + 1 : close]
    return ""


def strip_latex(value: str) -> str:
    value = value.replace("\\\\", "<br/>").replace("\n", " ")
    value = re.sub(r"\\rule\s*\{[^{}]*\}\s*\{[^{}]*\}", "<hr/>", value)
    # Keep the argument of common formatting commands.
    previous = None
    while previous != value:
        previous = value
        value = re.sub(r"\\(?:textbf|texttt|emph|code|textit|textrm|text|underline)\s*\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\(?:small|scriptsize|footnotesize|strut|vphantom|phantom)\b", "", value)
    value = re.sub(r"\\[a-zA-Z]+", "", value)
    value = value.replace("{", "").replace("}", "")
    value = value.replace(r"\_", "_").replace(r"\&", "&").replace(r"\%", "%")
    value = re.sub(r"\[-?\d+(?:\.\d+)?mm\]", "", value)
    value = value.replace("$", "")
    value = re.sub(r"\s+", " ", value).strip()
    return value.replace('"', "'") or "(tanpa label)"


def style_class(options: str) -> str:
    for needles, class_name in STYLE_TO_CLASS:
        if any(needle in options for needle in needles):
            return class_name
    return "default"


def parse_nodes(text: str):
    nodes = {}
    options_by_id = {}
    for command in command_chunks(text, "node"):
        # Only accept an explicit node identifier immediately after the style
        # options.  This excludes background `fit=(...)` nodes, whose
        # parentheses are layout references rather than node declarations.
        identifier_match = re.match(
            r"\\node(?:\[[^\]]*\])?\s*\(([A-Za-z][A-Za-z0-9_:-]*)\)",
            command,
        )
        if not identifier_match:
            continue
        identifier = identifier_match.group(1).strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_:-]*", identifier):
            continue
        options_match = re.match(r"\\node(?:\[([^\]]*)\])?", command)
        options = options_match.group(1) if options_match else ""
        label = strip_latex(last_braced_value(command))
        # TikZ panel nodes often carry their visible title in a label option.
        if label == "(tanpa label)":
            label_match = re.search(r"label=\{[^:}]*:([^}]*)\}", command, re.S)
            if label_match:
                label = strip_latex(label_match.group(1))
            else:
                label = identifier.replace("_", " ")
        nodes[identifier] = label
        options_by_id[identifier] = options
    return nodes, options_by_id


def parse_edges(text: str, node_ids: set[str]):
    edges = []
    seen = set()
    for command in command_chunks(text, "draw"):
        identifiers = []
        for match in re.finditer(r"\(([A-Za-z][A-Za-z0-9_:-]*)(?:\.[^()]*)?\)", command):
            identifier = match.group(1)
            if identifier in node_ids and (not identifiers or identifiers[-1] != identifier):
                identifiers.append(identifier)
        if len(identifiers) < 2:
            continue
        label_match = re.search(r"node(?:\[[^\]]*\])?\s*\{([^{}]*)\}", command, re.S)
        label = strip_latex(label_match.group(1)) if label_match else ""
        dashed = bool(re.search(r"(?:dashed|logical|data|read|control|async|rw|fail|stop)", command))
        arrow = "-.->" if dashed else "-->"
        for source, target in zip(identifiers, identifiers[1:]):
            key = (source, target, label, arrow)
            if source == target or key in seen:
                continue
            seen.add(key)
            edges.append((source, target, label, arrow))
    return edges


def convert(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    nodes, options_by_id = parse_nodes(text)
    edges = parse_edges(text, set(nodes))
    lines = ["%% Generated from " + path.name, "flowchart LR"]
    def safe_id(identifier: str) -> str:
        return "n_" + identifier.replace("-", "_")

    for identifier, label in nodes.items():
        lines.append(f'    {safe_id(identifier)}["{label}"]:::class_{style_class(options_by_id[identifier])}')
    for source, target, label, arrow in edges:
        source = safe_id(source)
        target = safe_id(target)
        if label:
            lines.append(f'    {source} {arrow}|{label}| {target}')
        else:
            lines.append(f"    {source} {arrow} {target}")
    lines.extend(
        [
            "    classDef default fill:#ffffff,stroke:#4b5563,stroke-width:1px,color:#111827;",
            "    classDef class_owned fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px,color:#111827;",
            "    classDef class_local fill:#dcfce7,stroke:#15803d,stroke-width:1px,color:#111827;",
            "    classDef class_danger fill:#fee2e2,stroke:#b91c1c,stroke-width:1px,color:#111827;",
            "    classDef class_store fill:#f3f4f6,stroke:#6b7280,stroke-width:1px,color:#111827;",
            "    classDef class_neutral fill:#f9fafb,stroke:#6b7280,stroke-width:1px,color:#111827;",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    tex_files = sorted(path for path in args.directory.glob("*.tex") if not path.name.startswith("._"))
    if not tex_files:
        raise SystemExit("No TikZ sources found")
    for tex_file in tex_files:
        output = tex_file.with_suffix(".mmd")
        output.write_text(convert(tex_file), encoding="utf-8")
        print(f"converted {tex_file.name} -> {output.name}")


if __name__ == "__main__":
    main()
