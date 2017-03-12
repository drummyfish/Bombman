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

test_map = bombman.GameMap(map_data,test_play_setup,0,0)

assertion("starting item == ITEM_FLAME", len(test_map.get_starting_items()) == 1 and test_map.get_starting_items()[0] == bombman.GameMap.ITEM_FLAME)
assertion("environment name == \"env1\"", test_map.get_environment_name() == "env1")
assertion("map time == 0", test_map.get_map_time() == 0)
assertion("map state == STATE_WAITING_TO_PLAY", test_map.get_state() == bombman.GameMap.STATE_WAITING_TO_PLAY)

coords = (-1,0)
assertion("tile at " + str(coords) + " == None", test_map.get_tile_at(coords) == None)
coords = (-1,bombman.GameMap.MAP_HEIGHT)
assertion("tile at " + str(coords) + " == None", test_map.get_tile_at(coords) == None)

for y in range(bombman.GameMap.MAP_HEIGHT):
  for x in range(bombman.GameMap.MAP_WIDTH):
    expecting_players = 1 if (x,y) == (0,0) or (x,y) == (14,0) or (x,y) == (0,10) or (x,y) == (14,10) else 0
    assertion("number of players at " + str((x,y)) + "] == " + str(expecting_players), len(test_map.get_players_at_tile((x,y))) == expecting_players)
    assertion("tile [" + str((x,y)) + "] has player", test_map.tile_has_player((x,y)) == (expecting_players == 1))

coords = (0,-1)
assertion("tile " + str(coords) + " is not walkable", not test_map.tile_is_walkable(coords))
coords = (1,0)
assertion("tile " + str(coords) + " is walkable", test_map.tile_is_walkable(coords))
coords = (2,5)
assertion("tile " + str(coords) + " is not walkable", not test_map.tile_is_walkable(coords))

player = test_map.get_players()[0]
assertion("player 0 is not boxing", not player.is_boxing())
assertion("player 0 is not teleporting", not player.is_teleporting())
assertion("player 0 is not throwing", not player.is_throwing())
assertion("player 0 is not dead", not player.is_dead())
assertion("player 0 state time == 0", player.get_state_time() == 0)
assertion("player 0 is not enemy of player 0", not player.is_enemy(player))
assertion("player 0 is enemy of player 1", player.is_enemy(test_map.get_players()[1]))

print("updating map, dt = 500")
test_map.update(500)
print("updating map, dt = 300")
test_map.update(300)

assertion("map state == STATE_WAITING_TO_PLAY", test_map.get_state() == bombman.GameMap.STATE_WAITING_TO_PLAY)

print("updating map, dt = 4000")
test_map.update(4000)

assertion("map state == STATE_PLAYING", test_map.get_state() == bombman.GameMap.STATE_PLAYING)
assertion("map time == 4800", test_map.get_map_time() == 4800)

actions = [(0,bombman.PlayerKeyMaps.ACTION_RIGHT)]

dt = 100

for i in range(20):
  print("moving player 0 to the right using inputs, dt = " + str(dt))
  player.react_to_inputs(actions,dt,test_map)
  test_map.update(dt)

expected_position = (1,0)

assertion("player 0 tile position = " + str(expected_position), player.get_tile_position() == expected_position)

print("making player 0 lay bomb")

actions = [(0,bombman.PlayerKeyMaps.ACTION_BOMB)]
player.react_to_inputs(actions,dt,test_map)
test_map.update(dt)

bombs = test_map.bombs_on_tile(expected_position)
assertion("1 bomb on tile " + str(expected_position), len(bombs) == 1)

bomb = bombs[0]

actions = [(0,bombman.PlayerKeyMaps.ACTION_DOWN)]

for i in range(10):
  print("moving player 0 to down using inputs, dt = " + str(dt))
  player.react_to_inputs(actions,dt,test_map)
  test_map.update(dt)

expected_bomb_time = bombman.Bomb.BOMB_EXPLODES_IN - 11 * dt

assertion("bomb explodes in " + str(expected_bomb_time), bomb.time_until_explosion() == expected_bomb_time)
assertion("bomb doesn't have detonator", not bomb.has_detonator())
assertion("bomb hasn't exploded", not bomb.has_exploded)
assertion("player tile position = (1,1)", player.get_tile_position() == (1,1))

actions = [(0,bombman.PlayerKeyMaps.ACTION_UP)]

for i in range(20):
  print("moving player 0 up using inputs, dt = " + str(dt))
  player.react_to_inputs(actions,dt,test_map)
  test_map.update(dt)

assertion("bomb has exploded", bomb.has_exploded)

tile = (0,0)
assertion("tile " + str(tile) + " has flame", test_map.tile_has_flame(tile))
tile = (1,0)
assertion("tile " + str(tile) + " has flame", test_map.tile_has_flame(tile))
tile = (2,0)
assertion("tile " + str(tile) + " has flame", test_map.tile_has_flame(tile))
tile = (1,1)
assertion("tile " + str(tile) + " has flame", test_map.tile_has_flame(tile))
tile = (0,1)
assertion("tile " + str(tile) + " doesn't have flame", not test_map.tile_has_flame(tile))

assertion("player 0 is dead",player.is_dead())

player1 = test_map.get_players()[1]

actions = [(1,bombman.PlayerKeyMaps.ACTION_RIGHT)]

for i in range(30):
  print("moving player 1 to the right using inputs, dt = " + str(dt))
  player1.react_to_inputs(actions,dt,test_map)
  test_map.update(dt)

assertion("player 1 tile position = (14,0)",player1.get_tile_position() == (14,0))

tile = (2,0)
assertion("tile " + str(tile) + " is walkable (destroyed by flame)", test_map.tile_is_walkable(tile))
tile = (3,0)
assertion("tile " + str(tile) + " is not walkable", not test_map.tile_is_walkable(tile))
tile = (1,2)
assertion("tile " + str(tile) + " is walkable (destroyed by flame)", test_map.tile_is_walkable(tile))

print("=====================")
print("total errors: " + str(errors_total))
