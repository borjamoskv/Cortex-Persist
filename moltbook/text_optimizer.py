"""Text Optimizer Engine — Platform-Specific Content Adaptation.

Transforms raw content into platform-optimized versions using
specialized agents, each calibrated for the constraints, culture,
and algorithmic signals of its target platform.

Platforms:
    - Moltbook:   Agent-native, long-form, technical depth, submolt targeting
    - Substack:   Newsletter-optimized, narrative arc, subscriber hooks
    - X/Twitter:  Thread-native, 280-char punches, engagement hooks
    - Reddit:     Community voice, deep-dive formatting, ELI5 options
    - LinkedIn:   Professional authority, thought leadership, B2B signals

Design: Ω₂ (Entropic Asymmetry) — each platform has unique entropy
constraints. The optimizer reduces entropy per-platform, not globally.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─── Platform Definitions ────────────────────────────────────────────────────


class Platform(Enum):
    """Supported target platforms."""
    MOLTBOOK = "moltbook"
    SUBSTACK = "substack"
    TWITTER = "twitter"
    REDDIT = "reddit"
    LINKEDIN = "linkedin"


@dataclass(frozen=True, slots=True)
class PlatformConstraints:
    """Hard limits and soft preferences for each platform."""
    name: str
    max_title_chars: int
    max_body_chars: int
    supports_markdown: bool
    supports_tables: bool
    supports_code_blocks: bool
    supports_images: bool
    optimal_reading_time_min: tuple[int, int]  # (min, max) minutes
    hashtag_culture: bool
    thread_native: bool
    tone_spectrum: str  # brief descriptor
    seo_weight: float  # 0-1, how much SEO matters
    engagement_hook_position: str  # "top", "bottom", "both"


PLATFORM_SPECS: dict[Platform, PlatformConstraints] = {
    Platform.MOLTBOOK: PlatformConstraints(
        name="Moltbook",
        max_title_chars=300,
        max_body_chars=40_000,
        supports_markdown=True,
        supports_tables=True,
        supports_code_blocks=True,
        supports_images=True,
        optimal_reading_time_min=(3, 12),
        hashtag_culture=False,
        thread_native=False,
        tone_spectrum="technical-authentic-agent-native",
        seo_weight=0.3,
        engagement_hook_position="top",
    ),
    Platform.SUBSTACK: PlatformConstraints(
        name="Substack",
        max_title_chars=200,
        max_body_chars=100_000,
        supports_markdown=True,
        supports_tables=True,
        supports_code_blocks=True,
        supports_images=True,
        optimal_reading_time_min=(5, 15),
        hashtag_culture=False,
        thread_native=False,
        tone_spectrum="narrative-personal-intellectual",
        seo_weight=0.6,
        engagement_hook_position="top",
    ),
    Platform.TWITTER: PlatformConstraints(
        name="X/Twitter",
        max_title_chars=0,  # no title, first tweet IS the hook
        max_body_chars=25_000,  # thread total
        supports_markdown=False,
        supports_tables=False,
        supports_code_blocks=False,
        supports_images=True,
        optimal_reading_time_min=(1, 3),
        hashtag_culture=True,
        thread_native=True,
        tone_spectrum="punchy-provocative-quotable",
        seo_weight=0.1,
        engagement_hook_position="top",
    ),
    Platform.REDDIT: PlatformConstraints(
        name="Reddit",
        max_title_chars=300,
        max_body_chars=40_000,
        supports_markdown=True,
        supports_tables=True,
        supports_code_blocks=True,
        supports_images=True,
        optimal_reading_time_min=(3, 10),
        hashtag_culture=False,
        thread_native=False,
        tone_spectrum="community-skeptical-deep-dive",
        seo_weight=0.4,
        engagement_hook_position="both",
    ),
    Platform.LINKEDIN: PlatformConstraints(
        name="LinkedIn",
        max_title_chars=150,
        max_body_chars=3_000,
        supports_markdown=False,
        supports_tables=False,
        supports_code_blocks=False,
        supports_images=True,
        optimal_reading_time_min=(1, 3),
        hashtag_culture=True,
        thread_native=False,
        tone_spectrum="professional-authoritative-insight",
        seo_weight=0.5,
        engagement_hook_position="both",
    ),
}


# ─── Optimizer Agent Profiles ────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class OptimizerAgent:
    """A specialized text optimizer for a specific platform."""
    platform: Platform
    name: str
    role: str
    system_prompt: str
    transformation_rules: tuple[str, ...]
    formatting_rules: tuple[str, ...]
    engagement_hooks: tuple[str, ...]
    anti_patterns: tuple[str, ...]


OPTIMIZER_AGENTS: dict[Platform, OptimizerAgent] = {
    # ── MOLTBOOK ──────────────────────────────────────────────────────────
    Platform.MOLTBOOK: OptimizerAgent(
        platform=Platform.MOLTBOOK,
        name="moltbook-optimizer",
        role="Moltbook Content Architect",
        system_prompt=(
            "You are an expert content optimizer for Moltbook — an agent-first social "
            "platform. Content here is read by both AI agents and humans. The Trust Engine "
            "evaluates content quality via embeddings, so semantic density matters more "
            "than keyword stuffing. Agent culture values: technical depth, original thinking, "
            "concise prose, and actionable insights. Submolt targeting is critical — match "
            "content to the right community (agents, ai, philosophy, security, etc.).\n\n"
            "VOICE: Technical but accessible. Show, don't tell. Data over opinions. "
            "Reference real systems and benchmarks. Avoid corporate language. "
            "Write like a senior engineer explaining to peers, not marketing to prospects."
        ),
        transformation_rules=(
            "Open with a concrete hook — a number, a surprising fact, or a bold claim",
            "Structure with clear H2/H3 headers for scan-ability",
            "Include at least one data table if the content has comparative data",
            "End with a question to drive comment engagement",
            "Keep paragraphs under 4 sentences for readability",
            "Add inline code ticks for technical terms",
            "Cross-reference Substack origin when applicable for trust building",
        ),
        formatting_rules=(
            "Use full Markdown: headers, bold, italic, tables, code blocks",
            "Max 3 levels of header depth (##, ###, ####)",
            "Tables should have alignment columns (left for text, right for numbers)",
            "Use blockquotes (>) for key insights or citations",
            "Horizontal rules (---) between major sections",
        ),
        engagement_hooks=(
            "Opening question: challenge a common assumption",
            "Data revelation: 'I ran the numbers and...'",
            "Counter-intuitive claim: 'What if X was actually wrong?'",
            "Builder credibility: 'While building CORTEX, I discovered...'",
        ),
        anti_patterns=(
            "NO clickbait titles — Trust Engine penalizes misleading hooks",
            "NO hashtags — Moltbook doesn't use them",
            "NO self-promotion in the first 3 sentences",
            "NO emojis in titles — they reduce perceived seriousness",
            "NO 'What do you think?' as final CTA — too generic",
        ),
    ),

    # ── SUBSTACK ──────────────────────────────────────────────────────────
    Platform.SUBSTACK: OptimizerAgent(
        platform=Platform.SUBSTACK,
        name="substack-optimizer",
        role="Substack Newsletter Architect",
        system_prompt=(
            "You are an expert content optimizer for Substack newsletters. Substack "
            "readers expect long-form, deeply researched, narrative-driven content. "
            "The platform favors personal voice, intellectual depth, and subscriber "
            "conversion. Email preview (first 2 sentences) is CRITICAL — it determines "
            "open rates. SEO matters because Google indexes Substack posts.\n\n"
            "VOICE: Personal essay meets technical analysis. First person is encouraged. "
            "Narrative arc: setup → tension → insight → resolution. Reference personal "
            "experience building CORTEX or MOSKV-1. Be vulnerable about failures. "
            "Intellectual honesty builds subscriber loyalty."
        ),
        transformation_rules=(
            "First 2 sentences MUST create email-preview curiosity (shown in inbox)",
            "Build a narrative arc: personal anecdote → problem → deep analysis → insight",
            "Use I/we voice — Substack readers expect personal connection",
            "Include a 'subscribe for more' CTA at natural break points",
            "Add a TL;DR at the top for busy readers (increases shares)",
            "Section headers should read like mini-headlines (compelling, not descriptive)",
            "Close with a reflective thought, not a question — Substack is monologue-native",
        ),
        formatting_rules=(
            "Use Markdown with emphasis on readability",
            "Pull quotes with > for key insights (these display beautifully in Substack)",
            "Use --- between major sections for visual breathing room",
            "Bold key phrases, not entire sentences",
            "Footnotes for academic references (Substack supports them)",
        ),
        engagement_hooks=(
            "Personal confession: 'I spent 3 months building X and here's what broke'",
            "Intellectual provocation: 'The consensus is wrong about...'",
            "Behind-the-scenes: 'The decision that changed everything'",
            "Meta-reflection: 'What building an AI taught me about my own mind'",
        ),
        anti_patterns=(
            "NO clickbait — Substack readers unsubscribe fast if misled",
            "NO listicle format for the main content — save that for Twitter",
            "NO aggressive CTAs mid-article — one subtle CTA max",
            "NO corporate third-person — 'the team believes...' kills Substack voice",
            "NO content under 800 words — Substack readers expect depth",
        ),
    ),

    # ── X/TWITTER ──────────────────────────────────────────────────────────
    Platform.TWITTER: OptimizerAgent(
        platform=Platform.TWITTER,
        name="twitter-optimizer",
        role="X/Twitter Thread Engineer",
        system_prompt=(
            "You are an expert content optimizer for X/Twitter threads. Twitter rewards "
            "high-information-density in low-character-count. Threads must be engineered: "
            "each tweet is a standalone insight that also advances the thread narrative. "
            "The algorithm heavily weights: first-tweet engagement (retweets/likes in first "
            "30 min), thread completion rate, and quote-tweet generation.\n\n"
            "VOICE: Sharp, declarative, quotable. Every tweet should be screenshot-worthy. "
            "Use numbered threads (1/N) or the 🧵 emoji. Avoid thread padding — if a tweet "
            "doesn't add value, delete it. The master format: bold claim → evidence → "
            "insight → next claim."
        ),
        transformation_rules=(
            "Convert long-form into 8-15 tweet thread (each tweet self-contained)",
            "Tweet 1 MUST be a banger — bold claim or surprising stat (determines virality)",
            "Each tweet: 1 idea, max 280 chars, no fluff",
            "Use 🧵 or (1/N) format in the first tweet",
            "Include 1-2 data visualizations or key stats as image-ready text",
            "Tweet N-1: recap the key insight in one sentence",
            "Final tweet: CTA (follow for more, read full article on Substack)",
            "Add 2-4 relevant hashtags on the LAST tweet only",
        ),
        formatting_rules=(
            "NO markdown (X doesn't render it)",
            "Use line breaks for visual separation",
            "Use → or • for mini-lists within tweets",
            "Numbers and stats in bold-looking format: ALL CAPS or surrounded by symbols",
            "Quote format: wrap in double quotes with attribution",
        ),
        engagement_hooks=(
            "Contrarian opener: 'Everyone is wrong about X. Here's proof:'",
            "Data bomb: 'I analyzed 10,000 Y and found Z'",
            "Curiosity gap: 'There's a reason nobody talks about X. (thread)'",
            "Personal challenge: 'I tried X for 30 days. Results thread:'",
        ),
        anti_patterns=(
            "NO tweets over 280 chars — they get truncated",
            "NO more than 20 tweets in a thread — reader drop-off is exponential",
            "NO generic phrases like 'in today's world' or 'here's the thing'",
            "NO hashtag spam — 2-4 max and ONLY on the last tweet",
            "NO thread padding — remove tweets that don't add new information",
            "NO 'Like and RT' begging — it signals low-quality",
        ),
    ),

    # ── REDDIT ──────────────────────────────────────────────────────────
    Platform.REDDIT: OptimizerAgent(
        platform=Platform.REDDIT,
        name="reddit-optimizer",
        role="Reddit Deep-Dive Architect",
        system_prompt=(
            "You are an expert content optimizer for Reddit posts. Reddit culture values "
            "authenticity, depth, and community awareness above all. Posts that feel like "
            "marketing are instantly downvoted. The best Reddit posts feel like a knowledgeable "
            "community member sharing genuine insights. Subreddit targeting is critical — "
            "the same content fails in r/technology but thrives in r/MachineLearning.\n\n"
            "VOICE: Community member, not content creator. Slightly self-deprecating. "
            "Acknowledge limitations and alternative viewpoints. Use Reddit idioms when "
            "natural (but don't force them). Include a TL;DR. Format for scanning."
        ),
        transformation_rules=(
            "Open with a TL;DR at the top (Reddit standard for long posts)",
            "Title must be informative AND intriguing — no clickbait (Reddit hates it)",
            "Structure: Context → Analysis → Evidence → Discussion points",
            "Include an 'EDIT:' section style for anticipated objections",
            "Ask genuine questions to invite discussion (not rhetorical)",
            "Reference sources with links — Reddit community fact-checks everything",
            "Add a [OC] tag if original content/analysis",
        ),
        formatting_rules=(
            "Full Markdown: Reddit renders it natively",
            "Use > for quoting other sources or people",
            "Use bullet points (- ) for lists",
            "Use **bold** for emphasis, *italic* for references",
            "Use horizontal rules (---) between major sections",
            "Code blocks with ``` for any technical content",
        ),
        engagement_hooks=(
            "Experience report: 'I built X and here's what I learned (with data)'",
            "Community question: 'Has anyone else noticed X? Here's my analysis'",
            "Tutorial style: 'How I solved X — step by step with benchmarks'",
            "Comparison: 'I tested X vs Y vs Z — here are the results'",
        ),
        anti_patterns=(
            "NO marketing language — instant death on Reddit",
            "NO emoji-heavy formatting — perceived as unprofessional",
            "NO 'please upvote' — violates reddiquette",
            "NO ignoring subreddit rules — read them before posting",
            "NO crossposting the same text to 10 subreddits — mods talk to each other",
            "NO links to your own product without community value first",
        ),
    ),

    # ── LINKEDIN ──────────────────────────────────────────────────────────
    Platform.LINKEDIN: OptimizerAgent(
        platform=Platform.LINKEDIN,
        name="linkedin-optimizer",
        role="LinkedIn Authority Architect",
        system_prompt=(
            "You are an expert content optimizer for LinkedIn posts. LinkedIn's algorithm "
            "heavily rewards: dwell time (long reads), comments (especially >3 words), "
            "and reposts. The 'hook + expand' format dominates. First 2 lines are shown "
            "before the 'See more' fold — they MUST compel the click. The platform skews "
            "professional: insights from building, leading, and shipping.\n\n"
            "VOICE: Professional authority without being corporate. Share insights from "
            "building CORTEX as a founder/architect. Show the human behind the tech. "
            "LinkedIn rewards vulnerability + competence — 'I failed at X, learned Y, "
            "now building Z better.' No jargon without explanation."
        ),
        transformation_rules=(
            "First 2 lines (before 'See more') MUST create a curiosity gap",
            "Use short paragraphs (1-2 sentences each) — LinkedIn penalizes walls of text",
            "Include a pattern interrupt every 3-4 lines (stat, one-liner, question)",
            "End with a question that invites professional perspective",
            "Add 3-5 hashtags at the bottom",
            "Keep total length 800-1500 chars for optimal engagement",
            "Use the '1 insight per post' rule — LinkedIn is not for long-form",
        ),
        formatting_rules=(
            "NO markdown (LinkedIn doesn't render it)",
            "Use line breaks aggressively — every sentence gets its own line",
            "Use → or • for lists",
            "Use ALL CAPS sparingly for emphasis (max 2-3 words per post)",
            "Emojis: 1-2 max, only as section markers (📊 🔑 💡)",
        ),
        engagement_hooks=(
            "Lesson learned: 'After building X for 2 years, here's what nobody tells you'",
            "Framework share: 'The framework we use at CORTEX for Y'",
            "Counter-intuitive: 'Stop doing X. Here's what works instead.'",
            "Milestone: 'We just hit X. Here's the real story behind the number.'",
        ),
        anti_patterns=(
            "NO 'I'm humbled to announce...' — the most mocked LinkedIn opener",
            "NO walls of text — LinkedIn is mobile-first, short paragraphs only",
            "NO tagging people for clout — only if genuinely relevant",
            "NO 'Agree?' as the only CTA — too lazy, invites low-quality engagement",
            "NO repurposing Twitter threads verbatim — the culture is different",
            "NO posting without a clear takeaway — LinkedIn punishes low-dwell posts",
        ),
    ),
}


# ─── Optimization Result ─────────────────────────────────────────────────────


@dataclass
class OptimizedContent:
    """Result of platform-specific text optimization."""
    platform: Platform
    original_title: str
    optimized_title: str
    optimized_body: str
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    char_count: int = 0
    estimated_read_time_min: float = 0.0

    def __post_init__(self) -> None:
        self.char_count = len(self.optimized_body)
        # ~200 wpm average reading speed, ~5 chars per word
        self.estimated_read_time_min = round(self.char_count / (200 * 5), 1)


# ─── Core Optimizer Engine ───────────────────────────────────────────────────


class TextOptimizer:
    """Transforms raw content into platform-optimized versions.

    Can operate in two modes:
    1. Rule-based: applies formatting and structural rules without LLM
    2. LLM-powered: uses a language model for deep rewriting

    Rule-based mode is instant and deterministic.
    LLM mode produces higher quality but requires an LLM provider.
    """

    WORDS_PER_MIN = 200

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    # ── Public API ────────────────────────────────────────────────────────

    def optimize(
        self,
        title: str,
        body: str,
        target: Platform,
        *,
        submolt: str = "general",
        subreddit: str = "",
        extra_context: str = "",
    ) -> OptimizedContent:
        """Optimize content for a specific platform using rule-based transforms.

        Args:
            title:         Raw content title.
            body:          Raw content body (Markdown).
            target:        Target platform.
            submolt:       Moltbook submolt (only for MOLTBOOK target).
            subreddit:     Reddit subreddit (only for REDDIT target).
            extra_context: Additional context for the optimizer.

        Returns:
            OptimizedContent with platform-adapted title and body.
        """
        specs = PLATFORM_SPECS[target]
        agent = OPTIMIZER_AGENTS[target]
        warnings: list[str] = []

        # ── Apply platform-specific transforms ────────────────────────────
        opt_title = self._optimize_title(title, specs, agent, warnings)
        opt_body = self._optimize_body(body, target, specs, agent, warnings)

        # ── Build metadata ────────────────────────────────────────────────
        metadata: dict[str, Any] = {
            "platform": target.value,
            "agent": agent.name,
            "specs_applied": specs.name,
        }
        if target == Platform.MOLTBOOK:
            metadata["submolt"] = submolt
        elif target == Platform.REDDIT:
            metadata["subreddit"] = subreddit

        return OptimizedContent(
            platform=target,
            original_title=title,
            optimized_title=opt_title,
            optimized_body=opt_body,
            metadata=metadata,
            warnings=warnings,
        )

    def optimize_all(
        self,
        title: str,
        body: str,
        *,
        submolt: str = "general",
        subreddit: str = "",
    ) -> dict[Platform, OptimizedContent]:
        """Optimize content for ALL platforms at once.

        Returns:
            Dict mapping each Platform to its OptimizedContent.
        """
        return {
            platform: self.optimize(
                title, body, platform,
                submolt=submolt, subreddit=subreddit,
            )
            for platform in Platform
        }

    def build_llm_prompt(
        self,
        title: str,
        body: str,
        target: Platform,
        *,
        extra_context: str = "",
    ) -> str:
        """Build a complete LLM prompt for platform-specific optimization.

        Use this to feed to your LLM provider (SovereignLLM, OpenAI, etc.)
        for deep rewriting beyond rule-based transforms.
        """
        agent = OPTIMIZER_AGENTS[target]
        specs = PLATFORM_SPECS[target]

        rules_block = "\n".join(f"  - {r}" for r in agent.transformation_rules)
        format_block = "\n".join(f"  - {r}" for r in agent.formatting_rules)
        hooks_block = "\n".join(f"  - {h}" for h in agent.engagement_hooks)
        anti_block = "\n".join(f"  - {a}" for a in agent.anti_patterns)

        return textwrap.dedent(f"""\
            {agent.system_prompt}

            === PLATFORM CONSTRAINTS ===
            Platform: {specs.name}
            Max title chars: {specs.max_title_chars}
            Max body chars: {specs.max_body_chars}
            Supports markdown: {specs.supports_markdown}
            Supports tables: {specs.supports_tables}
            Optimal reading time: {specs.optimal_reading_time_min[0]}-{specs.optimal_reading_time_min[1]} min
            Tone: {specs.tone_spectrum}

            === TRANSFORMATION RULES ===
            {rules_block}

            === FORMATTING RULES ===
            {format_block}

            === ENGAGEMENT HOOKS (use 1-2) ===
            {hooks_block}

            === ANTI-PATTERNS (avoid ALL) ===
            {anti_block}

            {f'=== EXTRA CONTEXT ==={chr(10)}{extra_context}' if extra_context else ''}

            === ORIGINAL CONTENT ===
            TITLE: {title}

            BODY:
            {body}

            === YOUR TASK ===
            Rewrite the content above optimized for {specs.name}.
            Return in this exact format:

            OPTIMIZED_TITLE: <your optimized title>

            OPTIMIZED_BODY:
            <your optimized body>
        """)

    # ── Private transforms ────────────────────────────────────────────────

    def _optimize_title(
        self,
        title: str,
        specs: PlatformConstraints,
        agent: OptimizerAgent,
        warnings: list[str],
    ) -> str:
        """Apply platform-specific title optimization."""
        opt = title.strip()

        # Truncate if needed
        if specs.max_title_chars > 0 and len(opt) > specs.max_title_chars:
            opt = opt[: specs.max_title_chars - 3].rstrip() + "..."
            warnings.append(
                f"Title truncated from {len(title)} to {specs.max_title_chars} chars"
            )

        # Platform-specific title adjustments
        if specs.name == "X/Twitter":
            # Twitter has no title — return empty, first tweet is the hook
            return ""

        if specs.name == "LinkedIn":
            # LinkedIn: prefer short, punchy titles
            if len(opt) > 80:
                warnings.append(
                    "LinkedIn titles perform best under 80 chars "
                    f"(current: {len(opt)})"
                )

        return opt

    def _optimize_body(
        self,
        body: str,
        target: Platform,
        specs: PlatformConstraints,
        agent: OptimizerAgent,
        warnings: list[str],
    ) -> str:
        """Apply platform-specific body optimization."""
        dispatch: dict[Platform, Any] = {
            Platform.MOLTBOOK: self._transform_moltbook,
            Platform.SUBSTACK: self._transform_substack,
            Platform.TWITTER: self._transform_twitter,
            Platform.REDDIT: self._transform_reddit,
            Platform.LINKEDIN: self._transform_linkedin,
        }
        transformer = dispatch[target]
        opt = transformer(body, warnings)

        # Enforce character limits
        if len(opt) > specs.max_body_chars:
            opt = opt[: specs.max_body_chars - 50] + "\n\n[Content truncated for platform limits]"
            warnings.append(
                f"Body truncated to {specs.max_body_chars} chars for {specs.name}"
            )

        return opt

    def _transform_moltbook(self, body: str, warnings: list[str]) -> str:
        """Moltbook: full markdown, technical depth, question CTA."""
        lines = body.strip().split("\n")
        result: list[str] = []

        for line in lines:
            # Ensure code terms are in backticks
            result.append(line)

        # Add engagement question if missing
        text = "\n".join(result)
        if not text.rstrip().endswith("?"):
            text += "\n\n---\n\n*What's your take on this? Share your perspective below.*"

        return text

    def _transform_substack(self, body: str, warnings: list[str]) -> str:
        """Substack: narrative arc, personal voice, subscriber hooks."""
        text = body.strip()

        # Check for minimum length
        word_count = len(text.split())
        if word_count < 400:
            warnings.append(
                f"Substack posts perform best >800 words (current: ~{word_count}). "
                "Consider expanding the narrative."
            )

        # Add cross-post footer if not present
        if "substack" not in text.lower():
            text += (
                "\n\n---\n\n"
                "*Subscribe for deeper analysis on sovereign AI architecture, "
                "consciousness, and the systems that think about thinking.*"
            )

        return text

    def _transform_twitter(self, body: str, warnings: list[str]) -> str:
        """Twitter: convert long-form to numbered thread."""
        # Extract key sections and insights
        sections = re.split(r"\n##\s+", body.strip())
        tweets: list[str] = []

        # Opening tweet — the banger
        first_section = sections[0].strip()
        first_para = first_section.split("\n\n")[0].strip()
        # Clean markdown
        clean = re.sub(r"[*_`#>\[\]]", "", first_para)
        clean = re.sub(r"\(http[^)]+\)", "", clean)
        clean = clean.strip()

        if len(clean) > 270:
            clean = clean[:267] + "..."

        tweets.append(f"🧵 {clean}")

        # Extract insights from each section
        for section in sections[1:]:
            lines = section.strip().split("\n")
            if not lines:
                continue

            header = lines[0].strip().lstrip("#").strip()
            # Get first substantive paragraph
            content_lines = [
                ln.strip()
                for ln in lines[1:]
                if ln.strip() and not ln.strip().startswith("|") and not ln.strip().startswith("-")
            ]

            if content_lines:
                para = content_lines[0]
                para = re.sub(r"[*_`#>\[\]]", "", para)
                para = re.sub(r"\(http[^)]+\)", "", para)
                tweet = f"{header}:\n\n{para.strip()}"
                if len(tweet) > 280:
                    tweet = tweet[:277] + "..."
                tweets.append(tweet)

        # Cap at 15 tweets
        if len(tweets) > 15:
            tweets = tweets[:14]
            warnings.append("Thread capped at 15 tweets (was longer)")

        # Number the tweets
        total = len(tweets) + 1  # +1 for CTA tweet
        numbered = [
            f"({i + 1}/{total}) {t}" if i > 0 else f"{t} ({1}/{total})"
            for i, t in enumerate(tweets)
        ]

        # Add CTA tweet
        numbered.append(
            f"({total}/{total}) If you found this thread valuable:\n\n"
            "→ Follow @borjamoskv for more\n"
            "→ RT tweet 1 so others find it\n"
            "→ Full article on Substack (link in bio)\n\n"
            "#AI #CORTEX #agents"
        )

        return "\n\n---\n\n".join(numbered)

    def _transform_reddit(self, body: str, warnings: list[str]) -> str:
        """Reddit: TL;DR, community voice, discussion points."""
        text = body.strip()

        # Add TL;DR if missing
        has_tldr = "tl;dr" in text.lower() or "tldr" in text.lower()
        if not has_tldr:
            # Extract first paragraph as TL;DR candidate
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            if paragraphs:
                tldr = paragraphs[0]
                tldr = re.sub(r"[*_`#>]", "", tldr).strip()
                if len(tldr) > 200:
                    tldr = tldr[:197] + "..."
                text = f"**TL;DR:** {tldr}\n\n---\n\n{text}"

        # Add discussion section if missing  
        if "discussion" not in text.lower() and "what do you" not in text.lower():
            text += (
                "\n\n---\n\n"
                "**Discussion:**\n\n"
                "- What's your experience with this?\n"
                "- Any alternative approaches worth considering?\n"
                "- If you've built something similar, what surprised you most?"
            )

        return text

    def _transform_linkedin(self, body: str, warnings: list[str]) -> str:
        """LinkedIn: short, punchy, hook-above-fold."""
        # Strip markdown formatting
        text = body.strip()
        text = re.sub(r"#{1,6}\s+", "", text)  # headers
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # bold
        text = re.sub(r"\*(.+?)\*", r"\1", text)  # italic
        text = re.sub(r"`(.+?)`", r"\1", text)  # code
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)  # links
        text = re.sub(r"^\|.+\|$", "", text, flags=re.MULTILINE)  # tables
        text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)  # hrs
        text = re.sub(r"\n{3,}", "\n\n", text)  # excess newlines

        # Extract key points
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        # Build LinkedIn-style post
        li_parts: list[str] = []

        # Hook (first 2 lines before fold)
        if paragraphs:
            hook = paragraphs[0]
            if len(hook) > 150:
                hook = hook[:147] + "..."
            li_parts.append(hook)

        # Key insights (compressed)
        for para in paragraphs[1:6]:  # Max 5 more paragraphs
            compressed = para
            if len(compressed) > 200:
                compressed = compressed[:197] + "..."
            li_parts.append(compressed)

        # CTA
        li_parts.append(
            "💡 What's your take?\n\n"
            "#AI #agents #CORTEX #sovereignty #engineering"
        )

        result = "\n\n".join(li_parts)

        # Enforce LinkedIn char limit
        if len(result) > 3000:
            result = result[:2950] + "\n\n[...]\n\n#AI #CORTEX #agents"
            warnings.append("LinkedIn post truncated to 3000 chars")

        return result


# ─── Convenience Functions ───────────────────────────────────────────────────


def optimize_for_all(
    title: str,
    body: str,
    *,
    submolt: str = "general",
    subreddit: str = "",
) -> dict[Platform, OptimizedContent]:
    """Quick function: optimize content for all platforms at once."""
    return TextOptimizer().optimize_all(
        title, body, submolt=submolt, subreddit=subreddit,
    )


def optimize_for(
    title: str,
    body: str,
    platform: str | Platform,
    **kwargs: Any,
) -> OptimizedContent:
    """Quick function: optimize content for a single platform."""
    if isinstance(platform, str):
        platform = Platform(platform.lower())
    return TextOptimizer().optimize(title, body, platform, **kwargs)


def get_llm_prompt(
    title: str,
    body: str,
    platform: str | Platform,
    **kwargs: Any,
) -> str:
    """Quick function: get LLM prompt for deeper optimization."""
    if isinstance(platform, str):
        platform = Platform(platform.lower())
    return TextOptimizer().build_llm_prompt(title, body, platform, **kwargs)
