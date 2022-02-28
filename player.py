import math
import config

class Player:
    
    def __init__(self):
        self.width = None
        self.height = None
        #turning radius of spaceship is function of angle_increment and speed
        self.turning_radius = config.speed['spaceship'] / math.atan(config.angle_increment / 2) / 2
        #bullet range in terms of frames it take the spaceship to travel distance
        self.shoot_range = (config.bullet_move_count * config.speed['bullet'] //
                            config.speed['spaceship'])

    def action(self, spaceship, asteroid_ls, bullet_ls, fuel, score):
        #store screen width/height as Player instance attributes
        self.width = spaceship.width
        self.height = spaceship.height

        #sort asteroid list by distance from spaceship
        sort_key = lambda x:(self.wraparound_dist_angle(spaceship.get_xy(), 
                                                        x.get_xy()))
        asteroid_ls.sort(key=sort_key)

        #copy of asteroid_ls, which we can modify
        asteroid_ls2 = asteroid_ls.copy()

        #detects which asteroids will be destroyed by already fired bullets
        #we can ignore these asteroids
        for projectile in bullet_ls:
            bullet_used = False
            for asteroid in asteroid_ls2:
                #use bullet_move_count + 1 as bullet travels immediately when fired
                bullet_path = self.get_path(projectile, config.bullet_move_count +1)
                asteroid_path = self.get_path(asteroid, config.bullet_move_count +1)
                for i in range(1, config.bullet_move_count + 1):
                    if self.collide_with('bullet', bullet_path[i], 
                                        asteroid.obj_type, 
                                        asteroid_path[i]):
                        asteroid_ls2.remove(asteroid)
                        bullet_used = True
                        break
                if bullet_used:
                    break

        #initial return values
        thrust = False
        left = False
        right = False
        bullet = False

        if fuel >= config.shoot_fuel_threshold: #check can shoot
            if len(asteroid_ls2) > 0: #check if asteroids to be targeted

                thrust, turn = self.move(asteroid_ls2, spaceship) #pursue
                options = self.shoot(spaceship, asteroid_ls2) #shoot

                #try align shooting movement with path to next asteroid
                if options:
                    option_score_ls = []
                    for move, offset, asteroid in options:
                        asteroid_ls3 = asteroid_ls2.copy()
                        asteroid_ls3.remove(asteroid)
                        best_move, best_turn = self.move(asteroid_ls3, spaceship)
                        if move == best_move:
                            option_score = 0
                        else:
                            option_score = 1
                        option_score += abs(offset - best_turn)

                        option_score_ls.append((score, move, offset))
                    thrust, turn = min(option_score_ls, key=lambda x:(x[0], -x[1]))[1:3]
                    bullet = True

                #convert turn to left, right bool
                if turn == -1:
                    left = False
                    right = True
                elif turn == 0:
                    left = False
                    right = False
                else:
                    left = True
                    right = False

        else: #not enough fuel, actions are opposite of pursuing
            thrust, turn = self.move(asteroid_ls2, spaceship) #pursue
            thrust = not thrust
            if turn == 1: #turns right when pursue indicates asteroid close left
                left = False
                right = True
            elif turn == 0:
                left = False
                right = False
            else:
                left = True
                right = False


        return (thrust, left, right, bullet)

    def get_path(self, asteroid, frames):
        '''returns list of coords of an asteroid's path over a number of frames'''
        x0, y0 = asteroid.get_xy()
        obj_type, angle = asteroid.obj_type, asteroid.angle
        speed = config.speed[obj_type]
        path = []
        for frame in range(frames):
            x = (x0 + frame * speed * math.cos(math.radians(angle))) % self.width
            y = (y0 - frame * speed * math.sin(math.radians(angle))) % self.height
            path.append((x,y))
        return path

    def get_bullet_path(self, spaceship, offset, spaceship_move):
        '''return list of coords of a bullet's path, given spaceship's current
        position and the movement it can take'''
        x0, y0 = spaceship.get_xy()
        speed = config.speed['bullet']
        angle = (spaceship.angle + config.angle_increment*offset) % 360
        if spaceship_move:
            x0 += config.speed['spaceship'] * math.cos(math.radians(angle))
            y0 -= config.speed['spaceship'] * math.sin(math.radians(angle))
        path = []
        for frame in range(config.bullet_move_count + 1):
            x = (x0 + frame * speed * math.cos(math.radians(angle))) % self.width
            y = (y0 - frame * speed * math.sin(math.radians(angle))) % self.height
            path.append((x,y))
        return path


    def shoot(self, spaceship, asteroid_ls):
        '''Returns list of (thrust, turn) actions which would lead to a
        successful hit on an asteroid if bullet is fired. Returns empty list
        when no asteroid in range'''
        options = []
        for turn in (0,-1,1):
            for spaceship_move in (True,False):
                path = self.get_bullet_path(spaceship, turn, spaceship_move)
                for asteroid in asteroid_ls:
                    astr_path = self.get_path(asteroid, 
                                            config.bullet_move_count + 1)

                    for frame in range(1, config.bullet_move_count + 1):
                        if self.collide_with('bullet', 
                                            path[frame], 
                                            asteroid.obj_type, 
                                            astr_path[frame]):

                            options.append((spaceship_move, turn, asteroid))
        return options

    def collide_with(self, obj1_type, xy1, obj2_type, xy2):
        '''detects if two objects would collide given obj_types and coords'''
        dst, angle = self.wraparound_dist_angle(xy1, xy2)
        dst_limit = config.radius[obj1_type] + config.radius[obj2_type]
        if dst <= dst_limit:
            return True
        return False

    def adj_d_angle(self, spaceship, spaceship_xy, spaceship_angle, asteroid_xy):
        '''returns shortest vector between spaceship and asteroid taking into
        account the orientation of the spaceship and wraparound'''
        x1, y1 = spaceship_xy
        x2, y2 = asteroid_xy
        vec_ls = []
        #all possible dx and dy
        x_diff = [x2-x1, x2-x1 + self.width, x2-x1 - self.width]
        y_diff = [y2-y1, y2-y1 + self.height, y2-y1 - self.height]

        for dx in x_diff:
            if abs(dx) > self.width: #skip if dx > width
                continue
            for dy in y_diff:
                if abs(dy) > self.height: #skip if dy > height
                    continue
                vec_ls.append((dx, dy))

        best_frames = 9999 #placeholder value
        best_trajectory = []
        #stationary turns the spaceship should take before thrust is activated
        trajectory_turns = 0 
        for dx, dy in vec_ls:
            #use -dy in angle calculation because y axis is inverted
            angle = math.degrees(math.atan2(-dy, dx)) % 360
            dst = math.sqrt(dx**2 + dy**2) #pythagoras
            frames, turns = self.frame_estimate(spaceship, (dst, angle))

            #keep best trajectory
            if frames < best_frames:
                best_frames = frames
                best_trajectory = dst, angle
                trajectory_turns = turns
        
        return (best_trajectory, trajectory_turns, best_frames)
    
    
    def normalized_angle(self, spaceship_angle, angle_to_ast):
        '''calculates the angle the spaceship needs to turn to be facing the
        asteroid. Returns angle between -180 and 180'''
        diff = (angle_to_ast - spaceship_angle) % 360
        if diff > 180:
            diff -= 360
        return diff

    def wraparound_dist_angle(self, xy1, xy2):
        '''calculate distance and direction from xy1 to xy2'''
        x1, y1 = xy1
        x2, y2 = xy2
        x_diff = min(x2-x1, x2-x1 + self.width, x2-x1 - self.width, key=abs)
        y_diff = min(y2-y1, y2-y1 + self.height, y2-y1 - self.height, key=abs)
        angle = math.degrees(math.atan2(-y_diff, x_diff)) % 360
        dst = math.dist([0, 0], [x_diff, y_diff])
        return (dst, angle)

    def frame_estimate(self, spaceship, vector):
        '''estimates number of frames spaceship takes travel vector'''
        dist, angle = vector
        angle_to_astr = abs(self.normalized_angle(spaceship.angle, angle))
        '''Number of stationary turns (thrust = False), if thrust is True while
        not facing the asteroid we would be moving away.
        The ceiling divide (angle - 90) / 15 gives us how many turns it takes 
        to reduce the angle to less than 90'''
        turns = max( 0, -(-(angle_to_astr - 90) // 15) )
        #angle diff after stationary turns
        angle_to_astr %= 90

        best_frames = 9999 #placeholder
        while True:
            #p = center of rotation
            p_x = self.turning_radius * math.cos(math.radians(angle_to_astr - 90))
            p_y = self.turning_radius * math.sin(math.radians(angle_to_astr - 90))
            p_to_astr = math.sqrt(p_x**2 + (p_y - dist)**2 )
            dist_tangent = math.sqrt(p_to_astr**2 - self.turning_radius**2)

            turning_angle = math.degrees( math.atan( (dist - p_y) / (-p_x) ) + 
                                    math.acos(self.turning_radius / p_to_astr) )

            #See report
            frames = (-(-(dist_tangent // config.speed['spaceship'])) + 
                    -(-(turning_angle // config.angle_increment)) + turns)
            if frames >= best_frames:
                return best_frames, turns

            best_frames = frames
            turns += 1 #see if aditional stationary turns are an improvement
            angle_to_astr -= config.angle_increment

    def cost_estimate(self, spaceship, asteroid_ls, frames=1):
        '''finds best target in terrms of number of frames to reach target;
        returns vector to target, number of stationary turns, and cost'''
        #variables to store best path
        best_dst = None
        best_angle = None
        best_turns = None
        least_cost = None
        for asteroid in asteroid_ls:
            radius_speed = config.radius[asteroid.obj_type] // config.speed['spaceship']
            moves = max(1, int(frames))
            astr_xy = self.get_path(asteroid, moves)[moves -1]

            trajectory, turns, frames = self.adj_d_angle(spaceship, 
                                                        spaceship.get_xy(), 
                                                        spaceship.angle, 
                                                        astr_xy)
            dst, angle = trajectory
            #get moves it takes to reach shooting distance
            moves = max(1, int(frames - self.shoot_range - radius_speed))
            astr_xy = self.get_path(asteroid, moves)[moves -1]

            #recalculate trajectory based on new asteroid position
            trajectory, turns, frames = self.adj_d_angle(spaceship, 
                                                        spaceship.get_xy(), 
                                                        spaceship.angle, 
                                                        astr_xy)
            dst, angle = trajectory
            #get moves it takes to reach shooting distance to predicted asteroid pos
            moves = max(1, int(frames - self.shoot_range - radius_speed))
            #repeating and recalculating move and predicted asteroid position
            #should approach optimal solution, but for speed we only do it once
            #this does assume spaceship is faster than asteroids

            #store path if cost is lowest
            cost = frames
            if least_cost == None or cost < least_cost:
                least_cost = cost
                best_dst = dst
                best_angle = angle
                best_turns = turns

        return best_dst, best_angle, best_turns

    def move(self, asteroid_ls, spaceship):
        #handles no asteroids left to target
        if len(asteroid_ls) == 0:
            return (False, 0)

        #get vector to asteroid and stationary turns
        dst, angle, stat_turns = self.cost_estimate(spaceship, asteroid_ls)

        angle_diff = self.normalized_angle(spaceship.angle, angle)

        #turn to match vector direction
        if abs(angle_diff) < config.angle_increment/2:
            turn = 0
        elif angle_diff > 0:
            turn = 1
        else:
            turn = -1
        
        #stop moving forward if too close or moving forward is not optimal
        if (dst > 3*self.turning_radius or turn == 0) and stat_turns <= 1:
            thrust = True
        else:
            thrust = False
        
        return (thrust, turn)