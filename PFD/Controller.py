from PyQt5.QtCore import QTimer, QObject

class Controller(QObject):
    def __init__(self, flight_control_unit, input_control):
        super().__init__()
        self.flight_control_unit = flight_control_unit
        self.input_control = input_control
        self.hdg_trk_active = False
        self.heading_printed = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_control)
        self.timer.start(100)  # Check every 100 milliseconds

    def update_control(self):
        hdg_trk_active = self.flight_control_unit.hdg_trk_active
        current_heading = self.flight_control_unit.current_heading
        desired_heading = self.flight_control_unit.heading_select

        if hdg_trk_active:
            if not self.heading_printed:
                self.heading_printed = True

            heading_diff = (desired_heading - current_heading + 360) % 360
            if heading_diff > 180:
                heading_diff -= 360

            roll_intensity = self.calculate_roll_intensity(heading_diff)
            self.input_control.set_roll(self.apply_resistance(self.input_control.roll, roll_intensity))
        else:
            self.heading_printed = False

    def calculate_roll_intensity(self, heading_diff):
        max_roll = 29  # Maximum roll angle in degrees
        degree_change_per_second = 3  # Aim for 3 degrees change per second
        if abs(heading_diff) < 5:  # Final degrees should be quick but smooth
            roll_sensitivity = 0.2  # High sensitivity for small final adjustments
        elif abs(heading_diff) < 15:
            roll_sensitivity = 0.5  # Higher sensitivity for remaining degrees
        else:
            roll_sensitivity = 1.0  # Normal sensitivity for larger changes

        optimal_roll = min(max(heading_diff / roll_sensitivity, -max_roll), max_roll)  # Ensure roll is within [-29, 29] degrees
        return -optimal_roll  # Invert roll direction

    def apply_resistance(self, current_roll, target_roll_intensity):
        roll_change_rate = 0.5  # Gradual roll change rate
        if abs(current_roll - target_roll_intensity) < roll_change_rate:
            return target_roll_intensity  # Set directly if within change rate
        if current_roll < target_roll_intensity:
            current_roll += roll_change_rate
        elif current_roll > target_roll_intensity:
            current_roll -= roll_change_rate
        return current_roll
