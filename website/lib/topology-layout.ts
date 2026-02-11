// Topology layout algorithm — pure function, no React/DOM dependencies.
// Kahn's algorithm for topological sort + layered coordinate assignment.

export interface TaskNode {
  id: string;
  title: string;
  assigneeId: string;
  prerequisites: string[];
}

export interface LayoutNode extends TaskNode {
  layer: number;
  x: number;
  y: number;
}

export interface LayoutEdge {
  from: string;
  to: string;
}

export interface TopologyLayout {
  nodes: LayoutNode[];
  edges: LayoutEdge[];
  width: number;
  height: number;
}

/**
 * Compute a layered DAG layout using Kahn's topological sort.
 * Returns null if a cycle is detected.
 */
export function computeTopologyLayout(
  tasks: TaskNode[],
  layerWidth: number = 200,
  nodeHeight: number = 100,
): TopologyLayout | null {
  const idSet = new Set(tasks.map((t) => t.id));
  const inDegree = new Map<string, number>();
  const children = new Map<string, string[]>();

  for (const t of tasks) {
    inDegree.set(t.id, 0);
    children.set(t.id, []);
  }

  // Build adjacency & in-degree from prerequisites
  for (const t of tasks) {
    for (const pre of t.prerequisites) {
      if (!idSet.has(pre)) continue; // skip unknown refs
      inDegree.set(t.id, (inDegree.get(t.id) ?? 0) + 1);
      children.get(pre)!.push(t.id);
    }
  }

  // Kahn's BFS — assign layers
  const layer = new Map<string, number>();
  const queue: string[] = [];

  for (const [id, deg] of inDegree) {
    if (deg === 0) queue.push(id);
  }

  let processed = 0;
  while (queue.length > 0) {
    const id = queue.shift()!;
    processed++;
    for (const child of children.get(id)!) {
      const newDeg = inDegree.get(child)! - 1;
      inDegree.set(child, newDeg);
      // child's layer = max of all prerequisite layers + 1
      const parentLayer = layer.get(id) ?? 0;
      layer.set(child, Math.max(layer.get(child) ?? 0, parentLayer + 1));
      if (newDeg === 0) queue.push(child);
    }
    if (!layer.has(id)) layer.set(id, 0);
  }

  // Cycle detected
  if (processed !== tasks.length) return null;

  // Group by layer, sort within layer by assigneeId for clustering
  const taskMap = new Map(tasks.map((t) => [t.id, t]));
  const layers = new Map<number, TaskNode[]>();
  let maxLayer = 0;

  for (const t of tasks) {
    const l = layer.get(t.id)!;
    if (l > maxLayer) maxLayer = l;
    if (!layers.has(l)) layers.set(l, []);
    layers.get(l)!.push(t);
  }

  // Sort each layer by assigneeId so same-assignee nodes are adjacent
  for (const [, group] of layers) {
    group.sort((a, b) => a.assigneeId.localeCompare(b.assigneeId));
  }

  // Compute coordinates
  let maxNodesInLayer = 0;
  const nodes: LayoutNode[] = [];

  for (let l = 0; l <= maxLayer; l++) {
    const group = layers.get(l) ?? [];
    if (group.length > maxNodesInLayer) maxNodesInLayer = group.length;
    for (let i = 0; i < group.length; i++) {
      const t = group[i];
      nodes.push({
        ...t,
        layer: l,
        x: l * layerWidth,
        y: i * nodeHeight,
      });
    }
  }

  // Edges from all prerequisites
  const edges: LayoutEdge[] = [];
  for (const t of tasks) {
    for (const pre of t.prerequisites) {
      if (idSet.has(pre)) {
        edges.push({ from: pre, to: t.id });
      }
    }
  }

  return {
    nodes,
    edges,
    width: (maxLayer + 1) * layerWidth,
    height: maxNodesInLayer * nodeHeight,
  };
}
