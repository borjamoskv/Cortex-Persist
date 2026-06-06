-- Migration: 018_temporal_kg
-- Description: Add decay_half_life to facts and confidence/agent_id to causal_edges for Temporal Knowledge Graph.

-- Add decay_half_life to facts
ALTER TABLE facts ADD COLUMN decay_half_life REAL DEFAULT 30.0;

-- Add confidence and agent_id to causal_edges
ALTER TABLE causal_edges ADD COLUMN confidence REAL DEFAULT 1.0;
ALTER TABLE causal_edges ADD COLUMN agent_id TEXT;
