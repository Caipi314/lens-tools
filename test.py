import json
import matplotlib.pyplot as plt
import numpy as np
import time

with open("./stitches/2025-06-03T174101/info.json", "r") as f:
    loaded_data = json.load(f)
    folder = loaded_data["folderPath"]
    stitch = np.load(folder + "/profile.npy")
    print(stitch.shape)
    print(stitch)
    plt.figure()
    plt.plot(stitch)

    # plt.imshow(stitch, cmap="jet")
    plt.show()
    # plt.imsave(stitch, folder + "/stitch.png")
