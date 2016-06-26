#!/usr/bin/env python
# coding=utf-8

# Bombman - free and open-source Bomberman clone
#
# Copyright (C) 2016 Miloslav Číž
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Map string format (may contain spaces and newlines, which will be ignored):
#
# <environment>;<player items>;<map items>;<tiles>
#    
# <environment>   - Name of the environment of the map (affects only visual appearance).
# <player items>  - Items that players have from the start of the game (can be an empty string),
#                   each item is represented by one letter (the same letter can appear multiple times):
#                     f - flame
#                     F - max flame
#                     b - bomb
#                     k - kicking shoe
#                     s - spring
#                     d - disease
#                     TODO
# <map items>     - Set of items that will appear on the map (in places of destroyed blocks). The items
#                   are specified with the same letter as in <player items>. If an item appears multiple
#                   times, its probability of being generated will be higher (every time a block is
#                   destroyed, an item is chosen from <map items> set randomly). There is also an
#                   additional symbol:
#                     ! - no item
# <tiles>         - left to right, top to bottom sequenced array of map tiles:
#                     . - floor
#                     x - block (destroyable)
#                     # - wall (undestroyable)
#                     <0-9> - starting position of the player specified by the number
#                     TODO

import sys
import pygame

MAP1 = ("env1;"
        "ff;"
        "ffffbbbbsdk!!!!!!!!;"
        "x . x x x x x x . x x x x . x"
        ". 0 . x x x x . 9 . x x . 3 ."
        "x . x x . x x x . x x . x . x"
        "x x x . 4 . x x x x . 5 . x x"
        "x x x x . x x x x x x . x x x"
        "# x x x x x # # # # x x x x #"
        "x x x x . x x x x x x . x x x"
        "x x x . 7 . x x x x . 6 . x x"
        "x . x x . x x . x x x . x . x"
        ". 2 . x x x . 8 . x x x . 1 ."
        "x . x x x x x . x x x x x . x")

# colors used for players and teams
COLOR_WHITE = 0
COLOR_BLACK = 1
COLOR_RED = 2
COLOR_BLUE = 3
COLOR_GREEN = 4
COLOR_CYAN = 5
COLOR_YELLOW = 6
COLOR_ORANGE = 7
COLOR_BROWN = 8
COLOR_PURPLE = 9

class Player(object):

  # possible player states
  STATE_IDLE_UP = 0
  STATE_IDLE_RIGHT = 1
  STATE_IDLE_DOWN = 2
  STATE_IDLE_LEFT = 3
  STATE_WALKING_UP = 4
  STATE_WALKING_RIGHT = 5
  STATE_WALKING_DOWN = 6
  STATE_WALKING_LEFT = 7
  STATE_DEAD = 8

  def __init__(self):
    self.color = COLOR_WHITE
    self.team_color = COLOR_WHITE
    self.state = Player.STATE_IDLE_DOWN
    self.position = [0.0,0.0]   ##< [X,Y] float position on the map

class Bomb(object):
  def __init__(self):
    self.time_of_existence = 0  ##< for how long (in ms) the bomb has existed
    self.player = None          ##< to which player the bomb belongs
    self.position = [0,0]       ##< [X,Y] int position on the map

class Map(object):
  TILE_FLOOR = 0                ##< walkable map tile
  TILE_BLOCK = 1                ##< non-walkable but destroyable map tile
  TILE_WALL = 2                 ##< non-walkable and non-destroyable map tile

  MAP_WIDTH = 15
  MAP_HEIGHT = 11

  ## Initialises a new map from map_data (string) and a PlaySetup object.

  def __init__(self, map_data, map_setup):
    # make the tiles array:
    self.tiles = []

    map_data = map_data.replace(" ","").replace("\n","")     # get rid of white characters

    string_split = map_data.split(";")

    for i in range(len(string_split[3])):
      tile_character = string_split[3][i]

      if i % Map.MAP_WIDTH == 0:                             # add new row
        self.tiles.append([])

      if tile_character == "x":
        tile = Map.TILE_BLOCK
      elif tile_character == "#":
        tile = Map.TILE_WALL
      else:
        tile = Map.TILE_FLOOR

      self.tiles[-1].append(tile)

  def get_tiles(self):
    return self.tiles

  def __str__(self):
    result = ""

    for line in self.tiles:
      for tile in line:
        if tile == Map.TILE_FLOOR:
          result += " "
        elif tile == Map.TILE_BLOCK:
          result += "x"
        else:
          result += "#"
  
      result += "\n"

    return result

## Defines how a game is set up, i.e. how many players
#  there are, what are the teams etc. Setup does not include
#  the selected map.

class PlaySetup(object):
  def __init__(self):
    self.player_slots = [None for i in range(10)]    ##< player slots: (player_number, team_color), negative player_number = AI, slot index ~ player color index

    # default setup, player 0 vs 3 AI players:
    self.player_slots[0] = (0,0)
    self.player_slots[1] = (-1,1)
    self.player_slots[2] = (-1,2)
    self.player_slots[3] = (-1,3)

## Handles conversion of keyboard events to actions of players, plus general
#  actions (such as menu, ...).

class PlayerKeyMaps(object):
  ACTION_UP = 0
  ACTION_RIGHT = 1
  ACTION_DOWN = 2
  ACTION_LEFT = 3
  ACTION_BOMB = 4
  ACTION_SPECIAL = 5
  ACTION_MENU = 6       ##< brings up the main menu

  def __init__(self):
    self.key_maps = {}  ##< maps keys to tuples of a format: (player_number, action), for general actions player_number will be -1

  ## Sets a key mapping for a player of specified (non-negative) number.

  def set_player_key_map(self, player_number, key_up, key_right, key_down, key_left, key_bomb, key_special):
    self.key_maps[key_up]      = (player_number,PlayerKeyMaps.ACTION_UP)
    self.key_maps[key_right]   = (player_number,PlayerKeyMaps.ACTION_RIGHT)
    self.key_maps[key_down]    = (player_number,PlayerKeyMaps.ACTION_DOWN)
    self.key_maps[key_left]    = (player_number,PlayerKeyMaps.ACTION_LEFT)
    self.key_maps[key_bomb]    = (player_number,PlayerKeyMaps.ACTION_BOMB)
    self.key_maps[key_special] = (player_number,PlayerKeyMaps.ACTION_SPECIAL)

  def set_special_key_map(self, key_menu):
    self.key_maps[key_menu]      = (-1,PlayerKeyMaps.ACTION_MENU)

  ## From currently pressed keys makes a list of actions being currently performed and returns it.

  def get_current_actions(self):
    keys_pressed = pygame.key.get_pressed()

    result = []

    for key_code in self.key_maps:
      if keys_pressed[key_code]:
        result.append(self.key_maps[key_code])

    return result

class Game(object):
  def __init__(self):
    pygame.init()
    self.player_key_maps = PlayerKeyMaps()

    self.player_key_maps.set_player_key_map(0,pygame.K_w,pygame.K_d,pygame.K_s,pygame.K_a,pygame.K_g,pygame.K_h)
    self.player_key_maps.set_player_key_map(1,pygame.K_i,pygame.K_l,pygame.K_k,pygame.K_j,pygame.K_o,pygame.K_p)

  def run(self):
    screen = pygame.display.set_mode((800,600))

    while True:     # main loop
      for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()

      print(self.player_key_maps.get_current_actions())

      screen.fill((0,0,0))
      pygame.display.flip()

# main:

m = Map(MAP1,PlaySetup())
print(m)
#game = Game()
#game.run()
