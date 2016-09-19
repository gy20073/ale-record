import numpy as np
import h5py

from collections import namedtuple

Timestep = namedtuple('Timestep', ['state', 'action', 'reward', 'terminal'])

class Demonstration(object):

    snapshot_interval = 1000

    def __init__(self, rom=None):
        self.rom = rom  # rom name as identified by ALE
        self.states = []
        self.actions = []
        self.rewards = []
        self.terminals = []
        self.snapshots = {}

    def record_timestep(self, screen_rgb, action, reward):
        self.states.append(screen_rgb)
        self.actions.append(action)
        self.rewards.append(reward)
        self.terminals.append(False)

    def end_episode(self):
        # TODO(shelhamer) save episode at a time?
        self.terminals[-1] = True

    def __len__(self):
        return len(self.states)

    def __getitem__(self, index):
        return Timestep(self.states[index], self.actions[index],
                        self.rewards[index], self.terminals[index])

    def save(self, path):
        with h5py.File(path, 'w', libver='latest') as f:
            rom = f.create_dataset('rom', data=np.string_(self.rom))
            S = f.create_dataset('S', (len(self), ) + self.states[0].shape, dtype='uint8', compression='gzip', data=np.array(self.states))
            A = f.create_dataset('A', (len(self), ), dtype='uint8', data=np.array(self.actions))
            R = f.create_dataset('R', (len(self), ), dtype='int32', data=np.array(self.rewards))
            terminal = f.create_dataset('terminal', (len(self), ), dtype='b', data=np.array(self.terminals))
            snapshot = f.create_dataset('snapshot', (len(self.snapshots), ) + self.snapshots.values()[0].shape, dtype='uint8', data=np.array(self.snapshots.values()))
            snapshot_t = f.create_dataset('snapshot_t', (len(self.snapshots), ) , dtype='uint32', data=np.array(self.snapshots.keys()))

    def snapshot(self, ale):
        state_ptr = ale.cloneSystemState()
        self.snapshots[len(self)] = ale.encodeState(state_ptr)
        ale.deleteState(state_ptr)

    def restore_timestep(self, ale, t):
        """
        Restore the emulator to a certain time step of the demonstration.
        N.B. Restoring the system state does not give a valid RAM or screen
        state until a step is taken in the emulator.
        """
        assert t > 0, "cannot restore initial state"
        # restore preceding snapshot
        snapshot_t = max(filter(lambda idx: idx < t, self.snapshots.keys()))
        snapshot = ale.decodeState(self.snapshots[snapshot_t])
        ale.restoreSystemState(snapshot)
        # seek through demonstration by following actions in emulator
        for idx in range(snapshot_t, t):
            ale.act(self.actions[idx])

    def reset_to_timestep(self, t):
        for key in self.snapshots.keys():
            if key > t:
                del self.snapshots[key]
        del self.states[t:]
        del self.actions[t:]
        del self.rewards[t:]
        del self.terminals[t:]

    def reset_to_latest_snapshot(self, ale):
        latest = max(self.snapshots.keys())
        self.reset_to_timestep(latest)
        state_enc = self.snapshots[latest]
        state_ptr = ale.decodeState(state_enc)
        ale.restoreSystemState(state_ptr)
        ale.deleteState(state_ptr)

    @staticmethod
    def load(path):
        demo = Demonstration()
        with h5py.File(path, 'r', libver='latest') as f:
            demo.rom = f['rom'].value
            demo.states = [s for s in np.array(f['S'])]  # don't worry, this is fine
            demo.actions = list(f['A'])
            demo.rewards = list(f['R'])
            demo.terminals = list(f['terminal'])
            demo.snapshots = dict(zip(list(f['snapshot_t']), list(f['snapshot'])))
        return demo
