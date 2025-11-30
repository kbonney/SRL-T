# Webber - Interactive WebGraph Editor

Python translation of the Simba `webber.simba` tool for manually creating and editing webgraphs.

## Overview

Webber is an interactive GUI tool for creating and editing webgraphs used for pathfinding in Old School RuneScape maps. It provides a visual interface to:

- Add nodes by clicking on the map
- Connect nodes together
- Move nodes by dragging
- Name nodes for landmarks
- Test paths between nodes
- Export graph code for use in scripts

## Installation

Make sure you have the required dependencies:

```bash
pip install matplotlib numpy pillow
```

## Usage

### Basic Usage

```bash
cd pysrl-t/tools
python webber.py
```

### Configuration

Edit the constants at the top of `webber.py`:

```python
# Define chunks to load
CHUNKS = [
    ((49, 54, 50, 53), 0),  # Varrock
    ((49, 51, 50, 49), 0),  # Lumbridge
]

# Or load from a file
FILE_NAME = 'my_map.png'

# Load existing graph (optional)
NODES_STR = '...'
PATHS_STR = '...'
NAMES_STR = '...'
```

## Controls

- **Click**: Add a new node or select an existing node
- **Click + Drag**: Move the selected node
- **Shift + Click**: Connect the selected node to the clicked node
- **Shift + Ctrl + Move**: Test path from selected node to nearest node under cursor
- **Delete Key**: Remove the selected node
- **Right Click + Drag**: Pan around the map (matplotlib default)
- **Mouse Wheel**: Zoom in/out (matplotlib default)

## UI Buttons

- **Drag mode**: Enable selection box mode (for future features)
- **Name Node**: Open dialog to name the selected node
- **UnSelect Node**: Deselect the current node
- **Print Graph**: Output graph code to console (copy this to your `.graph` file)

## Output

When you close the window, the tool will:

1. Print the graph code to the console (if you clicked "Print Graph")
2. Create a visualization image (`webber_visualization.png`)

The graph code can be saved to a `.graph` file and included in your scripts:

```python
# In your script
from pysrl_t import WebGraphV2

graph = WebGraphV2()
graph.load_nodes_from_string('...')
graph.load_paths_from_string('...')
graph.load_names_from_string('...')
```

## Features

- **Interactive editing**: Click to add, drag to move, connect nodes visually
- **Path testing**: Test paths between nodes in real-time
- **Node naming**: Name important nodes for landmarks
- **Visual feedback**: 
  - Blue dots = regular nodes
  - Orange dots = named nodes
  - Red square = selected node
  - Cyan lines = connections
  - Navy line = test path
- **Automatic visualization**: Creates final visualization image on exit

## Differences from Simba Version

- Uses matplotlib instead of Simba's GUI framework
- Keyboard shortcuts may differ slightly
- Visualization is automatically created at the end
- Uses Python's tkinter for input dialogs

## Troubleshooting

### Graph area not responding to clicks

- Make sure you click on the map area (not the buttons)
- The figure window needs to be focused for keyboard events

### Path testing not working

- Make sure you hold Shift+Ctrl while moving the mouse (not clicking)
- A node must be selected first

### Map not loading

- Check that `collision.zip` exists in `osr/map/files/`
- Verify chunk coordinates are correct
- Check console for error messages

## Example Workflow

1. Run `python webber.py`
2. Click on the map to add nodes at key locations
3. Select a node, then Shift+Click another node to connect them
4. Name important nodes using "Name Node" button
5. Test paths by selecting a node and Shift+Ctrl+Move to another
6. Click "Print Graph" to get the code
7. Copy the code to a `.graph` file
8. Close the window to generate visualization

