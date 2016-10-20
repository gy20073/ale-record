# Cloning

Clone recursively to pull the modified version of ALE too:

```
git clone --recursive git@github.com:shelhamer/ale-record.git
```

# Installation

You may need to `brew install` and/or `pip install` a bunch of things. In
particular, `pygame` is a pain to install. Hopefully this works for you:

```
pip install hg+http://bitbucket.org/pygame/pygame
```

We also need to compile ALE with SDL:

```
cd Arcade-Learning-Environment
mkdir build
cd build
cmake .. -DUSE_SDL=on
make -j8
```

Finally, you'll need `Arcade-Learning-Environment` on your PYTHONPATH. You can
`source .envrc` in the repo root, or install the excellent
[direnv](git@github.com:direnv/direnv.git) to have it automatically modify your
path whenever you enter this directory.

# Usage

`python record.py --help` will tell you the slighest bit about what to do.

Invoking with

```
python record.py new roms/enduro.bin enduro.h5 --episodes 10
```

will fire up the recorder for 10 episodes of enduro, saving the demonstrations to enduro.h5, with a 30 minute limit on the demonstration time.
