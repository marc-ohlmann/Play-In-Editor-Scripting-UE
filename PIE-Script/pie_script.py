import unreal

import time
import socket
import threading
 

@unreal.uclass()
class PIEScriptEditorTimerObject(unreal.Object):
    def __init__(self, outer_world, periodic_callback=None, periodic_tick_duration=1.0):
        unreal.Object.__init__(self, outer=outer_world)
        self._periodic_tick_timer_handle = None
        self._periodic_tick_timer_duration = periodic_tick_duration
        self._periodic_callback = periodic_callback
    
    
    # overridable handler called periodically on the main thread
    @unreal.ufunction(ret=None,params=[])
    def handle_periodic_timer_callback(self):
        if(self._periodic_callback is not None):
            self._periodic_callback()
        
    
        return
        
        
    # call to enable / disable the periodic tick timer used to process messages in the main thread
    def set_periodic_timer_enabled(self, b_enabled, world_context):
        if(self._periodic_tick_timer_handle is not None and unreal.SystemLibrary.is_timer_active(world_context, "handle_periodic_timer_callback") == True):
                unreal.SystemLibrary.clear_timer(self, self._periodic_tick_timer_handle)
    
        if(b_enabled == True):
            self._periodic_tick_timer_handle = unreal.SystemLibrary.set_timer(self, "handle_periodic_timer_callback", self._periodic_tick_timer_duration, True)
    
    
        return
        

@unreal.uclass()
class PIEScriptEditorDelegateHelperObject(unreal.EditorDelegateHelperObject):
    def __init__(self, on_editor_play_simulation_started_callback=None, on_editor_play_simulation_ending_callback=None, on_editor_world_changed_callback=None):
        unreal.Object.__init__(self)
        self._editor_play_simulation_started_callback = on_editor_play_simulation_started_callback
        self._editor_play_simulation_ending_callback = on_editor_play_simulation_ending_callback
        self._on_editor_world_changed_callback = on_editor_world_changed_callback
        self.bind_to_editor_delegates()
        self.on_editor_play_simulation_started.add_function_unique(self, "handle_editor_play_simulation_started")
        self.on_editor_play_simulation_ending.add_function_unique(self, "handle_editor_play_simulation_ending")
        self.on_editor_world_changed.add_function_unique(self, "handle_editor_world_changed")
    
    
    # callback to handle the editor event: play simulation started
    @unreal.ufunction(ret=None,params=[])
    def handle_editor_play_simulation_started(self):
        if(self._editor_play_simulation_started_callback is not None):
            self._editor_play_simulation_started_callback()
        
    
        return
        
        
    # callback to handle the editor event: play simulation ended
    @unreal.ufunction(ret=None,params=[])
    def handle_editor_play_simulation_ending(self):
        if(self._editor_play_simulation_ending_callback is not None):
            self._editor_play_simulation_ending_callback()
        
    
        return
        
    
    # callback to handle the editor event: world changed
    @unreal.ufunction(ret=None,params=[])
    def handle_editor_world_changed(self):
        if(self._on_editor_world_changed_callback is not None):
            self._on_editor_world_changed_callback()
        
    
        return


# class object that communicates with a PIEScript Messenger object that exists at runtime
# in an editor play simulation. Provides functions for starting and stopping a PIE session
# and sending / receiving messages from the runtime messenger object.
class PIEScript():

    def __init__(self):
    
        # socket connection
        self.c_ip_address = unreal.PIEScriptBpFunctionLibrary.get_pie_script_socket_address()
        self.c_port = unreal.PIEScriptBpFunctionLibrary.get_pie_script_socket_port()
        self.c_server_address = (self.c_ip_address, self.c_port)
        self._socket = None
        self._client = None
        self._client_address = None
        
        # message listening thread
        self._listen_thread = None
        self._b_continue_listen_thread = False
        self.c_listen_thread_sleep_duration = 0.01
        self._listen_buffer_size = 32
        self._message_queue = []
        
        # message type constants - defined by a C++ Blueprint Function Library that is accessible in Python through 
        # the Unreal Engine reflection system.
        self.c_socket_message_heartbeat = unreal.PIEScriptBpFunctionLibrary.get_pie_script_socket_message_heartbeat()
        self.c_socket_message_greeting = unreal.PIEScriptBpFunctionLibrary.get_pie_script_socket_message_greeting()
        self.c_socket_message_goodbye = unreal.PIEScriptBpFunctionLibrary.get_pie_script_socket_message_goodbye()
        self.c_runtime_message_beginplay = unreal.PIEScriptBpFunctionLibrary.get_pie_script_runtime_message_begin_play()
        self.c_runtime_message_endplay = unreal.PIEScriptBpFunctionLibrary.get_pie_script_runtime_message_end_play()
        
        # editor event handling
        self.c_editor_simulation_periodic_tick_duration = 0.5
        self.c_editor_periodic_tick_duration = 0.5
        self._editor_delegate_object = PIEScriptEditorDelegateHelperObject(
            on_editor_play_simulation_started_callback=self.handle_editor_play_simulation_started, 
            on_editor_play_simulation_ending_callback=self.handle_editor_play_simulation_ending,
            on_editor_world_changed_callback=self.handle_editor_world_changed)
        self._editor_simulation_timer_object = None
        self._editor_timer_object = None
        self._b_has_started_pie_session = False
        self._b_is_waiting_to_return_from_editor_simulation = False
        
        self._start_editor_periodic_timer()
        
    def __del__(self):
        if(self._editor_delegate_object is not None):
            del self._editor_delegate_object
            
        if(self._editor_timer_object is not None):
            del self._editor_timer_object
            
        if(self._editor_simulation_timer_object is not None):
            del self._editor_simulation_timer_object
            
        if(self._message_queue is not None):
            self._message_queue = []
            
        if(self._client is not None):
            self._client.close()
            
        if(self._socket is not None):
            self._socket.close()
            
            
    # print help to the log
    @staticmethod
    def help():
        unreal.log("=== Welcome to PIEScript ===")
        unreal.log("To begin using your python files with PIEScript:")
        unreal.log("\t 1) Create a folder ...\content\python\ in the contents folder")
        unreal.log("\t 2) Add an initialization file 'init_unreal.py' and within, import your file 'import filename'")
        #unreal.log("\t 3) Add to 'DefaultEngine.ini' under '[/Script/Engine.Engine]' the following: UnrealEdEngine=/Script/PIEScriptPlugin.PIEScriptEditorEngine")
        unreal.log("\t 3) initialize the PIEScript messenger component with a game mode on BeginPlay()")
        unreal.log("\t 4) make sure the level you want to test in is open")
        unreal.log("You can run python code by typing it into this console -- make sure 'Python' is selected in the dropdown on the bottom left")
        unreal.log("PIEScript uses the PIEScript class on python side to start() and stop() a PIE session")
        unreal.log("It expects a PIEScript Messenger component to be instantiated in your level on BeginPlay() and it will connect via sockets")
        
        
        return
        
        
    # get number of received messages waiting in the message queue
    def get_number_of_pending_received_messages(self):
        return len(self._message_queue)
        
        
    # check if this script is waiting to return from an ending editor play simulation
    def is_waiting_to_return_from_editor_simulation(self):
        return self._b_is_waiting_to_return_from_editor_simulation
        

    # set the listen thread receive message buffer size
    def set_listen_buffer_size(self, size):
        self._listen_buffer_size = size
        

     # check if this PIE script has a bound socket
    def is_socket_connected(self):
        return self._socket is not None and self._client is not None


    # check if this PIE script has a background thread that is actively listening for client messages
    def is_listening_for_messages(self):
        return self._b_continue_listen_thread is True and self._listen_thread is not None


    # check if this PIE script has started a PIE session
    def has_started_pie_session(self):
        return self._b_has_started_pie_session


    # call to start the PIE Script and intialize communications with the runtime messenger
    def start(self):
    
        # create a socket at server side
        # using TCP / IP protocol
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # bind the socket with server
        # and port number
        self._socket.bind(self.c_server_address)

        # allow maximum 1 connection to
        # the socket
        self._socket.listen(1)
        
        # start background thread to wait for clients and listen for messages from them
        self._start_listen_thread()
        
        # launch PIE session which should instantiate the runtime PIEScript Messenger 
        # the Messenger will connect to this socket
        self._start_pie_session()
        
        
        return
        
    
    # call to send the goodbye message to the runtime messenger and end the PIE Script
    def stop(self):
    
        # send goodbye message
        #if(self.is_socket_connected()):
        #    self.send_message(self.c_socket_message_goodbye)
            
        self.force_stop()
        
        
        return
        
    
    # forces the PIE Script to end immediately
    def force_stop(self):
        # disconnect client
        if(self._client is None):
            unreal.log_warning("no connected client")
        else:
            self._client.close()
            self._client = None
    
        # close socket
        if(self._socket is None):
            unreal.log_error("socket does not exist")
        else:
            self._socket.close()
            self._socket = None
            
        # stop listening for messages
        if(self.is_listening_for_messages()):
            self._stop_listen_thread()
            
        # end the PIE session
        self._stop_pie_session()
        
        
        return
        
        
    # call to send a message to the PIE Script Messenger in a live PIE session
    def send_message(self, msg):
        if(self.is_socket_connected() == True):
            try:
                self._client.send(msg.encode())
                #unreal.log("sent '" + msg + "'")
            except ConnectionResetError as cre:
                unreal.log_error("connection reset exception:\n" + str(cre) + "")
                
                # stop PIE session, stop background thread, and close connection
                self.force_stop()
            except Exception as e:
                unreal.log_error("exception:\n" + str(e) + "")
        else:
            unreal.log_error("not connected to socket, failed to send '" + msg + "'")
        
        
        return
        
        
    # overridable handler for when a message is received from a PIE Script Messenger in a live PIE session
    def receive_message(self, msg, b_was_handled):
        #unreal.log("received '" + msg + "'")
        
        if(b_was_handled == False):
            if(msg == self.c_runtime_message_beginplay):
                self.handle_begin_play()
            elif(msg == self.c_runtime_message_endplay):
                self.handle_end_play()
            elif(msg == self.c_socket_message_heartbeat):
                self.handle_socket_heartbeat()
            
            
        return
    
   
    # overridable handler for when the the editor play simulation started delegate is broadcasted
    def handle_editor_play_simulation_started(self):
        #unreal.log("editor play simulation started")
        self._start_editor_simulation_periodic_timer()
        
        
        return
    
   
    # overridable handler for when the the editor play simulation ended delegate is broadcasted
    def handle_editor_play_simulation_ending(self):
        #unreal.log("editor play simulation ending")
        self._b_is_waiting_to_return_from_editor_simulation = True
        
        return
    
   
    # overridable handler for when the the editor has finished returning from the play simulation
    def handle_editor_play_simulation_ended(self):
        #unreal.log("editor play simulation ended")
        
        
        return
    
   
    # overridable handler for when the the editor has changed worlds
    def handle_editor_world_changed(self):
        if(self.has_started_pie_session() == False):
            #unreal.log("editor world changed")
            self._start_editor_periodic_timer()
            
            
        return
    
   
    # overridable handler for when the begin play message is received
    # from a PIE Script Messenger in a live PIE session
    def handle_begin_play(self):
        #unreal.log("begin play received")
        
        
        return
        
        
    # overridable handler for when the end play message is received
    # from a PIE Script Messenger in a live PIE session
    def handle_end_play(self):
        #unreal.log("end play received")
        
        # stop the pie script
        self.stop()
        
        return
    
    
    # overridable handler called when a client connection is accepted
    def handle_accepted_client_connection(self):
        unreal.log("client connected at address '" + str(self._client_address) + "'")
        
        self.send_message(self.c_socket_message_greeting)
        
        
        return
        
    
    # overridable handler called when a client connection sends a heartbeat
    def handle_socket_heartbeat(self):
        # anything todo ?
        
    
        return
        
    
    # overridable handler called periodically on the main thread when pie simulation is NOT running
    def handle_editor_periodic_tick(self):
        if(self.is_waiting_to_return_from_editor_simulation() == True):
            self._b_is_waiting_to_return_from_editor_simulation = False
            self.handle_editor_play_simulation_ended()
            
    
        return
        
    
    # overridable handler called periodically on the main thread while pie simulation IS running
    def handle_editor_simulation_periodic_tick(self):
        pending_message_count = self.get_number_of_pending_received_messages()
        
        if(pending_message_count > 0):
            message_string = self._message_queue[0]
            self._message_queue = self._message_queue[1:]
            
            self.receive_message(message_string, False)
        
    
        return
        
        
    # creates and starts a listen thread in the background to listen for messages from the connected client
    def _start_listen_thread(self):
        if(self._listen_thread is not None):
            unreal.log_error("listen thread already exists")
            return
            
        self._b_continue_listen_thread = True
        self._listen_thread = threading.Thread(target=self._do_listen_thread, args=(self.handle_accepted_client_connection,), daemon=True)
        self._listen_thread.start()
        
        
        return
        
        
    # blocks and forces the listen thread to return    
    def _stop_listen_thread(self):
        if(self._listen_thread is None):
            unreal.log_error("listen thread does not exist")
            return
        
        self._b_continue_listen_thread = False
        self._listen_thread = None
        
        
        return
      
      
    # thread that listens for messages from the connected client    
    def _do_listen_thread(self, on_connection_accepted = None):
        while(self.is_listening_for_messages() == True):
            if(self._socket is None):
                unreal.log_error("socket does not exist")
            elif(self._client is None):
                unreal.log("waiting for client to connect...")
                # wait for a client and accept the connection
                try:
                    self._client, self._client_address = self._socket.accept()
                    on_connection_accepted()
                except Exception as e:
                    unreal.log_error("exception:\n" + str(e))
                    self._socket = None
            else:
                try:
                    data = self._receive_buffered_data()
                    if(len(data) > 0):
                        self._process_raw_message_data(data)
                except ConnectionAbortedError as cae:
                    break
                except Exception as e:
                    unreal.log_error("exception:\n" + str(e))
                    
                
            
            time.sleep(self.c_listen_thread_sleep_duration)
                
                
        unreal.log("listen thread aborting")
        
        
        return
        
        
    # pulls raw data from the socket until it no longer provides any
    def _receive_buffered_data(self):
        if(self.is_listening_for_messages() == False or self._client is None):
            unreal.log_error("not currently receiving data")
            return
        
        buff_size = self._listen_buffer_size
        data = b''
        while True:
            part = self._client.recv(buff_size)
            data += part
            if(len(part) < buff_size):
                break
        return data
     
     
    # converts raw socket data into strings and enqueues them as messages
    def _process_raw_message_data(self, data):
        if(len(data) <= 0):
            return
            
        data_bytes = data
        
        while(True):
            message_string = PIEScript.extract_string_from_raw_data(data_bytes)
            if(message_string is not None):
                self._message_queue.append(message_string)
                message_length = len(message_string)
                data_bytes = data_bytes[message_length:]
            else:
                break
                
        
        return
    
    
    # extracts a string from an array of bytes
    @staticmethod
    def extract_string_from_raw_data(data):
        if (len(data) <= 0):
            return None
    
        message_string = ""
        for byte in data:
            byte_char = chr(byte + 1)
            message_string += byte_char
            if(byte_char == '\0'):
                break
                
                
        return message_string
        
        
    # begins a PIE Play Simulation by executing a custom editor console command   
    def _start_pie_session(self):
        if(self.has_started_pie_session() == False):
            if(len(unreal.EditorLevelLibrary.get_pie_worlds(True)) > 0):
                unreal.EditorLevelLibrary.editor_end_play()
            
            unreal.EditorLevelLibrary.editor_play_simulate()
            #self._execute_editor_console_command(self.c_command_start)
            
            self._b_has_started_pie_session = True
            
            unreal.log_warning("starting PIE session")
            #unreal.log_warning("WARNING -- DO NOT use editor provided means of closing a PIE session -- may result in freezing / crash")
        
        
        return
        
        
    # ends a PIE Play Simulation by executing a custom editor console command   
    def _stop_pie_session(self):
        if(self.has_started_pie_session() == True):
            unreal.EditorLevelLibrary.editor_end_play()
            #self._execute_editor_console_command(self.c_command_end)
            
            self._b_has_started_pie_session = False
            
            unreal.log_warning("stopping PIE session")
        
        
        return
        
        
    # call to start the periodic timer 
    def _start_editor_simulation_periodic_timer(self):
        game_world = unreal.EditorLevelLibrary.get_game_world()
        
        if(game_world is None):
            unreal.log_error("game world is null")
            return
            
        #if(self._editor_simulation_timer_object is not None):
            #self._editor_simulation_timer_object.set_periodic_timer_enabled(False, game_world)
            #self._editor_simulation_timer_object.conditional_begin_destroy()
            #del self._editor_simulation_timer_object
        
        #unreal.log("editor simulation periodic timer started")
        self._editor_simulation_timer_object = PIEScriptEditorTimerObject(
            game_world, 
            periodic_callback=self.handle_editor_simulation_periodic_tick, 
            periodic_tick_duration=self.c_editor_simulation_periodic_tick_duration)
        self._editor_simulation_timer_object.set_periodic_timer_enabled(True, game_world)
        
        
        return
        
        
    # call to start the periodic timer 
    def _start_editor_periodic_timer(self):
        editor_world = unreal.EditorLevelLibrary.get_editor_world()
        
        if(editor_world is None):
            unreal.log_error("editor world is null")
            return
            
        #if(self._editor_timer_object is not None):
            #self._editor_timer_object.set_periodic_timer_enabled(False, editor_world)
            #self._editor_timer_object.conditional_begin_destroy()
            #del self._editor_timer_object
            
        #unreal.log("editor periodic timer started")
        self._editor_timer_object = PIEScriptEditorTimerObject(
            editor_world, 
            periodic_callback=self.handle_editor_periodic_tick,
            periodic_tick_duration=self.c_editor_periodic_tick_duration)
        self._editor_timer_object.set_periodic_timer_enabled(True, editor_world)
        
        
        return
        
     
    # executes the given command string in the editor console
    #def _execute_editor_console_command(self, command):
        #unreal.PIEScriptBpFunctionLibrary.execute_editor_console_command(command)
        #return
    
    