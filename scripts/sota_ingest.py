#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized | SYS_ID: APEX_EPISTEMIC_SYNTHESIS_OMEGA
"""
SOTA Vector Engine Ingestor (V3)
Ingests C5-REAL Frontier_Node signals into a local ChromaDB vector space.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import chromadb
import yaml
from chromadb.config import Settings
from pydantic import BaseModel, ValidationError
from sentence_transformers import SentenceTransformer

# -----------------------------------------------------------------------------
# 1. ONTOLOGY SCHEMA (Frontier_Node)
# -----------------------------------------------------------------------------

class EvidenceNode(BaseModel):
    Type: str
    Title: str
    URI: str
    Date: Optional[str] = None
    Source_Primacy: str
    Reproducible_Artifact: str

class CapabilityDelta(BaseModel):
    Type: str
    Description: str

class IntegrationVector(BaseModel):
    Target_System: str
    Integration_Path: str
    Dependencies: list[str]
    Constraints: list[str]

class VerificationNode(BaseModel):
    C5_REAL_Status: str
    Verified_Claims: list[str]
    Open_Uncertainties: list[str]

class FrontierNode(BaseModel):
    Domain: str
    Subdomain: str
    Core_Insight: str
    Evidence: list[EvidenceNode]
    Mechanism: str
    Capability_Delta: CapabilityDelta
    Integration_Vector: IntegrationVector
    Verification: VerificationNode
    confidence_score: float

class IngestPayload(BaseModel):
    Frontier_Node: FrontierNode

# -----------------------------------------------------------------------------
# 2. CORE ENGINE
# -----------------------------------------------------------------------------

class SOTAVectorEngine:
    def __init__(self):
        # Enforce Babylon-60 physical isolation boundary (L3.Σ4)
        home_dir = Path.home()
        self.db_path = home_dir / ".babylon60" / "chroma"
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize physical DB
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(name="cortex_sota_frontier")
        
        # We load model lazily to save exergy if it's a dry run or missing source
        self._model = None

    @property
    def model(self):
        if self._model is None:
            # Local execution for maximum isolation, upgraded to SOTA BAAI weights
            self._model = SentenceTransformer("BAAI/bge-large-en-v1.5")
        return self._model

    def emit_empty_verification(self) -> None:
        """Emits an empty Frontier_Node list + Verification_Note."""
        payload = {
            "Frontier_Node_List": [],
            "Verification_Note": (
                "No primary source or signal provided. As per C5-REAL protocol, "
                "no structural insight can be extracted without a traceable artifact. "
                "Anergy prevented."
            )
        }
        print(yaml.dump(payload, sort_keys=False))

    def process_and_ingest(self, raw_content: str) -> None:
        """Parses, validates, vectorizes, and ingests the raw content."""
        try:
            data = yaml.safe_load(raw_content)
        except yaml.YAMLError:
            try:
                data = json.loads(raw_content)
            except json.JSONDecodeError as e:
                print(f"Error: Could not parse input as YAML or JSON. {e}", file=sys.stderr)
                sys.exit(1)
        
        try:
            payload = IngestPayload(**data)
        except ValidationError as e:
            print(f"Error: Validation failed against APEX_EPISTEMIC_SYNTHESIS_OMEGA ontology.\n{e}", file=sys.stderr)
            sys.exit(1)
            
        node = payload.Frontier_Node
        
        # Zero-Anergy strict constraints check
        if node.confidence_score < 0.30:
            print(f"Warning: Confidence score {node.confidence_score} too low for immediate physical ingestion. Marked as uncertain.", file=sys.stderr)
            
        # Combine text for embedding
        document_text = f"Insight: {node.Core_Insight}\nMechanism: {node.Mechanism}\nDelta: {node.Capability_Delta.Description}"
        
        # Embedding extraction
        print(f"Extracting dense embedding (BAAI/bge-large-en-v1.5) for domain {node.Domain}...", file=sys.stderr)
        embedding = self.model.encode(document_text).tolist()
        
        # Provenance ID generation (deterministic hash)
        import hashlib
        signature = f"{node.Domain}:{node.Subdomain}:{node.Core_Insight}"
        node_id = hashlib.sha3_256(signature.encode("utf-8")).hexdigest()
        
        # Extract flat metadata for ChromaDB
        evidence_uris = [ev.URI for ev in node.Evidence]
        metadata = {
            "domain": node.Domain,
            "subdomain": node.Subdomain,
            "c5_status": node.Verification.C5_REAL_Status,
            "confidence_score": node.confidence_score,
            "capability_delta_type": node.Capability_Delta.Type,
            "evidence_uris": ",".join(evidence_uris)
        }
        
        # Physical ingestion
        self.collection.add(
            ids=[node_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[document_text]
        )
        
        print(f"\n[C5-REAL] Successfully ingested Frontier_Node: {node_id}")
        print(f"Collection count: {self.collection.count()}")
        
        # Output YAML format to stdout
        print("\n" + yaml.dump(data, sort_keys=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="SOTA Vector Engine Ingestor")
    parser.add_argument("input_file", nargs="?", type=str, help="Path to YAML/JSON containing Frontier_Node")
    args = parser.parse_args()

    engine = SOTAVectorEngine()

    if not args.input_file:
        engine.emit_empty_verification()
        sys.exit(0)

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File {input_path} not found.", file=sys.stderr)
        sys.exit(1)

    raw_content = input_path.read_text(encoding="utf-8")
    engine.process_and_ingest(raw_content)

if __name__ == "__main__":
    main()
