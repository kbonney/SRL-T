# PySRL-T WebGraph Generator

Python implementation of the SRL-T webgraph generator for pathfinding in Old School RuneScape maps.

## Overview

This module provides tools to automatically generate webgraphs from OSRS collision maps. A webgraph is a graph structure where nodes represent waypoints and edges represent walkable paths between them. This is used for pathfinding in game automation.

## Architecture

The webgraph generation process consists of three main stages:

1. **Map Loading**: Extract and combine OSRS map chunks from ZIP files
2. **Map Processing**: Extract walkable areas, detect doors, and prepare data structures
3. **Graph Generation**: Create nodes and connections to form the pathfinding graph

---

## Stage 1: OSRS Map Loading and Processing

### Map Storage Format

OSRS maps are stored as PNG images in ZIP files:
- **Location**: `osr/map/files/`
- **Files**: 
  - `collision.zip` - Collision maps (white=walkable, black=walls, red=doors)
  - `map.zip` - Normal map images
  - `heightmap.zip` - Height maps

### Chunk System

The OSRS world is divided into **chunks**:
- Each chunk is a 256×256 pixel image (Map.ChunkSide = TileSize × RSChunkSide = 4 × 64 = 256)
- Chunks are organized by plane (0-3) and coordinates (x, y)
- Chunk files are named: `{plane}/{x}-{y}.png` (e.g., `0/49-54.png`)

### Map Loading Process (`map_loader.py`)

#### 1. Chunk Extraction

```python
loader = MapLoader()
chunks = RSChunk.box_to_chunks((49, 54, 50, 53))  # Varrock box
collision_map = loader.get_collision_map(chunks, plane=0)
```

**Steps**:
1. **Convert box to chunks**: Box coordinates `(x1, y1, x2, y2)` are converted to a list of chunk coordinates
   - Example: `(49, 54, 50, 53)` → `[(49, 54), (49, 53), (50, 54), (50, 53)]`
   - Handles inverted Y coordinates (Simba uses `y := 199 - chunks[i].Y`)

2. **Extract from ZIP**: For each chunk:
   - Check cache first (`.png` files in `cache/collision/{plane}/`)
   - If not cached, extract from `collision.zip` using `zipfile`
   - Cache the extracted chunk for future use
   - If chunk doesn't exist in ZIP, create empty 256×256 black image

3. **Combine chunks**: 
   - Calculate dimensions: `(max_x - min_x + 1) * 256 + 1 + 256` pixels wide
   - Transform Y coordinates: `y_transformed = 199 - y` (matches Simba coordinate system)
   - Paste each chunk at calculated offset: `(chunk_x - min_x) * 256, (chunk_y - min_y) * 256`

#### 2. Coordinate System

The Simba code uses a coordinate transformation:
- **Chunk coordinates**: Standard (x, y) where Y increases downward
- **Map coordinates**: Transformed using `y := 199 - chunks[i].Y` to invert Y axis
- This matches OSRS's internal coordinate system where Y=0 is at the top

**Example**:
```
Chunk (49, 54) → Transformed to (49, 145) in map
Chunk (49, 53) → Transformed to (49, 146) in map
```

The final combined map positions chunks correctly relative to each other.

---

## Stage 2: Map Processing for Webgraph Generation

### Pixel Extraction (`build_graph` function)

The collision map is processed to extract walkable areas:

```python
# Extract white (walkable) and red (doors) pixels
white_mask = (img_array[:, :, 0] == 255) & (img_array[:, :, 1] == 255) & (img_array[:, :, 2] == 255)
red_mask = (img_array[:, :, 0] == 255) & (img_array[:, :, 1] == 0) & (img_array[:, :, 2] == 0)  # RGB red
```

**Color meanings**:
- **White (255, 255, 255)**: Walkable space
- **Black (0, 0, 0)**: Non-walkable (walls, obstacles)
- **Red (255, 0, 0)**: Doors
- **Gray (51, 51, 51)**: Objects (optional)

Uses numpy array operations for fast pixel extraction.

### Clustering Walkable Areas

Walkable pixels are clustered into connected regions:

```python
atpa = nr_cluster(white, 1.0)  # Cluster with distance 1.0
atpa.sort(key=len, reverse=True)  # Sort by size, largest first
```

**NRCluster Algorithm** (Non-Rounding Cluster):
1. **Connected Components**: Uses transitive closure to find all connected points
   - Distance 1.0 includes 4-connected neighbors (horizontal/vertical)
   - Points within distance are in the same cluster
   - Recursively expands: if A connects to B, and B connects to C, all are in same cluster

2. **Implementation**:
   - For small sets (< 100 points): Simple O(n²) algorithm
   - For large sets: Uses scipy's `cKDTree` for O(n log n) performance
   - Transitive closure ensures all connected pixels are grouped together

**Example**:
```
Pixels: (0,0), (0,1), (1,0), (1,1), (10,10)
Distance 1.0 clustering:
  - Cluster 1: [(0,0), (0,1), (1,0), (1,1)]  (all connected)
  - Cluster 2: [(10,10)]  (isolated)
```

### Door Detection

Red pixels are clustered and analyzed to detect doors:

```python
door_atpa = nr_cluster(red, 1.0)
doors = find_doors(door_atpa, white)
```

**Door Detection Algorithm**:
1. **Cluster red pixels**: Group nearby red pixels together
2. **Find direction**: Check if door is horizontal, vertical, or diagonal
   - Horizontal: Has pixels at `center ± (1, 0)`
   - Vertical: Has pixels at `center ± (0, 1)`
   - Diagonal: Has pixels at `center ± (1, 1)` or `center ± (1, -1)`
3. **Validate door**: Check if pixels around door are walkable
   - Must have walkable space on both sides
   - Excludes open doors (already passable)
4. **Classify type**: 
   - 4 pixels = NORMAL door
   - 8 pixels = WIDE door
5. **Calculate positions**:
   - `Before`: Point before door (walkable side)
   - `After`: Point after door (walkable side)
   - `Center`: Door center position
   - `Direction`: Direction vector

### Area Filtering

Small or invalid areas are filtered out:

```python
if len(cluster) <= settings.minimum_tiles * tile_area:  # tile_area = 16
    continue  # Skip this cluster
```

- **Minimum tiles**: Areas with fewer than `minimum_tiles × 16` pixels are ignored
- **Node radius**: Areas smaller than `node_radius` pixels get a single median node
- Clusters are sorted by size, so largest walkable areas are processed first

---

## Stage 3: Webgraph Generation

### Skeleton Extraction

For each large walkable area, a skeleton is extracted:

```python
eroded = erode_tpa(cluster, 1)  # Remove border pixels
skeleton = skeleton_tpa(eroded, 2, 7)  # Extract skeleton
```

**Process**:
1. **Erosion**: Remove border pixels (pixels not completely surrounded)
   - Iterates through points, keeps only those with all 8 neighbors present
2. **Skeletonization**: Extract the "centerline" of the walkable area
   - Uses morphological operations to find the medial axis
   - Creates a thin representation of the walkable path network
   - Parameters: `fMin=2, fMax=7` control skeleton thickness

**Why skeleton?**: The skeleton represents the optimal paths through an area - it's the centerline that maximizes distance from walls.

### Node Placement

Nodes are placed along the skeleton at regular intervals:

```python
partitions = partition_tpa(skeleton, spacing=18, spacing=18)
for partition in partitions:
    sub_clusters = nr_cluster(partition, 1.0)
    for sub_cluster in sub_clusters:
        nodes.append(middle_tpa(sub_cluster))
```

**Process**:
1. **Partition skeleton**: Divide skeleton into grid cells (18×18 pixel spacing)
2. **Cluster partitions**: Group nearby skeleton points in each partition
3. **Place nodes**: Put a node at the middle of each cluster
4. **Result**: Nodes are evenly distributed along walkable paths

**Spacing parameter**: Controls node density
- Lower spacing = more nodes = better pathfinding but slower
- Higher spacing = fewer nodes = faster but less precise

### Connection Building

Nodes are connected to form the graph:

```python
# For each node, find nearest neighbors
tree = cKDTree(nodes_array)
distances, indices = tree.query(node, k=max_connections + 1)

# Validate each potential connection
for neighbor in neighbors:
    if _validate_connection_simba(node, neighbor, skeleton_tree, settings, map_image):
        connection_map[neighbor.x, neighbor.y].append(node_index)
```

**Connection Validation** (matches Simba algorithm):

1. **Distance check**: `max(|dx|, |dy|) <= spacing * 2`
   - Only connect nodes within reasonable distance

2. **Wall crossing check** (if `wall_crossings=True`):
   ```python
   if not _colors_in_line_ex(p, q, map_image, [black, gray, red]):
       return True  # No walls in path, connection valid
   ```
   - Checks if line between nodes crosses walls (black/gray/red pixels)
   - If no walls, connection is valid

3. **Skeleton path validation** (if `wall_crossings=False`):
   ```python
   # Expand bounds around connection
   bounds = Box(p, q).Expand(spacing)
   skeleton_parts = skeleton_tree.RangeQuery(bounds).Cluster(1)
   
   # Check if both nodes are within sqrt(2) of skeleton parts
   for part in skeleton_parts:
       if part.InRange(p, sqrt(2)) and part.InRange(q, sqrt(2)):
           return True  # Valid path through skeleton
   ```
   - Queries skeleton points near the connection
   - Verifies both nodes are reachable via skeleton
   - Uses `sqrt(2)` distance threshold (matches Simba's `InRange`)

**Connection Map**: Uses pixel coordinates as keys
- `connection_map[q.x, q.y]` = list of node indices that connect to point q
- This matches Simba's 2D array indexing: `connectionMap[q.X, q.Y]`

### Door Node Connection

Door nodes are connected to the nearest walkable nodes:

```python
for door_node in door_nodes:
    # Find nearest nodes (up to 20)
    nearest = tree.query(door_node, k=20)
    
    for node in nearest:
        # Check if in same walkable cluster
        if door_node and node in same_cluster:
            # Connect door node to walkable node
            graph.connect_nodes(door_node, node)
            break
```

**Process**:
1. For each door (before/after points)
2. Find nearest graph nodes using spatial tree
3. Check if door and node are in the same walkable cluster
4. Connect them if valid

### Final Graph Structure

The resulting graph contains:

```python
graph.nodes      # List of (x, y) waypoint positions
graph.paths      # 2D array: paths[i] = list of connected node indices
graph.names      # Optional names for nodes (for landmarks)
graph.doors      # List of door objects with positions
graph.blocking   # List of blocked node indices (for dynamic obstacles)
```

**Pathfinding**: Uses Dijkstra-like algorithm
- Finds shortest path between node indices
- Optional randomness parameter for path variation
- Respects blocked nodes
- Returns list of node indices forming the path

---

## Algorithm Flow Summary

```
1. LOAD MAP
   ├─ Extract chunks from collision.zip
   ├─ Transform coordinates (y := 199 - y)
   └─ Combine into single map image

2. EXTRACT PIXELS
   ├─ Find white pixels (walkable)
   ├─ Find red pixels (doors)
   └─ Create white_set for fast lookup

3. CLUSTER AREAS
   ├─ NRCluster(white, 1.0) → connected walkable regions
   ├─ Sort by size (largest first)
   └─ Filter small areas (< minimum_tiles × 16)

4. PROCESS EACH CLUSTER
   ├─ Small clusters → single median node
   ├─ Large clusters:
   │  ├─ Erode → remove borders
   │  ├─ Skeleton → extract centerlines
   │  ├─ Partition → divide into grid cells
   │  ├─ Place nodes → middle of each partition cluster
   │  └─ Connect nodes → validate paths through skeleton
   └─ Add to graph

5. CONNECT DOORS
   ├─ Find nearest walkable nodes
   ├─ Validate same cluster
   └─ Add connections

6. SERIALIZE
   ├─ Compress nodes/paths/names/doors
   ├─ Base64 encode
   └─ Save to JSON
```

---

## Key Parameters

### WebGraphSettings

- **`spacing`** (default: 18): Distance between nodes in pixels
  - Lower = more nodes, better precision, slower generation
  - Higher = fewer nodes, faster, less precise

- **`minimum_tiles`** (default: 4): Minimum tiles per area
  - Areas with fewer than `minimum_tiles × 16` pixels are ignored
  - Filters out noise and tiny isolated spaces

- **`node_radius`** (default: 50): Single-node threshold
  - Areas smaller than this get a single median node
  - Avoids over-segmentation of small spaces

- **`max_connections`** (default: 6): Maximum connections per node
  - Limits graph complexity
  - Prevents nodes from connecting to too many neighbors

- **`wall_crossings`** (default: True): Allow wall crossings
  - If True: Connections can cross walls if no obstacles in direct line
  - If False: Only connect via skeleton paths (more restrictive)

---

## Usage

### Basic Example

```python
from pysrl_t import MapLoader, RSChunk, build_graph, WebGraphSettings

# Load collision map
loader = MapLoader()
chunks = RSChunk.box_to_chunks(RSChunk.VARROCK)
collision_map = loader.get_collision_map(chunks, plane=0)

# Generate graph
settings = WebGraphSettings(spacing=18, minimum_tiles=4)
graph = build_graph(collision_map, settings)

# Use graph for pathfinding
path = graph.path_between((100, 200), (500, 600))
```

### Running the Script

```bash
cd pysrl-t
python generate_from_osrs.py
```

This will:
1. Load Varrock, Lumbridge, and Falador collision maps
2. Generate webgraphs for each
3. Save graphs as JSON files
4. Create visualization images

---

## File Structure

```
pysrl-t/
├── webgraph.py          # Core graph data structures (WebGraph, WebGraphV2)
├── graph_generator.py   # Graph generation algorithm (build_graph)
├── map_loader.py        # OSRS map loading (MapLoader, RSChunk)
├── visualize_graph.py   # Visualization tools
├── generate_from_osrs.py  # Main script for OSRS maps
├── generate_graph.py    # Script for custom maps
└── example.py          # Usage examples
```

---

## Differences from Simba Implementation

The Python implementation matches the Simba code logic but uses:

- **NumPy/PIL** instead of Simba's bitmap types
- **scipy.spatial.cKDTree** instead of TSlackTree (when available)
- **scikit-image** for skeletonization (when available)
- **Python data structures** (lists, dicts, sets) instead of Simba arrays

The core algorithms (clustering, skeleton extraction, connection validation) are functionally equivalent.

---

## Performance Notes

- **Clustering**: O(n log n) with scipy, O(n²) fallback
- **Skeleton extraction**: Can be slow for large areas (100k+ pixels)
- **Connection validation**: O(k × m) where k = max_connections, m = skeleton points
- **Total time**: Typically 10-60 seconds for a region depending on size

For very large maps, consider:
- Increasing `spacing` to reduce node count
- Increasing `minimum_tiles` to filter more small areas
- Processing regions separately and merging graphs

---

## Troubleshooting

### Empty Graphs

If graphs have 0 nodes:
- Check if walkable pixels are being found (debug output shows count)
- Verify clustering is working (should have reasonable cluster count, not 100k+)
- Check if clusters are too small (all filtered out by `minimum_tiles`)

### Too Many/Few Nodes

- Adjust `spacing`: Lower = more nodes, Higher = fewer nodes
- Adjust `minimum_tiles`: Higher = filter more small areas
- Adjust `node_radius`: Higher = more single-node areas

### Incorrect Paths

- Verify map coordinate transformation is correct
- Check if `wall_crossings` setting matches your needs
- Ensure skeleton extraction is working (check debug output)

---

## License

Same as SRL-T project.
