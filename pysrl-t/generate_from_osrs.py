"""
Generate webgraph from OSRS map chunks.
This script loads collision maps from the OSRS map ZIP files and generates webgraphs.
"""

import sys
import os
import json
from typing import Optional
import matplotlib
import matplotlib.pyplot as plt
# matplotlib.use('Agg')  # Non-interactive backend for saving files


# Handle imports
if __name__ == '__main__' or not __package__:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from map_loader import MapLoader, RSChunk
    from graph_generator import build_graph, WebGraphSettings
    from webgraph import WebGraphV2
else:
    from .map_loader import MapLoader, RSChunk
    from .graph_generator import build_graph, WebGraphSettings
    from .webgraph import WebGraphV2


def generate_graph_for_region(region_name: str, box: tuple, plane: int = 0, 
                              output_file: Optional[str] = None, settings: Optional[WebGraphSettings] = None):
    """
    Generate webgraph for a specific OSRS region.
    
    Args:
        region_name: Name of the region
        box: Box coordinates (x1, y1, x2, y2)
        plane: Map plane (0-3)
        output_file: Output JSON file path (default: {region_name}_graph.json)
        settings: Graph generation settings (default: WebGraphSettings())
    """
    if settings is None:
        settings = WebGraphSettings()
    
    if output_file is None:
        output_file = f"{region_name.lower()}_graph.json"
    
    print(f"Generating webgraph for {region_name}...")
    print(f"  Box: {box}")
    print(f"  Plane: {plane}")
    
    # Load map
    loader = MapLoader()
    chunks = RSChunk.box_to_chunks(box)
    print(f"  Chunks: {len(chunks)}")
    
    collision_map = loader.get_collision_map(chunks, plane=plane)
    if not collision_map:
        print(f"Error: Failed to load collision map for {region_name}")
        return None
    
    print(f"  Map size: {collision_map.size}")
    
    # Generate graph
    print("  Generating graph...")
    graph = build_graph(collision_map, settings)
    
    # Plot map colored by clusters
    import numpy as np
    width, height = collision_map.size
    cluster_image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Generate colors for each cluster
    num_clusters = len(graph.walkable_clusters)
    colors = plt.cm.tab20(np.linspace(0, 1, num_clusters))[:, :3]  # Get RGB values
    colors = (colors * 255).astype(np.uint8)
    
    # Color each cluster
    for i, cluster in enumerate(graph.walkable_clusters):
        color = colors[i % len(colors)]
        for x, y in cluster:
            if 0 <= x < width and 0 <= y < height:
                cluster_image[y, x] = color
    
    # Display the plot
    plt.figure(figsize=(12, 12))
    plt.imshow(cluster_image, origin='upper')
    plt.title(f'{region_name} - Clusters ({num_clusters} clusters)')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(f'{region_name.lower()}_clusters.png', dpi=150, bbox_inches='tight')
    print(f"  Saved cluster visualization to: {region_name.lower()}_clusters.png")
    plt.close()
    
    print(f"  Generated: {len(graph.nodes)} nodes, {len(graph.doors)} doors")
    
    # Save graph
    graph_data = {
        'region': region_name,
        'box': box,
        'plane': plane,
        'nodes': graph.nodes_to_string(),
        'paths': graph.paths_to_string(),
        'names': graph.names_to_string(),
        'doors': graph.doors_to_string(),
        'settings': {
            'spacing': settings.spacing,
            'minimum_tiles': settings.minimum_tiles,
            'node_radius': settings.node_radius,
            'max_connections': settings.max_connections,
            'wall_crossings': settings.wall_crossings
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(graph_data, f, indent=2)
    
    print(f"  Saved to: {output_file}")
    
    return (graph, collision_map)


# Example: Generate graph for Varrock
if __name__ == '__main__':
    # Configure settings
    settings = WebGraphSettings(
        spacing=18,
        minimum_tiles=4,
        node_radius=50,
        max_connections=6,
        wall_crossings=True
    )
    
    # Generate graph for Varrock5
    result = generate_graph_for_region(
        'varrock',
        RSChunk.VARROCK,
        plane=0,
        settings=settings
    )
    
    # Create visualization
    if result:
        graph, collision_map = result
        try:
            from visualize_graph import visualize_graph_on_map
            visualize_graph_on_map(
                'varrock_graph.json',
                output_image='varrock_graph_visualization.png',
                show_map=True,
                show_nodes=True,
                show_connections=True,
                show_doors=True
            )
        except ImportError:
            print("Note: matplotlib not available, skipping visualization")
    
    # Generate more regions
    result = generate_graph_for_region('lumbridge', RSChunk.LUMBRIDGE, plane=0, settings=settings)
    if result:
        try:
            from visualize_graph import visualize_graph_on_map
            visualize_graph_on_map(
                'lumbridge_graph.json',
                output_image='lumbridge_graph_visualization.png',
                show_map=True,
                show_nodes=True,
                show_connections=True,
                show_doors=True
            )
        except ImportError:
            pass
    
    result = generate_graph_for_region('falador', RSChunk.FALADOR, plane=0, settings=settings)
    if result:
        try:
            from visualize_graph import visualize_graph_on_map
            visualize_graph_on_map(
                'falador_graph.json',
                output_image='falador_graph_visualization.png',
                show_map=True,
                show_nodes=True,
                show_connections=True,
                show_doors=True
            )
        except ImportError:
            pass

