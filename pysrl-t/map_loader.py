"""
Map loader for Old School RuneScape maps.
Loads collision maps from ZIP files containing chunk images.
Based on SRL-T's maploader.simba
"""

import zipfile
import os
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import numpy as np


class MapType:
    """Map type enumeration."""
    NORMAL = "normal"
    HEIGHT = "height"
    COLLISION = "collision"


class MapLoader:
    """Loader for OSRS map chunks from ZIP files."""
    
    # Chunk side calculation from translator.simba:
    # TileSize = 4, RSMap.ChunkSide = 64
    # Map.ChunkSide = TileSize * RSMap.ChunkSide = 4 * 64 = 256
    CHUNK_SIDE = 256  # Map chunk size in pixels (4 * 64)
    RS_CHUNK_SIDE = 64  # RS chunk size in tiles
    TILE_SIZE = 4  # Pixels per tile
    MAP_HEIGHT_CHUNKS = 200  # Map height in chunks (used for Y inversion: 199 - y)
    
    def __init__(self, map_path: str = None, cache_dir: str = None):
        """
        Initialize map loader.
        
        Args:
            map_path: Path to directory containing map ZIP files (default: osr/map/files)
            cache_dir: Directory for caching extracted chunks (default: cache/)
        """
        if map_path is None:
            # Default to SRL-T map directory
            script_dir = Path(__file__).parent.parent
            map_path = str(script_dir / "osr" / "map" / "files")
        
        self.map_path = Path(map_path)
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_chunk_filename(self, chunk: Tuple[int, int], plane: int = 0) -> str:
        """Get chunk filename in format: {x}-{y}.png"""
        return f"{chunk[0]}-{chunk[1]}.png"
    
    def get_zip_path(self, map_type: str) -> Path:
        """Get path to ZIP file for map type."""
        zip_files = {
            MapType.NORMAL: "map.zip",
            MapType.HEIGHT: "heightmap.zip",
            MapType.COLLISION: "collision.zip"
        }
        return self.map_path / zip_files.get(map_type, "collision.zip")
    
    def get_cache_path(self, chunk: Tuple[int, int], plane: int, map_type: str) -> Path:
        """Get cache path for a chunk."""
        chunk_name = self.get_chunk_filename(chunk, plane)
        
        if map_type == MapType.HEIGHT:
            # Height maps always use plane 0 in cache
            cache_subdir = self.cache_dir / "heightmap" / "0"
        else:
            cache_subdir = self.cache_dir / map_type / str(plane)
        
        cache_subdir.mkdir(parents=True, exist_ok=True)
        return cache_subdir / chunk_name
    
    def extract_chunk(self, chunk: Tuple[int, int], plane: int, map_type: str) -> Optional[Image.Image]:
        """
        Extract a chunk from ZIP file.
        
        Args:
            chunk: Chunk coordinates (x, y)
            plane: Map plane (0-3)
            map_type: Type of map (NORMAL, HEIGHT, COLLISION)
        
        Returns:
            PIL Image of the chunk, or None if not found
        """
        cache_path = self.get_cache_path(chunk, plane, map_type)
        
        # Check cache first
        if cache_path.exists():
            try:
                return Image.open(cache_path)
            except Exception as e:
                print(f"Warning: Failed to load cached chunk {chunk}: {e}")
        
        # Extract from ZIP
        zip_path = self.get_zip_path(map_type)
        if not zip_path.exists():
            print(f"Warning: ZIP file not found: {zip_path}")
            return None
        
        chunk_name = self.get_chunk_filename(chunk, plane)
        
        # For height maps, always use plane 0 in ZIP
        if map_type == MapType.HEIGHT:
            zip_file_path = f"0/{chunk_name}"
        else:
            zip_file_path = f"{plane}/{chunk_name}"
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                if zip_file_path not in zip_file.namelist():
                    # Chunk doesn't exist, create empty chunk (matches Simba: SetSize(ChunkSide, ChunkSide))
                    print(f"Warning: Chunk {zip_file_path} not found in ZIP, creating empty chunk")
                    img = Image.new('RGB', (self.CHUNK_SIDE, self.CHUNK_SIDE), color='black')
                else:
                    # Extract to memory
                    data = zip_file.read(zip_file_path)
                    from io import BytesIO
                    img = Image.open(BytesIO(data))
                    
                    # Ensure image is the correct size (should be CHUNK_SIDE x CHUNK_SIDE = 256x256)
                    if img.size != (self.CHUNK_SIDE, self.CHUNK_SIDE):
                        # Resize if needed (shouldn't happen, but handle it)
                        img = img.resize((self.CHUNK_SIDE, self.CHUNK_SIDE), Image.Resampling.LANCZOS)
                
                # Cache the image
                img.save(cache_path)
                return img
        except Exception as e:
            print(f"Error extracting chunk {chunk} from {zip_path}: {e}")
            return None
    
    def get_chunks(self, start: Tuple[int, int], finish: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Get list of chunk coordinates between start and finish.
        
        Args:
            start: Starting chunk coordinates (x, y)
            finish: Ending chunk coordinates (x, y)
        
        Returns:
            List of chunk coordinates
        """
        chunks = []
        x1, y1 = start
        x2, y2 = finish
        
        # Ensure x1 <= x2 and y1 <= y2
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                chunks.append((x, y))
        
        return chunks
    
    def get_map(self, chunks: List[Tuple[int, int]], plane: int = 0, 
                map_type: str = MapType.COLLISION) -> Optional[Image.Image]:
        """
        Get a combined map from multiple chunks.
        Matches Simba implementation: y := 199 - chunks[i].Y for coordinate transformation.
        
        Args:
            chunks: List of chunk coordinates
            plane: Map plane (0-3)
            map_type: Type of map (NORMAL, HEIGHT, COLLISION)
        
        Returns:
            Combined PIL Image, or None if no chunks could be loaded
        """
        if not chunks:
            return None
        
        # Transform chunks: invert Y coordinate (matches Simba: y := 199 - chunks[i].Y)
        # Note: Using MAP_HEIGHT_CHUNKS - 1 = 199 for the transformation
        transformed_chunks = []
        for chunk in chunks:
            x, y = chunk
            # Transform Y: invert it (199 - y in Simba)
            transformed_y = (self.MAP_HEIGHT_CHUNKS - 1) - y
            transformed_chunks.append((x, transformed_y, chunk))  # Store (x, transformed_y, original_chunk)
        
        # Calculate dimensions from transformed coordinates
        xs = [tc[0] for tc in transformed_chunks]
        ys = [tc[1] for tc in transformed_chunks]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        # Size calculation matches Simba: (hi.X-lo.X) * n + 1 + n
        # where n = CHUNK_SIDE
        width = (max_x - min_x) * self.CHUNK_SIDE + 1 + self.CHUNK_SIDE
        height = (max_y - min_y) * self.CHUNK_SIDE + 1 + self.CHUNK_SIDE
        
        # Create combined image
        combined = Image.new('RGB', (width, height), color='black')
        
        loaded_any = False
        for x, transformed_y, original_chunk in transformed_chunks:
            img = self.extract_chunk(original_chunk, plane, map_type)
            if img is None:
                continue
            
            loaded_any = True
            
            # Calculate position in combined image (matches Simba positioning)
            x_offset = (x - min_x) * self.CHUNK_SIDE
            y_offset = (transformed_y - min_y) * self.CHUNK_SIDE
            
            # Paste chunk into combined image
            combined.paste(img, (x_offset, y_offset))
        
        if not loaded_any:
            return None
        
        return combined
    
    def get_map_from_coords(self, start: Tuple[int, int], finish: Tuple[int, int],
                           plane: int = 0, map_type: str = MapType.COLLISION) -> Optional[Image.Image]:
        """
        Get a map from chunk coordinate range.
        
        Args:
            start: Starting chunk coordinates (x, y)
            finish: Ending chunk coordinates (x, y)
            plane: Map plane (0-3)
            map_type: Type of map (NORMAL, HEIGHT, COLLISION)
        
        Returns:
            Combined PIL Image, or None if no chunks could be loaded
        """
        chunks = self.get_chunks(start, finish)
        return self.get_map(chunks, plane, map_type)
    
    def get_collision_map(self, chunks: List[Tuple[int, int]], plane: int = 0) -> Optional[Image.Image]:
        """Get collision map (convenience method)."""
        return self.get_map(chunks, plane, MapType.COLLISION)
    
    def get_collision_map_from_coords(self, start: Tuple[int, int], finish: Tuple[int, int],
                                     plane: int = 0) -> Optional[Image.Image]:
        """Get collision map from coordinates (convenience method)."""
        return self.get_map_from_coords(start, finish, plane, MapType.COLLISION)


# Example usage and common chunk definitions
class RSChunk:
    """Common OSRS chunk definitions (from rschunk.simba).
    
    Chunks are defined as Box(x1, y1, x2, y2) where:
    - x1, y1: top-left chunk coordinates
    - x2, y2: bottom-right chunk coordinates
    """
    
    # Chunk definitions as Box(x1, y1, x2, y2)
    VARROCK = (49, 54, 50, 53)  # Box(49, 54, 50, 53)
    LUMBRIDGE = (49, 51, 50, 49)  # Box(49, 51, 50, 49)
    FALADOR = (45, 53, 47, 51)  # Box(45, 53, 47, 51)
    EDGEVILLE = (48, 54, 48, 54)  # Box(48, 54, 48, 54)
    AL_KHARID = (50, 51, 53, 48)  # Box(50, 51, 53, 48)
    ARDOUGNE = (40, 52, 41, 51)
    CASTLE_WARS = (37, 48, 38, 47)
    CATHERBY = (43, 54, 44, 53)
    DRAYNOR_VILLAGE = (47, 51, 48, 50)
    
    @staticmethod
    def box_to_chunks(box: Tuple[int, int, int, int]) -> List[Tuple[int, int]]:
        """Convert Box(x1, y1, x2, y2) to list of chunk coordinates.
        
        Note: Box coordinates may have y1 > y2 due to coordinate system,
        so we normalize the range.
        """
        x1, y1, x2, y2 = box
        chunks = []
        # Ensure ranges are correct (handle inverted coordinates)
        x_min, x_max = min(x1, x2), max(x1, x2)
        y_min, y_max = min(y1, y2), max(y1, y2)
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                chunks.append((x, y))
        return chunks


def example_load_map():
    """Example of loading a map."""
    loader = MapLoader()
    
    # Load Varrock collision map
    print("Loading Varrock collision map...")
    chunks = RSChunk.box_to_chunks(RSChunk.VARROCK)
    print(f"Chunks: {chunks}")
    
    collision_map = loader.get_collision_map(chunks, plane=0)
    if collision_map:
        print(f"Loaded map: {collision_map.size}")
        collision_map.save("varrock_collision.png")
        print("Saved to varrock_collision.png")
        
        # Now you can use this with build_graph
        try:
            from graph_generator import build_graph, WebGraphSettings
            
            settings = WebGraphSettings()
            print("Generating webgraph...")
            graph = build_graph(collision_map, settings)
            print(f"Generated graph with {len(graph.nodes)} nodes, {len(graph.doors)} doors")
        except ImportError:
            print("graph_generator not available")
    else:
        print("Failed to load map")


if __name__ == '__main__':
    example_load_map()

