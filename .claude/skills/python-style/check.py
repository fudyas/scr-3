import argparse
import ast
import io
import sys
import tokenize
from abc import ABC
from pathlib import Path
from typing import List, NamedTuple, Optional, Set


class Finding(NamedTuple):
    """A single style violation located at a file and line."""

    path: str
    line: int
    rule: str
    message: str


class PythonStyleChecker:
    """Checks one Python module against the the project style rules that can be decided mechanically."""

    # Builtin generics that must be spelled with their typing-module form
    TYPING_NAMES = {
        "list": "List",
        "dict": "Dict",
        "tuple": "Tuple",
        "set": "Set",
        "frozenset": "FrozenSet",
        "type": "Type",
    }
    # Module-level accessors allowed to stay bare functions (the singleton exception)
    SINGLETON_ACCESSORS = {"get_logger", "set_logger"}
    # Comment prefixes that are tooling pragmas, not prose, and so escape the inline rule
    COMMENT_PRAGMAS = ("type:", "noqa", "pragma", "pylint:", "mypy:", "isort:", "fmt:")
    # Characters that, alone, make a comment a divider/banner
    DIVIDER_CHARS = set("-=*_~")
    # Base-form (imperative) verbs that wrongly open a docstring purpose line or a comment; the
    # conventions require the third-person singular present ("Reads", not "Read"). Third-person
    # forms end in "s" and never match these, so noun openers (The/A/Whether/One) stay safe.
    IMPERATIVE_VERBS = {
        "read", "write", "create", "build", "make", "add", "remove", "insert", "update",
        "delete", "apply", "resolve", "reassign", "publish", "restore", "suspend", "flatten",
        "classify", "confirm", "return", "mint", "open", "close", "dispose", "initialize",
        "init", "bind", "seed", "validate", "reject", "walk", "compute", "collect", "keep",
        "carry", "enforce", "load", "serve", "route", "anchor", "inject", "register", "parse",
        "render", "fold", "split", "echo", "check", "run", "pin", "move", "drop", "skip",
        "hold", "track", "emit", "raise", "store", "fetch", "send", "wrap", "hand", "span",
        "reset", "flush", "dispatch", "handle", "adapt", "expose", "provide", "configure",
        "wire", "generate", "produce", "convert", "normalize", "persist", "lock", "allocate",
        "unlink", "mark", "gather", "ensure", "assign", "transfer", "append", "prepend",
        "count", "sort", "filter", "find", "locate", "select", "pick", "choose", "format",
        "get", "put", "set", "project", "record", "advance", "derive", "decide", "detect",
        "scope", "surface", "materialize", "tombstone", "front", "serialize", "join", "leave",
        "compose", "populate", "attach", "detach", "merge", "link", "finalize", "commit",
        "abort", "reconcile", "transform", "expand", "toggle", "swap", "cache", "snapshot",
        "adapt", "amortize", "orchestrate", "wrap", "unwrap", "translate", "aggregate", "yield",
        "revert", "navigate", "rollback", "retry", "dump", "raise", "halt", "abort", "spawn",
        "assemble", "retire",
    }

    def __init__(self, path: Path, source: str) -> None:
        """Stores the file path and its source for the upcoming checks."""
        self._path = path
        self._source = source
        self._findings: List[Finding] = []

    def check(self) -> List[Finding]:
        """Runs every mechanical check and returns the findings for this module.

        Returns:
            One Finding per detected violation, in discovery order.
        """
        # Parsing failure is itself a reportable finding, not a crash
        try:
            tree = ast.parse(self._source)
        except SyntaxError as error:
            self._add(error.lineno or 1, "SYNTAX", f"file does not parse: {error.msg}")
            return self._findings
        self._check_module_docstring(tree)
        self._check_module_functions(tree)
        self._check_imports(tree)
        self._check_signatures(tree)
        self._check_return_tuples(tree)
        self._check_hints(tree)
        self._check_docstrings(tree)
        self._check_imperative_mood(tree)
        self._check_annotations(tree)
        self._check_percent_format(tree)
        self._check_comments()
        return self._findings

    def _add(self, line: int, rule: str, message: str) -> None:
        """Records one finding against this module."""
        self._findings.append(Finding(str(self._path), line, rule, message))

    def _check_module_docstring(self, tree: ast.Module) -> None:
        """Flags a module-level docstring, which the conventions forbid."""
        if ast.get_docstring(tree) is not None:
            self._add(1, "MODULE_DOCSTRING", "module-level docstring is not allowed")

    def _check_module_functions(self, tree: ast.Module) -> None:
        """Flags bare module-level functions outside the singleton-accessor exception."""
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name not in self.SINGLETON_ACCESSORS:
                    self._add(
                        node.lineno,
                        "MODULE_FUNCTION",
                        f"module-level function '{node.name}' — group as a @staticmethod on a XxxHelper(ABC)",
                    )

    def _check_imports(self, tree: ast.Module) -> None:
        """Flags imports that sit after code or inside a function, class, or non-TYPE_CHECKING block.

        Steps:
            1. Walk the module body, collecting the imports that are legitimately at the top.
            2. Flag a top-level import that follows the first real statement.
            3. Treat imports under a top `if TYPE_CHECKING:` block as allowed.
            4. Flag every remaining import found anywhere else in the tree.
        """
        allowed: Set[ast.AST] = set()
        seen_code = False
        for index, node in enumerate(tree.body):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                allowed.add(node)
                if seen_code:
                    self._add(node.lineno, "IMPORT_NOT_TOP", "import appears after module-level code")
            elif index == 0 and self._is_string_expression(node):
                continue
            elif self._is_type_checking_block(node):
                for inner in node.body:
                    if isinstance(inner, (ast.Import, ast.ImportFrom)):
                        allowed.add(inner)
            else:
                seen_code = True
        # Any import outside the allowed set is an inline import
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and node not in allowed:
                self._add(node.lineno, "INLINE_IMPORT", "import is not at the top of the file")

    def _check_signatures(self, tree: ast.Module) -> None:
        """Flags the bare '*' keyword-only marker in any function signature."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # kwonlyargs with no *args means the author wrote a bare '*'
                if node.args.kwonlyargs and node.args.vararg is None:
                    self._add(
                        node.lineno,
                        "KEYWORD_ONLY_STAR",
                        f"function '{node.name}' uses the bare '*' keyword-only marker",
                    )

    def _check_return_tuples(self, tree: ast.Module) -> None:
        """Flags a return annotation that hands back a fixed-arity tuple of multiple values.

        A function returning ``Tuple[A, B, ...]`` is returning several distinct values at once;
        the conventions require a named immutable class instead. The variadic homogeneous tuple
        ``Tuple[X, ...]`` is a sequence, not multiple values, and stays allowed.

        Steps:
            1. Walk every function and skip those without a return annotation.
            2. Peel any Optional/Union wrappers to reach the leaf return members.
            3. Flag the function when any member is a fixed-arity (>=2) non-variadic tuple.
        """
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.returns is None:
                continue
            # Unwraps Optional/Union so a tuple hidden behind them is still caught
            for member in self._flatten_union_members(node.returns):
                if self._is_fixed_arity_tuple(member):
                    self._add(
                        node.returns.lineno,
                        "MULTI_VALUE_RETURN",
                        f"function '{node.name}' returns a multi-value tuple — return a named immutable class instead",
                    )
                    break

    @classmethod
    def _flatten_union_members(cls, annotation: ast.expr) -> List[ast.expr]:
        """Returns the leaf annotation members, recursively peeling Optional and Union wrappers.

        ``Optional[X]`` yields ``[X]``; ``Union[X, Y]`` yields ``[X, Y]``; ``Optional[Union[...]]``
        flattens through both layers. Anything else yields the annotation unchanged.
        """
        if isinstance(annotation, ast.Subscript) and cls._subscript_name(annotation) in ("Optional", "Union"):
            members: List[ast.expr] = []
            slice_node = annotation.slice
            elements = slice_node.elts if isinstance(slice_node, ast.Tuple) else [slice_node]
            for element in elements:
                members.extend(cls._flatten_union_members(element))
            return members
        return [annotation]

    @classmethod
    def _is_fixed_arity_tuple(cls, annotation: ast.expr) -> bool:
        """Returns whether the annotation is a fixed-arity (>=2) tuple, not the variadic Tuple[X, ...] form."""
        if not isinstance(annotation, ast.Subscript) or cls._subscript_name(annotation) not in ("Tuple", "tuple"):
            return False
        slice_node = annotation.slice
        # A non-tuple slice means a single element (Tuple[str]) — one value, not multiple
        if not isinstance(slice_node, ast.Tuple):
            return False
        elements = slice_node.elts
        # Tuple[X, ...] is a variadic homogeneous sequence, which the conventions allow
        if any(isinstance(element, ast.Constant) and element.value is Ellipsis for element in elements):
            return False
        return len(elements) >= 2

    @staticmethod
    def _subscript_name(node: ast.Subscript) -> Optional[str]:
        """Returns the head name of a subscript — ``Tuple`` for ``Tuple[...]`` and ``typing.Tuple``."""
        value = node.value
        if isinstance(value, ast.Name):
            return value.id
        if isinstance(value, ast.Attribute):
            return value.attr
        return None

    def _check_hints(self, tree: ast.Module) -> None:
        """Flags parameters and returns that carry no type hint."""
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            arguments = node.args
            named = list(arguments.posonlyargs) + list(arguments.args) + list(arguments.kwonlyargs)
            for argument in named:
                if argument.arg in ("self", "cls"):
                    continue
                if argument.annotation is None:
                    self._add(argument.lineno, "MISSING_HINT", f"parameter '{argument.arg}' lacks a type hint")
            for variadic in (arguments.vararg, arguments.kwarg):
                if variadic is not None and variadic.annotation is None:
                    self._add(variadic.lineno, "MISSING_HINT", f"parameter '{variadic.arg}' lacks a type hint")
            if node.returns is None:
                self._add(node.lineno, "MISSING_RETURN_HINT", f"function '{node.name}' lacks a return type hint")

    def _check_docstrings(self, tree: ast.Module) -> None:
        """Flags any class, function, or method that carries no docstring."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if ast.get_docstring(node) is None:
                    kind = "class" if isinstance(node, ast.ClassDef) else "function"
                    self._add(node.lineno, "MISSING_DOCSTRING", f"{kind} '{node.name}' has no docstring")

    def _check_imperative_mood(self, tree: ast.Module) -> None:
        """Flags a class/function docstring whose purpose line opens in the imperative mood."""
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            doc = ast.get_docstring(node, clean=True)
            if not doc or not doc.strip():
                continue
            verb = self._opening_verb(doc.strip().splitlines()[0])
            if verb is not None:
                self._add(
                    node.body[0].lineno,
                    "IMPERATIVE_MOOD",
                    f"docstring opens with the imperative '{verb}' — use the third-person singular present",
                )

    @classmethod
    def _opening_verb(cls, text: str) -> Optional[str]:
        """Returns the opening imperative verb if the text is in the imperative mood, else None.

        Looks at the first word, and — when that is a leading adverb ("Lazily create") — the word
        after it, so an adverb cannot smuggle an imperative past the third-person rule.
        """
        words = [word.strip("`*\"'(),.:;").lower() for word in text.strip().lstrip("`*\"'(").split()]
        if not words:
            return None
        if words[0] in cls.IMPERATIVE_VERBS:
            return words[0]
        if words[0].endswith("ly") and len(words) > 1 and words[1] in cls.IMPERATIVE_VERBS:
            return words[1]
        return None

    def _check_annotations(self, tree: ast.Module) -> None:
        """Flags lowercase builtin generics and '|' unions inside type annotations."""
        for node in ast.walk(tree):
            if isinstance(node, ast.arg) and node.annotation is not None:
                self._inspect_annotation(node.annotation)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns is not None:
                self._inspect_annotation(node.returns)
            elif isinstance(node, ast.AnnAssign):
                self._inspect_annotation(node.annotation)

    def _inspect_annotation(self, annotation: ast.expr) -> None:
        """Walks one annotation subtree and flags non-typing-module forms."""
        for node in ast.walk(annotation):
            if isinstance(node, ast.Name) and node.id in self.TYPING_NAMES:
                self._add(
                    node.lineno,
                    "LOWERCASE_GENERIC",
                    f"use typing.{self.TYPING_NAMES[node.id]} not the builtin '{node.id}'",
                )
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                self._add(node.lineno, "PEP604_UNION", "use Optional/Union not the '|' union syntax")

    def _check_percent_format(self, tree: ast.Module) -> None:
        """Flags '%' string formatting in favor of f-strings."""
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
                if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                    self._add(node.lineno, "PERCENT_FORMAT", "use an f-string not '%' formatting")

    def _check_comments(self) -> None:
        """Flags inline comments (after code) and pure divider/banner comments."""
        trivia = {tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
        last_code_line = -1
        # A malformed file may break the tokenizer; the AST pass already reported it
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(self._source).readline))
        except (tokenize.TokenError, IndentationError):
            return
        for token in tokens:
            if token.type == tokenize.COMMENT:
                self._inspect_comment(token, last_code_line)
            elif token.type not in trivia:
                last_code_line = token.start[0]

    def _inspect_comment(self, token: tokenize.TokenInfo, last_code_line: int) -> None:
        """Checks one comment token for inline placement and banner shape."""
        line = token.start[0]
        body = token.string.lstrip("#").strip()
        # A comment made only of divider characters is a banner
        if len(body) >= 3 and set(body) <= self.DIVIDER_CHARS:
            self._add(line, "BANNER_COMMENT", "divider/banner comment is not allowed")
        # A comment sharing its line with earlier code is inline
        if line == last_code_line and not body.startswith(self.COMMENT_PRAGMAS):
            self._add(line, "INLINE_COMMENT", "comment must sit on its own line, above the code")
        # A comment opens in the third person, like a docstring purpose line
        if not body.startswith(self.COMMENT_PRAGMAS):
            verb = self._opening_verb(body)
            if verb is not None:
                self._add(
                    line,
                    "IMPERATIVE_MOOD",
                    f"comment opens with the imperative '{verb}' — use the third-person singular present",
                )

    @staticmethod
    def _is_string_expression(node: ast.stmt) -> bool:
        """Returns whether the node is a bare string expression (a docstring position)."""
        return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)

    @staticmethod
    def _is_type_checking_block(node: ast.stmt) -> bool:
        """Returns whether the node is an `if TYPE_CHECKING:` guard block."""
        if not isinstance(node, ast.If):
            return False
        test = node.test
        if isinstance(test, ast.Name):
            return test.id == "TYPE_CHECKING"
        if isinstance(test, ast.Attribute):
            return test.attr == "TYPE_CHECKING"
        return False


class Cli(ABC):
    """Command-line entry that discovers .py files, runs the checker, and prints findings."""

    @staticmethod
    def run(arguments: List[str]) -> int:
        """Checks the given paths and returns a process exit code.

        Args:
            arguments: the raw command-line arguments (paths or directories).

        Returns:
            1 if any finding was reported, otherwise 0.
        """
        parser = argparse.ArgumentParser(description="Audit Python files against the the /python conventions.")
        parser.add_argument("paths", nargs="+", help="files or directories to check")
        namespace = parser.parse_args(arguments)
        files = Cli._gather(namespace.paths)
        findings: List[Finding] = []
        for path in files:
            # An __init__.py is a violation on its own; it is not parsed further
            if path.name == "__init__.py":
                findings.append(Finding(str(path), 1, "INIT_PY", "__init__.py files are not allowed"))
                continue
            source = path.read_text(encoding="utf-8")
            findings.extend(PythonStyleChecker(path, source).check())
        for finding in findings:
            print(f"{finding.path}:{finding.line}: [{finding.rule}] {finding.message}")
        print(f"\n{len(findings)} finding(s) across {len(files)} file(s).")
        return 1 if findings else 0

    @staticmethod
    def _gather(paths: List[str]) -> List[Path]:
        """Expands the given paths into a sorted list of .py files, recursing into directories."""
        collected: Set[Path] = set()
        for raw in paths:
            path = Path(raw)
            if path.is_dir():
                collected.update(path.rglob("*.py"))
            elif path.suffix == ".py":
                collected.add(path)
        return sorted(collected)


if __name__ == "__main__":
    sys.exit(Cli.run(sys.argv[1:]))
