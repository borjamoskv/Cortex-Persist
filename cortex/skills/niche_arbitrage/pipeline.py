from cortex.scraper.engine import ScraperEngine
from cortex.scraper.models import ExtractionStrategy, ScrapeRequest, ScrapeResult

# Depending on existing LLM integrations, we will try to use Instructor or directly the LLM gateway.
# Assuming standard CORTEX gateway interaction here for Pydantic structuring.
# If CORTEX has a different structured output method, this should be adapted.
try:
    import instructor
    from openai import AsyncOpenAI

    from cortex.gateway.adapters.openai_spoof import OpenAISpoofAdapter  # Example
except ImportError:
    instructor = None

from .models import NicheTarget, TrendSignal, MarketReport


class NicheArbitrageEngine:
    """Orchestrates scraping and synthesis for Niche Arbitrage."""
    
    def __init__(self, llm_client=None):
        self.scraper = ScraperEngine()
        self.llm_client = llm_client
        if not self.llm_client and instructor:
            # Fallback to default async client with instructor
            self.llm_client = instructor.from_openai(AsyncOpenAI())

    async def run_pipeline(self, target: NicheTarget) -> MarketReport:
        """Runs the fully autonomous pipeline for a given target."""
        
        # 1. Extraction (Scraping)
        scrape_req = ScrapeRequest(url=target.url, strategy=ExtractionStrategy.AUTO)
        scrape_result: ScrapeResult = await self.scraper.scrape(scrape_req)
        
        if not scrape_result.success or not scrape_result.markdown:
            return MarketReport(
                target_name=target.name,
                summary=f"FAILED EXTRACTION: {scrape_result.error}",
                signals=[]
            )
            
        # 2. Synthesis (LLM extraction of TrendSignals)
        report = await self.synthesize_signals(target.name, scrape_result.markdown)
        return report

    async def synthesize_signals(self, target_name: str, raw_markdown: str) -> MarketReport:
        """Uses structured LLM output to extract market signals with exergy scoring."""
        if not self.llm_client:
            raise RuntimeError("LLM Client not configured for synthesis.")
            
        # We process in chunks if markdown is too large, but for now we assume it fits in context.
        # This uses the CORTEX structural rigor (Axiom Ω₃) to enforce the MarketReport schema.
        
        system_prompt = (
            "You are a Sovereign Arbitrage Agent analyzing raw web extractions. "
            "Your goal is to extract actionable market inefficiencies, trends, or user complaints "
            "that can be monetized or arbitraged. "
            "Apply thermodynamic rigor: only return signals with high 'exergy' (useful work/value). "
            "Ignore noise, pleasantries, and generic information. "
            "Fill the proposed_arbitrage field with a concrete mechanism to extract value."
        )
        
        try:
            # Ensure we don't blow up context limit - naive truncation for demo
            max_chars = 60000 
            content_to_analyze = raw_markdown[:max_chars]
            
            report = await self.llm_client.chat.completions.create(
                model="gpt-4o", # Model policy: "high tier"
                response_model=MarketReport,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this extraction from {target_name}:\n\n{content_to_analyze}"}
                ]
            )
            
            # Ensure target name is set correctly
            report.target_name = target_name
            return report
            
        except Exception as e:
            # Fallback report on error
            return MarketReport(
                target_name=target_name,
                summary=f"LLM Synthesis Failed: {str(e)}",
                signals=[]
            )
