#!/usr/bin/env python
# coding=utf-8
#
# automatic tests for bombman

import bombman
import os

errors_total = 0

def assertion(message, condition):
  global errors_total
  print("  TESTING: " + message + ": " + ("OK" if condition else "ERROR"))

  if not condition:
    errors_total += 1

print("creating PlaySetup object, leaving default setup")
test_play_setup = bombman.PlaySetup()

number_of_games = 5

print("setting number of games to " + str(number_of_games) + ", then call increse, increse, decrease")
test_play_setup.set_number_of_games(number_of_games)

test_play_setup.increase_number_of_games()
test_play_setup.increase_number_of_games()
test_play_setup.decrease_number_of_games()

assertion("correct number of games in play setup", test_play_setup.get_number_of_games() == number_of_games + 1)

print("number of players in play setup: " + str(len(test_play_setup.get_slots())))

map_file = open(os.path.join(bombman.Game.MAP_PATH,"classic"))
map_data = map_file.read()
map_file.close()

print("initialising Map object (\"classic\") with play setup")

test_map = bombman.Map(map_data,test_play_setup,0,0)

assertion("starting item == ITEM_FLAME", len(test_map.get_starting_items()) == 1 and test_map.get_starting_items()[0] == bombman.Map.ITEM_FLAME)

print("=====================")
print("total errors: " + str(errors_total))
