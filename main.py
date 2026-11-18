# Runs ON the Raspberry Pi Pico (MicroPython).
# Save it to the Pico with the filename  main.py
#
# Wiring: one leg of each button goes to its GP pin, the other leg goes to GND.
#   N (up)    -> GP10 (physical pin 14)
#   S (down)  -> GP11 (physical pin 15)
#   W (left)  -> GP12 (physical pin 16)
#   E (right) -> GP13 (physical pin 17)
#   GND       -> physical pin 13 or 18

from machine import Pin
import time

PINS = {"N": 10, "S": 11, "W": 12, "E": 13}

# PULL_UP: the pin reads 1 normally and 0 while the button is pressed
buttons = {d: Pin(p, Pin.IN, Pin.PULL_UP) for d, p in PINS.items()}
was_pressed = {d: False for d in PINS}

while True:
    for direction, button in buttons.items():
        pressed = button.value() == 0
        # Send one letter per press, not continuously while held
        if pressed and not was_pressed[direction]:
            print(direction)      # goes to the PC over the USB cable
        was_pressed[direction] = pressed
    time.sleep_ms(20)             # also acts as a simple debounce