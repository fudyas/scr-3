/**
 * Deterministic checker for the `/typescript` conventions — the
 * mechanical half of the `/typescript-style` audit. Parses each target
 * with the TypeScript compiler API and reports one `Finding` per
 * violation it can decide without judgment (filename casing, `any`,
 * loose equality, `var`, banner comments, stray `console.log`, deep
 * relative imports, barrel `index` files).
 *
 * Rules that need a read of intent (JSDoc depth, naming by essence,
 * layering, wire-type provenance) live in the `/typescript-style`
 * judgment pass, not here. Keep this file aligned with `/typescript`:
 * if a convention there changes, update the matching check.
 *
 * Run through LETS (vite-node resolves `typescript` from the web
 * client's node_modules):
 *
 *   ./bin/lets devenv node npx --work-dir src/app/clients/web vite-node \
 *     "$(pwd)/.claude/skills/typescript-style/check.ts" -- <path> [<path> ...]
 */
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, basename, extname, isAbsolute, join, relative, resolve } from "node:path";
import ts from "typescript";

/** A single style violation located at a file and line. */
interface Finding {
  path: string;
  line: number;
  rule: string;
  message: string;
}

/**
 * Checks one TypeScript module against the the project style rules that can be
 * decided mechanically. One instance per file; `check()` returns its
 * findings in discovery order.
 */
class TypeScriptStyleChecker {
  // Directory characters that, alone on a comment line, make it a banner
  private static readonly DIVIDER = /^[-=*_~]{3,}$/;

  private readonly findings: Finding[] = [];
  private readonly source: string;
  private readonly displayPath: string;
  private readonly absolutePath: string;

  constructor(absolutePath: string, displayPath: string, source: string) {
    this.absolutePath = absolutePath;
    this.displayPath = displayPath;
    this.source = source;
  }

  /**
   * Runs every mechanical check and returns the findings for this module.
   *
   * Steps:
   *   1. Check the filename casing — no parse needed.
   *   2. Parse the source into a SourceFile (TSX-aware by extension).
   *   3. Walk the AST for `any`, loose equality, `var`, `console.log`,
   *      and deep relative imports.
   *   4. Scan the raw lines for banner/divider comments.
   */
  check(): Finding[] {
    this.checkFilename();
    const scriptKind = this.absolutePath.endsWith(".tsx")
      ? ts.ScriptKind.TSX
      : ts.ScriptKind.TS;
    const sourceFile = ts.createSourceFile(
      this.absolutePath,
      this.source,
      ts.ScriptTarget.Latest,
      true,
      scriptKind,
    );
    this.walk(sourceFile, sourceFile);
    this.checkBannerComments();
    return this.findings;
  }

  /** Records one finding against this module. */
  private add(line: number, rule: string, message: string): void {
    this.findings.push({ path: this.displayPath, line, rule, message });
  }

  /** Returns the 1-based line of a node's first token. */
  private lineOf(sourceFile: ts.SourceFile, node: ts.Node): number {
    return sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line + 1;
  }

  /**
   * Flags a filename that is neither kebab-case nor (for components) a
   * PascalCase `.tsx`. `.ts` files must be kebab-case; `.tsx` files may
   * be kebab-case (hooks, utilities) or PascalCase (components). Any
   * underscore or stray camelCase is a violation.
   */
  private checkFilename(): void {
    const ext = extname(this.absolutePath);
    // Strips compound suffixes (.test/.spec/.d) so only the stem is judged
    const stem = basename(this.absolutePath).split(".")[0] ?? "";
    if (stem.length === 0) {
      return;
    }
    const isKebab = /^[a-z0-9]+(-[a-z0-9]+)*$/.test(stem);
    const isPascal = /^[A-Z][A-Za-z0-9]*$/.test(stem);
    if (ext === ".tsx") {
      if (!isKebab && !isPascal) {
        this.add(
          1,
          "FILENAME_CASE",
          `'${stem}${ext}' is neither kebab-case nor PascalCase — components are PascalCase, everything else kebab-case`,
        );
      }
      return;
    }
    if (!isKebab) {
      this.add(1, "FILENAME_CASE", `'${stem}${ext}' must be kebab-case — no camelCase or snake_case`);
    }
  }

  /** Walks the tree, dispatching each node kind to its check. */
  private walk(node: ts.Node, sourceFile: ts.SourceFile): void {
    if (node.kind === ts.SyntaxKind.AnyKeyword) {
      this.add(this.lineOf(sourceFile, node), "EXPLICIT_ANY", "uses 'any' — prefer 'unknown' and narrow, or a precise type");
    } else if (ts.isBinaryExpression(node)) {
      this.checkLooseEquality(node, sourceFile);
    } else if (ts.isVariableDeclarationList(node)) {
      this.checkVarKeyword(node, sourceFile);
    } else if (ts.isCallExpression(node)) {
      this.checkConsoleLog(node, sourceFile);
    } else if (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) {
      this.checkDeepRelativeImport(node.moduleSpecifier, sourceFile);
    }
    ts.forEachChild(node, (child) => this.walk(child, sourceFile));
  }

  /** Flags `==` / `!=` in favor of strict `===` / `!==`. */
  private checkLooseEquality(node: ts.BinaryExpression, sourceFile: ts.SourceFile): void {
    const kind = node.operatorToken.kind;
    if (kind === ts.SyntaxKind.EqualsEqualsToken || kind === ts.SyntaxKind.ExclamationEqualsToken) {
      this.add(
        this.lineOf(sourceFile, node.operatorToken),
        "LOOSE_EQUALITY",
        "use strict equality '===' / '!==' not '==' / '!='",
      );
    }
  }

  /** Flags a `var` declaration in favor of `const` / `let`. */
  private checkVarKeyword(node: ts.VariableDeclarationList, sourceFile: ts.SourceFile): void {
    const isLet = (node.flags & ts.NodeFlags.Let) !== 0;
    const isConst = (node.flags & ts.NodeFlags.Const) !== 0;
    if (!isLet && !isConst) {
      this.add(this.lineOf(sourceFile, node), "VAR_KEYWORD", "use 'const' or 'let' not 'var'");
    }
  }

  /** Flags a bare `console.log` call — dev logging belongs behind an `import.meta.env.DEV` guard. */
  private checkConsoleLog(node: ts.CallExpression, sourceFile: ts.SourceFile): void {
    const callee = node.expression;
    if (
      ts.isPropertyAccessExpression(callee) &&
      ts.isIdentifier(callee.expression) &&
      callee.expression.text === "console" &&
      callee.name.text === "log"
    ) {
      this.add(
        this.lineOf(sourceFile, node),
        "CONSOLE_LOG",
        "console.log left in code — guard dev logging behind import.meta.env.DEV (console.debug) or remove",
      );
    }
  }

  /** Flags an import that reaches up two or more directories instead of using the `@/` alias. */
  private checkDeepRelativeImport(specifier: ts.Expression | undefined, sourceFile: ts.SourceFile): void {
    if (specifier !== undefined && ts.isStringLiteral(specifier) && specifier.text.startsWith("../../")) {
      this.add(
        this.lineOf(sourceFile, specifier),
        "DEEP_RELATIVE_IMPORT",
        `deep relative import '${specifier.text}' — use the '@/' path alias`,
      );
    }
  }

  /** Flags comment lines made only of divider characters (banners). */
  private checkBannerComments(): void {
    const lines = this.source.split("\n");
    lines.forEach((raw, index) => {
      // Strips the comment opener and any leading-block '*' before testing
      const body = raw.trim().replace(/^(\/\/|\/\*+|\*+\/?)/, "").replace(/\*\/$/, "").trim();
      if (TypeScriptStyleChecker.DIVIDER.test(body)) {
        this.add(index + 1, "BANNER_COMMENT", "divider/banner comment is not allowed");
      }
    });
  }
}

/** Walks paths, runs the checker, and prints findings as `path:line: [RULE] message`. */
function gather(repoRoot: string, paths: string[]): string[] {
  const collected = new Set<string>();
  // Directories and files that are generated or vendored and never audited
  const skip = (path: string): boolean =>
    path.includes("/node_modules/") || path.includes("/generated/") || path.includes("/dist/");
  const visit = (absolute: string): void => {
    if (skip(absolute) || !existsSync(absolute)) {
      return;
    }
    if (statSync(absolute).isDirectory()) {
      for (const entry of readdirSync(absolute)) {
        visit(join(absolute, entry));
      }
      return;
    }
    const ext = extname(absolute);
    if (ext === ".ts" || ext === ".tsx") {
      collected.add(absolute);
    }
  };
  for (const raw of paths) {
    visit(isAbsolute(raw) ? raw : resolve(repoRoot, raw));
  }
  return [...collected].sort();
}

/** Finds the repository root by walking up from `start` until a `.git` entry appears. */
function findRepoRoot(start: string): string {
  let current = start;
  while (true) {
    if (existsSync(join(current, ".git"))) {
      return current;
    }
    const parent = dirname(current);
    if (parent === current) {
      return start;
    }
    current = parent;
  }
}

/** Checks the given paths and returns a process exit code (1 if any finding). */
function run(argv: string[]): number {
  if (argv.length === 0) {
    process.stderr.write("usage: check.ts <path> [<path> ...]\n");
    return 2;
  }
  const repoRoot = findRepoRoot(process.cwd());
  const files = gather(repoRoot, argv);
  const findings: Finding[] = [];
  for (const file of files) {
    const displayPath = relative(repoRoot, file);
    // A barrel index file is a violation on its own; it is not parsed further
    if (basename(file) === "index.ts" || basename(file) === "index.tsx") {
      findings.push({ path: displayPath, line: 1, rule: "BARREL_INDEX", message: "barrel 'index' file is not allowed — import modules by their own path" });
      continue;
    }
    const source = readFileSync(file, "utf-8");
    findings.push(...new TypeScriptStyleChecker(file, displayPath, source).check());
  }
  for (const finding of findings) {
    process.stdout.write(`${finding.path}:${finding.line}: [${finding.rule}] ${finding.message}\n`);
  }
  process.stdout.write(`\n${findings.length} finding(s) across ${files.length} file(s).\n`);
  return findings.length > 0 ? 1 : 0;
}

process.exit(run(process.argv.slice(2)));
