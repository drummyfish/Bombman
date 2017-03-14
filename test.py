#!/usr/bin/env python
# coding=utf-8
#
# automatic tests for bombman

import bombman
import pygame
import os

errors_total = 0

def assertion(message, condition):
  global errors_total
  print("  TESTING: " + message + ": " + ("OK" if condition else "ERROR"))

  if not condition:
    errors_total += 1

#       ======================
#       play a small test game
#       ======================

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

assertion("number of block tiles on map = 122",test_map.get_number_of_block_tiles() == 122)
assertion("starting item = ITEM_FLAME", len(test_map.get_starting_items()) == 1 and test_map.get_starting_items()[0] == bombman.GameMap.ITEM_FLAME)
assertion("environment name = \"env1\"", test_map.get_environment_name() == "env1")
assertion("map time = 0", test_map.get_map_time() == 0)
assertion("map state = STATE_WAITING_TO_PLAY", test_map.get_state() == bombman.GameMap.STATE_WAITING_TO_PLAY)

coords = (-1,0)
assertion("tile at " + str(coords) + " = None", test_map.get_tile_at(coords) == None)
coords = (0,bombman.GameMap.MAP_HEIGHT)
assertion("tile at " + str(coords) + " = None", test_map.get_tile_at(coords) == None)

for y in range(bombman.GameMap.MAP_HEIGHT):
  for x in range(bombman.GameMap.MAP_WIDTH):
    expecting_players = 1 if (x,y) == (0,0) or (x,y) == (14,0) or (x,y) == (0,10) or (x,y) == (14,10) else 0
    assertion("number of players at " + str((x,y)) + "] = " + str(expecting_players), len(test_map.get_players_at_tile((x,y))) == expecting_players)
    assertion("tile [" + str((x,y)) + "] has player", test_map.tile_has_player((x,y)) == (expecting_players == 1))

coords = (0,-1)
assertion("tile " + str(coords) + " is not walkable", not test_map.tile_is_walkable(coords))
coords = (1,0)
assertion("tile " + str(coords) + " is walkable", test_map.tile_is_walkable(coords))
coords = (2,5)
assertion("tile " + str(coords) + " is not walkable", not test_map.tile_is_walkable(coords))

player = test_map.get_players()[0]
player1 = test_map.get_players()[1]
player2 = test_map.get_players()[2]
player3 = test_map.get_players()[3]

print("init AI for player 0")
ai = bombman.AI(player,test_map)

assertion("player 0 is not boxing", not player.is_boxing())
assertion("player 0 is not teleporting", not player.is_teleporting())
assertion("player 0 is not throwing", not player.is_throwing())
assertion("player 0 is not dead", not player.is_dead())
assertion("player 0 has 0 kills", player.get_kills() == 0)
assertion("player 0 state time = 0", player.get_state_time() == 0)
assertion("player 0 is not enemy of player 0", not player.is_enemy(player))
assertion("player 0 is enemy of player 1", player.is_enemy(test_map.get_players()[1]))
assertion("player 0 forward tile", player.get_forward_tile_position() == (0,1))
assertion("AI - player 0 is not trapped", not ai.is_trapped())


print("give some items to player 3")

player3.give_item(bombman.GameMap.ITEM_BOMB)
player3.give_item(bombman.GameMap.ITEM_BOMB)
player3.give_item(bombman.GameMap.ITEM_BOMB)
player3.give_item(bombman.GameMap.ITEM_SPEEDUP)

print(player3.get_item_count(bombman.GameMap.ITEM_BOMB))
assertion("right item count for ITEM_BOMB",player3.get_item_count(bombman.GameMap.ITEM_BOMB) == 4) # three plus one default bomb
assertion("right item count for ITEM_SPEEDUP",player3.get_item_count(bombman.GameMap.ITEM_SPEEDUP) == 1)
assertion("right item count for ITEM_SHOE",player3.get_item_count(bombman.GameMap.ITEM_SHOE) == 0)
assertion("total number of items",len(player3.get_items()) == 7)

tile = (0,0)
assertion("AI - number of blocks next to " + str(tile) + " = 0", ai.number_of_blocks_next_to_tile(tile) == 0)
tile = (1,1)
assertion("AI - number of blocks next to " + str(tile) + " = 2", ai.number_of_blocks_next_to_tile(tile) == 2)
tile = (0,5)
assertion("AI - number of blocks next to " + str(tile) + " = 0", ai.number_of_blocks_next_to_tile(tile) == 0)
tile = (0,0)
assertion("AI - tile " + str(tile) + " is escapable", ai.tile_is_escapable(tile))
assertion("AI - no players nearby",ai.players_nearby() == (0,0))

tile = (4,3)
print("make player 1 lay bomb at " + str(tile))
player1.lay_bomb(test_map,tile)

fyling_bomb = test_map.bomb_on_tile(tile)

direction_ratings = ai.rate_bomb_escape_directions(tile)
assertion("AI - all escape directions from tile " + str(tile) + " are rated 0",direction_ratings == (0,0,0,0))

print("send the bomb flying left")
fyling_bomb.send_flying((-1,tile[1]))

print("updating map, dt = 500")
test_map.update(500)
print("updating map, dt = 300")
test_map.update(300)

assertion("map state = STATE_WAITING_TO_PLAY", test_map.get_state() == bombman.GameMap.STATE_WAITING_TO_PLAY)

print("updating map, dt = 4000")
test_map.update(4000)

assertion("map state = STATE_PLAYING", test_map.get_state() == bombman.GameMap.STATE_PLAYING)
assertion("map time = 4800", test_map.get_map_time() == 4800)

actions = [(0,bombman.PlayerKeyMaps.ACTION_RIGHT)]

dt = 100

for i in range(20):
  print("moving player 0 to the right using inputs, dt = " + str(dt))
  player.react_to_inputs(actions,dt,test_map)
  test_map.update(dt)

assertion("bomb position = (11,3)",  fyling_bomb.get_tile_position() == (11,3))

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
assertion("tile " + str(tile) + " has flame and danger value = 0", test_map.tile_has_flame(tile) and test_map.get_danger_value(tile) == 0)
tile = (1,0)
assertion("tile " + str(tile) + " has flame and danger value = 0", test_map.tile_has_flame(tile) and test_map.get_danger_value(tile) == 0)
tile = (2,0)
assertion("tile " + str(tile) + " has flame and danger value = 0", test_map.tile_has_flame(tile) and test_map.get_danger_value(tile) == 0)
tile = (1,1)
assertion("tile " + str(tile) + " has flame and danger value = 0", test_map.tile_has_flame(tile) and test_map.get_danger_value(tile) == 0)
tile = (0,1)
assertion("tile " + str(tile) + " doesn't have flame and danger value != 0", not test_map.tile_has_flame(tile) and test_map.get_danger_value(tile) != 0)

assertion("player 0 is dead",player.is_dead())

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

print("making players 1 and 2 lay bombs")
actions = [(1,bombman.PlayerKeyMaps.ACTION_BOMB),(2,bombman.PlayerKeyMaps.ACTION_BOMB)]

player1.react_to_inputs(actions,dt,test_map)
player2.react_to_inputs(actions,dt,test_map)
test_map.update(dt)

assertion("2 bombs on map",len(test_map.get_bombs()) == 2)

tile = (0,0)
assertion("tile " + str(tile) + " - danger value is safe",test_map.get_danger_value(tile) >= bombman.GameMap.SAFE_DANGER_VALUE)
tile = (5,6)
assertion("tile " + str(tile) + " - danger value = 0",test_map.get_danger_value(tile) == 0)
tile = player2.get_tile_position()
assertion("tile 1 up from player 2 danger value >= bom explosion time - dt",test_map.get_danger_value(tile) >= bombman.Bomb.BOMB_EXPLODES_IN - dt)

for i in range(40):
  print("updating map, dt = " + str(dt))
  test_map.update(dt)

assertion("player 1 and player 2 are dead, player 3 is alive",player1.is_dead() and player2.is_dead() and not player3.is_dead())
assertion("map state = STATE_FINISHING",test_map.get_state() == bombman.GameMap.STATE_FINISHING)
assertion("number of block tiles on map = 117",test_map.get_number_of_block_tiles() == 117)

print("wait for a while")

for i in range(50):
  test_map.update(dt)

assertion("map state = STATE_GAME_OVER",test_map.get_state() == bombman.GameMap.STATE_GAME_OVER)
assertion("map winning team = 3",test_map.get_winner_team() == 3)

#       =================
#       test other things
#       =================

assertion("ACTION_DOWN is opposite of ACTION_UP",bombman.PlayerKeyMaps.get_opposite_action(bombman.PlayerKeyMaps.ACTION_UP) == bombman.PlayerKeyMaps.ACTION_DOWN)
assertion("ACTION_LEFT is opposite of ACTION_RIGHT",bombman.PlayerKeyMaps.get_opposite_action(bombman.PlayerKeyMaps.ACTION_LEFT) == bombman.PlayerKeyMaps.ACTION_RIGHT)

print("init game")
game = bombman.Game()

print("init animation")

animation = bombman.Animation(os.path.join(bombman.Game.RESOURCE_PATH,"animation_explosion"),1,10,".png",7)

print("init main menu")
main_menu = bombman.MainMenu(game.sound_player)

main_menu.process_inputs([])     # needed

print("press down and right")
actions = [(0,bombman.PlayerKeyMaps.ACTION_DOWN),(0,bombman.PlayerKeyMaps.ACTION_RIGHT)]
main_menu.process_inputs(actions)

print("scrolling (should do nothing)")
main_menu.scroll(True)

assertion("scroll position = 0",main_menu.scroll_position == 0)
assertion("menu state = MENU_STATE_SELECTING",main_menu.get_state() == bombman.Menu.MENU_STATE_SELECTING)
assertion("selected item = (1,0)",main_menu.get_selected_item() == (1,0))

print("press bomb")
actions = [(0,bombman.PlayerKeyMaps.ACTION_BOMB)]
main_menu.process_inputs(actions)
assertion("menu state = MENU_STATE_CONFIRM",main_menu.get_state() == bombman.Menu.MENU_STATE_CONFIRM)

print("init key map")
key_maps = bombman.PlayerKeyMaps()

print("set some keys")
key_maps.set_one_key_map(pygame.K_a,0,bombman.PlayerKeyMaps.ACTION_UP)
key_maps.set_one_key_map(pygame.K_ESCAPE,1,bombman.PlayerKeyMaps.ACTION_DOWN)
key_maps.set_one_key_map(pygame.K_b,0,bombman.PlayerKeyMaps.ACTION_BOMB)
key_maps.set_one_key_map(pygame.K_c,0,bombman.PlayerKeyMaps.ACTION_LEFT)

key_map0 = key_maps.get_players_key_mapping(0)
key_map1 = key_maps.get_players_key_mapping(1)

assertion("action up, player 0 = 'a'",key_map0[bombman.PlayerKeyMaps.ACTION_UP] == pygame.K_a)
assertion("action left, player 0 = 'c'",key_map0[bombman.PlayerKeyMaps.ACTION_LEFT] == pygame.K_c)
assertion("action left, player 1 = 'esc'",key_map1[bombman.PlayerKeyMaps.ACTION_DOWN] == pygame.K_ESCAPE)

print("init settings and set some values")

settings = bombman.Settings(key_maps)
settings.player_key_maps.set_one_key_map(pygame.K_a,0,bombman.PlayerKeyMaps.ACTION_UP)

settings.music_volume = 0.3
settings.sound_volume = 0
settings.fullscreen = True
settings.control_by_mouse = True

print("save and reload settings to/from string")

settings_string = settings.save_to_string()
settings.load_from_string(settings_string)

assertion("music volume",settings.music_volume == 0.3)
assertion("sound volume",settings.sound_volume == 0)
assertion("music on",settings.music_is_on())
assertion("sound off",not settings.sound_is_on())
assertion("fullscreen",settings.fullscreen)
assertion("mouse control",settings.control_by_mouse)
assertion("key map - action up, player 0 = 'a'",settings.player_key_maps.get_players_key_mapping(0)[bombman.PlayerKeyMaps.ACTION_UP] == pygame.K_a)

print("=====================")
print("total errors: " + str(errors_total))
