import math
import config

class SpaceObject:
    def __init__(self, x, y, width, height, angle, obj_type, id):
        
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.angle = angle
        self.obj_type = obj_type
        self.id = id
        self.radius = config.radius[self.obj_type]
        if self.obj_type == 'bullet':
            self.move_count = 0 #for tracking age of bullet objects

    def turn_left(self):
        #modulo, % operator, keeps 0 <= angle < 360
        self.angle = (self.angle + config.angle_increment) % 360

    def turn_right(self):
        self.angle = (self.angle - config.angle_increment) % 360

    def move_forward(self):
        if self.obj_type == 'bullet': #add 1 to age of bullet
            self.move_count += 1
        speed  = config.speed[self.obj_type]
        
        #movement is a vector with direction as object.angle and magnitude = 
        #object speed, so cos() gives change in x and sin() change in y
        #angles in deg must be converted to rad
        self.x = (self.x + speed*math.cos(math.radians(self.angle))) % self.width
        self.y = (self.y - speed*math.sin(math.radians(self.angle))) % self.height
        # % operator enables wraparound, and restricts x,y in width,height

    def get_xy(self):
        return (self.x, self.y)

    def collide_with(self, other):
        #wraparound means we must consider x,y diff in two directions and
        #take the minimum of each
        x_diff = min(abs(self.x - other.x), self.width-abs(self.x - other.x))
        y_diff = min(abs(self.y - other.y), self.height-abs(self.y - other.y))

        #use pythagoras to calculate distance
        dst = math.sqrt(x_diff * x_diff + y_diff * y_diff)

        #collision distance is sum of radii
        dst_limit = config.radius[self.obj_type] + config.radius[other.obj_type]

        if dst <= dst_limit:
            return True
        return False

    def __repr__(self):
        return f'{self.obj_type} {self.x:01.1f},{self.y:01.1f},{self.angle},{self.id}'