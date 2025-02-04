import sys
import math
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QPolygon, QFont, QLinearGradient, QTransform, QPainterPath
from PyQt5.QtCore import QRect, Qt, QRectF, QPoint, QTimer
from Input_Control import InputControl

class PrimaryFlightDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.pitch = 0
        self.roll = 0
        self.current_heading = 0
        self.hdg_trk_active = False
        self.speed = 0
        self.true_airspeed = 150  # True airspeed in knots
        self.alt_hold_active = False
        self.alt_hold_armed = False
        self.localizer_visible = False
        self.vertical_deviation_visible = False
        self.ap_status = ""  # Track AP status (AP1/AP2/OFF)
        self.ap1_active = False  # Add this attribute
        self.ap2_active = False
        self.appr_active = False
        self.appr_armed = False
        self.show_gs_loc_labels = False
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_horizon)
        self.timer.start(30)
        self.input_control = InputControl(self)
        self.setupFlightControlUnit()

    def setupFlightControlUnit(self):
        from Flight_Control_Unit import FlightControlUnit  # Import here to avoid circular dependency
        self.flight_control_unit = FlightControlUnit(self)
        self.flight_control_unit.show()

    def calculate_turn_rate(self):
        if self.true_airspeed == 0:
            return 0  # Prevent division by zero by returning 0 turn rate
        # Calculate load factor (g-force) during the turn
        load_factor = 1 / math.cos(math.radians(self.roll))
        # Adjust the turn rate calculation to include the load factor
        return (1091 * math.tan(math.radians(self.roll))) / (self.true_airspeed * load_factor)

    def update_ap_status(self, active, status):
        self.ap_status = status if active else ""
        self.update()

    def initUI(self):
        self.setWindowTitle('PFD')
        self.setGeometry(100, 100, 820, 820)
        self.setStyleSheet("background-color: black;")
        self.show()

    def keyPressEvent(self, event):
        self.input_control.handle_key_press(event)

    def keyReleaseEvent(self, event):
        self.input_control.handle_key_release(event)

    def toggle_alt_label(self, active):
        self.alt_hold_active = active
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        self.drawFlightModeAnnunciator(painter)
        self.drawHorizon(painter)
        painter.setClipping(False)
        if self.localizer_visible:
            self.drawLocalizerDeviation(painter)
        if self.vertical_deviation_visible:
            self.drawVerticalDeviationScale(painter)
        self.drawHeadingIndicator(painter)
        self.drawQNH(painter)  
        #self.drawAirspeedIndicator(painter)  # Call the method to draw airspeed indicator

    def closeEvent(self, event):
        self.flight_control_unit.close()
        event.accept()
    
    def toggle_gs_loc_labels(self, active):
        if active:
            # Ensure the labels are shown
            self.show_gs_loc_labels = True
        else:
            # Ensure the labels are hidden
            self.show_gs_loc_labels = False
        self.update()

    def drawAirspeedIndicator(self, painter):
        container_height = 460
        indicator_width = 78  # Increased width
        horizon_center_y = self.height() // 2
        sky_ground_right_x = self.rect().center().x() - 320  # Closer to the sky/ground
        container_x = sky_ground_right_x - 42  # Adjust positioning for closeness
        container_y = horizon_center_y - container_height // 2

        # Draw the gray rectangle for the airspeed indicator
        painter.setBrush(QColor("#57606E"))
        painter.setPen(QPen(QColor("#57606E"), 1))
        painter.drawRect(container_x, container_y, indicator_width, container_height)

        # Draw white lines on the right side, top, and bottom of the rectangle
        painter.setPen(QPen(Qt.white, 2))
        painter.drawLine(container_x + indicator_width, container_y, container_x + indicator_width + 20, container_y)  # Top extended
        painter.drawLine(container_x, container_y, container_x + indicator_width, container_y)  # Top
        painter.drawLine(container_x + indicator_width, container_y, container_x + indicator_width, container_y + container_height)  # Right side
        painter.drawLine(container_x, container_y + container_height, container_x + indicator_width, container_y + container_height)  # Bottom
        painter.drawLine(container_x + indicator_width, container_y + container_height, container_x + indicator_width + 20, container_y + container_height)  # Bottom extended

        # Draw the inverted yellow triangle pointing towards the rectangle, outside of it
        triangle_height = 15
        triangle_width = 20
        triangle_x = container_x + indicator_width + 20  # Move outside the rectangle
        triangle_y = container_y + container_height // 2 - triangle_height // 2
        points = [QPoint(triangle_x, triangle_y), QPoint(triangle_x - triangle_width, triangle_y + triangle_height // 2), QPoint(triangle_x, triangle_y + triangle_height)]
        painter.setBrush(QColor("yellow"))
        painter.setPen(QPen(QColor("yellow"), 2))
        painter.drawPolygon(QPolygon(points))

        # Draw tick marks and numbers for speeds, clipped to the airspeed container
        clip_path = QPainterPath()
        clip_path.addRect(container_x, container_y, indicator_width, container_height)
        painter.setClipPath(clip_path)
        tick_spacing = 60  # Spacing between tick marks
        total_ticks = 40 * tick_spacing  # speed with tick_spacing pixels per unit
        scroll_offset = int(self.speed * tick_spacing) % total_ticks
        painter.setPen(QPen(Qt.white, 3))
        painter.setFont(QFont("Arial", 14))  # Font size 14
        for i in range(0, total_ticks, tick_spacing):  # Major tick marks only
            y_pos = int(container_y + container_height - (i - scroll_offset + container_height // 2) % total_ticks)
            if container_y <= y_pos <= container_y + container_height:  # Only draw tick marks within the container
                painter.drawLine(container_x + indicator_width - 20, y_pos, container_x + indicator_width, y_pos)
                speed_value = (i // tick_spacing) * 10  # Speed in 10 increments
                number_text = f"{speed_value}"
                text_offset = len(number_text) * 3  # Adjust text offset for proper centering
                painter.drawText(int(container_x + 6), int(y_pos + 5), number_text)  # Speed numbers closer to tick marks
        painter.setClipping(False)  # Disable clipping

    def drawFlightModeAnnunciator(self, painter):
        container_width = 850
        container_height = 76
        horizon_center_x = self.width() // 2
        sky_ground_bottom_y = self.rect().center().y() - 324  # The bottom of the sky/ground container
        container_y = sky_ground_bottom_y - container_height  # Position at the top of the sky/ground container
        container_x = horizon_center_x - container_width // 2  # Centered with the sky/ground container

        # Calculate spacing and square width
        square_width = container_width // 5
        line_thickness = 2

        # Draw light gray lines to separate the squares
        painter.setPen(QPen(QColor("#717171"), line_thickness))
        for i in range(1, 5):
            line_x = container_x + i * square_width - line_thickness // 2
            painter.drawLine(line_x, container_y, line_x, container_y + container_height)

        # Draw status squares labels (e.g., SPEED, ALT, HDG) within each square
        labels = ["SPEED", "ALT", " ", " ", self.ap_status if self.ap_status else " "]
        for i in range(5):
            rect = QRect(container_x + i * square_width, container_y, square_width, container_height)
            painter.setFont(QFont("Helvetica", 12))  # Use a readable font for all labels

            if labels[i] == "ALT":
                if self.alt_hold_active:
                    painter.setPen(QPen(QColor("#67E159"), 2))  # Set ALT label to green if active
                elif self.alt_hold_armed:
                    painter.setPen(QPen(Qt.white, 2))  # White for armed
                else:
                    continue  # Skip drawing if ALT HOLD is not armed or active
                painter.drawText(rect, Qt.AlignTop | Qt.AlignHCenter, labels[i])

            elif labels[i] == " " and self.hdg_trk_active and i == 2:
                painter.setPen(QPen(QColor("#67E159"), 2))  # Set HDG label to green if active
                painter.drawText(rect, Qt.AlignTop | Qt.AlignHCenter, "HDG")

            elif i == 4:  # Display AP status and potentially LOC and GS in the last column
                painter.setPen(QPen(Qt.white, 2))  # White color for text
                painter.drawText(rect, Qt.AlignTop | Qt.AlignHCenter, self.ap_status if self.ap_status else " ")
                if self.show_gs_loc_labels:
                    loc_color = QColor("#5EFF33") if self.appr_active and (self.ap1_active or self.ap2_active) else Qt.white
                    gs_color = QColor("#5EFF33") if self.appr_active and (self.ap1_active or self.ap2_active) else Qt.white
                    loc_rect = rect.adjusted(0, 20, 0, 0)
                    gs_rect = rect.adjusted(0, 40, 0, 0)
                    painter.setPen(QPen(loc_color, 2))
                    painter.drawText(loc_rect, Qt.AlignTop | Qt.AlignHCenter, "LOC")
                    painter.setPen(QPen(gs_color, 2))
                    painter.drawText(gs_rect, Qt.AlignTop | Qt.AlignHCenter, "GS")
            else:
                painter.setPen(QPen(Qt.white, 2))  # White color for text
                painter.drawText(rect, Qt.AlignTop | Qt.AlignHCenter, labels[i])  # Centered text within the square

    def drawQNH(self, painter):
        container_width = 400
        horizon_center_x = self.width() // 2
        sky_ground_bottom_y = self.rect().center().y() + 194  # The bottom of the sky/ground container
        container_y = sky_ground_bottom_y + 100  # Fixed distance from the sky/ground container
        container_x = horizon_center_x - container_width // 2 + 60
        qnh_rect_width = 100
        qnh_rect_height = 30
        qnh_rect_x = container_x + container_width + 10  # Positioned to the right of the heading indicator
        qnh_rect_y = container_y
        painter.setBrush(QColor(1, 1, 1))  # Darker background
        painter.setPen(Qt.NoPen)  # No outline
        painter.drawRect(qnh_rect_x, qnh_rect_y, qnh_rect_width, qnh_rect_height)

        # Draw the QNH label in white and the digits in cyan
        painter.setPen(QPen(Qt.white, 2))
        painter.setFont(QFont("Arial", 14))
        painter.drawText(qnh_rect_x + 5, qnh_rect_y + 20, "QNH")

        painter.setPen(QPen(Qt.cyan, 2))
        painter.drawText(qnh_rect_x + 64, qnh_rect_y + 20, "1013")  # Adjusted for centering digits within the rectangle

    def drawVerticalDeviationScale(self, painter):
        container_width = 70
        container_height = 380
        horizon_center_x = self.width() // 2
        # Fixed horizontal distance from the sky/ground container
        sky_ground_center_x = self.rect().center().x()
        container_x = sky_ground_center_x + 218  # 218 pixels to the right of the sky/ground container
        container_y = self.height() // 2 - container_height // 2  # Centered vertically

        # Draw container rectangle (for visual reference)
        painter.setBrush(Qt.transparent)
        painter.setPen(QPen(QColor("transparent"), 1, Qt.DashLine))
        painter.drawRect(container_x, container_y, container_width, container_height)

        # Define positions with spacing within the container
        circle_radius = 6
        rectangle_width = 38
        rectangle_height = 4
        element_spacing = 70  # Spacing between the elements
        rect_center_y = container_y + container_height // 2
        top_circle_center1 = QPoint(container_x + container_width // 2, rect_center_y - rectangle_height // 2 - element_spacing - 2 * circle_radius)
        top_circle_center2 = QPoint(top_circle_center1.x(), top_circle_center1.y() - element_spacing - 2 * circle_radius)
        bottom_circle_center1 = QPoint(container_x + container_width // 2, rect_center_y + rectangle_height // 2 + element_spacing + 2 * circle_radius)
        bottom_circle_center2 = QPoint(bottom_circle_center1.x(), bottom_circle_center1.y() + element_spacing + 2 * circle_radius)

        # Draw top circles
        painter.setBrush(Qt.transparent)
        painter.setPen(QPen(QColor("white"), 2))
        painter.drawEllipse(top_circle_center1, circle_radius, circle_radius)
        painter.drawEllipse(top_circle_center2, circle_radius, circle_radius)

        # Draw bottom circles
        painter.drawEllipse(bottom_circle_center1, circle_radius, circle_radius)
        painter.drawEllipse(bottom_circle_center2, circle_radius, circle_radius)

        # Draw thinner yellow horizontal rectangle at the center between circles
        rect_top_left = QPoint(container_x + container_width // 2 - rectangle_width // 2, rect_center_y - rectangle_height // 2)
        painter.setBrush(QColor("yellow"))
        painter.setPen(QPen(QColor("yellow"), 2))
        painter.drawRect(rect_top_left.x(), rect_top_left.y(), rectangle_width, rectangle_height)

    def drawLocalizerDeviation(self, painter):
        if not self.localizer_visible:
            return
        
        container_width = 380
        container_height = 70
        horizon_center_x = self.width() // 2
        # Fixed vertical distance from the sky/ground container
        sky_ground_bottom_y = self.rect().center().y() + 232  # The bottom of the sky/ground container
        container_y = sky_ground_bottom_y + 20  # 20 pixels below the sky/ground container
        container_x = horizon_center_x - container_width // 2

        # Draw container rectangle (for visual reference)
        painter.setBrush(Qt.transparent)
        painter.setPen(QPen(QColor("transparent"), 1, Qt.DashLine))
        painter.drawRect(container_x, container_y, container_width, container_height)

        # Define positions with spacing within the container
        circle_radius = 6
        rectangle_width = 4
        rectangle_height = 38 
        element_spacing = 70  # Spacing between the elements

        rect_center_x = container_x + container_width // 2
        left_circle_center1 = QPoint(rect_center_x - rectangle_width // 2 - element_spacing - 2 * circle_radius, container_y + container_height // 2)
        left_circle_center2 = QPoint(left_circle_center1.x() - element_spacing - 2 * circle_radius, left_circle_center1.y())
        right_circle_center1 = QPoint(rect_center_x + rectangle_width // 2 + element_spacing + 2 * circle_radius, container_y + container_height // 2)
        right_circle_center2 = QPoint(right_circle_center1.x() + element_spacing + 2 * circle_radius, container_y + container_height // 2)

        # Draw left circles
        painter.setBrush(Qt.transparent)
        painter.setPen(QPen(QColor("white"), 2))
        painter.drawEllipse(left_circle_center1, circle_radius, circle_radius)
        painter.drawEllipse(left_circle_center2, circle_radius, circle_radius)

        # Draw right circles
        painter.drawEllipse(right_circle_center1, circle_radius, circle_radius)
        painter.drawEllipse(right_circle_center2, circle_radius, circle_radius)

        # Draw thinner yellow vertical rectangle at the center between circles
        rect_top_left = QPoint(rect_center_x - rectangle_width // 2, container_y + container_height // 2 - rectangle_height // 2)
        painter.setBrush(QColor("yellow"))
        painter.setPen(QPen(QColor("yellow"), 2))
        painter.drawRect(rect_top_left.x(), rect_top_left.y(), rectangle_width, rectangle_height)

    def drawHeadingIndicator(self, painter):
        container_width = 410
        indicator_height = 50
        horizon_center_x = self.width() // 2
        sky_ground_bottom_y = self.rect().center().y() + 240  # The bottom of the sky/ground container
        container_y = sky_ground_bottom_y + 100  # 100 pixels below the sky/ground container
        container_x = horizon_center_x - container_width // 2

        # Draw the gray rectangle for the heading indicator/compass scale
        painter.setBrush(QColor("#57606E"))
        painter.setPen(QPen(QColor("#57606E"), 1))
        painter.drawRect(container_x, container_y, container_width, indicator_height)

        # Draw white line on top of the tick marks
        painter.setPen(QPen(Qt.white, 3))
        painter.drawLine(container_x, container_y, container_x + container_width, container_y)

        # Draw lines on the left and right side of the container
        painter.setPen(QPen(Qt.white, 1))
        painter.drawLine(container_x, container_y, container_x, container_y + indicator_height)
        painter.drawLine(container_x + container_width, container_y, container_x + container_width, container_y + indicator_height)

        # Draw the yellow rectangle to indicate the current heading in the middle
        heading_rect_width = 4
        heading_rect_height = 30
        heading_rect_x = container_x + container_width // 2 - heading_rect_width // 2
        heading_rect_y = container_y - heading_rect_height // 2
        painter.setBrush(QColor("yellow"))
        painter.setPen(QPen(QColor("yellow"), 2))
        painter.drawRect(heading_rect_x, heading_rect_y, heading_rect_width, heading_rect_height)

        # Draw tick marks and numbers for degrees, clipped to the heading container
        clip_path = QPainterPath()
        clip_path.addRect(container_x, container_y, container_width, indicator_height)
        painter.setClipPath(clip_path)
        tick_spacing = 76  # Increased spacing between tick marks
        total_ticks = 360 * tick_spacing  # 360 degrees with tick_spacing pixels per degree
        scroll_offset = int(self.current_heading * tick_spacing) % total_ticks
        painter.setPen(QPen(Qt.white, 3))
        painter.setFont(QFont("Arial", 14))  # Font size 14
        for i in range(0, total_ticks, tick_spacing // 2):  # Including small tick marks
            x_pos = int(container_x + (i - scroll_offset + container_width // 2) % total_ticks)
            if container_x <= x_pos <= container_x + container_width:  # Only draw tick marks within the container
                if i % tick_spacing == 0:  # Major tick marks
                    painter.drawLine(x_pos, container_y, x_pos, container_y + 20)
                    # Calculate the heading value
                    heading_value = (i // tick_spacing) % 360  # Continuously show 0 to 359
                    number_text = f"{heading_value}"
                    # Center text based on its length
                    text_offset = len(number_text) * 5  # Adjust text offset for proper centering
                    painter.drawText(int(x_pos - text_offset), int(container_y + 47), number_text)
                else:  # Small tick marks
                    painter.setPen(QPen(Qt.white, 2))
                    painter.drawLine(x_pos, container_y, x_pos, container_y + 10)
        painter.setClipping(False)  # Disable clipping

        if self.hdg_trk_active:
            # Draw the heading bug on the right side of the heading indicator's container
            bug_rect_width = 50
            bug_rect_height = 30
            bug_rect_x = container_x + container_width - 30
            bug_rect_y = container_y + (indicator_height - bug_rect_height) // 2 + 5
            painter.setBrush(QColor(30, 30, 30))  # Darker background
            painter.setPen(QPen(Qt.white, 1))  # Thin white outline
            painter.drawRect(bug_rect_x, bug_rect_y, bug_rect_width, bug_rect_height)
            # Draw the selected heading in lighter purple digits
            selected_heading_str = str(self.selected_heading).zfill(3)  # Format heading to three digits
            painter.setPen(QPen(QColor("#D49BD9"), 2))  # Light purple color
            painter.setFont(QFont("Arial", 16))
            text_rect = QRect(bug_rect_x, bug_rect_y, bug_rect_width, bug_rect_height)
            painter.drawText(text_rect, Qt.AlignCenter, selected_heading_str)  # Center justified inside the rectangle

    def drawHorizon(self, painter):
        rect = self.rect()
        center = rect.center()

        # Define the radius of the circle
        circle_radius = 250

        # Create the clipping path for the circle container
        circle_path = QPainterPath()
        circle_path.addEllipse(center, circle_radius, circle_radius)
        painter.setClipPath(circle_path)

        # Draw the horizon
        self.draw_horizon(painter, center, circle_radius)

        # Disable clipping path to draw the bank angle arc and tick marks
        painter.setClipping(False)

        self.draw_bank_angle_arc(painter, center.x(), center.y())
        painter.setClipping(True)  # Re-enable clipping path

        # Draw black rectangles on both sides of the circle
        rect_width = 100  # Width of the rectangles
        rect_height = 2 * circle_radius  # Height of the rectangles

        left_rect = QRectF(center.x() - circle_radius - 68, center.y() - circle_radius, rect_width, rect_height)
        right_rect = QRectF(center.x() + circle_radius - 32, center.y() - circle_radius, rect_width, rect_height)

        painter.setBrush(QColor("black"))
        painter.setPen(Qt.NoPen)
        painter.drawRect(left_rect)
        painter.drawRect(right_rect)

    def draw_horizon(self, painter, center, circle_radius):
        width = circle_radius * 2
        height = circle_radius * 2
        center_x = center.x()
        center_y = center.y()

        # Calculate vertical offset based on pitch angle and invert it
        pitch_offset = int(-self.pitch * height / 50)  # Adjust the divisor for sensitivity

        # Define rectangles for the sky and ground with pitch offset
        sky_points = [
            QPoint(center_x - width, center_y - height + pitch_offset),
            QPoint(center_x + width, center_y - height + pitch_offset),
            QPoint(center_x + width, center_y + pitch_offset),
            QPoint(center_x - width, center_y + pitch_offset)
        ]

        ground_points = [
            QPoint(center_x - width, center_y + pitch_offset),
            QPoint(center_x + width, center_y + pitch_offset),
            QPoint(center_x + width, center_y + height + pitch_offset),
            QPoint(center_x - width, center_y + height + pitch_offset)
        ]

        # Rotate points
        roll_radians = math.radians(self.roll)
        def rotate_point(point, angle, cx, cy):
            s = math.sin(angle)
            c = math.cos(angle)
            x = point.x() - cx
            y = point.y() - cy
            new_x = x * c - y * s
            new_y = x * s + y * c
            return QPoint(int(new_x + cx), int(new_y + cy))

        rotated_sky_points = [rotate_point(point, roll_radians, center_x, center_y) for point in sky_points]
        rotated_ground_points = [rotate_point(point, roll_radians, center_x, center_y) for point in ground_points]

        # Create gradient for the sky
        sky_gradient = QLinearGradient(0, center_y - height + pitch_offset, 0, center_y + pitch_offset)
        sky_gradient.setColorAt(0, QColor("#3267EC"))  # Top color
        sky_gradient.setColorAt(0.5, QColor("#417EF0"))  # Bottom color
        sky_gradient.setColorAt(1, QColor("#5EB8E1"))  # Bottom color

        # Create gradient for the ground
        ground_gradient = QLinearGradient(0, center_y + pitch_offset, 0, center_y + height + pitch_offset)
        ground_gradient.setColorAt(0, QColor("#904C1C"))  # Top color
        ground_gradient.setColorAt(1, QColor("#654321"))  # Bottom color

        # Draw the sky with gradient
        painter.setBrush(sky_gradient)
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygon(rotated_sky_points))

        # Draw the ground with gradient
        painter.setBrush(ground_gradient)
        painter.drawPolygon(QPolygon(rotated_ground_points))

        # Draw the separator line between sky and ground
        painter.setPen(QPen(Qt.white, 2))
        painter.drawLine(rotated_sky_points[2], rotated_sky_points[3])

         # Draw scrolling major tick marks on the separator line, pointing towards the ground
        tick_length = 12  # Length of the tick marks
        tick_spacing = 76  # Match spacing with the heading indicator
        total_ticks = 360 * tick_spacing  # Ensure total ticks cover the same range
        scroll_offset = int(self.current_heading * tick_spacing) % total_ticks

        for i in range(0, total_ticks, tick_spacing):  # Only major tick marks
            x_pos = int(center_x + (i - scroll_offset + circle_radius) % total_ticks - circle_radius)
            if center_x - circle_radius <= x_pos <= center_x + circle_radius:  # Only draw tick marks within the container
                tick_start = QPoint(x_pos, center_y + pitch_offset)
                tick_end = QPoint(tick_start.x(), tick_start.y() + tick_length)
                # Apply roll rotation to the tick marks with the horizon line
                tick_start_rotated = rotate_point(tick_start, roll_radians, center_x, center_y)
                tick_end_rotated = rotate_point(tick_end, roll_radians, center_x, center_y)
                painter.drawLine(tick_start_rotated, tick_end_rotated)


        # Draw pitch lines and pitch ladder
        self.draw_pitch_lines_and_ladder(painter, center_x, center_y)

        # Define the L-shaped plane outline points
        left_L = [
            QPoint(center_x - 208, center_y - 8), QPoint(center_x - 124, center_y - 8),
            QPoint(center_x - 124, center_y - 8), QPoint(center_x - 114, center_y - 8),
            QPoint(center_x - 114, center_y + 34), QPoint(center_x - 130, center_y + 34),
            QPoint(center_x - 130, center_y + 8), QPoint(center_x - 208, center_y + 8)
        ]

        right_L = [
            QPoint(center_x + 208, center_y - 8), QPoint(center_x + 124, center_y - 8),
            QPoint(center_x + 124, center_y - 8), QPoint(center_x + 114, center_y - 8),
            QPoint(center_x + 114, center_y + 34), QPoint(center_x + 130, center_y + 34),
            QPoint(center_x + 130, center_y + 8), QPoint(center_x + 208, center_y + 8)
        ]

        # Draw plane outline
        painter.setPen(QPen(QColor("yellow"), 4))
        painter.setBrush(QColor("black"))
        painter.drawPolygon(QPolygon(left_L))
        painter.drawPolygon(QPolygon(right_L))

        # Draw smaller square at the center
        square_size = 16
        painter.drawRect(center_x - square_size // 2, center_y - square_size // 2, square_size, square_size)

    def draw_pitch_lines_and_ladder(self, painter, center_x, center_y):
        pitch_angles = [-30, -27.5, -25, -22.5, -20, -17.5, -15, -12.5, -10, -7.5, -5, -2.5, 2.5, 5, 7.5, 10, 12.5, 15, 17.5, 20, 22.5, 25, 27.5, 30]
        ellipse_radius = 250
        fade_start_distance = ellipse_radius * 0.56  # Start fading at 56% of the radius

        # Define the top and bottom limits for the pitch ladder
        top_limit = center_y - 186  # Adjust this value as needed
        bottom_limit = center_y + 186  # Adjust this value as needed

        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.roll)
        painter.translate(-center_x, -center_y)

        for i, pitch in enumerate(pitch_angles):
            y = int(center_y - (pitch + self.pitch) * 10)  # Controls vertical spacing between lines

            # Skip drawing lines outside the top and bottom limits
            if y < top_limit or y > bottom_limit:
                continue

            distance_from_center = abs(y - center_y)
            if distance_from_center < fade_start_distance:
                fade_factor = 1
            else:
                fade_factor = max(0, 1 - (distance_from_center - fade_start_distance) / (ellipse_radius - fade_start_distance))

            # Adjust fade factor based on proximity to the top and bottom limits
            if y < top_limit + 20:
                fade_factor *= (y - top_limit) / 20
            elif y > bottom_limit - 20:
                fade_factor *= (bottom_limit - y) / 20

            line_length = int(64 * fade_factor)  # Pitch line length
            opacity = int(255 * fade_factor)

            painter.setPen(QPen(QColor(255, 255, 255, opacity), 3))
            font = QFont()
            font.setPointSize(18)  # Increase font size
            painter.setFont(font)

            if pitch % 10 == 0:  # Long lines with labels
                painter.drawLine(center_x - line_length, y, center_x + line_length, y)
                painter.drawText(center_x - 118, y + 10, f"{abs(pitch):>3}")  # Move numbers closer
                painter.drawText(center_x + 78, y + 10, f"{abs(pitch):<3}")  # Move numbers closer
            elif pitch % 5 == 0:  # Medium lines
                painter.drawLine(center_x - int(line_length // 2), y, center_x + int(line_length // 2), y)
            else:  # Short lines
                painter.drawLine(center_x - line_length // 4, y, center_x + line_length // 4, y)

        painter.restore()

    def draw_bank_angle_arc(self, painter, center_x, center_y):
        # Define the radius of the circle
        circle_radius = 250

        # Create the clipping path for the circle
        circle_path = QPainterPath()
        circle_path.addEllipse(center_x - circle_radius, center_y - circle_radius, 2 * circle_radius, 2 * circle_radius)

        # Draw the arc at the top of the container circle
        arc_rect = QRectF(center_x - 250, center_y - 250, 500, 500)
        painter.setPen(QPen(QColor("white"), 3))
        painter.drawArc(arc_rect, 60 * 16, 60 * 16)  # Draw arc from -30 to +30 degrees

        # Draw tick marks for bank angles (rotated rectangles)
        for angle in range(-30, 31, 10):
            tick_length = 18  # Adjust rectangles' size
            tick_angle = math.radians(angle - 90)  # Adjust angle to align with the top arc
            x1 = center_x + 268 * math.cos(tick_angle)
            y1 = center_y + 268 * math.sin(tick_angle)
            x2 = center_x + (268 - tick_length) * math.cos(tick_angle)
            y2 = center_y + (268 - tick_length) * math.sin(tick_angle)

            if angle == 0:
                # Define points for the inverted yellow triangle
                triangle_points = [
                    QPoint(int((x1 + x2) / 2), int(y2)),
                    QPoint(int((x1 + x2) / 2 - 16), int(y1 - 4)),
                    QPoint(int((x1 + x2) / 2 + 16), int(y1 - 4))
                ]
                painter.setPen(QPen(QColor("yellow"), 3))
                painter.setBrush(Qt.NoBrush)
                painter.drawPolygon(QPolygon(triangle_points))
            else:
                # Define the rectangle for the tick mark
                rect_width = 12  # Width of the rectangle
                painter.setPen(QPen(QColor("white"), 3))
                if angle == -30 or angle == 30:
                    rect_height = abs(y1 - y2) + 8  # Increase height by 10 units
                    y1_adjusted = y1 - 5  # Adjust y-coordinate to keep the tick mark within the arc
                    y2_adjusted = y2 - 5  # Adjust y-coordinate to keep the tick mark within the arc
                else:
                    rect_height = abs(y1 - y2)  # Height of the rectangle
                    y1_adjusted = y1
                    y2_adjusted = y2
                rect_center_x = (x1 + x2) / 2
                rect_center_y = (y1_adjusted + y2_adjusted) / 2

                # Create the rectangle centered on the arc
                rect = QRectF(rect_center_x - rect_width / 2, rect_center_y - rect_height / 2, rect_width, rect_height)

                # Create a QTransform object to apply rotation
                transform = QTransform()
                transform.translate(rect_center_x, rect_center_y)
                transform.rotate(angle)
                transform.translate(-rect_center_x, -rect_center_y)

                # Apply the transformation and draw the rectangle with no fill
                painter.setTransform(transform)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(rect)
                painter.resetTransform()  # Reset transformation for the next tick mark

        # Apply the clipping path for the lines
        painter.setClipPath(circle_path)

        # Draw the moving trapezoid and triangle as a single unit
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.roll)
        painter.translate(-center_x, -center_y)

        # Define points for the inverted trapezoid at the top (Slip)
        trapezoid_points = [
            QPoint(center_x - 22, center_y - circle_radius + 38),
            QPoint(center_x + 22, center_y - circle_radius + 38),
            QPoint(center_x + 30, center_y - circle_radius + 50),
            QPoint(center_x - 30, center_y - circle_radius + 50)
        ]

        # Define points for the triangle at the top (Sky Pointer)
        triangle_points = [
            QPoint(center_x, center_y - circle_radius + 6),
            QPoint(center_x - 18, center_y - circle_radius + 32),
            QPoint(center_x + 18, center_y - circle_radius + 32)
        ]

        # Draw the trapezoid and triangle with yellow outline and no fill
        painter.setPen(QPen(QColor("yellow"), 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolygon(QPolygon(trapezoid_points))
        painter.drawPolygon(QPolygon(triangle_points))

        # Draw the horizontal yellow line
        line_y = center_y - 188
        painter.setPen(QPen(QColor("yellow"), 3)) 
        painter.drawLine(center_x - 200, line_y, center_x + 200, line_y)

        # Draw the horizontal white line
        white_line_y = center_y + 188
        painter.setPen(QPen(QColor("white"), 3))
        painter.drawLine(center_x - 176, white_line_y, center_x + 176, white_line_y)

        painter.restore()

    def update_horizon(self):
        if self.roll != 0:
            # Calculate turn rate based on bank angle (roll) and true airspeed
            turn_rate = self.calculate_turn_rate()
            # Update heading based on the turn rate
            self.current_heading = (self.current_heading - turn_rate * 0.01) % 360  # Adjust 0.01 based on simulation speed multiplier
        self.update()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    horizon = PrimaryFlightDisplay()
    app.lastWindowClosed.connect(app.quit)
    sys.exit(app.exec_())