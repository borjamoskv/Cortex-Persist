import React, { useRef, useEffect } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import SpriteText from 'three-spritetext';

export interface GraphNode {
  id: number;
  val: number;
  name: string;
  group: string;
  color: string;
}

export interface GraphLink {
  source: number;
  target: number;
  value: number;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

interface HiveGraphProps {
  data: GraphData;
  onNodeClick?: (node: GraphNode) => void;
}

const HiveGraph: React.FC<HiveGraphProps> = ({ data, onNodeClick }) => {
  const fgRef = useRef<any>(null);

  useEffect(() => {
    // Initial camera orbit
    if (fgRef.current) {
      fgRef.current.d3Force('charge')?.strength(-120);
    }
  }, []);

  return (
    <ForceGraph3D
      ref={fgRef}
      graphData={data}
      nodeLabel="name"
      nodeColor="color"
      nodeVal="val"
      
      // Node appearance
      nodeRelSize={4}
      nodeOpacity={0.9}
      nodeResolution={16}

      // Link appearance
      linkWidth={1}
      linkColor={() => "#444444"}
      linkOpacity={0.3}

      // Text sprites for labels (optional, can be heavy)
      nodeThreeObjectExtend={true}
      nodeThreeObject={(node: any) => {
        const sprite = new SpriteText(node.name);
        sprite.color = node.color;
        sprite.textHeight = 4;
        sprite.position.y = 8; // offset label
        return sprite;
      }}

      // Interaction
      onNodeClick={(node: any) => onNodeClick && onNodeClick(node as GraphNode)}
      
      // Scene
      backgroundColor="#050505"
      showNavInfo={false}
    />
  );
};

export default HiveGraph;
