#!/usr/bin/env python3
"""
Command-line tool to generate webgraphs from map images.
"""

import argparse
import json
from pathlib import Path
from PIL import Image

import sys
import os

# Add parent directory to path for script execution
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Handle imports for both package and script execution
if __name__ == '__main__' or not __package__:
    from webgraph import WebGraphV2, WebGraphSettings
    from graph_generator import build_graph
else:
    from .webgraph import WebGraphV2, WebGraphSettings
    from .graph_generator import build_graph


# Example: Generate graph from a map image
if __name__ == '__main__':
    # Configure input file
    input_file = 'test_map.png'  # Change this to your map image
    
    # Load image
    print(f"Loading image: {input_file}")
    image = Image.open(input_file)
    
    # Create settings
    settings = WebGraphSettings(
        spacing=18,
        minimum_tiles=4,
        node_radius=50,
        max_connections=6,
        wall_crossings=True
    )
    
    print(f"Generating webgraph with settings:")
    print(f"  Spacing: {settings.spacing}")
    print(f"  Minimum tiles: {settings.minimum_tiles}")
    print(f"  Node radius: {settings.node_radius}")
    print(f"  Max connections: {settings.max_connections}")
    print(f"  Wall crossings: {settings.wall_crossings}")
    
    # Generate graph
    graph = build_graph(image, settings)
    
    print(f"Generated graph with {len(graph.nodes)} nodes, {len(graph.doors)} doors")
    
    # Save to JSON
    input_path = Path(input_file)
    output_path = input_path.with_suffix('.json')
    
    graph_data = {
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
    
    with open(output_path, 'w') as f:
        json.dump(graph_data, f, indent=2)
    
    print(f"Saved graph to: {output_path}")

