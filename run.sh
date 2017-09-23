#!/usr/bin/env bash

dt=$(date| sed 's/ /_/g')

#python record_torcs.py new /home/yang/rlTORCS  torcs${dt}.h5 /home/yang/rlTORCS/game_config/huazhe.xml --episodes 1 --frames 900
python record_torcs.py new /home/yang/rlTORCS  yang2_torcs${dt}.h5 /home/yang/rlTORCS/game_config/quickrace_discrete_single.xml --episodes 1 --frames 900

