---
name: python
description: >-
  Apply the project's Python coding and documentation conventions. Auto-invoke when writing or editing Python (.py) files — covers docstrings, type hints, comment policy, signatures, and style rules.
---

# Python Conventions

Apply when writing or editing `.py` files in this repo.

## Packages

- Never add `__init__.py` files. Do not create them unless the user explicitly asks.

## Module-level functions

- **No bare module-level functions.** Group closely related free functions as `@staticmethod`s on an abstract `class XxxHelper(ABC)`. Callers never hold an instance — they call `XxxHelper.method(...)` directly. This namespaces the helpers and keeps related logic together. Mirror the existing helpers: `AsyncFileHelper`, `ApiKeyHelper`, `SalCollectionHelper`, `SpecItemTextHelper`, `LoggingSetupHelper`.
  - A helper with a single static method is fine (e.g. `ApiKeyHelper.load`).
  - Module-level mutable state a helper needs (a singleton handle, an idempotency guard) becomes a class attribute the static methods reference by the class name.
  - A private function used only as a callback (e.g. a tenacity `before_sleep`) or only by one class becomes a `@staticmethod` on that class, not a module-level def.

  ```python
  class PathHelper(ABC):
      """Joins and normalizes filesystem paths."""

      @staticmethod
      def join(*parts: str) -> str:
          """Joins path components into one normalized path."""
          ...
  ```

- **The one exception — singleton accessors.** A process-wide singleton accessor that mirrors a stdlib idiom — `get_logger()` / `set_logger()` (cf. `logging.getLogger`) — stays a module-level function. Wrapping it in a helper would churn the whole repo for no gain. The exception is narrow: it covers the logger singleton, not general utilities.
- **Constants stay module-level** — the rule is about functions. Document a constant with a `#` comment on the line directly above it, never a floating `"""..."""` string after the assignment.

## Docstrings

- **Every class, function, and method carries a docstring** — but scale its depth to the function (see obvious vs. complex below).
- **No module-level docstrings.** Never add a top-of-file `"""..."""` block.
- **Class**: a fluent one-or-two-liner stating the responsibility — what this class is and what it owns. No implementation details, no history.
- **Function/method purpose line**: open with a single line in the **third-person singular present tense** — "Returns the active session", "Loads the seed corpus", "Indexes the given spec items". Never the imperative: write "Reads…", not "Read…"; "Creates…", not "Create…". Class docstrings may instead open with a noun phrase stating the responsibility.
- **Obvious functions** (simple getters and setters, trivial pass-throughs): the purpose line **alone**. Skip the `Args:`/`Returns:`/`Raises:` dance — it only adds noise.

  ```python
  def name(self) -> str:
      """Returns the session's display name."""
      return self._name
  ```

- **Non-trivial functions**: after the purpose line, document the arguments, the return value, and the raised exceptions:

  ```python
  def resolve(self, key: str) -> Bar:
      """Returns the Bar resolved from the given key.

      Args:
          key: one line arg purpose.

      Returns:
          One line return value description.

      Raises:
          KeyError: one line description.
          LookupError: one line description.
      """
  ```

  - Include `Args:` whenever the function takes arguments; omit `self`/`cls`.
  - Include `Returns:` whenever the function returns a value; omit it when the function returns `None`.
  - Include `Raises:` only for exceptions a caller should anticipate; omit it when the function raises none.
  - Describe purpose, not type — never repeat types already in the signature.

- **Complex functions**: under the purpose line, add a short **algorithm outline** — the ordered steps the function takes — then the `Args:`/`Returns:`/`Raises:` sections.

  ```python
  def reconcile(self, seeds: List[Seed]) -> ReconcileReport:
      """Reconciles incoming seeds against the indexed taxonomy.

      Steps:
          1. Search the index for each seed's closest existing match.
          2. Mark seeds above the match threshold as seeded, the rest as new.
          3. Persist new seeds and return a report of both sets.

      Args:
          seeds: the seeds to reconcile this run.

      Returns:
          A report partitioning the seeds into seeded and new.

      Raises:
          IndexUnavailableError: one line description.
      """
  ```

- Present the **intended design as it stands now**. Do not narrate prior approaches, rejected alternatives, or iteration history.

## Comments

- Add a short comment before each meaningful code block — every block longer than two lines and every complex one-liner — hinting what the block is doing.
- Explain **why** or signpost **what's next**, never restate the obvious line-by-line.
- **Never write an inline comment on the same line as a statement.** A comment always sits on its own line, directly above the code it describes.
- **Start every comment with a third-person active-voice verb** — `Gets`, `Returns`, `Validates`, `Resets` — mirroring the docstring purpose line. Never an imperative ("Reset", "Get") or a noun phrase.
- Start every comment with a capital letter. No trailing period.
- One-line form: `# Resets session state on startup`
- Never use `#----`, `#====`, or any divider/banner-style comments.
- Never use `#` comments in place of docstrings.
- Present the final decision only. Do not record prior discussion, rejected options, or claim IDs (e.g., `INFER-`, `SAL-`) in code.

## Imports

- **All imports go at the top of the file.** No exceptions for circular imports, lazy loading, optional dependencies, conditional imports, or "expensive" modules — restructure the code instead.
- Never import inside functions, methods, class bodies, `if`/`try` blocks, or any other inline position.
- Grouped in order: stdlib, third-party, local. One blank line between groups.
- Hint-only types go under a top-of-file `if TYPE_CHECKING:` block — still at the top, not inline.

## Type hints

- All functions and methods are fully type-hinted.
- **Use the `typing` module forms**: `List`, `Dict`, `Tuple`, `Set`, `Optional`, `Union`, `Iterable`, `Callable`, etc. Not the lowercase builtins (`list`, `dict`, `tuple`).
- Be precise: `Dict[str, Any]`, not bare `Dict`.
- Use real imported types, not string annotations. Import hint-only types under `if TYPE_CHECKING:`.
- Docstrings do not repeat types already in hints.

## Function signatures

- **Never use the bare `*` keyword-only marker.** Declare every parameter as a normal positional-or-keyword argument. The bare `*` adds a cryptic token, forces every caller to spell out keywords, and signals intent obscurely — callers can already pass by name wherever that reads better.

  ```python
  # Wrong — bare * forces keyword-only and clutters the signature
  async def apply_turn(self, *, project_id: str, turn: AuthoringTurn) -> TurnResult:
      ...

  # Right — plain positional-or-keyword parameters
  async def apply_turn(self, project_id: str, turn: AuthoringTurn) -> TurnResult:
      ...
  ```

- The only `*` allowed in a signature is a genuine variadic — `*args` / `**kwargs` — and it goes at the end, after all named parameters.
- Order: positional → named-with-defaults → `*args` → `**kwargs`.

## Return values

- **Never return multiple values as a bare tuple.** A function that hands back several distinct values — `Tuple[str, str]`, `Tuple[Claim, int]`, `Tuple[bool, str, str]` — forces every caller to unpack by position and remember what each slot means. Return a small immutable class instead, with a named field per value.

  ```python
  # Wrong — a positional pair; callers unpack blind
  def split_ref(self, ref: str) -> Tuple[str, str]:
      ...
  owner, name = repo.split_ref(ref)

  # Right — a named immutable result
  @dataclass(frozen=True)
  class ParsedRef:
      """A claim reference split into its owner and name."""

      owner: str
      name: str

  def split_ref(self, ref: str) -> ParsedRef:
      ...
  ```

  - Use the repo's established model carrier for the result type. This codebase models domain values as Pydantic `BaseModel`, so make the result a `BaseModel` with `model_config = ConfigDict(frozen=True)` to keep it immutable. (In a repo that uses neither, a `@dataclass(frozen=True)` or `class XxxResult(NamedTuple)` is the equivalent.) Name every field with full, self-explanatory words.
  - The same applies to the wrapped forms — `Optional[Tuple[str, str]]` and `Union[Tuple[...], ...]` are the same anti-pattern, just behind an `Optional`/`Union`.
  - **Allowed:** the variadic homogeneous tuple `Tuple[str, ...]` is an immutable *sequence*, not multiple values — keep it. A single-element `Tuple[str]` is one value, not multiple, and is allowed too.
  - This rule is about a function's **own** return. A tuple nested inside a returned collection — `List[Tuple[str, str]]`, `Dict[str, Tuple[int, int]]` — is a collection of pairs; prefer a named element type where it reads better, but treat that as a judgment call, not a hard breach.

## Style

- f-strings, not `%` formatting.
- Indentation aligns with the surrounding block.
- Tone: concise, precise, neutral.

## When editing existing code

- Bring docstrings and comments in line with these rules; improve docs rather than rewriting logic.
- Preserve behavior unless explicitly asked to change it.
- If you encounter an existing top-of-file module docstring, leave it alone unless the user asks for cleanup — but do not add new ones.

## Project document references

In docstrings, comments, or code, reference the project's spec documents by name only (e.g., `PRD`, `SRS`). Do not link to specific sections or claim IDs — those churn.
