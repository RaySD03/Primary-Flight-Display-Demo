from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, Qt, QObject, QParallelAnimationGroup

class InputControl(QObject):
    def __init__(self, primary_flight_display):
        super().__init__()
        self.primary_flight_display = primary_flight_display
        self._pitch = 0
        self._roll = 0

        self.pitch_animation = QPropertyAnimation(self, b"pitch")
        self.roll_animation = QPropertyAnimation(self, b"roll")

        self.animation_group = QParallelAnimationGroup()
        self.animation_group.addAnimation(self.pitch_animation)
        self.animation_group.addAnimation(self.roll_animation)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_angles)
        self.timer.start(50)  # Update every 50 milliseconds for smoother control

        self.keys_pressed = set()

    @pyqtProperty(float)
    def pitch(self):
        return self._pitch

    @pitch.setter
    def pitch(self, value):
        self._pitch = value
        self.primary_flight_display.pitch = value
        self.primary_flight_display.update()

    @pyqtProperty(float)
    def roll(self):
        return self._roll

    @roll.setter
    def roll(self, value):
        # Add tolerance check to round down to 0 if close to 0
        if abs(value) < 0.18:
            value = 0
        self._roll = value
        self.primary_flight_display.roll = value
        self.primary_flight_display.update()

    def set_pitch(self, pitch, duration=100):
        if self.pitch != pitch:  # Only start animation if the value has changed
            self.pitch_animation.stop()  # Stop ongoing animations
            self.pitch_animation.setStartValue(self.pitch)  # Set the start value
            self.pitch_animation.setDuration(duration)
            self.pitch_animation.setEndValue(pitch)
            self.pitch_animation.start()

    def set_roll(self, roll, duration=100):
        # Limit the roll angle (-30 to 30 degrees on arc)
        if roll < -30:
            roll = -30
        elif roll > 30:
            roll = 30
        if self.roll != roll:  # Only start animation if the value has changed
            self.roll_animation.stop()  # Stop ongoing animations
            self.roll_animation.setStartValue(self.roll)  # Set the start value
            self.roll_animation.setDuration(duration)
            self.roll_animation.setEndValue(roll)
            self.roll_animation.start()

    def update_angles(self):
        increment = 0.5  # Set the increment value for precise control
        duration = 100  # Shorter duration for smoother control

        if Qt.Key_Up in self.keys_pressed:
            self.set_pitch(self.pitch + increment, duration)
        if Qt.Key_Down in self.keys_pressed:
            self.set_pitch(self.pitch - increment, duration)
        if Qt.Key_Left in self.keys_pressed:
            self.set_roll(self.roll + increment, duration)  # Invert the direction for left arrow
        if Qt.Key_Right in self.keys_pressed:
            self.set_roll(self.roll - increment, duration)  # Invert the direction for right arrow

    def handle_key_press(self, event):
        self.keys_pressed.add(event.key())
        self.update_angles()  # Update angles immediately on key press

    def handle_key_release(self, event):
        self.keys_pressed.discard(event.key())

