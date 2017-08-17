import sys
sys.path.insert(0, "/home/yang/rlTORCS")  # /data/yang/code/rlTORCS

import gym
from gym.envs.registration import register
import py_torcs

register(
    id='rltorcs-v0',
    entry_point='py_torcs:TorcsEnv',
    kwargs={"subtype": "discrete_improved",
            "server": True,
            "auto_back": False,
            "game_config": "/home/yang/rlTORCS/game_config/huazhe.xml",
            "custom_reward": "reward_ben",
            "detailed_info": True}
)

# some naive code that could run
from gym.envs.classic_control import rendering
import numpy as np        
viewer = rendering.SimpleImageViewer()
img = np.zeros([550, 550, 3])

env = gym.make("rltorcs-v0")
obs = env.reset()
for i in range(10):
    print i
    #env.render()
    # replacing render
    viewer.imshow(obs)
    
    obs, reward, terminal, info=env.step(env.action_space.sample()) # take a random action
    if terminal:
        env.reset()


