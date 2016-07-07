#!/usr/bin/env python
# coding=utf-8
#
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
#
# Map string format (may contain spaces and newlines, which will be ignored):
#
# <environment>;<player items>;<map items>;<tiles>
#    
# <environment>   - Name of the environment of the map (affects only visual appearance).
# <player items>  - Items that players have from the start of the game (can be an empty string),
#                   each item is represented by one letter (the same letter can appear multiple times):
#                     f - flame
#                     F - superflame
#                     b - bomb
#                     k - kicking shoe
#                     s - speedup
#                     p - spring
#                     d - disease
#                     m - multibomb
#                     r - random
#                     x - boxing glove
#                     e - detonator
#                     t - throwing glove
#                     TODO
# <map items>     - Set of items that will be hidden in block on the map. This is a string of the
#                   same format as in <player items>. If there is more items specified than there is
#                   block tiles, then some items will be left out.
# <tiles>         - left to right, top to bottom sequenced array of map tiles:
#                     . - floor
#                     x - block (destroyable)
#                     # - wall (undestroyable)
#                     A - teleport A
#                     B - teleport B
#                     T - trampoline
#                     <0-9> - starting position of the player specified by the number
#                     TODO

import sys
import pygame
import os
import math
import copy
import random
import time

MAP1 = ("env3;"
        "bf;"
        "bbbbbbFssssspppppddddmmmrxxettkkkkk;"
        "x T x x x x x x . x x x x . x"
        ". 0 . . . x x B 9 . x x . 3 ."
        "x . x x T x x x . x x . x . x"
        "x x x . 4 . x x x x A 5 . x x"
        "x x x x T x x x x x x . x x x"
        "# x x x x x # # # # x x x x #"
        "x x x x . x x x x x x T x x x"
        "x x x A 7 . x x x x . 6 . x x"
        "x . x x . x x . x x x . x . x"
        ". 2 . x x x . 8 B x x x . 1 ."
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

COLOR_RGB_VALUES = [
  (210,210,210),           # white
  (10,10,10),              # black
  (255,0,0),               # red
  (0,0,255),               # blue
  (0,255,0),               # green
  (52,237,250),            # cyan
  (255,255,69),            # yellow
  (255,192,74),            # orange
  (168,127,56),            # brown
  (209,117,206)            # purple
  ]

RESOURCE_PATH = "resources"

## Something that has a float position on the map.

class Positionable(object):
  def __init__(self):
    self.position = (0.0,0.0)

  def set_position(self,position):
    self.position = position

  def get_position(self):
    return self.position
  
  ## Moves the object to center of tile (if not specified, objects current tile is used).
  
  def move_to_tile_center(self, tile_coordinates=None):
    if tile_coordinates != None:
      self.position = tile_coordinates
    
    self.position = (math.floor(self.position[0]) + 0.5,math.floor(self.position[1]) + 0.5)

  ## Converts float position to integer tile position.

  @staticmethod
  def position_to_tile(position):
    return (int(math.floor(position[0])),int(math.floor(position[1])))
  
  def is_near_tile_center(self):
    position_within_tile = (self.position[0] % 1,self.position[1] % 1)
    
    limit = 0.2
    limit2 = 1.0 - limit
    
    return (limit < position_within_tile[0] < limit2) and (limit < position_within_tile[1] < limit2)

class Player(Positionable):
  # possible player states
  STATE_IDLE_UP = 0
  STATE_IDLE_RIGHT = 1
  STATE_IDLE_DOWN = 2
  STATE_IDLE_LEFT = 3
  STATE_WALKING_UP = 4
  STATE_WALKING_RIGHT = 5
  STATE_WALKING_DOWN = 6
  STATE_WALKING_LEFT = 7
  STATE_IN_AIR = 8
  STATE_DEAD = 9

  DISEASE_NONE = 0
  DISEASE_DIARRHEA = 1
  DISEASE_SLOW = 2
  DISEASE_REVERSE_CONTROLS = 3
  DISEASE_SHORT_FLAME = 4
  DISEASE_SWITCH_PLAYERS = 5
  DISEASE_FAST_BOMB = 6
  DISEASE_NO_BOMB = 7

  INITIAL_SPEED = 3
  SLOW_SPEED = 1.5
  MAX_SPEED = 10
  SPEEDUP_VALUE = 1
  DISEASE_TIME = 20000
  
  JUMP_DURATION = 2000

  def __init__(self):
    super(Player,self).__init__()
    self.number = 0                       ##< players number and also color index
    self.team_color = COLOR_WHITE
    self.state = Player.STATE_IDLE_DOWN
    self.state_time = 0                   ##< how much time (in ms) has been spent in current time
    self.speed = Player.INITIAL_SPEED     ##< speed in tiles per second
    self.bombs_left = 1                   ##< how many more bombs the player can put at the time
    self.flame_length = 1                 ##< how long the flame is in tiles
    self.items = {}                       ##< which items and how many the player has, format: [item code]: count
    self.has_spring = False               ##< whether player's bombs have springs
    self.has_shoe = False                 ##< whether player has a kicking shoe
    self.disease_time_left = 0
    self.disease = Player.DISEASE_NONE
    self.has_multibomb = False
    self.has_boxing_glove = False
    self.has_throwing_glove = False
    self.boxing = False
    self.detonator_boms_left = 0          ##< what number of following bombs will have detonators
    self.detonator_bombs = []             ##< references to bombs to be detonated
    self.wait_for_special_release = False ##< helper used to wait for special key release
    self.wait_for_bomb_release = False
    self.throwing_time_left = 0           ##< for how longer (in ms) the player will be in a state of throwing (only for visuals)
    self.state_backup = Player.STATE_IDLE_UP    ##< used to restore previous state, for example after jump
    self.jumping_to = (0,0)               ##< coordinates of a tile the player is jumping to
    
  def is_boxing(self):
    return self.boxing

  def send_to_air(self, game_map):
    if self.state == Player.STATE_IN_AIR:
      return
    
    game_map.add_sound_event(SoundPlayer.SOUND_EVENT_TRAMPOLINE)
    
    self.state_backup = self.state
    self.state = Player.STATE_IN_AIR
    self.jumping_from = Positionable.position_to_tile(self.position)
    
    landing_tiles = []  # potential tiles to land on
    
    # find a landing tile:
    
    for y in range (self.jumping_from[1] - 3,self.jumping_from[1] + 4):
      for x in range (self.jumping_from[0] - 3,self.jumping_from[0] + 4):
        tile = game_map.get_tile_at((x,y))
        
        if tile != None and game_map.tile_is_walkable((x,y)) and tile.special_object == None:
          landing_tiles.append((x,y))
    
    if len(landing_tiles) == 0:    # this should practically not happen
      self.jumping_to = (self.jumping_from[0],self.jumping_from[1] + 1)
    else:
      self.jumping_to = random.choice(landing_tiles)
    
    self.state_time = 0

  def get_state_time(self):
    return self.state_time

  def get_jump_destination(self):
    return self.jumping_to

  def is_in_air(self):
    return self.state == Player.STATE_IN_AIR

  def is_throwing(self):
    return self.throwing_time_left > 0

  ## Gives player an item with given code (see Map class constants). game_map
  #  is needed so that sounds can be made on item pickup - if no map is provided,
  #  no sounds will be generated.

  def give_item(self, item,game_map=None):
    if not item in self.items:
      self.items[item] = 1
    else:
      self.items[item] += 1
      
    if item == Map.ITEM_RANDOM:
      item = random.choice((
        Map.ITEM_BOMB,
        Map.ITEM_FLAME,
        Map.ITEM_SUPERFLAME,
        Map.ITEM_MULTIBOMB,
        Map.ITEM_SPRING,
        Map.ITEM_SHOE,
        Map.ITEM_SPEEDUP,
        Map.ITEM_DISEASE,
        Map.ITEM_BOXING_GLOVE,
        Map.ITEM_DETONATOR,
        Map.ITEM_THROWING_GLOVE
        ))
      
    sound_to_make = SoundPlayer.SOUND_EVENT_CLICK
      
    if item == Map.ITEM_BOMB:
      self.bombs_left += 1
    elif item == Map.ITEM_FLAME:
      self.flame_length += 1
    elif item == Map.ITEM_SUPERFLAME:
      self.flame_length = max(Map.MAP_WIDTH,Map.MAP_HEIGHT)
    if item == Map.ITEM_MULTIBOMB:
      self.has_multibomb = True
    elif item == Map.ITEM_DETONATOR:
      self.detonator_boms_left = 3      
    elif item == Map.ITEM_SPRING:
      self.has_spring = True
      sound_to_make = SoundPlayer.SOUND_EVENT_SPRING
    elif item == Map.ITEM_SPEEDUP:
      self.speed = min(self.speed + Player.SPEEDUP_VALUE,Player.MAX_SPEED)
    elif item == Map.ITEM_SHOE:
      self.has_shoe = True
    elif item == Map.ITEM_BOXING_GLOVE:
      self.has_boxing_glove = True
    elif item == Map.ITEM_THROWING_GLOVE:
      self.has_throwing_glove = True
    elif item == Map.ITEM_DISEASE:
      chosen_disease = random.choice([
        (Player.DISEASE_SHORT_FLAME,SoundPlayer.SOUND_EVENT_DISEASE),     
        (Player.DISEASE_SLOW,SoundPlayer.SOUND_EVENT_SLOW),
        (Player.DISEASE_DIARRHEA,SoundPlayer.SOUND_EVENT_DIARRHEA),
        (Player.DISEASE_FAST_BOMB,SoundPlayer.SOUND_EVENT_DISEASE),
        (Player.DISEASE_REVERSE_CONTROLS,SoundPlayer.SOUND_EVENT_DISEASE),
        (Player.DISEASE_SWITCH_PLAYERS,SoundPlayer.SOUND_EVENT_DISEASE),
        (Player.DISEASE_NO_BOMB,SoundPlayer.SOUND_EVENT_DISEASE)
        ])
      
      if chosen_disease[0] == Player.DISEASE_SWITCH_PLAYERS:
        if game_map != None:
          players = game_map.get_players()
          
          player_to_switch = self
          
          while player_to_switch == self:
            player_to_switch = random.choice(players)
          
          my_position = self.get_position()
          self.set_position(player_to_switch.get_position())
          player_to_switch.set_position(my_position)
      else:
        self.disease = chosen_disease[0]
        self.disease_time_left = Player.DISEASE_TIME
    
      sound_to_make = chosen_disease[1]
    
    if game_map != None and sound_to_make != None:
      game_map.add_sound_event(sound_to_make)
    
  def lay_bomb(self, game_map, tile_coordinates=None):  
    new_bomb = Bomb(self)
    
    if tile_coordinates != None:
      new_bomb.set_position(tile_coordinates)
      new_bomb.move_to_tile_center()
    
    game_map.add_bomb(new_bomb)
    game_map.add_sound_event(SoundPlayer.SOUND_EVENT_BOMB_PUT)
    self.bombs_left -= 1
      
    if self.disease == Player.DISEASE_SHORT_FLAME:
      new_bomb.flame_length = 1
    elif self.disease == Player.DISEASE_FAST_BOMB:
      new_bomb.explodes_in = 800 
      
    if self.detonator_boms_left > 0:
      new_bomb.detonator_time_left = Bomb.DETONATOR_EXPIRATION_TIME
      self.detonator_bombs.append(new_bomb)
      self.detonator_boms_left -= 1
    
  def has_kicking_shoe(self):
    return self.has_shoe
      
  def get_disease(self):
    return self.disease
      
  def bombs_have_spring(self):
    return self.has_spring
      
  ## Says how many of a given item the player has.
      
  def how_many_items(self, item):
    if not item in self.items:
      return 0
    
    return self.items[item]
    
  def set_number(self, number):
    self.number = number

  ## Must be called when this player's bomb explodes so that their bomb limit is increased again.

  def bomb_exploded(self):
    self.bombs_left += 1

  def get_number(self):
    return self.number

  def get_state(self):
    return self.state

  def get_state_time(self):
    return self.state_time

  def get_flame_length(self):
    return self.flame_length

  ## Gets a direction vector (x and y: 0, 1 or -1) depending on where the player is facing.

  def get_direction_vector(self):
    if self.state == Player.STATE_WALKING_UP or self.state == Player.STATE_IDLE_UP:
      return (0,-1)
    elif self.state == Player.STATE_WALKING_RIGHT or self.state == Player.STATE_IDLE_RIGHT:
      return (1,0)
    elif self.state == Player.STATE_WALKING_DOWN or self.state == Player.STATE_IDLE_DOWN:
      return (0,1)
    else:              # left
      return (-1,0)    

  ## Sets the state and other attributes like position etc. of this player accoording to a list of input action (returned by PlayerKeyMaps.get_current_actions()).

  def react_to_inputs(self, input_actions, dt, game_map):
    if self.state == Player.STATE_IN_AIR:
      self.state_time += dt
      
      if self.state_time >= Player.JUMP_DURATION:
        self.state = self.state_backup
        self.state_time = 0
      else:
        return
    
    current_speed = self.speed if self.disease != Player.DISEASE_SLOW else Player.SLOW_SPEED
    
    distance_to_travel = dt / 1000.0 * current_speed
    
    self.throwing_time_left = max(0,self.throwing_time_left - dt)

    self.position = list(self.position)    # in case position was tuple

    old_state = self.state
 
    if self.state == Player.STATE_WALKING_UP or self.state == Player.STATE_IDLE_UP:
      self.state = Player.STATE_IDLE_UP
    elif self.state == Player.STATE_WALKING_RIGHT or self.state == Player.STATE_IDLE_RIGHT:
      self.state = Player.STATE_IDLE_RIGHT
    elif self.state == Player.STATE_WALKING_DOWN or self.state == Player.STATE_IDLE_DOWN:
      self.state = Player.STATE_IDLE_DOWN
    else:
      self.state = Player.STATE_IDLE_LEFT

    moved = False  # to allow movement along only one axis at a time

    previous_position = copy.copy(self.position)  # in case of collision we save the previous position

    putting_bomb = False
    putting_multibomb = False
    throwing = False
    detonator_triggered = False
    self.boxing = False
    special_was_pressed = False
    bomb_was_pressed = False
    
    if self.disease == Player.DISEASE_DIARRHEA:
      input_actions.append((self.number,PlayerKeyMaps.ACTION_BOMB))  # inject bomb put event

    for item in input_actions:
      if item[0] != self.number:
        continue                           # not an action for this player
      
      input_action = item[1]

      if self.disease == Player.DISEASE_REVERSE_CONTROLS:
        if input_action == PlayerKeyMaps.ACTION_UP:
          input_action = PlayerKeyMaps.ACTION_DOWN
        elif input_action == PlayerKeyMaps.ACTION_RIGHT:
          input_action = PlayerKeyMaps.ACTION_LEFT
        elif input_action == PlayerKeyMaps.ACTION_DOWN:
          input_action = PlayerKeyMaps.ACTION_UP
        elif input_action == PlayerKeyMaps.ACTION_LEFT:
          input_action = PlayerKeyMaps.ACTION_RIGHT
          
      if not moved and input_action == PlayerKeyMaps.ACTION_UP:
        self.position[1] -= distance_to_travel
        self.state = Player.STATE_WALKING_UP
        game_map.add_sound_event(SoundPlayer.SOUND_EVENT_WALK)
        moved = True
      elif not moved and input_action == PlayerKeyMaps.ACTION_DOWN:
        self.position[1] += distance_to_travel
        self.state = Player.STATE_WALKING_DOWN
        game_map.add_sound_event(SoundPlayer.SOUND_EVENT_WALK)
        moved = True
      elif not moved and input_action == PlayerKeyMaps.ACTION_RIGHT:
        self.position[0] += distance_to_travel
        self.state = Player.STATE_WALKING_RIGHT
        game_map.add_sound_event(SoundPlayer.SOUND_EVENT_WALK)
        moved = True
      elif not moved and input_action == PlayerKeyMaps.ACTION_LEFT:
        self.position[0] -= distance_to_travel
        self.state = Player.STATE_WALKING_LEFT
        game_map.add_sound_event(SoundPlayer.SOUND_EVENT_WALK)
        moved = True
    
      if input_action == PlayerKeyMaps.ACTION_BOMB:
        bomb_was_pressed = True
        
        if not self.wait_for_bomb_release and self.bombs_left >= 1 and not game_map.tile_has_bomb(self.position) and not self.disease == Player.DISEASE_NO_BOMB:
          putting_bomb = True
    
      if input_action == PlayerKeyMaps.ACTION_BOMB_DOUBLE:  # check multibomb
        if self.has_throwing_glove:
          throwing = True
        elif self.has_multibomb: 
          putting_multibomb = True

      if input_action == PlayerKeyMaps.ACTION_SPECIAL:
        special_was_pressed = True
        
        if not self.wait_for_special_release:       
          while len(self.detonator_bombs) != 0:   # find a bomb to ddetonate (some may have exploded by themselves already)
            bomb_to_check = self.detonator_bombs.pop()
          
            if bomb_to_check.has_detonator() and not bomb_to_check.has_exploded and bomb_to_check.movement != Bomb.BOMB_FLYING:
              game_map.bomb_explodes(bomb_to_check)
              detonator_triggered = True
              self.wait_for_special_release = True    # to not detonate other bombs until the key is released and pressed again
              break
            
          if not detonator_triggered and self.has_boxing_glove:
            self.boxing = True
      
    if not special_was_pressed:
      self.wait_for_special_release = False
      
    if not bomb_was_pressed:
      self.wait_for_bomb_release = False
      
    # resolve collisions:

    check_collisions = True
    collision_happened = False

    current_tile = Positionable.position_to_tile(self.position)
    
    previous_tile = None
    
    if game_map.tile_has_bomb(current_tile):    # first check if the player is standing on a bomb
      previous_tile = Positionable.position_to_tile(previous_position)
      
      if current_tile == previous_tile:         # no transition between tiles -> let the player move
        check_collisions = False

    if check_collisions:
      collision_type = game_map.get_position_collision_type(self.position)
    
      if collision_type == Map.COLLISION_TOTAL:
        self.position = previous_position
        collision_happened = True
      elif collision_type == Map.COLLISION_BORDER_UP:
        if self.state == Player.STATE_WALKING_UP:
          self.position = previous_position
          collision_happened = True
        elif self.state == Player.STATE_WALKING_LEFT or self.state == Player.STATE_WALKING_RIGHT:
          self.position[1] += distance_to_travel
      elif collision_type == Map.COLLISION_BORDER_RIGHT:
        if self.state == Player.STATE_WALKING_RIGHT:
          self.position = previous_position
          collision_happened = True
        elif self.state == Player.STATE_WALKING_UP or self.state == Player.STATE_WALKING_DOWN:
          self.position[0] -= distance_to_travel
      elif collision_type == Map.COLLISION_BORDER_DOWN:
        if self.state == Player.STATE_WALKING_DOWN:
          self.position = previous_position
          collision_happened = True
        elif self.state == Player.STATE_WALKING_LEFT or self.state == Player.STATE_WALKING_RIGHT:
          self.position[1] -= distance_to_travel
      elif collision_type == Map.COLLISION_BORDER_LEFT:
        if self.state == Player.STATE_WALKING_LEFT:
          self.position = previous_position
          collision_happened = True
        elif self.state == Player.STATE_WALKING_UP or self.state == Player.STATE_WALKING_DOWN:
          self.position[0] += distance_to_travel
    
    if putting_bomb and not game_map.tile_has_bomb(Positionable.position_to_tile(self.position)):
      self.lay_bomb(game_map)
    
    # check if bomb kick or box happens
    
    direction_vector = self.get_direction_vector()
    current_tile = Positionable.position_to_tile(self.position)
    forward_tile = (current_tile[0] + direction_vector[0],current_tile[1] + direction_vector[1])
    
    if collision_happened: 
      bomb_movement = Bomb.BOMB_NO_MOVEMENT
    
      if self.state == Player.STATE_WALKING_UP:
        bomb_movement = Bomb.BOMB_ROLLING_UP
      elif self.state == Player.STATE_WALKING_RIGHT:
        bomb_movement = Bomb.BOMB_ROLLING_RIGHT
      elif self.state == Player.STATE_WALKING_DOWN:
        bomb_movement = Bomb.BOMB_ROLLING_DOWN
      else:
        bomb_movement = Bomb.BOMB_ROLLING_LEFT
    
      if self.has_shoe and forward_tile != None:
        if game_map.tile_has_bomb(forward_tile):
          # kick or box happens
          bomb_hit = game_map.bomb_on_tile(forward_tile)
          
          if self.boxing:
            destination_tile = (forward_tile[0] + direction_vector[0] * 3,forward_tile[1] + direction_vector[1] * 3)           
            bomb_hit.send_flying(destination_tile)
          else:
            bomb_hit = game_map.bomb_on_tile(forward_tile)
          
            # align the bomb in case of kicking an already moving bomb:
            bomb_position = bomb_hit.get_position()
          
            if bomb_movement == Bomb.BOMB_ROLLING_LEFT or bomb_movement == Bomb.BOMB_ROLLING_RIGHT:
              bomb_hit.set_position((bomb_position[0],math.floor(bomb_position[1]) + 0.5))
            else:
              bomb_hit.set_position((math.floor(bomb_position[0]) + 0.5,bomb_position[1]))
             
            bomb_hit.movement = bomb_movement
            game_map.add_sound_event(SoundPlayer.SOUND_EVENT_KICK)
    
    if throwing:
      bomb_thrown = game_map.bomb_on_tile(current_tile)
      game_map.add_sound_event(SoundPlayer.SOUND_EVENT_THROW)
    
      if bomb_thrown != None:
        direction_vector = self.get_direction_vector()
        destination_tile = (forward_tile[0] + direction_vector[0] * 3,forward_tile[1] + direction_vector[1] * 3)
        bomb_thrown.send_flying(destination_tile)
        self.wait_for_bomb_release = True
        self.throwing_time_left = 200
    
    elif putting_multibomb:  # put multibomb
      current_tile = Positionable.position_to_tile(self.position)
      
      if self.state in (Player.STATE_WALKING_UP,Player.STATE_IDLE_UP):
        tile_increment = (0,-1)
      elif self.state in (Player.STATE_WALKING_RIGHT,Player.STATE_IDLE_RIGHT):
        tile_increment = (1,0)
      elif self.state in (Player.STATE_WALKING_DOWN,Player.STATE_IDLE_DOWN):
        tile_increment = (0,1)
      else:     # left
        tile_increment = (-1,0)
  
      i = 1
  
      while self.bombs_left > 0:
        next_tile = (current_tile[0] + i * tile_increment[0],current_tile[1] + i * tile_increment[1])
        if not game_map.tile_is_walkable(next_tile) or game_map.tile_has_player(next_tile):
          break
        
        self.lay_bomb(game_map,next_tile)
        i += 1
  
    # check disease:
    
    if self.disease != Player.DISEASE_NONE:
      self.disease_time_left = max(0,self.disease_time_left - dt)
      
      if self.disease_time_left == 0:
        self.disease = Player.DISEASE_NONE
    
    if old_state == self.state:
      self.state_time += dt
    else:
      self.state_time = 0       # reset the state time

## Info about a bomb's flight (when boxed or thrown).

class BombFlightInfo(object):
  def __init__(self):
    self.total_distance_to_travel = 0     ##< in tiles
    self.distance_travelled = 0           ##< in tiles
    self.direction = (0,0)                ##< in which direction the bomb is flying, 0, 1 or -1

class Bomb(Positionable):
  ROLLING_SPEED = 4
  FLYING_SPEED = 5
  
  BOMB_ROLLING_UP = 0
  BOMB_ROLLING_RIGHT = 1
  BOMB_ROLLING_DOWN = 2
  BOMB_ROLLING_LEFT = 3
  BOMB_FLYING = 4
  BOMB_NO_MOVEMENT = 5
  
  DETONATOR_EXPIRATION_TIME = 20000
  
  def __init__(self, player):
    super(Bomb,self).__init__()
    self.time_of_existence = 0                       ##< for how long (in ms) the bomb has existed
    self.flame_length = player.get_flame_length()    ##< how far the flame will go
    self.player = player                             ##< to which player the bomb belongs
    self.explodes_in = 3000                          ##< time in ms in which the bomb exploded from the time it was created (detonator_time_left must expire before this starts counting down)
    self.detonator_time_left = 0                     ##< if > 0, the bomb has a detonator on it, after expiring it becomes a regular bomb
    self.set_position(player.get_position())
    self.move_to_tile_center()
    self.has_spring = player.bombs_have_spring()
    self.movement = Bomb.BOMB_NO_MOVEMENT
    self.has_exploded = False
    self.flight_info = BombFlightInfo()
    
  ## Sends the bomb flying from its currents position to given tile (can be outside the map boundaries, will fly over the border from the other side).
    
  def send_flying(self, destination_tile_coords):
    self.movement = Bomb.BOMB_FLYING

    current_tile = Positionable.position_to_tile(self.position)
    self.flight_info.distance_travelled = 0
    
    if current_tile[0] == destination_tile_coords[0]:
      self.flight_info.total_distance_to_travel = abs(current_tile[1] - destination_tile_coords[1])
      
      if current_tile[1] > destination_tile_coords[1]:   # up
        self.flight_info.direction = (0,-1) 
      else:                                              # down
        self.flight_info.direction = (0,1)
    else:
      self.flight_info.total_distance_to_travel = abs(current_tile[0] - destination_tile_coords[0])
      
      if current_tile[0] < destination_tile_coords[0]:   # right
        self.flight_info.direction = (1,0)
      else:                                              # left
        self.flight_info.direction = (-1,0)

    destination_tile_coords = (destination_tile_coords[0] % Map.MAP_WIDTH,destination_tile_coords[1] % Map.MAP_HEIGHT)
    self.move_to_tile_center(destination_tile_coords)

  def has_detonator(self):
    return self.detonator_time_left > 0 and self.time_of_existence < Bomb.DETONATOR_EXPIRATION_TIME

  def exploded(self):
    if not self.has_exploded:
      self.player.bomb_exploded()
      self.has_exploded = True

## Represents a flame coming off of an exploding bomb.

class Flame(object):
  def __init__(self):
    self.player = None          ##< reference to player to which the exploding bomb belonged
    self.time_to_burnout = 1000 ##< time in ms till the flame disappears
    self.direction = "all"      ##< string representation of the flame direction

class MapTile(object):
  TILE_FLOOR = 0                ##< walkable map tile
  TILE_BLOCK = 1                ##< non-walkable but destroyable map tile
  TILE_WALL = 2                 ##< non-walkable and non-destroyable map tile
  
  SPECIAL_OBJECT_TRAMPOLINE = 0
  SPECIAL_OBJECT_TELEPORT_A = 1
  SPECIAL_OBJECT_TELEPORT_B = 2
  
  def __init__(self, coordinates):
    self.kind = MapTile.TILE_FLOOR
    self.flames = []
    self.coordinates = coordinates
    self.to_be_destroyed = False   ##< Flag that marks the tile to be destroyed after the flames go out.
    self.item = None               ##< Item that's present on the file
    self.special_object = None     ##< special object present on the tile, like trampoline or teleport

## Holds and manipulates the map data including the players, bombs etc.

class Map(object):
  MAP_WIDTH = 15
  MAP_HEIGHT = 11
  WALL_MARGIN_HORIZONTAL = 0.2
  WALL_MARGIN_VERTICAL = 0.4
  
  COLLISION_BORDER_UP = 0       ##< position is inside upper border with non-walkable tile
  COLLISION_BORDER_RIGHT = 1    ##< position is inside right border with non-walkable tile
  COLLISION_BORDER_DOWN = 2     ##< position is inside bottom border with non-walkable tile
  COLLISION_BORDER_LEFT = 3     ##< position is inside left border with non-walkable tile
  COLLISION_TOTAL = 4           ##< position is inside non-walkable tile
  COLLISION_NONE = 5            ##< no collision

  ITEM_BOMB = 0
  ITEM_FLAME = 1
  ITEM_SUPERFLAME = 2
  ITEM_SPEEDUP = 3
  ITEM_DISEASE = 4
  ITEM_RANDOM = 5
  ITEM_SPRING = 6
  ITEM_SHOE = 7
  ITEM_MULTIBOMB = 8
  ITEM_BOXING_GLOVE = 9
  ITEM_DETONATOR = 10
  ITEM_THROWING_GLOVE = 11
  
  ## Initialises a new map from map_data (string) and a PlaySetup object.

  def __init__(self, map_data, play_setup):
    # make the tiles array:
    self.tiles = []
    starting_positions = [(0.0,0.0) for i in range(10)]      # starting position for each player

    map_data = map_data.replace(" ","").replace("\n","")     # get rid of white characters

    string_split = map_data.split(";")

    self.environment_name = string_split[0]

    block_tiles = []

    line = -1
    column = 0

    for i in range(len(string_split[3])):
      tile_character = string_split[3][i]

      if i % Map.MAP_WIDTH == 0:                             # add new row
        line += 1
        column = 0
        self.tiles.append([])

      tile = MapTile((column,line))

      if tile_character == "x":
        tile.kind = MapTile.TILE_BLOCK
        block_tiles.append(tile)
      elif tile_character == "#":
        tile.kind = MapTile.TILE_WALL
      else:
        tile.kind = MapTile.TILE_FLOOR
        
        if tile_character == "A":
          tile.special_object = MapTile.SPECIAL_OBJECT_TELEPORT_A
        elif tile_character == "B":
          tile.special_object = MapTile.SPECIAL_OBJECT_TELEPORT_A
        elif tile_character == "T":
          tile.special_object = MapTile.SPECIAL_OBJECT_TRAMPOLINE

      self.tiles[-1].append(tile)

      if tile_character.isdigit():
        starting_positions[int(tile_character)] = (float(column),float(line))

      column += 1

    # place items on under block tiles:
    
    for i in range(len(string_split[2])):
      random_tile = random.choice(block_tiles)
      random_tile.item = self.letter_to_item(string_split[2][i])
      block_tiles.remove(random_tile)

    # initialise players:

    self.players = []                                        ##< list of players in the game
    self.players_by_numbers = {}                             ##< mapping of numbers to players
    self.players_by_numbers[-1] = None

    player_slots = play_setup.get_slots()

    for i in range(len(player_slots)):
      if player_slots[i] != None:
        new_player = Player()
        new_player.set_number(i)
        new_player.move_to_tile_center(starting_positions[i])
        self.players.append(new_player)
        self.players_by_numbers[i] = new_player
      else:
        self.players_by_numbers[i] = None
        
    # give players starting items:
    
    for i in range(len(string_split[1])):
      for player in self.players:
        player.give_item(self.letter_to_item(string_split[1][i]))
        
    self.bombs = []                           ##< bombs on the map

    self.sound_events = []         ##< list of currently happening sound event (see SoundPlayer class)

  def add_sound_event(self, sound_event):
    self.sound_events.append(sound_event)
    
  def get_tile_at(self, tile_coordinates):
    if self.tile_is_withing_map(tile_coordinates):
      return self.tiles[tile_coordinates[1]][tile_coordinates[0]]
    
    return None
    
  def get_and_clear_sound_events(self):
    result = self.sound_events[:]      # copy of the list
    self.sound_events = []
    return result

  ## Converts given letter (as in map encoding string) to item code (see class constants).
  def letter_to_item(self, letter):
    if letter == "f":
      return Map.ITEM_FLAME
    elif letter == "F":
      return Map.ITEM_SUPERFLAME
    elif letter == "b":
      return Map.ITEM_BOMB
    elif letter == "k":
      return Map.ITEM_SHOE
    elif letter == "s":
      return Map.ITEM_SPEEDUP
    elif letter == "p":
      return Map.ITEM_SPRING
    elif letter == "d":
      return Map.ITEM_DISEASE
    elif letter == "m":
      return Map.ITEM_MULTIBOMB
    elif letter == "r":
      return Map.ITEM_RANDOM
    elif letter == "x":
      return Map.ITEM_BOXING_GLOVE
    elif letter == "e":
      return Map.ITEM_DETONATOR
    elif letter == "t":
      return Map.ITEM_THROWING_GLOVE
    else:
      return -1

  def tile_has_flame(self, tile_coordinates):
    if not self.tile_is_withing_map(tile_coordinates):
      return False     # coordinates outside the map
    
    return len(self.tiles[tile_coordinates[1]][tile_coordinates[0]].flames) >= 1

  def bomb_on_tile(self, tile_coordinates):
    bombs = self.bombs_on_tile(tile_coordinates)
    
    if len(bombs) > 0:
      return bombs[0]
    
    return None

  ## Checks if there is a bomb at given tile (coordinates may be float or int).

  def tile_has_bomb(self, tile_coordinates):
    return self.bomb_on_tile(tile_coordinates) != None

  def tile_has_player(self, tile_coordinates):
    tile_coordinates = Positionable.position_to_tile(tile_coordinates)
    
    for player in self.players:
      player_tile_position = Positionable.position_to_tile(player.get_position())

      if not player.is_in_air() and player_tile_position[0] == tile_coordinates[0] and player_tile_position[1] == tile_coordinates[1]:
        return True
    
    return False

  ## Checks if given tile coordinates are within the map boundaries.

  def tile_is_withing_map(self, tile_coordinates):
    return tile_coordinates[0] >= 0 and tile_coordinates[1] >= 0 and tile_coordinates[0] <= Map.MAP_WIDTH - 1 and tile_coordinates[1] <= Map.MAP_HEIGHT - 1

  def tile_is_walkable(self, tile_coordinates):
    if not self.tile_is_withing_map(tile_coordinates):
      return False
    
    tile = self.tiles[tile_coordinates[1]][tile_coordinates[0]]
    return self.tile_is_withing_map(tile_coordinates) and (self.tiles[tile_coordinates[1]][tile_coordinates[0]].kind == MapTile.TILE_FLOOR or tile.to_be_destroyed) and not self.tile_has_bomb(tile_coordinates)

  ## Gets a collision type (see class constants) for give float position.

  def get_position_collision_type(self, position):
    tile_coordinates = Positionable.position_to_tile(position)
    
    if not self.tile_is_walkable(tile_coordinates):
      return Map.COLLISION_TOTAL
    
    position_within_tile = (position[0] % 1,position[1] % 1)
    
    if position_within_tile[1] < Map.WALL_MARGIN_HORIZONTAL:
      if not self.tile_is_walkable((tile_coordinates[0],tile_coordinates[1] - 1)):
        return Map.COLLISION_BORDER_UP
    elif position_within_tile[1] > 1.0 - Map.WALL_MARGIN_HORIZONTAL:
      if not self.tile_is_walkable((tile_coordinates[0],tile_coordinates[1] + 1)):
        return Map.COLLISION_BORDER_DOWN
      
    if position_within_tile[0] < Map.WALL_MARGIN_VERTICAL:
      if not self.tile_is_walkable((tile_coordinates[0] - 1,tile_coordinates[1])):
        return Map.COLLISION_BORDER_LEFT
    elif position_within_tile[0] > 1.0 - Map.WALL_MARGIN_VERTICAL:
      if not self.tile_is_walkable((tile_coordinates[0] + 1,tile_coordinates[1])):
        return Map.COLLISION_BORDER_RIGHT
    
    return Map.COLLISION_NONE

  def bombs_on_tile(self, tile_coordinates):
    result = []
    
    tile_coordinates = Positionable.position_to_tile(tile_coordinates)
    
    for bomb in self.bombs:
      bomb_tile_position = Positionable.position_to_tile(bomb.get_position())

      if bomb.movement != Bomb.BOMB_FLYING and bomb_tile_position[0] == tile_coordinates[0] and bomb_tile_position[1] == tile_coordinates[1]:
        result.append(bomb)
      
    return result

  ## Tells the map that given bomb is exploding, the map then creates
  #  flames from the bomb, the bomb is destroyed and players are informed.

  def bomb_explodes(self, bomb):
    if bomb.movement == Bomb.BOMB_FLYING:
      return
    
    self.add_sound_event(SoundPlayer.SOUND_EVENT_EXPLOSION)
    
    bomb_position = Positionable.position_to_tile(bomb.get_position())
    
    new_flame = Flame()
    new_flame.direction = "all"
    
    self.tiles[bomb_position[1]][bomb_position[0]].flames.append(new_flame)
    
    # information relevant to flame spreading in each direction:
    
                     # up                    right                down                 left
    axis_position    = [bomb_position[1] - 1,bomb_position[0] + 1,bomb_position[1] + 1,bomb_position[0] - 1]
    flame_stop       = [False,               False,               False,               False]
    map_limit        = [0,                   Map.MAP_WIDTH - 1,   Map.MAP_HEIGHT - 1,  0]
    increment        = [-1,                  1,                   1,                   -1]
    goes_horizontaly = [False,               True,                False,               True]
    previous_flame   = [None,                None,                None,                None]
    
    # spread the flame in all 4 directions:

    for i in range(bomb.flame_length + 1):
      if i >= bomb.flame_length:
        flame_stop = [True, True, True, True]

      for direction in (0,1,2,3): # for each direction
        if flame_stop[direction]:  
          if previous_flame[direction] != None:   # flame stopped in previous iteration
          
            if direction == 0:
              previous_flame[direction].direction = "up"
            elif direction == 1:
              previous_flame[direction].direction = "right"
            elif direction == 2:
              previous_flame[direction].direction = "down"
            else:
              previous_flame[direction].direction = "left"
          
            previous_flame[direction] = None
        else:
          if ((increment[direction] == -1 and axis_position[direction] >= map_limit[direction]) or
            (increment[direction] == 1 and axis_position[direction] <= map_limit[direction])):
            # flame is inside the map here          
        
            if goes_horizontaly[direction]:
              tile_for_flame = self.tiles[bomb_position[1]][axis_position[direction]]
            else:
              tile_for_flame = self.tiles[axis_position[direction]][bomb_position[0]]
        
            if tile_for_flame.kind == MapTile.TILE_WALL:
              flame_stop[direction] = True
            else:
              new_flame2 = copy.copy(new_flame)
              new_flame2.direction = "horizontal" if goes_horizontaly[direction] else "vertical"
              tile_for_flame.flames.append(new_flame2)
            
              previous_flame[direction] = new_flame2
            
              if tile_for_flame.kind == MapTile.TILE_BLOCK:
                flame_stop[direction] = True
          else:
            flame_stop[direction] = True
          
        axis_position[direction] += increment[direction]
    
    bomb.exploded()
   
    if bomb in self.bombs:
      self.bombs.remove(bomb)

  ## Updates some things on the map that change with time.

  def update(self, dt):
    i = 0
    
    while i <= len(self.bombs) - 1:    # update all bombs
      bomb = self.bombs[i]
      
      if bomb.has_exploded:            # just in case
        self.bombs.remove(bomb)
        continue
      
      bomb.time_of_existence += dt
      
      if bomb.time_of_existence > bomb.explodes_in + bomb.detonator_time_left: # bomb explodes
        self.bomb_explodes(bomb)
      else:
        i += 1
        
      if bomb.movement != Bomb.BOMB_NO_MOVEMENT:
        if bomb.movement == Bomb.BOMB_FLYING:
          distance_to_travel = dt / 1000.0 * Bomb.FLYING_SPEED
          bomb.flight_info.distance_travelled += distance_to_travel
          
          if bomb.flight_info.distance_travelled >= bomb.flight_info.total_distance_to_travel:
            bomb_tile = Positionable.position_to_tile(bomb.get_position())
            self.add_sound_event(SoundPlayer.SOUND_EVENT_BOMB_PUT)

            if not self.tile_is_walkable(bomb_tile) or self.tile_has_player(bomb_tile):
              destination_tile = (bomb_tile[0] + bomb.flight_info.direction[0],bomb_tile[1] + bomb.flight_info.direction[1])
              bomb.send_flying(destination_tile)
            else:  # bomb lands
              bomb.movement = Bomb.BOMB_NO_MOVEMENT
              self.get_tile_at(bomb_tile).item = None
              
        else:            # bomb rolling
          bomb_position = bomb.get_position()
          bomb_tile = Positionable.position_to_tile(bomb_position)
        
          if self.tiles[bomb_tile[1]][bomb_tile[0]].item != None:   # rolling bomb destroys items
            self.tiles[bomb_tile[1]][bomb_tile[0]].item = None
        
          bomb_position_within_tile = (bomb_position[0] % 1,bomb_position[1] % 1) 
          check_collision = False
          forward_tile = None
          distance_to_travel = dt / 1000.0 * Bomb.ROLLING_SPEED
          
          helper_boundaries = (0.5,0.9)
          helper_boundaries2 = (1 - helper_boundaries[1],1 - helper_boundaries[0])
        
          opposite_direction = Bomb.BOMB_NO_MOVEMENT
        
          if bomb.movement == Bomb.BOMB_ROLLING_UP:
            bomb.set_position((bomb_position[0],bomb_position[1] - distance_to_travel))
            opposite_direction = Bomb.BOMB_ROLLING_DOWN
        
            if helper_boundaries2[0] < bomb_position_within_tile[1] < helper_boundaries2[1]:
              check_collision = True
              forward_tile = (bomb_tile[0],bomb_tile[1] - 1)
        
          elif bomb.movement == Bomb.BOMB_ROLLING_RIGHT:
            bomb.set_position((bomb_position[0] + distance_to_travel,bomb_position[1]))
            opposite_direction = Bomb.BOMB_ROLLING_LEFT
          
            if helper_boundaries[0] < bomb_position_within_tile[0] < helper_boundaries[1]:
              check_collision = True
              forward_tile = (bomb_tile[0] + 1,bomb_tile[1])
          
          elif bomb.movement == Bomb.BOMB_ROLLING_DOWN:
            bomb.set_position((bomb_position[0],bomb_position[1] + distance_to_travel))
            opposite_direction = Bomb.BOMB_ROLLING_UP
          
            if helper_boundaries[0] < bomb_position_within_tile[1] < helper_boundaries[1]:
              check_collision = True
              forward_tile = (bomb_tile[0],bomb_tile[1] + 1)
          
          elif bomb.movement == Bomb.BOMB_ROLLING_LEFT:
            bomb.set_position((bomb_position[0] - distance_to_travel,bomb_position[1]))        
            opposite_direction = Bomb.BOMB_ROLLING_RIGHT

            if helper_boundaries2[0] < bomb_position_within_tile[0] < helper_boundaries2[1]:
              check_collision = True
              forward_tile = (bomb_tile[0] - 1,bomb_tile[1])

          if check_collision and (not self.tile_is_walkable(forward_tile) or self.tile_has_player(forward_tile)):
            bomb.move_to_tile_center()          
          
            if bomb.has_spring:
              bomb.movement = opposite_direction
              self.add_sound_event(SoundPlayer.SOUND_EVENT_SPRING)
            else:
              bomb.movement = Bomb.BOMB_NO_MOVEMENT
              self.add_sound_event(SoundPlayer.SOUND_EVENT_KICK)

    for line in self.tiles:
      for tile in line:
        if tile.to_be_destroyed and tile.kind == MapTile.TILE_BLOCK and not self.tile_has_flame(tile.coordinates):
          tile.kind = MapTile.TILE_FLOOR
          tile.to_be_destroyed = False
        
        i = 0
        
        while True:
          if i >= len(tile.flames):
            break
          
          if tile.kind == MapTile.TILE_BLOCK:  # flame on a block tile -> destroy the block
            tile.to_be_destroyed = True
          elif tile.kind == MapTile.TILE_FLOOR and tile.item != None:
            tile.item = None                   # flame destroys the item
          
          bombs_inside_flame = self.bombs_on_tile(tile.coordinates)
          
          for bomb in bombs_inside_flame:      # bomb inside flame -> detonate it
            self.bomb_explodes(bomb)
          
          flame = tile.flames[i]
          
          flame.time_to_burnout -= dt
          
          if flame.time_to_burnout < 0:
            tile.flames.remove(flame)
      
          i += 1
    
    for player in self.players:
      player_tile_position = Positionable.position_to_tile(player.get_position())
      player_tile = self.tiles[player_tile_position[1]][player_tile_position[0]]
      
      if player_tile.item != None:
        player.give_item(player_tile.item,self)
        player_tile.item = None
      
      if player.is_in_air():
        if player.get_state_time() > Player.JUMP_DURATION / 2:  # jump to destination tile in the middle of the flight
          player.move_to_tile_center(player.get_jump_destination())
      
      elif player_tile.special_object == MapTile.SPECIAL_OBJECT_TRAMPOLINE and player.is_near_tile_center():
        player.send_to_air(self)
      
  def add_bomb(self, bomb):
    self.bombs.append(bomb)

  def get_bombs(self):
    return self.bombs

  def get_environment_name(self):
    return self.environment_name

  def get_players(self):
    return self.players

  ## Gets a dict that maps numbers to players (with Nones if player with given number doesn't exist).

  def get_players_by_numbers(self):
    return self.players_by_numbers

  def get_tiles(self):
    return self.tiles

  def __str__(self):
    result = ""

    for line in self.tiles:
      for tile in line:
        if tile.kind == MapTile.TILE_FLOOR:
          result += " "
        elif tile.kind == MapTile.TILE_BLOCK:
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

  def get_slots(self):
    return self.player_slots

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
  ACTION_BOMB_DOUBLE = 7
  
  MOUSE_CONTROL_UP = -1
  MOUSE_CONTROL_RIGHT = -2
  MOUSE_CONTROL_DOWN = -3
  MOUSE_CONTROL_LEFT = -4
  MOUSE_CONTROL_BUTTON_L = -5
  MOUSE_CONTROL_BUTTON_M = -6
  MOUSE_CONTROL_BUTTON_R = -7
  
  MOUSE_CONTROL_SMOOTH_OUT_TIME = 350

  def __init__(self):
    self.key_maps = {}  ##< maps keys to tuples of a format: (player_number, action), for general actions player_number will be -1
    
    self.bomb_key_last_pressed_time = [0 for i in range(10)]  ##< for bomb double press detection
    self.bomb_key_previous_state = [False for i in range(10)] ##< for bomb double press detection

    self.allow_mouse_control = False       ##< if true, player movement by mouse is allowed, otherwise not

    mouse_control_constants = [
      PlayerKeyMaps.MOUSE_CONTROL_UP,
      PlayerKeyMaps.MOUSE_CONTROL_RIGHT,
      PlayerKeyMaps.MOUSE_CONTROL_DOWN,
      PlayerKeyMaps.MOUSE_CONTROL_LEFT,
      PlayerKeyMaps.MOUSE_CONTROL_BUTTON_L,
      PlayerKeyMaps.MOUSE_CONTROL_BUTTON_M,
      PlayerKeyMaps.MOUSE_CONTROL_BUTTON_R]

    self.mouse_control_states = {}
    self.mouse_control_keep_until = {} ## time in which specified control was activated, helps keeping them active for a certain amount of time to smooth them out 

    mouse_control_states = {
      PlayerKeyMaps.MOUSE_CONTROL_UP : False,
      PlayerKeyMaps.MOUSE_CONTROL_RIGHT : False,
      PlayerKeyMaps.MOUSE_CONTROL_DOWN : False,
      PlayerKeyMaps.MOUSE_CONTROL_LEFT : False,
      PlayerKeyMaps.MOUSE_CONTROL_BUTTON_L : False,
      PlayerKeyMaps.MOUSE_CONTROL_BUTTON_M : False,
      PlayerKeyMaps.MOUSE_CONTROL_BUTTON_R : False
      }

    for item in mouse_control_constants:
      self.mouse_control_states[item] = False
      self.mouse_control_keep_until[item] = 0

  ## Sets a key mapping for a player of specified (non-negative) number.

  def set_player_key_map(self, player_number, key_up, key_right, key_down, key_left, key_bomb, key_special):
    self.key_maps[key_up]      = (player_number,PlayerKeyMaps.ACTION_UP)
    self.key_maps[key_right]   = (player_number,PlayerKeyMaps.ACTION_RIGHT)
    self.key_maps[key_down]    = (player_number,PlayerKeyMaps.ACTION_DOWN)
    self.key_maps[key_left]    = (player_number,PlayerKeyMaps.ACTION_LEFT)
    self.key_maps[key_bomb]    = (player_number,PlayerKeyMaps.ACTION_BOMB)
    self.key_maps[key_special] = (player_number,PlayerKeyMaps.ACTION_SPECIAL)

  def allow_control_by_mouse(self, allow=True):
   self.allow_mouse_control = allow

  def set_special_key_map(self, key_menu):
    self.key_maps[key_menu]      = (-1,PlayerKeyMaps.ACTION_MENU)

  ## From currently pressed keys makes a list of actions being currently performed and returns it, format: (player_number, action).

  def get_current_actions(self):
    keys_pressed = pygame.key.get_pressed()

    result = []

    reset_bomb_key_previous_state = [True for i in range(10)]

    # check mouse control:

    if self.allow_mouse_control:
      screen_center = (Renderer.SCREEN_WIDTH / 2,Renderer.SCREEN_HEIGHT / 2)
      mouse_position = pygame.mouse.get_pos(screen_center)
      pressed = pygame.mouse.get_pressed()
      
      current_time = pygame.time.get_ticks()
      
      for item in self.mouse_control_states:    # reset
        if current_time > self.mouse_control_keep_until[item]:
          self.mouse_control_states[item] = False
      
      dx = abs(mouse_position[0] - screen_center[0])
      dy = abs(mouse_position[1] - screen_center[1])
      
      if dx > dy:  # choose the prevelant axis
        if mouse_position[0] > screen_center[0]:
          self.mouse_control_states[PlayerKeyMaps.MOUSE_CONTROL_RIGHT] = True
          self.mouse_control_states[PlayerKeyMaps.MOUSE_CONTROL_LEFT] = False          
          self.mouse_control_keep_until[PlayerKeyMaps.MOUSE_CONTROL_RIGHT] = current_time + PlayerKeyMaps.MOUSE_CONTROL_SMOOTH_OUT_TIME
        elif mouse_position[0] < screen_center[0]:
          self.mouse_control_states[PlayerKeyMaps.MOUSE_CONTROL_LEFT] = True
          self.mouse_control_states[PlayerKeyMaps.MOUSE_CONTROL_RIGHT] = False
          self.mouse_control_keep_until[PlayerKeyMaps.MOUSE_CONTROL_LEFT] = current_time + PlayerKeyMaps.MOUSE_CONTROL_SMOOTH_OUT_TIME
      else:
        if mouse_position[1] < screen_center[1]:
          self.mouse_control_states[PlayerKeyMaps.MOUSE_CONTROL_UP] = True
          self.mouse_control_states[PlayerKeyMaps.MOUSE_CONTROL_DOWN] = False
          self.mouse_control_keep_until[PlayerKeyMaps.MOUSE_CONTROL_UP] = current_time + PlayerKeyMaps.MOUSE_CONTROL_SMOOTH_OUT_TIME
        elif mouse_position[1] > screen_center[1]:
          self.mouse_control_states[PlayerKeyMaps.MOUSE_CONTROL_DOWN] = True
          self.mouse_control_states[PlayerKeyMaps.MOUSE_CONTROL_UP] = False
          self.mouse_control_keep_until[PlayerKeyMaps.MOUSE_CONTROL_DOWN] = current_time + PlayerKeyMaps.MOUSE_CONTROL_SMOOTH_OUT_TIME
        
      if pressed[0]:
        self.mouse_control_states[PlayerKeyMaps.MOUSE_CONTROL_BUTTON_L] = True
        self.mouse_control_keep_until[PlayerKeyMaps.MOUSE_CONTROL_BUTTON_L] = current_time# + PlayerKeyMaps.MOUSE_CONTROL_SMOOTH_OUT_TIME
          
      if pressed[1]:
        self.mouse_control_states[PlayerKeyMaps.MOUSE_CONTROL_BUTTON_M] = True
        self.mouse_control_keep_until[PlayerKeyMaps.MOUSE_CONTROL_BUTTON_M] = current_time# + PlayerKeyMaps.MOUSE_CONTROL_SMOOTH_OUT_TIME
      
      if pressed[2]:
        self.mouse_control_states[PlayerKeyMaps.MOUSE_CONTROL_BUTTON_R] = True
        self.mouse_control_keep_until[PlayerKeyMaps.MOUSE_CONTROL_BUTTON_R] = current_time# + PlayerKeyMaps.MOUSE_CONTROL_SMOOTH_OUT_TIME
      
      pygame.mouse.set_pos(screen_center)

    for key_code in self.key_maps:
      key_is_active = self.mouse_control_states[key_code] if key_code < 0 else keys_pressed[key_code]
      
      if key_is_active:
        action_tuple = self.key_maps[key_code]  
        result.append(action_tuple)
        
        if action_tuple[1] == PlayerKeyMaps.ACTION_BOMB:
          player_number = action_tuple[0]
          
          if self.bomb_key_previous_state[player_number] == False and pygame.time.get_ticks() - self.bomb_key_last_pressed_time[player_number] < 200:
            result.append((player_number,PlayerKeyMaps.ACTION_BOMB_DOUBLE))
          
          self.bomb_key_last_pressed_time[player_number] = pygame.time.get_ticks()
          self.bomb_key_previous_state[player_number] = True
          reset_bomb_key_previous_state[player_number] = False

    for i in range(10):
      if reset_bomb_key_previous_state[i]:
        self.bomb_key_previous_state[i] = False

    return result

class SoundPlayer(object):
  # sound events used by other classes to tell soundplayer what to play:
  
  SOUND_EVENT_EXPLOSION = 0
  SOUND_EVENT_BOMB_PUT = 1
  SOUND_EVENT_WALK = 2
  SOUND_EVENT_KICK = 3
  SOUND_EVENT_DIARRHEA = 4
  SOUND_EVENT_SPRING = 5
  SOUND_EVENT_SLOW = 6
  SOUND_EVENT_DISEASE = 7
  SOUND_EVENT_CLICK = 8
  SOUND_EVENT_THROW = 9
  SOUND_EVENT_TRAMPOLINE = 10
  
  def __init__(self):
    pygame.mixer.init()
    
    self.sound = {}
    self.sound[SoundPlayer.SOUND_EVENT_EXPLOSION] = pygame.mixer.Sound(os.path.join(RESOURCE_PATH,"explosion.wav"))
    self.sound[SoundPlayer.SOUND_EVENT_BOMB_PUT] = pygame.mixer.Sound(os.path.join(RESOURCE_PATH,"bomb.wav"))
    self.sound[SoundPlayer.SOUND_EVENT_WALK] = pygame.mixer.Sound(os.path.join(RESOURCE_PATH,"footsteps.wav"))
    self.sound[SoundPlayer.SOUND_EVENT_KICK] = pygame.mixer.Sound(os.path.join(RESOURCE_PATH,"kick.wav"))
    self.sound[SoundPlayer.SOUND_EVENT_SPRING] = pygame.mixer.Sound(os.path.join(RESOURCE_PATH,"spring.wav"))
    self.sound[SoundPlayer.SOUND_EVENT_DIARRHEA] = pygame.mixer.Sound(os.path.join(RESOURCE_PATH,"fart.wav"))
    self.sound[SoundPlayer.SOUND_EVENT_SLOW] = pygame.mixer.Sound(os.path.join(RESOURCE_PATH,"slow.wav"))
    self.sound[SoundPlayer.SOUND_EVENT_DISEASE] = pygame.mixer.Sound(os.path.join(RESOURCE_PATH,"disease.wav"))
    self.sound[SoundPlayer.SOUND_EVENT_CLICK] = pygame.mixer.Sound(os.path.join(RESOURCE_PATH,"click.wav"))
    self.sound[SoundPlayer.SOUND_EVENT_THROW] = pygame.mixer.Sound(os.path.join(RESOURCE_PATH,"throw.wav"))
    self.sound[SoundPlayer.SOUND_EVENT_TRAMPOLINE] = pygame.mixer.Sound(os.path.join(RESOURCE_PATH,"trampoline.wav"))
    
    self.playing_walk = False
    self.kick_last_played_time = 0
    
  ## Processes a list of sound events (see class constants) by playing
  #  appropriate sounds.
    
  def process_events(self, sound_event_list): 
    stop_playing_walk = True
    
    for sound_event in sound_event_list:
      if sound_event in (          # simple sound play
        SoundPlayer.SOUND_EVENT_EXPLOSION,
        SoundPlayer.SOUND_EVENT_CLICK,
        SoundPlayer.SOUND_EVENT_BOMB_PUT,
        SoundPlayer.SOUND_EVENT_SPRING,
        SoundPlayer.SOUND_EVENT_DIARRHEA,
        SoundPlayer.SOUND_EVENT_SLOW,
        SoundPlayer.SOUND_EVENT_DISEASE,
        SoundPlayer.SOUND_EVENT_THROW,
        SoundPlayer.SOUND_EVENT_TRAMPOLINE
        ):
        self.sound[sound_event].play()
    
      elif sound_event == SoundPlayer.SOUND_EVENT_WALK:
        if not self.playing_walk:
          self.sound[SoundPlayer.SOUND_EVENT_WALK].play(loops=-1)
          self.playing_walk = True
        
        stop_playing_walk = False
      elif sound_event == SoundPlayer.SOUND_EVENT_KICK:
        time_now = pygame.time.get_ticks()
        
        if time_now > self.kick_last_played_time + 200: # wait 200 ms before playing kick sound again        
          self.sound[SoundPlayer.SOUND_EVENT_KICK].play()
          self.kick_last_played_time = time_now
      
    if self.playing_walk and stop_playing_walk:
      self.sound[SoundPlayer.SOUND_EVENT_WALK].stop()
      self.playing_walk = False
    
  #  if not self.playing_walk = False
    
class Renderer(object):
  MAP_TILE_WIDTH = 50              ##< tile width in pixels
  MAP_TILE_HEIGHT = 45             ##< tile height in pixels
  MAP_TILE_HALF_WIDTH = MAP_TILE_WIDTH / 2
  MAP_TILE_HALF_HEIGHT = MAP_TILE_HEIGHT / 2
  SCREEN_WIDTH = 800
  SCREEN_HEIGHT = 600

  PLAYER_SPRITE_CENTER = (30,80)   ##< player's feet (not geometrical) center of the sprite in pixels
  BOMB_SPRITE_CENTER = (22,33)
  SHADOW_SPRITE_CENTER = (25,22)

  MAP_BORDER_WIDTH = 10

  def __init__(self):
    self.screen_resolution = (Renderer.SCREEN_WIDTH,Renderer.SCREEN_HEIGHT)

    self.environment_images = {}

    environment_names = ["env1","env2","env3","env4","env5"]

    for environment_name in environment_names:
      filename_floor = os.path.join(RESOURCE_PATH,"tile_" + environment_name + "_floor.png")
      filename_block = os.path.join(RESOURCE_PATH,"tile_" + environment_name + "_block.png")
      filename_wall = os.path.join(RESOURCE_PATH,"tile_" + environment_name + "_wall.png")

      self.environment_images[environment_name] = (pygame.image.load(filename_floor),pygame.image.load(filename_block),pygame.image.load(filename_wall))

    self.prerendered_map = None     # keeps a reference to a map for which some parts have been prerendered
    self.prerendered_map_background = pygame.Surface((Map.MAP_WIDTH * Renderer.MAP_TILE_WIDTH + 2 * Renderer.MAP_BORDER_WIDTH,Map.MAP_HEIGHT * Renderer.MAP_TILE_HEIGHT + 2 * Renderer.MAP_BORDER_WIDTH))

    self.player_images = []         ##< player images in format [color index]["sprite name"] and [color index]["sprite name"][frame]

    for i in range(10):
      self.player_images.append({})
      
      for helper_string in ["up","right","down","left"]:
        self.player_images[-1][helper_string] =  self.color_surface(pygame.image.load(os.path.join(RESOURCE_PATH,"player_" + helper_string + ".png")),i)
        
        string_index = "walk " + helper_string
      
        self.player_images[-1][string_index] = []
        self.player_images[-1][string_index].append(self.color_surface(pygame.image.load(os.path.join(RESOURCE_PATH,"player_" + helper_string + "_walk1.png")),i))
        
        if helper_string == "up" or helper_string == "down":
          self.player_images[-1][string_index].append(self.color_surface(pygame.image.load(os.path.join(RESOURCE_PATH,"player_" + helper_string + "_walk2.png")),i))
        else:
          self.player_images[-1][string_index].append(self.player_images[-1][helper_string])
        
        self.player_images[-1][string_index].append(self.color_surface(pygame.image.load(os.path.join(RESOURCE_PATH,"player_" + helper_string + "_walk3.png")),i))
        self.player_images[-1][string_index].append(self.player_images[-1][string_index][0])
        
        string_index = "box " + helper_string
        self.player_images[-1][string_index] = self.color_surface(pygame.image.load(os.path.join(RESOURCE_PATH,"player_" + helper_string + "_box.png")),i)
     
    self.bomb_images = []
    self.bomb_images.append(pygame.image.load(os.path.join(RESOURCE_PATH,"bomb1.png")))
    self.bomb_images.append(pygame.image.load(os.path.join(RESOURCE_PATH,"bomb2.png")))
    self.bomb_images.append(pygame.image.load(os.path.join(RESOURCE_PATH,"bomb3.png")))
    self.bomb_images.append(self.bomb_images[0])
     
    # load flame images:
    self.flame_images = []
    
    for i in [1,2]:
      helper_string = "flame" + str(i)
      
      self.flame_images.append({})
      self.flame_images[-1]["all"] = pygame.image.load(os.path.join(RESOURCE_PATH,helper_string + ".png"))
      self.flame_images[-1]["horizontal"] = pygame.image.load(os.path.join(RESOURCE_PATH,helper_string + "_horizontal.png"))
      self.flame_images[-1]["vertical"] = pygame.image.load(os.path.join(RESOURCE_PATH,helper_string + "_vertical.png"))
      self.flame_images[-1]["left"] = pygame.image.load(os.path.join(RESOURCE_PATH,helper_string + "_left.png"))
      self.flame_images[-1]["right"] = pygame.image.load(os.path.join(RESOURCE_PATH,helper_string + "_right.png"))
      self.flame_images[-1]["up"] = pygame.image.load(os.path.join(RESOURCE_PATH,helper_string + "_up.png"))
      self.flame_images[-1]["down"] = pygame.image.load(os.path.join(RESOURCE_PATH,helper_string + "_down.png"))
      
    # load item images:
    self.item_images = {}
    
    self.item_images[Map.ITEM_BOMB] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_bomb.png"))
    self.item_images[Map.ITEM_FLAME] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_flame.png"))
    self.item_images[Map.ITEM_SUPERFLAME] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_superflame.png"))
    self.item_images[Map.ITEM_SPEEDUP] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_speedup.png"))
    self.item_images[Map.ITEM_DISEASE] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_disease.png"))
    self.item_images[Map.ITEM_RANDOM] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_random.png"))
    self.item_images[Map.ITEM_SPRING] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_spring.png"))
    self.item_images[Map.ITEM_SHOE] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_shoe.png"))
    self.item_images[Map.ITEM_MULTIBOMB] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_multibomb.png"))
    self.item_images[Map.ITEM_RANDOM] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_random.png"))
    self.item_images[Map.ITEM_BOXING_GLOVE] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_boxing_glove.png"))
    self.item_images[Map.ITEM_DETONATOR] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_detonator.png"))
    self.item_images[Map.ITEM_THROWING_GLOVE] = pygame.image.load(os.path.join(RESOURCE_PATH,"item_throwing_glove.png"))
      
    # load other images:
    
    self.other_images = {}
    
    self.other_images["shadow"] = pygame.image.load(os.path.join(RESOURCE_PATH,"other_shadow.png"))
    self.other_images["spring"] = pygame.image.load(os.path.join(RESOURCE_PATH,"other_spring.png"))
    self.other_images["antena"] = pygame.image.load(os.path.join(RESOURCE_PATH,"other_antena.png"))
     
    self.other_images["disease"] = []
    self.other_images["disease"].append(pygame.image.load(os.path.join(RESOURCE_PATH,"other_disease1.png")))
    self.other_images["disease"].append(pygame.image.load(os.path.join(RESOURCE_PATH,"other_disease2.png")))    
     
  ## Returns colored image from another image (replaces red color with given color). This method is slow. Color is (r,g,b) tuple of 0 - 1 floats.

  def color_surface(self, surface, color_number):
    result = surface.copy()
    
    # change all red pixels to specified color:
    for j in range(result.get_size()[1]):
      for i in range(result.get_size()[0]):
        pixel_color = result.get_at((i,j))
        
        if pixel_color.r == 255 and pixel_color.g == 0 and pixel_color.b == 0:
          pixel_color.r = COLOR_RGB_VALUES[color_number][0]
          pixel_color.g = COLOR_RGB_VALUES[color_number][1]
          pixel_color.b = COLOR_RGB_VALUES[color_number][2]
          result.set_at((i,j),pixel_color)

    return result

  def tile_position_to_pixel_position(self, tile_position,center=(0,0)):
    return (int(float(tile_position[0]) * Renderer.MAP_TILE_WIDTH) - center[0],int(float(tile_position[1]) * Renderer.MAP_TILE_HEIGHT) - center[1])

  def set_resolution(self, new_resolution):
    self.screen_resolution = new_resolution

  def render_map(self, map_to_render):
    result = pygame.Surface(self.screen_resolution)

    if map_to_render != self.prerendered_map:     # first time rendering this map, prerender some stuff
      print("prerendering map...")

      # following images are only needed here, so we dont store them to self
      image_trampoline = pygame.image.load(os.path.join(RESOURCE_PATH,"other_trampoline.png"))
      image_teleport = pygame.image.load(os.path.join(RESOURCE_PATH,"other_teleport.png"))

      self.prerendered_map_background.fill((255,255,255))

      for j in range(Map.MAP_HEIGHT):
        for i in range(Map.MAP_WIDTH):
          render_position = (i * Renderer.MAP_TILE_WIDTH + Renderer.MAP_BORDER_WIDTH,j * Renderer.MAP_TILE_HEIGHT + + Renderer.MAP_BORDER_WIDTH)          
          self.prerendered_map_background.blit(self.environment_images[map_to_render.get_environment_name()][0],render_position)
       
          tile = map_to_render.get_tile_at((i,j))
          
          if tile.special_object == MapTile.SPECIAL_OBJECT_TELEPORT_A or tile.special_object == MapTile.SPECIAL_OBJECT_TELEPORT_B:
            self.prerendered_map_background.blit(image_teleport,render_position)
          elif tile.special_object == MapTile.SPECIAL_OBJECT_TRAMPOLINE:
            self.prerendered_map_background.blit(image_trampoline,render_position)
          
      self.prerendered_map = map_to_render

    result.blit(self.prerendered_map_background,(0,0))

    # order the players and bombs by their y position so that they are drawn correctly

    ordered_objects_to_render = []
    ordered_objects_to_render.extend(map_to_render.get_players())
    ordered_objects_to_render.extend(map_to_render.get_bombs())
    ordered_objects_to_render.sort(key = lambda what: 1000 if (isinstance(what,Bomb) and what.movement == Bomb.BOMB_FLYING) else what.get_position()[1]) # flying bomb are rendered above everything else
    
    # render the map by lines:

    tiles = map_to_render.get_tiles()
    environment_images = self.environment_images[map_to_render.get_environment_name()]
    
    y = Renderer.MAP_BORDER_WIDTH
    y_offset_block = Renderer.MAP_TILE_HEIGHT - environment_images[1].get_size()[1]
    y_offset_wall = Renderer.MAP_TILE_HEIGHT - environment_images[2].get_size()[1]
    
    line_number = 0
    object_to_render_index = 0
    
    flame_animation_frame = (pygame.time.get_ticks() / 100) % 2
    
    for line in tiles:
      x = (Map.MAP_WIDTH - 1) * Renderer.MAP_TILE_WIDTH + Renderer.MAP_BORDER_WIDTH
      
      while True: # render players and bombs in the current line 
        if object_to_render_index >= len(ordered_objects_to_render):
          break
        
        object_to_render = ordered_objects_to_render[object_to_render_index]
        
        if object_to_render.get_position()[1] > line_number + 1:
          break
        
        overlay_images = []        # images that should additionaly be rendered over image_to_render
        
        relative_offset = [0,0]    # to relatively shift images by given offset
        
        if isinstance(object_to_render,Player):      # <= not very nice, maybe fix this later
          sprite_center = Renderer.PLAYER_SPRITE_CENTER
          
          animation_frame = (object_to_render.get_state_time() / 100) % 4
          
          if object_to_render.is_in_air():
            image_to_render = self.player_images[object_to_render.get_number()]["down"]
          
            if object_to_render.get_state_time() < Player.JUMP_DURATION / 2:
              quotient = abs(object_to_render.get_state_time() / float(Player.JUMP_DURATION / 2))
            else:
              quotient = 2.0 - abs(object_to_render.get_state_time() / float(Player.JUMP_DURATION / 2))
              
            relative_offset[1] = -1 * int(quotient * Renderer.MAP_TILE_HEIGHT * Map.MAP_HEIGHT)
            
          elif object_to_render.is_boxing() or object_to_render.is_throwing():
            if not object_to_render.is_throwing() and animation_frame == 0:
              helper_string = ""
            else:
              helper_string = "box "
            
            if object_to_render.get_state() == Player.STATE_IDLE_UP or object_to_render.get_state() == Player.STATE_WALKING_UP:
              image_to_render = self.player_images[object_to_render.get_number()][helper_string + "up"]
            elif object_to_render.get_state() == Player.STATE_IDLE_RIGHT or object_to_render.get_state() == Player.STATE_WALKING_RIGHT:
              image_to_render = self.player_images[object_to_render.get_number()][helper_string + "right"]
            elif object_to_render.get_state() == Player.STATE_IDLE_DOWN or object_to_render.get_state() == Player.STATE_WALKING_DOWN:
              image_to_render = self.player_images[object_to_render.get_number()][helper_string + "down"]
            else:      # left
              image_to_render = self.player_images[object_to_render.get_number()][helper_string + "left"]
          else:
            if object_to_render.get_state() == Player.STATE_IDLE_UP:
              image_to_render = self.player_images[object_to_render.get_number()]["up"]
            elif object_to_render.get_state() == Player.STATE_IDLE_RIGHT:
              image_to_render = self.player_images[object_to_render.get_number()]["right"]
            elif object_to_render.get_state() == Player.STATE_IDLE_DOWN:
              image_to_render = self.player_images[object_to_render.get_number()]["down"]
            elif object_to_render.get_state() == Player.STATE_IDLE_LEFT:
              image_to_render = self.player_images[object_to_render.get_number()]["left"]
            elif object_to_render.get_state() == Player.STATE_WALKING_UP:
              image_to_render = self.player_images[object_to_render.get_number()]["walk up"][animation_frame]
            elif object_to_render.get_state() == Player.STATE_WALKING_RIGHT:
              image_to_render = self.player_images[object_to_render.get_number()]["walk right"][animation_frame]
            elif object_to_render.get_state() == Player.STATE_WALKING_DOWN:
              image_to_render = self.player_images[object_to_render.get_number()]["walk down"][animation_frame]
            else: # Player.STATE_WALKING_LEFT
              image_to_render = self.player_images[object_to_render.get_number()]["walk left"][animation_frame]
        
          if object_to_render.get_disease() != Player.DISEASE_NONE:
            overlay_images.append(self.other_images["disease"][animation_frame % 2])          
        else:    # bomb
          sprite_center = Renderer.BOMB_SPRITE_CENTER
          animation_frame = (object_to_render.time_of_existence / 100) % 4
         
          if object_to_render.has_detonator():
            overlay_images.append(self.other_images["antena"])
            
            if object_to_render.time_of_existence < Bomb.DETONATOR_EXPIRATION_TIME:
              animation_frame = 0                 # bomb won't pulse if within detonator expiration time
          
          if object_to_render.movement == Bomb.BOMB_FLYING:
            
            normalised_distance_travelled = object_to_render.flight_info.distance_travelled / float(object_to_render.flight_info.total_distance_to_travel)
            
            helper_offset = -1 * object_to_render.flight_info.total_distance_to_travel + object_to_render.flight_info.distance_travelled
            
            relative_offset[0] = int(object_to_render.flight_info.direction[0] * helper_offset * Renderer.MAP_TILE_WIDTH)
            relative_offset[1] = int(object_to_render.flight_info.direction[1] * helper_offset * Renderer.MAP_TILE_HALF_HEIGHT)
            
            relative_offset[1] -= int(math.sin(normalised_distance_travelled * math.pi) * object_to_render.flight_info.total_distance_to_travel * Renderer.MAP_TILE_HEIGHT / 2)  # height in air
            
          image_to_render = self.bomb_images[animation_frame]
          
          if object_to_render.has_spring:
            overlay_images.append(self.other_images["spring"])
        
        render_position = self.tile_position_to_pixel_position(object_to_render.get_position(),Renderer.SHADOW_SPRITE_CENTER)
        render_position = ((render_position[0] + Renderer.MAP_BORDER_WIDTH + relative_offset[0]) % self.prerendered_map_background.get_size()[0],render_position[1] + Renderer.MAP_BORDER_WIDTH)
        result.blit(self.other_images["shadow"],(render_position[0],render_position[1]))
        
        render_position = self.tile_position_to_pixel_position(object_to_render.get_position(),sprite_center)
        render_position = ((render_position[0] + Renderer.MAP_BORDER_WIDTH + relative_offset[0]) % self.prerendered_map_background.get_size()[0],render_position[1] + Renderer.MAP_BORDER_WIDTH + relative_offset[1])
        
        result.blit(image_to_render,render_position)
        
        for additional_image in overlay_images:
          result.blit(additional_image,render_position)
      
        object_to_render_index += 1
            
      for tile in reversed(line):           # render tiles in the current line
        if not tile.to_be_destroyed:        # don't render a tile that is being destroyed
          if tile.kind == MapTile.TILE_BLOCK:
            result.blit(environment_images[1],(x,y + y_offset_block))
          elif tile.kind == MapTile.TILE_WALL:
            result.blit(environment_images[2],(x,y + y_offset_wall))
          elif tile.item != None:
            result.blit(self.item_images[tile.item],(x,y))

        if len(tile.flames) != 0: # there is at least one flame - draw it
          sprite_name = tile.flames[0].direction

          result.blit(self.flame_images[flame_animation_frame][sprite_name],(x,y))

        x -= Renderer.MAP_TILE_WIDTH
  
      x = (Map.MAP_WIDTH - 1) * Renderer.MAP_TILE_WIDTH + Renderer.MAP_BORDER_WIDTH
  
      y += Renderer.MAP_TILE_HEIGHT
      line_number += 1

    return result    

class AI(object):
  REPEAT_ACTIONS = (100,500)    ##< In order not to compute actions with every single call to
                                #   play(), actions will be stored in self.outputs and repeated
                                #   for next random(REPEAT_ACTIONS[0],REPEAT_ACTIONS[1]) ms - saves
                                #   CPU time and prevents jerky AI movement.
  
  def __init__(self, player, game_map):
    self.player = player
    self.game_map = game_map
    
    self.outputs = []      # holds currently active outputs
    self.recompute_compute_actions_on = 0
    
  ## Decides what moves to make and returns a list of event in the same
  #  format as PlayerKeyMaps.get_current_actions().
    
  def play(self):
    current_time = pygame.time.get_ticks()
    
    if current_time < self.recompute_compute_actions_on:
      return self.outputs             # only repeat actions
    
    self.recompute_compute_actions_on = current_time + random.randint(AI.REPEAT_ACTIONS[0],AI.REPEAT_ACTIONS[1])
    
    print(self.recompute_compute_actions_on)
    
    # calculate new actions here:
      
    self.outputs = []
    maximum_score = 0       # maximum score so far
    
    # consider all possible moves and find the one with biggest score:
    
    #TODO
    
    # test: assign random action
    self.outputs.append((self.player.get_number(),random.choice((PlayerKeyMaps.ACTION_UP,PlayerKeyMaps.ACTION_RIGHT,PlayerKeyMaps.ACTION_DOWN,PlayerKeyMaps.ACTION_LEFT))))
    
    return self.outputs

class Game(object):
  def __init__(self):
    pygame.mixer.pre_init(22050,-16,2,512)   # set smaller audio buffer size to prevent audio lag
    pygame.init()
    self.player_key_maps = PlayerKeyMaps()
    
    self.player_key_maps.allow_control_by_mouse()

    self.player_key_maps.set_player_key_map(0,pygame.K_w,pygame.K_d,pygame.K_s,pygame.K_a,pygame.K_g,pygame.K_h)
    self.player_key_maps.set_player_key_map(1,pygame.K_i,pygame.K_l,pygame.K_k,pygame.K_j,pygame.K_o,pygame.K_p)
    self.player_key_maps.set_player_key_map(2,PlayerKeyMaps.MOUSE_CONTROL_UP,PlayerKeyMaps.MOUSE_CONTROL_RIGHT,PlayerKeyMaps.MOUSE_CONTROL_DOWN,PlayerKeyMaps.MOUSE_CONTROL_LEFT,PlayerKeyMaps.MOUSE_CONTROL_BUTTON_L,PlayerKeyMaps.MOUSE_CONTROL_BUTTON_R)

    self.renderer = Renderer()
    self.sound_player = SoundPlayer()

  def run(self):
    screen = pygame.display.set_mode((800,600))
    time_before = pygame.time.get_ticks()

    self.game_map = Map(MAP1,PlaySetup())

    self.test_ai = AI(self.game_map.get_players_by_numbers()[3],self.game_map)

    show_fps_in = 0
    pygame_clock = pygame.time.Clock()

    while True:     # main loop
      dt = min(pygame.time.get_ticks() - time_before,100)
      time_before = pygame.time.get_ticks()

      self.simulation_step(dt)

      for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()

      screen.blit(self.renderer.render_map(self.game_map),(0,0))
      pygame.display.flip()
      
      self.sound_player.process_events(self.game_map.get_and_clear_sound_events())  # play sounds

      pygame_clock.tick()

      if show_fps_in <= 0:
        print("fps: " + str(pygame_clock.get_fps()))
        show_fps_in = 255
      else:
        show_fps_in -= 1

  def simulation_step(self,dt):
    actions_being_performed = self.player_key_maps.get_current_actions()
    
    actions_being_performed = actions_being_performed + self.test_ai.play()
    
    players = self.game_map.get_players()

    for player in players:
      player.react_to_inputs(actions_being_performed,dt,self.game_map)
      
    self.game_map.update(dt)

# main:

game = Game()
game.run()