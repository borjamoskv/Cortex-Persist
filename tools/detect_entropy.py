#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized | borjamoskv
"""
detect_entropy — BABYLON-60 Linguistic Entropy CLI (PLAYGROUND EDITION)
========================================================================

Usage:
  detect_entropy --text "some text"
  detect_entropy --file README.md
  detect_entropy --dir ./docs --format table
  detect_entropy --stdin < corpus.txt
  detect_entropy --file text.md --format json
  detect_entropy --dir . --threshold 0.6 --fail-on-anergy

Exit codes:
  0 — All texts pass exergy threshold
  1 — One or more texts below threshold (CI gate)
  2 — Input/runtime error
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# ─── ANSI color palette (no third-party deps) ────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
BLUE   = "\033[94m"
MAGENTA= "\033[95m"
WHITE  = "\033[97m"
GRAY   = "\033[90m"

_SUPPORTS_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def c(text: str, color: str, bold: bool = False) -> str:
    if not _SUPPORTS_COLOR:
        return text
    return f"{BOLD if bold else ''}{color}{text}{RESET}"


# ─── Exergy color thresholds ─────────────────────────────────────────────────

def _exergy_color(score: float) -> str:
    if score >= 0.85:
        return GREEN
    if score >= 0.65:
        return YELLOW
    return RED


def _exergy_badge(score: float) -> str:
    if score >= 0.85:
        return c("● EXERGY", GREEN, bold=True)
    if score >= 0.65:
        return c("◑ MEDIUM", YELLOW, bold=True)
    return c("○ ANERGY", RED, bold=True)


def _burstiness_label(b: float) -> str:
    if b >= 0.3:
        return c("BURSTY", CYAN)
    if b >= -0.2:
        return c("NEUTRAL", GRAY)
    return c("ROBOTIC", RED)


# ─── Output formatters ────────────────────────────────────────────────────────

def _bar(value: float, width: int = 20, color: str = GREEN) -> str:
    filled = int(round(value * width))
    bar = "█" * filled + "░" * (width - filled)
    return c(bar, color)


def _fmt_rich(report_dict: dict[str, Any], label: str = "") -> str:
    r = report_dict
    exergy = r["exergy_score"]
    ec = _exergy_color(exergy)

    lines: list[str] = []
    if label:
        lines.append(c(f"\n  ┌─ {label} ", BLUE, bold=True) + c("─" * max(0, 60 - len(label)), BLUE))
    else:
        lines.append(c("\n  ┌─ ANALYSIS ─────────────────────────────────────────────", BLUE, bold=True))

    lines.append(f"  │  {_exergy_badge(exergy)}   {c(str(exergy), ec, bold=True)}  {_bar(exergy, 24, ec)}")
    lines.append("  │")
    lines.append(f"  │  {c('COUNTS', WHITE, bold=True)}")

    words_s   = c(str(r["word_count"]),    CYAN)
    chars_s   = c(str(r["char_count"]),    CYAN)
    sents_s   = c(str(r["sentence_count"]), CYAN)
    unique_s  = c(str(r["unique_words"]),  CYAN)
    lines.append(f"  │    words      {words_s:>10}    chars     {chars_s:>10}")
    lines.append(f"  │    sentences  {sents_s:>10}    unique    {unique_s:>10}")
    lines.append("  │")
    lines.append(f"  │  {c('ENTROPY', WHITE, bold=True)}")

    ce  = c(f"{r['char_entropy']:.4f}",    MAGENTA)
    we  = c(f"{r['word_entropy']:.4f}",    MAGENTA)
    be  = c(f"{r['bigram_entropy']:.4f}",  MAGENTA)
    te  = c(f"{r['trigram_entropy']:.4f}", MAGENTA)
    lines.append(f"  │    char       {ce:>10}    word      {we:>10}")
    lines.append(f"  │    bigram     {be:>10}    trigram   {te:>10}")
    lines.append("  │")
    lines.append(f"  │  {c('LEXICAL DIVERSITY', WHITE, bold=True)}")

    ttr_s   = c(f"{r['ttr']:.4f}",   CYAN)
    mattr_s = c(f"{r['mattr']:.4f}", CYAN)
    lines.append(f"  │    TTR        {ttr_s:>10}    MATTR     {mattr_s:>10}")
    lines.append("  │")
    lines.append(f"  │  {c('STRUCTURAL', WHITE, bold=True)}")

    asl   = c(f"{r['avg_sentence_length']:.1f} words",   CYAN)
    var_s = c(f"{r['sentence_length_variance']:.1f}",    CYAN)
    bur   = c(f"{r['burstiness']:.4f}",                  CYAN)
    rot   = c(f"{r['context_rot_score']:.4f}",           CYAN)
    rot_l = "LOW" if r["context_rot_score"] < 0.2 else ("HIGH" if r["context_rot_score"] > 0.5 else "MEDIUM")
    lines.append(f"  │    avg sent   {asl:>16}    variance  {var_s:>10}")
    lines.append(f"  │    burstiness {bur:>10}    {_burstiness_label(r['burstiness'])}")
    lines.append(f"  │    ctx rot    {rot:>10}    {rot_l}")
    lines.append("  │")

    slop   = r["slop_instances_count"]
    slop_d = r["slop_density"]
    slop_color = RED if slop > 0 else GREEN
    slop_s   = c(str(slop),               slop_color, bold=True)
    slop_ds  = c(f"{slop_d:.4f}",        slop_color)
    slop_ws  = c(f"{r['slop_weight_total']:.2f}", slop_color)
    lines.append(f"  │  {c('SLOP / ANERGY', WHITE, bold=True)}")
    lines.append(f"  │    instances  {slop_s:>10}    density   {slop_ds:>10}    weight {slop_ws}")

    if slop > 0:
        lines.append(f"  │    {c('▸ SLOP MATCHES:', YELLOW)}")
        for s in r.get("slop_instances", [])[:8]:
            matched  = s["matched_text"][:50]
            weight_s = c(f"[{s['severity_weight']:.1f}]", RED)
            text_s   = c(matched, GRAY)
            lines.append(f"  │      {weight_s} {text_s}")
        if slop > 8:
            lines.append(f"  │      {c(f'... and {slop - 8} more', GRAY)}")

    lines.append(c("  └─────────────────────────────────────────────────────────", BLUE))
    return "\n".join(lines)


def _fmt_table(reports: list[tuple[str, dict[str, Any]]]) -> str:

    """Tabular summary for batch --dir mode."""
    header = f"{'Label':<40} {'Exergy':>8} {'Words':>7} {'W-Ent':>7} {'Bigram':>8} {'TTR':>7} {'Slop#':>6} {'Burst':>7}"
    sep = "─" * len(header)
    rows = [c(header, WHITE, bold=True), sep]
    for label, r in reports:
        ex = r["exergy_score"]
        ec = _exergy_color(ex)
        short = label[-38:] if len(label) > 38 else label
        row = (
            f"{short:<40} "
            f"{c(f'{ex:.3f}', ec, bold=True):>8} "
            f"{r['word_count']:>7} "
            f"{r['word_entropy']:>7.3f} "
            f"{r['bigram_entropy']:>8.3f} "
            f"{r['ttr']:>7.3f} "
            f"{r['slop_instances_count']:>6} "
            f"{r['burstiness']:>7.3f}"
        )
        rows.append(row)
    rows.append(sep)
    return "\n".join(rows)


def _fmt_json(report_dict: dict[str, Any]) -> str:
    return json.dumps(report_dict, ensure_ascii=False, indent=2)


def _fmt_yaml(report_dict: dict[str, Any]) -> str:
    try:
        import yaml
        return yaml.dump(report_dict, allow_unicode=True, sort_keys=False)
    except ImportError:
        # Fallback: minimal YAML-like output
        lines = []
        for k, v in report_dict.items():
            if isinstance(v, list):
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)


# ─── Directory scanning ───────────────────────────────────────────────────────

_TEXT_EXTENSIONS = {".md", ".txt", ".rst", ".mdx"}


def _scan_directory(
    path: str,
    extensions: set[str],
    exclude: list[str],
) -> list[tuple[str, str]]:
    """Returns list of (relative_path, content) tuples."""
    results: list[tuple[str, str]] = []
    base = Path(path).resolve()
    for root, dirs, files in os.walk(base):
        # Prune hidden and excluded dirs
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".")
            and d not in {"node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
            and d not in exclude
        ]
        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix.lower() in extensions:
                try:
                    content = fpath.read_text(encoding="utf-8")
                    rel = str(fpath.relative_to(base))
                    results.append((rel, content))
                except (OSError, UnicodeDecodeError):
                    continue
    return sorted(results)


# ─── Main ─────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="detect_entropy",
        description="BABYLON-60 Linguistic Entropy Detector (Ω₁₇) — borjamoskv",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  detect_entropy -t "Aquí tienes el código. Espero que esto ayude."
  detect_entropy -f README.md --format rich
  detect_entropy --dir ./docs --format table --threshold 0.7
  detect_entropy --dir . --ext md txt --fail-on-anergy
  cat corpus.txt | detect_entropy --stdin --format json
"""
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", "-t", type=str, help="Literal text string to analyze.")
    source.add_argument("--file", "-f", type=str, help="Path to file to analyze.")
    source.add_argument("--dir", "-d", type=str, help="Directory to batch-scan.")
    source.add_argument("--stdin", "-s", action="store_true", help="Read from stdin.")

    parser.add_argument(
        "--format",
        choices=["rich", "json", "yaml", "table"],
        default="rich",
        help="Output format (default: rich).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Exergy score threshold. Files below this are flagged.",
    )
    parser.add_argument(
        "--fail-on-anergy",
        action="store_true",
        help="Exit code 1 if any text is below --threshold (default 0.65 if not specified).",
    )
    parser.add_argument(
        "--ext",
        nargs="+",
        default=["md"],
        help="File extensions to scan in --dir mode (default: md).",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        help="Directory names to exclude in --dir scan.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Limit results shown in table mode (default: 20).",
    )
    parser.add_argument(
        "--no-slop-list",
        action="store_true",
        help="Suppress individual slop match list in output.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).parent.parent))

    try:
        from babylon60.utils.linguistic_entropy import LinguisticEntropyDetector
    except ImportError:
        print(
            f"{RED}ERROR{RESET}: Cannot import babylon60. "
            "Run: PYTHONPATH=. python3 tools/detect_entropy.py",
            file=sys.stderr,
        )
        return 2

    detector = LinguisticEntropyDetector()
    threshold = args.threshold if args.threshold > 0 else (0.65 if args.fail_on_anergy else 0.0)
    failed: list[str] = []

    # ── SINGLE TEXT ──────────────────────────────────────────────────────
    if args.text or args.file or args.stdin:
        if args.text:
            text = args.text
            label = "<inline>"
        elif args.stdin:
            text = sys.stdin.read()
            label = "<stdin>"
        else:
            try:
                text = Path(args.file).read_text(encoding="utf-8")
                label = args.file
            except (OSError, UnicodeDecodeError) as e:
                print(f"{RED}ERROR{RESET}: {e}", file=sys.stderr)
                return 2

        report = detector.analyze(text)
        rdict = report.to_dict()
        if args.no_slop_list:
            rdict["slop_instances"] = []

        if args.format == "rich":
            print(_fmt_rich(rdict, label))
        elif args.format == "json":
            print(_fmt_json(rdict))
        elif args.format == "yaml":
            print(_fmt_yaml(rdict))
        elif args.format == "table":
            print(_fmt_table([(label, rdict)]))

        if args.fail_on_anergy and report.exergy_score < threshold:
            failed.append(label)

    # ── BATCH DIRECTORY ──────────────────────────────────────────────────
    else:
        exts = {f".{e.lstrip('.')}" for e in args.ext}
        files = _scan_directory(args.dir, exts, args.exclude)

        if not files:
            print(c(f"No files found in '{args.dir}' with extensions {exts}", YELLOW))
            return 0

        reports: list[tuple[str, dict[str, Any]]] = []
        for rel, content in files:
            report = detector.analyze(content)
            rdict = report.to_dict()
            reports.append((rel, rdict))

            if args.fail_on_anergy and report.exergy_score < threshold:
                failed.append(rel)

        # Sort by exergy ascending (worst first)
        reports.sort(key=lambda x: x[1]["exergy_score"])
        top_reports = reports[:args.top]

        if args.format == "table":
            print(c(f"\n  BABYLON-60 LINGUISTIC ENTROPY SCAN — {args.dir}", BLUE, bold=True))
            print(c(f"  Files: {len(files)} | Extensions: {', '.join(sorted(exts))}", GRAY))
            if threshold > 0:
                print(c(f"  Threshold: {threshold}", GRAY))
            print()
            print(_fmt_table(top_reports))

            # Summary stats
            all_scores = [r["exergy_score"] for _, r in reports]
            avg_score = sum(all_scores) / len(all_scores)
            below = sum(1 for s in all_scores if s < threshold)
            print()
            print(c(f"  Summary: {len(files)} files | avg exergy {avg_score:.3f}", WHITE, bold=True))
            if threshold > 0 and below > 0:
                print(c(f"  ⚠ {below} file(s) below threshold {threshold}", YELLOW))

        elif args.format == "rich":
            for label, rdict in top_reports:
                if args.no_slop_list:
                    rdict["slop_instances"] = []
                print(_fmt_rich(rdict, label))
        elif args.format == "json":
            print(json.dumps([{"file": k, "report": v} for k, v in reports], ensure_ascii=False, indent=2))
        elif args.format == "yaml":
            print(_fmt_yaml({"files": [{"file": k, **v} for k, v in reports]}))

    if failed:
        print(c(f"\n  ✗ ANERGY GATE FAILED: {len(failed)} file(s) below threshold {threshold}", RED, bold=True))
        for f in failed:
            print(c(f"    · {f}", RED))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
