#!/usr/bin/env python3
"""
Example usage of the webgraph generator.
"""

from PIL import Image
import json
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


def example_basic():
    """Basic example of generating and using a webgraph."""
    print("Example: Basic webgraph generation")
    
    # Create a simple test image (white walkable area)
    # In practice, you would load an actual map image
    print("Note: This example requires an actual map image file")
    print("Usage: python example.py <map_image.png>")
    
    import sys
    if len(sys.argv) < 2:
        print("\nCreating a simple test image...")
        # Create a simple test image
        img = Image.new('RGB', (200, 200), color='black')
        pixels = img.load()
        
        # Create a white walkable area
        for x in range(50, 150):
            for y in range(50, 150):
                pixels[x, y] = (255, 255, 255)
        
        img.save('test_map.png')
        print("Created test_map.png")
        image = img
    else:
        image = Image.open(sys.argv[1])
    
    # Configure settings
    settings = WebGraphSettings(
        spacing=18,
        minimum_tiles=4,
        node_radius=50,
        max_connections=6,
        wall_crossings=True
    )
    
    print(f"\nGenerating webgraph...")
    print(f"Settings: spacing={settings.spacing}, min_tiles={settings.minimum_tiles}")
    
    # Generate graph
    graph = build_graph(image, settings)
    
    print(f"\nGenerated graph:")
    print(f"  Nodes: {len(graph.nodes)}")
    print(f"  Doors: {len(graph.doors)}")
    print(f"  Walkable space: {len(graph.walkable_space)} points")
    
    # Example: Find path between two points
    if len(graph.nodes) >= 2:
        print(f"\nFinding path between first and last node...")
        try:
            path = graph.path_between(graph.nodes[0], graph.nodes[-1])
            print(f"  Path found with {len(path)} waypoints")
            print(f"  Start: {path[0]}")
            print(f"  End: {path[-1]}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Save graph
    output_file = 'example_graph.json'
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
    
    with open(output_file, 'w') as f:
        json.dump(graph_data, f, indent=2)
    
    print(f"\nSaved graph to: {output_file}")
    
    # Load graph back
    print(f"\nLoading graph from file...")
    graph2 = WebGraphV2()
    graph2.load_nodes_from_string(graph_data['nodes'])
    graph2.load_paths_from_string(graph_data['paths'])
    graph2.load_names_from_string(graph_data['names'])
    graph2.load_doors_from_string(graph_data['doors'])
    
    print(f"Loaded graph with {len(graph2.nodes)} nodes")


if __name__ == '__main__':
    example_basic()

