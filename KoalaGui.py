import pyautogui as gui
import time
from datetime import datetime


def launchKoala():
    gui.click(x=1, y=gui.size().height - 1)

    gui.write("Koala")  # Types 'Hello, world!' with a slight delay between characters
    gui.press("enter")

    time.sleep(10)
    gui.write("user")
    gui.press("tab")
    gui.write("user")
    gui.press("enter")

    time.sleep(5)
    gui.press("enter")

    gui.click(x=210, y=60)

    time.sleep(1)
    gui.screenshot().save(f'./shots/screen{datetime.now().strftime("%H_%M_%S")}.png')


def turnLive(on):
    x_init, y_init = gui.position()

    onColour = (192, 220, 243)
    x, y = 160, 63
    gui.moveTo(1, 1)  # prevent the hover color
    is_live = gui.pixelMatchesColor(x, y, onColour)
    if on and not is_live or not on and is_live:
        gui.click(x=x, y=y)
    gui.moveTo(x_init, y_init)


if __name__ == "__main__":
    launchKoala()
