from math import atan2
import os
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPixmap
from PyQt5.QtCore import QElapsedTimer, QPointF, Qt, pyqtSignal
from Primary_Flight_Display import PrimaryFlightDisplay, QPen, QPoint, QPolygon, QRect, QTimer, QTransform  # Adjust path if needed
from Controller import Controller
from Input_Control import InputControl

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()

class IndicatorLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active = False
        self.color = "#2d2d2d"  # Default to dark gray

    def set_active(self, active, color="#2d2d2d"):
        self.active = active
        self.color = color
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        if self.active:
            painter.setBrush(QColor(self.color))  # Use the specified color
            painter.setPen(Qt.NoPen)
            painter.drawRect(0, 0, self.width(), self.height())

            # Draw black dividers to create three equal segments
            total_height = self.height()
            segment_height = total_height // 3
            margin = 1  # Margin between segments

            painter.setBrush(QColor("#000000"))  # Black for the dividers
            for i in range(1, 3):
                painter.drawRect(0, i * segment_height, self.width(), margin)  # Dividers between segments
        else:
            # Draw the entire dark gray rectangle for inactive state
            painter.setBrush(QColor("#2d2d2d"))
            painter.setPen(Qt.NoPen)
            painter.drawRect(0, 0, self.width(), self.height())

class FlightControlUnit(QWidget):
    def __init__(self, primary_flight_display):
        super().__init__()
        self.heading_select = 17
        self.speed_digits = 250
        self.vertical_speed_digits = 1500
        self.altitude_select = 30000
        self.loc_active = False
        self.alt_hold_active = False
        self.alt_hold_armed = False
        self.hdg_trk_active = False
        self.appr_active = False
        self.ap1_active = False
        self.ap2_active = False
        self.athr_active = False
        self.athr_armed = False
        self.knob_angle = 0
        self.current_heading = 0  # Add for current heading
        self.primary_flight_display = primary_flight_display
        self.input_control = InputControl(self.primary_flight_display)
        self.controller = Controller(self, self.input_control)  # Initialize the controller
        self.initUI()
        self.start_heading_update_timer()

    def initUI(self):
        self.setWindowTitle('Flight Control Unit')
        self.setGeometry(300, 300, 400, 638)  # Adjusted window height
        self.setStyleSheet("background-color: black;")

        # Create top Mode Control Panel display
        self.mode_control_panel = self.create_mode_control_panel()

        # Add outer circle with adjusted size and alignment
        outer_circle_radius = 30  # Reduced radius
        knob_x, knob_y, knob_width, knob_height = 177, 127, 46, 46
        self.outer_circle = QLabel(self)
        self.outer_circle.setGeometry(knob_x + (knob_width // 2) - outer_circle_radius, knob_y + (knob_height // 2) - outer_circle_radius, outer_circle_radius * 2, outer_circle_radius * 2)
        self.outer_circle.setStyleSheet(f"background-color: #7D786D; border-radius: {outer_circle_radius}px;")

        # Add white circle with outline only outside the outer circle
        white_circle_radius = 36  # Slightly larger radius
        self.white_circle = QLabel(self)
        self.white_circle.setGeometry(knob_x + (knob_width // 2) - white_circle_radius, knob_y + (knob_height // 2) - white_circle_radius, white_circle_radius * 2, white_circle_radius * 2)
        self.white_circle.setStyleSheet(f"border: 2px solid white; border-radius: {white_circle_radius}px; background-color: transparent;")

        # Create knob for heading adjustment below Mode Control Panel
        self.knob = HeadingSelectKnob(self)
        self.knob.setGeometry(knob_x, knob_y, knob_width, knob_height)  # Positioned knob lower with more spacing

        # Create outer circle for the SPD/M knob
        spd_knob_x, spd_knob_y, spd_knob_width, spd_knob_height = 64, 127, 46, 46  # Position to the left of the heading knob
        self.spd_outer_circle = QLabel(self)
        self.spd_outer_circle.setGeometry(spd_knob_x + (spd_knob_width // 2) - outer_circle_radius, spd_knob_y + (spd_knob_height // 2) - outer_circle_radius, outer_circle_radius * 2, outer_circle_radius * 2)
        self.spd_outer_circle.setStyleSheet(f"background-color: #7D786D; border-radius: {outer_circle_radius}px;")
        
        # Add white circle with outline for the SPD/M knob
        self.spd_white_circle = QLabel(self)
        self.spd_white_circle.setGeometry(spd_knob_x + (spd_knob_width // 2) - white_circle_radius, spd_knob_y + (spd_knob_height // 2) - white_circle_radius, white_circle_radius * 2, white_circle_radius * 2)
        self.spd_white_circle.setStyleSheet(f"border: 2px solid white; border-radius: {white_circle_radius}px; background-color: transparent;")

        # Create knob for SPD/M adjustment below Mode Control Panel
        self.spd_knob = SpeedMachKnob(self)
        self.spd_knob.setGeometry(spd_knob_x, spd_knob_y, spd_knob_width, spd_knob_height)

        # Add first separator line below knob
        self.first_separator_line = QLabel(self)
        self.first_separator_line.setGeometry(30, 200, 340, 2)  # Position the line below the knob
        self.first_separator_line.setStyleSheet("background-color: #444;")

        # Create Vertical Control Panel display below the knob
        self.vertical_control_panel = self.create_vertical_control_panel()
        self.vertical_control_panel.setGeometry(30, 210, 340, 80)  # Adjusted y-position for vertical control panel

        # Create second dark gray line separator below the vertical control panel
        self.second_separator_line = QLabel(self)
        self.second_separator_line.setGeometry(30, 300, 340, 2)  # Position the line below the vertical control panel
        self.second_separator_line.setStyleSheet("background-color: #444;")

        # Adjust the spacing after the second separator line
        self.second_separator_line.move(self.second_separator_line.x(), self.second_separator_line.y() + 10)

        # Increase spacing below the second separator line for button container
        button_spacing = 30  # Adjust the spacing value as needed
        button_y_position = self.second_separator_line.y() + button_spacing

        # Create containers for each button with adjusted y-position
        self.alt_container = self.create_button_container('ALT\nHOLD', button_y_position, self.toggle_alt_hold)  # Move buttons lower
        self.ap1_container = self.create_button_container('AP1', button_y_position + 100, self.toggle_ap1)  # Move AP1 down a row
        self.ap2_container = self.create_button_container('AP2', button_y_position + 100, self.toggle_ap2)  # Move AP2 down a row
        self.athr_container = self.create_button_container('A/THR', button_y_position + 200, self.toggle_athr)
        self.loc_container = self.create_button_container('LOC', button_y_position + 100, self.toggle_loc_visibility)  # Align vertically below ALT HOLD
        self.appr_container = self.create_button_container('APPR', button_y_position + 200, self.toggle_appr_visibility)  # Align vertically below ALT HOLD

        # Create HDG TRK knob on the first row, between the second and third columns
        hdg_trk_knob_x, hdg_trk_knob_y, hdg_trk_knob_radius = 220, button_y_position, 25
        self.hdg_trk_knob = QPushButton(self)
        self.hdg_trk_knob.setGeometry(hdg_trk_knob_x, hdg_trk_knob_y, hdg_trk_knob_radius * 2, hdg_trk_knob_radius * 2)
        self.hdg_trk_knob.setStyleSheet(f"""
            background-color: #7D786D;
            border-radius: {hdg_trk_knob_radius}px;
        """)
        self.hdg_trk_knob.clicked.connect(self.toggle_hdg_trk)  # Connect the button to the function
        
        # Ensure button is on top layer and is visible
        self.hdg_trk_knob.raise_()
        self.hdg_trk_knob.setFocusPolicy(Qt.ClickFocus)  # Ensure button receives focus
        self.hdg_trk_knob.show()  # Make sure the button is visible

        # Add white outline for the HDG TRK knob
        self.hdg_trk_knob_outline = QLabel(self)
        self.hdg_trk_knob_outline.setGeometry(hdg_trk_knob_x - 6, hdg_trk_knob_y - 6, hdg_trk_knob_radius * 2 + 12, hdg_trk_knob_radius * 2 + 12)
        self.hdg_trk_knob_outline.setStyleSheet(f"border: 2px solid white; border-radius: {hdg_trk_knob_radius + 6}px; background-color: transparent;")
        self.hdg_trk_knob_outline.lower()  # Ensure outline is behind the button
        
        # Add "HDG TRK" label to the left of the circular button
        self.hdg_trk_label = QLabel("HDG\nTRK", self)
        self.hdg_trk_label.setGeometry(hdg_trk_knob_x - 50, hdg_trk_knob_y, 40, 40)
        self.hdg_trk_label.setStyleSheet("color: white; font-size: 14px; text-align: center;")
        self.hdg_trk_label.setAlignment(Qt.AlignCenter)

        # Add "V/S FPA" label to the right of the circular button
        self.vs_fpa_label = QLabel("V/S\nFPA", self)
        self.vs_fpa_label.setGeometry(hdg_trk_knob_x + 60, hdg_trk_knob_y, 40, 40)
        self.vs_fpa_label.setStyleSheet("color: white; font-size: 14px; text-align: center;")
        self.vs_fpa_label.setAlignment(Qt.AlignCenter)

        print("UI setup complete")

    def start_heading_update_timer(self):
        self.heading_update_timer = QTimer(self)
        self.heading_update_timer.timeout.connect(self.update_current_heading)
        self.heading_update_timer.start(1000)  # Update every second

    def update_current_heading(self):
        # Get current heading from PrimaryFlightDisplay
        self.current_heading = self.primary_flight_display.current_heading
        self.primary_flight_display.update()

    def create_vertical_control_panel(self):
        container = QWidget(self)
        container.setGeometry(30, 120, 340, 80)  # Positioned below the mode control panel
        container.setStyleSheet("background-color: black;")  # Black background
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # First row
        first_row = QWidget(container)
        first_row_layout = QHBoxLayout(first_row)
        first_row_layout.setContentsMargins(0, 0, 0, 0)
        
        alt_label = QLabel("ALT", first_row)
        alt_label.setStyleSheet("color: #FFC90E; font-size: 14px;")
        first_row_layout.addWidget(alt_label, alignment=Qt.AlignCenter)  # Center the ALT label
        
        lvlch_label = QLabel("LVL / CH", first_row)
        lvlch_label.setStyleSheet("color: #FFC90E; font-size: 14px; margin-left: 10px;")
        first_row_layout.addWidget(lvlch_label, alignment=Qt.AlignCenter)
        
        vs_label = QLabel("V/S", first_row)
        vs_label.setStyleSheet("color: #FFC90E; font-size: 14px; margin-left: 10px;")
        first_row_layout.addWidget(vs_label, alignment=Qt.AlignCenter)  # Center the V/S label
        
        layout.addWidget(first_row)
        
        # Second row
        second_row = QWidget(container)
        second_row_layout = QHBoxLayout(second_row)
        second_row_layout.setContentsMargins(0, 0, 0, 0)

        # Function to add 7-segment digits
        def add_segment_digits(container, value, num_digits=5):
            digit_container = QWidget(container)
            digit_layout = QHBoxLayout(digit_container)
            digit_layout.setSpacing(4)  # Increase the space between the digits slightly
            digit_layout.setContentsMargins(0, 0, 0, 0)
            for digit in str(value).zfill(num_digits):  # Ensure there are num_digits digits, pad with zeros if necessary
                digit_label = QLabel(container)
                digit_pixmap = QPixmap(os.path.join(os.path.dirname(__file__), "7 segment digits", f"{digit}.png"))
                digit_pixmap = digit_pixmap.scaled(20, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Scale the images
                digit_label.setPixmap(digit_pixmap)
                digit_layout.addWidget(digit_label)
            container.layout().addWidget(digit_container)

        # ALT value
        alt_container = QWidget(second_row)
        alt_layout = QHBoxLayout(alt_container)
        alt_layout.setContentsMargins(0, 0, 0, 0)
        alt_container.setStyleSheet("border: none;")  # No border
        add_segment_digits(alt_container, self.altitude_select, num_digits=5)
        second_row_layout.addWidget(alt_container, alignment=Qt.AlignCenter)
        
        # Empty space for LVL CH
        empty_widget = QWidget(second_row)
        second_row_layout.addWidget(empty_widget)
        
        # V/S value
        vs_container = QWidget(second_row)
        vs_layout = QHBoxLayout(vs_container)
        vs_layout.setContentsMargins(0, 0, 0, 0)
        vs_container.setStyleSheet("border: none;")  # No border
        add_segment_digits(vs_container, self.vertical_speed_digits, num_digits=5)
        second_row_layout.addWidget(vs_container, alignment=Qt.AlignCenter)
        
        layout.addWidget(second_row)
        
        # Add lines from LVL CH to the digits
        lines = QWidget(container)
        lines.setGeometry(0, 0, 340, 80)
        lines.setStyleSheet("background-color: transparent;")  # Transparent to see the background

        painter = QPainter(lines)
        painter.setPen(QPen(QColor("#FFC90E"), 2))  # Same color as the labels

        # Draw left line from LVL to ALT digits
        left_line_start = QPointF(170, 20)  # Starting point (x, y) from LVL
        left_line_mid = QPointF(90, 40)  # Midpoint (x, y) down to the middle
        left_line_end = QPointF(90, 80)  # Ending point (x, y) pointing to the digits
        painter.drawLine(left_line_start, left_line_mid)
        painter.drawLine(left_line_mid, left_line_end)

        return container

    def update_heading(self, heading_value, managed_mode=False):  # Added managed_mode parameter
        self.heading_select = heading_value
        self.add_segment_digits(self.hdg_layout, self.heading_select, managed_mode)
        self.mode_control_panel.update()

    def update_speed_mach(self, new_speed):
        self.speed_digits = new_speed
        self.spd_layout.setContentsMargins(0, 0, 0, 0)
        self.add_segment_digits(self.spd_layout, self.speed_digits)

    def add_segment_digits(self, layout, value, managed_mode=False):  # Added managed_mode parameter
        # Clear existing digits
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().deleteLater()
        if managed_mode:
            digit_pixmap = QPixmap(os.path.join(os.path.dirname(__file__), "7 segment digits", "managed.png"))
            digit_pixmap_resized = digit_pixmap.scaled(20, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            for _ in range(3):  # Assuming 3 digits for heading
                digit_label = QLabel()
                digit_label.setPixmap(digit_pixmap_resized)
                layout.addWidget(digit_label)
            # Add an orange circle on the right side
            circle_label = QLabel()
            circle_pixmap = QPixmap(10, 10)  # Reduced size to 10 pixels
            circle_pixmap.fill(Qt.transparent)
            painter = QPainter(circle_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor("#FFC90E")))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, 10, 10)  # Draw 10 pixel circle
            painter.end()
            circle_label.setPixmap(circle_pixmap)
            layout.addWidget(circle_label)
        else:
            for digit in str(value).zfill(3):
                digit_label = QLabel()
                digit_pixmap = QPixmap(os.path.join(os.path.dirname(__file__), "7 segment digits", f"{digit}.png"))
                digit_pixmap_resized = digit_pixmap.scaled(20, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                digit_label.setPixmap(digit_pixmap_resized)
                layout.addWidget(digit_label)

    def create_mode_control_panel(self):
        container_width = 340
        container_x = (self.width() - container_width) // 2
        container = QWidget(self)
        container.setGeometry(container_x, 10, container_width, 80)
        container.setStyleSheet("background-color: black;")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 5, 10, 5)

        # First row
        first_row = QWidget(container)
        first_row_layout = QHBoxLayout(first_row)
        first_row_layout.setContentsMargins(0, 0, 0, 0)
        spd_label = QLabel("SPD", first_row)
        spd_label.setStyleSheet("color: #FFC90E; font-size: 14px;")
        first_row_layout.addWidget(spd_label, alignment=Qt.AlignLeft)

        hglat_widget = QWidget(first_row)
        hglat_layout = QHBoxLayout(hglat_widget)
        hglat_layout.setContentsMargins(0, 0, 0, 0)
        heading_label = QLabel("HDG", hglat_widget)
        heading_label.setStyleSheet("color: #FFC90E; font-size: 14px;")
        hglat_layout.addWidget(heading_label)
        lat_label = QLabel("LAT", hglat_widget)
        lat_label.setStyleSheet("color: #FFC90E; font-size: 14px; margin-left: 10px;")
        hglat_layout.addWidget(lat_label)
        first_row_layout.addWidget(hglat_widget, alignment=Qt.AlignCenter)

        empty_widget1 = QWidget(first_row)
        first_row_layout.addWidget(empty_widget1)

        layout.addWidget(first_row)

        # Second row
        second_row = QWidget(container)
        second_row_layout = QHBoxLayout(second_row)
        second_row_layout.setContentsMargins(0, 0, 0, 0)

        # SPD value
        self.spd_container = QWidget(second_row)
        self.spd_layout = QHBoxLayout(self.spd_container)
        self.spd_layout.setContentsMargins(0, 0, 0, 0)
        self.spd_container.setStyleSheet("border: none;")
        self.add_segment_digits(self.spd_layout, self.speed_digits)
        second_row_layout.addWidget(self.spd_container, alignment=Qt.AlignCenter)

        # HDG value
        self.hdg_container = QWidget(second_row)
        self.hdg_layout = QHBoxLayout(self.hdg_container)
        self.hdg_layout.setContentsMargins(0, 0, 0, 0)
        self.hdg_container.setStyleSheet("border: none;")
        self.add_segment_digits(self.hdg_layout, self.heading_select)
        second_row_layout.addWidget(self.hdg_container, alignment=Qt.AlignCenter)

        # LAT value placeholder
        lat_value = QLabel("", second_row)
        lat_value.setStyleSheet("color: white; font-size: 14px; margin-left: 10px; border: none;")
        second_row_layout.addWidget(lat_value)

        layout.addWidget(second_row)

        return container
    
    def create_button_container(self, text, y_position, toggle_function):
        container = QWidget(self)
        if text == 'AP1':
            container_x = 160  # Center the AP1 button in the second column
        elif text == 'AP2':
            container_x = 280  # Center the AP2 button in the third column
        elif text == 'A/THR':
            container_x = 160  # Center the "A/THR" button below AP1
        elif text == 'LOC':
            container_x = 40  # Center the LOC button in the first column
        elif text in ['ALT\nHOLD', 'APPR']:
            container_x = 40  # Center ALT HOLD and APPR buttons in the first column
        container.setGeometry(container_x, y_position, 80, 80)
        container.setStyleSheet("background-color: #212121;")
        indicator = IndicatorLabel(container)
        indicator.setGeometry(16, 5, 48, 12)
        indicator.setStyleSheet("background-color: #212121;")  # Default to dark gray
        button = ClickableLabel(text, container)
        button.setGeometry(0, 20, 80, 60)
        button.setStyleSheet("background-color: #212121; color: white; font-size: 16px; text-align: center;")
        button.setAlignment(Qt.AlignCenter)
        button.clicked.connect(toggle_function)
        if text == 'ALT\nHOLD':
            self.alt_button = button
        elif text == 'LOC':
            self.loc_button = button
        elif text == 'APPR':
            self.appr_button = button
        elif text == 'AP1':
            self.ap1_button = button
        elif text == 'AP2':
            self.ap2_button = button
        elif text == 'A/THR':
            self.athr_button = button
        return container

    def toggle_hdg_trk(self):
        print("HDG TRK button pressed")  # Debug statement
        self.hdg_trk_active = not self.hdg_trk_active
        print(f"HDG TRK active: {self.hdg_trk_active}")  # Debug statement
        self.primary_flight_display.hdg_trk_active = self.hdg_trk_active  # Update status in PrimaryFlightDisplay

        # Pass the selected heading to the primary flight display
        self.primary_flight_display.selected_heading = self.heading_select
        self.primary_flight_display.update()  # Redraw the FMA

    def toggle_athr(self):
        # Implement functionality for toggling A/THR
        self.athr_armed = not self.athr_armed
        self.athr_active = False  # Reset active state when toggling armed state
        self.athr_container.findChild(IndicatorLabel).set_active(self.athr_armed, color="orange" if self.athr_armed else "#212121")
        self.primary_flight_display.update()
        print("A/THR button pressed")  # Add debug statement to verify button press

    def toggle_alt_hold(self):
        if self.appr_active:
            return  # Do nothing if APPR is active
        if not (self.ap1_active or self.ap2_active):
            self.alt_hold_armed = not self.alt_hold_armed
            self.alt_container.findChild(IndicatorLabel).set_active(self.alt_hold_armed, color="orange")  # Orange for armed
        else:
            self.alt_hold_active = not self.alt_hold_active
            self.alt_container.findChild(IndicatorLabel).set_active(self.alt_hold_active, color="#5EFF33")  # Green for active
        if not self.alt_hold_active:
            self.primary_flight_display.alt_hold_active = False  # Ensure LOC label is hidden if ALT HOLD is off
            self.loc_container.findChild(IndicatorLabel).set_active(False, color="#212121")  # Turn off LOC button
        self.primary_flight_display.alt_hold_active = self.alt_hold_active  # Ensure PrimaryFlightDisplay knows about ALT HOLD state
        self.primary_flight_display.alt_hold_armed = self.alt_hold_armed  # Ensure PrimaryFlightDisplay knows about ALT HOLD armed state
        self.primary_flight_display.update()

    def toggle_appr_visibility(self):
        self.appr_active = not self.appr_active  # Toggle APPR active state
        self.appr_container.findChild(IndicatorLabel).set_active(self.appr_active, color="orange" if not (self.ap1_active or self.ap2_active) else "#5EFF33")  # Orange for armed, green for active
        self.primary_flight_display.appr_active = self.appr_active  # Ensure PrimaryFlightDisplay knows about APPR state
        self.primary_flight_display.vertical_deviation_visible = self.appr_active if (self.ap1_active or self.ap2_active) else False  # Show vertical deviation scale only if active
        self.primary_flight_display.localizer_visible = self.appr_active if (self.ap1_active or self.ap2_active) else False  # Show localizer deviation scale only if active
        self.loc_active = self.appr_active  # Reflect APPR activation in LOC button
        self.loc_container.findChild(IndicatorLabel).set_active(self.loc_active, color="orange" if not (self.ap1_active or self.ap2_active) else "#5EFF33")  # Orange for armed, green for active
        self.primary_flight_display.show_gs_loc_labels = self.appr_active  # Show GS/LOC labels when APPR is active
        if self.appr_active and (self.ap1_active or self.ap2_active):
            self.alt_hold_armed = False  # Disarm ALT HOLD when APPR is activated
            self.alt_hold_active = False  # Ensure ALT HOLD is not active
            self.alt_container.findChild(IndicatorLabel).set_active(self.alt_hold_active, color="#212121")  # Turn off ALT-HOLD button
            self.primary_flight_display.toggle_alt_label(self.alt_hold_active)
        self.primary_flight_display.update()

    def toggle_loc_visibility(self):
        if self.appr_active:  # Check if APPR is active
            return  # Prevent disarming LOC if APPR is active
        self.loc_active = not self.loc_active  # Toggle LOC active state
        if not (self.ap1_active or self.ap2_active):
            self.loc_container.findChild(IndicatorLabel).set_active(self.loc_active, color="orange")  # Orange for armed
            self.primary_flight_display.localizer_visible = False  # Ensure the deviation scale is not shown when only armed
        else:
            self.loc_container.findChild(IndicatorLabel).set_active(self.loc_active, color="#5EFF33")  # Green for active LOC
            self.primary_flight_display.localizer_visible = self.loc_active  # Show the deviation scale when active
        self.primary_flight_display.loc_active = self.loc_active  # Ensure PrimaryFlightDisplay knows about LOC state
        self.primary_flight_display.update()

    def toggle_ap1(self):
        if self.ap2_active:
            self.ap2_active = False
            self.ap2_container.findChild(IndicatorLabel).set_active(self.ap2_active)
        self.ap1_active = not self.ap1_active
        self.ap1_container.findChild(IndicatorLabel).set_active(self.ap1_active, color="#5EFF33")  # Green for active AP1
        self.primary_flight_display.update_ap_status(self.ap1_active, 'AP1')
        # Activate the correct mode
        if self.ap1_active:
            if self.appr_active:
                self.appr_container.findChild(IndicatorLabel).set_active(True, color="#5EFF33")  # Engage APPR if armed
                self.loc_container.findChild(IndicatorLabel).set_active(True, color="#5EFF33")  # Ensure LOC also turns green
                self.primary_flight_display.vertical_deviation_visible = True  # Show vertical deviation scale
                self.primary_flight_display.localizer_visible = True  # Show localizer deviation scale
                self.alt_hold_armed = False  # Disarm ALT HOLD
                self.alt_hold_active = False  # Ensure ALT HOLD is off
                self.alt_container.findChild(IndicatorLabel).set_active(False, color="#212121")  # Turn off ALT-HOLD button
            elif self.loc_active:
                self.loc_container.findChild(IndicatorLabel).set_active(True, color="#5EFF33")  # Activate LOC if armed
                self.primary_flight_display.localizer_visible = True  # Show the deviation scale when LOC is active
                self.alt_hold_armed = False  # Disarm ALT HOLD
                self.alt_hold_active = False  # Ensure ALT HOLD is off
                self.alt_container.findChild(IndicatorLabel).set_active(False, color="#212121")  # Turn off ALT-HOLD button
            elif self.alt_hold_armed:
                self.alt_hold_active = True  # Engage ALT HOLD if armed
                self.alt_container.findChild(IndicatorLabel).set_active(True, color="#5EFF33")
        else:
            self.alt_hold_active = False
            self.alt_hold_armed = False
            self.appr_active = False
            self.loc_active = False
            self.primary_flight_display.vertical_deviation_visible = False  # Hide the vertical deviation scale when AP is off
            self.primary_flight_display.localizer_visible = False  # Hide the localizer deviation scale when AP is off
            self.appr_container.findChild(IndicatorLabel).set_active(False, color="#212121")  # Turn off APPR button
            self.loc_container.findChild(IndicatorLabel).set_active(False, color="#212121")  # Turn off LOC button
            self.alt_container.findChild(IndicatorLabel).set_active(False, color="#212121")  # Turn off ALT-HOLD button
            self.primary_flight_display.toggle_gs_loc_labels(False)  # Hide GS/LOC labels from flight mode annunciator
        self.primary_flight_display.toggle_alt_label(self.alt_hold_active)
        self.primary_flight_display.alt_hold_armed = self.alt_hold_armed 
        self.primary_flight_display.update()

    def toggle_ap2(self):
        if self.ap1_active:
            self.ap1_active = False
            self.ap1_container.findChild(IndicatorLabel).set_active(self.ap1_active)
        self.ap2_active = not self.ap2_active
        self.ap2_container.findChild(IndicatorLabel).set_active(self.ap2_active, color="#5EFF33")  # Green for active AP2
        self.primary_flight_display.update_ap_status(self.ap2_active, 'AP2')
        # Activate the correct mode
        if self.ap2_active:
            if self.appr_active:
                self.appr_container.findChild(IndicatorLabel).set_active(True, color="#5EFF33")  # Engage APPR if armed
                self.loc_container.findChild(IndicatorLabel).set_active(True, color="#5EFF33")  # Ensure LOC also turns green
                self.primary_flight_display.vertical_deviation_visible = True  # Show vertical deviation scale
                self.primary_flight_display.localizer_visible = True  # Show localizer deviation scale
                self.alt_hold_armed = False  # Disarm ALT HOLD
                self.alt_hold_active = False  # Ensure ALT HOLD is off
                self.alt_container.findChild(IndicatorLabel).set_active(False, color="#212121")  # Turn off ALT-HOLD button
            elif self.loc_active:
                self.loc_container.findChild(IndicatorLabel).set_active(True, color="#5EFF33")  # Activate LOC if armed
                self.primary_flight_display.localizer_visible = True  # Show the deviation scale when LOC is active
                self.alt_hold_armed = False  # Disarm ALT HOLD
                self.alt_hold_active = False  # Ensure ALT HOLD is off
                self.alt_container.findChild(IndicatorLabel).set_active(False, color="#212121")  # Turn off ALT-HOLD button
            elif self.alt_hold_armed:
                self.alt_hold_active = True  # Engage ALT HOLD if armed
                self.alt_container.findChild(IndicatorLabel).set_active(True, color="#5EFF33")
        else:
            self.alt_hold_active = False
            self.alt_hold_armed = False
            self.appr_active = False
            self.loc_active = False
            self.primary_flight_display.vertical_deviation_visible = False  # Hide the vertical deviation scale when AP is off
            self.primary_flight_display.localizer_visible = False  # Hide the localizer deviation scale when AP is off
            self.appr_container.findChild(IndicatorLabel).set_active(False, color="#212121")  # Turn off APPR button
            self.loc_container.findChild(IndicatorLabel).set_active(False, color="#212121")  # Turn off LOC button
            self.alt_container.findChild(IndicatorLabel).set_active(False, color="#212121")  # Turn off ALT-HOLD button
            self.primary_flight_display.toggle_gs_loc_labels(False)  # Hide GS/LOC labels from flight mode annunciator
        self.primary_flight_display.toggle_alt_label(self.alt_hold_active)
        self.primary_flight_display.alt_hold_armed = self.alt_hold_armed 
        self.primary_flight_display.update()

class HeadingSelectKnob(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.knob_angle = 0
        self.knob_start_pos = QPoint()
        self.total_rotation = 0  # Track cumulative rotation
        self.is_pressing = False  # Track if the mouse button is pressed
        self.managed_mode = False  # Track if managed mode is active
        self.press_timer = QTimer()
        self.press_timer.setSingleShot(True)
        self.press_timer.timeout.connect(self.on_press_timeout)
        self.rotated = False  # To track if the knob has been rotated

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.knob_start_pos = event.pos()
            self.is_pressing = True  # Set the pressing state to true
            self.press_timer.start(500)  # Start the timer for detecting a quick press
            self.rotated = False  # Reset rotation flag

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_pressing = False  # Reset pressing state on mouse release
            if self.press_timer.isActive() and not self.rotated:
                # Timer is still active and no rotation has happened, so it's a quick press
                self.press_timer.stop()
                self.managed_mode = not self.managed_mode  # Toggle managed mode
                self.update_heading_display()

    def mouseMoveEvent(self, event):
        if self.is_pressing and event.buttons() & Qt.LeftButton:
            center = self.rect().center()
            start_vector = self.knob_start_pos - center
            current_vector = event.pos() - center
            start_angle = (180 / 3.14159) * atan2(start_vector.y(), start_vector.x())
            current_angle = (180 / 3.14159) * atan2(current_vector.y(), current_vector.x())
            angle_diff = current_angle - start_angle
            if abs(angle_diff) > 180:  # Handle angle wrapping issues
                angle_diff = -((360 - abs(angle_diff)) * (1 if angle_diff < 0 else -1))
            self.knob_angle = (self.knob_angle + angle_diff) % 360
            # Ensure smooth updates to prevent large jumps
            self.total_rotation += angle_diff / 10  # One degree heading change for every ten degrees of knob rotation
            heading_change = int(self.total_rotation)
            if heading_change != 0:
                self.managed_mode = False  # Deactivate managed mode on rotation
                new_heading = (self.parent().heading_select + heading_change) % 360
                self.parent().update_heading(new_heading, self.managed_mode)  # Pass managed mode to update_heading
                self.total_rotation -= heading_change  # Only subtract the integer part of the rotation
            self.knob_start_pos = event.pos()  # Update for smooth continuous rotation
            self.update()
            self.update_heading_display()
            self.rotated = True  # Set rotation flag
            self.press_timer.stop()  # Cancel the press timer if the knob is moved

    def update_heading_display(self):
        self.parent().update_heading(self.parent().heading_select, self.managed_mode)  # Pass managed mode to update_heading

    def on_press_timeout(self):
        # This method is called if the press lasts longer than 50ms
        self.is_pressing = True

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        painter.setRenderHint(QPainter.Antialiasing)
        
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2
        
        painter.translate(center)
        painter.rotate(self.knob_angle)
        
        painter.setBrush(QBrush(QColor('#E2DCD0')))
        painter.setPen(Qt.NoPen)  # No outline
        for i in range(8):
            painter.drawEllipse(QPoint(radius - 6, 0), 6, 6)  # Move circles farther from center
            painter.rotate(45)

        # Larger central circle
        painter.setBrush(QBrush(QColor('#E2DCD0')))
        painter.drawEllipse(QPoint(0, 0), 18, 18)  # Slightly larger central circle
        
        # Blue triangle centered in the knob
        painter.setBrush(Qt.transparent)
        painter.setPen(QPen(QColor('#89B2FA'), 3))  # Thick blue outline
        triangle_side = radius
        triangle_height = int((3 ** 0.5) / 2 * triangle_side)
        triangle = QPolygon([
            QPoint(0, -triangle_height // 2 - 2),  # Move up more
            QPoint(triangle_side // 2, triangle_height // 2 - 2),  # Move up more
            QPoint(-triangle_side // 2, triangle_height // 2 - 2)  # Move up more
        ])
        painter.drawPolygon(triangle)
        painter.end()

class SpeedMachKnob(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.knob_angle = 0
        self.knob_start_pos = QPoint()
        self.total_rotation = 0
        self.is_pressing = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.knob_start_pos = event.pos()
            self.is_pressing = True

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_pressing = False

    def mouseMoveEvent(self, event):
        if self.is_pressing and event.buttons() & Qt.LeftButton:
            center = self.rect().center()
            start_vector = self.knob_start_pos - center
            current_vector = event.pos() - center
            start_angle = (180 / 3.14159) * atan2(start_vector.y(), start_vector.x())
            current_angle = (180 / 3.14159) * atan2(current_vector.y(), current_vector.x())
            angle_diff = current_angle - start_angle
            if abs(angle_diff) > 180:
                angle_diff = -((360 - abs(angle_diff)) * (1 if angle_diff < 0 else -1))
            self.knob_angle = (self.knob_angle + angle_diff) % 360
            self.total_rotation += angle_diff / 10
            speed_change = int(self.total_rotation)
            if speed_change != 0:
                new_speed = max(0, min(999, self.parent().speed_digits + speed_change))
                self.parent().update_speed_mach(new_speed)
                self.total_rotation -= speed_change
            self.knob_start_pos = event.pos()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2

        painter.translate(center)
        painter.rotate(self.knob_angle)

        # Draw the knob circle with fill color
        painter.setBrush(QBrush(QColor('#C7C1B6')))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(0, 0), radius, radius)

        # Draw white outlined circle on top
        painter.setBrush(Qt.transparent)
        painter.setPen(QPen(QColor('white'), 2))
        painter.drawEllipse(QPoint(0, 0), radius - 4, radius - 4)

        # Draw small tick marks for detents outside the white circle
        tick_length = 2  # Reduced length of the tick marks
        tick_color = QColor('white')
        tick_pen = QPen(tick_color, 2)
        painter.setPen(tick_pen)

        tick_radius = radius - 2  # Positioning closer to the white circle to avoid clipping

        for i in range(36):  # Keep 36 tick marks
            angle = i * (360 / 36)
            painter.save()
            painter.rotate(angle)
            painter.drawLine(QPoint(tick_radius - tick_length, 0), QPoint(tick_radius, 0))
            painter.restore()

        painter.end()