#!/usr/bin/env python
import time
import os

import ale_python_interface as ALE
import click
import pygame
import pygame.locals as pl

from demonstration import Demonstration

keys = [pl.K_SPACE, pl.K_UP, pl.K_RIGHT, pl.K_LEFT, pl.K_DOWN]

mapping = {
    # dlruf
    0b00000: 0,
    0b00001: 1,
    0b00010: 2,
    0b00100: 3,
    0b01000: 4,
    0b10000: 5,
    0b00110: 6,
    0b01010: 7,
    0b10100: 8,
    0b11000: 9,
    0b00011: 10,
    0b00101: 11,
    0b01001: 12,
    0b10001: 13,
    0b00111: 14,
    0b01011: 15,
    0b10101: 16,
    0b11001: 17
}


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
    return mapping[bitvec]


def update_keystates(keystates):
    events = pygame.event.get()
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
@click.option('--frames', default=60 * 60 * 30, help="Maximum number of frames")
@click.option('--episodes', default=0, help="Maximum number of episodes (game overs)")
@click.option('--seed', default=0, help="Seed for emulator state")
@click.option('--snapshot_interval', default=1800, help="Interval (in timesteps) to snapshot emulator state")
def record_new(rom, output, frames, episodes, seed, snapshot_interval):
    rom_name = os.path.splitext(os.path.split(rom)[-1])[0]
    pygame.init()
    ale = ALE.ALEInterface()
    ale.setInt('random_seed', seed)
    ale.setFloat('repeat_action_probability', 0)
    ale.setBool('color_averaging', False)
    ale.setBool('display_screen', True)
    ale.loadROM(rom)
    demo = Demonstration(rom=rom_name, action_set=ale.getMinimalActionSet())
    record(ale, demo, output, frames, episodes, snapshot_interval)

@cli.command(name='resume')
@click.argument('partial_demo', type=click.Path(exists=True))
@click.argument('rom', type=click.Path(exists=True))
@click.option('--frames', default=60 * 60 * 30, help="Maximum number of frames")
@click.option('--episodes', default=0, help="Maximum number of episodes (game overs)")
@click.option('--snapshot_interval', default=1800, help="Interval (in timesteps) to snapshot emulator state")
def resume(partial_demo, rom, frames, episodes, snapshot_interval):
    pygame.init()
    demo = Demonstration.load(partial_demo)
    ale = ALE.ALEInterface()
    ale.setFloat('repeat_action_probability', 0)
    ale.setBool('color_averaging', False)
    ale.setBool('display_screen', True)
    ale.loadROM(rom)
    # restore snapshot from original recording + begin new episode
    # n.b. needed to preserve state from the original recording, like the seed
    demo.reset_to_latest_snapshot(ale)
    ale.reset_game()
    record(ale, demo, partial_demo, frames, episodes, snapshot_interval)

def record(ale, demo, output, num_frames, num_episodes, snapshot_interval):
    keystates = {key: False for key in keys}
    score = 0
    clock = pygame.time.Clock()
    episodes = 0
    try:
        while len(demo) < num_frames:
            if len(demo) % snapshot_interval == 0:
                demo.snapshot(ale)
            # collect transition
            frame = ale.getScreenRGB()
            update_keystates(keystates)
            action = keystates_to_ale_action(keystates)
            reward = ale.act(action)
            lives = ale.lives()
            score += reward
            demo.record_timestep(frame, action, reward, lives)
            # end episode on game over
            if ale.game_over():
                # record terminal, take snapshot for resuming, advance to next
                demo.end_episode()
                demo.snapshot(ale)
                episodes += 1
                if num_episodes > 0 and episodes >= num_episodes:
                    break
                if ale.game_over():
                    # only reset on game over
                    print 'game over, score: {}'.format(score)
                    print 'restarting in 5 seconds'
                    score = 0
                    time.sleep(5)
                    ale.reset_game()
            clock.tick(60)
            if len(demo) % 10000 == 0:
                print 'FPS:', clock.get_fps()
    except KeyboardInterrupt:
        pass
    finally:
        demo.discard_incomplete_episode()
        demo.save(output)

if __name__ == '__main__':
    cli()
