from observable import Observable
import types

def private(attrname):
        return "_" + attrname + "_private"

def signame(attrname):
    return attrname + "-changed"

class property_descriptor(object):

    prop_access = []
    n_checkpoints = 0

    def __init__(self, name):
        self.name = name
        self.attrname = private(name)
        self.funcattrname = private(name) + '_func'
        self.signame = signame(name)

    def __set__(self, instance, value):
        oldvalue = getattr(instance, self.attrname)
        if oldvalue != value:
            setattr(instance, self.attrname, value)
            if isinstance(value, types.FunctionType):
                self._initialize_constraint(instance, value, oldvalue)
            else:
                self._remove_constraint(instance)
                instance.emit("attribute-changed", self.name, oldvalue, value)
                instance.emit(self.signame, oldvalue, value)

    def __get__(self, instance, cls):
        self.push_prop_access(self, instance)
        return getattr(instance, self.attrname)

    def _initialize_constraint(self, instance, function, oldvalue):
        setattr(instance, self.funcattrname, function)

        checkpoint = self.checkpoint()
        value = function()
        dependencies = self.pop_prop_access(checkpoint)

        setattr(instance, self.attrname, value)

        for prop, object in dependencies:
            self.addDependency(prop, object, instance)

        instance.emit("attribute-changed", self.name, oldvalue, value)
        instance.emit(self.signame, oldvalue, value)

    def _remove_constraint(self, instance):
        pass

    def addDependency(self, prop, object, instance):
        sigid = object.connect(prop.signame, self._updateValue, instance)

    def _updateValue(self, sender, old, new, instance):
        oldvalue = getattr(instance, self.attrname)
        value = getattr(instance, self.funcattrname)()
        setattr(instance, self.attrname, value)
        instance.emit("attribute-changed", self.name, oldvalue,
            value)
        instance.emit(self.signame, oldvalue, value)

## Totally not threadsafe

    @classmethod
    def push_prop_access(cls, property, instance):
        if cls.n_checkpoints > 0:
            cls.prop_access.append((property, instance))

    @classmethod
    def checkpoint(cls):
        cls.n_checkpoints += 1
        return len(cls.prop_access)

    @classmethod
    def pop_prop_access(cls, checkpoint):
        cls.n_checkpoints -= 1
        values = cls.prop_access[checkpoint:]
        del cls.prop_access[checkpoint:]
        return values

class property(object):

    def __init__(self, default=None):
        self.default = default

class BaseMeta(type):

    def __new__(self, name, bases, dict):
        # get a list of all the properties the user installed
        properties = [attr for attr, obj in
            dict.iteritems()
                if isinstance(obj, property)]

        # we do it this way to avoid modifying dict while iterating it
        if not "__signals__" in dict:
            dict["__signals__"] = {}
        signals = dict["__signals__"]

        deferred = {}
        dict["__deferred__"] = deferred

        for prop in properties:
            dict["__properties__"] = properties

            # don't set the default value for functions yet
            if isinstance(dict[prop].default, types.FunctionType):
                deferred[prop] = dict[prop].default
            else:
                dict[private(prop)] = dict[prop].default
            dict[prop] = property_descriptor(prop)
            signals[signame(prop)] = ["new", "old"]

        return type.__new__(self, name, bases, dict)


class BaseModel(Observable):

    """The base class for all model objects in the PyModel framework. This
    class provides automatic support for undo and file serialization provided
    that certain rules are adhered to."""

    __metaclass__ = BaseMeta

    __signals__ = {
        "attribute-changed": ("name", "old_value", "new_value"),
        "child-added": ("child",),
        "child-removed": ("child",),
    }

    __name__ = "BaseModel"

    def __init__(self):
        self.__children = []
        for prop, function in self.__deferred__.iteritems():
            method = types.MethodType(function, self, self.__class__)
            setattr(self, prop, value)

    def add_child(self, child):
        assert isinstance(child, BaseModel)
        self.__children.append(child)
        self.emit("child-added", child)

    def remove_child(self, child):
        self.__children.remove(child)
        self.emit("child-removed", child)

    def iter_children(self):
        return iter(self.__children)

    def iter_attributes(self):
        return self.__attributes.iteritems()
