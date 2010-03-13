import unittest
import basemodel as basemodel

TestCase = unittest.TestCase

class MyModel(basemodel.BaseModel):

    foo = basemodel.property("foo")
    bar = basemodel.property()
    baz = basemodel.property()

    def __init__(self):
        basemodel.BaseModel.__init__(self)
        self.bar = "bar"
        self.baz = "baz"

class MyModelTwo(MyModel):

    @basemodel.property
    def baz(self):
        return self.foo + self.bar

    def __init__(self):
        self.bar = "bar"
        self.baz = lambda : self.foo + self.bar

class MyModelThree(MyModel):

    def __init__(self):
        self.bar = lambda : self.foo + "bar"
        self.baz = lambda : self.bar + "baz"

class TestBaseModel (TestCase):

    def setUp(self):
        self.attrchangedcount = 0
        self.foochangedcount = 0
        self.children = []

    def attrChanged(self, model, propname, oldvalue, newvalue):
        self.attrchangedcount += 1

    def fooChanged(self, instance, oldvalue, newvalue):
        self.foochangedcount += 1

    def childAdded(self, model, child):
        self.children.append(child)

    def childRemoved(self, model, child):
        self.children.remove(child)

    def testBaseModelProperties(self):
        m = MyModel()
        m.connect ("attribute-changed", self.attrChanged)

        m.foo = "bar"

        self.failUnlessEqual(self.attrchangedcount, 1)

        m.bar = "quux"
        self.failUnlessEqual(self.attrchangedcount, 2)

        m2 = MyModel()
        m2.foo = "asfkjadsklfj"
        self.failIfEqual(m.foo, m2.foo)

        m.foo = "bar"
        # shouldn't emit a signal if property value hasn't changed
        self.failUnlessEqual(self.attrchangedcount, 2)

    def testAddRemoveChildren(self):
        m = MyModel()
        m.connect("child-added", self.childAdded)
        m.connect("child-removed", self.childRemoved)

        m2 = MyModel ()
        m.add_child(m2)

        self.failUnlessEqual(self.children, [m2])
        self.failUnlessEqual(list(m.iter_children()), [m2])
        m.remove_child(m2)
        self.failUnlessEqual(self.children, [])
        self.failUnlessEqual(list(m.iter_children()), [])

    def testConstraints(self):
        m = MyModelTwo()
        m.connect("attribute-changed", self.attrChanged)
        m.connect("baz-changed", self.fooChanged)

        self.failUnlessEqual(m.baz, "foobar")

        m.foo = "candy"

        self.failUnlessEqual(m.baz, "candybar")
        self.failUnlessEqual(self.attrchangedcount, 2)
        self.failUnlessEqual(self.foochangedcount, 1)

        m.bar = "cane"
        self.failUnlessEqual(m.baz, "candycane")
        self.failUnlessEqual(self.attrchangedcount, 4)
        self.failUnlessEqual(self.foochangedcount, 2)

        m3 = MyModelThree()

        self.failUnlessEqual(m3.bar, "foobar")
        self.failUnlessEqual(m3.baz, "foobarbaz")

        m3.foo = "candy"
        self.failUnlessEqual(m3.baz, "candybarbaz")

        m = MyModel()
        m.bar = lambda : m.foo + m3.bar
        self.failUnlessEqual(m.bar, "foocandybar")
        m.foo = "snickers"
        self.failUnlessEqual(m.bar, "snickerscandybar")


if __name__ == '__main__':
    print unittest.main()
