import socket
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge
import math
import re
import threading
import sys
import os
import platform

class CyBotMapper:
    def __init__(self, host="192.168.1.1", port=288):
        # Connection settings
        self.host = host
        self.port = port
        self.socket = None
        self.buffer = ""
        self.lock = threading.Lock()
        
        # CyBot state
        self.position = [0, 0]  # [x, y] in cm
        self.orientation = 90   # Degrees (0 = right, 90 = up)
        self.objects = []       # List of detected objects
        
        # Map settings
        self.fig, self.ax = plt.subplots(figsize=(10, 10))
        self.max_range = 250    # cm - maximum display range
        self.scan_data = []     # Raw scan data points
        self.object_patches = []  # Store object visualization elements
        
        # Initialize plot elements
        self.setup_map()
        
    def setup_map(self):
        """Initialize the map visualization"""
        # Set up a square map with proper scaling
        self.ax.set_xlim(-self.max_range, self.max_range)
        self.ax.set_ylim(-self.max_range, self.max_range)
        self.ax.set_aspect('equal')
        self.ax.grid(True)
        self.ax.set_title('CyBot Mapping')
        self.ax.set_xlabel('X (cm)')
        self.ax.set_ylabel('Y (cm)')
        
        # Add the CyBot as a marker at the origin
        self.cybot_marker = Circle((0, 0), 10, color='blue', fill=True, zorder=5)
        self.ax.add_patch(self.cybot_marker)
        
        # Add direction indicator
        angle_rad = math.radians(self.orientation)
        dir_x = 20 * math.cos(angle_rad)
        dir_y = 20 * math.sin(angle_rad)
        self.direction_line, = self.ax.plot([0, dir_x], [0, dir_y], 'b-', linewidth=2, zorder=5)
        
        # Initialize the path visualization
        self.path_x = [0]
        self.path_y = [0]
        self.path_line, = self.ax.plot(self.path_x, self.path_y, 'g-', linewidth=1, zorder=2)
        
        # Initialize the scan data visualization
        self.scan_points = self.ax.scatter([], [], color='red', s=10, zorder=3)
        
        # Add a legend
        self.ax.plot([], [], 'b-', label='CyBot')
        self.ax.plot([], [], 'g-', label='Path')
        self.ax.plot([], [], 'ro', markersize=4, label='Scan Points')
        self.ax.plot([], [], 'orange', marker='o', linestyle='none', markersize=8, label='Objects')
        self.ax.legend(loc='upper right')
        
        plt.tight_layout()
        
    def connect(self):
        """Connect to the CyBot server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"Connected to CyBot at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.socket = None
            return False
    
    def send_command(self, command):
        """Send a command to the CyBot"""
        if not self.socket:
            print("Not connected to CyBot")
            return False
        
        try:
            self.socket.send((command + '\n').encode())
            print(f"Sent command: {command}")
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
    
    def receive_data(self, timeout=0.5):
        """Receive and process incoming data"""
        if not self.socket:
            return ""
        
        try:
            self.socket.settimeout(timeout)
            data = self.socket.recv(1024).decode('utf-8', errors='replace')
            return data
        except socket.timeout:
            return ""
        except Exception as e:
            print(f"Error receiving data: {e}")
            return ""
    
    def update_position(self, movement_type, value):
        """Update the CyBot's position based on confirmed movement"""
        with self.lock:
            if movement_type == "forward":
                # Convert to cm and calculate new position based on orientation
                distance = value / 10.0  # Value is in mm, convert to cm
                rad_angle = math.radians(self.orientation)  # Use orientation directly
                dx = distance * math.cos(rad_angle)
                dy = distance * math.sin(rad_angle)
                self.position[0] += dx
                self.position[1] += dy
                
                # Update path
                self.path_x.append(self.position[0])
                self.path_y.append(self.position[1])
                
            elif movement_type == "backward":
                # Same as forward but negative
                distance = -value / 10.0
                rad_angle = math.radians(self.orientation)  # Use orientation directly
                dx = distance * math.cos(rad_angle)
                dy = distance * math.sin(rad_angle)
                self.position[0] += dx
                self.position[1] += dy
                
                # Update path
                self.path_x.append(self.position[0])
                self.path_y.append(self.position[1])
                
            elif movement_type == "turn_right":
                self.orientation = (self.orientation - value) % 360
                
            elif movement_type == "turn_left":
                self.orientation = (self.orientation + value) % 360

    def parse_scan_data(self, data, scan_type="ir"):
        """Parse scan results from the CyBot response"""
        scan_points = []
        
        if scan_type == "ir":
            # Match lines with angle, distance, IR reading
            pattern = r"(\d+)\s+(\d+\.\d+)\s+(\d+)"
        else:  # ping
            # Match lines with angle, distance
            pattern = r"(\d+)\s+(\d+\.\d+)"
            
        matches = re.findall(pattern, data)
        
        for match in matches:
            angle = float(match[0])
            distance = float(match[1])
            
            if distance > 0 and distance < self.max_range:
                # Convert to global coordinates
                # Adjust angle: 0° is front, increases clockwise
                global_angle = (self.orientation + angle - 90) % 360
                rad_angle = math.radians(global_angle)
                
                # Calculate global position
                x = self.position[0] + distance * math.cos(rad_angle)
                y = self.position[1] + distance * math.sin(rad_angle)
                scan_points.append((x, y, angle, distance))
        
        return scan_points
    
    def parse_objects(self, data):
        """Parse object detection results"""
        objects = []
        
        # Look for object details in the format: ID | Center | Distance | Width
        pattern = r"(\d+) \| +(\d+\.\d+) \| +(\d+\.\d+) \| +(\d+\.\d+)"
        matches = re.findall(pattern, data)
        
        for match in matches:
            obj_id = int(match[0])
            center_angle = float(match[1])
            distance = float(match[2])
            width = float(match[3])
            
            # Convert to global coordinates
            global_angle = (self.orientation + center_angle - 90) % 360
            rad_angle = math.radians(global_angle)
            
            x = self.position[0] + distance * math.cos(rad_angle)
            y = self.position[1] + distance * math.sin(rad_angle)
            
            objects.append({
                'id': obj_id,
                'x': x, 
                'y': y,
                'center_angle': center_angle,
                'global_angle': global_angle,
                'distance': distance,
                'width': width
            })
            
        return objects
    
    def update_map(self):
        """Update the map visualization with current state"""
        with self.lock:
            # Update CyBot position and orientation
            self.cybot_marker.center = self.position
            
            # Update direction indicator
            angle_rad = math.radians(self.orientation)
            dir_x = self.position[0] + 20 * math.cos(angle_rad)
            dir_y = self.position[1] + 20 * math.sin(angle_rad)
            self.direction_line.set_data([self.position[0], dir_x], [self.position[1], dir_y])
            
            # Update path line
            self.path_line.set_data(self.path_x, self.path_y)
            
            # Update scan points
            if self.scan_data:
                x_points = [point[0] for point in self.scan_data]
                y_points = [point[1] for point in self.scan_data]
                self.scan_points.set_offsets(np.column_stack([x_points, y_points]))
            
            # Clear previous object patches
            for patch in self.object_patches:
                patch.remove()
            self.object_patches = []
            
            # Add new object patches
            for obj in self.objects:
                # Draw object as a circle with size based on width
                radius = obj['width'] / 2
                circle = Circle((obj['x'], obj['y']), radius, 
                               color='orange', alpha=0.7, zorder=4)
                self.ax.add_patch(circle)
                
                # Add text label for object ID
                text = self.ax.text(obj['x'], obj['y'], str(obj['id']), 
                                  fontsize=8, ha='center', va='center', 
                                  color='black', zorder=6)
                
                self.object_patches.append(circle)
                self.object_patches.append(text)
    
    def process_response(self, response):
        """Process a response from the CyBot"""
        if not response:
            return False
        
        changes = False
        
        # Buffer the response for complete message processing
        self.buffer += response
        
        # Look for complete movement confirmations
        if "complete" in self.buffer:
            # Quick turn right
            if "Quick turn right" in self.buffer and "complete" in self.buffer:
                match = re.search(r"Quick turn right (\d+) degrees", self.buffer)
                if match:
                    angle = int(match.group(1))
                    self.update_position("turn_right", angle)
                    changes = True
                    print(f"► Confirmed turn right {angle}°")
            
            # Quick turn left
            elif "Quick turn left" in self.buffer and "complete" in self.buffer:
                match = re.search(r"Quick turn left (\d+) degrees", self.buffer)
                if match:
                    angle = int(match.group(1))
                    self.update_position("turn_left", angle)
                    changes = True
                    print(f"◄ Confirmed turn left {angle}°")
            
            # Quick move forward
            elif "Quick move forward" in self.buffer and "complete" in self.buffer:
                match = re.search(r"Quick move forward (\d+)cm", self.buffer)
                if match:
                    distance = int(match.group(1)) * 10  # Convert to mm
                    self.update_position("forward", distance)
                    changes = True
                    print(f"▲ Confirmed forward {distance/10}cm")
            
            # Quick move backward
            elif "Quick move backward" in self.buffer and "complete" in self.buffer:
                match = re.search(r"Quick move backward (\d+)cm", self.buffer)
                if match:
                    distance = int(match.group(1)) * 10  # Convert to mm
                    self.update_position("backward", distance)
                    changes = True
                    print(f"▼ Confirmed backward {distance/10}cm")
            
            # Standard movements from "m" command
            elif "Moving forward" in self.buffer and "Movement complete" in self.buffer:
                match = re.search(r"Moving forward (\d+) mm", self.buffer)
                if match:
                    distance = int(match.group(1))
                    self.update_position("forward", distance)
                    changes = True
                    print(f"▲ Confirmed forward {distance/10}cm")
            
            elif "Turning right" in self.buffer and "Movement complete" in self.buffer:
                match = re.search(r"Turning right (\d+) degrees", self.buffer)
                if match:
                    angle = int(match.group(1))
                    self.update_position("turn_right", angle)
                    changes = True
                    print(f"► Confirmed turn right {angle}°")
            
            elif "Turning left" in self.buffer and "Movement complete" in self.buffer:
                match = re.search(r"Turning left (\d+) degrees", self.buffer)
                if match:
                    angle = int(match.group(1))
                    self.update_position("turn_left", angle)
                    changes = True
                    print(f"◄ Confirmed turn left {angle}°")
        
        # Check for scan completions
        if "IR scan complete" in self.buffer:
            self.scan_data = self.parse_scan_data(self.buffer, "ir")
            print(f"📊 Processed IR scan with {len(self.scan_data)} points")
            changes = True
        
        elif "PING scan complete" in self.buffer:
            self.scan_data = self.parse_scan_data(self.buffer, "ping")
            print(f"📊 Processed PING scan with {len(self.scan_data)} points")
            changes = True
        
        # Check for object detection
        if "Object Detection Results" in self.buffer:
            if "IR Object Detection Results" in self.buffer:
                self.objects = self.parse_objects(self.buffer)
                print(f"🔍 Detected {len(self.objects)} objects with IR")
                changes = True
            
            elif "PING Object Detection Results" in self.buffer:
                self.objects = self.parse_objects(self.buffer)
                print(f"🔍 Detected {len(self.objects)} objects with PING")
                changes = True
        
        # If we've processed a complete response, reset the buffer
        if ">" in self.buffer:
            self.buffer = ""
        
        return changes
    
    def run(self):
        """Run the mapping application"""
        if not self.connect():
            print("Failed to connect. Exiting.")
            return
        
        plt.ion()  # Interactive mode
        plt.show()
        
        try:
            print("\nCyBot Mapper running. Press Ctrl+C to exit.")
            print("Available commands:")
            print("  i - IR scan")
            print("  p - PING scan")
            print("  m - Move with parameters")
            print("  f - Quick move forward 10cm")
            print("  b - Quick move backward 10cm")
            print("  r - Quick turn right 10°")
            print("  l - Quick turn left 10°")
            
            while True:
                # Non-blocking input method using modified input_available function
                if check_for_input():
                    cmd = input("\nEnter command: ")
                    self.send_command(cmd)
                
                # Receive and process data
                data = self.receive_data()
                if data:
                    if self.process_response(data):
                        self.update_map()
                        plt.draw()
                
                plt.pause(0.1)  # Allow plot to update
                
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            if self.socket:
                self.socket.close()
            plt.ioff()

# Cross-platform input checking function
def check_for_input():
    """
    Cross-platform implementation of non-blocking input check.
    Returns True if input is available, False otherwise.
    """
    # Windows-specific implementation
    if platform.system() == 'Windows':
        # Use msvcrt for Windows
        try:
            import msvcrt
            return msvcrt.kbhit()
        except ImportError:
            # Fall back to polling method if msvcrt not available
            return False
    else:
        # Unix/Linux/Mac implementation
        import select
        # Use select for checking stdin on non-Windows platforms
        try:
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            return bool(ready)
        except:
            # Fall back to returning False if select fails
            return False

# Thread-safe user input function
def get_user_input(prompt=""):
    """Get user input in a thread-safe way"""
    if prompt:
        print(prompt, end='', flush=True)
    return input()

if __name__ == "__main__":
    mapper = CyBotMapper(host="192.168.1.1", port=288)
    mapper.run()