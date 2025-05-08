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

class CybotControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PING PATROL GUI")
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
        
        # Create UI elements
        self.create_menu()
        self.create_main_frame()
        
        # Log toggle state
        self.show_log = True
        
    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.on_closing)
        menu_bar.add_cascade(label="File", menu=file_menu)
        
        # View menu
        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_checkbutton(label="Show Log", command=self.toggle_log, variable=tk.BooleanVar(value=True))
        menu_bar.add_cascade(label="View", menu=view_menu)
        
        self.root.config(menu=menu_bar)
    
    def create_main_frame(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top section: Connection
        connection_frame = ttk.LabelFrame(main_frame, text="Connection")
        connection_frame.pack(fill=tk.X, pady=5)
        
        # Simplified connection controls with hardcoded IP and port
        self.connect_button = ttk.Button(connection_frame, text="Connect to CyBot", command=self.toggle_connection)
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
                
                buffer += data
                lines = buffer.split('\n')
                buffer = lines.pop()  # Keep the last incomplete line in the buffer
                
                for line in lines:
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
        
        # Check for scan data
        if self.scan_data['type'] is not None:
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
        
        # Check for object detection
        elif "Object Detection Results" in line:
            # Reset object list when new detection starts
            if "IR Object Detection Results" in line:
                self.objects = []  # Reset only when IR detection starts
            # PING object detection will be processed separately
        
        # Process object data
        elif re.match(r'^\s*\d+\s+\|\s+\d+\.\d+\s+\|\s+\d+\.\d+\s+\|\s+\d+\.\d+\s*$', line):
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
        # Skip header lines
        if "Angle" in line or "---" in line or not line.strip():
            return
        
        # Parse scan data line
        parts = line.strip().split()
        if len(parts) >= 2:  # At least angle and distance
            try:
                angle = float(parts[0])
                distance = float(parts[1])
                
                self.scan_data['angles'].append(angle)
                self.scan_data['distances'].append(distance)
            except:
                pass  # Skip lines that don't parse correctly
    
    def process_object_data(self, line):
        # Example line format: "  1 |   45.0 |   35.20 |   15.30"
        parts = re.findall(r'[\d.]+', line)
        if len(parts) >= 4:
            try:
                obj_id = int(parts[0])
                center_angle = float(parts[1])
                distance = float(parts[2])
                width = float(parts[3])
                
                # Convert angle and distance to x,y coordinates relative to CyBot
                # Note: CyBot uses 0° = right, 90° = forward, 180° = left
                # Convert to standard: 0° = right, 90° = up, 180° = left, 270° = down
                theta = math.radians(center_angle)
                
                # Calculate object position (relative to current CyBot position)
                # Note: we need to convert from CyBot coordinate system to our map system
                rel_x = distance * math.sin(theta)  # sin because 90° is forward in CyBot system
                rel_y = distance * math.cos(theta)  # cos because 0° is right in CyBot system
                
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
                    'type': self.scan_data['type']  # IR or PING
                })
                
                self.update_map()
            except Exception as e:
                self.log(f"Error processing object data: {str(e)}")
    
    def complete_scan(self):
        if not self.scan_data['angles'] or not self.scan_data['distances']:
            self.log("No scan data to process")
            self.scan_data = {'angles': [], 'distances': [], 'type': None}
            return
        
        # Update polar plot
        self.update_polar_plot()
        
        # Clear scan data type to stop collecting
        self.scan_data['type'] = None
    
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