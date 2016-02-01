"""
A Physics module built from clean-rooming the Notchian Minecraft client

Collision detection and resolution is done by a Separating Axis Theorem
implementation for concave shapes decomposed into Axis-Aligned Bounding Boxes.
This isn't totally equivalent to vanilla behavior, but it's faster and
Close Enough^TM

AKA this file does Minecraft physics
"""

import collections
import math

from spockbot.mcdata import blocks, constants as const
from spockbot.mcdata.utils import BoundingBox
from spockbot.plugins.base import PluginBase, pl_announce
from spockbot.plugins.tools import collision
from spockbot.vector import Vector3

FP_CLOSE = 1e-4


class PhysicsCore(object):
    def __init__(self, pos, vec, abilities):
        self.pos = pos
        self.vec = vec
        self.sprinting = False
        self.move_accel = abilities.walking_speed
        self.abilities = abilities
        self.direction = Vector3()

    def jump(self, horse_jump_boost=100):
        if mounted:
            self.interact._entity_action(const.ENTITY_ACTION_JUMP_HORSE,
                                         horse_jump_boost)
        # xxx
        if self.pos.on_ground:
            if self.sprinting:
                ground_speed = Vector3(self.vec.x, 0, self.vec.z)
                if ground_speed:
                    self.vec += ground_speed.norm() * const.PHY_JMP_MUL
            self.vec.y = const.PHY_JMP_ABS

    def walk(self):
        if self.sprinting:
            self.interact._entity_action(const.ENTITY_ACTION_STOP_SPRINT)
        self.sprinting = False
        self.move_accel = self.abilities.walking_speed

    def sprint(self):
        if not self.sprinting:
            self.interact._entity_action(const.ENTITY_ACTION_START_SPRINT)
        self.sprinting = True
        self.move_accel = self.abilities.walking_speed * const.PHY_SPR_MUL

    # TODO sneaking?

    def move_target(self, vector):
        self.direction = vector - self.pos
        self.direction.y = 0
        if self.direction <= Vector3(self.vec.x, 0, self.vec.z):
            return True

    def move_vector(self, vector):
        vector.y = 0
        self.direction = vector

    def move_angle(self, angle, radians=False):
        angle = angle if radians else math.radians(angle)
        self.direction = Vector3(math.sin(angle), 0, math.cos(angle))


@pl_announce('Physics')
class PhysicsPlugin(PluginBase):
    requires = ('Event', 'ClientInfo', 'Interact', 'Net', 'World')
    events = {
        'physics_tick': 'physics_tick',
        'client_tick': 'client_tick',
        'client_position_update': 'skip_physics',
    }

    def __init__(self, ploader, settings):
        super(PhysicsPlugin, self).__init__(ploader, settings)
        self.vec = Vector3(0.0, 0.0, 0.0)
        self.col = collision.MTVTest(
            self.world, BoundingBox(const.PLAYER_WIDTH, const.PLAYER_HEIGHT)
        )
        self.pos = self.clientinfo.position
        self.skip_tick = False
        self.pc = PhysicsCore(self.pos, self.vec, self.clientinfo.abilities)
        ploader.provides('Physics', self.pc)

    def skip_physics(self, *_):
        self.vec.zero()
        self.skip_tick = True

    def client_tick(self, name, data):
        if self.clientinfo.mounted:
            self.net.push_packet('PLAY>Player Look',
                                 self.clientinfo.position.get_dict())
            self.net.push_packet('PLAY>Steer Vehicle', {
                'sideways': 0.0,
                'forward': self.pc.direction.dist(),
                'flags': 0,  # xxx no jump/unmount
            })
        else:
            self.net.push_packet('PLAY>Player Position and Look',
                                 self.clientinfo.position.get_dict())

    def physics_tick(self, *_):
        if self.skip_tick:
            self.skip_tick = False
            return

        if self.clientinfo.mounted:
            self.interact.look_at_rel(self.pc.direction)
            # xxx all other calculations done in client_tick
        else:
            self.apply_accel()
            mtv = self.get_mtv()
            self.apply_vector(mtv)
            self.pos.on_ground = mtv.y > 0
            self.vec -= Vector3(0, const.PHY_GAV_ACC, 0)
            self.apply_drag()

        self.pc.direction = Vector3()

    def get_block_slip(self):
        if self.pos.on_ground:
            bpos = self.pos.floor()
            return blocks.get_block(*self.world.get_block(*bpos)).slipperiness
        return 1

    def apply_accel(self):
        if not self.pc.direction:
            return
        if self.pos.on_ground:
            block_slip = self.get_block_slip()
            accel_mod = const.BASE_GND_SLIP**3 / block_slip**3
            accel = self.pc.move_accel * accel_mod * const.PHY_BASE_DRG
        else:
            accel = const.PHY_JMP_ACC
        self.vec += self.pc.direction.norm() * accel

    def apply_vector(self, mtv):
        self.pos += (self.vec + mtv)
        self.vec.x = 0 if mtv.x else self.vec.x
        self.vec.y = 0 if mtv.y else self.vec.y
        self.vec.z = 0 if mtv.z else self.vec.z

    def apply_drag(self):
        drag = self.get_block_slip() * const.PHY_DRG_MUL
        self.vec.x *= drag
        self.vec.z *= drag
        self.vec.y *= const.PHY_BASE_DRG

    # Breadth-first search for a minimum translation vector
    def get_mtv(self):
        pos = self.pos + self.vec
        pos = collision.uncenter_position(pos, self.col.bbox)
        q = collections.deque((Vector3(),))
        while q:
            current_vector = q.popleft()
            transform_vectors = self.col.check_collision(pos, current_vector)
            if not all(transform_vectors):
                break
            for vector in transform_vectors:
                test_vec = self.vec + current_vector + vector
                if test_vec.dist_sq() <= self.vec.dist_sq() + FP_CLOSE:
                    q.append(current_vector + vector)
        else:
            self.event.emit('physics_bail')
            self.vec.zero()
            return Vector3()
        possible_mtv = [current_vector]
        while q:
            current_vector = q.popleft()
            transform_vectors = self.col.check_collision(pos, current_vector)
            if not all(transform_vectors):
                possible_mtv.append(current_vector)
        return min(possible_mtv)
