// File: src/scanner/repoScanner.ts

const fg = require("fast-glob");
const path = require("path");
const fs = require("fs");
const {
    Project,
    SyntaxKind
} = require("ts-morph");

const TARGET_EXTENSIONS = [".ts", ".tsx", ".js"];
const IGNORE_PATTERNS = ["**/node_modules/**", "**/*.test.ts", "**/*.spec.ts"];

export async function scanRepository(repoPath: string): Promise<string[]> {
    const pattern = TARGET_EXTENSIONS.map(
        (ext: string) => `${repoPath.replace(/\\/g, "/")}/**/*${ext}`
    );

    const files = await fg(pattern, {
        ignore: IGNORE_PATTERNS,
        onlyFiles: true,
        absolute: true
    });

    return files.filter((file: string) => fs.existsSync(file));
}

export function extractFunctionsFromFile(filePath: string) {
    const project = new Project({
        compilerOptions: { allowJs: true }
    });

    const sourceFile = project.addSourceFileAtPath(filePath);
    const result: any[] = [];

    const extractCalls = (node: any): string[] => {
        return node
            .getDescendantsOfKind(SyntaxKind.CallExpression)
            .map((expr: any) => expr.getExpression().getText())
            .filter((name: string) => /^[a-zA-Z_$][a-zA-Z0-9_$]*$/.test(name)); // Simple identifiers only
    };

    sourceFile.getFunctions().forEach((fn: any) => {
        result.push({
            type: "function",
            name: fn.getName(),
            filePath,
            startLine: fn.getStartLineNumber(),
            endLine: fn.getEndLineNumber(),
            content: fn.getText(),
            calls: extractCalls(fn)
        });
    });

    sourceFile.getClasses().forEach((cls: any) => {
        const className = cls.getName();
        cls.getMethods().forEach((method: any) => {
            result.push({
                type: "class-method",
                class: className,
                name: method.getName(),
                filePath,
                startLine: method.getStartLineNumber(),
                endLine: method.getEndLineNumber(),
                content: method.getText(),
                calls: extractCalls(method)
            });
        });
    });

    return result;
}

export function parseCoverageSummary(coveragePath: string) {
    if (!fs.existsSync(coveragePath)) {
        throw new Error("❌ coverage-summary.json not found. Please run jest with --coverage first.");
    }

    const raw = fs.readFileSync(coveragePath, "utf-8");
    const summary = JSON.parse(raw);

    const uncovered: Record<string, number[]> = {};

    Object.entries(summary).forEach(([filePath, metrics]: any) => {
        if (filePath === "total") return;
        const absolutePath = path.resolve(filePath);

        if (!metrics.lines || !metrics.lines.details) return;
        const uncoveredLines = metrics.lines.details
            .filter((d: any) => d.hit === 0)
            .map((d: any) => d.line);

        if (uncoveredLines.length) {
            uncovered[absolutePath] = uncoveredLines;
        }
    });

    return uncovered;
}

if (require.main === module) {
    const inputPath = process.argv[2];
    if (!inputPath) {
        console.error("❌ Please provide a repository path to scan.");
        process.exit(1);
    }

    (async () => {
        const files = await scanRepository(path.resolve(inputPath));
        console.log(`✅ Found ${files.length} source files. Parsing AST...`);

        const allFunctions: any[] = [];
        for (const file of files) {
            try {
                const extracted = extractFunctionsFromFile(file);
                allFunctions.push(...extracted);
            } catch (err) {
                console.warn(`⚠️ Skipping ${file} due to parse error.`);
            }
        }

        const functionMapPath = "function-map.json";
        fs.writeFileSync(functionMapPath, JSON.stringify(allFunctions, null, 2));
        console.log(`📄 Extracted ${allFunctions.length} functions/methods. Saved to ${functionMapPath}`);

        try {
            const coverage = parseCoverageSummary("coverage/coverage-summary.json");
            const uncoveredFns = allFunctions.filter(fn => {
                const lines = coverage[fn.filePath];
                if (!lines) return false;
                return lines.some(line => line >= fn.startLine && line <= fn.endLine);
            });

            fs.writeFileSync("uncovered-functions.json", JSON.stringify(uncoveredFns, null, 2));
            console.log(`🔍 Identified ${uncoveredFns.length} uncovered functions. Saved to uncovered-functions.json`);
        } catch (err) {
            if (err instanceof Error) {
                console.warn(`⚠️ Skipped coverage parsing: ${err.message}`);
            } else {
                console.warn(`⚠️ Skipped coverage parsing due to unknown error.`);
            }
        }
    })();
}
