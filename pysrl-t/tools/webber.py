#!/usr/bin/env python3
"""
Webber - WebGraph Visualizer
Python translation of tools/webber.simba

Tool for visualizing webgraphs. Loads existing graphs or creates new ones,
then saves a visualization image.
"""

import sys
from pathlib import Path
import argparse

# Use non-interactive backend for saving plots
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving files

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import matplotlib.pyplot as plt

from map_loader import MapLoader, RSChunk
from webgraph import WebGraphV2, WebGraphSettings
from graph_generator import build_graph

# Configuration (matches Simba constants)
CHUNKS = [
    # Example chunks - modify as needed
    # Format: (x1, y1, x2, y2, plane)
    # ((20, 152, 24, 148), 0),
    # ((21, 151, 23, 149), 1),
]

GRAPH_OFFSET = (0, 0)
FILE_NAME = ''  # Set to load from file instead of chunks
NODES_STR = ''
PATHS_STR = ''
NAMES_STR = ''

# Graph generation settings
GENERATED_GRAPH = WebGraphSettings(
    spacing=18,
    minimum_tiles=4,
    node_radius=50,
    max_connections=6,
    wall_crossings=True
)


class WebberApp:
    """Webgraph visualizer application."""
    
    def __init__(self, chunks=None, file_name=None, nodes_str=None, paths_str=None, names_str=None):
        self.graph = WebGraphV2()
        self.map_image = None
        self.map_loader = MapLoader()
        
        # Use provided args or fall back to module-level constants
        chunks = chunks or CHUNKS
        file_name = file_name or FILE_NAME
        nodes_str = nodes_str or NODES_STR
        paths_str = paths_str or PATHS_STR
        names_str = names_str or NAMES_STR
        
        # Load map
        if file_name:
            # Load from file (not implemented in map_loader, would need custom implementation)
            print(f"Loading from file: {file_name}")
            # For now, use chunks
            if chunks:
                chunk_list = []
                for box, plane in chunks:
                    chunk_list.extend(RSChunk.box_to_chunks(box))
                self.map_image = self.map_loader.get_collision_map(chunk_list, plane=0)
        else:
            # Load from chunks
            if chunks:
                chunk_list = []
                for box, plane in chunks:
                    chunk_list.extend(RSChunk.box_to_chunks(box))
                self.map_image = self.map_loader.get_collision_map(chunk_list, plane=0)
            else:
                # Default: Varrock
                print("No chunks specified, using Varrock as default")
                chunk_list = RSChunk.box_to_chunks(RSChunk.VARROCK)
                self.map_image = self.map_loader.get_collision_map(chunk_list, plane=0)
        
        if not self.map_image:
            raise ValueError("Failed to load map")
        
        # Load or initialize graph
        if nodes_str and paths_str:
            self.graph.load_nodes_from_string(nodes_str)
            self.graph.load_paths_from_string(paths_str)
            if names_str:
                self.graph.load_names_from_string(names_str)
        else:
            # Auto-generate graph from collision map
            print("No graph provided, generating from collision map...")
            collision_array = np.array(self.map_image)
            self.graph = build_graph(collision_array, GENERATED_GRAPH)
            print(f"Generated graph with {len(self.graph.nodes)} nodes")
        
        # Ensure names array matches nodes
        while len(self.graph.names) < len(self.graph.nodes):
            self.graph.names.append('')
    
    def create_visualization(self, output_file: str = 'webber_visualization.png'):
        """Create and save visualization."""
        if not self.graph.nodes:
            print("No nodes in graph to visualize")
            return
        
        print(f"Creating visualization with {len(self.graph.nodes)} nodes...")
        
        fig, ax = plt.subplots(1, 1, figsize=(16, 16))
        
        # Draw map background first
        if self.map_image:
            img_array = np.array(self.map_image)
            h, w = img_array.shape[0], img_array.shape[1]
            # Use origin='upper' to match image coordinates (Y=0 at top)
            ax.imshow(img_array, cmap='gray', origin='upper', alpha=0.7, extent=[0, w, h, 0])
            ax.set_xlim(0, w)
            ax.set_ylim(h, 0)  # Y axis: top is 0, bottom is h
        else:
            # If no map, set limits based on nodes
            xs = [n[0] for n in self.graph.nodes]
            ys = [n[1] for n in self.graph.nodes]
            margin = 50
            ax.set_xlim(min(xs) - margin, max(xs) + margin)
            ax.set_ylim(max(ys) + margin, min(ys) - margin)
        
        # Draw connections (cyan lines)
        connection_count = 0
        for i, node in enumerate(self.graph.nodes):
            if i < len(self.graph.paths):
                for connected_idx in self.graph.paths[i]:
                    if connected_idx < len(self.graph.nodes) and connected_idx > i:  # Only draw once per pair
                        connected_node = self.graph.nodes[connected_idx]
                        ax.plot([node[0], connected_node[0]], 
                               [node[1], connected_node[1]], 
                               'c-', linewidth=0.8, alpha=0.7, zorder=2)
                        connection_count += 1
        
        # Draw doors
        if self.graph.doors:
            for door in self.graph.doors:
                # Draw door center
                ax.plot(door.center[0], door.center[1], 'm+', markersize=12, 
                       markeredgewidth=2, zorder=4)
                # Draw door line
                ax.plot([door.before[0], door.after[0]], 
                       [door.before[1], door.after[1]], 
                       'm-', linewidth=2.5, alpha=0.8, zorder=3)
        
        # Draw nodes
        regular_nodes = []
        named_nodes = []
        for i, node in enumerate(self.graph.nodes):
            if i < len(self.graph.names) and self.graph.names[i]:
                named_nodes.append(node)
            else:
                regular_nodes.append(node)
        
        if regular_nodes:
            xs = [n[0] for n in regular_nodes]
            ys = [n[1] for n in regular_nodes]
            ax.scatter(xs, ys, c='blue', s=25, alpha=0.9, 
                      zorder=5, edgecolors='darkblue', linewidths=0.5)
        
        if named_nodes:
            xs = [n[0] for n in named_nodes]
            ys = [n[1] for n in named_nodes]
            ax.scatter(xs, ys, c='orange', s=40, alpha=1.0, 
                      zorder=6, edgecolors='darkorange', linewidths=0.5)
        
        # Set aspect ratio - important for correct display
        ax.set_aspect('equal')
        
        ax.set_title('WebGraph Visualization', fontsize=16, fontweight='bold')
        ax.set_xlabel('X coordinate', fontsize=12)
        ax.set_ylabel('Y coordinate', fontsize=12)
        
        # Add legend
        handles = []
        if regular_nodes:
            handles.append(plt.Line2D([0], [0], marker='o', color='w', 
                                     markerfacecolor='blue', markersize=8, label='Nodes'))
        if named_nodes:
            handles.append(plt.Line2D([0], [0], marker='o', color='w', 
                                     markerfacecolor='orange', markersize=10, label='Named Nodes'))
        if self.graph.doors:
            handles.append(plt.Line2D([0], [0], marker='+', color='magenta', 
                                     markersize=12, label='Doors', linewidth=0))
        if connection_count > 0:
            handles.append(plt.Line2D([0], [0], color='cyan', linewidth=2, label='Connections'))
        
        if handles:
            ax.legend(handles=handles, loc='upper right', fontsize=10)
        
        # Add info text
        info_text = f"Nodes: {len(self.graph.nodes)}\n"
        info_text += f"Connections: {connection_count}\n"
        if self.graph.doors:
            info_text += f"Doors: {len(self.graph.doors)}\n"
        info_text += f"Named nodes: {len(named_nodes)}"
        
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
               fontsize=11, verticalalignment='top', family='monospace',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9, edgecolor='black'))
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"\nSaved visualization to: {output_file}")
        print(f"  Nodes: {len(self.graph.nodes)}")
        print(f"  Connections: {connection_count}")
        if self.graph.doors:
            print(f"  Doors: {len(self.graph.doors)}")
        plt.close()
    
    def get_file_string(self) -> str:
        """Get graph as string for saving."""
        result = ""
        result += f"graph.load_nodes_from_string('{self.graph.nodes_to_string()}');\n"
        result += f"graph.load_paths_from_string('{self.graph.paths_to_string()}');\n"
        result += f"graph.load_names_from_string('{self.graph.names_to_string()}');\n"
        return result
    
    def print_graph(self):
        """Print graph code to console."""
        graph_str = self.get_file_string()
        print("\n" + "="*80)
        print("GRAPH CODE (copy this to your .graph file):")
        print("="*80)
        print(graph_str)
        print("="*80 + "\n")
    
    def create_polygon_visualization(self, output_file: str = 'webber_polygons.png'):
        """Create visualization showing underlying polygons from the algorithm."""
        if not hasattr(self.graph, 'walkable_clusters') or not self.graph.walkable_clusters:
            print("No polygon data available. Generate graph first.")
            return
        
        print("Creating polygon visualization...")
        
        # Import graph generator functions to rebuild with intermediate data
        from graph_generator import (
            nr_cluster, erode_tpa, skeleton_tpa, partition_tpa
        )
        
        # Rebuild to capture intermediate data
        img_array = np.array(self.map_image)
        
        # Extract walkable pixels (same as build_graph)
        white = []
        if len(img_array.shape) == 3:
            white_mask = (img_array[:, :, 0] == 255) & (img_array[:, :, 1] == 255) & (img_array[:, :, 2] == 255)
            white_coords = np.argwhere(white_mask)
            white = [(int(coord[1]), int(coord[0])) for coord in white_coords]
        else:
            white_mask = img_array == 255
            white_coords = np.argwhere(white_mask)
            white = [(int(coord[1]), int(coord[0])) for coord in white_coords]
        
        # Get clusters
        atpa = self.graph.walkable_clusters if hasattr(self.graph, 'walkable_clusters') else nr_cluster(white, 1.0)
        
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(16, 16))
        
        # Draw map background
        if self.map_image:
            img_array = np.array(self.map_image)
            h, w = img_array.shape[0], img_array.shape[1]
            ax.imshow(img_array, cmap='gray', origin='upper', alpha=0.3, extent=[0, w, h, 0])
            ax.set_xlim(0, w)
            ax.set_ylim(h, 0)
        
        # Draw walkable clusters as polygons (convex hulls)
        try:
            from scipy.spatial import ConvexHull
            HAS_SCIPY = True
        except ImportError:
            HAS_SCIPY = False
            print("  Warning: scipy not available, using simple point visualization")
        import matplotlib.patches as patches
        
        colors = plt.cm.tab20(np.linspace(0, 1, min(20, len(atpa))))
        
        for i, cluster in enumerate(atpa[:20]):  # Limit to first 20 for visibility
            if len(cluster) < 3:
                continue
            
            if HAS_SCIPY:
                try:
                    cluster_array = np.array(cluster)
                    hull = ConvexHull(cluster_array)
                    hull_points = cluster_array[hull.vertices]
                    
                    # Create polygon patch
                    polygon = patches.Polygon(hull_points, closed=True, 
                                            facecolor=colors[i % len(colors)], 
                                            edgecolor='blue', 
                                            alpha=0.3, 
                                            linewidth=1,
                                            label=f'Cluster {i+1}' if i < 10 else None)
                    ax.add_patch(polygon)
                except Exception:
                    # If convex hull fails, just draw points
                    xs = [p[0] for p in cluster]
                    ys = [p[1] for p in cluster]
                    ax.scatter(xs, ys, c=[colors[i % len(colors)]], s=1, alpha=0.5)
            else:
                # Draw points if scipy not available
                xs = [p[0] for p in cluster]
                ys = [p[1] for p in cluster]
                ax.scatter(xs, ys, c=[colors[i % len(colors)]], s=1, alpha=0.5)
        
        # Draw skeletons for first few clusters
        for i, cluster in enumerate(atpa[:5]):  # First 5 clusters
            if len(cluster) < 10:
                continue
            
            try:
                eroded = erode_tpa(cluster, 1)
                skeleton = skeleton_tpa(eroded, 2, 7)
                
                if skeleton:
                    xs = [p[0] for p in skeleton]
                    ys = [p[1] for p in skeleton]
                    ax.scatter(xs, ys, c='yellow', s=2, alpha=0.6, 
                             label='Skeleton' if i == 0 else None, zorder=3)
            except Exception:
                pass
        
        # Draw partitions for first cluster
        if atpa:
            try:
                cluster = atpa[0]
                eroded = erode_tpa(cluster, 1)
                skeleton = skeleton_tpa(eroded, 2, 7)
                if skeleton:
                    partitions = partition_tpa(skeleton, GENERATED_GRAPH.spacing, GENERATED_GRAPH.spacing)
                    
                    partition_colors = plt.cm.Set3(np.linspace(0, 1, len(partitions)))
                    for j, partition in enumerate(partitions[:20]):  # First 20 partitions
                        if partition:
                            xs = [p[0] for p in partition]
                            ys = [p[1] for p in partition]
                            ax.scatter(xs, ys, c=[partition_colors[j % len(partition_colors)]], 
                                     s=3, alpha=0.7, marker='s',
                                     label='Partitions' if j == 0 else None, zorder=4)
            except Exception as e:
                print(f"  Could not draw partitions: {e}")
        
        # Draw final nodes
        if self.graph.nodes:
            xs = [n[0] for n in self.graph.nodes]
            ys = [n[1] for n in self.graph.nodes]
            ax.scatter(xs, ys, c='red', s=30, alpha=1.0, 
                     edgecolors='darkred', linewidths=1, 
                     label='Nodes', zorder=5)
        
        # Draw connections
        connection_count = 0
        for i, node in enumerate(self.graph.nodes):
            if i < len(self.graph.paths):
                for connected_idx in self.graph.paths[i]:
                    if connected_idx < len(self.graph.nodes) and connected_idx > i:
                        connected_node = self.graph.nodes[connected_idx]
                        ax.plot([node[0], connected_node[0]], 
                               [node[1], connected_node[1]], 
                               'cyan', linewidth=1, alpha=0.5, zorder=2)
                        connection_count += 1
        
        ax.set_aspect('equal')
        ax.set_title('WebGraph Algorithm Polygons', fontsize=16, fontweight='bold')
        ax.set_xlabel('X coordinate', fontsize=12)
        ax.set_ylabel('Y coordinate', fontsize=12)
        
        # Add legend
        ax.legend(loc='upper right', fontsize=9, ncol=2)
        
        # Add info text
        info_text = f"Clusters: {len(atpa)}\n"
        info_text += f"Nodes: {len(self.graph.nodes)}\n"
        info_text += f"Connections: {connection_count}"
        
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
               fontsize=11, verticalalignment='top', family='monospace',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9, edgecolor='black'))
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"\nSaved polygon visualization to: {output_file}")
        print(f"  Clusters: {len(atpa)}")
        print(f"  Nodes: {len(self.graph.nodes)}")
        print(f"  Connections: {connection_count}")
        plt.close()
    
    def run(self, output_file: str = 'webber_visualization.png', print_code: bool = False, 
            polygon_viz: bool = False):
        """Run the application."""
        if print_code:
            self.print_graph()
        
        self.create_visualization(output_file)
        
        if polygon_viz:
            self.create_polygon_visualization(output_file.replace('.png', '_polygons.png'))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='WebGraph Visualizer - Create visualization images from webgraphs')
    parser.add_argument('--output', '-o', default='webber_visualization.png',
                       help='Output file path (default: webber_visualization.png)')
    parser.add_argument('--print', '-p', action='store_true',
                       help='Print graph code to console')
    parser.add_argument('--nodes', type=str, help='Nodes string (base64 encoded)')
    parser.add_argument('--paths', type=str, help='Paths string (base64 encoded)')
    parser.add_argument('--names', type=str, help='Names string (base64 encoded)')
    parser.add_argument('--chunks', type=str, help='Chunks to load (format: "x1,y1,x2,y2,plane")')
    parser.add_argument('--polygons', action='store_true',
                       help='Also create polygon visualization showing algorithm internals')
    
    args = parser.parse_args()
    
    try:
        chunks = None
        if args.chunks:
            # Parse chunks from string
            parts = args.chunks.split(',')
            if len(parts) == 5:
                x1, y1, x2, y2, plane = map(int, parts)
                chunks = [((x1, y1, x2, y2), plane)]
        
        app = WebberApp(
            chunks=chunks,
            nodes_str=args.nodes,
            paths_str=args.paths,
            names_str=args.names
        )
        app.run(output_file=args.output, print_code=args.print, polygon_viz=args.polygons)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
