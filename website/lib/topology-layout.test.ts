/**
 * Topology layout algorithm validation script.
 * Run: npx tsx lib/topology-layout.test.ts
 *
 * No test framework required — uses plain assertions.
 */
import { computeTopologyLayout, TaskNode } from "./topology-layout";

let passed = 0;
let failed = 0;

function assert(condition: boolean, msg: string) {
  if (condition) {
    passed++;
    console.log(`  PASS: ${msg}`);
  } else {
    failed++;
    console.error(`  FAIL: ${msg}`);
  }
}

function test(name: string, fn: () => void) {
  console.log(`\n${name}`);
  fn();
}

// ─── Test 1: Linear chain A → B → C ───

test("1. Linear chain: A → B → C", () => {
  const tasks: TaskNode[] = [
    { id: "A", title: "Task A", assigneeId: "u1", prerequisites: [] },
    { id: "B", title: "Task B", assigneeId: "u1", prerequisites: ["A"] },
    { id: "C", title: "Task C", assigneeId: "u1", prerequisites: ["B"] },
  ];
  const result = computeTopologyLayout(tasks);
  assert(result !== null, "should not be null");
  if (!result) return;

  const nodeMap = new Map(result.nodes.map((n) => [n.id, n]));
  assert(nodeMap.get("A")!.layer === 0, "A is layer 0");
  assert(nodeMap.get("B")!.layer === 1, "B is layer 1");
  assert(nodeMap.get("C")!.layer === 2, "C is layer 2");
  assert(result.edges.length === 2, "2 edges (A→B, B→C)");
  assert(result.width === 3 * 200, "width = 3 layers * 200");
  assert(result.height === 1 * 100, "height = 1 node per layer * 100");
});

// ─── Test 2: Fan-out A → [B, C, D] ───

test("2. Fan-out: A → [B, C, D]", () => {
  const tasks: TaskNode[] = [
    { id: "A", title: "Task A", assigneeId: "u1", prerequisites: [] },
    { id: "B", title: "Task B", assigneeId: "u1", prerequisites: ["A"] },
    { id: "C", title: "Task C", assigneeId: "u2", prerequisites: ["A"] },
    { id: "D", title: "Task D", assigneeId: "u3", prerequisites: ["A"] },
  ];
  const result = computeTopologyLayout(tasks);
  assert(result !== null, "should not be null");
  if (!result) return;

  const nodeMap = new Map(result.nodes.map((n) => [n.id, n]));
  assert(nodeMap.get("A")!.layer === 0, "A is layer 0");
  assert(nodeMap.get("B")!.layer === 1, "B is layer 1");
  assert(nodeMap.get("C")!.layer === 1, "C is layer 1");
  assert(nodeMap.get("D")!.layer === 1, "D is layer 1");
  assert(result.edges.length === 3, "3 edges");
  assert(result.width === 2 * 200, "width = 2 layers * 200");
  assert(result.height === 3 * 100, "height = 3 nodes in layer 1 * 100");

  // Same-layer Y coordinates must not overlap
  const layer1Ys = result.nodes
    .filter((n) => n.layer === 1)
    .map((n) => n.y);
  const uniqueYs = new Set(layer1Ys);
  assert(uniqueYs.size === 3, "3 unique Y values in layer 1 (no overlap)");
});

// ─── Test 3: Diamond dependency [A, B] → C ───

test("3. Diamond: [A, B] → C", () => {
  const tasks: TaskNode[] = [
    { id: "A", title: "Task A", assigneeId: "u1", prerequisites: [] },
    { id: "B", title: "Task B", assigneeId: "u2", prerequisites: [] },
    { id: "C", title: "Task C", assigneeId: "u1", prerequisites: ["A", "B"] },
  ];
  const result = computeTopologyLayout(tasks);
  assert(result !== null, "should not be null");
  if (!result) return;

  const nodeMap = new Map(result.nodes.map((n) => [n.id, n]));
  assert(nodeMap.get("A")!.layer === 0, "A is layer 0");
  assert(nodeMap.get("B")!.layer === 0, "B is layer 0");
  assert(nodeMap.get("C")!.layer === 1, "C is layer 1");
  assert(result.edges.length === 2, "2 edges (A→C, B→C)");

  // Layer 0 nodes should have different Y
  const layer0Ys = result.nodes
    .filter((n) => n.layer === 0)
    .map((n) => n.y);
  assert(new Set(layer0Ys).size === 2, "layer 0 nodes have distinct Y");
});

// ─── Test 4: Parallel + merge [A, B] → C → D ───

test("4. Parallel + merge: [A, B] → C → D", () => {
  const tasks: TaskNode[] = [
    { id: "A", title: "Task A", assigneeId: "u1", prerequisites: [] },
    { id: "B", title: "Task B", assigneeId: "u2", prerequisites: [] },
    { id: "C", title: "Task C", assigneeId: "u1", prerequisites: ["A", "B"] },
    { id: "D", title: "Task D", assigneeId: "u2", prerequisites: ["C"] },
  ];
  const result = computeTopologyLayout(tasks);
  assert(result !== null, "should not be null");
  if (!result) return;

  const nodeMap = new Map(result.nodes.map((n) => [n.id, n]));
  assert(nodeMap.get("A")!.layer === 0, "A is layer 0");
  assert(nodeMap.get("B")!.layer === 0, "B is layer 0");
  assert(nodeMap.get("C")!.layer === 1, "C is layer 1");
  assert(nodeMap.get("D")!.layer === 2, "D is layer 2");
  assert(result.edges.length === 3, "3 edges (A→C, B→C, C→D)");
  assert(result.width === 3 * 200, "width = 3 layers * 200");
});

// ─── Test 5: Cycle detection A → B → A ───

test("5. Cycle: A → B → A", () => {
  const tasks: TaskNode[] = [
    { id: "A", title: "Task A", assigneeId: "u1", prerequisites: ["B"] },
    { id: "B", title: "Task B", assigneeId: "u1", prerequisites: ["A"] },
  ];
  const result = computeTopologyLayout(tasks);
  assert(result === null, "cycle detected — returns null");
});

// ─── Summary ───

console.log(`\n${"=".repeat(40)}`);
console.log(`Results: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
