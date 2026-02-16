const API_URL = 'http://localhost:8000';
const DEFAULT_KEY = 'ctx_bootstrap_key'; // Fallback for local dev

export interface Node {
  id: number;
  val: number;
  name: string;
  group: string;
  color: string;
}

export interface Link {
  source: number;
  target: number;
  value: number;
}

export interface GraphData {
  nodes: Node[];
  links: Link[];
}

export interface Fact {
  id: number;
  content: string;
  project: string;
  fact_type: string;
  tags: string[];
  created_at?: string;
}

const getHeaders = () => ({
    'Authorization': `Bearer ${localStorage.getItem('cortex_key') || DEFAULT_KEY}`,
    'Content-Type': 'application/json'
});

export const fetchGraphData = async (): Promise<GraphData> => {
  const response = await fetch(`${API_URL}/hive/graph?limit=500`, {
      headers: getHeaders()
  });
  if (!response.ok) {
    throw new Error('Failed to fetch graph data');
  }
  return response.json();
};

export const searchFacts = async (query: string, project: string = 'cortex', limit: number = 10): Promise<Fact[]> => {
  const response = await fetch(`${API_URL}/v1/search?query=${encodeURIComponent(query)}&project=${project}&limit=${limit}`, {
      headers: getHeaders()
  });
  if (!response.ok) {
    throw new Error('Failed to search facts');
  }
  return response.json();
};
