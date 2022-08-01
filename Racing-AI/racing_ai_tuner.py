import unreal
import pie_script

import datetime
import time
import sys
#import socket
#import threading


# class that provides functions necessary to perform AI tuning for the currently opened level
class RacingAITuner(pie_script.PIEScript):

    def __init__(self):
        super().__init__()
        self._b_is_expecting_ai_control_properties_json_string = False
        self._b_is_expecting_race_time_string = False
        self._number_of_simulations_ran = 0
        self._total_number_of_desired_simulations = 0
        self._best_race_time = sys.float_info.max
        self._ai_control_properties_json_string = ""
        self._tuning_ai_controller_class_path = ""
        self.c_racer_ai_tuning_message_control_props_json_string = unreal.RacerAiTuningBpFunctionLibrary.get_racer_ai_tuning_message_incoming_ai_control_properties()
        self.c_racer_ai_tuning_message_race_time = unreal.RacerAiTuningBpFunctionLibrary.get_racer_ai_tuning_message_incoming_race_time()
        self.c_racer_ai_tuning_message_accept_control_props = unreal.RacerAiTuningBpFunctionLibrary.get_racer_ai_tuning_message_accept_control_properties()
        self.c_racer_ai_tuning_message_deny_control_props = unreal.RacerAiTuningBpFunctionLibrary.get_racer_ai_tuning_message_deny_control_properties()
        self.set_listen_buffer_size(4096) # must be larger than size of largest message -- json control properties
        self._tuning_begin_timestamp = None
        self._tuning_end_timestamp = None
        
    @staticmethod
    def help():
        unreal.log("=== Racing AI Tuner ===")
        unreal.log("Built on top of PIE Script")
        unreal.log("To start tuning instantiate a RacingAITuner and call: '.begin_tuning(level_path, game_mode_reference, ai_controller_reference, number_of_simulations)'")
        unreal.log("\t level_path - string path to level, right click on a map file in the content browser and select 'Copy File Path'")
        unreal.log("\t game_mode_reference - string reference to gamemode, right click on a Racing AI Tuning Game Mode blueprint in the content browser and select 'Copy Reference'")
        unreal.log("\t ai_controller_reference - string reference to ai controller, right click on a Racer AI Controller blueprint in the content browser and select 'Copy Reference'")
        unreal.log("\t number_of_simulations - the number of simulations to run")
        unreal.log("A copy of the Racer AI Controller blueprint will be created with '_AITuningCopy' appended to it's name.")
        unreal.log("The editor will load an unsaved untitled copy of the provided level, set it's game mode to the AI Tuning Game Mode, and set the AI Tuning Game Mode's default AI racer.")
        
        
        return
     
     
    # get the currently cached json string representing ai control properties
    def get_cached_ai_control_properties_json_string(self):
        return self._ai_control_properties_json_string
     
     
    # check if the tuner is expecting that the next message received is a race time string
    def is_expecting_race_time_string_on_next_message(self):
        return self._b_is_expecting_race_time_string
     
     
    # check if the tuner is expecting that the next message received is a json string representing ai control properties
    def is_expecting_ai_control_properties_json_string_on_next_message(self):
        return self._b_is_expecting_ai_control_properties_json_string
     
     
    # get total number of simulations that will be executed
    def get_total_number_of_desired_simulations(self):
        return self._total_number_of_desired_simulations
     
     
    # get number of simulations that have been executed
    def get_number_of_simulations_ran(self):
        return self._number_of_simulations_ran
    
    
    # overridable handler for when a message is received from a PIE Script Messenger in a live PIE session
    def receive_message(self, msg, b_was_handled):
        
        b_did_this_class_handle_message = False
        
        # make sure message was not already handled
        if(b_was_handled == False):
            
            if(msg == self.c_racer_ai_tuning_message_control_props_json_string):
                unreal.log("expecting incoming ai control properties")
                b_did_this_class_handle_message = True
                self._b_is_expecting_ai_control_properties_json_string = True
                
            elif(self.is_expecting_ai_control_properties_json_string_on_next_message() == True):
                unreal.log("received incoming ai control properties")
                b_did_this_class_handle_message = True
                self._b_is_expecting_ai_control_properties_json_string = False
                self.handle_received_ai_control_properties_json_string(msg)
            
            elif(msg == self.c_racer_ai_tuning_message_race_time):
                unreal.log("expecting incoming race time")
                b_did_this_class_handle_message = True
                self._b_is_expecting_race_time_string = True
                
            elif(self.is_expecting_race_time_string_on_next_message() == True):
                #unreal.log("received incoming race time")
                b_did_this_class_handle_message = True
                self._b_is_expecting_race_time_string = False
                self.handle_received_race_time_string(msg)
                
                
            
        super().receive_message(msg, b_was_handled or b_did_this_class_handle_message)
        
        
        return
        
        
    # handler for when the expected race time string is received
    # from a PIE Script Messenger in a live PIE session
    def handle_received_race_time_string(self, race_time_string):
        race_time = sys.float_info.max
        
        try:
            race_time = float(race_time_string)
        except Exception as e:
            unreal.log_error("exception:\n" + str(e))
        
        if(race_time < self._best_race_time):
            self._best_race_time = race_time
            unreal.log("received race time: '" + str(race_time_string) + "' -- accepting control properties...")
            self.send_message(self.c_racer_ai_tuning_message_accept_control_props)
        else:
            unreal.log("received race time: '" + str(race_time_string) + "' -- denying control properties (best race time: '" + str(self._best_race_time) + "')...")
            self.send_message(self.c_racer_ai_tuning_message_deny_control_props)
        
        
        return
        
        
    # handler for when the expected ai control properties json message is received
    # from a PIE Script Messenger in a live PIE session
    def handle_received_ai_control_properties_json_string(self, json_string):
        self._ai_control_properties_json_string = json_string
        
        
        return
        
        
    # overridable handler for when the begin play message is received
    # from a PIE Script Messenger in a live PIE session
    def handle_begin_play(self):
        super().handle_begin_play()
        
        
        return
        
        
    # overridable handler for when the end play message is received
    # from a PIE Script Messenger in a live PIE session
    def handle_end_play(self):
        super().handle_end_play()
        
        
        return
    
    
    # overridable handler called when a client connection is accepted
    def handle_accepted_client_connection(self):
        super().handle_accepted_client_connection()
        
        
        return
        
    
    # overridable handler called when a client connection sends a heartbeat
    def handle_socket_heartbeat(self):
        super().handle_socket_heartbeat()
        
    
        return
    
   
    # overridable handler called periodically on the main thread when pie simulation is NOT running
    def handle_editor_periodic_tick(self):
        super().handle_editor_periodic_tick()
        
        
        return
    
   
    # overridable handler called periodically on the main thread while pie simulation IS running
    def handle_editor_simulation_periodic_tick(self):
        super().handle_editor_simulation_periodic_tick()
        
        
        return
    
   
    # overridable handler for when the editor play simulation started delegate is broadcasted
    def handle_editor_play_simulation_started(self):
        super().handle_editor_play_simulation_started()
        
        
        return
    
   
    # overridable handler for when the editor play simulation ending delegate is broadcasted
    def handle_editor_play_simulation_ending(self):
        super().handle_editor_play_simulation_ending()
        
        
        return
    
   
    # overridable handler for when the editor play simulation has finished ending
    def handle_editor_play_simulation_ended(self):
        super().handle_editor_play_simulation_ended()
        
        self._number_of_simulations_ran += 1
        total_simulations = self.get_total_number_of_desired_simulations()
        
        if(self.get_number_of_simulations_ran() < total_simulations):
            unreal.log("running simulation '" + str(self._number_of_simulations_ran + 1) + "' of '" + str(total_simulations) + "'")
            self._iterate_next_simulation()
        else:
            self.handle_finish_tuning()
        
        
        return
    
   
    # overridable handler for when the the editor has changed worlds
    def handle_editor_world_changed(self):
        super().handle_editor_world_changed()
            
            
        return
        
        
    # start tuning in a given level, with the given ai tuning game mode class, and given ai controller class
    def begin_tuning(self, level_path, game_mode_path, ai_controller_path, number_of_simulations = 1):
    
        # create tuning ai controller copy
        if(self.create_tuning_ai_controller(ai_controller_path) == False):
            return
        
        # set tuning ai game mode default ai controller to the tuning ai controller copy
        if(self.set_game_mode_class_default_ai_controller(game_mode_path, self.get_ai_tuning_ai_controller_path()) == False):
            return
            
        # duplicate the given level and load into the duplicate
        if(self.duplicate_level_and_load_copy(level_path) == False):
            return
            
        # clear cached best race time
        self._best_race_time = sys.float_info.max
        
        # set the current level game mode class override to the tuning ai game mode
        self.set_editor_world_game_mode(game_mode_path)
        
        self._number_of_simulations_ran = 0
        self._total_number_of_desired_simulations = number_of_simulations
    
        unreal.log("beginning tuning for level '" + level_path + "', using tuning game mode at '" + game_mode_path + "' and template ai controller '" + ai_controller_path + "'")
        
        # launch PIE session and connect to runtime messenger
        self.start()
        
        self._tuning_begin_timestamp = datetime.datetime.utcnow()
        self._tuning_end_timestamp = None
        
        
        return
    

    # called when tuning is finished
    def handle_finish_tuning(self):
        self._tuning_end_timestamp = datetime.datetime.utcnow()
        if(self._tuning_begin_timestamp is not None):
            elapsed_time = (self._tuning_end_timestamp - self._tuning_begin_timestamp).total_seconds()
            unreal.log("tuning completed after '" + str(elapsed_time) + "' seconds with best race time '" + str(self._best_race_time) + "'")
        
        
        return
        
        
    # convert and cache path to the ai controller to use for AI tuning
    def set_ai_tuning_ai_controller_path(self, ai_controller_class_path):
        self._tuning_ai_controller_class_path = ai_controller_class_path
        
        
        return
        
        
    # cache path to the ai controller to use for AI tuning
    def get_ai_tuning_ai_controller_path(self):
        return self._tuning_ai_controller_class_path
        
    
    # replaces the name of an asset within a path string with a new name
    @staticmethod
    def replace_asset_name_in_path_string(path, old_name, new_name):
        return path.replace(old_name, new_name)
        
        
    # duplicate a given ai controller and cache a reference to it
    # returns true on success
    def create_tuning_ai_controller(self, ai_controller_class_path):
        ai_controller_data = None
        try:
            ai_controller_data = unreal.EditorAssetLibrary.find_asset_data(ai_controller_class_path)
        except Exception as e:
            unreal.log_error("exception:\n" + str(e))
            unreal.log_error("failed to create tuning ai controller")
            return False
        
        ai_controller_name = str(ai_controller_data.get_editor_property("asset_name"))
        new_ai_controller_name = ai_controller_name + "_AiTuningCopy"
        new_ai_controller_class_path = RacingAITuner.replace_asset_name_in_path_string(ai_controller_class_path, ai_controller_name, new_ai_controller_name)
        
        # cache new tuning ai controller path
        self.set_ai_tuning_ai_controller_path(new_ai_controller_class_path)
        
        # check if new controller already exists
        if(unreal.load_class(None, new_ai_controller_class_path[:-1] + "_C'") is not None):
            unreal.log("copy of ai controller at '" + ai_controller_class_path + "' named '" + new_ai_controller_name + "' already exists -- using it in place")
            return True
        
        unreal.EditorAssetLibrary.duplicate_asset(ai_controller_class_path, self.get_ai_tuning_ai_controller_path())
        
        unreal.log("created copy of ai controller at '" + ai_controller_class_path + "' named '" + new_ai_controller_name + "'")
        
        
        return True
    
        
    # set the default ai controller class property for the given game mode class
    # returns true on success
    def set_game_mode_class_default_ai_controller(self, game_mode_path, ai_controller_path):
        game_mode_class = None
        ai_controller_class = None
        
        if(ai_controller_path is not None and ai_controller_path != ""):
            ai_controller_class_path = ai_controller_path[:-1] + "_C'"
            ai_controller_class = unreal.load_class(None, ai_controller_class_path)
        
        if(game_mode_path is not None and game_mode_path != ""):
            game_mode_class_path = game_mode_path[:-1] + "_C'"
            game_mode_class = unreal.load_class(None, game_mode_class_path)
            game_mode_class_default_object = unreal.get_default_object(game_mode_class)
            
        if(game_mode_class is None):
            unreal.log_error("failed to set game mode at '" + game_mode_path + "' ai controller to '" + ai_controller_path + "'")
            return False
        
        game_mode_class_default_object.set_editor_property("default_racer_ai_controller_class", ai_controller_class)
        
        unreal.EditorAssetLibrary.save_asset(game_mode_class_path)
        
        unreal.log("set game mode at '" + game_mode_path + "' to use ai controller '" + ai_controller_path + "'")
        
        return True
        
    
    # duplicate the given level and load into the copy
    def duplicate_level_and_load_copy(self, level_path):
        #duplicate_level_path = level_path[:-5] + "_AITuningCopy.umap'"

        loaded_level = unreal.EditorLoadingAndSavingUtils.load_map(level_path)
        if(loaded_level == False):
            unreal.log_error(" failed to duplicate level at '" + level_path + "'. make sure to use the file path, not a reference path")
            return False
            
        # create a new map using the provided one as a template and load it
        unreal.EditorLoadingAndSavingUtils.new_map_from_template(level_path, False)
        
        unreal.log("duplicated level at '" + level_path + "'")
        
        
        return True
        
        
    # set the currently loaded level's game mode to the class at the given path
    def set_editor_world_game_mode(self, game_mode_path):
        game_mode_class = None
        
        if(game_mode_path is not None and game_mode_path != ""):
            game_mode_class_path = game_mode_path[:-1] + "_C'"
            game_mode_class = unreal.load_class(None, game_mode_class_path)
    
        w = unreal.EditorLevelLibrary.get_editor_world()
        ws = w.get_world_settings()
        ws.set_editor_property("default_game_mode", game_mode_class)
        
        unreal.log("set current level default game mode class override to game mode at '" + game_mode_path + "'")
        
        
        return
        
        
    # sets ai control properties for the given ai controller class using the given json string to construct the properties
    def set_ai_tuning_ai_controller_control_properties_from_json_string(self, ai_controller_path, json_string):
        ai_controller_class = None
        ai_controller_class_default_object = None
        
        if(ai_controller_path is not None and ai_controller_path != ""):
            ai_controller_class_path = ai_controller_path[:-1] + "_C'"
            ai_controller_class = unreal.load_class(None, ai_controller_class_path)
            ai_controller_class_default_object = unreal.get_default_object(ai_controller_class)
            
        if(ai_controller_class is None or ai_controller_class_default_object is None):
            unreal.log_error("could not find racer ai controller class at '" + ai_controller_path + "'")
            return
        
        ai_control_props = unreal.RacerAiTuningBpFunctionLibrary.convert_json_string_to_racing_ai_control_properties(json_string)
        ai_controller_class_default_object.set_editor_property("control_properties", ai_control_props)
        
        unreal.EditorAssetLibrary.save_asset(ai_controller_class_path)
        
        unreal.log("set control properties of racer ai controller at '" + ai_controller_path + "'")
        #unreal.log("set control properties of racer ai controller at '" + ai_controller_path + "' using json string:\n" + json_string)
        
        
        return
    

    # prepare and start another simulation
    def _iterate_next_simulation(self):
        # prep next simulation 
        ai_controller_path = self.get_ai_tuning_ai_controller_path()
        ai_control_props_json_string = self.get_cached_ai_control_properties_json_string()
        
        if(ai_controller_path == "" or ai_controller_path is None):
            unreal.log_error("ai controller path is null")
        
        if(ai_control_props_json_string != "" and ai_control_props_json_string is not None):
            self.set_ai_tuning_ai_controller_control_properties_from_json_string(ai_controller_path, ai_control_props_json_string)
        else:
            unreal.log_error("no control properties were received")
        
        # launch PIE session and connect to runtime messenger
        self.start()
        
        
        return
        
        
