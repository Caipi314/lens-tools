import matplotlib.pyplot as plt
import numpy as np
import time

plt.ion()  # Turn on interactive mode
fig, ax = plt.subplots()
x = np.linspace(0, 10, 100)
y = np.sin(x)
(line,) = ax.plot(x, y)

for i in range(100):
    y = np.sin(x + i * 0.1)
    line.set_ydata(y)
    fig.canvas.draw()
    fig.canvas.flush_events()
    time.sleep(0.1)

plt.ioff()  # Turn off interactive mode
plt.show()
