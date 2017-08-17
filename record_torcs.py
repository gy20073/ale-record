#!/usr/bin/env python
import time
import os

import click
import pygame
import pygame.locals as pl

from demonstration import Demonstration

# added by Yang
import gym
from gym.envs.registration import register
import sys
import numpy as np
from scipy.misc import imresize
from time import sleep
import time

# manually switch the order of left and right
keys = [pl.K_SPACE, pl.K_UP, pl.K_LEFT, pl.K_RIGHT, pl.K_DOWN]

# really up is right, right key is left, left key is backup,
mapping = {
    # the original 1st=acceleration==up==4bit == real 2bit
    # 2nd = break == down == 1bit == 5bit
    # (3rd=-1) == left == l == 2bit == 4bit
    # (3rd == 1) == right == r == 3bit == 3bit
    # dlruf
    0b00110: 0,
    0b00010: 1,
    0b01010: 2,
    0b00100: 3,
    0b00000: 4,
    0b01000: 5,
    0b10100: 6,
    0b10000: 7,
    0b11000: 8
}
mapping2 = ["Up Left", "Up", "Up Right", "Left", "NoOp", "Right", "Break Left", "Break", "Break Right"]

def keystates_to_ale_action(keystates):
    keystates = dict(keystates)
    if keystates[pl.K_UP] and keystates[pl.K_DOWN]:
        keystates[pl.K_UP] = False
        keystates[pl.K_DOWN] = False
    if keystates[pl.K_LEFT] and keystates[pl.K_RIGHT]:
        keystates[pl.K_LEFT] = False
        keystates[pl.K_RIGHT] = False
    bitvec = sum(2 ** i if keystates[key] else 0 for i, key in enumerate(keys))
    assert bitvec in mapping
    print mapping2[mapping[bitvec]]
    return mapping[bitvec]


def update_keystates(keystates):
    events = pygame.event.get()
    #print events
    for event in events:
        if hasattr(event, 'key') and event.key == pl.K_ESCAPE:
            exit(0)
        if hasattr(event, 'key') and event.key in keys:
            if event.type == pygame.KEYDOWN:
                keystates[event.key] = True
            elif event.type == pygame.KEYUP:
                keystates[event.key] = False

@click.group()
def cli():
    pass

@cli.command(name='new')
@click.argument('rom', type=click.Path(exists=True))
@click.argument('output', type=click.Path())
@click.argument('game_config', type=click.Path(exists=True))
@click.option('--frames', default=60 * 60 * 30, help="Maximum number of frames")
@click.option('--episodes', default=0, help="Maximum number of episodes (game overs)")
@click.option('--snapshot_interval', default=1800, help="Interval (in timesteps) to snapshot emulator state")
def record_new(rom, output, game_config, frames, episodes, snapshot_interval):
    pygame.init()

    sys.path.insert(0, rom)  # /data/yang/code/rlTORCS
    register(
        id='rltorcs-v0',
        entry_point='py_torcs:TorcsEnv',
        kwargs={"subtype": "discrete_improved",
                "server": True,
                "auto_back": False,
                "game_config": game_config,
                "custom_reward": "reward_ben",
                "detailed_info": True}
    )
    env = gym.make("rltorcs-v0")

    demo = Demonstration(rom="torcs", action_set=np.array([0,1,2,3,4,5,6,7,8]))

    last_obs = env.reset()
    record(env, demo, output, frames, episodes, snapshot_interval, last_obs)

def record(env, demo, output, num_frames, num_episodes, snapshot_interval, last_obs_original):
    keystates = {key: False for key in keys}
    score = 0
    clock = pygame.time.Clock()
    episodes = 0
    screen = pygame.display.set_mode((320, 240))
    update_keystates(keystates)

    try:
        while len(demo) < num_frames:
            # collect transition
            #clock.tick(5)

            action = keystates_to_ale_action(keystates)
            last_obs_original, reward, terminal, info = env.step(action)
            if len(demo)+1 == num_frames:
                terminal = True

            # display it
            last_obs = np.transpose(last_obs_original, [1, 0, 2])
            last_obs = imresize(last_obs, (320, 240))
            surf = pygame.surfarray.make_surface(last_obs)
            screen.blit(surf, (0, 0))
            pygame.display.flip()  # update the display

            lives = 0
            score += reward
            demo.record_timestep(last_obs_original, action, reward, lives, info)
            # end episode on game over
            if terminal:
                # record terminal, take snapshot for resuming, advance to next
                demo.end_episode()
                #demo.snapshot(ale)
                episodes += 1
                if num_episodes > 0 and episodes >= num_episodes:
                    break
                if terminal:
                    # only reset on game over
                    print 'game over, score: {}'.format(score)
                    print 'restarting in 5 seconds'
                    score = 0
                    time.sleep(5)
                    env.reset()

            # prepare the key state for next image
            start = time.time()
            while time.time() - start < 1.0 / 5:
                update_keystates(keystates)
                sleep(0.03)

            if len(demo) % 10000 == 0:
                print 'FPS:', clock.get_fps()
    except KeyboardInterrupt:
        pass
    finally:
        demo.discard_incomplete_episode()
        demo.save(output)

if __name__ == '__main__':
    cli()
