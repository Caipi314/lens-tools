from KoalaController import KoalaController
import matplotlib.pyplot as plt
import timeit
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

	execution_time = timeit.timeit(lambda: host.find_focus(guessHeight_mm = 2, topDown = True), number=1)
	# execution_time = timeit.timeit(lambda: host.getContrast(avg=3), number=1)
	print(f"Execution time: {execution_time:.6f} seconds")

	# display2dArray(phase)





finally:
	host.logout()

#TODO: max height safety