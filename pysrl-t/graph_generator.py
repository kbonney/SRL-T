"""
WebGraph generator - automatically generates webgraphs from map images.
Based on SRL-T's maploader.simba _BuildGraph function.
"""

from typing import Any, List, Tuple, Optional
import numpy as np
from PIL import Image
import math
import sys
import os
from webgraph import WebGraphSettings

# Handle imports for both package and script execution
if __name__ == '__main__' or not __package__:
    # Running as script or not in a package
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from webgraph import WebGraphV2, Door, DoorType, WebGraphSettings, Point, PointArray, PointArray2D
else:
    # Running as package
    from .webgraph import WebGraphV2, Door, DoorType, WebGraphSettings, Point, PointArray, PointArray2D

try:
    from scipy import ndimage
    from scipy.spatial import cKDTree
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available, some features may be limited")


def nr_cluster(points: PointArray, dist: float) -> PointArray2D:
    """
    Cluster points using nearest neighbor clustering (transitive closure).
    Groups points that are within 'dist' distance of each other.
    Uses connected components approach to ensure all connected points are in same cluster.
    """
    if not points:
        return []
    
    if not SCIPY_AVAILABLE:
        return _nr_cluster_simple(points, dist)
    
    # For very small sets, simple implementation is faster
    if len(points) < 100:
        return _nr_cluster_simple(points, dist)
    
    points_array = np.array(points)
    tree = cKDTree(points_array)  # type: ignore
    
    clusters = []
    used = set()
    
    # Use connected components approach for proper clustering
    for i in range(len(points)):
        if i in used:
            continue
        
        # Start new cluster with this point
        cluster_indices = {i}
        used.add(i)
        
        # Expand cluster by finding all connected points (transitive closure)
        to_process = [i]
        while to_process:
            current_idx = to_process.pop()
            point = points_array[current_idx]  # Keep as numpy array for query_ball_point
            
            # Find all neighbors within distance
            neighbors = tree.query_ball_point(point, dist)
            for j in neighbors:
                if j not in used and j != current_idx:
                    cluster_indices.add(j)
                    used.add(j)
                    to_process.append(j)
        
        # Convert indices to points
        cluster = [tuple[Any, ...](points_array[idx]) for idx in cluster_indices]
        clusters.append(cluster)
    
    return clusters


def _nr_cluster_simple(points: PointArray, dist: float) -> PointArray2D:
    """Simple clustering without scipy - uses transitive closure."""
    clusters = []
    used = set()
    
    for i, p1 in enumerate(points):
        if i in used:
            continue
        
        # Start cluster with transitive closure
        cluster_indices = {i}
        used.add(i)
        to_process = [i]
        
        while to_process:
            current_idx = to_process.pop()
            current_point = points[current_idx]
            
            # Find all points within distance (transitive closure)
            for j, p2 in enumerate(points):
                if j in used or j == current_idx:
                    continue
                d = math.hypot(current_point[0] - p2[0], current_point[1] - p2[1])
                if d <= dist:
                    cluster_indices.add(j)
                    used.add(j)
                    to_process.append(j)
        
        # Convert to point list
        cluster = [points[idx] for idx in cluster_indices]
        clusters.append(cluster)
    
    return clusters


def erode_tpa(points: PointArray, iterations: int = 1) -> PointArray:
    """Erode a point array (remove border points)."""
    if not points or iterations == 0:
        return points.copy()
    
    points_set = set(points)
    result = []
    
    for point in points:
        x, y = point
        neighbors = [
            (x-1, y-1), (x, y-1), (x+1, y-1),
            (x-1, y),             (x+1, y),
            (x-1, y+1), (x, y+1), (x+1, y+1)
        ]
        
        all_neighbors = all(n in points_set for n in neighbors)
        if all_neighbors:
            result.append(point)
    
    if iterations > 1:
        return erode_tpa(result, iterations - 1)
    
    return result


def skeleton_tpa(points: PointArray, f_min: int = 2, f_max: int = 7) -> PointArray:
    """
    Extract skeleton from point array using morphological operations.
    Simplified version - uses erosion and distance transform.
    """
    if not points:
        return []
    
    if not SCIPY_AVAILABLE:
        return _skeleton_simple(points, f_min, f_max)
    
    # Convert to binary image
    if not points:
        return []
    
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    width = max_x - min_x + 1
    height = max_y - min_y + 1
    
    img = np.zeros((height, width), dtype=bool)
    for x, y in points:
        img[y - min_y, x - min_x] = True
    
    # Apply skeletonization
    from skimage.morphology import skeletonize
    try:
        skeleton = skeletonize(img)
    except ImportError:
        return _skeleton_simple(points, f_min, f_max)
    
    # Convert back to points
    result = []
    for y in range(height):
        for x in range(width):
            if skeleton[y, x]:
                result.append((x + min_x, y + min_y))
    
    return result


def _skeleton_simple(points: PointArray, f_min: int, f_max: int) -> PointArray:
    """Simple skeleton extraction using erosion."""
    if not points:
        return []
    
    # Use erosion-based approach
    eroded = erode_tpa(points, f_min)
    
    # Keep points that are on the "edge" of the shape
    points_set = set(points)
    result = []
    
    for point in eroded:
        x, y = point
        neighbors = [
            (x-1, y), (x+1, y), (x, y-1), (x, y+1)
        ]
        
        # Keep if at least one neighbor is not in the set
        if any(n not in points_set for n in neighbors):
            result.append(point)
    
    return result if result else points


def partition_tpa(points: PointArray, spacing_x: int, spacing_y: int) -> PointArray2D:
    """Partition points into grid cells."""
    if not points:
        return []
    
    partitions = {}
    
    for point in points:
        x, y = point
        grid_x = x // spacing_x
        grid_y = y // spacing_y
        key = (grid_x, grid_y)
        
        if key not in partitions:
            partitions[key] = []
        partitions[key].append(point)
    
    return list(partitions.values())


def middle_tpa(points: PointArray) -> Point:
    """Get the middle point of a point array."""
    if not points:
        return (0, 0)
    
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    
    return (sum(xs) // len(xs), sum(ys) // len(ys))


def median_tpa(points: PointArray) -> Point:
    """Get the median point of a point array."""
    if not points:
        return (0, 0)
    
    xs = sorted([p[0] for p in points])
    ys = sorted([p[1] for p in points])
    
    mid = len(xs) // 2
    return (xs[mid], ys[mid])


def bounds_tpa(points: PointArray) -> Tuple[int, int, int, int]:
    """Get bounding box of points (x1, y1, x2, y2)."""
    if not points:
        return (0, 0, 0, 0)
    
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    
    return (min(xs), min(ys), max(xs), max(ys))


def find_doors(door_atpa: PointArray2D, white: PointArray) -> List[Door]:
    """Find doors from door clusters."""
    doors = []
    white_set = set(white)
    
    for door_cluster in door_atpa:
        if not door_cluster:
            continue
        
        center = middle_tpa(door_cluster)
        direction = (0, 0)
        
        # Check horizontal
        if (center[0] + 1, center[1]) in door_cluster and (center[0] - 1, center[1]) in door_cluster:
            direction = (0, 1)
        
        # Check vertical
        if (center[0], center[1] + 1) in door_cluster and (center[0], center[1] - 1) in door_cluster:
            direction = (1, 0)
        
        # Check diagonal
        if (center[0] + 1, center[1] + 1) in door_cluster and (center[0] - 1, center[1] - 1) in door_cluster:
            direction = (1, -1)
        
        if (center[0] + 1, center[1] - 1) in door_cluster and (center[0] - 1, center[1] + 1) in door_cluster:
            direction = (1, 1)
        
        if direction == (0, 0):
            continue
        
        # Check if pixels around door are walkable
        dir_point = (center[0] + direction[0], center[1] + direction[1])
        opposite_dir = (-direction[0], -direction[1])
        opposite_point = (center[0] + opposite_dir[0], center[1] + opposite_dir[1])
        
        if dir_point not in white_set or opposite_point not in white_set:
            continue
        
        door_type = DoorType.NORMAL
        if len(door_cluster) >= 8:
            door_type = DoorType.WIDE
        
        door = Door(
            center=center,
            direction=direction,
            door_type=door_type,
            separating=True
        )
        
        # Adjust center for wide doors
        if door_type == DoorType.WIDE:
            if direction == (0, 1):
                door.center = (door.center[0] - 2, door.center[1])
            elif direction == (1, 0):
                door.center = (door.center[0], door.center[1] - 2)
        
        # Calculate before and after points
        door.before = (door.center[0] + direction[0] * 2, door.center[1] + direction[1] * 2)
        door.after = (door.center[0] - direction[0] * 2, door.center[1] - direction[1] * 2)
        
        doors.append(door)
    
    return doors


def build_graph(map_image: Image.Image, settings: WebGraphSettings) -> WebGraphV2:
    """
    Build a webgraph from a map image.
    
    Map colors:
    - White (0xFFFFFF): Walkable space
    - Black (0x000000): Non-walkable space
    - Red (0x0000FF): Doors (optional)
    - Gray (0x333333): Objects (optional)
    """
    result = WebGraphV2()
    
    # Normalize image to RGB or grayscale based on mode
    if map_image.mode == 'L':
        # Grayscale image
        img_array = np.array(map_image)
        height, width = img_array.shape
        white_mask = img_array == 255
        white_coords = np.argwhere(white_mask)
        white = [(int(coord[1]), int(coord[0])) for coord in white_coords]
        white_set = set(white)
        red = []
    else:
        # Color image - convert to RGB to ensure consistent format
        rgb_image = map_image.convert('RGB')
        img_array = np.array(rgb_image)
        height, width = img_array.shape[:2]
        
        # Extract white (walkable) and red (doors) pixels
        # PIL RGB format: (R, G, B) = (255, 255, 255) for white, (255, 0, 0) for red
        white_mask = (img_array[:, :, 0] == 255) & (img_array[:, :, 1] == 255) & (img_array[:, :, 2] == 255)
        red_mask = (img_array[:, :, 0] == 255) & (img_array[:, :, 1] == 0) & (img_array[:, :, 2] == 0)
        
        white_coords = np.argwhere(white_mask)
        red_coords = np.argwhere(red_mask)
        
        # Convert to (x, y) format (numpy gives (y, x))
        white = [(int(coord[1]), int(coord[0])) for coord in white_coords]
        red = [(int(coord[1]), int(coord[0])) for coord in red_coords]
        white_set = set(white)
    
    # Cluster walkable areas
    # Simba uses NRCluster(1) which clusters points within distance 1.0
    # This includes 4-connected neighbors (horizontal/vertical), not diagonal
    # But for proper clustering of walkable areas, we might need sqrt(2) for 8-connected
    print(f"  Found {len(white)} walkable pixels, {len(red)} door pixels")
    cluster_dist = 1.0  # Match Simba: NRCluster(1)
    atpa = nr_cluster(white, cluster_dist)
    atpa.sort(key=len, reverse=True)
    print(f"  Clustered into {len(atpa)} walkable areas")
    if atpa:
        print(f"  Largest cluster: {len(atpa[0])} pixels")
        if len(atpa) > 1:
            print(f"  Second largest: {len(atpa[1])} pixels")
        if len(atpa) > 2:
            print(f"  Third largest: {len(atpa[2])} pixels")
        # Show more info about cluster sizes
        sizes = [len(c) for c in atpa[:10]]
        print(f"  Top 10 cluster sizes: {sizes}")
    
    # Find doors
    door_atpa = nr_cluster(red, cluster_dist) if red else []
    doors = find_doors(door_atpa, white)
    
    # Process doors
    door_nodes = []
    non_sep_doors = 0
    
    for i, door in enumerate(doors):
        if door.door_type == DoorType.UNKNOWN:
            non_sep_doors += 1
            continue
        
        # Check if door separates areas (matches Simba: atpa.InSameTPA)
        # InSameTPA checks if both points are in the same cluster using bounds
        door_in_same_cluster = False
        for cluster in atpa:
            if not cluster:
                continue
            # Check if cluster bounds contain either point
            bounds = bounds_tpa(cluster)
            before_in = (bounds[0] <= door.before[0] <= bounds[2] and 
                        bounds[1] <= door.before[1] <= bounds[3])
            after_in = (bounds[0] <= door.after[0] <= bounds[2] and 
                       bounds[1] <= door.after[1] <= bounds[3])
            
            if before_in or after_in:
                # Check intersection - if both points are in cluster, length should be 2
                intersection = [p for p in [door.before, door.after] if p in cluster]
                if len(intersection) == 2:
                    door_in_same_cluster = True
                    break
        
        if door_in_same_cluster:
            non_sep_doors += 1
            continue
        
        result.doors.append(door)
        door_nodes.extend([door.before, door.after])
    
    # Process walkable areas
    # TileArea = TileSize * TileSize = 4 * 4 = 16 (from translator.simba)
    tile_area = 16
    
    for i, cluster in enumerate(atpa):
        if len(cluster) <= settings.minimum_tiles * tile_area:
            if i == 0:
                print(f"  Warning: First cluster too small ({len(cluster)} <= {settings.minimum_tiles * tile_area})")
            continue
        
        bounds = bounds_tpa(cluster)
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        max_dim = max(width, height)
        
        # Small areas get single node
        if max_dim < settings.node_radius:
            result.nodes.append(median_tpa(cluster))
            result.paths.append([])
            result.names.append('')
            continue
        
        # Extract skeleton
        eroded = erode_tpa(cluster, 1)
        skeleton = skeleton_tpa(eroded, 2, 7)
        
        if not skeleton:
            if i == 0:
                print(f"  Warning: No skeleton extracted for first cluster (had {len(eroded)} points after erosion)")
            result.nodes.append(median_tpa(cluster))
            result.paths.append([])
            result.names.append('')
            continue
        
        if i == 0:
            print(f"  First cluster: {len(cluster)} points, skeleton: {len(skeleton)} points")
        
        # Partition skeleton
        nodes = []
        partitions = partition_tpa(skeleton, settings.spacing, settings.spacing)
        
        if i == 0:
            print(f"  Partitioned skeleton into {len(partitions)} partitions")
        
        for partition in partitions:
            if not partition:
                continue
            sub_clusters = nr_cluster(partition, 1.0)
            for sub_cluster in sub_clusters:
                nodes.append(middle_tpa(sub_cluster))
        
        if not nodes:
            if i == 0:
                print(f"  Warning: No nodes generated from partitions")
            result.nodes.append(median_tpa(cluster))
            result.paths.append([])
            result.names.append('')
            continue
        
        if i == 0:
            print(f"  Generated {len(nodes)} nodes from skeleton")
        
        # Build connections using spatial tree (matches Simba implementation)
        # Use connectionMap indexed by pixel coordinates [q.X, q.Y] -> list of node indices
        connection_map = {}  # Dict of (x, y) -> list of node indices
        
        if SCIPY_AVAILABLE and nodes and skeleton:
            nodes_array = np.array(nodes)
            skeleton_array = np.array(skeleton)
            nodes_tree = cKDTree(nodes_array)  # type: ignore
            skeleton_tree = cKDTree(skeleton_array)  # type: ignore
            
            for j, p in enumerate(nodes):
                # Find nearest neighbors (Simba: KNearest with True flag excludes self)
                distances, indices = nodes_tree.query(p, k=min(settings.max_connections + 1, len(nodes)))
                
                if not isinstance(distances, np.ndarray):
                    # Single result
                    if indices != j and indices < len(nodes):
                        q = tuple(nodes_array[indices])
                        if max(abs(p[0] - q[0]), abs(p[1] - q[1])) <= settings.spacing * 2:
                            if _validate_connection_simba(p, q, skeleton_tree, skeleton, settings, map_image):
                                key = (int(q[0]), int(q[1]))
                                if key not in connection_map:
                                    connection_map[key] = []
                                if j not in connection_map[key]:
                                    connection_map[key].append(j)
                    continue
                
                for idx, dist in zip(indices, distances):
                    if idx == j:
                        continue
                    if idx >= len(nodes):
                        continue
                    
                    q = tuple(nodes_array[idx])
                    
                    # Check distance constraint
                    if max(abs(p[0] - q[0]), abs(p[1] - q[1])) > settings.spacing * 2:
                        continue
                    
                    # Validate connection (matches Simba logic)
                    if _validate_connection_simba(p, q, skeleton_tree, skeleton, settings, map_image):
                        key = (int(q[0]), int(q[1]))
                        if key not in connection_map:
                            connection_map[key] = []
                        if j not in connection_map[key]:
                            connection_map[key].append(j)
        else:
            # Fallback without scipy
            for j, p in enumerate(nodes):
                for k, q in enumerate(nodes):
                    if j == k:
                        continue
                    if max(abs(p[0] - q[0]), abs(p[1] - q[1])) > settings.spacing * 2:
                        continue
                    if _path_in_skeleton(p, q, skeleton, settings.spacing):
                        key = (int(q[0]), int(q[1]))
                        if key not in connection_map:
                            connection_map[key] = []
                        if j not in connection_map[key]:
                            connection_map[key].append(j)
        
        # Add nodes and connections (matches Simba: connectionMap[p.X, p.Y])
        start_idx = len(result.nodes)
        for node in nodes:
            result.nodes.append(node)
            result.paths.append([])
            result.names.append('')
        
        connections_added = 0
        for j, p in enumerate(nodes):
            key = (int(p[0]), int(p[1]))
            if key in connection_map:
                for n in connection_map[key]:
                    if n < len(nodes):
                        idx1 = start_idx + j
                        idx2 = start_idx + n
                        if idx2 not in result.paths[idx1]:
                            result.paths[idx1].append(idx2)
                            connections_added += 1
                        if idx1 not in result.paths[idx2]:
                            result.paths[idx2].append(idx1)
        
        if i == 0:
            print(f"  Added {connections_added} connections for first cluster")
    
    # Connect door nodes to nearest nodes
    if door_nodes and SCIPY_AVAILABLE and result.nodes:
        nodes_array = np.array(result.nodes)
        tree = cKDTree(nodes_array)  # type: ignore
        
        for door_node in door_nodes:
            if door_node in result.nodes:
                continue
            
            distances, indices = tree.query(door_node, k=min(20, len(result.nodes)))
            
            if isinstance(indices, np.ndarray):
                for idx in indices:
                    if idx >= len(result.nodes):
                        continue
                    nearest_node = tuple(nodes_array[idx])
                    
                    # Check if in same cluster
                    in_same_cluster = False
                    for cluster in atpa:
                        if door_node in cluster and nearest_node in cluster:
                            in_same_cluster = True
                            break
                    
                    if in_same_cluster:
                        result.nodes.append(door_node)
                        result.paths.append([])
                        result.names.append('')
                        result.paths[idx].append(len(result.nodes) - 1)
                        result.paths[-1].append(idx)
                        break
            else:
                if indices < len(result.nodes):
                    result.nodes.append(door_node)
                    result.paths.append([])
                    result.names.append('')
                    result.paths[indices].append(len(result.nodes) - 1)
                    result.paths[-1].append(indices)
                    break
    
    # Store walkable space
    result.walkable_space = white
    result.walkable_clusters = atpa
    
    return result


def _validate_connection_simba(p: Point, q: Point, skeleton_tree, skeleton_points: PointArray,
                               settings: WebGraphSettings, map_image: Image.Image) -> bool:
    """
    Validate connection between p and q using Simba's algorithm.
    Matches Simba: checks wall crossings and skeleton path validation.
    """
    # Check wall crossing (Simba: ColorsInLineEx)
    if settings.wall_crossings:
        # Check if line doesn't cross walls (black, gray, or red)
        # Simba: not map.ColorsInLineEx means no walls, so connection is valid
        if not _colors_in_line_ex(p, q, map_image, [0, 0x333333, 0xFF]):
            return True
    
    # Validate using skeleton (Simba: RangeQuery and InRange checks)
    if skeleton_tree is None or not skeleton_points:
        return False
    
    # Expand bounds by spacing (Simba: Box(p, q).Expand(GENERATED_GRAPH.Spacing))
    x1, y1 = p
    x2, y2 = q
    min_x = min(x1, x2) - settings.spacing
    max_x = max(x1, x2) + settings.spacing
    min_y = min(y1, y2) - settings.spacing
    max_y = max(y1, y2) + settings.spacing
    
    # Range query on skeleton (Simba: skeletonTree.RangeQuery(bounds))
    center = ((x1 + x2) / 2, (y1 + y2) / 2)
    radius = math.hypot(max_x - min_x, max_y - min_y) / 2
    skeleton_indices = skeleton_tree.query_ball_point(center, radius)
    
    if not skeleton_indices:
        return False
    
    # Cluster skeleton parts (Simba: .Cluster(1))
    # Extract skeleton points in the box and cluster them
    skeleton_in_box = [skeleton_points[idx] for idx in skeleton_indices if idx < len(skeleton_points)]
    if not skeleton_in_box:
        return False
    
    skeleton_parts = nr_cluster(skeleton_in_box, 1.0)
    
    # Check if both nodes are within sqrt(2) of the same skeleton cluster part
    # Simba logic: For each part, check if both p and q are in range
    # If both are in range of the same part, connection is valid
    # If one is in range but not the other, break (invalid)
    sqrt2 = math.sqrt(2)
    
    for part in skeleton_parts:
        j_in_range = False
        n_in_range = False
        
        for skel_point in part:
            # Check if p and q are within Sqrt(2) of skeleton point (Simba: InRange(p, Sqrt(2)))
            dist_p = math.hypot(p[0] - skel_point[0], p[1] - skel_point[1])
            dist_q = math.hypot(q[0] - skel_point[0], q[1] - skel_point[1])
            
            if dist_p <= sqrt2:
                j_in_range = True
            if dist_q <= sqrt2:
                n_in_range = True
            
            # If both in range of same skeleton part, connection is valid (Simba: Break(2))
            if j_in_range and n_in_range:
                return True
        
        # If one is in range but not the other, this part is invalid (Simba: if jInRange <> nInRange then Break)
        if j_in_range != n_in_range:
            break
    
    # Connection is invalid if not both nodes are in range of the same skeleton part
    return False


def _colors_in_line_ex(p: Point, q: Point, map_image: Image.Image, colors: List[int]) -> bool:
    """
    Check if line p-q contains any of the specified colors (Simba: ColorsInLineEx).
    
    Colors checked:
    - Black: (0, 0, 0) in RGB
    - Gray: (0x33, 0x33, 0x33) = (51, 51, 51) in RGB
    - Red: (255, 0, 0) in RGB or (0, 0, 255) in BGR format
    """
    img_array = np.array(map_image)
    steps = max(abs(p[0] - q[0]), abs(p[1] - q[1]))
    if steps == 0:
        return False
    
    for i in range(steps + 1):
        t = i / steps if steps > 0 else 0
        x = int(p[0] + t * (q[0] - p[0]))
        y = int(p[1] + t * (q[1] - p[1]))
        
        if 0 <= x < img_array.shape[1] and 0 <= y < img_array.shape[0]:
            if len(img_array.shape) == 3:
                pixel = tuple(img_array[y, x])
                # Check if pixel matches any color
                # Black: (0, 0, 0)
                # Gray: (51, 51, 51) = 0x333333
                # Red in RGB: (255, 0, 0) or in BGR: (0, 0, 255)
                if pixel == (0, 0, 0):
                    return True
                if pixel == (0x33, 0x33, 0x33):
                    return True
                # Red: RGB (255, 0, 0) or BGR (0, 0, 255)
                if (pixel[0] == 255 and pixel[1] == 0 and pixel[2] == 0) or \
                   (pixel[0] == 0 and pixel[1] == 0 and pixel[2] == 255):
                    return True
            else:
                if img_array[y, x] in colors:
                    return True
    
    return False


def _line_in_walkable(p: Point, q: Point, white: PointArray, spacing: int) -> bool:
    """Check if line p-q is mostly in walkable area."""
    white_set = set(white)
    steps = max(abs(p[0] - q[0]), abs(p[1] - q[1]))
    if steps == 0:
        return True
    
    walkable_count = 0
    for i in range(steps + 1):
        t = i / steps if steps > 0 else 0
        x = int(p[0] + t * (q[0] - p[0]))
        y = int(p[1] + t * (q[1] - p[1]))
        if (x, y) in white_set:
            walkable_count += 1
    
    return walkable_count / (steps + 1) > 0.7


def _path_in_skeleton(p: Point, q: Point, skeleton: PointArray, spacing: int) -> bool:
    """Check if path p-q exists in skeleton."""
    skeleton_set = set(skeleton)
    steps = max(abs(p[0] - q[0]), abs(p[1] - q[1]))
    if steps == 0:
        return True
    
    for i in range(steps + 1):
        t = i / steps if steps > 0 else 0
        x = int(p[0] + t * (q[0] - p[0]))
        y = int(p[1] + t * (q[1] - p[1]))
        
        # Check if point or nearby point is in skeleton
        nearby = False
        for dx in range(-spacing, spacing + 1):
            for dy in range(-spacing, spacing + 1):
                if (x + dx, y + dy) in skeleton_set:
                    nearby = True
                    break
            if nearby:
                break
        if not nearby:
            return False
    
    return True

