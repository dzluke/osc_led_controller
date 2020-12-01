import abc
import numpy as np
import colorsys
import socket
import select
from LightingControl import *
from osc4py3.as_eventloop import *
from osc4py3 import oscbuildparse

class MixerInput(abc.ABC):
    """Represents an object to be passed to Mixer"""

    @abc.abstractmethod
    def update(self):
        """Update the object"""

    @abc.abstractmethod
    def value(self, x):
        """Get color value at a certain location"""


class GaussianPeak(MixerInput):
    ALPHA = 0.01

    def __init__(self,
                 bounds,
                 std,
                 pos=None,
                 vel=None,
                 color=None):

        self.bounds = bounds
        self.std = np.diag(1 / std)

        if color:
            self.color = color
        else:
            self.color = np.array(
                colorsys.hsv_to_rgb(
                    np.random.random(),
                    1,
                    1,
                )
            )

        if pos:
            self.pos = pos
        else:
            self.pos = np.random.random(bounds.shape) * bounds

        if vel:
            self.vel = vel
        else:
            self.vel = np.random.random(bounds.shape) * bounds

    def update(self):
        self.pos += self.ALPHA * self.vel

        # flip
        indices = (self.pos <= 0) + (self.pos >= self.bounds)
        indices = indices.astype(np.float32) * -2 + 1
        self.vel = self.vel * indices

    def value(self, x):
        x -= self.pos
        return self.color * np.exp(-1 * x.T @ self.std @ x)


class CNMAT_2DMixer:
    def __init__(self):
        self.bounds = np.array([8, 1])
        self.resolution = 47
        self.things = []

    def add(self,
            std,
            pos=None,
            vel=None,
            color=None):
        self.things.append(GaussianPeak(self.bounds, std, pos, vel, color))

    def universify(self, output, universe_size=512, num_strips_per_universe=3):
        universes = []
        while len(output.flatten()) > 0:
            universe = np.zeros(universe_size)
            flat = output[:num_strips_per_universe, :, :].flatten()
            universe[:len(flat)] = flat
            universes.append(universe)
            output = output[num_strips_per_universe:, :, :]
        return np.concatenate(universes)

    def update(self):
        for thing in self.things:
            thing.update()

    def value(self):
        x_base = np.linspace(0, self.bounds[1], self.resolution)
        output = np.empty((self.bounds[0], self.resolution, 3), dtype=np.int32)
        for i in range(self.bounds[0]):
            for j in range(self.resolution):
                val = sum([t.value(np.array([i, x_base[j]]))
                           for t in self.things])
                val = (val.clip(0, 1) * 256).astype(np.int32)
                output[i, j, :] = val
        return self.universify(output)


if __name__ == "__main__":
    # create send socket on port 7000
    # max : udpreceive 7000
    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_socket.connect(("localhost", 7000))

    mixer = CNMAT_2DMixer()
    for _ in range(20):
        mixer.add(np.array([.1, .1]))
    while True:
        output = mixer.value().tolist()
        send(send_socket, "/channels", output)
        mixer.update()

    # Properly close the system.
    send_socket.close()
    recv_socket.close()
