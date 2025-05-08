import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading
import time
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import re
import random

class CybotControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CyBot Control Interface")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # Socket variables
        self.socket = None
        self.connected = False
        self.receive_thread = None
        self.stop_thread = False
        
        # Data storage
        self.scan_data = {'angles': [], 'distances': [], 'type': None}
        self.cybot_position = {'x': 0, 'y': 0, 'angle': 90}  # Starting position, facing up (90°)
        self.movement_history = [{'x': 0, 'y': 0, 'angle': 90}]  # Start with initial position
        self.objects = []
        self.water_samples = []
        
        # Debug mode - enables extra debug output
        self.debug_mode = True
        
        # Create UI elements
        self.create_menu()
        self.create_main_frame()
        
        # Log toggle state
        self.show_log = True
        
        # Initial log
        self.log("CyBot Control Interface started. Ready to connect to CyBot at 192.168.1.1:288")
        
    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.on_closing)
        menu_bar.add_cascade(label="File", menu=file_menu)
        
        # View menu
        view_menu = tk.Menu(menu_bar, tearoff=0)
        
        # Use a variable to track the state
        self.show_log_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(label="Show Log", command=self.toggle_log, 
                                 variable=self.show_log_var)
        
        # Debug mode toggle
        self.debug_mode_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(label="Debug Mode", command=self.toggle_debug,
                                 variable=self.debug_mode_var)
        
        menu_bar.add_cascade(label="View", menu=view_menu)
        
        # Testing menu
        test_menu = tk.Menu(menu_bar, tearoff=0)
        test_menu.add_command(label="Test IR Scan", command=self.test_ir_scan)
        test_menu.add_command(label="Test PING Scan", command=self.test_ping_scan)
        test_menu.add_command(label="Test Object Detection", command=self.test_object_detection)
        test_menu.add_separator()
        test_menu.add_command(label="Clear Map", command=self.clear_map)
        menu_bar.add_cascade(label="Testing", menu=test_menu)
        
        self.root.config(menu=menu_bar)
    
    def toggle_debug(self):
        self.debug_mode = self.debug_mode_var.get()
        self.log(f"Debug mode {'enabled' if self.debug_mode else 'disabled'}")
    
    def test_ir_scan(self):
        """Simulate an IR scan for testing visualization"""
        self.log("Simulating IR scan...")
        
        # Create some sample data
        angles = list(range(0, 181, 4))  # 0 to 180 in steps of 4
        distances = []
        
        # Generate some realistic-looking data
        for angle in angles:
            # Base distance with some randomness
            base_distance = 2.0
            
            # Add "objects" at specific angles
            if 30 <= angle <= 50:
                base_distance = 1.0  # Object at 30-50 degrees
            elif 90 <= angle <= 110:
                base_distance = 0.5  # Object at 90-110 degrees
            elif 150 <= angle <= 170:
                base_distance = 1.5  # Object at 150-170 degrees
                
            # Add some noise
            noise = (random.random() - 0.5) * 0.2
            distance = max(0.1, base_distance + noise)
            distances.append(distance)
        
        # Set as scan data
        self.scan_data = {
            'angles': angles,
            'distances': distances,
            'type': 'IR'
        }
        
        # Update visualization
        self.update_polar_plot()
        
        # Clear scan data type
        self.scan_data['type'] = None
        
        self.log("IR scan simulation complete")
    
    def test_ping_scan(self):
        """Simulate a PING scan for testing visualization"""
        self.log("Simulating PING scan...")
        
        # Create some sample data
        angles = list(range(0, 181, 4))  # 0 to 180 in steps of 4
        distances = []
        
        # Generate some realistic-looking data
        for angle in angles:
            # Base distance with some randomness
            base_distance = 2.0
            
            # Add "objects" at specific angles
            if 20 <= angle <= 40:
                base_distance = 0.8  # Object at 20-40 degrees
            elif 80 <= angle <= 100:
                base_distance = 0.7  # Object at 80-100 degrees
            elif 140 <= angle <= 160:
                base_distance = 1.2  # Object at 140-160 degrees
                
            # Add some noise
            noise = (random.random() - 0.5) * 0.1
            distance = max(0.1, base_distance + noise)
            distances.append(distance)
        
        # Set as scan data
        self.scan_data = {
            'angles': angles,
            'distances': distances,
            'type': 'PING'
        }
        
        # Update visualization
        self.update_polar_plot()
        
        # Clear scan data type
        self.scan_data['type'] = None
        
        self.log("PING scan simulation complete")
    
    def test_object_detection(self):
        """Simulate object detection for testing map visualization"""
        self.log("Simulating object detection...")
        
        # Define some test objects
        test_objects = [
            {'id': 1, 'angle': 30, 'distance': 50, 'width': 25, 'type': 'IR'},
            {'id': 2, 'angle': 90, 'distance': 40, 'width': 20, 'type': 'IR'},
            {'id': 3, 'angle': 150, 'distance': 60, 'width': 30, 'type': 'IR'},
        ]
        
        # Add objects to the map
        for obj in test_objects:
            theta = math.radians(obj['angle'])
            
            # Calculate object position
            rel_x = obj['distance'] * math.sin(theta)
            rel_y = obj['distance'] * math.cos(theta)
            
            # Transform by CyBot's position and orientation
            cybot_theta = math.radians(self.cybot_position['angle'])
            rotated_x = rel_x * math.cos(cybot_theta) - rel_y * math.sin(cybot_theta)
            rotated_y = rel_x * math.sin(cybot_theta) + rel_y * math.cos(cybot_theta)
            
            abs_x = self.cybot_position['x'] + rotated_x
            abs_y = self.cybot_position['y'] + rotated_y
            
            # Add to objects list
            self.objects.append({
                'id': obj['id'],
                'x': abs_x,
                'y': abs_y,
                'angle': obj['angle'],
                'distance': obj['distance'],
                'width': obj['width'],
                'type': obj['type']
            })
        
        # Update map
        self.update_map()
        self.log(f"Added {len(test_objects)} test objects to the map")
    
    def clear_map(self):
        """Clear all objects and reset the map"""
        self.log("Clearing map...")
        
        # Reset objects and water samples
        self.objects = []
        self.water_samples = []
        
        # Reset position to start position (but keep movement history)
        self.cybot_position = {'x': 0, 'y': 0, 'angle': 90}
        
        # Reset movement history
        self.movement_history = [{'x': 0, 'y': 0, 'angle': 90}]
        
        # Update map
        self.update_map()
        self.log("Map cleared")
    
    def create_main_frame(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top section: Connection
        connection_frame = ttk.LabelFrame(main_frame, text="Connection")
        connection_frame.pack(fill=tk.X, pady=5)
        
        # Simplified connection controls with hardcoded IP and port
        self.connect_button = ttk.Button(connection_frame, text="Connect to 192.168.1.1:288", command=self.toggle_connection)
        self.connect_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.status_label = ttk.Label(connection_frame, text="Disconnected", foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Middle section: split between controls and visualization
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Left side: Control buttons
        left_frame = ttk.LabelFrame(middle_frame, text="Controls")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        # Control buttons
        buttons = [
            ("IR Scan", "i", 0, 0),
            ("PING Scan", "p", 0, 1),
            ("Move", "m", 1, 0),
            ("Check Blue Sample", "b", 1, 1),
            ("Turn Right 45°", "r", 2, 0),
            ("Turn Left 45°", "l", 2, 1),
            ("Forward 10cm", "f", 3, 0),
            ("Backward 10cm", "v", 3, 1),
            ("Sample Collection", "s", 4, 0),
            ("Help", "h", 4, 1)
        ]
        
        for text, cmd, row, col in buttons:
            btn = ttk.Button(left_frame, text=text, width=15,
                           command=lambda c=cmd: self.send_command(c))
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        
        # Right side: Visualization (Polar Plot and Map)
        right_frame = ttk.Frame(middle_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Create visualization frames
        viz_frame = ttk.Frame(right_frame)
        viz_frame.pack(fill=tk.BOTH, expand=True)
        
        # Polar Plot frame (top)
        polar_frame = ttk.LabelFrame(viz_frame, text="Sensor Scan")
        polar_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Create polar plot (half circle for 0-180 degrees)
        self.polar_fig = Figure(figsize=(6, 3), dpi=100)
        self.polar_ax = self.polar_fig.add_subplot(111, projection='polar')
        
        # Configure for half circle (0-180 degrees)
        self.polar_ax.set_thetamin(0)
        self.polar_ax.set_thetamax(180)
        
        # 0 degrees at right, 90 at top, 180 at left
        self.polar_ax.set_theta_zero_location("E")
        self.polar_ax.set_rlabel_position(-22.5)
        self.polar_ax.set_rticks([0.5, 1, 1.5, 2, 2.5])
        self.polar_ax.set_rmax(2.5)
        self.polar_ax.set_title("CyBot Sensor Scan (0°-180°)")
        self.polar_canvas = FigureCanvasTkAgg(self.polar_fig, polar_frame)
        self.polar_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Map frame (bottom)
        map_frame = ttk.LabelFrame(viz_frame, text="Navigation Map")
        map_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Create map plot
        self.map_fig = Figure(figsize=(6, 4), dpi=100)
        self.map_ax = self.map_fig.add_subplot(111)
        self.map_ax.set_xlim(-250, 250)
        self.map_ax.set_ylim(-250, 250)
        self.map_ax.set_xlabel("X Position (cm)")
        self.map_ax.set_ylabel("Y Position (cm)")
        self.map_ax.set_title("CyBot Map")
        self.map_ax.grid(True)
        self.map_canvas = FigureCanvasTkAgg(self.map_fig, map_frame)
        self.map_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.update_map()
        
        # Bottom section: Log
        self.log_frame = ttk.LabelFrame(main_frame, text="Log")
        self.log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def toggle_log(self):
        self.show_log = not self.show_log
        if self.show_log:
            self.log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        else:
            self.log_frame.pack_forget()
    
    def toggle_connection(self):
        if not self.connected:
            self.connect()
        else:
            self.disconnect()
    
    def connect(self):
        try:
            # Hardcoded IP and port
            ip = "192.168.1.1"
            port = 288
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3)  # 3 second timeout for connection
            self.socket.connect((ip, port))
            self.socket.settimeout(None)  # Remove timeout for normal operation
            
            self.connected = True
            self.connect_button.config(text="Disconnect")
            self.status_label.config(text="Connected", foreground="green")
            
            # Start receive thread
            self.stop_thread = False
            self.receive_thread = threading.Thread(target=self.receive_data)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            self.log("Connected to CyBot at {}:{}".format(ip, port))
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.log(f"Connection error: {str(e)}")
    
    def disconnect(self):
        if self.socket:
            try:
                self.stop_thread = True
                time.sleep(0.5)  # Give receive thread time to exit
                self.socket.close()
            except:
                pass
            finally:
                self.socket = None
        
        self.connected = False
        self.connect_button.config(text="Connect to 192.168.1.1:288")
        self.status_label.config(text="Disconnected", foreground="red")
        self.log("Disconnected from CyBot")
    
    def send_command(self, cmd):
        if not self.connected:
            messagebox.showinfo("Not Connected", "Please connect to CyBot first")
            return
        
        try:
            # Some commands need special handling
            if cmd == 'm':
                # For move command, we need to get turn angle and distance
                angle_dialog = MovementDialog(self.root, "Enter turn angle (+ right, - left)")
                if angle_dialog.result is not None:
                    turn_angle = angle_dialog.result
                    
                    distance_dialog = MovementDialog(self.root, "Enter distance (cm)")
                    if distance_dialog.result is not None:
                        distance_cm = distance_dialog.result
                        
                        # Send the 'm' command
                        self.socket.send(f"{cmd}\n".encode())
                        self.log(f"Sent: {cmd}")
                        
                        # Wait for the prompt for turn angle
                        time.sleep(0.5)
                        
                        # Send turn angle
                        self.socket.send(f"{turn_angle}\n".encode())
                        self.log(f"Sent turn angle: {turn_angle}")
                        
                        # Wait for the prompt for distance
                        time.sleep(0.5)
                        
                        # Send distance
                        self.socket.send(f"{distance_cm}\n".encode())
                        self.log(f"Sent distance: {distance_cm}")
                        
                        # The movement will be processed in the receive_data method
                        # when confirmation is received
            else:
                # Simple command, just send it
                self.socket.send(f"{cmd}\n".encode())
                self.log(f"Sent: {cmd}")
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send command: {str(e)}")
            self.log(f"Send error: {str(e)}")
    
    def receive_data(self):
        buffer = ""
        
        while not self.stop_thread:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                
                # Log raw data for debugging
                self.log(f"Raw data received: {repr(data)}", "gray")
                
                # Add to buffer and process lines
                buffer += data
                lines = buffer.split('\n')
                
                # Keep the last incomplete line in the buffer
                buffer = lines.pop() if lines else ""
                
                for line in lines:
                    if line.strip():  # Skip empty lines
                        self.process_line(line)
            except Exception as e:
                if not self.stop_thread:  # Only log if not stopping intentionally
                    self.log(f"Receive error: {str(e)}")
                    break
        
        if not self.stop_thread:  # Only disconnect if not stopping intentionally
            self.root.after(0, self.disconnect)  # Disconnect in main thread
    
    def process_line(self, line):
        # Log the received line
        self.log(f"Received: {line}", "blue")
        
        # Check for scan data - need to handle both IR and PING scan formats
        if self.scan_data['type'] is not None:
            # Try to parse scan data line
            self.process_scan_data(line)
        
        # Check for movement confirmation
        elif "Moving forward" in line:
            distance_mm = self.extract_number(line, r"Moving forward (\d+) mm")
            if distance_mm is not None:
                self.move_forward(distance_mm / 10)  # Convert mm to cm
        
        elif "Turning right" in line:
            angle = self.extract_number(line, r"Turning right (\d+) degrees")
            if angle is not None:
                self.turn_right(angle)
        
        elif "Turning left" in line:
            angle = self.extract_number(line, r"Turning left (\d+) degrees")
            if angle is not None:
                self.turn_left(angle)
        
        # Check for scan start
        elif "Beginning IR environment scan" in line:
            self.scan_data = {'angles': [], 'distances': [], 'type': 'IR'}
            self.log("Starting IR scan data collection")
        
        elif "Beginning PING environment scan" in line:
            self.scan_data = {'angles': [], 'distances': [], 'type': 'PING'}
            self.log("Starting PING scan data collection")
        
        # Check for scan completion
        elif "IR scan complete" in line or "PING scan complete" in line:
            self.log(f"{self.scan_data['type']} scan complete. Processing data...")
            self.complete_scan()
        
        # Look for object detection results lines
        elif "Object Detection Results" in line:
            self.log("Processing object detection results...")
            # Reset object list when new detection starts
            if "IR Object Detection Results" in line:
                self.objects = []  # Reset only when IR detection starts
        
        # Process object data lines like: "  1 |   45.0 |   35.20 |   15.30"
        elif "|" in line and re.search(r'\d+\s*\|\s*\d+\.\d+\s*\|\s*\d+\.\d+\s*\|\s*\d+\.\d+', line):
            self.process_object_data(line)
        
        # Check for blue sample detection
        elif "blue sample detected" in line:
            self.log("Blue water sample detected!")
            # Add water sample at current position
            self.water_samples.append({
                'x': self.cybot_position['x'],
                'y': self.cybot_position['y']
            })
            self.update_map()
    
    def process_scan_data(self, line):
        # Skip header lines and empty lines
        if "Angle" in line or "Distance" in line or "---" in line or not line.strip():
            return
        
        # Debug the line format
        self.log(f"Parsing scan line: '{line}'")
        
        # Parse scan data line - handle both formats
        # IR format has: angle, distance, IR raw
        # PING format has: angle, distance
        parts = line.strip().split()
        
        if len(parts) >= 2:  # At least angle and distance
            try:
                angle = float(parts[0])
                distance = float(parts[1])
                
                # Log the parsed values
                self.log(f"Parsed scan data: angle={angle}, distance={distance}")
                
                # Only store valid data points
                if 0 <= angle <= 180 and distance > 0:
                    self.scan_data['angles'].append(angle)
                    self.scan_data['distances'].append(distance)
            except Exception as e:
                self.log(f"Error parsing scan data: {str(e)}")
                # Try to recover what we can
                try:
                    # Look for numbers in the line
                    numbers = re.findall(r"[\d.]+", line)
                    if len(numbers) >= 2:
                        angle = float(numbers[0])
                        distance = float(numbers[1])
                        
                        # Only store valid data points
                        if 0 <= angle <= 180 and distance > 0:
                            self.scan_data['angles'].append(angle)
                            self.scan_data['distances'].append(distance)
                            self.log(f"Recovered scan data: angle={angle}, distance={distance}")
                except:
                    pass  # If recovery fails, just skip this line
    
    def process_object_data(self, line):
        # Debug the raw object data line
        self.log(f"Processing object data: '{line}'")
        
        try:
            # Parse the object data line format: "  1 |   45.0 |   35.20 |   15.30"
            # Split by | and extract numbers
            parts = line.split('|')
            if len(parts) < 4:
                return  # Not enough parts
                
            obj_id = int(parts[0].strip())
            center_angle = float(parts[1].strip())
            distance = float(parts[2].strip())
            width = float(parts[3].strip())
            
            # Log the extracted object properties
            self.log(f"Object {obj_id}: angle={center_angle}, distance={distance}, width={width}")
            
            # Convert angle and distance to x,y coordinates relative to CyBot
            # Note: CyBot uses 0° = right, 90° = forward, 180° = left
            theta = math.radians(center_angle)
            
            # Calculate object position (relative to current CyBot position)
            # Sin for X because 90° is forward, Cos for Y because 0° is right
            rel_x = distance * math.sin(theta)
            rel_y = distance * math.cos(theta)
            
            # Transform by CyBot's current position and orientation
            cybot_theta = math.radians(self.cybot_position['angle'])
            rotated_x = rel_x * math.cos(cybot_theta) - rel_y * math.sin(cybot_theta)
            rotated_y = rel_x * math.sin(cybot_theta) + rel_y * math.cos(cybot_theta)
            
            abs_x = self.cybot_position['x'] + rotated_x
            abs_y = self.cybot_position['y'] + rotated_y
            
            # Add to objects list
            self.objects.append({
                'id': obj_id,
                'x': abs_x,
                'y': abs_y,
                'angle': center_angle,
                'distance': distance,
                'width': width,
                'type': self.scan_data['type'] or 'Unknown'  # IR or PING
            })
            
            # Update map after adding an object
            self.update_map()
            
            # Log the added object
            self.log(f"Added object at map position: x={abs_x:.1f}, y={abs_y:.1f}")
            
        except Exception as e:
            self.log(f"Error processing object data: {str(e)}")
            # Try a more forgiving approach
            try:
                # Find all numbers in the line
                numbers = re.findall(r"[\d.]+", line)
                if len(numbers) >= 4:
                    obj_id = int(float(numbers[0]))
                    center_angle = float(numbers[1])
                    distance = float(numbers[2])
                    width = float(numbers[3])
                    
                    # Log recovery attempt
                    self.log(f"Recovered object data: id={obj_id}, angle={center_angle}, distance={distance}, width={width}")
                    
                    # Rest of the code as above...
                    theta = math.radians(center_angle)
                    rel_x = distance * math.sin(theta)
                    rel_y = distance * math.cos(theta)
                    
                    cybot_theta = math.radians(self.cybot_position['angle'])
                    rotated_x = rel_x * math.cos(cybot_theta) - rel_y * math.sin(cybot_theta)
                    rotated_y = rel_x * math.sin(cybot_theta) + rel_y * math.cos(cybot_theta)
                    
                    abs_x = self.cybot_position['x'] + rotated_x
                    abs_y = self.cybot_position['y'] + rotated_y
                    
                    self.objects.append({
                        'id': obj_id,
                        'x': abs_x,
                        'y': abs_y,
                        'angle': center_angle,
                        'distance': distance,
                        'width': width,
                        'type': self.scan_data['type'] or 'Unknown'
                    })
                    
                    self.update_map()
                    self.log(f"Added recovered object at map position: x={abs_x:.1f}, y={abs_y:.1f}")
            except Exception as inner_e:
                self.log(f"Failed to recover object data: {str(inner_e)}")
    
    def complete_scan(self):
        if not self.scan_data['angles'] or not self.scan_data['distances']:
            self.log("Warning: No scan data to process")
            self.scan_data = {'angles': [], 'distances': [], 'type': None}
            return
        
        # Log the collected data for debugging
        self.log(f"Scan complete. Collected {len(self.scan_data['angles'])} data points.")
        self.log(f"Angle range: {min(self.scan_data['angles'])}-{max(self.scan_data['angles'])}")
        self.log(f"Distance range: {min(self.scan_data['distances']):.2f}-{max(self.scan_data['distances']):.2f}")
        
        # Update polar plot with the scan data
        self.update_polar_plot()
        
        # Clear scan data type to stop collecting
        scan_type = self.scan_data['type']
        self.scan_data = {'angles': [], 'distances': [], 'type': None}
        
        # Log completion
        self.log(f"{scan_type} scan visualization complete.")
    
    def update_polar_plot(self):
        # Convert angles to radians for polar plot
        # CyBot uses 0° = right, 90° = forward, 180° = left
        # which matches our polar plot configuration
        angles_rad = [math.radians(angle) for angle in self.scan_data['angles']]
        
        # Clear previous plot
        self.polar_ax.clear()
        
        # Set up polar plot (half circle for 0-180 degrees)
        self.polar_ax.set_thetamin(0)
        self.polar_ax.set_thetamax(180)
        self.polar_ax.set_theta_zero_location("E")  # 0 at right
        self.polar_ax.set_rlabel_position(-22.5)
        self.polar_ax.set_rticks([0.5, 1, 1.5, 2, 2.5])
        self.polar_ax.set_rmax(2.5)
        
        # Plot scan data
        color = 'red' if self.scan_data['type'] == 'IR' else 'blue'
        self.polar_ax.plot(angles_rad, self.scan_data['distances'], color=color, linewidth=2)
        
        # Set title
        self.polar_ax.set_title(f"CyBot {self.scan_data['type']} Scan (0°-180°)")
        
        # Redraw canvas
        self.polar_canvas.draw()
    
    def update_map(self):
        # Clear previous plot
        self.map_ax.clear()
        
        # Set up map
        self.map_ax.set_xlim(-250, 250)
        self.map_ax.set_ylim(-250, 250)
        self.map_ax.set_xlabel("X Position (cm)")
        self.map_ax.set_ylabel("Y Position (cm)")
        self.map_ax.set_title("CyBot Map")
        self.map_ax.grid(True)
        
        # Plot movement history
        x_history = [pos['x'] for pos in self.movement_history]
        y_history = [pos['y'] for pos in self.movement_history]
        self.map_ax.plot(x_history, y_history, 'k-', linewidth=1)
        
        # Plot objects
        for obj in self.objects:
            color = 'red' if obj['type'] == 'IR' else 'blue'
            circle = plt.Circle((obj['x'], obj['y']), obj['width']/2, 
                               color=color, alpha=0.5)
            self.map_ax.add_patch(circle)
            
            # Add width label
            self.map_ax.annotate(f"{obj['width']:.1f}cm", 
                               (obj['x'], obj['y']), 
                               fontsize=8, 
                               ha='center', va='center')
        
        # Plot water samples
        for sample in self.water_samples:
            self.map_ax.plot(sample['x'], sample['y'], 'bo', markersize=10)
            self.map_ax.annotate("WATER", 
                               (sample['x'], sample['y']), 
                               fontsize=8, 
                               ha='center', va='center', 
                               xytext=(0, 10), 
                               textcoords='offset points')
        
        # Plot CyBot position and direction
        # Draw CyBot as a triangle pointing in the current direction
        bot_size = 20  # Size of triangle
        
        # Calculate triangle points based on position and angle
        theta = math.radians(self.cybot_position['angle'])
        x1 = self.cybot_position['x'] + bot_size * math.sin(theta)
        y1 = self.cybot_position['y'] + bot_size * math.cos(theta)
        
        # Create points 60 degrees to either side for the back corners
        theta_left = theta + math.radians(150)
        theta_right = theta - math.radians(150)
        
        x2 = self.cybot_position['x'] + bot_size * math.sin(theta_left)
        y2 = self.cybot_position['y'] + bot_size * math.cos(theta_left)
        
        x3 = self.cybot_position['x'] + bot_size * math.sin(theta_right)
        y3 = self.cybot_position['y'] + bot_size * math.cos(theta_right)
        
        self.map_ax.fill([x1, x2, x3], [y1, y2, y3], 'green', alpha=0.7)
        
        # Redraw canvas
        self.map_canvas.draw()
    
    def move_forward(self, distance_cm):
        # Calculate new position based on current angle
        theta = math.radians(self.cybot_position['angle'])
        dx = distance_cm * math.sin(theta)
        dy = distance_cm * math.cos(theta)
        
        # Update position
        self.cybot_position['x'] += dx
        self.cybot_position['y'] += dy
        
        # Add to movement history
        self.movement_history.append(dict(self.cybot_position))
        
        # Update map
        self.update_map()
        self.log(f"Moved forward {distance_cm} cm")
    
    def turn_right(self, angle):
        # Update angle (negative because right turn decreases angle)
        self.cybot_position['angle'] -= angle
        
        # Normalize angle to 0-360
        self.cybot_position['angle'] %= 360
        
        # Add to movement history
        self.movement_history.append(dict(self.cybot_position))
        
        # Update map
        self.update_map()
        self.log(f"Turned right {angle} degrees")
    
    def turn_left(self, angle):
        # Update angle (positive because left turn increases angle)
        self.cybot_position['angle'] += angle
        
        # Normalize angle to 0-360
        self.cybot_position['angle'] %= 360
        
        # Add to movement history
        self.movement_history.append(dict(self.cybot_position))
        
        # Update map
        self.update_map()
        self.log(f"Turned left {angle} degrees")
    
    def extract_number(self, text, pattern):
        match = re.search(pattern, text)
        if match:
            try:
                return float(match.group(1))
            except:
                return None
        return None
    
    def log(self, message, color="black"):
        if not self.show_log:
            return
            
        # Add timestamp
        timestamp = time.strftime("%H:%M:%S")
        
        # Skip debug messages if debug mode is off
        if color == "gray" and not self.debug_mode:
            return
            
        full_message = f"[{timestamp}] {message}\n"
        
        # Update log in main thread
        self.root.after(0, self._update_log, full_message, color)
    
    def _update_log(self, message, color):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message)
        
        # Apply color to the last inserted line
        last_line_start = self.log_text.index(f"end-{len(message)+1}c")
        last_line_end = self.log_text.index("end-1c")
        self.log_text.tag_add(color, last_line_start, last_line_end)
        self.log_text.tag_config(color, foreground=color)
        
        self.log_text.see(tk.END)  # Scroll to the end
        self.log_text.config(state=tk.DISABLED)
    
    def on_closing(self):
        if self.connected:
            self.disconnect()
        self.root.destroy()


class MovementDialog:
    def __init__(self, parent, prompt):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Input Required")
        self.dialog.geometry("300x120")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center on parent
        x = parent.winfo_x() + parent.winfo_width() // 2 - 150
        y = parent.winfo_y() + parent.winfo_height() // 2 - 60
        self.dialog.geometry(f"+{x}+{y}")
        
        # Add prompt label
        ttk.Label(self.dialog, text=prompt).pack(pady=(10, 5))
        
        # Add entry field
        self.entry = ttk.Entry(self.dialog, width=10)
        self.entry.pack(pady=5)
        self.entry.focus_set()
        
        # Add buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Handle Enter key
        self.dialog.bind("<Return>", lambda event: self.on_ok())
        self.dialog.bind("<Escape>", lambda event: self.on_cancel())
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def on_ok(self):
        try:
            self.result = float(self.entry.get())
            self.dialog.destroy()
        except ValueError:
            tk.messagebox.showerror("Invalid Input", "Please enter a valid number")
    
    def on_cancel(self):
        self.dialog.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CybotControlApp(root)
    root.mainloop()