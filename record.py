#!/usr/bin/env python
import time
import os

import click
import gym
import pygame
import pygame.locals as pl

from demonstration import Demonstration

# taken from gym/util/play.py
def display_arr(screen, arr, video_size):
    pyg_img = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
    pyg_img = pygame.transform.scale(pyg_img, video_size)
    screen.blit(pyg_img, (0,0))

def configure_keys(env):
    keys_to_action = {}
    # substitute WASD -> up, left, down, right arrows
    wasd2arrows = {
        pl.K_SPACE: pl.K_SPACE,
        pl.K_w: pl.K_UP,
        pl.K_a: pl.K_LEFT,
        pl.K_s: pl.K_DOWN,
        pl.K_d: pl.K_RIGHT,
    }
    wasd_keys_to_action = env.unwrapped.get_keys_to_action()
    for ks, v in wasd_keys_to_action.items():
        ks = tuple([wasd2arrows[k] for k in ks])
        keys_to_action[ks] = v
    # screen irrelevant keys
    minimal_keys = set(sum(map(list, keys_to_action.keys()), []))
    # map keystates to minimal actions
    def keystates_to_action(keystates):
        keys = keystates.copy()
        # screen conflicting keys for no-ops
        if pl.K_UP in keys and pl.K_DOWN in keys:
            keys.remove(pl.K_UP)
            keys.remove(pl.K_DOWN)
        if pl.K_RIGHT in keys and pl.K_LEFT in keys:
            keys.remove(pl.K_RIGHT)
            keys.remove(pl.K_LEFT)
        # index by canonical keys, or no-op in case of non-minimal combo
        return keys_to_action.get(tuple(sorted(keys)), 0)
    return keystates_to_action, minimal_keys

def update_keystates(keystates, minimal_keys):
    # track key down/up states
    events = pygame.event.get()
    for event in events:
        if hasattr(event, 'key'):
            if event.key == pl.K_ESCAPE:
                exit(0)
            if event.key in minimal_keys:
                if event.type == pygame.KEYDOWN:
                    keystates.append(event.key)
                elif event.type == pygame.KEYUP:
                    keystates.remove(event.key)
    return keystates

@click.group()
def cli():
    pass

@cli.command(name='new')
@click.argument('rom')
@click.argument('output', type=click.Path())
@click.option('--fps', default=60, help="frames per second to play")
@click.option('--frames', default=60 * 60 * 30, help="Maximum number of frames")
@click.option('--episodes', default=0, help="Maximum number of episodes (game overs)")
@click.option('--seed', default=0, help="Seed for emulator state")
@click.option('--snapshot_interval', default=1800, help="Interval (in timesteps) to snapshot emulator state")
def record_new(rom, output, fps, frames, episodes, seed, snapshot_interval):
    env = gym.make('{}NoFrameskip-v3'.format(rom))
    env.seed(seed)
    demo = Demonstration(rom=rom)
    record(env, demo, output, fps, frames, episodes, snapshot_interval)

@cli.command(name='resume')
@click.argument('partial_demo', type=click.Path(exists=True))
@click.argument('rom')
@click.option('--fps', default=60, help="frames per second to play")
@click.option('--frames', default=60 * 60 * 30, help="Maximum number of frames")
@click.option('--episodes', default=0, help="Maximum number of episodes (game overs)")
@click.option('--snapshot_interval', default=1800, help="Interval (in timesteps) to snapshot emulator state")
def resume(partial_demo, rom, fps, frames, episodes, snapshot_interval):
    demo = Demonstration.load(partial_demo)
    env = gym.make('{}NoFrameskip-v3'.format(rom))
    # restore snapshot from original recording + begin new episode
    # n.b. needed to preserve state from the original recording, like the seed
    demo.reset_to_latest_snapshot(env)
    record(env, demo, partial_demo, fps, frames, episodes, snapshot_interval)

def record(env, demo, output, fps, num_frames, num_episodes, snapshot_interval):
    # configure display and control
    pygame.init()
    clock = pygame.time.Clock()
    screen = pygame.display.set_mode(env.observation_space.shape[:2], pygame.FULLSCREEN|pygame.HWSURFACE)
    keystates = []
    keys_to_action, minimal_keys = configure_keys(env)
    # begin recording
    score = 0
    episodes = 0
    obs = env.reset()
    try:
        while len(demo) < num_frames:
            # update recording interface
            display_arr(screen, obs, env.observation_space.shape[:2])
            update_keystates(keystates, minimal_keys)
            action = keys_to_action(keystates)
            # collect data
            if len(demo) % snapshot_interval == 0:
                demo.snapshot(env)
            obs_t = obs.copy()  # lag one obs. for state and not sucessor
            obs, reward, done, _ = env.step(action)
            lives = env.unwrapped.ale.lives()
            score += reward
            demo.record_timestep(obs_t, action, reward, lives)
            # end episode
            if done:
                episodes += 1
                # record terminal, take snapshot for resuming, advance to next
                demo.end_episode()
                demo.snapshot(env)
                # reset on game over
                print("game over, score: {}".format(score))
                if num_episodes > 0 and episodes >= num_episodes:
                    break
                print("restarting in 5 seconds")
                score = 0
                time.sleep(5)
                env.reset()
            pygame.display.flip()
            clock.tick(fps)
            if len(demo) % 10000 == 0:
                print("FPS:", clock.get_fps())
    except KeyboardInterrupt:
        pass
    finally:
        demo.discard_incomplete_episode()
        demo.save(output)

if __name__ == '__main__':
    cli()
