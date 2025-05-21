from KoalaController import KoalaController
import time
import matplotlib.pyplot as plt
import numpy as np

def guessTop():
	# x = 52222
	# y = 52500
	x = 55735
	y = 52759
	host.move_to(x, y)

def display2dArray(array):
	print(np.min(array), np.max(array))
	fig, ax = plt.subplots()
	im = ax.imshow(array, cmap="jet")  # Choose any colormap

	# Add a color bar to show the mapping of values to colors
	cbar = plt.colorbar(im)
	cbar.set_label("Color Intensity")
	plt.tight_layout()
	plt.savefig('./datas/pic.png')

try:
	host = KoalaController()
	host.setup()
	# guessTop()

	start = time.time()
	host.find_focus(guessHeight_mm = 10, topDown = False)
	end = time.time()


	print(f"Execution time: {end - start:.3f} seconds")
	# display2dArray(phase)





finally:
	host.logout()

#TODO: max height safety