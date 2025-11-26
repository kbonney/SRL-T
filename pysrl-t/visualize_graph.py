"""
Visualize webgraph on top of the map.
"""

import sys
import os
import json
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Handle imports
if __name__ == '__main__' or not __package__:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from map_loader import MapLoader, RSChunk
    from webgraph import WebGraphV2, WebGraphSettings
else:
    from .map_loader import MapLoader, RSChunk
    from .webgraph import WebGraphV2, WebGraphSettings


def load_graph_from_json(json_file: str) -> WebGraphV2:
    """Load graph from JSON file."""
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    graph = WebGraphV2()
    graph.load_nodes_from_string(data['nodes'])
    graph.load_paths_from_string(data['paths'])
    graph.load_names_from_string(data['names'])
    graph.load_doors_from_string(data['doors'])
    
    return graph


def visualize_graph_on_map(json_file: str, output_image: str = None, 
                           show_map: bool = True, show_nodes: bool = True,
                           show_connections: bool = True, show_doors: bool = True):
    """
    Visualize webgraph on top of the map.
    
    Args:
        json_file: JSON file containing graph data (should have 'region' and 'box' fields)
        output_image: Output image file (default: {json_file}_visualization.png)
        show_map: Whether to show the collision map background
        show_nodes: Whether to show graph nodes
        show_connections: Whether to show connections between nodes
        show_doors: Whether to show doors
    """
    # Load graph data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Load graph
    graph = WebGraphV2()
    graph.load_nodes_from_string(data['nodes'])
    graph.load_paths_from_string(data['paths'])
    graph.load_names_from_string(data['names'])
    if 'doors' in data:
        graph.load_doors_from_string(data['doors'])
    
    # Load map if needed
    map_image = None
    if show_map and 'box' in data and 'plane' in data:
        loader = MapLoader()
        box = data['box']
        plane = data.get('plane', 0)
        chunks = RSChunk.box_to_chunks(box)
        map_image = loader.get_collision_map(chunks, plane=plane)
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(16, 16))
    
    # Show map background
    if map_image and show_map:
        ax.imshow(np.array(map_image), cmap='gray', origin='upper', alpha=0.7)
        ax.set_title(f"Webgraph Visualization - {data.get('region', 'Unknown')}", fontsize=16)
    else:
        # If no map, create a black background
        if graph.nodes:
            xs = [n[0] for n in graph.nodes]
            ys = [n[1] for n in graph.nodes]
            width = max(xs) - min(xs) + 100
            height = max(ys) - min(ys) + 100
            ax.set_xlim(min(xs) - 50, max(xs) + 50)
            ax.set_ylim(max(ys) + 50, min(ys) - 50)  # Invert Y axis
            ax.set_facecolor('black')
            ax.set_title(f"Webgraph Visualization - {data.get('region', 'Unknown')}", fontsize=16)
    
    # Draw connections
    if show_connections and graph.nodes and graph.paths:
        for i, node in enumerate(graph.nodes):
            if i < len(graph.paths):
                for connected_idx in graph.paths[i]:
                    if connected_idx < len(graph.nodes):
                        connected_node = graph.nodes[connected_idx]
                        ax.plot([node[0], connected_node[0]], 
                               [node[1], connected_node[1]], 
                               'c-', linewidth=0.5, alpha=0.6)
    
    # Draw doors
    if show_doors and graph.doors:
        for door in graph.doors:
            # Draw door center
            ax.plot(door.center[0], door.center[1], 'm+', markersize=10, markeredgewidth=2)
            # Draw door line
            ax.plot([door.before[0], door.after[0]], 
                   [door.before[1], door.after[1]], 
                   'm-', linewidth=2, alpha=0.8)
    
    # Draw nodes
    if show_nodes and graph.nodes:
        # Regular nodes
        regular_nodes = []
        named_nodes = []
        for i, node in enumerate(graph.nodes):
            if i < len(graph.names) and graph.names[i]:
                named_nodes.append(node)
            else:
                regular_nodes.append(node)
        
        if regular_nodes:
            xs = [n[0] for n in regular_nodes]
            ys = [n[1] for n in regular_nodes]
            ax.scatter(xs, ys, c='blue', s=20, alpha=0.8, label='Nodes', zorder=5)
        
        if named_nodes:
            xs = [n[0] for n in named_nodes]
            ys = [n[1] for n in named_nodes]
            ax.scatter(xs, ys, c='orange', s=30, alpha=0.9, label='Named Nodes', zorder=6)
    
    # Set aspect ratio and invert Y axis (image coordinates)
    ax.set_aspect('equal')
    ax.invert_yaxis()
    
    # Add legend
    if show_nodes or show_doors:
        ax.legend(loc='upper right')
    
    # Add info text
    info_text = f"Nodes: {len(graph.nodes)}\n"
    info_text += f"Connections: {sum(len(p) for p in graph.paths) // 2}\n"
    if graph.doors:
        info_text += f"Doors: {len(graph.doors)}"
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
           fontsize=10, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    
    # Save or show
    if output_image is None:
        output_image = Path(json_file).with_suffix('.png').name.replace('.png', '_visualization.png')
    
    plt.savefig(output_image, dpi=150, bbox_inches='tight')
    print(f"Saved visualization to: {output_image}")
    
    plt.show()


# Example usage
if __name__ == '__main__':
    # Visualize Varrock graph
    json_file = '../varrock_graph.json'
    
    if not os.path.exists(json_file):
        # Try current directory
        json_file = 'varrock_graph.json'
    
    if os.path.exists(json_file):
        visualize_graph_on_map(
            json_file,
            output_image='varrock_graph_visualization.png',
            show_map=True,
            show_nodes=True,
            show_connections=True,
            show_doors=True
        )
    else:
        print(f"Error: Graph file not found: {json_file}")
        print("Please generate a graph first using generate_from_osrs.py")

