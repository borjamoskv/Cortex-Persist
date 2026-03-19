import json
import logging
from typing import Any

try:
    from mlx_lm import generate, load
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False


logger = logging.getLogger(__name__)


class LocalSDFPipeline:
    """
    Sovereign Data Format (SDF) Classification and Extraction Engine.
    
    Uses MLX (Apple Silicon) to run small, structurally-tuned local LLMs
    (e.g., 1.5B for classification, 3B for extraction) with zero API costs
    and high thermodynamic efficiency (Shannon Compaction).
    """
    
    def __init__(
        self, 
        classify_model_id: str = "borjamoskv/sdf-classify-qwen1.5b-q4", # Placeholder for actual repo
        extract_model_id: str = "borjamoskv/sdf-extract-smollm3b-q4",    # Placeholder for actual repo
        lazy_load: bool = True
    ):
        if not MLX_AVAILABLE:
            raise ImportError(
                "mlx-lm is required for LocalSDFPipeline. "
                "Install it with: pip install mlx-lm"
            )
            
        self.classify_model_id = classify_model_id
        self.extract_model_id = extract_model_id
        
        self._classify_model = None
        self._classify_tokenizer = None
        self._extract_model = None
        self._extract_tokenizer = None
        
        if not lazy_load:
            self._load_classify()
            self._load_extract()
            
    def _load_classify(self):
        if self._classify_model is None:
            logger.info("Loading SDF Classify Model: %s", self.classify_model_id)
            self._classify_model, self._classify_tokenizer = load(self.classify_model_id)
            
    def _load_extract(self):
        if self._extract_model is None:
            logger.info("Loading SDF Extract Model: %s", self.extract_model_id)
            self._extract_model, self._extract_tokenizer = load(self.extract_model_id)

    def classify(self, text: str) -> str:
        """Runs the 1.5B model to categorize the raw text into one of the 50+ subtypes."""
        self._load_classify()
        
        # Simple instruction wrapper for the classify task
        prompt = f"<|im_start|>system\nYou are a classification AI. Reply only with the Category ID.<|im_end|>\n<|im_start|>user\nClassify this:\n{text}<|im_end|>\n<|im_start|>assistant\n"
        
        response = generate(
            self._classify_model, 
            self._classify_tokenizer, 
            prompt=prompt, 
            max_tokens=64,
            verbose=False
        )
        return response.strip()

    def extract(self, text: str, category: str) -> dict[str, Any]:
        """Runs the 3B model to extract structured data based on the category."""
        self._load_extract()
        
        prompt = f"<|im_start|>system\nYou are an extraction AI. Extract the data as JSON for category: {category}. Reply ONLY with raw JSON.<|im_end|>\n<|im_start|>user\nText:\n{text}<|im_end|>\n<|im_start|>assistant\n{{"
        
        response = generate(
            self._extract_model, 
            self._extract_tokenizer, 
            prompt=prompt, 
            max_tokens=1024,
            verbose=False
        )
        
        # mlx_lm generation doesn't auto-include the prompt's trailing character if we stop early, 
        # so we prepend the '{' back to parse it safely.
        raw_json = "{" + response.strip()
        
        # Cleanup potential trailing markdown tags (e.g. if the model hallucinates ```)
        raw_json = raw_json.replace("`", "").strip()
        
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError as e:
            logger.error("SDF Extract failed to produce valid JSON: %s\nRaw output: %s", e, raw_json)
            # Fallback or strict drop according to Maxwell Demon rules
            return {"error": "Invalid schema extraction", "raw": raw_json}

    def process(self, text: str) -> dict[str, Any] | None:
        """
        Full Shannon Compaction pipeline:
        Raw Text -> Classify (1.5B) -> Extract (3B) -> Structured Dict
        """
        category = self.classify(text)
        if not category or category.lower() in ("unknown", "none"):
            logger.warning("SDF Classify rejected the text. Dropping.")
            return None
            
        data = self.extract(text, category)
        
        # Inject metadata about the extraction provenance
        if "error" not in data:
            data["_sdf_meta"] = {
                "category": category,
                "engine": "mlx",
                "extracted_by": self.extract_model_id
            }
            
        return data

