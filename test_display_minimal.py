from gym.envs.classic_control import rendering
import numpy as np
            
viewer = rendering.SimpleImageViewer()
img = np.zeros([550, 550, 3])
viewer.imshow(img)

