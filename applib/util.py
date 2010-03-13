import gtk
import sys
import goocanvas

## GTK Conveinence Functions

def _normalize(self, p1, p2):
    w, h = p2 - p1
    x, y = p1
    if w < 0:
        w = abs(w)
        x -= w
    if h < 0:
        h = abs(h)
        y -= h
    return (x, y), (w, h)


def widget_helper(klass, func=None, *args, **kwargs):
    """Used to create convenience functions like scrolled()"""
    def retfunc(*children, **properties):
        properties.update(kwargs)
        ret = klass(*args)
        for child in children:
            if func:
                func(ret, child)
            else:
                ret.add(child)
        width = properties.setdefault("width", -1)
        height = properties.setdefault("height", -1)
        del properties["width"]
        del properties["height"]
        ret.set_size_request(width, height)
        for p in properties.iteritems():
            ret.set_property(*p)

        return ret
    return retfunc

def boxhelper(container, child):
    """Used to create convinience functions like HBox() and VBox()"""
    widget, end, expand, fill = child
    if end == 'end':
        container.pack_end(widget, expand, fill)
    elif end == 'start':
        container.pack_start(widget, expand, fill)
    else:
        container.add(widget)

def tbhelper(tb, item):
    tb.insert(item, -1)

scrolled = widget_helper(gtk.ScrolledWindow,
    vscrollbar_policy=gtk.POLICY_AUTOMATIC,
    hscrollbar_policy=gtk.POLICY_AUTOMATIC)
viewport = widget_helper(gtk.Viewport)
hbox = widget_helper(gtk.HBox, boxhelper)
hbuttonbox = widget_helper(gtk.HButtonBox)
vbuttonbox = widget_helper(gtk.VButtonBox)
vbox = widget_helper(gtk.VBox, boxhelper)
vpane = widget_helper(gtk.VPaned)
hpane = widget_helper(gtk.HPaned)
toolbar = widget_helper(gtk.Toolbar, tbhelper)
toolitem = widget_helper(gtk.ToolItem)
window = widget_helper(gtk.Window)

## utility functions for working with points
def event_coords(canvas, event):
    """returns the coordinates of an event"""
    return canvas.convert_from_pixels(canvas.props.scale_x * event.x, 
        canvas.props.scale_y * event.y)

def pixel_coords(canvas, point):
    return canvas.convert_from_pixels(canvas.props.scale_x * point[0], 
        canvas.props.scale_y * point[1])

def point_difference(p1, p2):
    """Returns the 2-dvector difference p1 - p2"""
    p1_x, p1_y = p1
    p2_x, p2_y = p2
    return (p1_x - p2_x, p1_y - p2_y)

def point_sum(p1, p2):
    """Returns the 2d vector sum p1 + p2"""
    p1_x, p1_y = p1
    p2_x, p2_y = p2
    return (p1_x + p2_x, p1_y + p2_y)

def scalar_mul(factor, point):
    """Returns a scalar multiple factor * point"""
    return tuple(factor * v for v in point)

def point_mul(p1, p2):
    p1_x, p1_y = p1
    p2_x, p2_y = p2
    return (p1_x * p2_x, p1_y * p2_y)

def point_div(p1, p2):
    p1_x, p1_y = p1
    p2_x, p2_y = p2
    return (p1_x / p2_x, p1_y / p2_y)

## Base Classes
## Most of the following code is experimental. I'm trying to see how to use
## python to support true MVC programming.

# this is a python decorator which specifies that the following function is
# to be considered a signal handler. Basically this just adds the function's
# name to the class's 'handlers' dictionary. Unfortunately I had to do some
# runtime hacks to make this work. 
# TODO: find a cleaner way to implement this
# TODO: parameterize this into a factory, passing in the signal name so we can
# name our signal handlers arbitrarily.

def handler(method):
    """adds a signal handler to the current object"""
    frame = sys._getframe(1)
    try:
        locals = frame.f_locals
        handlers = locals.setdefault("_handlers", {})
    finally:
        del frame
    handlers[method.__name__] = None
    return method

# Similar to the view class, this keeps track of the view in a similar manner
# to the way view keeps track of the model. We need to do this because it is
# actually the view in gtk which receives events. Subclasses can define which
# signals they want to receive from view by simply defining functions with the
# same name as the signal, prefixed with the @handler decorator.

class BaseController(object):

    """Default controller for children of BaseView. Provides an easy way to
    connect to gobject signals."""

    _view = None
    _model = None
    _handlers = {}
    _transform = None

    def __init__(self, model=None, view=None, *args, **kwargs):
        super(BaseController, self).__init__(*args, **kwargs)
        self.setModel(model)
        self.setView(view)

    def setModel(self, model):
        self._model = model

    def setView(self, view):
        """Set the view and connect to any registered handlers"""
        if self._view:
            for sigid in self._handlers.itervalues():
                self._view.disconnect(sigid)
            self._view = None
        if view:
            self._view = view
            self._transform = view.getTransform()
            for signal in self._handlers:
                id = view.connect(signal, getattr(self, signal))
                self._handlers[signal] = id

# This is a mixin class which is designed to facilitate connecting to the
# model. Child classes can specify which signals they wish to receive from the
# model by defining methods with the same name as the signal, prefixed with
# the @handler decorator. When the model is changed, the appropriate signals
# are automatically connected and disconnected.

class BaseView(object):
    
    _model = None
    _handlers = {}
    _controller = None
    _transform = None
    Controller = BaseController

    def __init__(self, model=None, transform=None, *args, **kwargs):
        super(BaseView, self).__init__(*args, **kwargs)
        if not transform:
            transform = WindowingTransformation()
        self._transform = transform
        self._controller = self.Controller(view=self)
        self.setModel(model)
        self.normal()

    def getTransform(self):
        return self._transform

    def setModel(self, model):
        """Set the model and connect to any registered handlers"""
        if self._model:
            for sigid in self._handlers.itervalues():
                self._model.disconnect(sigid)
            self._model = None
            self._controller.setModel(None)
        if model:
            self._model = model
            for signal in self._handlers:
                id = model.connect(signal, getattr(self, signal))
                self._handlers[signal] = id
            self._controller.setModel(model)

    def getModel(self):
        return self._model

    # implementation interface for base view. Subclasses should
    # implement these methods

    def focus(self):
        pass

    def select(self):
        pass

    def activate(self):
        pass

    def normal(self):
        pass

# Controllers are reusable and implement specific behaviors. Currently this
# Includes only click, and drag. Multiple controllers could be attached to a
# given view, but might interfere with each other if they attempt to handle
# the same set of signals. It is probably better to define a new controller
# that explictly combines the functionality of both when custom behavior is
# desired.

#TODO: refactor to handle cursors

class DragController(BaseController):

    """A controller which implements drag-and-drop bahavior on connected view
    objects. Subclasses may override the drag_start, drag_end, pos, and
    set_pos methods"""

    _dragging = None
    _canvas = None
    _mouse_down = None
    _ptr_within = False
    _last_click = None

    def drag_start(self):
        pass

    def drag_end(self):
        pass

    def _drag_start(self, item, target, event):
        self._view.activate()
        self.drag_start()

    def _drag_end(self, item, target, event):
        self.drag_end()
        if self._ptr_within:
            self._view.focus()
            if self._last_click and (event.time - self._last_click < 400):
                self.double_click(event_coords(self._canvas, event))
            else:
                self.click(event_coords(self._canvas, event))
            self._last_click = event.time
        else:
            self._view.normal()

    def click(self, pos):
        pass

    def double_click(self, pos):
        pass

    def set_pos(self, obj, pos):
        obj.props.x, obj.props.y = pos

    def pos(self, obj):
        return obj.props.x, obj.props.y

    def transform(self, pos):
        return pos

    def enter(self, item, target):
        if not self._dragging:
            self._view.focus()

    def leave(self, item, target):
        if not self._dragging:
            self._view.normal()

    @handler
    def enter_notify_event(self, item, target, event):
        self.enter(item, target)
        self._ptr_within = True
        return True

    @handler
    def leave_notify_event(self, item, target, event):
        self._ptr_within = False
        if not self._dragging:
            self.leave(item, target)
        return True

    @handler
    def button_press_event(self, item, target, event):
        if not self._canvas:
            self._canvas = item.get_canvas()
        self._dragging = target
        self._mouse_down = point_difference(
            self.pos(self._view),
                self.transform(
                    event_coords(self._canvas, event)))
        self._drag_start(item, target, event)
        return True

    @handler
    def motion_notify_event(self, item, target, event):
        if self._dragging:
            self.set_pos(self._dragging, 
                self.transform(point_sum(self._mouse_down,
                    event_coords(self._canvas, event))))
            return True
        return False

    @handler
    def button_release_event(self, item, target, event):
        self._drag_end(item, self._dragging, event)
        self._dragging = None
        return True

class ClickController(DragController):

    def set_pos(self, obj, pos):
        pass

# This is an idea i got from reading an article on SmallTalk MVC. 
# FIXME/TODO: do we really need windoing transformation? or would just the
# coordinate system class be enough. Then you could have
# view.cs.convertTo(point, model.cs) or something similar.

class WindowingTransformation(object):

    """Represents a transformation between two arbitrary 2D coordinate system"""

    class System(object):

        def __init__(self, *args, **kwargs):
            object.__init__(self)

        def setBounds(self, min, max):
            self._min = min
            self._max = max
            self._range = point_difference(max, min)

        def getMin(self):
            return self._min

        def getRange(self):
            return self._range

        def convertTo(self, point, other):
            # ((point - min) * other.range / (self.range)) + other.min) 
            return point_sum(
                point_div(
                    point_mul(
                        point_difference(point, self._min), 
                        other.getRange()),
                self._range), 
                other.getMin())

    def __init__(self, A=None, B=None, *args, **kwargs):
        super(WindowingTransformation, self).__init__(*args, **kwargs)
        self._A = self.System()
        self._B = self.System()

    def setBounds(self, a, b):
        self._A.setBounds(*a)
        self._B.setBounds(*b)

    def aToB(self, point):
        return self._A.convertTo(point, self._B)

    def bToA(self, point):
        return self._B.convertTo(point, self._A)

