import config
from space_object import SpaceObject

class Engine:
    def __init__(self, game_state_filename, player_class, gui_class):
        self.asteroid_ls = []
        self.bullet_ls = []
        self.upcoming_asteroid_ls = []
        self.import_state(game_state_filename)
        self.player = player_class()
        self.GUI = gui_class(self.game_state['width'], self.game_state['height'])
        self.fuel_warning_count = 0

    def import_state(self, game_state_filename):
    
        try: #open game_state file
            f = open(game_state_filename, 'r')
        except FileNotFoundError:
            raise FileNotFoundError(f'Error: unable to open {game_state_filename}')

        

        #game_state dict
        self.game_state = {'width': None,
                        'height': None,
                        'score': None,
                        'spaceship': None,
                        'fuel': None,
                        'asteroids_count': None,
                        'bullets_count': None,
                        'upcoming_asteroids_count': None}
        
        line_counter = 0 #for raising exceptions with line number
        for key in self.game_state: #iterate through keys in game_state dict
            line_counter += 1
            key_value = self.get_key_value([key], f, line_counter)

            #spaceship is a special key in dict because it needs to be handled
            #as a space object
            if key_value[0] == 'spaceship':
                self.game_state['spaceship'] = self.import_space_obj(key_value, line_counter)

            else: #not space_object
                try: #convert value to int
                    self.game_state[key] = int(key_value[1])
                except ValueError:
                    raise ValueError(f'Error: invalid data type in line {line_counter}')

            #certain keys indicate space_objects are in the following lines
            if key in ('asteroids_count', 'bullets_count', 'upcoming_asteroids_count'):
                #check type of space_object
                #generate list of accepted keys
                if key == 'asteroids_count':
                    key_ls = ['asteroid_small', 'asteroid_large']
                elif key == 'bullets_count':
                    key_ls = ['bullet']
                else:
                    key_ls = ['upcoming_asteroid_small', 'upcoming_asteroid_large']

                for _ in range(self.game_state[key]): #expected number of objects
                    line_counter += 1
                    space_obj_key_value = self.get_key_value(key_ls, f, line_counter)
                    space_obj = self.import_space_obj(space_obj_key_value, line_counter)
                    if key_value[0] == 'asteroids_count':
                        self.asteroid_ls.append(space_obj)
                    elif key_value[0] == 'bullets_count':
                        self.bullet_ls.append(space_obj)
                    else:
                        self.upcoming_asteroid_ls.append(space_obj)

        #Check EOF                
        line_counter +=1
        key_value = f.readline().strip().split(' ')
        if key_value != ['']:
            raise ValueError(f'Error: unexpected key: {key_value[0]} in line {line_counter}')
        f.close()
        f.close()

        
        #update bullet id counter
        self.bullet_id_counter = max([bullet.id for bullet in self.bullet_ls], default = -1)

        #max fuel
        self.max_fuel = self.game_state['fuel']


    def export_state(self, game_state_filename):
        
        f = open(game_state_filename, 'w')
        for key in self.game_state:
            if key == 'spaceship':
                f.write(str(self.game_state['spaceship']) + '\n')
            else:
                f.write(f'{key} {self.game_state[key]}\n')

                if key == 'asteroids_count':
                    for asteroid in self.asteroid_ls:
                        f.write(str(asteroid) + '\n')
                elif key == 'bullets_count':
                    for bullet in self.bullet_ls:
                        f.write(str(bullet) + '\n')
                elif key == 'upcoming_asteroids_count':
                    for asteroid in self.upcoming_asteroid_ls:
                        f.write('upcoming_' + str(asteroid) + '\n')
        
        f.close()

    def run_game(self):

        Done = False
        while not Done:
            # 1. Receive player input -> (thrust, left, right, bullet)
            player_input = self.player.action(self.game_state['spaceship'], 
                                            self.asteroid_ls, 
                                            self.bullet_ls, 
                                            self.game_state['fuel'], 
                                            self.game_state['score'])
            thrust, left, right, bullet = player_input
            # 2. Process game logic
            # Player movement input
            if left:
                self.game_state['spaceship'].turn_left()
            if right:
                self.game_state['spaceship'].turn_right()
            if thrust:
                self.game_state['spaceship'].move_forward()

            bullet_shot = False #variable to keep track of bullet firing for deducting fuel later
            if bullet: #attempt shoot bullet
                if self.game_state['fuel'] < config.shoot_fuel_threshold: #not enough fuel
                    print('Cannot shoot due to low fuel')
                else: #bullet succesfully shot
                    #inherit spaceship position
                    new_bullet_x, new_bullet_y = self.game_state['spaceship'].get_xy()
                    new_bullet_angle = self.game_state['spaceship'].angle

                    self.bullet_id_counter += 1
                    new_bullet = SpaceObject(
                        new_bullet_x, new_bullet_y, self.game_state['width'], 
                        self.game_state['height'], new_bullet_angle, 'bullet', 
                        self.bullet_id_counter)

                    self.bullet_ls.append(new_bullet) #add bullet to list
                    self.game_state['bullets_count'] += 1
                    bullet_shot = True

            #Update positions asteroids, bullets
            for asteroid in self.asteroid_ls:
                asteroid.move_forward()

            bullet_ls_2 = self.bullet_ls.copy() #create copy to iterate through
            for bullet in bullet_ls_2:
                if bullet.move_count >= config.bullet_move_count:
                    self.bullet_ls.remove(bullet)
                    self.game_state['bullets_count'] -= 1
                else:
                    bullet.move_forward()
            #Deduct fuel
            if bullet_shot: #use variable rather than player input as attempt 
                            #to shoot can fail
                self.game_state['fuel'] -= config.bullet_fuel_consumption
            self.game_state['fuel'] -= config.spaceship_fuel_consumption

            #Fuel warning
            percent_fuel = self.game_state['fuel']/self.max_fuel * 100
            
            if self.fuel_warning_count < len(config.fuel_warning_threshold):
                current_fuel_warn_thresh = config.fuel_warning_threshold[self.fuel_warning_count]
                if percent_fuel <= current_fuel_warn_thresh:
                    #triple quotes to avoid conflict with dict key
                    print(f'''{current_fuel_warn_thresh:02}% fuel warning: ''' 
                        f'''{self.game_state['fuel']} remaining''')
                    self.fuel_warning_count += 1

            elif self.game_state['fuel'] <= 0:
                Done = True

            #Detect collisions bullet v asteroid
            #asteroid_ls as main loop as low asteroid id takes priority
            asteroid_ls_2 = self.asteroid_ls.copy() #create copy to iterate through
            for asteroid in asteroid_ls_2: 
                for bullet in self.bullet_ls:
                    if bullet.collide_with(asteroid):
                        if asteroid.obj_type == 'asteroid_small':
                            self.game_state['score'] += config.shoot_small_ast_score
                        else:
                            self.game_state['score'] += config.shoot_large_ast_score
                        print(f'''Score: {self.game_state['score']} \t '''
                            f'''[Bullet {bullet.id} has shot asteroid {asteroid.id}]''')
                        self.asteroid_ls.remove(asteroid)
                        self.bullet_ls.remove(bullet)
                        self.game_state['bullets_count'] -= 1
                        break

            #asteroid v spaceship
            asteroid_ls_2 = self.asteroid_ls.copy()
            for asteroid in asteroid_ls_2:
                if asteroid.collide_with(self.game_state['spaceship']):
                    self.game_state['score'] += config.collide_score
                    print(f'''Score: {self.game_state['score']} \t [Spaceship'''
                        f''' collided with asteroid {asteroid.id}]''')
                    self.asteroid_ls.remove(asteroid)

            #Replenish asteroids
            while len(self.asteroid_ls) < self.game_state['asteroids_count']:
                if len(self.upcoming_asteroid_ls) == 0: #check if any asteroids available
                    self.game_state['asteroids_count'] = len(self.asteroid_ls)
                    Done = True #end game if no asteroids
                    print('Error: no more asteroids available')
                    break
                self.asteroid_ls.append(self.upcoming_asteroid_ls.pop(0))
                print(f'Added asteroid {self.asteroid_ls[-1].id}')
                self.game_state['upcoming_asteroids_count'] -= 1



            # 3. Draw the game state on screen using the GUI class
            self.GUI.update_frame(
                self.game_state['spaceship'], 
                self.asteroid_ls, 
                self.bullet_ls, 
                self.game_state['score'], 
                self.game_state['fuel'])


        # Display final score
        self.GUI.finish(self.game_state['score'])

    def get_key_value(self, key_ls, file, line_num):
        '''reads line in file and returns key_value pair as tuple'''
        key_value = file.readline().strip().split(' ')

        #checking for exceptions
        if key_value == ['']: #empty line/EOF
            raise ValueError("Error: game state incomplete")
        if len(key_value) < 2:
            raise ValueError(f'Error: expecting a key and value in line {line_num}')
        if len(key_value) > 2:
            raise ValueError(f'Error: invalid data type in line {line_num}')
        if key_value[0] not in key_ls:
            raise ValueError(f'Error: unexpected key: {key_value[0]} in line {line_num}')

        return key_value

    def import_space_obj(self, key_value, line_num = None):
        '''takes key_value tuple, initializes and return space_object'''

        space_obj_attr = key_value[1].split(',')
        if len(space_obj_attr) != 4:
            raise ValueError(f'Error: invalid data type in line {line_num}')
        
        try:
            x = float(space_obj_attr[0])
            y = float(space_obj_attr[1])
            angle = int(space_obj_attr[2])
            id = int(space_obj_attr[3])
        except ValueError:
            raise ValueError(f'Error: invalid data type in line {line_num}')

        if key_value[0] == 'spaceship':
            obj_type = 'spaceship'
        elif key_value[0] == 'bullet':
            obj_type = 'bullet'
        elif key_value[0] in ('asteroid_small', 'upcoming_asteroid_small'):
            obj_type = 'asteroid_small'
        else:
            obj_type = 'asteroid_large'

        return SpaceObject(x, y, self.game_state['width'], 
                        self.game_state['height'], angle, obj_type, id)
