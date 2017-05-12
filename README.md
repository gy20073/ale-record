# Cloning

Clone recursively to pull the future gym and atari-py too:

```
git clone --branch dm --recursive  git@github.com:shelhamer/ale-record.git gym-record
```

# Installation

You need to satisfy the dependencies of gym and atari-py.
Once done, build atari-py by `cd atari-py; make`

Next, you need `pygame`, which is a pain to install. Hopefully this works for you:

```
pip install hg+http://bitbucket.org/pygame/pygame
```

Finally, you'll need both gym and atari-py on your PYTHONPATH. You can `source
.envrc` in the repo root, or install the excellent
[direnv](git@github.com:direnv/direnv.git) to have it automatically modify your
path whenever you enter this directory.

# Usage

`python record.py --help` will tell you the slighest bit about what to do.

Invoking with

```
python record.py new SpaceInvaders invaders.h5 --episodes 10
```

will fire up the recorder for 10 episodes of Space Invaders, saving the demonstrations to invaders.h5, with a 30 minute limit on the demonstration time.
