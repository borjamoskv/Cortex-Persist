#!/usr/bin/env python3
"""
BABYLON-60 / CORTEX: Black-Box Evaluation Harness v1.1

C5 rules:
- TTFT only if true streaming is available; otherwise null.
- Tokens/sec only if provider returns usage.completion_tokens; otherwise null.
- No internal inference claims.
"""

import os, sys, json, time, yaml, hashlib, argparse, statistics, math, re
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import requests

# ---- Protocol thresholds (Section 5) ----
ABORT_RATE_LIMIT_THRESHOLD = 0.05   # 5%
ABORT_FORMAT_FAIL_THRESHOLD = 0.10  # 10%

DEFAULT_TIMEOUT_SEC = 120
DEFAULT_MAX_RETRIES = 3

# ------------------- Data Structures -------------------

@dataclass
class InferenceParams:
    temperature: float = 0.0
    top_p: float = 1.0
    max_output_tokens: int = 1024
    seed: Optional[int] = None
    reasoning_effort: Optional[str] = None

@dataclass
class Provenance:
    model_id: str
    endpoint: str
    adapter: str
    inference_params: InferenceParams
    timestamp_iso: str
    region: str

@dataclass
class SingleResult:
    prompt_sha256: str
    status_code: int
    rejected: bool
    error_type: Optional[str]

    latency_ms: float
    ttft_ms: Optional[float]          # None if not measurable
    completion_tokens: Optional[int]  # None if provider doesn't return
    tokens_per_sec: Optional[float]   # None if completion_tokens None

    json_valid: bool
    exact_match: Optional[bool]       # None if no ground truth provided
    response_text: str
    response_preview: str
    timestamp_iso: str

# ------------------- Utilities -------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def safe_mkdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

# ------------------- Adapter: OpenAI-compatible Chat Completions -------------------

class OpenAIChatCompletionsAdapter:
    """
    Expects an OpenAI-compatible endpoint:
      POST /v1/chat/completions
    Supports:
      - non-stream responses (JSON)
      - stream responses (SSE 'data: {...}')
    """
    def __init__(self, endpoint: str, api_key: str, timeout_sec: int):
        self.endpoint = endpoint
        self.timeout_sec = timeout_sec
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def call_nonstream(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any], float]:
        t0 = time.perf_counter()
        r = requests.post(self.endpoint, headers=self.headers, json=payload, timeout=self.timeout_sec)
        t1 = time.perf_counter()
        latency_ms = (t1 - t0) * 1000.0
        data = {}
        try:
            data = r.json() if r.content else {}
        except Exception:
            data = {}
        return r.status_code, data, latency_ms

    def call_stream(self, payload: Dict[str, Any]) -> Tuple[int, str, Optional[float], float, Dict[str, Any]]:
        """
        Returns:
          status_code, full_text, ttft_ms(or None), total_latency_ms, tail_json(if any)
        """
        t0 = time.perf_counter()
        first_token_t = None
        chunks: List[str] = []
        tail_json: Dict[str, Any] = {}

        r = requests.post(
            self.endpoint,
            headers=self.headers,
            json=payload,
            stream=True,
            timeout=self.timeout_sec,
        )
        status = r.status_code
        if status != 200:
            t1 = time.perf_counter()
            return status, "", None, (t1 - t0) * 1000.0, {}

        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="ignore")
            if not line.startswith("data: "):
                continue
            datum = line[6:]
            if datum.strip() == "[DONE]":
                break
            try:
                obj = json.loads(datum)
                if first_token_t is None:
                    first_token_t = time.perf_counter()
                delta = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if delta:
                    chunks.append(delta)
                tail_json = obj
            except Exception:
                continue

        t1 = time.perf_counter()
        ttft_ms = ((first_token_t - t0) * 1000.0) if first_token_t is not None else None
        return 200, "".join(chunks), ttft_ms, (t1 - t0) * 1000.0, tail_json

## ------------------- Passive Provenance Auditor -------------------

@dataclass
class BaselineProfile:
    """
    Perfil de referencia OPACO. El operador lo calibra contra sus propios
    endpoints conocidos. Deliberadamente NO contiene atribución de proveedor.
    """
    id: str
    features_mean: Dict[str, float]
    features_std: Dict[str, float]
    calibrated_at: float = field(default_factory=time.time)
    sample_size: int = 0  # N de runs usados para calibrar este perfil

# Baselines opacos de ejemplo calibrados. Sin comentarios identificatorios de proveedor.
PROVENANCE_BASELINES = [
    BaselineProfile(
        id="profile_alpha",
        features_mean={"itl_ms": 22.5, "char_ratio": 3.8, "md_density": 0.12, "lexical_bias": 0.04},
        features_std={"itl_ms": 4.2, "char_ratio": 0.3, "md_density": 0.02, "lexical_bias": 0.01},
        calibrated_at=1770000000.0,
        sample_size=100
    ),
    BaselineProfile(
        id="profile_beta",
        features_mean={"itl_ms": 10.2, "char_ratio": 4.2, "md_density": 0.05, "lexical_bias": 0.02},
        features_std={"itl_ms": 2.1, "char_ratio": 0.4, "md_density": 0.01, "lexical_bias": 0.005},
        calibrated_at=1770000000.0,
        sample_size=100
    ),
    BaselineProfile(
        id="profile_gamma",
        features_mean={"itl_ms": 15.8, "char_ratio": 4.0, "md_density": 0.08, "lexical_bias": 0.03},
        features_std={"itl_ms": 3.5, "char_ratio": 0.2, "md_density": 0.03, "lexical_bias": 0.008},
        calibrated_at=1770000000.0,
        sample_size=100
    )
]

class ProvenanceAuditor:
    """
    Auditor de consistencia de endpoint basado en firmas pasivas.

    Usos soportados (C4-C5 según el componente):
      - drift detection (¿cambió el comportamiento del mismo endpoint?)
      - clustering anónimo
      - regression testing
      - consistency auditing

    NO soportado sin validación etiquetada:
      - atribución de proveedor/modelo/checkpoint exacto
      - claims numéricos de precisión
    """

    DEFAULT_WEIGHTS = {
        "itl_ms": 0.1,
        "char_ratio": 1.0,
        "md_density": 10.0,
        "lexical_bias": 50.0,
    }

    def __init__(
        self,
        baselines: List[BaselineProfile],
        weights: Optional[Dict[str, float]] = None,
        jitter_baseline_ms: float = 0.0,  # latencia de red de referencia a restar
    ):
        self.baselines = baselines
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)
        self.jitter_baseline_ms = max(jitter_baseline_ms, 0.0)
        self.lexical_targets = {
            "certainly": 1.0, "delve": 1.2, "tapestry": 1.2,
            "however": 0.5, "cannot": 0.6,
        }

    def _compute_lexical_bias(self, text: str) -> float:
        if not text:
            return 0.0
        words = re.findall(r"[a-zA-Z]+", text.lower())
        if not words:
            return 0.0
        score = sum(self.lexical_targets.get(w, 0.0) for w in words)
        return score / len(words)

    def _extract_features(self, results: List[SingleResult]) -> Optional[Dict[str, float]]:
        valid = [r for r in results if r.status_code == 200 and not r.rejected]
        if not valid:
            return None

        itl_vals, ratio_vals, md_vals, bias_vals = [], [], [], []

        for r in valid:
            tokens = max(r.completion_tokens or 1, 1)
            ttft = r.ttft_ms or 0.0
            latency = r.latency_ms

            if tokens > 1 and latency > ttft:
                # Normalización de jitter: resta la latencia de red de referencia
                itl = ((latency - ttft) / tokens) - self.jitter_baseline_ms
                itl_vals.append(max(itl, 0.0))

            text = r.response_text or ""
            if text:
                ratio_vals.append(len(text) / tokens)
                md = sum(1 for c in text if c in "#*-`") / max(len(text), 1)
                md_vals.append(md)
                bias_vals.append(self._compute_lexical_bias(text))

        def mean(xs):
            return sum(xs) / len(xs) if xs else 0.0

        return {
            "itl_ms": mean(itl_vals),
            "char_ratio": mean(ratio_vals),
            "md_density": mean(md_vals),
            "lexical_bias": mean(bias_vals),
        }

    def analyze(self, results: List[SingleResult]) -> Dict[str, Any]:
        obs = self._extract_features(results)
        if obs is None:
            return {
                "status": "insufficient_data",
                "identity_claim": "not_supported"
            }

        if not self.baselines:
            return {
                "status": "no_baselines",
                "observed_vector": obs,
                "note": "Signature computed; no calibrated baselines configured.",
                "identity_claim": "not_supported"
            }

        distances = {}
        for p in self.baselines:
            d_sq = 0.0
            for k in obs:
                if k not in p.features_mean or k not in p.features_std:
                    continue  # Evita contaminación por inconsistencia de dimensiones
                obs_val = obs[k]
                ref_mean = p.features_mean[k]
                ref_std = max(p.features_std[k], 1e-6)  # Prevent division by zero
                # Normalización dimensional empírica (Mahalanobis-style distance per axis)
                diff_norm = (obs_val - ref_mean) / ref_std
                d_sq += self.weights.get(k, 1.0) * (diff_norm ** 2)
            distances[p.id] = math.sqrt(d_sq)

        # Softmax con traslación log-sum-exp para estabilidad numérica extrema
        min_dist = min(distances.values()) if distances else 0.0
        raw = {k: math.exp(-(v - min_dist)) for k, v in distances.items()}
        total = sum(raw.values()) or 1.0
        similarities = {k: round(v / total, 4) for k, v in raw.items()}
        nearest = min(distances, key=distances.get)

        return {
            "status": "ok",
            "observed_vector": obs,
            "nearest_profile": nearest,
            "distances": {k: round(v, 4) for k, v in distances.items()},
            "similarity_scores": similarities,  # heurístico, no probabilidad calibrada
            "identity_claim": "not_supported"
        }

# ------------------- Evaluator -------------------

class BlackBoxHarness:
    def __init__(self, cfg: Dict[str, Any]):
        self.endpoint = cfg["endpoint_url"]
        self.model_id = cfg["model_id"]
        self.region = cfg.get("region", "unknown")
        self.adapter_name = cfg.get("adapter", "openai_chat_completions")

        api_key = cfg.get("api_key")
        if api_key and api_key.startswith("${") and api_key.endswith("}"):
            api_key = os.getenv(api_key[2:-1])
        if not api_key:
            raise SystemExit("api_key missing (direct value or ${ENV_VAR}).")

        ip = cfg.get("inference_params", {}) or {}
        self.params = InferenceParams(
            temperature=float(ip.get("temperature", 0.0)),
            top_p=float(ip.get("top_p", 1.0)),
            max_output_tokens=int(ip.get("max_output_tokens", 1024)),
            seed=ip.get("seed", None),
            reasoning_effort=ip.get("reasoning_effort", None),
        )

        self.timeout_sec = int(cfg.get("timeout_sec", DEFAULT_TIMEOUT_SEC))
        self.max_retries = int(cfg.get("max_retries", DEFAULT_MAX_RETRIES))
        self.workers = int(cfg.get("eval_workers", 4))
        self.expect_json = bool(cfg.get("expect_json", False))

        if self.adapter_name != "openai_chat_completions":
            raise SystemExit(f"Unsupported adapter: {self.adapter_name}")

        self.adapter = OpenAIChatCompletionsAdapter(self.endpoint, api_key, self.timeout_sec)

        self.total_calls = 0
        self.rate_limit_429 = 0
        self.format_fail = 0

    def provenance(self) -> Provenance:
        return Provenance(
            model_id=self.model_id,
            endpoint=self.endpoint,
            adapter=self.adapter_name,
            inference_params=self.params,
            timestamp_iso=now_iso(),
            region=self.region,
        )

    def _build_payload(self, prompt: str, stream: bool) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.params.temperature,
            "top_p": self.params.top_p,
            "max_tokens": self.params.max_output_tokens,
            "stream": stream,
        }
        if self.params.seed is not None:
            payload["seed"] = self.params.seed
        if self.params.reasoning_effort is not None:
            payload["reasoning_effort"] = self.params.reasoning_effort
        return payload

    def _extract_text_usage(self, data: Dict[str, Any]) -> Tuple[str, Optional[int]]:
        try:
            text = data["choices"][0]["message"]["content"]
        except Exception:
            text = ""
        completion_tokens = None
        try:
            completion_tokens = int(data.get("usage", {}).get("completion_tokens"))
        except Exception:
            completion_tokens = None
        return text, completion_tokens

    def run_prompt(self, prompt: str, ground_truth: Optional[str], force_stream: bool) -> SingleResult:
        self.total_calls += 1
        p_hash = sha256_hex(prompt)
        tstamp = now_iso()

        for attempt in range(self.max_retries + 1):
            try:
                if force_stream:
                    payload = self._build_payload(prompt, stream=True)
                    status, text, ttft_ms, latency_ms, _tail = self.adapter.call_stream(payload)
                    completion_tokens = None 
                else:
                    payload = self._build_payload(prompt, stream=False)
                    status, data, latency_ms = self.adapter.call_nonstream(payload)
                    text, completion_tokens = self._extract_text_usage(data)
                    ttft_ms = None

                if status == 429:
                    self.rate_limit_429 += 1
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue

                rejected = status != 200
                error_type = None if status == 200 else f"HTTP_{status}"

                json_valid = False
                if self.expect_json:
                    try:
                        json.loads(text)
                        json_valid = True
                    except Exception:
                        json_valid = False
                        self.format_fail += 1

                exact_match = None
                if ground_truth is not None:
                    exact_match = (text.strip() == ground_truth.strip())

                tps = None
                if completion_tokens is not None and latency_ms > 0:
                    tps = completion_tokens / (latency_ms / 1000.0)

                return SingleResult(
                    prompt_sha256=p_hash,
                    status_code=status,
                    rejected=rejected,
                    error_type=error_type,
                    latency_ms=round(latency_ms, 2),
                    ttft_ms=(round(ttft_ms, 2) if ttft_ms is not None else None),
                    completion_tokens=completion_tokens,
                    tokens_per_sec=(round(tps, 3) if tps is not None else None),
                    json_valid=json_valid if self.expect_json else False,
                    exact_match=exact_match,
                    response_text=text,
                    response_preview=text[:200],
                    timestamp_iso=tstamp,
                )

            except requests.exceptions.Timeout:
                return SingleResult(
                    prompt_sha256=p_hash, status_code=0, rejected=True, error_type="TIMEOUT",
                    latency_ms=0.0, ttft_ms=None, completion_tokens=None, tokens_per_sec=None,
                    json_valid=False, exact_match=None, response_text="", response_preview="", timestamp_iso=tstamp
                )
            except requests.exceptions.ConnectionError:
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                return SingleResult(
                    prompt_sha256=p_hash, status_code=0, rejected=True, error_type="CONNECTION_ERROR",
                    latency_ms=0.0, ttft_ms=None, completion_tokens=None, tokens_per_sec=None,
                    json_valid=False, exact_match=None, response_text="", response_preview="", timestamp_iso=tstamp
                )

        raise RuntimeError("retry loop escaped")

    def abort_flags(self) -> Dict[str, Any]:
        total = max(self.total_calls, 1)
        rate_limit_rate = self.rate_limit_429 / total
        format_fail_rate = self.format_fail / total if self.expect_json else 0.0
        should_abort = (rate_limit_rate > ABORT_RATE_LIMIT_THRESHOLD) or (format_fail_rate > ABORT_FORMAT_FAIL_THRESHOLD)
        return {
            "total_calls": self.total_calls,
            "rate_limit_429": self.rate_limit_429,
            "rate_limit_rate": round(rate_limit_rate, 4),
            "format_failures": self.format_fail,
            "format_fail_rate": round(format_fail_rate, 4),
            "should_abort": should_abort,
        }

# ------------------- Main -------------------

def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--output", default="eval_report.json")
    ap.add_argument("--stream_ttft", action="store_true", help="Attempt streaming to measure TTFT.")
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    required = ["endpoint_url", "api_key", "model_id"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise SystemExit(f"Missing config keys: {missing}")

    harness = BlackBoxHarness(cfg)
    prov = harness.provenance()

    axes: Dict[str, Any] = {}
    abort_global = False

    eval_axes: Dict[str, List[Any]] = cfg.get("eval_axes", {})
    if not eval_axes:
        raise SystemExit("eval_axes empty.")

    for axe_name, items in eval_axes.items():
        results: List[SingleResult] = []
        for item in items:
            if isinstance(item, str):
                prompt = item
                gt = None
            elif isinstance(item, dict):
                prompt = item["prompt"]
                gt = item.get("ground_truth")
            else:
                raise SystemExit(f"Bad eval_axes item type in {axe_name}: {type(item)}")

            r = harness.run_prompt(prompt, gt, force_stream=bool(args.stream_ttft))
            results.append(r)

        ok = [x for x in results if x.status_code == 200 and not x.rejected]
        latency = [x.latency_ms for x in ok]
        tps = [x.tokens_per_sec for x in ok if x.tokens_per_sec is not None]
        ttft = [x.ttft_ms for x in ok if x.ttft_ms is not None]

        agg = {
            "n": len(results),
            "success_rate": round((len(ok) / len(results)), 4),
            "latency_avg_ms": round(statistics.mean(latency), 2) if latency else None,
            "latency_p50_ms": round(statistics.median(latency), 2) if latency else None,
            "tokens_per_sec_avg": round(statistics.mean(tps), 3) if tps else None,
            "ttft_avg_ms": round(statistics.mean(ttft), 2) if ttft else None,
        }

        auditor = ProvenanceAuditor(PROVENANCE_BASELINES)
        provenance_data = auditor.analyze(results)

        axes[axe_name] = {
            "provenance": asdict(prov),
            "aggregated_metrics": agg,
            "provenance_signature": provenance_data,
            "results": [asdict(x) for x in results],
        }

        flags = harness.abort_flags()
        if flags["should_abort"]:
            axes[axe_name]["abort_flags"] = flags
            abort_global = True
            break
        else:
            axes[axe_name]["abort_flags"] = flags

    final = {
        "protocol": "BABYLON-60/CORTEX-BlackBox-v1.1",
        "timestamp_iso": now_iso(),
        "abort_triggered": abort_global,
        "axes": axes,
    }

    blob = json.dumps(final, sort_keys=True, ensure_ascii=False).encode("utf-8")
    final["report_sha256"] = hashlib.sha256(blob).hexdigest()

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    if abort_global:
        sys.exit(1)

if __name__ == "__main__":
    main()
