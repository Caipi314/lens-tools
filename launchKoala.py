import pyautogui as gui
import time
from datetime import datetime

gui.click(x=1, y=gui.size().height - 1)

gui.write('Koala')  # Types 'Hello, world!' with a slight delay between characters
gui.press('enter')

time.sleep(10)
gui.write('user')
gui.press('tab')
gui.write('user')
gui.press('enter')

time.sleep(5)
gui.press('enter')

gui.click(x=210, y=60)

time.sleep(1)
gui.screenshot().save(f'./shots/screen{datetime.now().strftime("%H_%M_%S")}.png')

