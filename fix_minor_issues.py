import os
import re

CSS_REPLACEMENTS = {
    "/Users/borjafernandezangulo/projects/sonograft/src/style.css": [
        (
            r"backdrop-filter:([^;]+);(?![\s\n]*-webkit-backdrop-filter)",
            r"-webkit-backdrop-filter:\1;\n  backdrop-filter:\1;",
        ),
        (r"-webkit-mask:([^;]+);", r"-webkit-mask:\1;\n  mask:\1;"),
        (
            r"mask-image:([^;]+);\s*-webkit-mask-image:([^;]+);",
            r"-webkit-mask-image:\2;\n  mask-image:\1;",
        ),
        (
            r"backdrop-filter:([^;]+);\s*-webkit-backdrop-filter:([^;]+);",
            r"-webkit-backdrop-filter:\2;\n  backdrop-filter:\1;",
        ),
    ],
    "/Users/borjafernandezangulo/cortex/saas/saas.css": [
        (
            r"backdrop-filter:([^;]+);\s*-webkit-backdrop-filter:([^;]+);",
            r"-webkit-backdrop-filter:\2;\n  backdrop-filter:\1;",
        )
    ],
    "/Users/borjafernandezangulo/cortex/impact-web/src/index.css": [
        (
            r"backdrop-filter:([^;]+);\s*-webkit-backdrop-filter:([^;]+);",
            r"-webkit-backdrop-filter:\2;\n  backdrop-filter:\1;",
        )
    ],
    "/Users/borjafernandezangulo/cortex/sonic-supreme/src/index.css": [
        (
            r"backdrop-filter:([^;]+);\s*-webkit-backdrop-filter:([^;]+);",
            r"-webkit-backdrop-filter:\2;\n  backdrop-filter:\1;",
        )
    ],
    "/Users/borjafernandezangulo/cortex/saas/dashboard.html": [
        (
            r"backdrop-filter:([^;]+);",
            r"-webkit-backdrop-filter:\1;\n            backdrop-filter:\1;",
        )
    ],
}

for filepath, replacements in CSS_REPLACEMENTS.items():
    if not os.path.exists(filepath):
        continue
    with open(filepath) as f:
        content = f.read()

    original_content = content
    for patt, repl in replacements:
        content = re.sub(patt, repl, content)

    if content != original_content:
        with open(filepath, "w") as f:
            f.write(content)

tsconfig_fixes = [
    "/Users/borjafernandezangulo/cortex/impact-web/tsconfig.app.json",
    "/Users/borjafernandezangulo/cortex/impact-web/tsconfig.node.json",
    "/Users/borjafernandezangulo/cortex/sdks/js/tsconfig.json",
    "/Users/borjafernandezangulo/cortex/sonic-supreme/tsconfig.app.json",
    "/Users/borjafernandezangulo/cortex/sonic-supreme/tsconfig.node.json",
    "/Users/borjafernandezangulo/projects/sonograft/tsconfig.json",
]

for p in tsconfig_fixes:
    if os.path.exists(p):
        with open(p) as f:
            c = f.read()
        if '"forceConsistentCasingInFileNames"' not in c:
            c = re.sub(
                r'"compilerOptions":\s*\{',
                '"compilerOptions": {\n    "forceConsistentCasingInFileNames": true,',
                c,
            )
            with open(p, "w") as f:
                f.write(c)

print("Automated fixes applied successfully.")
