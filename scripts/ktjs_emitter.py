"""Turns the parsed VTable declarations into Kotlin/JS external declarations.

Driven by `scripts/generate-api.py`: that script parses the upstream `.d.ts` files and computes the
reachable declarations, this module writes the Kotlin sources. The output is deterministic, so the
generated files can live in the repository and be diffed on every upstream bump.

Modelling rules follow the project's `ktjs-type-mapping` skill:

* structural types become `external interface` (never `: JsAny`);
* unions become one opaque interface plus one same-named factory per member;
* string-literal unions become a `sealed external interface` plus a `<Name>s` constants object;
* upstream type parameters are dropped and their uses become `JsAny` — the wrapper is generic-free
  on purpose, see `docs/development/technical-decisions.md`;
* whatever Kotlin cannot express is *recorded* as a fallback instead of silently becoming `JsAny`.

Every upstream `.d.ts` is its own ESM module (`@visactor/vtable/es/<path>`), because the published
packages ship `es/` without an `exports` map: a value is imported from the file that declares it,
and the root `index.d.ts` namespaces (`TYPES`, `core`, `themes`, …) need no special modelling.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

KOTLIN_PACKAGE = "io.github.shijianjs.ktjs.vtable"

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

#: JavaScript globals mapped onto kotlin-wrappers types.
EXTERNALS = {
    "HTMLElement": "web.html.HTMLElement",
    "HTMLInputElement": "web.html.HTMLInputElement",
    "HTMLDivElement": "web.html.HTMLDivElement",
    "HTMLButtonElement": "web.html.HTMLButtonElement",
    "HTMLAnchorElement": "web.html.HTMLAnchorElement",
    "HTMLSpanElement": "web.html.HTMLSpanElement",
    "HTMLTableElement": "web.html.HTMLTableElement",
    "Element": "web.dom.Element",
    "Document": "web.dom.Document",
    "DocumentFragment": "web.dom.DocumentFragment",
    "Event": "web.events.Event",
    "EventTarget": "web.events.EventTarget",
    "CustomEvent": "web.events.CustomEvent",
    "MouseEvent": "web.mouse.MouseEvent",
    "KeyboardEvent": "web.keyboard.KeyboardEvent",
    "DragEvent": "web.dnd.DragEvent",
    "TouchEvent": "web.touch.TouchEvent",
    "Touch": "web.touch.Touch",
    "File": "web.file.File",
    "Blob": "web.blob.Blob",
    "ArrayBuffer": "js.buffer.ArrayBuffer",
    "Uint8Array": "js.typedarrays.Uint8Array",
    "ReadonlyMap": "js.collections.ReadonlyMap",
    "Promise": "kotlin.js.Promise",
    "Date": "kotlin.js.Date",
    "RegExp": "kotlin.js.RegExp",
    "Function": "Function",
    "Error": "Error",
    # Kotlin maps `kotlin.Error` / `kotlin.reflect`-free globals onto the JS objects, so these need
    # no import; the value repeats the name to say "render bare, ignore for imports".
    "Uint8ClampedArray": "js.typedarrays.Uint8ClampedArray",
}

CONTAINERS = {    "Array": ("Array", 1),
    "ReadonlyArray": ("Array", 1),
    "Set": ("JsSet", 1),
    "ReadonlySet": ("JsSet", 1),
    "WeakSet": ("WeakSet", 1),
    "Map": ("JsMap", 2),
    "ReadonlyMap": ("ReadonlyMap", 2),
    "WeakMap": ("WeakMap", 2),
    "Record": ("Record", 2),
    "Promise": ("Promise", 1),
}

#: Utility generics whose single argument is the whole answer.
UTILITY_PASSTHROUGH = {"Partial", "Required", "Readonly", "NonNullable", "Awaited", "ThisType"}

#: Utility generics Kotlin cannot express; they collapse to `JsAny`.
UTILITY_OPAQUE = {
    "Exclude",
    "Extract",
    "ReturnType",
    "Parameters",
    "ConstructorParameters",
    "InstanceType",
    "ThisParameterType",
    "OmitThisParameter",
}

#: Upstream "field path" types are mapped types over generic parameters (`field?: ColDefField<TData>`).
#: The wrapper is generic-free, so the mapped type cannot be evaluated; every value it can produce is
#: a string (a dotted path), which is exactly what AG Grid accepts at runtime, so these map to `String`.
STRING_TYPES = {"ColDefField", "NestedFieldPaths", "OwnFieldPaths", "NestedOnlyPaths"}

#: Members every Kotlin value already has; redeclaring them needs `@JsName` + a distinct Kotlin name.
ANY_MEMBERS = {"toString", "hashCode", "equals"}

KEYWORDS = {
    "as", "break", "class", "continue", "do", "else", "false", "for", "fun", "if", "in",
    "interface", "is", "null", "object", "package", "return", "super", "this", "throw", "true",
    "try", "typealias", "typeof", "val", "var", "when", "while", "by", "catch", "constructor",
    "delegate", "dynamic", "field", "file", "finally", "get", "import", "init", "param",
    "property", "receiver", "set", "setparam", "where", "actual", "abstract", "annotation",
    "companion", "const", "crossinline", "data", "enum", "expect", "external", "final", "infix",
    "inline", "inner", "internal", "lateinit", "noinline", "open", "operator", "out", "override",
    "private", "protected", "public", "reified", "sealed", "suspend", "tailrec", "vararg", "it",
}

_IDENTIFIER = re.compile(r"^[A-Za-z_]\w*$")


def kotlin_string(text: str) -> str:
    """A Kotlin string literal for `text`, escaping what Kotlin needs escaped."""
    return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")


def kotlin_ident(name: str) -> str:
    """Names a Kotlin declaration or property; keywords get backticks."""
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not cleaned or not (cleaned[0].isalpha() or cleaned[0] == "_"):
        cleaned = "_" + cleaned
    if cleaned in KEYWORDS:
        return "`%s`" % cleaned
    return cleaned


def pascal(text: str) -> str:
    parts = [p for p in re.split(r"[^0-9A-Za-z]+", text) if p]
    return "".join(p[:1].upper() + p[1:] for p in parts)


def camel(text: str) -> str:
    text = pascal(text)
    return text[:1].lower() + text[1:] if text else text


@dataclass
class Synth:
    """A synthesized Kotlin declaration (union, literal set, inline object or tuple)."""

    kind: str
    name: str
    doc: str
    body: list[str] = field(default_factory=list)


class Renderer:
    def __init__(self, gen, universe, decls, public, version: str, upstream: str, kotlin_names=None):
        self.gen = gen
        self.universe = universe
        self.decls = decls
        self.public = public
        self.version = version
        self.upstream = upstream
        self.kotlin_names = dict(kotlin_names or {})
        self.by_name: dict[str, tuple[str, str]] = {}
        for key in sorted(decls):
            self.by_name.setdefault(key[1], key)
        self.synth: dict[str, Synth] = {}
        self.synth_order: list[Synth] = []
        self.imports: set[str] = set()
        self.fallbacks: list[tuple[str, str, str]] = []
        self.bound: list[str] = []
        self.owner = ""
        self.member = ""
        self.flatten_cache = {}
        self.type_names = {name for name in self.kotlin_names.values()}
        self.plain_aliases: dict[str, str] = {}
        self.js_names: set[str] = set()
        # Handed in by the generator: rendered Kotlin bodies for files that hold no declarations
        # (the public `typealias` spellings).
        self.extra_files: dict[str, list[str]] = {}

    def kname(self, key) -> str:
        """The Kotlin name of a declaration key (public spelling when it has one)."""
        name = self.kotlin_names.get(key)
        if name is not None:
            return name
        decl = self.decls.get(key)
        return decl.name if decl is not None else key[1]

    # -- bookkeeping ---------------------------------------------------------------------
    def fallback(self, kind: str, context: str, detail: str = "") -> None:
        self.fallbacks.append((kind, context, detail))

    def imp(self, fqn: str) -> str:
        simple = fqn.rsplit(".", 1)[-1]
        if simple == fqn or simple in self.type_names:
            # Kotlin default imports (`Error`, `Function`) and shadowed names render bare.
            return simple
        self.imports.add(fqn)
        return simple

    def overload_key(self, text: str, expr) -> str:
        """A key that is equal exactly when two union branches give the same Kotlin signature."""
        expanded = self.erased(text)
        plain = self.erase(expr)
        if expanded in ("JsAny", "?") or plain in ("any", "?"):
            return "opaque"
        return expanded if expanded != text.rstrip("?") else plain

    def erased(self, text: str) -> str:
        """The Kotlin signature a rendered type contributes: aliases are transparent."""
        text = text.rstrip("?")
        for _ in range(6):
            if text not in self.plain_aliases:
                break
            text = self.plain_aliases[text].rstrip("?")
        return text

    def erase(self, expr, depth: int = 0) -> str:
        """Collapses a type expression to the JavaScript value shape it denotes.

        `any` means upstream wrote `any`/`unknown`; `?` means the name is neither declared nor
        mapped, so the wrapper renders it as `JsAny` as well. Both make a union un-distinguishable
        at runtime.
        """
        if expr is None or depth > 8:
            return "?"
        kind = expr.kind
        if kind == "ref":
            name = expr.name
            if name in ("any", "unknown", "object", "Object") or name in PRIMITIVES:
                return "any" if name not in PRIMITIVES else "P:" + PRIMITIVES[name]
            if name in STRING_TYPES:
                return "P:String"
            key = self.by_name.get(name) if not expr.args else None
            if key is not None:
                decl = self.decls[key]
                if decl.kind == "alias" and decl.alias is not None:
                    return self.erase(decl.alias, depth + 1)
                return "N:" + name
            if name in EXTERNALS:
                return "N:" + EXTERNALS[name]
            if name in CONTAINERS:
                return "N:" + name
            return "?"
        if kind == "literal":
            return "P:String" if expr.value[:1] in "'\"" else "P:Double"
        if kind == "object":
            return "object"
        if kind == "function":
            params = ",".join(self.erase(p.type, depth + 1) for p in expr.params)
            return "fn(%s)->%s" % (params, self.erase(expr.returns, depth + 1))
        if kind == "array":
            return "array<" + self.erase(expr.items[0], depth + 1) + ">"
        if kind == "tuple":
            return "tuple(" + ",".join(self.erase(i, depth + 1) for i in expr.items) + ")"
        if kind in ("union", "intersection"):
            parts = sorted(self.erase(i, depth + 1) for i in expr.items)
            if kind == "union" and any(p in ("any", "?") for p in parts):
                # Such a union renders as `JsAny` too, so it is opaque as a whole.
                return "any"
            return kind + "(" + ",".join(parts) + ")"
        if kind == "new":
            return "new:" + (expr.name or self.canon(expr))
        return "?"

    def is_function_like(self, text: str, depth: int = 0) -> bool:
        """Whether a rendered type is a lambda at the Kotlin level (typealiases are transparent)."""
        if "->" in text or "->" in self.erased(text):
            return True
        if depth > 4 or text.endswith("?"):
            return False
        key = self.by_name.get(text)
        if key is None:
            return False
        decl = self.decls[key]
        if decl.kind != "alias" or decl.alias is None:
            return False
        if decl.alias.kind == "function":
            return True
        if decl.alias.kind == "ref":
            return self.is_function_like(decl.alias.name, depth + 1)
        if decl.alias.kind == "union":
            return all(self.is_function_like(self.describe(i), depth + 1) for i in decl.alias.items)
        return False

    def jsany(self) -> str:
        return self.imp("kotlin.js.JsAny")

    def where(self) -> str:
        if self.owner and self.member:
            return "%s.%s" % (self.owner, self.member)
        return self.owner or "?"

    # -- canonical forms -----------------------------------------------------------------
    def human(self, expr) -> str:
        """Type expression spelled the way upstream's `.d.ts` spells it (for KDoc, not keys)."""
        k = expr.kind
        if k == "ref":
            args = ", ".join(self.human(a) for a in expr.args)
            return expr.name + ("<%s>" % args if args else "")
        if k == "literal":
            return expr.value[1:-1] if expr.value[:1] in "'\"" else expr.value
        if k == "union":
            return " | ".join(self.human(i) for i in expr.items)
        if k == "intersection":
            return " & ".join(self.human(i) for i in expr.items)
        if k == "array":
            return self.human(expr.items[0]) + "[]"
        if k == "object":
            return "{ … }"
        if k == "function":
            return "(…) => …"
        return expr.raw or k

    def canon(self, expr) -> str:
        k = expr.kind
        if k == "ref":
            args = ",".join(self.canon(a) for a in expr.args)
            return "ref:" + expr.name + ("<" + args + ">" if args else "")
        if k == "literal":
            return "lit:" + expr.value
        if k == "union":
            return "union(" + "|".join(sorted(self.canon(i) for i in expr.items)) + ")"
        if k == "intersection":
            return "inter(" + "&".join(sorted(self.canon(i) for i in expr.items)) + ")"
        if k == "array":
            return "array<" + self.canon(expr.items[0]) + ">"
        if k == "object":
            parts = []
            for m in expr.members:
                part = m.kind + ":" + m.name + ("?" if m.optional else "")
                if m.type is not None:
                    part += ":" + self.canon(m.type)
                if m.params:
                    part += "(" + ",".join(
                        (p.name or "") + ":" + (self.canon(p.type) if p.type else "any")
                        for p in m.params
                    ) + ")"
                parts.append(part)
            return "object{" + ";".join(parts) + "}"
        if k == "function":
            params = ",".join(
                ("." if p.variadic else "")
                + (p.name or "")
                + ":"
                + (self.canon(p.type) if p.type else "any")
                for p in expr.params
            )
            ret = self.canon(expr.returns) if expr.returns else "void"
            return "fn(" + params + ")->" + ret
        if k in ("indexed", "keyof", "typeof", "readonly"):
            return k + "(" + ",".join(self.canon(i) for i in expr.items) + ")"
        if k == "tuple":
            return "tuple(" + ",".join(self.canon(i) for i in expr.items) + ")"
        if k == "import":
            return "import:" + expr.name + "." + expr.value
        return k + ":" + (expr.name or "")

    # -- rendering -----------------------------------------------------------------------
    def split_null(self, expr) -> tuple[list, bool]:
        items = expr.items if expr.kind == "union" else [expr]
        real = []
        nullable = False
        for item in items:
            if item.kind == "ref" and item.name in ("null", "undefined") and not item.args:
                nullable = True
                continue
            if item.kind == "union":
                sub, sub_null = self.split_null(item)
                real.extend(sub)
                nullable = nullable or sub_null
                continue
            real.append(item)
        return real, nullable

    def resolve_key(self, expr):
        if expr is None:
            return None
        if expr.kind == "import":
            return self.by_name.get(expr.value)
        if expr.kind != "ref":
            return None
        if expr.name in self.bound:
            return None
        return self.by_name.get(expr.name)

    def render(self, expr) -> str:
        text, nullable = self.render_nullable(expr)
        if nullable and text not in ("Unit", "Nothing") and not text.endswith("?"):
            return text + "?"
        return text

    def render_nullable(self, expr) -> tuple[str, bool]:
        if expr is None:
            return self.jsany(), False
        k = expr.kind
        if k == "union":
            items, nullable = self.split_null(expr)
            if not items:
                return self.jsany(), True
            if len(items) == 1:
                return self.render_nullable(items[0])[0], nullable
            return self.render_union(items), nullable
        if k == "intersection":
            return self.render_intersection(expr), False
        if k == "literal":
            return self.render_literal_value(expr), False
        if k == "array":
            element = self.render(expr.items[0]) if expr.items else self.jsany()
            return "Array<%s>" % element, False
        if k == "readonly":
            return self.render_nullable(expr.items[0])[0], False
        if k == "ref":
            return self.render_ref(expr), False
        if k == "import":
            key = self.by_name.get(expr.value)
            if key is not None:
                return key[1], False
            self.fallback("unresolved", self.where(), expr.raw or expr.value)
            return self.jsany(), False
        if k == "object":
            return self.inline_object(expr), False
        if k == "function":
            return self.render_function_type(expr), False
        if k == "tuple":
            return self.tuple_type(expr), False
        if k == "keyof":
            return self.render_keyof(expr), False
        if k == "typeof":
            key = self.resolve_key(expr.items[0]) if expr.items else None
            if key is not None:
                decl = self.decls.get(key)
                if decl is not None and decl.kind == "const" and decl.const_type is not None:
                    return self.render_nullable(decl.const_type)[0], False
            self.fallback("typeof", self.where(), self.canon(expr))
            return self.jsany(), False
        if k == "indexed":
            return self.render_indexed(expr), False
        if k == "raw":
            self.fallback("raw", self.where(), expr.name)
            return self.jsany(), False
        self.fallback("kind-" + k, self.where(), self.canon(expr))
        return self.jsany(), False

    def render_ref(self, expr) -> str:
        name = expr.name
        if name in self.bound:
            return self.jsany()
        if name in PRIMITIVES:
            if name in ("null", "undefined"):
                return self.jsany()
            return PRIMITIVES[name]
        if name == "Uint8Array":
            # `js.typedarrays.Uint8Array` is generic over its buffer in Kotlin/JS.
            self.imp("js.buffer.ArrayBuffer")
            return "%s<ArrayBuffer>" % self.imp("js.typedarrays.Uint8Array")
        if name in CONTAINERS:
            return self.render_container(expr)
        if name in UTILITY_PASSTHROUGH:
            if expr.args and expr.args[0].kind != "raw":
                return self.render(expr.args[0])
            return self.jsany()
        if name in ("Omit", "Pick"):
            if expr.args and expr.args[0].kind != "raw":
                self.fallback("utility", self.where(), "%s<%s>" % (name, self.canon(expr)))
                return self.render(expr.args[0])
            return self.jsany()
        if name in UTILITY_OPAQUE:
            self.fallback("utility", self.where(), "%s<%s>" % (name, self.canon(expr)))
            return self.jsany()
        if name in STRING_TYPES:
            return "String"
        if name == "Function":
            # A bare `Function` in upstream's declarations: `kotlin.Function` needs its type
            # argument, and `Function<*>` accepts every callable shape.
            return "Function<*>"
        key = self.by_name.get(name)
        if key is not None:
            return self.kname(key)
        if name in EXTERNALS:
            return self.imp(EXTERNALS[name])
        self.fallback("unresolved", self.where(), name)
        return self.jsany()

    def render_container(self, expr) -> str:
        kotlin, arity = CONTAINERS[expr.name]
        if not expr.args:
            return self.jsany()
        if kotlin == "Record":
            self.imp("js.objects.Record")
            value = self.render(expr.args[1]) if len(expr.args) > 1 else self.jsany()
            return "Record<String, %s>" % value
        if arity == 2:
            self.imp("js.collections." + kotlin)
            first = self.render(expr.args[0])
            second = self.render(expr.args[1]) if len(expr.args) > 1 else self.jsany()
            return "%s<%s, %s>" % (kotlin, first, second)
        if kotlin == "Promise":
            self.imp("kotlin.js.Promise")
        elif kotlin in ("JsSet", "JsMap"):
            self.imp("js.collections." + kotlin)
        elif kotlin in ("WeakSet", "WeakMap"):
            self.imp("js.collections." + kotlin)
        text, nullable = self.render_nullable(expr.args[0])
        if nullable and text != "Unit" and not text.endswith("?"):
            text += "?"
        return "%s<%s>" % (kotlin, text)

    def render_function_type(self, expr) -> str:
        params = []
        for param in expr.params:
            text = self.render(param.type) if param.type is not None else self.jsany()
            if param.variadic:
                text = "Array<%s>" % text
            params.append(text)
        ret = self.render(expr.returns) if expr.returns is not None else "Unit"
        if not params:
            return "() -> " + ret
        return "(%s) -> %s" % (", ".join(params), ret)

    def render_literal_value(self, expr) -> str:
        value = expr.value
        if value in ("true", "false"):
            return "Boolean"
        if value[:1] in "'\"":
            return "String"
        return "Double"

    # -- unions ---------------------------------------------------------------------------
    def render_union(self, items) -> str:
        kinds = {i.kind for i in items}
        if kinds <= {"literal"}:
            return self.literal_union(items)
        return self.opaque_union(items)

    def literal_union(self, items) -> str:
        key = "literal|" + "|".join(sorted(self.canon(i) for i in items))
        existing = self.synth.get(key)
        if existing is not None:
            return existing.name
        values = [i.value for i in items]
        strings = [v for v in values if v[:1] in "'\""]
        others = [v for v in values if v[:1] not in "'\""]
        if others and not strings:
            return "Boolean" if all(v in ("true", "false") for v in others) else "Double"
        if not strings:
            return self.jsany()
        if len(strings) <= 4:
            base = "Or".join(pascal(v[1:-1]) or "Empty" for v in strings)
        else:
            base = self.owner_member_base()
        name = self.unique_type_name(base)
        synth = Synth(
            kind="literal",
            name=name,
            doc="上游字符串字面量联合：%s%s。"
            % (
                "、".join("`%s`" % v[1:-1] for v in strings[:10]),
                " 等 %d 个取值" % len(strings) if len(strings) > 10 else "",
            ),
        )
        synth.body = [
            "sealed external interface %s" % name,
            "",
            "inline fun %s(value: String): %s = value.unsafeCast<%s>()" % (name, name, name),
            "",
            "object %ss {" % name,
        ]
        seen = set()
        for value in strings:
            literal = value[1:-1]
            prop = kotlin_ident(literal)
            if prop in seen:
                continue
            seen.add(prop)
            kotlin_literal = '"%s"' % literal.replace("\\", "\\\\").replace('"', '\\"')
            synth.body.append("    inline val %s: %s get() = %s(%s)" % (prop, name, name, kotlin_literal))
        synth.body.append("}")
        self.register(synth, key)
        return name

    def opaque_union(self, items) -> str:
        key = "union|" + "|".join(sorted(self.canon(i) for i in items))
        existing = self.synth.get(key)
        if existing is not None:
            return existing.name
        rendered = []
        keys = []
        for item in items:
            text, nullable = self.render_nullable(item)
            if nullable and text != "Unit" and not text.endswith("?"):
                text += "?"
            rendered.append(text)
            keys.append(self.overload_key(text, item))
        jsany = self.jsany()
        if any(key == "opaque" for key in keys) or any(t.rstrip("?") == jsany for t in rendered):
            return jsany
        if len(rendered) <= 3:
            base = "Or".join(self.name_hint(t) for t in rendered)
        else:
            base = self.owner_member_base()
        name = self.unique_type_name(base)
        synth = Synth(
            kind="union",
            name=name,
            doc="上游联合类型：%s。" % " | ".join("`%s`" % self.describe(i) for i in items[:8]),
        )
        synth.body = ["external interface %s" % name, ""]
        seen = set()
        for text, key in zip(rendered, keys):
            if key in seen:
                continue
            seen.add(key)
            noinline = "noinline " if self.is_function_like(text) else ""
            synth.body.append(
                "inline fun %s(%svalue: %s): %s = value.unsafeCast<%s>()"
                % (name, noinline, text, name, name)
            )
        self.imp("kotlin.js.unsafeCast")
        self.register(synth, key)
        return name

    def name_hint(self, text: str) -> str:
        text = text.replace("?", "").replace("Array<", "Array")
        for prefix in ("web.html.", "web.dom.", "web.events.", "kotlin.js.", "js.objects.", "js.collections."):
            text = text.replace(prefix, "")
        return pascal(text) or "Value"

    def describe(self, expr) -> str:
        if expr.kind == "literal":
            return expr.value[1:-1] if expr.value[:1] in "'\"" else expr.value
        if expr.kind == "ref":
            return expr.name
        if expr.kind == "object":
            return "{ … }"
        if expr.kind == "function":
            return "(…) => …"
        return self.canon(expr)

    def owner_member_base(self) -> str:
        if self.owner.startswith("AG_GRID_LOCALE_"):
            # Every locale export repeats the same key set; one shared shape keeps the output small.
            return "LocaleStrings"
        if self.owner and self.member:
            return pascal(self.owner + " " + self.member)
        if self.owner:
            return pascal(self.owner)
        return "Union"

    def unique_type_name(self, base: str) -> str:
        base = re.sub(r"\W", "", base) or "Union"
        if not base[:1].isalpha():
            base = "T" + base
        candidate = base
        counter = 2
        while candidate in self.type_names:
            candidate = "%s%d" % (base, counter)
            counter += 1
        self.type_names.add(candidate)
        return candidate

    def register(self, synth: Synth, key: str) -> None:
        self.synth[key] = synth
        self.synth_order.append(synth)

    # -- inline objects, tuples, keyof, indexed, intersections ---------------------------
    def inline_object(self, expr) -> str:
        key = "object|" + self.canon(expr)
        existing = self.synth.get(key)
        if existing is not None:
            return existing.name
        name = self.unique_type_name(self.owner_member_base() + (
            "" if self.owner.startswith("AG_GRID_LOCALE_") else "Options"
        ))
        synth = Synth(
            kind="object",
            name=name,
            doc="上游内联对象类型（`%s`）。" % self.where(),
        )
        local_bound = list(self.bound)
        synth.body = ["external interface %s {" % name]
        synth.body.extend(self.member_lines(expr.members, indent="    "))
        synth.body.append("}")
        if local_bound != self.bound:
            self.bound = local_bound
        self.register(synth, key)
        return name

    def tuple_type(self, expr) -> str:
        key = "tuple|" + self.canon(expr)
        existing = self.synth.get(key)
        if existing is not None:
            return existing.name
        name = self.unique_type_name(self.owner_member_base() + "Tuple")
        synth = Synth(kind="tuple", name=name, doc="上游元组类型（真数组）。")
        synth.body = ["external interface %s" % name, ""]
        params = []
        values = []
        for index, item in enumerate(expr.items):
            text = self.render(item)
            params.append("value%d: %s" % (index, text))
            values.append("value%d" % index)
        synth.body.append(
            "inline fun %s(%s): %s = arrayOf<JsAny>(%s).unsafeCast<%s>()"
            % (name, ", ".join(params), name, ", ".join(values), name)
        )
        self.imp("kotlin.js.unsafeCast")
        self.register(synth, key)
        return name

    def render_keyof(self, expr) -> str:
        operand = expr.items[0] if expr.items else None
        key = self.resolve_key(operand)
        if key is None:
            return "String"
        names = [name for name, _member in self.flatten_members(key) if _IDENTIFIER.match(name)]
        if not names or len(names) > 40:
            return "String"
        literals = [self.gen.TypeExpr("literal", value='"%s"' % name) for name in names]
        return self.literal_union(literals)

    def is_empty_extension(self, expr) -> bool:
        """`CustomColumnDefineMap[keyof CustomColumnDefineMap]` where the map is an empty interface.

        Upstream leaves these as extension points (a user augments the interface); an empty indexed
        access contributes nothing to a union, so dropping the branch keeps the remaining members
        instead of collapsing the whole union to `JsAny`.
        """
        if expr.kind != "indexed" or len(expr.items) < 1:
            return False
        base = expr.items[0]
        if base.kind != "ref":
            return False
        key = self.by_name.get(base.name)
        if key is None:
            return False
        decl = self.decls.get(key)
        return decl is not None and decl.kind == "interface" and not decl.members

    def render_indexed(self, expr) -> str:
        if len(expr.items) < 2:
            return self.jsany()
        key = self.resolve_key(expr.items[0])
        index = expr.items[1]
        if key is not None and index.kind == "literal":
            wanted = index.value[1:-1] if index.value[:1] in "'\"" else index.value
            for name, member in self.flatten_members(key):
                if name == wanted:
                    return self.render(member.type) if member.type is not None else self.jsany()
        self.fallback("indexed", self.where(), self.canon(expr))
        return self.jsany()

    def render_intersection(self, expr) -> str:
        refs = [i for i in expr.items if self.resolve_key(i) is not None]
        objects = [i for i in expr.items if i.kind == "object"]
        if len(refs) == 1 and objects:
            return self.hoist_intersection(self.resolve_key(refs[0]), objects)
        if len(refs) == 1:
            return self.render(refs[0])
        self.fallback("intersection", self.where(), self.canon(expr))
        return self.jsany()

    def hoist_intersection(self, base_key, objects, name: str = "") -> str:
        key = "inter|" + base_key[1] + "|" + "|".join(self.canon(o) for o in objects)
        if not name:
            existing = self.synth.get(key)
            if existing is not None:
                return existing.name
        else:
            self.type_names.add(name)
        if not name:
            name = self.unique_type_name(self.owner_member_base() + "Merged")
        synth = Synth(kind="object", name=name, doc="上游 `%s & { … }`。" % base_key[1])
        synth.body = self.intersection_body(base_key, objects, name)
        self.register(synth, key)
        return name

    def intersection_body(self, base_key, objects, name) -> list[str]:
        """`Base & { … }`: inherit the base and declare only what the object literal adds."""
        base_flat = dict(self.flatten_members(base_key))
        own = []
        for obj in objects:
            for member in obj.members:
                if not self.emittable(member):
                    continue
                inherited = base_flat.get(member.name)
                if inherited is not None:
                    if self.canonical_member(inherited) == self.canonical_member(member):
                        continue
                    own.append(self.as_typed_member(member))
                    continue
                own.append(member)
        lines = ["external interface %s : %s {" % (name, base_key[1])]
        lines.extend(self.member_lines(own, indent="    "))
        lines.append("}")
        return lines

    # -- members --------------------------------------------------------------------------
    def flatten_members(self, key, seen=None) -> list[tuple[str, object]]:
        if key in self.flatten_cache:
            return self.flatten_cache[key]
        if seen is None:
            seen = set()
        if key in seen:
            return []
        seen.add(key)
        decl = self.decls.get(key)
        if decl is None:
            return []
        result: list[tuple[str, object]] = []
        for heritage in decl.heritage:
            base_key = self.resolve_heritage(heritage)
            if base_key is None or base_key not in self.decls:
                continue
            for name, member in self.flatten_members(base_key, seen):
                result = [(n, m) for n, m in result if n != name]
                result.append((name, member))
        for member in decl.members:
            if not self.emittable(member):
                continue
            result = [(n, m) for n, m in result if n != member.name]
            result.append((member.name, member))
        self.flatten_cache[key] = result
        return result

    def emittable(self, member) -> bool:
        if member.private or member.static:
            return False
        if member.kind in ("index", "call", "construct"):
            return False
        return True

    def resolve_heritage(self, text: str):
        name = text.split("<", 1)[0].strip()
        return self.by_name.get(name)

    def member_lines(self, members, indent="    ") -> list[str]:
        lines: list[str] = []
        seen = set()
        for member in members:
            if not self.emittable(member):
                continue
            if member.name in seen and not getattr(member, "js_name", None):
                continue
            seen.add(member.name)
            self.member = member.name
            previous_bound = self.bound
            self.bound = previous_bound + list(member.type_params)
            try:
                lines.extend(self.emit_member(member, indent))
            finally:
                self.bound = previous_bound
        self.member = ""
        return lines

    def emit_member(self, member, indent="    ", override=False, rename=None) -> list[str]:
        lines: list[str] = []
        js_name = getattr(member, "js_name", None)
        name = kotlin_ident(member.name)
        if rename:
            # Upstream redeclares an inherited member with a different shape (a method in the base
            # class, a function-typed property in the subclass). Kotlin cannot override across that
            # difference, so the JavaScript name is kept through `@JsName`.
            js_name = js_name or member.name
            name = rename
        if name in ANY_MEMBERS:
            # `Any` already declares these, and an external member cannot override it: keep the
            # JavaScript name through `@JsName` and expose it under a distinct Kotlin name.
            js_name = js_name or member.name
            name = "typed" + pascal(member.name)
        if re.fullmatch(r"_+", member.name or ""):
            # `_`, `__`, … are reserved in Kotlin; the upstream property keeps its spelling through
            # `@JsName` (placeholders in destructured event arguments).
            js_name = js_name or member.name
            name = "typedUnderscore%d" % len(member.name)
        if js_name:
            self.imp("kotlin.js.JsName")
            lines.append('%s@JsName("%s")' % (indent, js_name))
        if member.doc:
            lines.append(indent_doc(member.doc, indent))
        prefix = "override " if override else ""
        if member.kind == "method":
            params = self.render_params(member.params)
            ret = self.render(member.type) if member.type is not None else "Unit"
            signature = "%sfun %s(%s)" % (prefix, name, params)
            if ret != "Unit":
                signature += ": %s" % ret
            lines.append(indent + signature)
            return lines
        text = self.render(member.type) if member.type is not None else self.jsany()
        if member.optional and text != "Unit" and not text.endswith("?"):
            text += "?"
        keyword = "val" if member.readonly else "var"
        lines.append(indent + "%s%s %s: %s" % (prefix, keyword, name, text))
        return lines

    def render_params(self, params) -> str:
        out = []
        used = set()
        for index, param in enumerate(params):
            name = param.name or "arg%d" % (index + 1)
            if name == "this":
                name = "self"
            name = kotlin_ident(name)
            if name in used:
                name = "%s%d" % (name, index + 1)
            used.add(name)
            text = self.render(param.type) if param.type is not None else self.jsany()
            if param.variadic:
                text = "Array<%s>" % text
            if param.optional and text != "Unit" and not text.endswith("?"):
                text += "?"
            out.append("%s: %s" % (name, text))
        return ", ".join(out)

    # -- declarations ---------------------------------------------------------------------
    def emit_decl(self, key) -> list[str]:
        decl = self.decls[key]
        name = self.kname(key)
        self.owner = name
        self.member = ""
        previous_bound = self.bound
        self.bound = list(decl.type_params)
        try:
            if decl.kind == "interface":
                lines = self.emit_interface(decl, key)
            elif decl.kind == "class":
                lines = self.emit_class(decl, key)
            elif decl.kind == "alias":
                lines = self.emit_alias(decl, key)
            elif decl.kind == "enum":
                lines = self.emit_enum(decl, key)
            elif decl.kind == "const":
                lines = self.emit_const(decl, key)
            elif decl.kind == "function":
                lines = self.emit_function(decl, key)
            else:
                self.fallback("decl-" + decl.kind, name, decl.raw[:100])
                lines = []
            for line in lines:
                if line.startswith("typealias %s = " % name):
                    # Kotlin type aliases are transparent, so a union branch naming one is really
                    # the target type; remember it to spot colliding factory overloads.
                    self.plain_aliases[name] = line.split(" = ", 1)[1].strip()
            return lines
        finally:
            self.bound = previous_bound
            self.owner = ""

    def doc_lines(self, decl, extra: str = "") -> list[str]:
        text = decl.doc or ""
        extra_text = extra
        if not text and not extra_text:
            return []
        joined = text + ("\n\n" + extra_text if extra_text else "")
        return indent_doc(joined, "").splitlines()

    def emit_interface(self, decl, key) -> list[str]:
        name = self.kname(key)
        base = self.safe_base(decl, key)
        flat = self.flatten_members(key)
        own = {m.name: m for m in decl.members if self.emittable(m)}
        base_flat = dict(self.flatten_members(base)) if base is not None else {}
        extra = "继承上游 `%s`。" % self.kname(base) if base is not None else ""
        lines = self.doc_lines(decl, extra)
        head = "external interface %s" % name
        if base is not None:
            head += " : %s" % self.kname(base)
        lines.append(head + " {")
        to_emit = []
        for name, member in flat:
            base_member = base_flat.get(name)
            if base_member is not None:
                if self.canonical_member(base_member) == self.canonical_member(member):
                    continue
                if name in own:
                    to_emit.append(self.as_typed_member(own[name]))
                continue
            to_emit.append(member)
        lines.extend(self.member_lines(to_emit))
        lines.append("}")
        return lines

    def safe_base(self, decl, key):
        for heritage in decl.heritage:
            base_key = self.resolve_heritage(heritage)
            if base_key is None or base_key not in self.decls:
                continue
            base = self.decls[base_key]
            if base.kind != "interface":
                continue
            merged = dict(self.flatten_members(key))
            base_flat = dict(self.flatten_members(base_key))
            if all(
                name in merged and self.canonical_member(merged[name]) == self.canonical_member(member)
                for name, member in base_flat.items()
            ):
                return base_key
        return None

    def as_typed_member(self, member):
        copy = self.gen.Member(
            kind=member.kind,
            name="typed" + member.name[:1].upper() + member.name[1:],
            optional=member.optional,
            readonly=member.readonly,
            type=member.type,
            params=member.params,
            type_params=member.type_params,
            doc="与 `%s` 是同一个 JS 属性（`@JsName`），这里给出更精确的类型。"
            % member.name
            + (" " + member.doc if member.doc else ""),
            raw=member.raw,
        )
        copy.js_name = member.name
        return copy

    def canonical_member(self, member) -> str:
        text = self.canon(member.type) if member.type is not None else "any"
        if member.kind == "method":
            text += "(" + ",".join(
                self.canon(p.type) if p.type is not None else "any" for p in member.params
            ) + ")"
        return member.kind + ":" + text

    def same_signature(self, left, right) -> bool:
        """Whether two upstream methods map to the same Kotlin signature."""
        if len(left.params) != len(right.params):
            return False
        for a, b in zip(left.params, right.params):
            ta = self.render(a.type) if a.type is not None else self.jsany()
            tb = self.render(b.type) if b.type is not None else self.jsany()
            if ta.rstrip("?") != tb.rstrip("?"):
                return False
        ra = self.render(left.type) if left.type is not None else "Unit"
        rb = self.render(right.type) if right.type is not None else "Unit"
        return ra == rb

    def emit_class(self, decl, key) -> list[str]:
        name = self.kname(key)
        lines = self.doc_lines(decl)
        if name != decl.name:
            # The public alias is exposed under a shorter Kotlin name (`ListTableAll` -> `ListTable`),
            # but the JavaScript export keeps its upstream spelling.
            lines.append('@JsName("%s")' % decl.name)
        # Kotlin/JS external classes cannot implement interfaces, so an `implements X` clause is
        # folded in: the interface's members are declared on the class itself, which is exactly the
        # shape upstream's class body already has.
        base = None
        interfaces: list[tuple[str, tuple[str, str]]] = []
        for heritage in decl.heritage:
            text = heritage.split("<", 1)[0].strip()
            heritage_key = self.by_name.get(text)
            if heritage_key is None or heritage_key not in self.decls:
                continue
            if self.decls[heritage_key].kind == "class":
                if base is None:
                    base = heritage_key
            else:
                interfaces.append((text, heritage_key))
        # External classes are final by default; upstream subclasses its own classes, and the
        # wrapper has to keep them extensible.
        head = "open external class %s" % name
        if base is not None:
            head += " : %s" % self.kname(base)
        lines.append(head + " {")
        statics = []
        seen_names: set[str] = set()
        constructors = 0
        base_members = dict(self.flatten_members(base)) if base is not None else {}
        base_types = {n: m for n, m in base_members.items()}
        for member in decl.members:
            if member.static:
                if not member.private:
                    statics.append(member)
                continue
            if member.private:
                continue
            if member.kind == "construct" or (
                member.kind == "method" and member.name == "constructor"
            ):
                lines.append("    constructor(%s)" % self.render_params(member.params))
                constructors += 1
                continue
            if member.kind in ("index", "call"):
                self.fallback("member-" + member.kind, name + "." + member.name, member.raw[:100])
                continue
            if member.name == "constructor":
                continue
            seen_names.add(member.name)
            self.member = member.name
            previous_bound = self.bound
            self.bound = previous_bound + list(member.type_params)
            override = False
            rename = None
            base_member = base_types.get(member.name)
            if base_member is not None:
                if member.kind == "method" and base_member.kind == "method":
                    if self.same_signature(member, base_member):
                        # The base class already declares exactly this method; an external member
                        # cannot be `open`, so restating it would be an illegal override.
                        seen_names.add(member.name)
                        self.member = ""
                        continue
                    rename = "typed" + pascal(member.name)
                elif member.kind == "property" and base_member.kind == "property":
                    own_type = self.render(member.type) if member.type is not None else self.jsany()
                    base_type = (
                        self.render(base_member.type) if base_member.type is not None else self.jsany()
                    )
                    if own_type == base_type:
                        seen_names.add(member.name)
                        self.member = ""
                        continue
                    rename = "typed" + pascal(member.name)
                else:
                    rename = "typed" + pascal(member.name)
            try:
                lines.extend(self.emit_member(member, "    ", override=override, rename=rename))
            finally:
                self.bound = previous_bound
            self.member = ""
        # Members only the implemented interface declares (upstream relies on the interface, the
        # class body does not repeat them).
        for _text, iface_key in interfaces:
            for member_name, member in self.flatten_members(iface_key):
                if member_name in seen_names or member_name in base_types:
                    # The base class already declares this member; re-declaring it from the
                    # implemented interface is what makes Kotlin report "hides member of supertype".
                    continue
                seen_names.add(member_name)
                self.member = member.name
                previous_bound = self.bound
                self.bound = previous_bound + list(member.type_params)
                try:
                    lines.extend(self.emit_member(member, "    "))
                finally:
                    self.bound = previous_bound
                self.member = ""
        lines.append("}")
        if not constructors:
            # A subclass that does not redeclare a constructor inherits the upstream one
            # (`ListTableAll extends ListTable`); Kotlin still needs an explicit constructor to be
            # able to call it.
            for params in self.inherited_constructors(base):
                lines.insert(len(lines) - 1, "    constructor(%s)" % params)
        if statics:
            lines.extend(self.emit_statics(decl, statics, name))
        return lines

    def inherited_constructors(self, base) -> list[str]:
        seen: set[tuple[str, str]] = set()
        found: list[str] = []
        while base is not None and base not in seen:
            seen.add(base)
            decl = self.decls.get(base)
            if decl is None:
                break
            for member in decl.members:
                if member.kind in ("construct", "constructor"):
                    found.append(self.render_params(member.params))
                elif member.kind == "method" and member.name == "constructor":
                    found.append(self.render_params(member.params))
            if found:
                break
            base = self.safe_base(decl, base)
        return found

    def emit_statics(self, decl, statics, class_name: str = "") -> list[str]:
        """Upstream `static` members: the JavaScript class value, exposed as a value of its own.

        An `external class` cannot carry statics (Kotlin has no companion in external classes), so
        the constructor object is bound twice: once as the class, once through a private interface
        that declares the static members, mirroring how kotlin-wrappers models module objects.
        """
        class_name = class_name or decl.name
        iface = class_name + "Statics"
        value = camel(class_name) + "Statics"
        lines = [
            "",
            "/** [%s] 的静态成员；在 JavaScript 里就是构造函数对象本身。 */" % class_name,
            "external interface %s {" % iface,
        ]
        previous_bound = self.bound
        self.bound = list(decl.type_params)
        try:
            for member in statics:
                self.member = member.name
                self.bound = list(decl.type_params) + list(member.type_params)
                lines.extend(self.emit_member(member, "    "))
        finally:
            self.bound = previous_bound
            self.member = ""
        lines.append("}")
        lines.append("")
        self.imp("kotlin.js.JsName")
        lines.append('@JsName("%s")' % decl.name)
        lines.append("external val %s: %s" % (value, iface))
        return lines

    def emit_alias(self, decl, key) -> list[str]:
        name = self.kname(key)
        alias = decl.alias
        if alias is None:
            return []
        if decl.name in STRING_TYPES:
            lines = self.doc_lines(
                decl, "上游是按泛型参数算出的字段路径类型；wrapper 不保留泛型，所有取值都是字符串路径。"
            )
            lines.append("typealias %s = String" % name)
            return lines
        if alias.kind == "object":
            lines = self.doc_lines(decl)
            lines.append("external interface %s {" % name)
            lines.extend(self.member_lines(alias.members))
            lines.append("}")
            return lines
        if alias.kind == "union":
            return self.emit_alias_union(decl, alias, name)
        if alias.kind == "intersection":
            items = alias.items
            refs = [i for i in items if self.resolve_key(i) is not None]
            objects = [i for i in items if i.kind == "object"]
            if len(refs) >= 2 and not objects:
                # `ITextColumnBodyDefine & HeaderDefine`: Kotlin interfaces can extend several
                # supertypes, and both upstream halves are interfaces here.
                self.type_names.add(name)
                lines = self.doc_lines(decl, "上游 `%s`。" % self.human(alias))
                lines.append(
                    "external interface %s : %s" % (name, ", ".join(self.kname(self.resolve_key(r)) for r in refs))
                )
                return lines
            if len(refs) == 1 and objects:
                base_key = self.resolve_key(refs[0])
                self.type_names.add(name)
                lines = self.doc_lines(decl, "上游 `%s & { … }`。" % self.kname(base_key))
                lines.extend(self.intersection_body(base_key, objects, name))
                return lines
            if len(refs) == 1:
                lines = self.doc_lines(decl)
                lines.append("typealias %s = %s" % (name, self.render(refs[0])))
                return lines
            self.fallback("intersection", name, self.canon(alias))
            lines = self.doc_lines(decl)
            lines.append("typealias %s = %s" % (name, self.jsany()))
            return lines
        lines = self.doc_lines(decl)
        target = self.render(alias)
        lines.append("typealias %s = %s" % (name, target))
        return lines

    def emit_alias_union(self, decl, alias, name: str = "") -> list[str]:
        name = name or self.kname((decl.file, decl.name))
        items, nullable = self.split_null(alias)
        items = [i for i in items if not self.is_empty_extension(i)]
        lines = self.doc_lines(decl)
        if not items:
            lines.append("typealias %s = %s" % (name, self.jsany() + "?"))
            return lines
        if len(items) == 1:
            target = self.render(items[0])
            if nullable and not target.endswith("?"):
                target += "?"
            lines.append("typealias %s = %s" % (name, target))
            return lines
        if {i.kind for i in items} <= {"literal"} and not nullable:
            return self.emit_literal_alias(decl, items, lines, name)
        rendered = []
        keys = []
        for item in items:
            text, item_nullable = self.render_nullable(item)
            if item_nullable and text != "Unit" and not text.endswith("?"):
                text += "?"
            rendered.append(text)
            keys.append(self.overload_key(text, item))
        jsany = self.jsany()
        if any(t.rstrip("?") == jsany for t in rendered):
            # A union with an `any`-typed branch cannot be told apart at runtime (type-mapping §3).
            lines.append("typealias %s = %s" % (name, jsany))
            return lines
        distinct = []
        seen = set()
        for text, key in zip(rendered, keys):
            if key in seen:
                # Two branches Kotlin cannot tell apart would collide as overloads: keep the first.
                continue
            seen.add(key)
            distinct.append(text)
        self.type_names.add(name)
        lines.append("external interface %s" % name)
        lines.append("")
        for text in distinct:
            noinline = "noinline " if self.is_function_like(text) else ""
            lines.append(
                "inline fun %s(%svalue: %s): %s = value.unsafeCast<%s>()"
                % (name, noinline, text, name, name)
            )
        self.imp("kotlin.js.unsafeCast")
        if nullable:
            lines.append("")
            lines.append(
                "/** 上游允许 `null`；参数直接传 `null` 即可。 */"
            )
        return lines

    def emit_literal_alias(self, decl, items, lines, name: str = "") -> list[str]:
        name = name or self.kname((decl.file, decl.name))
        values = [i.value for i in items]
        strings = [v for v in values if v[:1] in "'\""]
        if not strings:
            lines.append("typealias %s = Double" % name)
            return lines
        if not decl.doc:
            lines.extend(
                indent_doc(
                    "上游字符串字面量联合：%s。" % "、".join("`%s`" % v[1:-1] for v in strings[:8]),
                    "",
                ).splitlines()
            )
        lines.append("sealed external interface %s" % name)
        lines.append("")
        lines.append(
            "inline fun %s(value: String): %s = value.unsafeCast<%s>()"
            % (name, name, name)
        )
        lines.append("")
        lines.append("object %ss {" % name)
        seen = set()
        for value in strings:
            literal = value[1:-1]
            prop = kotlin_ident(literal)
            if prop in seen:
                continue
            seen.add(prop)
            lines.append(
                "    inline val %s: %s get() = %s(%s)"
                % (prop, name, name, kotlin_string(literal))
            )
        lines.append("}")
        self.imp("kotlin.js.unsafeCast")
        return lines

    def emit_enum(self, decl, key) -> list[str]:
        name = self.kname(key)
        values = [v for v in decl.enum_members if v[0]]
        strings = [raw for _member, raw in values if raw[:1] in "'\""]
        if strings and len(strings) == len(values):
            # VTable's enums are string enums (`'default' = "default"`): they behave like the literal
            # unions the rest of the declarations use, not like numbers.
            lines = self.doc_lines(decl, "上游字符串枚举：`%s(String)` 取值工厂，常量见 `%ss`。" % (name, name))
            lines.append("sealed external interface %s" % name)
            lines.append("")
            lines.append("inline fun %s(value: String): %s = value.unsafeCast<%s>()" % (name, name, name))
            lines.append("")
            lines.append("object %ss {" % name)
            seen = set()
            for member_name, raw in values:
                literal = raw[1:-1]
                prop = kotlin_ident(literal or member_name)
                if prop in seen:
                    continue
                seen.add(prop)
                lines.append(
                    "    inline val %s: %s get() = %s(%s)"
                    % (prop, name, name, kotlin_string(literal))
                )
            lines.append("}")
            self.imp("kotlin.js.unsafeCast")
            return lines
        lines = self.doc_lines(
            decl, "上游数字枚举：值在 JS 侧是 `Double`，常量见 `%ss`。" % name
        )
        lines.append("external interface %s" % name)
        lines.append("")
        lines.append(
            "inline fun %s(value: Double): %s = value.unsafeCast<%s>()"
            % (name, name, name)
        )
        lines.append("")
        lines.append("object %ss {" % name)
        for member_name, raw in values:
            try:
                number = float(raw)
            except ValueError:
                number = float(len(lines))
            lines.append(
                "    inline val %s: %s get() = %s(%s)"
                % (kotlin_ident(member_name), name, name, format_double(number))
            )
        lines.append("}")
        self.imp("kotlin.js.unsafeCast")
        return lines

    def emit_const(self, decl, key) -> list[str]:
        name = self.kname(key)
        text = self.render(decl.const_type) if decl.const_type is not None else self.jsany()
        lines = self.doc_lines(decl)
        js = "" if decl.name == name else '@JsName("%s")\n' % decl.name
        if js:
            self.imp("kotlin.js.JsName")
        if js:
            lines.extend(js.rstrip("\n").splitlines())
        lines.append("external val %s: %s" % (kotlin_ident(name), text))
        return lines

    def emit_function(self, decl, key) -> list[str]:
        name = self.kname(key)
        params = self.render_params(decl.params)
        ret = self.render(decl.returns) if decl.returns is not None else "Unit"
        lines = self.doc_lines(decl)
        if decl.name != name:
            self.imp("kotlin.js.JsName")
            lines.append('@JsName("%s")' % decl.name)
        signature = "external fun %s(%s)" % (kotlin_ident(name), params)
        if ret != "Unit":
            signature += ": %s" % ret
        lines.append(signature)
        return lines

    # -- files ----------------------------------------------------------------------------
    def render_all(self, entries: dict[str, tuple[str, list[tuple[str, str]]]]) -> dict[str, str]:
        """Renders every declaration.

        ``entries`` maps a Kotlin file name to `(npm module, declaration keys)`: the module decides
        the `@file:JsModule` annotation of files that declare values, and `"."` means "no values,
        no module import".
        """
        outputs: dict[str, str] = {}
        # Type aliases first: they are transparent in Kotlin, and the union factories decide
        # whether two branches collide by looking at the alias targets, so those must be known.
        rendered: dict[tuple[str, str], list[str]] = {}
        alias_keys = [key for _f, (_m, keys) in sorted(entries.items()) for _n, key in keys
                      if self.decls[key].kind in ("alias", "enum")]
        rest_keys = [key for _f, (_m, keys) in sorted(entries.items()) for _n, key in keys
                     if self.decls[key].kind not in ("alias", "enum")]
        for key in alias_keys + rest_keys:
            self.owner = ""
            self.member = ""
            rendered[key] = self.emit_decl(key)
        for file_name, (module, keys) in sorted(entries.items()):
            self.imports = set()
            body: list[str] = []
            has_values = False
            local_names = set()
            for name, key in keys:
                decl = self.decls[key]
                if decl.kind in ("const", "function", "class"):
                    has_values = True
                local_names.add(self.kname(key))
                lines = rendered.get(key, [])
                if not lines:
                    continue
                if body:
                    body.append("")
                body.extend(lines)
            if body:
                outputs[file_name] = self.assemble(body, has_values, local_names, module)
        by_bucket: dict[str, list[Synth]] = {}
        for synth in self.synth_order:
            by_bucket.setdefault(SYNTH_FILES.get(synth.kind, "Synthesized.kt"), []).append(synth)
        for bucket, synth_list in sorted(by_bucket.items()):
            self.imports = set()
            body = []
            local_names = {synth.name for synth in synth_list}
            for synth in synth_list:
                if body:
                    body.append("")
                doc = indent_doc(synth.doc, "")
                if doc:
                    body.extend(doc.splitlines())
                body.extend(synth.body)
            outputs[bucket] = self.assemble(body, False, local_names, ".")
        for file_name, body in sorted(self.extra_files.items()):
            self.imports = set()
            local_names = {line.split(" = ")[0].split("(")[0].split(" ")[-1] for line in body if line}
            outputs[file_name] = self.assemble(body, False, local_names, ".")
        return outputs

    def assemble(self, body, has_values, local_names, module) -> str:
        imports: set[str] = set()
        text = "\n".join(body)
        for fqn in sorted(self.imports):
            simple = fqn.rsplit(".", 1)[1]
            if simple in local_names or fqn == simple:
                continue
            imports.add(fqn)
        # Synthesized bodies are rendered before their file exists, so their imports are recovered
        # from the text: every mapped global is looked up once, and a shadowing declaration makes the
        # renderer emit the fully qualified name instead, which the pattern below skips.
        candidates = dict(EXTERNALS)
        candidates.update(
            {
                "JsAny": "kotlin.js.JsAny",
                "JsName": "kotlin.js.JsName",
                "unsafeCast": "kotlin.js.unsafeCast",
                "Record": "js.objects.Record",
                "JsMap": "js.collections.JsMap",
                "JsSet": "js.collections.JsSet",
                "WeakMap": "js.collections.WeakMap",
                "WeakSet": "js.collections.WeakSet",
            }
        )
        for simple, fqn in sorted(candidates.items()):
            if simple in self.type_names or simple in local_names:
                continue
            if "." not in fqn:
                continue
            if re.search(r"(?<![.\w])%s\b" % re.escape(simple), text):
                imports.add(fqn)
        if "unsafeCast<" in text:
            imports.add("kotlin.js.unsafeCast")
        if "@JsName(" in text:
            imports.add("kotlin.js.JsName")
        header = [
            "// Generated by scripts/generate-api.py from %s %s." % (self.upstream, self.version),
            "// Do not edit: re-run the script instead (see docs/development/technical-decisions.md).",
            "",
        ]
        annotations = []
        if has_values and module != ".":
            annotations.append('@file:JsModule("%s")' % module)
        annotations.append('@file:Suppress("unused")')
        lines = header + annotations + ["", "package %s" % KOTLIN_PACKAGE, ""]
        for fqn in sorted(imports):
            lines.append("import %s" % fqn)
        if imports:
            lines.append("")
        lines.extend(body)
        return "\n".join(lines).rstrip() + "\n"


SYNTH_FILES = {
    "union": "Unions.kt",
    "literal": "Literals.kt",
    "object": "InlineObjects.kt",
    "tuple": "Tuples.kt",
}


def indent_doc(text: str, indent: str) -> str:
    text = (text or "").replace("*/", "* /").strip()
    if not text:
        return ""
    wrapped = wrap_text(text, max(40, 100 - len(indent) - 3))
    lines = ["%s/**" % indent]
    for line in wrapped:
        lines.append("%s * %s" % (indent, line.rstrip()))
    lines.append("%s */" % indent)
    return "\n".join(lines)


def wrap_text(text: str, width: int) -> list[str]:
    out: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        current = ""
        for word in words:
            if not current:
                current = word
            elif len(current) + 1 + len(word) <= width:
                current += " " + word
            else:
                out.append(current)
                current = word
        if current:
            out.append(current)
    return out or [""]


def format_double(value: float) -> str:
    if value == int(value):
        return "%d.0" % int(value)
    return repr(value)


def kotlin_file_name(upstream: str) -> str:
    """The Kotlin file for an upstream `.d.ts`.

    Both roots feed the same Kotlin package, so the root prefix is dropped; the remaining path is
    pascal-cased (`ts-types/list-table/layout-map/api.d.ts` -> `TsTypesListTableLayoutMapApi.kt`).
    """
    parts = upstream.split("/")
    if parts and parts[0] in ("vtable", "editors"):
        parts = parts[1:]
    if parts and parts[-1].endswith(".d.ts"):
        parts[-1] = parts[-1][: -len(".d.ts")]
    name = "".join(pascal(part) for part in parts if part)
    return (name or "Main") + ".kt"


def render_public_aliases(renderer, aliases) -> list[str]:
    """Declarations whose npm export name differs from the Kotlin name of the declaration itself.

    `ListTableAll` is exported as `ListTable`, so the Kotlin class is named after the public name
    and the base class keeps a `Base` suffix; anything else renamed (currently `EVENT_TYPE`) gets a
    transparent alias here.
    """
    lines: list[str] = []
    for public_name, kotlin_name, kind, key in aliases:
        decl = renderer.decls.get(key)
        if decl is None:
            continue
        if kind in ("interface", "alias", "class", "enum"):
            lines.append("/** 上游把这同一个类型同时导出为 `%s`。 */" % public_name)
            lines.append("typealias %s = %s" % (_sanitize_name(public_name), kotlin_name))
            lines.append("")
            continue
        if kind == "const":
            text = renderer.render(decl.const_type) if decl.const_type is not None else renderer.jsany()
            lines.append("/** 上游把同一个导出也命名为 `%s`。 */" % public_name)
            lines.append("val %s: %s get() = %s" % (_sanitize_name(public_name), text, kotlin_name))
            lines.append("")
            continue
        if kind == "function":
            params = renderer.render_params(decl.params)
            ret = renderer.render(decl.returns) if decl.returns is not None else "Unit"
            names = ", ".join(p.name or "arg%d" % (i + 1) for i, p in enumerate(decl.params))
            signature = "fun %s(%s)" % (_sanitize_name(public_name), params)
            if ret != "Unit":
                signature += ": %s" % ret
            lines.append("/** 上游把同一个导出也命名为 `%s`。 */" % public_name)
            lines.append("%s = %s(%s)" % (signature, kotlin_name, names))
            lines.append("")
    return lines


def _sanitize_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not cleaned or not (cleaned[0].isalpha() or cleaned[0] == "_"):
        cleaned = "_" + cleaned
    return cleaned
