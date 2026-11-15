#!/usr/bin/env python3
"""Generates the Kotlin/JS declarations for ``ag-grid-community`` from its TypeScript definitions.

The upstream package ships ``dist/types/src`` next to its JavaScript: one ``.d.ts`` per source file,
with ``main.d.ts`` naming what the package actually exports. That pair *is* the scope of the
wrapper — see ``docs/development/technical-decisions.md`` for why the declarations are generated
rather than hand-written.

Usage::

    python3 scripts/generate-api.py --types <ag-grid-community>/dist/types/src --out <module>/src/jsMain/kotlin
    python3 scripts/generate-api.py --types ... --stats
    python3 scripts/generate-api.py --types ... --coverage docs/development/coverage.md

``--stats`` prints the size of the public surface without writing anything; ``--coverage`` rewrites
the coverage document the task list links to.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable, Iterator

# ------------------------------------------------------------------------------------------------
# Scanning helpers: comments, strings and balanced regions
# ------------------------------------------------------------------------------------------------

_LINE_COMMENT = "//"
_BLOCK_OPEN = "/*"
_BLOCK_CLOSE = "*/"


def _skip_string(src: str, i: int) -> int:
    """Returns the index just past the string literal starting at ``src[i]``."""
    quote = src[i]
    i += 1
    n = len(src)
    while i < n:
        c = src[i]
        if c == "\\":
            i += 2
            continue
        if c == quote:
            return i + 1
        if quote == "`" and c == "$" and i + 1 < n and src[i + 1] == "{":
            # Template substitution: skip the balanced braces, then keep going.
            i = _skip_balanced(src, i + 1, "{", "}")
            continue
        i += 1
    raise ValueError("unterminated string literal")


def _skip_comment(src: str, i: int) -> tuple[int, str]:
    """Returns (index past the comment, comment text)."""
    if src.startswith(_BLOCK_OPEN, i):
        end = src.find(_BLOCK_CLOSE, i + 2)
        if end < 0:
            raise ValueError("unterminated block comment")
        return end + 2, src[i + 2 : end]
    end = src.find("\n", i)
    return (len(src) if end < 0 else end), src[i + 2 : end]


def _skip_balanced(src: str, i: int, open_ch: str, close_ch: str) -> int:
    """``src[i]`` is ``open_ch``; returns the index just past the matching ``close_ch``."""
    depth = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c in "'\"`":
            i = _skip_string(src, i)
            continue
        if src.startswith(_BLOCK_OPEN, i):
            i, _ = _skip_comment(src, i)
            continue
        if src.startswith(_LINE_COMMENT, i):
            i, _ = _skip_comment(src, i)
            continue
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError(f"unbalanced {open_ch}{close_ch}")


def split_top_level(src: str, separator: str) -> list[str]:
    """Splits ``src`` on ``separator`` occurrences that sit outside any bracket or string.

    Angle brackets count as brackets: a `,` inside `Map<Column, string>` separates type
    arguments, not parameters, and splitting there used to produce fragments like `any>`.
    """
    parts: list[str] = []
    depth = 0
    angle = 0
    start = 0
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c in "'\"`":
            i = _skip_string(src, i)
            continue
        if src.startswith(_BLOCK_OPEN, i):
            i, _ = _skip_comment(src, i)
            continue
        if src.startswith(_LINE_COMMENT, i):
            i, _ = _skip_comment(src, i)
            continue
        if c == "<":
            angle += 1
        elif c == ">":
            if angle > 0 and src[i - 1] != "=":
                angle -= 1
        elif c in "{([":
            depth += 1
        elif c in "})]":
            depth -= 1
        elif depth == 0 and angle == 0 and src.startswith(separator, i):
            parts.append(src[start:i])
            i += len(separator)
            start = i
            continue
        i += 1
    if start < n:
        parts.append(src[start:])
    return parts


def find_top_level(src: str, chars: str) -> int:
    """Index of the first character in ``chars`` at bracket depth 0, or -1."""
    depth = 0
    angle = 0
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c in "'\"`":
            i = _skip_string(src, i)
            continue
        if c == "<":
            angle += 1
        elif c == ">":
            if angle > 0 and src[i - 1] != "=":
                angle -= 1
        elif c in "{([":
            depth += 1
        elif c in "})]":
            depth -= 1
        elif depth == 0 and angle == 0 and c in chars:
            return i
        i += 1
    return -1


def split_angle(src: str, i: int) -> int:
    """``src[i]`` is ``<``; returns the index just past the matching ``>``."""
    depth = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c in "'\"`":
            i = _skip_string(src, i)
            continue
        if c == "<":
            depth += 1
        elif c == ">":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced <>")


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# ------------------------------------------------------------------------------------------------
# Declaration model
# ------------------------------------------------------------------------------------------------


@dataclass
class Member:
    """One member of an interface body, class body or object type."""

    kind: str  # "property" | "method" | "construct" | "index" | "call"
    name: str = ""
    optional: bool = False
    readonly: bool = False
    private: bool = False
    static: bool = False
    type: "TypeExpr | None" = None
    params: list["Param"] = field(default_factory=list)
    type_params: list[str] = field(default_factory=list)
    doc: str = ""
    raw: str = ""


@dataclass
class Param:
    name: str
    type: "TypeExpr | None"
    optional: bool = False
    variadic: bool = False
    default: str | None = None


@dataclass
class Decl:
    kind: str  # interface | class | alias | enum | function | const | namespace
    name: str
    file: str
    exported: bool = False
    doc: str = ""
    raw: str = ""
    type_params: list[str] = field(default_factory=list)
    type_param_defaults: dict[str, str] = field(default_factory=dict)
    heritage: list[str] = field(default_factory=list)
    members: list[Member] = field(default_factory=list)
    alias: "TypeExpr | None" = None
    params: list[Param] = field(default_factory=list)
    returns: "TypeExpr | None" = None
    enum_members: list[tuple[str, str]] = field(default_factory=list)
    const_type: "TypeExpr | None" = None


@dataclass
class TypeExpr:
    """A parsed TypeScript type expression."""

    kind: str
    # kind == "ref":  name in `name`, type arguments in `args`
    # kind == "union" / "intersection": operands in `items`
    # kind == "array": element in `items[0]`
    # kind == "literal": literal source text in `name` (e.g. `"a"`, `1`, `true`)
    # kind == "object": `members`
    # kind == "function": `params`, `returns`, `type_params`
    # kind == "tuple": `items`
    # kind == "keyof" / "readonly" / "typeof": operand in `items[0]`
    # kind == "indexed": object in `items[0]`, index in `items[1]`
    # kind == "import": module in `name`, member in `value`
    # kind == "raw": unparsed text in `name`
    name: str = ""
    args: list["TypeExpr"] = field(default_factory=list)
    items: list["TypeExpr"] = field(default_factory=list)
    members: list[Member] = field(default_factory=list)
    params: list[Param] = field(default_factory=list)
    returns: "TypeExpr | None" = None
    type_params: list[str] = field(default_factory=list)
    value: str = ""
    raw: str = ""


PRIMITIVES = {
    "string": "String",
    "number": "Double",
    "boolean": "Boolean",
    "void": "Unit",
    "never": "Unit",
    "null": "Nothing",
    "undefined": "Nothing",
    "any": "JsAny",
    "unknown": "JsAny",
    "object": "JsAny",
    "symbol": "JsAny",
    "bigint": "JsAny",
    "this": "JsAny",
}


# ------------------------------------------------------------------------------------------------
# Type expression parser
# ------------------------------------------------------------------------------------------------


class TypeParser:
    def __init__(self, text: str, type_params: Iterable[str] = ()):
        self.text = text.strip()
        self.type_params = set(type_params)

    def parse(self) -> TypeExpr:
        src = self.text
        if not src:
            return TypeExpr("raw", name="")
        try:
            expr, end = self._parse_conditional(src, 0)
            if src[end:].strip():
                return TypeExpr("raw", name=normalize_ws(src))
            return expr
        except (ValueError, IndexError):
            return TypeExpr("raw", name=normalize_ws(src))

    # -- conditional / infer ----------------------------------------------------------------
    def _parse_conditional(self, src: str, i: int) -> tuple[TypeExpr, int]:
        expr, i = self._parse_union(src, i)
        i = self._skip_ws(src, i)
        # `T extends U ? X : Y` and `T extends U ? X : Y` chained. Kotlin cannot express it; the
        # generator records the raw text and the emitter decides (`JsAny`).
        if _at_keyword(src, i, "extends"):
            _, i = self._parse_union(src, self._skip_ws(src, i + len("extends")))
            i = self._skip_ws(src, i)
            if i < len(src) and src[i] == "?":
                _, i = self._parse_union(src, i + 1)
                i = self._skip_ws(src, i)
                if i < len(src) and src[i] == ":":
                    _, i = self._parse_union(src, i + 1)
                return TypeExpr("raw", name=normalize_ws(src)), len(src)
        return expr, i

    def _skip_ws(self, src: str, i: int) -> int:
        while i < len(src) and src[i].isspace():
            i += 1
        return i

    # -- unions and intersections -----------------------------------------------------------
    def _parse_union(self, src: str, i: int) -> tuple[TypeExpr, int]:
        items: list[TypeExpr] = []
        i = self._skip_ws(src, i)
        if i < len(src) and src[i] == "|":
            i += 1
        first, i = self._parse_intersection(src, i)
        items.append(first)
        while True:
            j = self._skip_ws(src, i)
            if j < len(src) and src[j] == "|":
                nxt, i = self._parse_intersection(src, j + 1)
                items.append(nxt)
            else:
                break
        if len(items) == 1:
            return items[0], i
        return TypeExpr("union", items=items), i

    def _parse_intersection(self, src: str, i: int) -> tuple[TypeExpr, int]:
        items: list[TypeExpr] = []
        first, i = self._parse_postfix(src, i)
        items.append(first)
        while True:
            j = self._skip_ws(src, i)
            if j < len(src) and src[j] == "&":
                nxt, i = self._parse_postfix(src, j + 1)
                items.append(nxt)
            else:
                break
        if len(items) == 1:
            return items[0], i
        return TypeExpr("intersection", items=items), i

    # -- array / indexed access -------------------------------------------------------------
    def _parse_postfix(self, src: str, i: int) -> tuple[TypeExpr, int]:
        expr, i = self._parse_atom(src, i)
        while True:
            j = self._skip_ws(src, i)
            if j < len(src) and src[j] == "[":
                end = _skip_balanced(src, j, "[", "]")
                inner = src[j + 1 : end - 1].strip()
                if not inner:
                    expr = TypeExpr("array", items=[expr])
                else:
                    expr = TypeExpr(
                        "indexed",
                        items=[expr, TypeParser(inner, self.type_params).parse()],
                    )
                i = end
                continue
            break
        return expr, i

    # -- atoms ------------------------------------------------------------------------------
    def _parse_atom(self, src: str, i: int) -> tuple[TypeExpr, int]:
        i = self._skip_ws(src, i)
        if i >= len(src):
            raise ValueError("expected a type")
        c = src[i]

        if c == "(":
            # A parenthesised type, or the parameter list of a function type.
            end = _skip_balanced(src, i, "(", ")")
            inner = src[i + 1 : end - 1]
            j = self._skip_ws(src, end)
            if src.startswith("=>", j):
                return self._finish_function(src, inner, j + 2, "(")
            return TypeParser(inner, self.type_params).parse(), end

        if c == "<":
            # Generic function type: `<T>(x: T) => T`.
            close = split_angle(src, i)
            type_params = self._type_param_names(src[i + 1 : close - 1])
            j = self._skip_ws(src, close)
            if j < len(src) and src[j] == "(":
                end = _skip_balanced(src, j, "(", ")")
                inner = src[j + 1 : end - 1]
                k = self._skip_ws(src, end)
                if src.startswith("=>", k):
                    return self._finish_function(src, inner, k + 2, type_params)
            raise ValueError("unsupported generic form")

        if c == "{":
            end = _skip_balanced(src, i, "{", "}")
            body = src[i + 1 : end - 1]
            return TypeExpr("object", members=parse_members(body, self.type_params)), end

        if c == "[":
            end = _skip_balanced(src, i, "[", "]")
            inner = src[i + 1 : end - 1]
            if not inner.strip():
                return TypeExpr("tuple", items=[]), end
            items: list[TypeExpr] = []
            for part in split_top_level(inner, ","):
                part = part.strip()
                if not part:
                    continue
                if part.startswith("..."):
                    part = part[3:]
                # Named tuple members: `name: type` or `name?: type`.
                named = re.match(r"^([A-Za-z_$][\w$]*)\??\s*:\s*(.+)$", part, re.S)
                if named:
                    part = named.group(2)
                items.append(TypeParser(part, self.type_params).parse())
            return TypeExpr("tuple", items=items), end

        if c in "'\"":
            end = _skip_string(src, i)
            return TypeExpr("literal", value=src[i:end]), end

        if c == "`":
            end = _skip_string(src, i)
            return TypeExpr("raw", name=normalize_ws(src[i:end])), end

        if c == "-" or c.isdigit():
            m = re.match(r"-?\d+(?:\.\d+)?", src[i:])
            if not m:
                raise ValueError("bad numeric literal")
            return TypeExpr("literal", value=m.group(0)), i + len(m.group(0))

        word = None
        for w in (
            "readonly",
            "keyof",
            "typeof",
            "new",
            "infer",
            "globalThis",
            "unique",
            "asserts",
        ):
            if _at_keyword(src, i, w):
                word = w
                break

        if word == "readonly":
            j = self._skip_ws(src, i + len(word))
            inner, i = self._parse_postfix(src, j)
            if inner.kind == "array":
                return TypeExpr("readonly", items=[inner.items[0]]), i
            return inner, i

        if word in ("keyof", "typeof"):
            j = self._skip_ws(src, i + len(word))
            inner, i = self._parse_postfix(src, j)
            return TypeExpr(word, items=[inner]), i

        if word == "unique":
            j = self._skip_ws(src, i + len("unique"))
            _, i = self._parse_postfix(src, j)
            return TypeExpr("raw", name="unique symbol"), i

        if word == "infer":
            j = self._skip_ws(src, i + len("infer"))
            name, i = self._read_ident(src, j)
            return TypeExpr("raw", name=f"infer {name}"), i

        if word == "new":
            j = self._skip_ws(src, i + len("new"))
            close = split_angle(src, j) if j < len(src) and src[j] == "<" else j
            j = self._skip_ws(src, close)
            if j < len(src) and src[j] == "(":
                end = _skip_balanced(src, j, "(", ")")
                inner = src[j + 1 : end - 1]
                k = self._skip_ws(src, end)
                if src.startswith("=>", k):
                    expr, i = self._finish_function(src, inner, k + 2, ())
                    return TypeExpr("raw", name="new " + normalize_ws(expr.raw or "() => any")), i
            raise ValueError("unsupported constructor type")

        if word == "asserts":
            j = self._skip_ws(src, i + len("asserts"))
            name, i = self._read_ident(src, j)
            return TypeExpr("raw", name=f"asserts {name}"), i

        m = re.match(r"[A-Za-z_$][\w$]*", src[i:])
        if not m:
            raise ValueError(f"unexpected type syntax at {src[i:i + 24]!r}")
        name = m.group(0)
        i += len(name)

        if name == "import":
            j = self._skip_ws(src, i)
            if j < len(src) and src[j] == "(":
                end = _skip_balanced(src, j, "(", ")")
                module = src[j + 1 : end - 1].strip().strip("'\"")
                k = self._skip_ws(src, end)
                member = ""
                if k < len(src) and src[k] == ".":
                    k = self._skip_ws(src, k + 1)
                    member, k = self._read_ident(src, k)
                return TypeExpr("import", name=module, value=member), k
            raise ValueError("unsupported import type")

        if name in ("true", "false"):
            return TypeExpr("literal", value=name), i

        j = self._skip_ws(src, i)
        args: list[TypeExpr] = []
        if j < len(src) and src[j] == "<":
            close = split_angle(src, j)
            inner = src[j + 1 : close - 1]
            for part in split_top_level(inner, ","):
                part = part.strip()
                if part:
                    args.append(TypeParser(part, self.type_params).parse())
            i = close
            j = self._skip_ws(src, i)

        # `is` predicates (`value is string`) become their right-hand type.
        if _at_keyword(src, j, "is"):
            k = self._skip_ws(src, j + 2)
            return self._parse_atom(src, k)

        # Upstream's `Either<A, B>` (`tools/helper`) is just a union spelled as a generic.
        if name == "Either" and len(args) == 2:
            return TypeExpr("union", items=args), i

        return TypeExpr("ref", name=name, args=args), i

    def _read_ident(self, src: str, i: int) -> tuple[str, int]:
        i = self._skip_ws(src, i)
        m = re.match(r"[A-Za-z_$][\w$]*", src[i:])
        if not m:
            raise ValueError("expected an identifier")
        return m.group(0), i + len(m.group(0))

    def _type_param_names(self, inner: str) -> list[str]:
        names: list[str] = []
        for part in split_top_level(inner, ","):
            part = part.strip()
            if not part:
                continue
            m = re.match(r"([A-Za-z_$][\w$]*)", part)
            if m:
                names.append(m.group(1))
        return names

    def _finish_function(
        self,
        src: str,
        params_text: str,
        ret_start: int,
        type_params: Iterable[str] | str,
    ) -> tuple[TypeExpr, int]:
        params = parse_params(params_text, self.type_params)
        ret, i = self._parse_union(src, ret_start)
        if isinstance(type_params, str):
            type_params = ()
        return (
            TypeExpr("function", params=params, returns=ret, type_params=list(type_params)),
            i,
        )


def _at_keyword(src: str, i: int, word: str) -> bool:
    if not src.startswith(word, i):
        return False
    end = i + len(word)
    if end < len(src) and (src[end].isalnum() or src[end] in "_$"):
        return False
    if i > 0 and (src[i - 1].isalnum() or src[i - 1] in "_$"):
        return False
    return True


def parse_type(text: str, type_params: Iterable[str] = ()) -> TypeExpr:
    return TypeParser(text, type_params).parse()


def parse_params(text: str, type_params: Iterable[str] = ()) -> list[Param]:
    params: list[Param] = []
    for part in split_top_level(text, ","):
        part = part.strip()
        if not part:
            continue
        variadic = part.startswith("...")
        if variadic:
            part = part[3:].strip()
        # A trailing `= default` may itself contain commas; split_top_level already handled the
        # commas that matter, so any remaining `=` splits name/type from the default.
        default = None
        eq = find_top_level(part, "=")
        if eq >= 0:
            default = part[eq + 1 :].strip()
            part = part[:eq].strip()
        m = re.match(r"(?:readonly\s+)?([A-Za-z_$][\w$]*|this)\s*(\?)?\s*:?\s*(.*)$", part, re.S)
        if m:
            name, optional, type_text = m.group(1), bool(m.group(2)), m.group(3)
        else:
            name, optional, type_text = "", False, part
        params.append(
            Param(
                name=name,
                type=parse_type(type_text, type_params) if type_text.strip() else None,
                optional=optional or default is not None,
                variadic=variadic,
                default=default,
            )
        )
    return params


def parse_members(body: str, type_params: Iterable[str] = ()) -> list[Member]:
    """Parses the body of an interface, class or object type into members."""
    members: list[Member] = []
    pending_doc: list[str] = []
    for chunk in split_top_level(body, ";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        doc, chunk = _take_doc(chunk)
        if doc:
            pending_doc.append(doc)
        if not chunk:
            continue
        member = parse_member(chunk, type_params)
        if member is not None:
            if pending_doc and not member.doc:
                member.doc = pending_doc[-1]
            members.append(member)
            pending_doc.clear()
    # `get x()` + `set x(v)` is one Kotlin `var`: drop the setter half once the getter owns the
    # property, and turn a lone setter into a writable property.
    merged: list[Member] = []
    properties: dict[str, Member] = {}
    for member in members:
        if member.kind == "setter":
            existing = properties.get(member.name)
            if existing is not None:
                existing.readonly = False
                if existing.type is None:
                    existing.type = member.type
                continue
            member.kind = "property"
            member.readonly = False
        if member.kind == "property":
            properties.setdefault(member.name, member)
        merged.append(member)
    # Keep any trailing doc for the next declaration: harmless here.
    return merged


def _take_doc(chunk: str) -> tuple[str, str]:
    """Strips leading `/** ... */` blocks, returning their text and the rest."""
    docs: list[str] = []
    while True:
        chunk = chunk.lstrip()
        if not chunk.startswith("/**"):
            break
        end = chunk.find("*/")
        if end < 0:
            break
        docs.append(_clean_doc(chunk[3:end]))
        chunk = chunk[end + 2 :]
    return "\n".join(d for d in docs if d), chunk


def _clean_doc(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("*"):
            line = line[1:]
        lines.append(line.strip())
    out = " ".join(l for l in lines if l)
    return out.strip()


def parse_member(chunk: str, type_params: Iterable[str]) -> Member | None:
    raw = normalize_ws(chunk)
    text = chunk.strip()
    readonly = False
    private = False
    static = False
    # Modifiers may appear in any order before the member itself.
    while True:
        stripped = text
        for word in ("private", "protected", "public", "static", "abstract", "declare", "override", "readonly", "accessor"):
            if _at_keyword(stripped, 0, word) and stripped[len(word) : len(word) + 1].isspace():
                if word == "readonly":
                    readonly = True
                elif word in ("private", "protected"):
                    private = True
                elif word == "static":
                    static = True
                stripped = stripped[len(word) :].lstrip()
                break
        if stripped == text:
            break
        text = stripped
    if not text:
        return None

    member = _parse_member_body(text, raw, readonly, type_params)
    if member is None:
        return None
    member.private = private or member.private
    member.static = static or member.static
    member.readonly = readonly or member.readonly
    return member


def _parse_member_body(
    text: str, raw: str, readonly: bool, type_params: Iterable[str]
) -> Member | None:
    if text.startswith("new "):
        text = text[3:].strip()
        if text.startswith("("):
            end = _skip_balanced(text, 0, "(", ")")
            inner = text[1 : end - 1]
            ret = text[end:].strip()
            if ret.startswith(":"):
                ret = ret[1:]
            return Member(
                kind="construct",
                params=parse_params(inner, type_params),
                type=parse_type(ret, type_params) if ret else None,
                raw=raw,
            )
        return Member(kind="construct", raw=raw)

    # Call signatures: `(a: A): R` and `<T>(a: A): R`, in interfaces.
    if text.startswith("(") or text.startswith("<"):
        if text.startswith("<"):
            close = split_angle(text, 0)
            own = TypeParser(text[:close], type_params)._type_param_names(text[1 : close - 1])
            text = text[close:].strip()
        else:
            own = []
        if text.startswith("("):
            end = _skip_balanced(text, 0, "(", ")")
            inner = text[1 : end - 1]
            ret = text[end:].strip()
            if ret.startswith(":"):
                ret = ret[1:]
            return Member(
                kind="call",
                params=parse_params(inner, type_params),
                type=parse_type(ret, type_params) if ret else None,
                type_params=list(own),
                raw=raw,
            )
        return None

    # Index signature: `[key: string]: T`.
    if text.startswith("["):
        end = _skip_balanced(text, 0, "[", "]")
        inner = text[1 : end - 1]
        key = inner.split(":", 1)[0].strip()
        rest = text[end:].strip()
        if rest.startswith(":"):
            rest = rest[1:]
        return Member(
            kind="index",
            name=key,
            type=parse_type(rest, type_params) if rest else None,
            readonly=readonly,
            raw=raw,
        )

    # Getters and setters: upstream declares `get sortState(): SortState` and
    # `set columns(v: ColumnsDefine)`. In Kotlin these are one property, not a method, so the
    # accessor is recorded and the two halves are merged after the whole declaration is parsed.
    accessor = None
    for prefix in ("get", "set"):
        if _at_keyword(text, 0, prefix):
            accessor = prefix
            text = text[len(prefix) :].lstrip()
            break

    m = re.match(r"([A-Za-z_$][\w$]*|'[^']*'|\"[^\"]*\")\s*(\?)?", text)
    if not m:
        return None
    name = m.group(1)
    if name[:1] in "'\"":
        name = name[1:-1]
    optional = bool(m.group(2))
    i = m.end()

    # Method with its own type parameters.
    if i < len(text) and text[i] == "<":
        close = split_angle(text, i)
        own = TypeParser(text[i:close], type_params)._type_param_names(text[i + 1 : close - 1])
        i = close
        j = i
        while j < len(text) and text[j].isspace():
            j += 1
        if j < len(text) and text[j] == "(":
            end = _skip_balanced(text, j, "(", ")")
            inner = text[j + 1 : end - 1]
            ret = text[end:].strip()
            if ret.startswith(":"):
                ret = ret[1:]
            return Member(
                kind="method",
                name=name,
                optional=optional,
                type=parse_type(ret, type_params) if ret else None,
                params=parse_params(inner, type_params),
                type_params=own,
                raw=raw,
            )

    if i < len(text) and text[i] == "(":
        end = _skip_balanced(text, i, "(", ")")
        inner = text[i + 1 : end - 1]
        ret = text[end:].strip()
        if ret.startswith(":"):
            ret = ret[1:]
        if accessor == "get":
            return Member(
                kind="property",
                name=name,
                type=parse_type(ret, type_params) if ret else None,
                readonly=True,
                raw=raw,
            )
        if accessor == "set":
            params = parse_params(inner, type_params)
            return Member(
                kind="setter",
                name=name,
                type=params[0].type if params else None,
                optional=optional,
                raw=raw,
            )
        return Member(
            kind="method",
            name=name,
            optional=optional,
            readonly=readonly,
            type=parse_type(ret, type_params) if ret else None,
            params=parse_params(inner, type_params),
            raw=raw,
        )

    # Property: `name?: T`, or a bare `name;` (implicitly `any`).
    rest = text[i:].strip()
    if rest.startswith(":"):
        type_text = rest[1:].strip()
        return Member(
            kind="property",
            name=name,
            optional=optional,
            readonly=readonly,
            type=parse_type(type_text, type_params),
            raw=raw,
        )
    return Member(
        kind="property",
        name=name,
        optional=optional,
        readonly=readonly,
        type=TypeExpr("ref", name="any"),
        raw=raw,
    )


# ------------------------------------------------------------------------------------------------
# File parsing: declarations, imports, re-exports
# ------------------------------------------------------------------------------------------------


@dataclass
class ParsedFile:
    path: str  # path relative to the types root, POSIX separators
    decls: dict[str, Decl] = field(default_factory=dict)
    imports: dict[str, tuple[str, str]] = field(default_factory=dict)  # local -> (file, name)
    reexports: dict[str, tuple[str, str]] = field(default_factory=dict)  # name -> (file, name)
    # `export { A, B as C }` without `from`: the names come from this file (via its imports or its
    # own declarations). Upstream's `index.d.ts` exports most of its surface this way.
    local_exports: dict[str, str] = field(default_factory=dict)  # public name -> local name
    star_reexports: list[str] = field(default_factory=list)


_DECL_START = re.compile(
    r"(?m)^(?P<prefix>(?:export\s+)?(?:declare\s+)?(?:default\s+)?(?:abstract\s+)?)"
    r"(?P<keyword>interface|class|type|enum|const|let|var|function|namespace|module)\b"
)
_IMPORT_START = re.compile(r"(?m)^import\b")
_EXPORT_LIST_START = re.compile(r"(?m)^export\s*(?:type\s+)?(?P<sigil>[*{])")
_BLOCK_KEYWORDS = {"interface", "class", "enum", "namespace", "module"}


def _doc_before(src: str, start: int) -> str:
    """The `/** ... */` block comment directly above ``start``, if there is one."""
    trimmed = src[:start].rstrip()
    if not trimmed.endswith(_BLOCK_CLOSE):
        return ""
    open_index = trimmed.rfind(_BLOCK_OPEN)
    if open_index < 0:
        return ""
    body = trimmed[open_index + 2 : -len(_BLOCK_CLOSE)]
    if not body.lstrip().startswith("*"):
        return ""
    return _clean_doc(body.lstrip()[1:])


def _statement_end(src: str, start: int, keyword: str) -> int:
    """Index just past the statement that starts at ``start``.

    ``interface`` / ``class`` / ``enum`` / ``namespace`` / ``module`` end at their brace body;
    everything else ends at the first `;` outside any bracket. Angle brackets are tracked so that a
    `{` inside a type argument (`extends Foo<{ a: string }>`) is not mistaken for a body.
    """
    block = keyword in _BLOCK_KEYWORDS
    i = start
    depth = 0
    angle = 0
    n = len(src)
    while i < n:
        ch = src[i]
        if ch in "'\"`":
            i = _skip_string(src, i)
            continue
        if src.startswith(_BLOCK_OPEN, i):
            i, _ = _skip_comment(src, i)
            continue
        if src.startswith(_LINE_COMMENT, i):
            i, _ = _skip_comment(src, i)
            continue
        if ch == "<":
            angle += 1
        elif ch == ">":
            if angle > 0 and src[i - 1] != "=":
                angle -= 1
        elif block and ch == "{" and depth == 0 and angle == 0:
            return _skip_balanced(src, i, "{", "}")
        elif ch == ";" and depth == 0 and angle == 0:
            return i + 1
        elif ch in "{([":
            depth += 1
        elif ch in "})]":
            if depth > 0:
                depth -= 1
        i += 1
    return n


def parse_file(path: str, rel: str) -> ParsedFile:
    with open(path, "r", encoding="utf-8") as handle:
        src = handle.read()
    parsed = ParsedFile(path=rel)

    pos = 0
    n = len(src)
    while pos < n:
        candidates = [
            m
            for m in (
                _IMPORT_START.search(src, pos),
                _EXPORT_LIST_START.search(src, pos),
                _DECL_START.search(src, pos),
            )
            if m is not None
        ]
        if not candidates:
            break
        match = min(candidates, key=lambda m: m.start())
        if match.re is _IMPORT_START:
            end = _statement_end(src, match.start(), "import")
            _parse_import(src[match.start() : end], rel, parsed)
        elif match.re is _EXPORT_LIST_START:
            end = _statement_end(src, match.start(), "const")
            _parse_export_list(src[match.start() : end], rel, parsed)
        else:
            keyword = match.group("keyword")
            end = _statement_end(src, match.start(), keyword)
            statement = src[match.start() : end]
            decl = parse_declaration(statement, rel, _doc_before(src, match.start()))
            if decl is not None:
                parsed.decls[decl.name] = decl
        pos = end

    return parsed


def _parse_export_list(statement: str, rel: str, parsed: ParsedFile) -> None:
    body = statement[len("export") :].strip()
    if body.startswith("type "):
        body = body[len("type ") :].strip()
    if body.startswith("*"):
        m = re.search(r"from\s+['\"]([^'\"]+)['\"]", body)
        if m:
            parsed.star_reexports.append(_resolve_module(m.group(1), rel))
        return
    if not body.startswith("{"):
        return
    end = _skip_balanced(body, 0, "{", "}")
    names = body[1 : end - 1]
    m = re.search(r"from\s+['\"]([^'\"]+)['\"]", body)
    for entry in split_top_level(names, ","):
        entry = entry.strip()
        if not entry:
            continue
        # `export { A as B }` — B is the public name.
        parts = entry.split(" as ")
        source = parts[0].strip()
        public = parts[-1].strip()
        if m:
            parsed.reexports[public] = (_resolve_module(m.group(1), rel), source)
        else:
            parsed.local_exports[public] = source
            # Mark the local declaration exported: its values are real module exports, and the
            # emitter uses that flag to decide whether an `external` declaration may carry the
            # upstream JavaScript name.
            decl = parsed.decls.get(source)
            if decl is not None:
                decl.exported = True


_IMPORT_NAMED = re.compile(r"import\s+(?:type\s+)?\{([^}]*)\}\s+from\s+(['\"])([^'\"]+)\2")


def _parse_import(statement: str, rel: str, parsed: ParsedFile) -> None:
    m = re.search(r"import\s+\*\s+as\s+([A-Za-z_$][\w$]*)\s+from\s+['\"]([^'\"]+)['\"]", statement)
    if m:
        # A namespace import: remember it as `(file, "*")` so an `export { X }` of that binding can
        # expand to the module's own exports.
        parsed.imports[m.group(1)] = (_resolve_module(m.group(2), rel), "*")
        return
    m = _IMPORT_NAMED.search(statement)
    if m:
        target = _resolve_module(m.group(3), rel)
        for entry in split_top_level(m.group(1), ","):
            entry = entry.strip()
            if not entry:
                continue
            parts = entry.split(" as ")
            source = parts[0].strip()
            local = parts[-1].strip()
            parsed.imports[local] = (target, source)
        return
    # `import X from` and `import * as X from` carry no type information we need here.
    m = re.search(r"import\s+([A-Za-z_$][\w$]*)\s+from\s+['\"]([^'\"]+)['\"]", statement)
    if m:
        parsed.imports[m.group(1)] = (_resolve_module(m.group(2), rel), "default")


def _resolve_module(spec: str, from_rel: str) -> str:
    """Resolves a relative module specifier to a types-root-relative file."""
    if not spec.startswith("."):
        return spec  # External package (`ag-stack` etc.)
    base = os.path.dirname(from_rel)
    joined = os.path.normpath(os.path.join(base, spec)).replace("\\", "/")
    if joined.endswith(".d.ts"):
        return joined
    return joined + ".d.ts"


def parse_declaration(statement: str, rel: str, doc: str) -> Decl | None:
    exported = False
    text = statement
    for prefix in ("export", "declare", "default", "abstract"):
        if _at_keyword(text, 0, prefix):
            exported = exported or prefix == "export"
            text = text[len(prefix) :].lstrip()
    head = re.match(
        r"(interface|class|type|enum|const|let|var|function|namespace|module)\b", text
    )
    if not head:
        return None
    keyword = head.group(1)
    name, i = _read_name(text, head.end())
    if not name:
        return None

    if keyword == "interface":
        type_params, defaults, i = _read_type_params(text, i)
        heritage, i = _read_heritage(text, i)
        body, _ = _read_body(text, i)
        return Decl(
            kind="interface",
            name=name,
            file=rel,
            exported=exported,
            doc=doc,
            raw=normalize_ws(statement),
            type_params=type_params,
            type_param_defaults=defaults,
            heritage=heritage,
            members=parse_members(body, type_params),
        )

    if keyword == "class":
        type_params, defaults, i = _read_type_params(text, i)
        heritage, i = _read_heritage(text, i)
        body, _ = _read_body(text, i)
        return Decl(
            kind="class",
            name=name,
            file=rel,
            exported=exported,
            doc=doc,
            raw=normalize_ws(statement),
            type_params=type_params,
            type_param_defaults=defaults,
            heritage=heritage,
            members=parse_members(body, type_params),
        )

    if keyword == "type":
        type_params, defaults, i = _read_type_params(text, i)
        eq = find_top_level(text[i:], "=")
        if eq < 0:
            return None
        # A mapped type body holds `in`/`keyof`; keep the text and let the emitter decide.
        alias_text = text[i + eq + 1 :].strip().rstrip(";")
        return Decl(
            kind="alias",
            name=name,
            file=rel,
            exported=exported,
            doc=doc,
            raw=normalize_ws(statement),
            type_params=type_params,
            type_param_defaults=defaults,
            alias=parse_type(alias_text, type_params),
        )

    if keyword in ("const", "let", "var"):
        colon = find_top_level(text[i:], ":")
        if colon < 0:
            # `export declare const version = "1.26.8"`: the type is the initializer literal.
            eq = find_top_level(text[i:], "=")
            if eq < 0:
                return None
            initializer = text[i + eq + 1 :].strip().rstrip(";")
            return Decl(
                kind="const",
                name=name,
                file=rel,
                exported=exported,
                doc=doc,
                raw=normalize_ws(statement),
                const_type=parse_type(initializer),
            )
        type_text = text[i + colon + 1 :].strip().rstrip(";")
        return Decl(
            kind="const",
            name=name,
            file=rel,
            exported=exported,
            doc=doc,
            raw=normalize_ws(statement),
            const_type=parse_type(type_text),
        )

    if keyword == "function":
        type_params, defaults, i = _read_type_params(text, i)
        body, end = _read_params(text, i)
        ret = text[end:].strip()
        if ret.startswith(":"):
            ret = ret[1:].strip().rstrip(";")
        return Decl(
            kind="function",
            name=name,
            file=rel,
            exported=exported,
            doc=doc,
            raw=normalize_ws(statement),
            type_params=type_params,
            type_param_defaults=defaults,
            params=parse_params(body, type_params),
            returns=parse_type(ret, type_params) if ret else None,
        )

    if keyword == "enum":
        body, _ = _read_body(text, i)
        entries: list[tuple[str, str]] = []
        for part in split_top_level(body, ","):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                key, value = part.split("=", 1)
                entries.append((key.strip(), value.strip()))
            else:
                entries.append((part, '"%s"' % part))
        return Decl(
            kind="enum",
            name=name,
            file=rel,
            exported=exported,
            doc=doc,
            raw=normalize_ws(statement),
            enum_members=entries,
        )

    return None


def _read_name(text: str, i: int) -> tuple[str, int]:
    while i < len(text) and text[i].isspace():
        i += 1
    if i < len(text) and text[i] in "'\"":
        end = _skip_string(text, i)
        return text[i + 1 : end - 1], end
    m = re.match(r"[A-Za-z_$][\w$-]*", text[i:])
    if not m:
        return "", i
    return m.group(0), i + len(m.group(0))


def _read_type_params(text: str, i: int) -> tuple[list[str], dict[str, str], int]:
    j = i
    while j < len(text) and text[j].isspace():
        j += 1
    if j >= len(text) or text[j] != "<":
        return [], {}, i
    close = split_angle(text, j)
    inner = text[j + 1 : close - 1]
    names: list[str] = []
    defaults: dict[str, str] = {}
    for part in split_top_level(inner, ","):
        part = part.strip()
        if not part:
            continue
        eq = find_top_level(part, "=")
        head = part if eq < 0 else part[:eq]
        m = re.match(r"(?:const\s+)?([A-Za-z_$][\w$]*)", head)
        if m:
            names.append(m.group(1))
            if eq >= 0:
                defaults[m.group(1)] = part[eq + 1 :].strip()
    return names, defaults, close


def _read_heritage(text: str, i: int) -> tuple[list[str], int]:
    heritage: list[str] = []
    while True:
        j = i
        while j < len(text) and text[j].isspace():
            j += 1
        if j < len(text) and text[j] == "{":
            return heritage, j
        matched = None
        for keyword in ("extends", "implements"):
            if _at_keyword(text, j, keyword):
                matched = keyword
                j += len(keyword)
                break
        if matched is None:
            return heritage, i
        # Heritage entries end at `{`, or at `implements`, or at a depth-0 `;`.
        start = j
        depth = 0
        while j < len(text):
            c = text[j]
            if c in "'\"`":
                j = _skip_string(text, j)
                continue
            if depth == 0 and c == "{":
                break
            if depth == 0 and _at_keyword_static(text, j, "implements"):
                break
            if c in "{([":
                depth += 1
            elif c in "})]":
                depth -= 1
            j += 1
        for part in split_top_level(text[start:j], ","):
            part = normalize_ws(part)
            if part:
                heritage.append(part.rstrip(";").strip())
        i = j


def _at_keyword_static(text: str, i: int, word: str) -> bool:
    return text.startswith(word, i) and not (
        i + len(word) < len(text) and (text[i + len(word)].isalnum() or text[i + len(word)] in "_$")
    )


def _read_body(text: str, i: int) -> tuple[str, int]:
    while i < len(text) and text[i].isspace():
        i += 1
    if i >= len(text) or text[i] != "{":
        return "", i
    end = _skip_balanced(text, i, "{", "}")
    return text[i + 1 : end - 1], end


def _read_params(text: str, i: int) -> tuple[str, int]:
    while i < len(text) and text[i].isspace():
        i += 1
    if i >= len(text) or text[i] != "(":
        return "", i
    end = _skip_balanced(text, i, "(", ")")
    return text[i + 1 : end - 1], end


# ------------------------------------------------------------------------------------------------
# Symbol table and reachability
# ------------------------------------------------------------------------------------------------


class Universe:
    def __init__(self, roots: dict[str, str], modules: dict[str, str] | None = None):
        """``roots`` maps a prefix to a types directory; ``modules`` maps npm specs to prefixes."""
        self.roots = dict(roots)
        self.modules = dict(modules or {})
        self.files: dict[str, ParsedFile] = {}
        # Every root is a whole published package whose entry point is `index.d.ts`; the npm package
        # path stays implicit in the prefix, and each declaration's `@file:JsModule` is derived from
        # the `.d.ts` path it lives in (the packages ship `es/` without an `exports` map).
        self.entries = {prefix: prefix + "/index.d.ts" for prefix in self.roots}
        # Files whose star re-exports are not part of the public surface (upstream's `internal`
        # entry points).
        self.skip_star: set[str] = set()
        for prefix, root in self.roots.items():
            for dirpath, _dirnames, filenames in os.walk(root):
                for filename in filenames:
                    if not filename.endswith(".d.ts"):
                        continue
                    full = os.path.join(dirpath, filename)
                    rel = prefix + "/" + os.path.relpath(full, root).replace("\\", "/")
                    self.files[rel] = parse_file(full, rel)
        # Import specifiers do not always match the file name's casing (`./iRangeService` for
        # `IRangeService.d.ts`), and the file system is case-insensitive on Windows. Resolve through
        # a lower-cased index so both worlds agree.
        self.lower_index = {rel.lower(): rel for rel in self.files}

    def file_key(self, rel: str) -> str | None:
        if rel in self.files:
            return rel
        found = self.lower_index.get(rel.lower())
        if found is not None:
            return found
        # TypeScript resolves a directory import to its `index.d.ts`; `_resolve_module` appends
        # `.d.ts` first, so both spellings are tried (`./ts-types` -> `ts-types/index.d.ts`).
        candidates = [rel + "/index.d.ts"]
        if rel.endswith(".d.ts"):
            candidates.insert(0, rel[: -len(".d.ts")] + "/index.d.ts")
        for index in candidates:
            if index in self.files:
                return index
            found = self.lower_index.get(index.lower())
            if found is not None:
                return found
        return None

    def module_entry(self, spec: str) -> str | None:
        prefix = self.modules.get(spec)
        if prefix is None:
            return None
        return self.entries.get(prefix)

    # -- export resolution -----------------------------------------------------------------
    def exports_of(self, rel: str, _seen: set[str] | None = None) -> dict[str, tuple[str, str]]:
        """Every name the file exports, as name -> (file, original name)."""
        seen = _seen if _seen is not None else set()
        if rel in seen:
            return {}
        seen.add(rel)
        parsed = self.files.get(rel)
        if parsed is None:
            return {}
        out: dict[str, tuple[str, str]] = {}
        for rel_target in parsed.star_reexports:
            if rel_target in self.skip_star:
                continue
            out.update(self.exports_of(rel_target, seen))
        for name, target in parsed.reexports.items():
            target_file, original = target
            entry = self.module_entry(target_file)
            if entry is not None and target_file not in self.files:
                target_file = entry
            resolved_file = self.file_key(target_file)
            if resolved_file is None:
                continue
            exported = self.exports_of(resolved_file, set())
            if original in exported:
                out[name] = exported[original]
            elif original in self.files[resolved_file].decls:
                out[name] = (resolved_file, original)
        for public, source in parsed.local_exports.items():
            if source in parsed.decls:
                out[public] = (rel, source)
                continue
            target = parsed.imports.get(source)
            if target is None:
                continue
            target_file, original = target
            entry = self.module_entry(target_file)
            if entry is not None and target_file not in self.files:
                target_file = entry
            resolved_file = self.file_key(target_file)
            if resolved_file is None:
                continue
            if original == "*":
                # `import * as TYPES from './ts-types'; export { TYPES }`: the Kotlin surface is
                # the members of that module, not one opaque namespace value.
                out.update(self.exports_of(resolved_file, set()))
                continue
            exported = self.exports_of(resolved_file, set())
            if original in exported:
                out[public] = exported[original]
            elif original in self.files[resolved_file].decls:
                out[public] = (resolved_file, original)
        for name, decl in parsed.decls.items():
            if decl.exported:
                out[name] = (rel, name)
        return out

    def public_names(self, entry: str) -> dict[str, tuple[str, str]]:
        return self.exports_of(entry)

    # -- resolution -------------------------------------------------------------------------
    def resolve(self, name: str, rel: str) -> tuple[str, str] | None:
        """Resolves a type name used inside `rel` to its definition."""
        # `Foo<T>` and `Foo<A, B>` name the same declaration; the arguments are dropped (the
        # wrapper is generic-free), so the lookup only ever needs the bare name.
        name = name.split("<", 1)[0].strip()
        parsed = self.files.get(rel)
        if parsed is not None:
            if name in parsed.decls:
                return (rel, name)
            if name in parsed.imports:
                target_file, original = parsed.imports[name]
                entry = self.module_entry(target_file)
                if entry is not None:
                    target_file = entry
                resolved_file = self.file_key(target_file)
                if resolved_file is not None:
                    if original in self.files[resolved_file].decls:
                        return (resolved_file, original)
                    exported = self.exports_of(resolved_file, set())
                    if original in exported:
                        return exported[original]
        # Fall back to the file's own export table (covers `export *` chains).
        exported = self.exports_of(rel, set())
        if name in exported:
            return exported[name]
        return None

    def decl(self, key: tuple[str, str]) -> Decl | None:
        return self.files[key[0]].decls.get(key[1])


# ------------------------------------------------------------------------------------------------
# Reachability: the transitive closure of the exported names
# ------------------------------------------------------------------------------------------------


def recursive_types(decl: Decl) -> list[TypeExpr]:
    """Every type expression a declaration spells out."""
    out: list[TypeExpr] = []
    if decl.alias is not None:
        out.append(decl.alias)
    if decl.const_type is not None:
        out.append(decl.const_type)
    if decl.returns is not None:
        out.append(decl.returns)
    for param in decl.params:
        if param.type is not None:
            out.append(param.type)
    for member in decl.members:
        out.append(member_type_expr(member))
    return out


def member_type_expr(member: Member) -> TypeExpr:
    """A member's value type: the property type, or the return type of a method."""
    if member.type is not None:
        return member.type
    return TypeExpr("ref", name="any")


def walk_member(member: Member) -> Iterator[TypeExpr]:
    yield from walk_type(member_type_expr(member))
    for param in member.params:
        if param.type is not None:
            yield from walk_type(param.type)


def walk_type(expr: TypeExpr) -> Iterator[TypeExpr]:
    yield expr
    for child in expr.args:
        yield from walk_type(child)
    for child in expr.items:
        yield from walk_type(child)
    if expr.returns is not None:
        yield from walk_type(expr.returns)
    for param in expr.params:
        if param.type is not None:
            yield from walk_type(param.type)
    for member in expr.members:
        yield from walk_member(member)


def collect_surface(
    universe: Universe, entries: Iterable[str], skip_star: set[str]
) -> dict[str, tuple[str, str]]:
    """Returns the public names of the given entry files."""
    universe.skip_star = set(skip_star)
    public: dict[str, tuple[str, str]] = {}
    for entry in entries:
        public.update(universe.public_names(entry))
    return public


BUILTIN_TYPE_NAMES = set(PRIMITIVES) | {
    # TypeScript utility generics, resolved structurally by the emitter.
    "Record",
    "Partial",
    "Required",
    "Readonly",
    "Pick",
    "Omit",
    "Exclude",
    "Extract",
    "NonNullable",
    "ReturnType",
    "Parameters",
    "ConstructorParameters",
    "InstanceType",
    "Awaited",
    "ThisType",
    # JavaScript globals the emitter maps onto Kotlin types.
    "Array",
    "ReadonlyArray",
    "Map",
    "Set",
    "WeakMap",
    "WeakSet",
    "Promise",
    "Function",
    "Date",
    "RegExp",
    "Error",
    "String",
    "Number",
    "Boolean",
    "Object",
    "Iterable",
    "Iterator",
    "Symbol",
    "JSON",
    "Math",
}


def bound_type_names(decl: Decl) -> set[str]:
    """Every type parameter a declaration brings into scope, including member-level ones."""
    names = set(decl.type_params)
    for member in decl.members:
        names.update(member.type_params)
        for param in member.params:
            if param.type is not None:
                for node in walk_type(param.type):
                    names.update(n for n in node.type_params if isinstance(n, str))
    for expr in recursive_types(decl):
        for node in walk_type(expr):
            names.update(n for n in node.type_params if isinstance(n, str))
    return {n for n in names if isinstance(n, str)}


def closure(
    universe: Universe, public: dict[str, tuple[str, str]]
) -> tuple[dict[tuple[str, str], Decl], dict[tuple[str, str], str], list[str]]:
    """Grows the public names into everything their members mention.

    Returns (declarations, public name per key, unresolved references).
    """
    keys: set[tuple[str, str]] = set()
    names: dict[tuple[str, str], str] = {}
    unresolved: set[str] = set()
    queue: list[tuple[str, str]] = []
    for name, key in sorted(public.items()):
        keys.add(key)
        names[key] = name
        queue.append(key)

    decls: dict[tuple[str, str], Decl] = {}
    while queue:
        key = queue.pop()
        if key in decls:
            continue
        decl = universe.decl(key)
        if decl is None:
            unresolved.add(f"{key[1]} (missing declaration in {key[0]})")
            continue
        decls[key] = decl
        bound = bound_type_names(decl)
        for expr in recursive_types(decl):
            for node in walk_type(expr):
                if node.kind != "ref":
                    continue
                if node.name in bound or node.name in BUILTIN_TYPE_NAMES:
                    continue
                referenced = universe.resolve(node.name, key[0])
                if referenced is None:
                    unresolved.add(node.name)
                    continue
                if referenced not in decls:
                    keys.add(referenced)
                    queue.append(referenced)
        # Base interfaces are stored as raw heritage strings, so they are not reached by the
        # member-type walk above; pull them in explicitly or whole API groups go missing
        # (`GridApi.destroy()` sits in a base interface, for instance).
        for heritage in decl.heritage:
            base_name = heritage.split("<", 1)[0].strip()
            if base_name in bound:
                continue
            referenced = universe.resolve(base_name, key[0])
            if referenced is None:
                unresolved.add(base_name)
                continue
            if referenced not in decls:
                keys.add(referenced)
                queue.append(referenced)
    return decls, names, sorted(unresolved)



# ------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------------------------------------

KOTLIN_PACKAGE = "io.github.shijianjs.ktjs.vtable"

#: npm package each root prefix belongs to. The `es/` layout is shipped in the published tarball
#: without an `exports` map, so every `.d.ts` path is also a valid ESM entry point.
ROOT_MODULES = {
    "vtable": "@visactor/vtable",
    "editors": "@visactor/vtable-editors",
}

#: Upstream declarations that exist but must not become Kotlin names of their own.
SKIPPED_NAMES = {"default", "_default", "constructor"}


def build_universe(args) -> Universe:
    roots = {"vtable": args.types}
    if args.editors_types:
        roots["editors"] = args.editors_types
    return Universe(
        roots,
        modules={
            "@visactor/vtable": "vtable",
            "@visactor/vtable-editors": "editors",
        },
    )


def _sanitize(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not cleaned or not (cleaned[0].isalpha() or cleaned[0] == "_"):
        cleaned = "_" + cleaned
    return cleaned


def assign_kotlin_names(public: dict[str, tuple[str, str]], decls) -> dict[tuple[str, str], str]:
    """One Kotlin name per upstream declaration, unique inside the module's Kotlin package.

    The public export name wins, because that is the name a caller sees on the npm package:
    `ListTableAll` is exported as `ListTable`, so it becomes `ListTable`. A declaration that
    already owns that name (the base class `ListTable` in `ListTable.d.ts`) gets a `Base`
    suffix instead, and every reference to it keeps pointing at the base class.
    """
    names: dict[tuple[str, str], str] = {}
    used: set[str] = set()

    for public_name, key in sorted(public.items()):
        if public_name in SKIPPED_NAMES or key not in decls:
            continue
        name = _sanitize(public_name)
        if name in used:
            continue
        names[key] = name
        used.add(name)

    for key in sorted(decls):
        if key in names:
            continue
        decl = decls[key]
        if decl.name in SKIPPED_NAMES:
            continue
        base = _sanitize(decl.name)
        candidate = base
        if candidate in used:
            # The usual collision is a public alias for a subclass (`ListTableAll` -> `ListTable`)
            # and the upstream base class of the same name.
            candidate = base + "Base"
        counter = 2
        while candidate in used:
            candidate = "%s%d" % (base, counter)
            counter += 1
        names[key] = candidate
        used.add(candidate)
    return names


def module_for(rel: str) -> str:
    """The ESM specifier a declaration's values are imported from.

    Two upstream packaging details decide the shape:

    * `@visactor/vtable` has no `exports` map, so a `.d.ts` path is imported directly — but the
      Kotlin/JS webpack config treats the generated bundle as strict ESM, so the specifier needs the
      runtime `.js` suffix even though the declaration file is `.d.ts`.
    * `@visactor/vtable-editors` exposes only `"."` in its `exports` map; deep imports are rejected
      by the resolver, so every declaration comes from the package root.
    """
    prefix, _, path = rel.partition("/")
    if prefix == "editors":
        return ROOT_MODULES[prefix]
    path = path[: -len(".d.ts")] if path.endswith(".d.ts") else path
    return "%s/es/%s.js" % (ROOT_MODULES[prefix], path)


def surface_report(decls, public, unresolved, fallbacks, version: str) -> str:
    """Markdown summary of what the generator produced and what it could not express."""
    kinds: dict[str, int] = {}
    for _key, decl in decls.items():
        kinds[decl.kind] = kinds.get(decl.kind, 0) + 1
    groups: dict[str, list[tuple[str, str]]] = {}
    for kind, context, detail in fallbacks:
        groups.setdefault(kind, []).append((context, detail))
    lines = [
        "# API surface report",
        "",
        "Generated by `scripts/generate-api.py`; do not edit by hand.",
        "",
        "- Upstream: `@visactor/vtable` %s and `@visactor/vtable-editors` %s (`es/*.d.ts`)"
        % (version, version),
        "- Public names exported by the two `index.d.ts`: %d" % len(public),
        "- Reachable declarations: %d" % len(decls),
        "",
        "## Declaration kinds",
        "",
        "| kind | count |",
        "|---|---:|",
    ]
    for kind, count in sorted(kinds.items()):
        lines.append("| %s | %d |" % (kind, count))
    lines.extend(
        [
            "",
            "## Unresolved upstream references",
            "",
            "Names the upstream declarations mention but neither declare nor re-export. They are",
            "declared as `JsAny` in the wrapper. The VTable packages reach into `@visactor/vutils`,",
            "`@visactor/vrender*`, `@visactor/vdataset` and `@visactor/vscale` for a handful of",
            "graphics/data helpers; those belong to sibling VisActor libraries and are outside this",
            "wrapper's scope.",
            "",
        ]
    )
    if unresolved:
        lines.extend("- `%s`" % name for name in sorted(unresolved))
    else:
        lines.append("None.")
    lines.extend(["", "## Kotlin fallbacks", ""])
    if not groups:
        lines.append("None.")
    for kind, items in sorted(groups.items()):
        lines.append("### %s (%d)" % (kind, len(items)))
        lines.append("")
        for context, detail in items[:60]:
            lines.append("- `%s`: %s" % (context, detail.replace("|", "\\|")))
        if len(items) > 60:
            lines.append("- … %d more" % (len(items) - 60))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def emit(args, universe, public, decls, kotlin_names) -> int:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ktjs_emitter

    renderer = ktjs_emitter.Renderer(
        gen=sys.modules[__name__],
        universe=universe,
        decls=decls,
        public=public,
        version=args.version,
        upstream="@visactor/vtable",
        kotlin_names=kotlin_names,
    )

    entries: dict[str, tuple[str, list[tuple[str, str]]]] = {}
    emitted_names: set[str] = set()
    per_file: dict[str, list[tuple[str, tuple[str, str]]]] = {}
    modules: dict[str, str] = {}
    for key in sorted(decls):
        if key[1] in SKIPPED_NAMES:
            continue
        name = kotlin_names.get(key)
        if name is None or name in emitted_names:
            continue
        # `TableEvents` and the base classes are fine as types; what must not repeat is the
        # JavaScript value behind the same Kotlin name.
        decl = decls[key]
        if decl.kind in ("const", "function", "class") and name in emitted_names:
            continue
        emitted_names.add(name)
        file_name = ktjs_emitter.kotlin_file_name(key[0])
        modules.setdefault(file_name, module_for(key[0]))
        per_file.setdefault(file_name, []).append((name, key))

    # Two roots share file names (`index.d.ts`); keep the prefix in the Kotlin file name when they
    # collide, which only happens for the entry files.
    final_files: dict[str, list[tuple[str, tuple[str, str]]]] = {}
    for file_name, keys in per_file.items():
        target = file_name
        if target in final_files:
            target = ktjs_emitter.pascal(keys[0][1][0].split("/")[0]) + file_name
        final_files[target] = keys
        modules[target] = modules[file_name]

    buckets = {"alias": "Aliases.kt", "enum": "Enums.kt", "union": "Unions.kt",
               "literal": "Literals.kt", "object": "InlineObjects.kt", "tuple": "Tuples.kt"}
    for file_name, keys in final_files.items():
        has_values = any(decls[key].kind in ("const", "function", "class") for _n, key in keys)
        if not has_values:
            entries[file_name] = (".", keys)
            continue
        # `@file:JsModule` only accepts external declarations, so Kotlin-level pieces (`typealias`,
        # factory functions, the constant objects of enums) move to files without it.
        values = [item for item in keys if decls[item[1]].kind not in ("alias", "enum")]
        entries[file_name] = (modules[file_name], values)
        for kind in ("alias", "enum"):
            moved = [item for item in keys if decls[item[1]].kind == kind]
            if not moved:
                continue
            bucket = buckets[kind]
            if bucket not in entries:
                entries[bucket] = (".", [])
            entries[bucket][1].extend(moved)

    # Public names that differ from the Kotlin name of their declaration: `ListTableAll` is
    # exported as `ListTable`, so a `typealias` restores the public spelling.
    aliases: list[tuple[str, str, str, tuple[str, str]]] = []
    for public_name, key in sorted(public.items()):
        name = kotlin_names.get(key)
        if name is None or name == public_name or public_name in SKIPPED_NAMES:
            continue
        decl = decls[key]
        aliases.append((public_name, name, decl.kind, key))
    alias_lines = ktjs_emitter.render_public_aliases(renderer, aliases)
    if alias_lines:
        entries["PublicAliases.kt"] = (".", [])
        renderer.extra_files["PublicAliases.kt"] = alias_lines

    outputs = renderer.render_all(entries)

    out_dir = os.path.abspath(args.out)
    if os.path.isdir(out_dir):
        for name in os.listdir(out_dir):
            if name.endswith(".kt"):
                os.remove(os.path.join(out_dir, name))
    os.makedirs(out_dir, exist_ok=True)
    for name, text in sorted(outputs.items()):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    report = surface_report(decls, public, args.unresolved, renderer.fallbacks, args.version)
    os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
    with open(args.report, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(report)

    print(f"wrote {len(outputs)} Kotlin files to {out_dir}")
    print(f"fallbacks: {len(renderer.fallbacks)}")
    for kind, count in sorted(
        {kind: sum(1 for f in renderer.fallbacks if f[0] == kind) for kind in {f[0] for f in renderer.fallbacks}}.items()
    ):
        print(f"  {kind:22s} {count}")
    print(f"report: {os.path.abspath(args.report)}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--types", required=True, help="@visactor/vtable/es")
    parser.add_argument("--editors-types", help="@visactor/vtable-editors/es")
    parser.add_argument("--entry", default="index.d.ts")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--emit", action="store_true", help="write the Kotlin declarations")
    parser.add_argument(
        "--out",
        default="ktjs-vtable/src/jsMain/kotlin/io/github/shijianjs/ktjs/vtable",
    )
    parser.add_argument("--report", default="docs/development/api-surface-report.md")
    parser.add_argument("--version", default="1.26.8")
    args = parser.parse_args(argv)

    universe = build_universe(args)
    entries = [universe.entries[prefix] for prefix in universe.roots]
    public = collect_surface(universe, entries, skipped_entries())
    decls, names, unresolved = closure(universe, public)
    args.unresolved = unresolved
    kotlin_names = assign_kotlin_names(public, decls)

    kinds: dict[str, int] = {}
    for key, decl in decls.items():
        kinds[decl.kind] = kinds.get(decl.kind, 0) + 1

    print(f"files: {len(universe.files)}")
    print(f"exported names: {len(public)}")
    print(f"reachable declarations: {len(decls)}")
    for kind, count in sorted(kinds.items()):
        print(f"  {kind:10s} {count}")
    print(f"unresolved references: {len(unresolved)}")

    if args.emit:
        return emit(args, universe, public, decls, kotlin_names)
    return 0


def skipped_entries() -> set[str]:
    """Upstream entry points that are internal and therefore not part of the wrapper's surface."""
    return set()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))