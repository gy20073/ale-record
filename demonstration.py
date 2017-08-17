import numpy as np
import h5py
import pickle

from collections import namedtuple

Timestep = namedtuple('Timestep', ['state', 'action', 'reward', 'terminal'])

class Demonstration(object):

    VERSION = 3

    def __init__(self, rom=None, action_set=None):
        self.rom = rom  # rom name as identified by ALE
        self.action_set = action_set  # action indices for ALE
        self.states = []
        self.actions = []
        self.rewards = []
        self.terminals = []
        self.lives = []
        self.snapshots = {}
        self.infos = []

    def record_timestep(self, screen_rgb, action, reward, lives, info=None):
        self.states.append(screen_rgb)
        # record action as index, instead of absolute ALE action
        if action in self.action_set:
            action = self.action_set.tolist().index(action)
        else:
            # TODO(shelhamer) check that all non-minimal actions are no-ops
            action = 0
        self.actions.append(action)
        self.rewards.append(reward)
        self.terminals.append(False)
        self.lives.append(lives)
        self.infos.append(info)

    def end_episode(self):
        # TODO(shelhamer) save episode at a time?
        self.terminals[-1] = True

    def __len__(self):
        return len(self.states)

    def __getitem__(self, index):
        return Timestep(self.states[index], self.actions[index],
                        self.rewards[index], self.terminals[index])

    def save(self, path):
        # don't record partial, single episode demonstrations
        if not len(self):
            return
        with h5py.File(path, 'w', libver='latest') as f:
            # metadata
            version = f.create_dataset('version', (1, ), dtype='uint8', data=Demonstration.VERSION)
            rom = f.create_dataset('rom', data=np.string_(self.rom))
            action_set = f.create_dataset('action_set', (len(self.action_set), ), dtype='uint8', data=np.array(self.action_set))
            skip = f.create_dataset('skip', (1, ), dtype='uint8', data=1)
            # transitions
            state_shape = self.states[0].shape
            S = f.create_dataset('S', (len(self), ) + state_shape, dtype='uint8', compression='lzf', data=np.array(self.states))
            A = f.create_dataset('A', (len(self), ), dtype='uint8', data=np.array(self.actions))
            R = f.create_dataset('R', (len(self), ), dtype='int32', data=np.array(self.rewards))
            terminal = f.create_dataset('terminal', (len(self), ), dtype='b', data=np.array(self.terminals))
            lives = f.create_dataset('lives', (len(self), ), dtype='uint8', data=np.array(self.lives))
            # emulator state
            # Yang: don't save snapshots
            #snapshot = f.create_dataset('snapshot', (len(self.snapshots), ) + self.snapshots.values()[0].shape, dtype='uint8', data=np.array(self.snapshots.values()))
            #snapshot_t = f.create_dataset('snapshot_t', (len(self.snapshots), ), dtype='uint32', data=np.array(self.snapshots.keys()))
        pickle.dump(self.infos, open(path+".p", 'wb'))

    def snapshot(self, ale):
        print "not supposed to use"
        state_ptr = ale.cloneSystemState()
        self.snapshots[len(self)] = ale.encodeState(state_ptr)
        ale.deleteState(state_ptr)

    def restore_timestep(self, ale, t):
        print "not supposed to use"
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
        '''
        for key in self.snapshots.keys():
            if key > t:
                del self.snapshots[key]
        '''
        del self.states[t:]
        del self.actions[t:]
        del self.rewards[t:]
        del self.terminals[t:]
        del self.lives[t:]

    def reset_to_latest_snapshot(self, ale):
        print "not supposed to use"
        latest = max(self.snapshots.keys())
        self.reset_to_timestep(latest)
        state_enc = self.snapshots[latest]
        state_ptr = ale.decodeState(state_enc)
        ale.restoreSystemState(state_ptr)
        ale.deleteState(state_ptr)

    def discard_incomplete_episode(self):
        if np.sum(self.terminals):
            # rollback recording to end of last episode
            last_episode_start = np.max(np.where(self.terminals)) + 1
            self.reset_to_timestep(last_episode_start)
        else:
            # incomplete single episode: reset
            self.__init__(rom=self.rom, action_set=self.action_set)

    @staticmethod
    def load(path):
        """Load recorded demonstration metadata, transitions, and snapshots."""
        demo = Demonstration()
        with h5py.File(path, 'r', libver='latest') as f:
            try:
                version = f['version'].value[0]
            except:
                version = 1
            if version != Demonstration.VERSION:
                raise Exception("Format conflict: file is v{} but code is v{}.".format(version, Demonstration.VERSION))
            demo.rom = f['rom'].value
            demo.action_set = list(f['action_set'])
            demo.states = [s for s in np.array(f['S'])]  # don't worry, this is fine
            demo.actions = list(f['A'])
            demo.rewards = list(f['R'])
            demo.terminals = list(f['terminal'])
            demo.lives = list(f['lives'])
            # Yang: don't save snapshots
            #demo.snapshots = dict(zip(list(f['snapshot_t']), list(f['snapshot'])))
        demo.infos = pickle.load(open(path+".p", "rb"))
        return demo

    @staticmethod
    def load_h5(path):
        """Open raw h5 of the recorded demonstration and return for use."""
        f = h5py.File(path, 'r', libver='latest')
        try:
            version = f['version'].value[0]
        except:
            version = 1
        if version != Demonstration.VERSION:
            raise Exception("Format conflict: file is v{} but code is v{}.".format(version, Demonstration.VERSION))
        return f
