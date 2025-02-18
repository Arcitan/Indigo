import gamelib
import random
import math
import warnings
from sys import maxsize
import json

"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""


class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global FILTER, ENCRYPTOR, DESTRUCTOR, PING, EMP, SCRAMBLER
        FILTER = config["unitInformation"][0]["shorthand"]
        ENCRYPTOR = config["unitInformation"][1]["shorthand"]
        DESTRUCTOR = config["unitInformation"][2]["shorthand"]
        PING = config["unitInformation"][3]["shorthand"]
        EMP = config["unitInformation"][4]["shorthand"]
        SCRAMBLER = config["unitInformation"][5]["shorthand"]
        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.funnel_left = True

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  # Comment or remove this line to enable warnings.

        self.funnel_strategy(game_state)

        game_state.submit_turn()

    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def funnel_strategy(self, game_state):
        # First, place basic defenses
        self.build_defenses(game_state)
        # Now build reactive defenses based on where the enemy scored
        self.build_reactive_defense(game_state)

        # If the turn is less than 3, stall with Scramblers and wait to see enemy's base
        if game_state.turn_number < 3:
            self.stall_with_scramblers(game_state)
        else:
            # On turn 3, check which direction to funnel towards, and commit to it
            if game_state.turn_number == 3:
                ping_spawn_location_options = [[3, 10], [24, 10]]
                self.best_location = self.least_damage_spawn_location(game_state, ping_spawn_location_options)
                if self.best_location == [2, 11]:
                    self.build_left_funnel(game_state)
                    self.funnel_left = True
                else:
                    self.build_right_funnel(game_state)
                    self.funnel_left = False

            # On all turns after turn 3..
            elif game_state.turn_number > 3:
                # Keep committing to the funnel...
                if self.funnel_left:
                    self.build_left_funnel(game_state)
                else:
                    self.build_right_funnel(game_state)

                # Fortify defenses w/ our additional cores
                self.build_additional_defenses(game_state)
                self.build_better_tunnel(game_state)
                self.build_defenses3(game_state)
                # self.build_center(game_state)

                # And swarm down the funnel with units if we have enough bits
                if game_state.get_resource(game_state.BITS) >= 10:
                    game_state.attempt_spawn(PING, self.best_location, 1000)


    def build_defenses(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy EMPs can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place initial units
        destructor_locations = [[x, 13] for x in range(28) if x not in [3, 6, 10, 12, 15, 17, 21, 24]]

        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build destructor one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1] + 3]
            game_state.attempt_spawn(DESTRUCTOR, build_location)

    def build_additional_defenses(self, game_state):
        destructor_locations = []
        for i in range(1, 27):
            if i not in [3, 6, 10, 12, 15, 17, 21, 24]:
                destructor_locations.extend([[i, 12], [27-i, 12]])
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations)

    def build_better_tunnel(self, game_state):
        el = [[5, 11], [6, 10], [7, 9], [8, 8], [9, 7], [10, 6], [11, 5], [12, 4],
              [14, 3], [15, 4], [16, 5], [17, 6], [18, 7], [19, 8]]

        game_state.attempt_spawn(ENCRYPTOR, el)

    def build_defenses3(self, game_state):
        destructor_locations = []
        for i in range(2, 26):
            if i not in [3, 6, 10, 12, 15, 17, 21, 24]:
                destructor_locations.extend([[i, 11], [27-i, 11]])
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations)


    def build_additional_defenses(self, game_state):
        destructor_locations = []
        for i in range(1, 13):
            if i not in [3, 6, 10, 12, 15, 17, 21, 24]:
                destructor_locations.extend([[i, 12], [27-i, 12]])
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations)




    def emp_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our EMP's can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [FILTER, DESTRUCTOR, ENCRYPTOR]
        cheapest_unit = FILTER
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost < gamelib.GameUnit(cheapest_unit, game_state.config).cost:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our EMPs from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn EMPs next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(EMP, [24, 10], 2)


    def build_right_funnel(self, game_state):
        enc_locations =[[3, 11], [4, 11], [5, 10], [6, 9], [7, 8], [8,7], [9, 6], [10, 5], [11, 4],
                        [12, 3], [13, 2], [14, 2], [15, 3], [16, 4], [17, 5], [18, 6], [19, 7],
                        [20, 8]]
        game_state.attempt_spawn(ENCRYPTOR, enc_locations)

    def build_left_funnel(self, game_state):
        enc_locations = [[24, 11], [23, 11], [22, 10], [21, 9], [20, 8], [19, 7], [18, 6], [17, 5],
                         [16, 4], [15, 3], [14, 2], [12, 3], [11, 4], [10, 5], [9, 6], [8, 7], [7, 8]]
        game_state.attempt_spawn(ENCRYPTOR, enc_locations)

    def stall_with_scramblers(self, game_state):
        """
        Send out Scramblers at random locations to defend our base from enemy moving units.
        """
        deploy_locations = [[9, 4], [18, 4]]

        # Randomly spawn up to quarter scramblers
        count = 0
        quarter = game_state.get_resource(game_state.BITS) // 4 + 1
        while count < quarter and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]

            game_state.attempt_spawn(SCRAMBLER, deploy_location)
            count += 1
            """
            We don't have to remove the location since multiple information 
            units can occupy the same space.
            """

    def emp_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our EMP's can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [FILTER, DESTRUCTOR, ENCRYPTOR]
        cheapest_unit = FILTER
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost < gamelib.GameUnit(cheapest_unit, game_state.config).cost:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our EMPs from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn EMPs next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(EMP, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR,
                                                                                             game_state.config).damage
            damages.append(damage)

        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x=None, valid_y=None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (
                            valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
