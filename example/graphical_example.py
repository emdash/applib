import goocanvas
import gtk
import gobject
from basemodel import BaseModel, property
import math

# a model for time
class Time(BaseModel):

    time = property(0.0)

# a model for a shape defined with in a box
class Shape (BaseModel):

    x = property()
    y = property()
    width = property()
    height = property()

# represents shapes as a rectangle. when a shape's property is updated, we
# update the corresponding graphical property
class ShapeItem (goocanvas.Rect):

    def __init__(self, shape):
        goocanvas.Rect.__init__(self,
            x = shape.x,
            y = shape.y,
            width = shape.width,
            height = shape.height)
        self.shape = shape
        shape.connect("attribute-changed", self._updateAttribute)

    def _updateAttribute(self, shape, attrname, old, new):
        self.set_property(attrname, new)

# creates a timer
time = Time()
def increment_time():
    # setting this property here triggers an update of all the properties
    # which depend on time, even indirectly
    time.time += 10
    return True
gobject.timeout_add(50, increment_time)

shape1 = Shape()
# define x as a sawtooth function over time (moves to the right but wraps
# around when it reaches the edge of the window
shape1.x = lambda : (time.time / 2) % 200
shape1.y = 50
# make the shape expand and contract smoothly to a maximum of 100 pixels
# square
shape1.width = lambda : 50 * math.sin(time.time / 100.0) + 50
shape1.height = lambda : 50 * math.sin(time.time / 100.0) + 50

shape2 = Shape()
# the second shape is centered within the first shape
shape2.x = lambda : (shape1.width / 2) - 5 + shape1.x
shape2.y = lambda : (shape1.height / 2) - 5 + shape1.y
shape2.width = 10
shape2.height = 10

c = goocanvas.Canvas()
c.props.automatic_bounds = True
c.get_root_item().add_child(ShapeItem(shape2))
c.get_root_item().add_child(ShapeItem(shape1))
w = gtk.Window()
w.set_size_request(200, 200)
w.add(c)
w.show_all()
w.connect("destroy", gtk.main_quit)
gtk.main()
