"""
WebGraph implementation for pathfinding in game maps.
Based on SRL-T's webgraph.simba
"""

from typing import List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import IntEnum
import math
import base64
import gzip
import json


Point = Tuple[int, int]
PointArray = List[Point]
PointArray2D = List[PointArray]
IntArray = List[int]
IntArray2D = List[IntArray]
StringArray = List[str]


class DoorType(IntEnum):
    UNKNOWN = 0
    NORMAL = 1
    WIDE = 2


@dataclass
class Door:
    before: Point = (0, 0)
    after: Point = (0, 0)
    center: Point = (0, 0)
    direction: Point = (0, 0)
    door_type: DoorType = DoorType.UNKNOWN
    separating: bool = False

    def get_door_angle(self) -> float:
        """Returns the compass angle needed to face the door directly."""
        cardinals = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        angles = [180, 90, 0, 270]
        
        best = -1
        best_angle = 0.0
        
        for i, cardinal in enumerate(cardinals):
            tmp = (self.center[0] - self.after[0], self.center[1] - self.after[1])
            dot = cardinal[0] * tmp[0] + cardinal[1] * tmp[1]
            if dot > best:
                best = dot
                best_angle = angles[i]
        
        return best_angle


@dataclass
class WebGraphSettings:
    spacing: int = 18
    minimum_tiles: int = 4
    node_radius: int = 50
    max_connections: int = 6
    wall_crossings: bool = True
    disabled: bool = False

    def hash(self) -> str:
        """Generate a hash for caching purposes."""
        data = [self.spacing, self.minimum_tiles, self.node_radius, 
                self.max_connections, int(self.wall_crossings)]
        h = 0x811C9DC5
        for d in data:
            if d == 0:
                continue
            h = (h * 0x1000193) ^ d
        return format(h & 0xFFFFFFFF, '08x')


@dataclass
class WebGraph:
    """Basic webgraph structure for pathfinding."""
    nodes: PointArray = field(default_factory=list)
    paths: IntArray2D = field(default_factory=list)
    names: StringArray = field(default_factory=list)
    blocking: IntArray = field(default_factory=list)

    def copy(self) -> 'WebGraph':
        """Create a copy of the graph."""
        return WebGraph(
            nodes=self.nodes.copy(),
            paths=[p.copy() for p in self.paths],
            names=self.names.copy(),
            blocking=self.blocking.copy()
        )

    def block_inside(self, area: Tuple[int, int, int, int]):
        """Block nodes inside the given area (x1, y1, x2, y2)."""
        x1, y1, x2, y2 = area
        for i, node in enumerate(self.nodes):
            if x1 <= node[0] <= x2 and y1 <= node[1] <= y2:
                if i not in self.blocking:
                    self.blocking.append(i)

    def block_outside(self, area: Tuple[int, int, int, int]):
        """Block nodes outside the given area."""
        x1, y1, x2, y2 = area
        for i, node in enumerate(self.nodes):
            if not (x1 <= node[0] <= x2 and y1 <= node[1] <= y2):
                if i not in self.blocking:
                    self.blocking.append(i)

    def find_path(self, start: int, goal: int, rnd: float = 0.0) -> IntArray:
        """Find path between two node indices using Dijkstra-like algorithm."""
        import random
        
        class Node:
            def __init__(self, indices: IntArray, score: float):
                self.indices = indices
                self.score = score

        queue = [Node([start], 0.0)]
        visited = set(self.blocking)
        
        while queue:
            queue.sort(key=lambda n: n.score)
            current = queue.pop(0)
            c_idx = current.indices[-1]
            
            if c_idx in visited:
                continue
            visited.add(c_idx)
            
            if c_idx == goal:
                return current.indices
            
            p = self.nodes[c_idx]
            for path_idx in self.paths[c_idx]:
                if path_idx not in visited:
                    q = self.nodes[path_idx]
                    new_indices = current.indices + [path_idx]
                    
                    hyp = math.hypot(p[0] - q[0], p[1] - q[1])
                    score = current.score + hyp + (hyp * random.random() * rnd - rnd / 2)
                    
                    queue.append(Node(new_indices, score))
        
        return []

    def find_nearest_node(self, p: Point) -> int:
        """Find the nearest node to point p."""
        best = float('inf')
        result = -1
        
        for i in range(len(self.paths)):
            for j in self.paths[i]:
                d = self._dist_to_line(p, self.nodes[i], self.nodes[j])
                if d < best:
                    best = d
                    dn1 = math.hypot(self.nodes[i][0] - p[0], self.nodes[i][1] - p[1])
                    dn2 = math.hypot(self.nodes[j][0] - p[0], self.nodes[j][1] - p[1])
                    result = i if dn1 < dn2 else j
        
        return result if result >= 0 else 0

    def _dist_to_line(self, p: Point, a: Point, b: Point) -> float:
        """Distance from point p to line segment ab."""
        if a == b:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        
        ab = (b[0] - a[0], b[1] - a[1])
        ap = (p[0] - a[0], p[1] - a[1])
        
        ab_sq = ab[0] * ab[0] + ab[1] * ab[1]
        if ab_sq == 0:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        
        ap_ab = ap[0] * ab[0] + ap[1] * ab[1]
        t = max(0, min(1, ap_ab / ab_sq))
        
        closest = (a[0] + t * ab[0], a[1] + t * ab[1])
        return math.hypot(p[0] - closest[0], p[1] - closest[1])

    def nodes_to_points(self, node_list: IntArray) -> PointArray:
        """Convert node indices to points."""
        return [self.nodes[i] for i in node_list]

    def path_between(self, p: Point, q: Point, rnd: float = 0.0) -> PointArray:
        """Find path between two points."""
        n1 = self.find_nearest_node(p)
        n2 = self.find_nearest_node(q)
        
        nodes = self.find_path(n1, n2, rnd)
        if not nodes:
            raise ValueError(f"Points {p} and {q} don't connect")
        
        result = [p]
        result.extend(self.nodes_to_points(nodes))
        result.append(q)
        return result

    def invalid_connection(self, p: Point, q: Point) -> bool:
        """Check if connection p-q would intersect existing paths."""
        for i in range(len(self.paths)):
            for j in self.paths[i]:
                a = self.nodes[i]
                b = self.nodes[j]
                if (p == a and q == b) or (p == b and q == a):
                    continue
                if self._lines_intersect(p, q, a, b):
                    return True
        return False

    def _lines_intersect(self, p1: Point, p2: Point, q1: Point, q2: Point) -> bool:
        """Check if line segments p1-p2 and q1-q2 intersect."""
        def det(a: Point, b: Point) -> int:
            return a[0] * b[1] - a[1] * b[0]
        
        dx = (p1[0] - p2[0], q1[0] - q2[0])
        dy = (p1[1] - p2[1], q1[1] - q2[1])
        dt = det(dx, dy)
        
        if dt == 0:
            return False
        
        d = (det(p1, p2), det(q1, q2))
        i_x = det(d, dx) / dt
        i_y = det(d, dy) / dt
        
        s = (dx[0] * (q1[1] - p1[1]) + dy[0] * (p1[0] - q1[0])) / dt
        t = (dx[1] * (p1[1] - q1[1]) + dy[1] * (q1[0] - p1[0])) / (-dt)
        
        return 0 < s < 1 and 0 < t < 1

    def add_node(self, p: Point, from_node: int = -1) -> bool:
        """Add a node to the graph."""
        if from_node != -1 and self.invalid_connection(p, self.nodes[from_node]):
            return False
        
        c = len(self.nodes)
        self.nodes.append(p)
        self.paths.append([])
        
        if from_node != -1:
            self.paths[from_node].append(c)
            self.paths[c].append(from_node)
        
        return True

    def connect_nodes(self, a: int, b: int) -> bool:
        """Connect two nodes by index."""
        if b in self.paths[a]:
            self.paths[a].remove(b)
            self.paths[b].remove(a)
        else:
            if self.invalid_connection(self.nodes[a], self.nodes[b]):
                return False
            self.paths[a].append(b)
            self.paths[b].append(a)
        return True

    def nodes_to_string(self) -> str:
        """Serialize nodes to base64 compressed string."""
        s = ''.join(f'[{n[0]} {n[1]}]' for n in self.nodes)
        compressed = gzip.compress(s.encode())
        return base64.b64encode(compressed).decode()

    def load_nodes_from_string(self, s: str):
        """Load nodes from base64 compressed string."""
        compressed = base64.b64decode(s)
        decompressed = gzip.decompress(compressed).decode()
        
        import re
        matches = re.findall(r'\[(\d+) (\d+)\]', decompressed)
        self.nodes = [(int(x), int(y)) for x, y in matches]

    def paths_to_string(self) -> str:
        """Serialize paths to base64 compressed string."""
        s = ''.join(f'[{" ".join(map(str, p)) if p else " "}]' for p in self.paths)
        compressed = gzip.compress(s.encode())
        return base64.b64encode(compressed).decode()

    def load_paths_from_string(self, s: str):
        """Load paths from base64 compressed string."""
        compressed = base64.b64decode(s)
        decompressed = gzip.decompress(compressed).decode()
        
        import re
        matches = re.findall(r'\[([^\]]+)\]', decompressed)
        self.paths = []
        for m in matches:
            if m.strip() == '':
                self.paths.append([])
            else:
                self.paths.append([int(x) for x in m.split()])

    def names_to_string(self) -> str:
        """Serialize names to base64 compressed string."""
        s = ''.join(f'[{n if n else "#0"}]' for n in self.names)
        compressed = gzip.compress(s.encode())
        return base64.b64encode(compressed).decode()

    def load_names_from_string(self, s: str):
        """Load names from base64 compressed string."""
        compressed = base64.b64decode(s)
        decompressed = gzip.decompress(compressed).decode()
        
        import re
        matches = re.findall(r'\[([^\]]+)\]', decompressed)
        self.names = [m if m != '#0' else '' for m in matches]


@dataclass
class WebGraphV2(WebGraph):
    """Enhanced webgraph with doors and collision data."""
    doors: List[Door] = field(default_factory=list)
    walkable_space: PointArray = field(default_factory=list)
    walkable_clusters: PointArray2D = field(default_factory=list)
    object_clusters: PointArray2D = field(default_factory=list)
    use_collision_data: bool = False

    def copy(self) -> 'WebGraphV2':
        """Create a copy of the graph."""
        return WebGraphV2(
            nodes=self.nodes.copy(),
            paths=[p.copy() for p in self.paths],
            names=self.names.copy(),
            blocking=self.blocking.copy(),
            doors=self.doors.copy(),
            walkable_space=self.walkable_space.copy(),
            walkable_clusters=[c.copy() for c in self.walkable_clusters],
            object_clusters=[c.copy() for c in self.object_clusters],
            use_collision_data=self.use_collision_data
        )

    def find_nearest_nodes(self, p: Point, amount: int) -> IntArray:
        """Find nearest nodes using spatial tree (simplified)."""
        if not self.nodes:
            return []
        
        distances = []
        for i, node in enumerate(self.nodes):
            dist = math.hypot(node[0] - p[0], node[1] - p[1])
            distances.append((i, dist))
        
        distances.sort(key=lambda x: x[1])
        result = [i for i, _ in distances[:amount]]
        
        if self.use_collision_data:
            filtered = []
            for i in result:
                node = self.nodes[i]
                if self._in_same_cluster(p, node):
                    filtered.append(i)
            result = filtered[:amount] if filtered else result[:amount]
        
        return result

    def _in_same_cluster(self, p: Point, q: Point) -> bool:
        """Check if two points are in the same walkable cluster."""
        for cluster in self.walkable_clusters:
            p_in = p in cluster
            q_in = q in cluster
            if p_in and q_in:
                return True
        return False

    def path_between_ex(self, p: Point, q: Point, rnd: float = 0.0, 
                       attempts: int = 3, safe: bool = True) -> PointArray:
        """Enhanced path finding with multiple attempts."""
        if self._point_in_range(p, q, 4):
            return [p, q]
        
        if self.use_collision_data:
            if p not in self.walkable_space:
                p = self.nearest_walkable_point(p)
            if q not in self.walkable_space:
                q = self.nearest_walkable_point(q)
        
        n_s = self.find_nearest_nodes(p, attempts)
        n_g = self.find_nearest_nodes(q, attempts)
        
        if n_s and n_g and n_s[0] == n_g[0]:
            return [p, q]
        
        nodes = []
        for i in n_s:
            for j in n_g:
                if i == j:
                    continue
                path = self.find_path(i, j, rnd)
                if path:
                    nodes = path
                    break
            if nodes:
                break
        
        if safe and not nodes:
            return []
        
        if not nodes:
            raise ValueError(f"Points {p} and {q} don't connect")
        
        result = [p]
        result.extend(self.nodes_to_points(nodes))
        result.append(q)
        return result

    def _point_in_range(self, p: Point, q: Point, dist: float) -> bool:
        """Check if two points are within distance."""
        return math.hypot(p[0] - q[0], p[1] - q[1]) <= dist

    def nearest_walkable_point(self, p: Point) -> Point:
        """Find nearest walkable point to p."""
        if not self.walkable_space:
            return p
        
        best = None
        best_dist = float('inf')
        
        for point in self.walkable_space:
            dist = math.hypot(point[0] - p[0], point[1] - p[1])
            if dist < best_dist:
                best_dist = dist
                best = point
        
        return best if best else p

    def doors_to_string(self) -> str:
        """Serialize doors to base64 compressed string."""
        s = ''.join(
            f'[{d.before[0]} {d.before[1]} {d.after[0]} {d.after[1]} '
            f'{d.center[0]} {d.center[1]} {d.direction[0]} {d.direction[1]} '
            f'{d.door_type.value} {int(d.separating)}]'
            for d in self.doors
        )
        compressed = gzip.compress(s.encode())
        return base64.b64encode(compressed).decode()

    def load_doors_from_string(self, s: str):
        """Load doors from base64 compressed string."""
        compressed = base64.b64decode(s)
        decompressed = gzip.decompress(compressed).decode()
        
        import re
        matches = re.findall(r'\[([^\]]+)\]', decompressed)
        self.doors = []
        for m in matches:
            values = [int(x) for x in m.split()]
            if len(values) >= 10:
                door = Door(
                    before=(values[0], values[1]),
                    after=(values[2], values[3]),
                    center=(values[4], values[5]),
                    direction=(values[6], values[7]),
                    door_type=DoorType(values[8]),
                    separating=bool(values[9])
                )
                self.doors.append(door)

