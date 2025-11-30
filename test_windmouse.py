#!/usr/bin/env python3
"""
WindMouse Algorithm and Miss Chance System Test Script

This script demonstrates the WindMouse algorithm and miss chance system
from SRL-T's mouse movement implementation.
"""

import math
import random
import time
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Tuple

# Try to import pynput for real-time mouse control
try:
    from pynput import mouse
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("Warning: pynput not available. Install with: pip install pynput")

# Constants
SQRT_3 = math.sqrt(3)
SQRT_5 = math.sqrt(5)
GAUSS_CUTOFF = 4.0


def nz_random() -> float:
    """Generates a random number that is never 0."""
    return max(random.random(), 1.0e-320)


def gauss_rand(mean: float, dev: float) -> float:
    """Generates a random gaussian/normal number."""
    length = dev * math.sqrt(-2 * math.log(nz_random()))
    return mean + length * math.cos(2 * math.pi * random.random())


def truncated_gauss(left: float, right: float, cutoff: float = 0.0) -> float:
    """Generates a truncated gaussian number within [left, right] weighted towards left."""
    if cutoff <= 0:
        cutoff = GAUSS_CUTOFF
    
    result = cutoff + 1
    while result >= cutoff:
        result = abs(math.sqrt(-2 * math.log(nz_random())) * math.cos(2 * math.pi * random.random()))
    return result / cutoff * (right - left) + left


def skewed_rand(mode: float, lo: float, hi: float, cutoff: float = 0.0) -> float:
    """Random skewed distribution generation. Mode is where most numbers will land."""
    if cutoff <= 0:
        cutoff = GAUSS_CUTOFF
    
    top = lo
    if random.random() * (hi - lo) > mode - lo:
        top = hi
    
    result = cutoff + 1
    while result >= cutoff:
        result = abs(math.sqrt(-2 * math.log(nz_random())) * math.cos(2 * math.pi * random.random()))
    return result / cutoff * (top - mode) + mode


def normal_range(min_val: float, max_val: float, cutoff: float = 0.0) -> float:
    """Generates a random number in the given range, weighted towards the mean."""
    if cutoff <= 0:
        cutoff = GAUSS_CUTOFF
    
    if random.randint(0, 1) == 0:
        return (max_val + min_val) / 2.0 + truncated_gauss(0, (max_val - min_val) / 2, cutoff)
    else:
        return (max_val + min_val) / 2.0 - truncated_gauss(0, (max_val - min_val) / 2, cutoff)


def dice(chance_percent: float) -> bool:
    """Returns True with the given chance percentage."""
    return random.random() < chance_percent / 100.0


def hypot(x: float, y: float) -> float:
    """Calculate hypotenuse/distance."""
    return math.sqrt(x * x + y * y)


def distance_to(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate distance between two points."""
    return hypot(p2[0] - p1[0], p2[1] - p1[1])


class Mouse:
    """Mouse class implementing WindMouse algorithm and miss chance system."""
    
    def __init__(self, speed: int = 12, gravity: float = 9.0, wind: float = 5.0, 
                 miss_chance: float = 15.0):
        self.speed = speed
        self.gravity = gravity
        self.wind = wind
        self.miss_chance = miss_chance
        self.position = (0.0, 0.0)
        self.path_history: List[Tuple[float, float]] = []
    
    def wind_mouse(self, xs: float, ys: float, xe: float, ye: float, 
                   gravity: float, wind: float, min_wait: float, max_wait: float,
                   max_step: float, target_area: float) -> List[Tuple[float, float]]:
        """
        WindMouse algorithm - moves mouse in a human-like way.
        Returns the path taken as a list of (x, y) coordinates.
        """
        path = []
        x, y = xs, ys
        velo_x, velo_y = 0.0, 0.0
        wind_x, wind_y = 0.0, 0.0
        max_iterations = 10000
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            path.append((x, y))
            
            traveled_distance = hypot(x - xs, y - ys)
            remaining_distance = hypot(x - xe, y - ye)
            
            if remaining_distance <= 1:
                break
            
            # Wind effect
            wind = min(wind, remaining_distance)
            wind_x = wind_x / SQRT_3 + (random.randint(0, int(wind * 2)) - wind) / SQRT_5
            wind_y = wind_y / SQRT_3 + (random.randint(0, int(wind * 2)) - wind) / SQRT_5
            
            # Step size calculation
            if remaining_distance < target_area:
                step = (remaining_distance / 2) + (random.random() * 6 - 3)
            elif traveled_distance < target_area:
                if traveled_distance < 3:
                    traveled_distance = 10 * random.random()
                step = traveled_distance * (1 + random.random() * 3)
            else:
                step = max_step
            
            step = min(step, max_step)
            if step < 3:
                step = 3 + (random.random() * 3)
            
            # Apply wind and gravity
            velo_x += wind_x
            velo_y += wind_y
            velo_x += gravity * (xe - x) / remaining_distance
            velo_y += gravity * (ye - y) / remaining_distance
            
            # Limit velocity to step size
            if hypot(velo_x, velo_y) > step:
                random_dist = step / 3.0 + (step / 2 * random.random())
                velo_mag = math.sqrt(velo_x * velo_x + velo_y * velo_y)
                velo_x = (velo_x / velo_mag) * random_dist
                velo_y = (velo_y / velo_mag) * random_dist
            
            # Update position
            x += velo_x
            y += velo_y
            
            # Simulate wait time (not actually waiting, just for algorithm)
            idle = (max_wait - min_wait) * (hypot(velo_x, velo_y) / max_step) + min_wait
        
        # Final position
        path.append((xe, ye))
        return path
    
    def miss(self, destination: Tuple[float, float]) -> Tuple[float, float]:
        """
        Miss function - causes mouse to miss the destination point.
        Returns the position the mouse was moved to instead.
        """
        temp_miss_chance = self.miss_chance
        self.miss_chance = 0  # Prevent recursion
        
        try:
            current_pos = self.position
            range_val = int(math.pow(distance_to(current_pos, destination), 0.80))
            
            # Where miss will happen (1 = destination)
            miss_factor = skewed_rand(0.9, 0.1, 1.5)
            
            # Interpolate between current and destination
            result_x = (1 - miss_factor) * current_pos[0] + miss_factor * destination[0]
            result_y = (1 - miss_factor) * current_pos[1] + miss_factor * destination[1]
            
            # Add random offset
            result_x += normal_range(-range_val, range_val)
            result_y += normal_range(-range_val, range_val)
            
            result = (int(result_x), int(result_y))
            
            # 25% chance to add extra delay
            if dice(25):
                pass  # Would wait here in real implementation
            
            return result
        finally:
            self.miss_chance = temp_miss_chance
    
    def move(self, destination: Tuple[float, float], use_miss: bool = True) -> List[Tuple[float, float]]:
        """
        Move mouse to destination, optionally using miss chance.
        Returns the path taken.
        """
        start = self.position
        
        # Apply miss chance if enabled
        if use_miss and dice(self.miss_chance):
            start = self.miss(destination)
            # Move to the miss point first
            miss_path = self.wind_mouse(
                self.position[0], self.position[1], start[0], start[1],
                self.gravity, self.wind, 5, 10, 20, 20
            )
            self.position = start
            return miss_path
        
        # Calculate speed based on distance
        distance = distance_to(start, destination)
        exponential = math.pow(distance, 0.33) / 10
        
        rand_speed = truncated_gauss(self.speed, self.speed * 1.5)
        rand_speed *= max(0.1, exponential)
        rand_speed /= 10
        
        # Calculate WindMouse parameters
        min_wait = 5 / rand_speed
        max_wait = 10 / rand_speed
        max_step = 20 * rand_speed
        target_area = 20 * rand_speed
        
        # Execute WindMouse
        path = self.wind_mouse(
            start[0], start[1], destination[0], destination[1],
            self.gravity, self.wind, min_wait, max_wait, max_step, target_area
        )
        
        self.position = destination
        return path


def plot_paths(paths: List[List[Tuple[float, float]]], destinations: List[Tuple[float, float]],
               title: str, start_pos: Tuple[float, float]):
    """Plot multiple mouse paths for comparison."""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(paths)))
    
    for i, (path, dest) in enumerate(zip(paths, destinations)):
        if path:
            x_coords = [p[0] for p in path]
            y_coords = [p[1] for p in path]
            
            ax.plot(x_coords, y_coords, color=colors[i], alpha=0.6, linewidth=1.5,
                   label=f'Path {i+1}')
            ax.scatter([dest[0]], [dest[1]], color=colors[i], s=100, marker='x', 
                      linewidths=3, zorder=5)
    
    # Mark start position
    ax.scatter([start_pos[0]], [start_pos[1]], color='green', s=150, marker='o',
              label='Start', zorder=6, edgecolors='black', linewidths=2)
    
    ax.set_xlabel('X Position', fontsize=12)
    ax.set_ylabel('Y Position', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_aspect('equal', adjustable='box')
    
    plt.tight_layout()
    return fig


def test_windmouse_basic():
    """Test basic WindMouse algorithm without miss chance."""
    print("=" * 60)
    print("Test 1: Basic WindMouse (No Miss Chance)")
    print("=" * 60)
    
    mouse = Mouse(speed=12, gravity=9.0, wind=5.0, miss_chance=0.0)
    mouse.position = (100, 100)
    
    destinations = [
        (400, 300),
        (200, 500),
        (600, 200),
    ]
    
    paths = []
    for dest in destinations:
        mouse.position = (100, 100)  # Reset start
        path = mouse.move(dest, use_miss=False)
        paths.append(path)
        print(f"  Moved to {dest}: {len(path)} points in path")
    
    fig = plot_paths(paths, destinations, 
                     "WindMouse Algorithm - Basic Movement (No Miss Chance)",
                     (100, 100))
    plt.savefig('windmouse_basic.png', dpi=150, bbox_inches='tight')
    print("  Saved: windmouse_basic.png")
    plt.close()


def test_windmouse_with_miss():
    """Test WindMouse algorithm with miss chance enabled."""
    print("\n" + "=" * 60)
    print("Test 2: WindMouse with Miss Chance (15%)")
    print("=" * 60)
    
    mouse = Mouse(speed=12, gravity=9.0, wind=5.0, miss_chance=15.0)
    mouse.position = (100, 100)
    
    destinations = [
        (400, 300),
        (200, 500),
        (600, 200),
    ]
    
    paths = []
    for dest in destinations:
        mouse.position = (100, 100)  # Reset start
        path = mouse.move(dest, use_miss=True)
        paths.append(path)
        actual_end = path[-1] if path else mouse.position
        print(f"  Target: {dest}, Actual end: ({actual_end[0]:.1f}, {actual_end[1]:.1f})")
    
    fig = plot_paths(paths, destinations,
                     "WindMouse Algorithm - With Miss Chance (15%)",
                     (100, 100))
    plt.savefig('windmouse_with_miss.png', dpi=150, bbox_inches='tight')
    print("  Saved: windmouse_with_miss.png")
    plt.close()


def test_miss_chance_comparison():
    """Compare multiple runs with and without miss chance."""
    print("\n" + "=" * 60)
    print("Test 3: Miss Chance Comparison (10 runs each)")
    print("=" * 60)
    
    start = (100, 100)
    destination = (500, 400)
    
    # Without miss chance
    print("\n  Without Miss Chance:")
    paths_no_miss = []
    for i in range(10):
        mouse = Mouse(speed=12, gravity=9.0, wind=5.0, miss_chance=0.0)
        mouse.position = start
        path = mouse.move(destination, use_miss=False)
        paths_no_miss.append(path)
        end = path[-1] if path else mouse.position
        error = distance_to(end, destination)
        print(f"    Run {i+1}: End error = {error:.2f} pixels")
    
    # With miss chance
    print("\n  With Miss Chance (15%):")
    paths_with_miss = []
    for i in range(10):
        mouse = Mouse(speed=12, gravity=9.0, wind=5.0, miss_chance=15.0)
        mouse.position = start
        path = mouse.move(destination, use_miss=True)
        paths_with_miss.append(path)
        end = path[-1] if path else mouse.position
        error = distance_to(end, destination)
        print(f"    Run {i+1}: End error = {error:.2f} pixels")
    
    # Plot comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # Without miss
    for i, path in enumerate(paths_no_miss):
        if path:
            x_coords = [p[0] for p in path]
            y_coords = [p[1] for p in path]
            ax1.plot(x_coords, y_coords, alpha=0.5, linewidth=1)
    
    ax1.scatter([start[0]], [start[1]], color='green', s=150, marker='o',
               label='Start', zorder=6, edgecolors='black', linewidths=2)
    ax1.scatter([destination[0]], [destination[1]], color='red', s=150, marker='x',
               linewidths=3, label='Target', zorder=6)
    ax1.set_title('Without Miss Chance', fontsize=12, fontweight='bold')
    ax1.set_xlabel('X Position')
    ax1.set_ylabel('Y Position')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_aspect('equal', adjustable='box')
    
    # With miss
    for i, path in enumerate(paths_with_miss):
        if path:
            x_coords = [p[0] for p in path]
            y_coords = [p[1] for p in path]
            ax2.plot(x_coords, y_coords, alpha=0.5, linewidth=1)
    
    ax2.scatter([start[0]], [start[1]], color='green', s=150, marker='o',
               label='Start', zorder=6, edgecolors='black', linewidths=2)
    ax2.scatter([destination[0]], [destination[1]], color='red', s=150, marker='x',
               linewidths=3, label='Target', zorder=6)
    ax2.set_title('With Miss Chance (15%)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('X Position')
    ax2.set_ylabel('Y Position')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_aspect('equal', adjustable='box')
    
    plt.suptitle('WindMouse Comparison: 10 Runs Each', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('windmouse_comparison.png', dpi=150, bbox_inches='tight')
    print("\n  Saved: windmouse_comparison.png")
    plt.close()


def test_different_miss_chances():
    """Test different miss chance percentages."""
    print("\n" + "=" * 60)
    print("Test 4: Different Miss Chance Percentages")
    print("=" * 60)
    
    start = (100, 100)
    destination = (500, 400)
    miss_chances = [0, 5, 15, 30, 50]
    
    fig, axes = plt.subplots(1, len(miss_chances), figsize=(20, 4))
    
    for idx, miss_chance in enumerate(miss_chances):
        paths = []
        for _ in range(5):
            mouse = Mouse(speed=12, gravity=9.0, wind=5.0, miss_chance=miss_chance)
            mouse.position = start
            path = mouse.move(destination, use_miss=(miss_chance > 0))
            paths.append(path)
        
        ax = axes[idx]
        for path in paths:
            if path:
                x_coords = [p[0] for p in path]
                y_coords = [p[1] for p in path]
                ax.plot(x_coords, y_coords, alpha=0.6, linewidth=1)
        
        ax.scatter([start[0]], [start[1]], color='green', s=100, marker='o',
                  zorder=6, edgecolors='black', linewidths=1)
        ax.scatter([destination[0]], [destination[1]], color='red', s=100, marker='x',
                  linewidths=2, zorder=6)
        ax.set_title(f'Miss: {miss_chance}%', fontsize=10, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal', adjustable='box')
    
    plt.suptitle('WindMouse with Different Miss Chance Percentages (5 runs each)',
                fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig('windmouse_miss_percentages.png', dpi=150, bbox_inches='tight')
    print("  Saved: windmouse_miss_percentages.png")
    plt.close()


class MouseRealTime:
    """Real-time mouse controller using WindMouse algorithm."""
    
    def __init__(self, speed: int = 12, gravity: float = 9.0, wind: float = 5.0,
                 miss_chance: float = 15.0):
        if not PYNPUT_AVAILABLE:
            raise ImportError("pynput is required for real-time mouse control. Install with: pip install pynput")
        
        self.speed = speed
        self.gravity = gravity
        self.wind = wind
        self.miss_chance = miss_chance
        self.mouse_controller = mouse.Controller()
    
    def get_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        pos = self.mouse_controller.position
        # pynput returns position as a tuple (x, y) directly
        return pos
    
    def set_position(self, x: int, y: int):
        """Set mouse position."""
        self.mouse_controller.position = (x, y)
    
    def wind_mouse_real(self, xs: float, ys: float, xe: float, ye: float,
                        gravity: float, wind: float, min_wait: float, max_wait: float,
                        max_step: float, target_area: float):
        """
        WindMouse algorithm that actually moves the mouse cursor in real-time.
        """
        x, y = xs, ys
        velo_x, velo_y = 0.0, 0.0
        wind_x, wind_y = 0.0, 0.0
        max_iterations = 10000
        iteration = 0
        
        # Move to starting position
        self.set_position(int(x), int(y))
        time.sleep(0.01)  # Small delay to ensure position is set
        
        while iteration < max_iterations:
            iteration += 1
            
            traveled_distance = hypot(x - xs, y - ys)
            remaining_distance = hypot(x - xe, y - ye)
            
            if remaining_distance <= 1:
                break
            
            # Wind effect
            wind = min(wind, remaining_distance)
            wind_x = wind_x / SQRT_3 + (random.randint(0, int(wind * 2)) - wind) / SQRT_5
            wind_y = wind_y / SQRT_3 + (random.randint(0, int(wind * 2)) - wind) / SQRT_5
            
            # Step size calculation
            if remaining_distance < target_area:
                step = (remaining_distance / 2) + (random.random() * 6 - 3)
            elif traveled_distance < target_area:
                if traveled_distance < 3:
                    traveled_distance = 10 * random.random()
                step = traveled_distance * (1 + random.random() * 3)
            else:
                step = max_step
            
            step = min(step, max_step)
            if step < 3:
                step = 3 + (random.random() * 3)
            
            # Apply wind and gravity
            velo_x += wind_x
            velo_y += wind_y
            velo_x += gravity * (xe - x) / remaining_distance
            velo_y += gravity * (ye - y) / remaining_distance
            
            # Limit velocity to step size
            if hypot(velo_x, velo_y) > step:
                random_dist = step / 3.0 + (step / 2 * random.random())
                velo_mag = math.sqrt(velo_x * velo_x + velo_y * velo_y)
                velo_x = (velo_x / velo_mag) * random_dist
                velo_y = (velo_y / velo_mag) * random_dist
            
            # Update position
            x += velo_x
            y += velo_y
            
            # Actually move the mouse
            self.set_position(int(x), int(y))
            
            # Calculate and apply wait time
            idle = (max_wait - min_wait) * (hypot(velo_x, velo_y) / max_step) + min_wait
            time.sleep(idle / 1000.0)  # Convert ms to seconds
        
        # Final position
        self.set_position(int(xe), int(ye))
    
    def miss_real(self, destination: Tuple[float, float]) -> Tuple[float, float]:
        """Miss function for real-time movement."""
        temp_miss_chance = self.miss_chance
        self.miss_chance = 0  # Prevent recursion
        
        try:
            current_pos = self.get_position()
            range_val = int(math.pow(distance_to(current_pos, destination), 0.80))
            
            miss_factor = skewed_rand(0.9, 0.1, 1.5)
            
            result_x = (1 - miss_factor) * current_pos[0] + miss_factor * destination[0]
            result_y = (1 - miss_factor) * current_pos[1] + miss_factor * destination[1]
            
            result_x += normal_range(-range_val, range_val)
            result_y += normal_range(-range_val, range_val)
            
            result = (int(result_x), int(result_y))
            
            if dice(25):
                time.sleep(random.uniform(0, 5))  # 25% chance to pause
            
            return result
        finally:
            self.miss_chance = temp_miss_chance
    
    def move_real(self, destination: Tuple[float, float], use_miss: bool = True):
        """Move mouse to destination in real-time."""
        start = self.get_position()
        
        # Apply miss chance if enabled
        if use_miss and dice(self.miss_chance):
            miss_point = self.miss_real(destination)
            # Move to miss point first
            distance = distance_to(start, miss_point)
            exponential = math.pow(distance, 0.33) / 10
            rand_speed = truncated_gauss(self.speed, self.speed * 1.5)
            rand_speed *= max(0.1, exponential)
            rand_speed /= 10
            
            self.wind_mouse_real(
                start[0], start[1], miss_point[0], miss_point[1],
                self.gravity, self.wind,
                5 / rand_speed, 10 / rand_speed, 20 * rand_speed, 20 * rand_speed
            )
            start = miss_point
        
        # Calculate speed based on distance
        distance = distance_to(start, destination)
        exponential = math.pow(distance, 0.33) / 10
        
        rand_speed = truncated_gauss(self.speed, self.speed * 1.5)
        rand_speed *= max(0.1, exponential)
        rand_speed /= 10
        
        # Calculate WindMouse parameters
        min_wait = 5 / rand_speed
        max_wait = 10 / rand_speed
        max_step = 20 * rand_speed
        target_area = 20 * rand_speed
        
        # Execute WindMouse
        self.wind_mouse_real(
            start[0], start[1], destination[0], destination[1],
            self.gravity, self.wind, min_wait, max_wait, max_step, target_area
        )


def test_realtime_mouse():
    """Test real-time mouse movement."""
    if not PYNPUT_AVAILABLE:
        print("\n" + "=" * 60)
        print("Skipping real-time mouse test (pynput not available)")
        print("Install with: pip install pynput")
        print("=" * 60)
        return
    
    print("\n" + "=" * 60)
    print("Real-Time Mouse Movement Test")
    print("=" * 60)
    
    # Loop to allow repeating the test
    while True:
        print("\nThis will move your mouse cursor in real-time!")
        print("Move your mouse to a safe area and press ENTER to start...")
        print("(Press Ctrl+C to cancel)")
        
        try:
            input()  # Wait for user to press ENTER
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return
        
        time.sleep(1)
        
        mouse_controller = MouseRealTime(speed=12, gravity=9.0, wind=5.0, miss_chance=15.0)
        
        # Get current mouse position
        start_pos = mouse_controller.get_position()
        print(f"\nStarting position: {start_pos}")
        
        # Define movement pattern (relative to start)
        movements = [
            (300, 200),   # Move right and down
            (0, -150),    # Move up
            (-200, 100),  # Move left and down
            (100, 50),    # Move right and down
            (-200, -200), # Move left and up (back toward start)
        ]
        
        print("\nMoving mouse in a pattern...")
        print("(Press Ctrl+C to stop early)\n")
        
        try:
            for i, (dx, dy) in enumerate(movements, 1):
                target = (start_pos[0] + dx, start_pos[1] + dy)
                print(f"Movement {i}/{len(movements)}: Moving to {target}")
                
                # Move with miss chance enabled
                mouse_controller.move_real(target, use_miss=True)
                
                # Small pause between movements
                time.sleep(0.3)
            
            # Return to start
            print(f"\nReturning to start position: {start_pos}")
            mouse_controller.move_real(start_pos, use_miss=False)
            
            print("\n" + "=" * 60)
            print("Real-time mouse movement test completed!")
            print("=" * 60)
            
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user.")
        except Exception as e:
            print(f"\nError during mouse movement: {e}")
        
        # Ask if user wants to repeat
        print("\n" + "-" * 60)
        try:
            repeat = input("Would you like to repeat the test? (y/n): ").strip().lower()
            if repeat != 'y':
                print("Exiting real-time mouse test.")
                break
        except (EOFError, KeyboardInterrupt):
            print("\nExiting real-time mouse test.")
            break


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("WindMouse Algorithm and Miss Chance System Test")
    print("=" * 60)
    
    # Set random seed for reproducibility (optional)
    random.seed(42)
    
    test_windmouse_basic()
    test_windmouse_with_miss()
    test_miss_chance_comparison()
    test_different_miss_chances()
    
    print("\n" + "=" * 60)
    print("All visualization tests completed!")
    print("=" * 60)
    print("\nGenerated files:")
    print("  - windmouse_basic.png")
    print("  - windmouse_with_miss.png")
    print("  - windmouse_comparison.png")
    print("  - windmouse_miss_percentages.png")
    
    # Real-time mouse test (optional, requires pynput)
    print("\n" + "=" * 60)
    print("Real-Time Mouse Movement Test")
    print("=" * 60)
    response = input("\nWould you like to test real-time mouse movement? (y/n): ").strip().lower()
    if response == 'y':
        test_realtime_mouse()
    else:
        print("Skipping real-time mouse test.")


if __name__ == "__main__":
    main()

