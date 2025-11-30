Reviewing key files to understand the repository's structure and purpose.


[4 tools called]


Exploring major components to understand how they fit together:


[5 tools called]


Reviewing interface and finder components:


[4 tools called]


Checking a few more components to complete the picture:


[3 tools called]


## Overview

SRL-T (SRL Resource Library - T variant) is a library for writing automation scripts in Simba for Old School RuneScape. It's a fork/alternative to the official SRL-Development, used by WaspLib and WaspScripts. It provides APIs for interacting with the game client programmatically.

## Core Architecture

The library uses a modular include system. The main entry point (`osr.simba`) conditionally includes modules to avoid duplicate includes. It builds on a base utilities layer (`utils.simba`) that provides geometry, math, string handling, and system utilities.

## Major Components

### 1. Client Detection & Input System (`osr/rsclient.simba`)

- Detects client type (Official, RuneLite, Legacy) and mode (Fixed, Resizable Classic, Resizable Modern)
- Handles window dimensions and bounds
- Integrates with RemoteInput plugin for direct client interaction
- Supports drawing debug overlays on the client

### 2. Positioning & Navigation Systems

#### Walker System (`osr/walker/walker.simba`)
- RSWalker (RSW) for accurate positioning and walking
- Works by:
  1. Loading a large map image covering the region
  2. Capturing and processing the minimap (rotating north, removing player/NPC/item dots)
  3. Template matching the minimap against the map image to find position
  4. Using this position for tile targeting and navigation
- Features:
  - ScreenWalk: uses mainscreen instead of minimap
  - AdaptiveWalk: switches between minimap and mainscreen based on distance
  - WebGraph integration for pathfinding
  - Energy-based run toggling

#### Map System (`osr/map/map.simba`)
- TRSMap for positioning with heightmap support
- Tracks X, Y, Z (height), and Plane
- Uses TRSWalkerV2 internally
- Supports region-based maps and filtering

#### WebGraph System (`utils/webgraphv2.simba`)
- Pathfinding for web walking
- Handles doors (normal, wide, separating)
- Calculates door angles and compass directions
- Does not handle obstacles (as noted in README)

#### MM2MS (Minimap to Mainscreen) (`osr/mm2ms.simba`)
- Projects coordinates between minimap and mainscreen
- Supports rotation, zoom, and resizable clients
- Uses calibrated projectors for fixed and resizable modes
- Enables accurate tile hovering on the mainscreen

### 3. OCR System (`osr/ocr/ocr.simba`)

- Uses libsimpleocr plugin
- Loads RuneScape font sets:
  - Plain 11, Plain 12
  - Bold 12, Bold 12 Shadow
  - Quill 8, Quill
- Font files stored in `osr/ocr/fonts/` (1375+ bitmap files)
- Enables text reading from the game client

### 4. Interface System (`osr/interfaces/`)

Modular interface handling:

- Core (`core/interface.simba`): Base interface detection with color-based button finding
- Game Tabs (`gametabs/`): Inventory, Equipment, Combat, Magic, Prayer, Stats, Options, Logout, Music, Emotes
- Main Screen (`mainscreen/`): Bank, Bank PIN, Grand Exchange, Deposit Box
- Chat (`chat/`): Chat interface and buttons
- Login (`login.simba`): Login screen handling
- Minimap (`minimap.simba`): Minimap interface
- XP Bar (`xpbar.simba`): Experience bar tracking

Each interface uses color matching (CTS1) and alignment-based detection to locate UI elements.

### 5. Finder Systems

#### Item Finder (`osr/finders/itemfinder/itemfinder.simba`)
- Finds item sprites/bitmaps in specified boxes
- Uses hash-based matching for fast lookup
- Database system for item ID/name mapping
- Custom filters for item detection
- Similarity threshold (default 0.999)

#### Spell Finder (`osr/finders/spellfinder/spellfinder.simba`)
- Finds spell icons in the magic interface
- Uses image matching similar to item finder

### 6. Input System

#### Mouse (`utils/input/mouse.simba`)
- Uses libasyncmouse plugin
- Human-like movement with gravity/wind algorithms
- Distributions: Random, Gaussian, Skewed, ROWP
- Configurable speed, miss chance, idle intervals
- Callbacks for movement and teleport events

#### Keyboard (`utils/input/keyboard.simba`)
- Key press simulation with configurable delays
- Sentence delays for typing
- Virtual key code support

#### RemoteInput (`osr/remoteinput.simba`)
- Uses libremoteinput plugin
- Direct client injection (EIOS-based)
- Can disable real input for safety
- Cross-platform support (Windows, Linux, macOS, ARM)

### 7. Utility Systems

#### Geometry (`utils/geometry/`)
- TPoint, TPointArray, TBox, TBoxArray, TRectangle, TCircle, TCuboid, Vector
- Geometric operations and transformations

#### Math (`utils/math/`)
- Color matching (CTS1)
- Matrix operations
- Pixel shift detection
- Random number generation
- OTP (One-Time Pad) for encryption
- RSTranslator for coordinate transformations

#### System (`utils/system/`)
- File operations
- Database (SimpleDatabase)
- HTTP requests
- Time utilities

### 8. Anti-Ban (`osr/antiban.simba`)

- Random tab switching
- Random mouse movements
- Human-like delays
- Other anti-detection behaviors

### 9. Key Bindings (`osr/keybindings.simba`)

- Manages in-game key bindings
- Allows scripts to use configured hotkeys

## How Components Fit Together

1. Initialization: `osr.simba` includes modules in dependency order, starting with utilities, then client detection, then interfaces and specialized systems.

2. Client Setup: RSClient detects the client type/mode and sets up RemoteInput if enabled, establishing communication with the game.

3. Positioning: Walker/Map systems use minimap template matching against loaded map images to determine position, enabling accurate navigation.

4. Navigation: WebGraph calculates paths between points. Walker executes movement using MM2MS for accurate tile targeting, switching between minimap and mainscreen as needed.

5. Interaction: Interface system locates UI elements via color matching. OCR reads text. Finders locate items/spells. Mouse/Keyboard simulate human-like input.

6. Automation Flow: Scripts use these components together—e.g., find position → calculate path → walk → interact with interface → read text → perform action.

## Plugins

Binary plugins (in `plugins/`) provide low-level functionality:
- `libasyncmouse`: Asynchronous mouse movement
- `libremoteinput`: Direct client injection
- `libsimpleocr`: OCR engine
- `libslacktree`: Tree data structures (likely for pathfinding)
- `libtpaex`: Extended TPA (TPointArray) operations

All plugins support multiple platforms (32/64-bit Windows, Linux, macOS, ARM).

## Design Patterns

- Record-based API: Most functionality is exposed through record types with methods
- Conditional includes: Prevents duplicate includes using `{$IFNDEF}` guards
- Setup pattern: Components have `Setup()` methods for initialization
- Base record inheritance: Many components inherit from `TSRLBaseRecord` for common functionality
- Callback system: Events like `OnWalkingEvent` allow custom behavior during operations

This architecture provides a modular, extensible framework for automating Old School RuneScape tasks while maintaining flexibility for script developers.