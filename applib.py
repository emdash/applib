import gtk
import os
import cPickle
from signalinterface import Signallable
from gettext import gettext as _

## Command Base Class  ------------------------------------------------------

class Command(object):

    undoable = True
    name = ""
    label = None
    tooltip = None
    stockid = None
    accelerator = None
    action_class = gtk.Action

    def __init__(self, app, action):
        self.app = app
        self.action = action

    def do(self):
        pass

    def redo(self):
        self.do()

    def undo(self):
        pass

    def is_valid(self):
        return True

## Document Base Class ------------------------------------------------------

class Document(object):

    def save(self, filename):
        raise NotImplementedError

    def getFilename(self):
        return None

    @classmethod
    def getDefaultFilename(self):
        return _("Untitled Document")

    @classmethod
    def createFromPath(self, path):
        raise NotImplementedError

## Application Base Class ---------------------------------------------------

class Application(object):

    __apname__ = "Application"
    __mainwindowclass__ = gtk.Window
    __documentclass__ = Document
    __documenteditorclass__ = None
    __configpath__ = os.path.expanduser("~/." + __apname__.lower())
    __defaultsettings__ = {
        "last_document_dir" : os.getcwd(),
    }

    __menus__ = [
        ("File", _("File")),
        ("Edit", _("Edit")),
        ("View", _("View")),
        ("Document", _("Document")),
    ]

    uistring = """
    <ui>
        <menubar name="mainmenubar">
            <menu action="File">
                <menuitem action="New"/>
                <menuitem action="Open"/>
                <separator />
                <menuitem action="Save"/>
                <menuitem action="SaveAs"/>
                <separator />
                <menuitem action="Quit"/>
            </menu>
            <menu action="Edit">
                <menuitem action="Undo"/>
                <menuitem action="Redo"/>
                <separator/>
                <menuitem action="Cut" />
                <menuitem action="Copy" />
                <menuitem action="Paste" />
                <menuitem action="Delete"/>
            </menu>
            <menu action="View">
            </menu>
            <menu action="Document">
            </menu>
        </menubar>
    </ui>"""

    def __init__(self):
        try:
            self.settings = cPickle.load(file(self.__configpath__, "r"))
        except:
            self.settings = dict(self.__defaultsettings__)

        self.uiman = gtk.UIManager()
        self.history_manager = HistoryManager()
        self.selection = Selection()
        self.clipboard = Clipboard()
        self.document = self._createDocument()
        self._initActions()
        self.uiman.add_ui_from_string(self.uistring)
        self.ui = self._createUI()
        self.selection = Selection()

    def newDocument(self):
        self.document = self._createDocument()

    def loadDocument(self):
        chooser = gtk.FileChooserDialog(_("Open ..."),
            parent=self.ui,
            action=gtk.FILE_CHOOSER_ACTION_OPEN,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_select_multiple(False)
        chooser.set_current_folder(self.settings["last_document_dir"])

        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            self._createDocument(chooser.get_filename())
            self.settings["last_document_dir"] = chooser.get_current_folder()
        chooser.destroy()

    def saveDocument(self):
        if not self.document.getFilename():
            self.saveDocumentAs()
        else:
            self._saveDocument(document)

    def saveDocumentAs(self):
        chooser = gtk.FileChooserDialog(_("Save Document File..."),
            self.ui,
            action=gtk.FILE_CHOOSER_ACTION_SAVE,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        chooser.set_select_multiple(False)

        folder = self.settings["last_document_dir"]
        name = self.document.getDefaultFilename()
        guess = os.path.join(folder, name)
        chooser.set_current_folder(folder)
        chooser.set_current_name(name)

        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            filename = chooser.get_filename()
            self.settings["last_document_dir"] = chooser.get_current_folder()
        else:
            filename = None
        chooser.destroy()

        self._saveDocument(filename)

    def _saveDocument(self, filename):
        self.document.save(filename)

    def _createDocument(self, path = None):
        if path:
            return self.__documentclass__.createFromPath(path)
        return self.__documentclass__()

    def run(self):
        self.ui.show()
        gtk.main()
        cPickle.dump(self.settings, open(self.__configpath__, "w"))

    def stop(self, *args):
        gtk.main_quit()

    def deleteObjects(self, objects):
        raise NotImplementedError

    def restoreObjects(self, objs):
        raise NotImplementedError

    def createObjectsFromClipboard(self):
        raise NotImplementedError

    def copySelectionToClipboard(self):
        raise NotImplementedError

    def _initActions(self):
        # standard menu actions
        ag = gtk.ActionGroup('menu_actions')
        for action, label in self.__menus__:
            action = gtk.Action(action, label, None, None)
            ag.add_action(action)
        self.uiman.insert_action_group(ag)

        ag = gtk.ActionGroup('command_actions')

        # create an action for each high-level command
        for klass in Command.__subclasses__():
            action = klass.action_class(klass.__name__, klass.label,
                klass.tooltip, klass.stockid)
            action.connect("activate", self._imperativeCommand, klass)
            ag.add_action_with_accel(action, klass.accelerator)
        self.uiman.insert_action_group(ag)

    def _imperativeCommand(self, action, command):
        cmd = command(self, action)
        cmd.do()

        if cmd.undoable:
            self.history_manager.append(cmd)

    def _documentErrorCb(self, document, error, reason):
        dlg = gtk.MessageDialog(self.ui,
            gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_ERROR,
            gtk.BUTTONS_OK,
            "Could not load audio file: %s (%s)" % (error, reason))
        dlg.connect("response", self._errorRespononseCb)
        dlg.show()

    def _errorRespononseCb(self, dlg, response):
        dlg.destroy()

    def _createUI(self):
        box = gtk.HBox()
        box.show()
        box.pack_start(self.uiman.get_widget("/mainmenubar"), False, False)
        if self.__documenteditorclass__:
            content = self.__documenteditorclass__(self, self.document)
            box.pack_start(content)
        ret = self.__mainwindowclass__()
        ret.add(box)
        ret.show_all()
        return ret

class Open(Command):

    undoable = False
    label = _("Open...")
    stockid = gtk.STOCK_OPEN
    accelerator = "<Shift><Control>O"

    def do(self):
        self.app.loadDocument()

class New(Command):

    undoable = False
    label = _("_New")
    stockid = gtk.STOCK_NEW

    def do(self):
        self.app.newDocument()

class Save(Command):

    undoable = False
    label = _("_Save")
    stockid = gtk.STOCK_SAVE

    def do(self):
        self.app.saveProject()

class SaveAs(Command):

    undoable = False
    label = _("Save _As...")
    stockid = gtk.STOCK_SAVE

    def do(self):
        self.app.saveProjectAs()

class Quit(Command):

    undoable = False
    name = "Quit"
    label = _("Quit")
    stockid = gtk.STOCK_QUIT

    def do(self):
        self.app.stop()

## Implements Command History -----------------------------------------------

class HistoryManager(object):

    def __init__(self):
        self._undo = []
        self._redo = []

    def undo(self):
        if self._undo:
            cmd = self._undo.pop()
            cmd.undo()
            self._redo.append(cmd)

    def redo(self):
        if self._redo:
            cmd = self._redo.pop()
            cmd.redo()
            self._undo.append(cmd)

    def append(self, cmd):
        self._undo.append(cmd)

    def can_undo(self):
        return len(self._undo) > 0

    def can_redo(self):
        return len(self._redo) > 0

class Undo(Command):

    undoable = False
    label = _("Undo")
    stockid = gtk.STOCK_UNDO
    accelerator="<Control>Z"

    def do(self):
        self.app.history_manager.undo()

    def is_valid(self):
        return self.app.history_manager.can_undo()

class Redo(Command):

    undoable = False
    label = _("Redo")
    stockid = gtk.STOCK_REDO
    accelerator = "<Shift><Control>Z"

    def do(self):
        self.app.history_manager.redo()

    def is_valid(self):
        return self.app.history_manager.can_redo()

## Selection and Clipboard Management ---------------------------------------

class Selection(Signallable):

    __signals__ = {
        "changed" : ["selected", "deselected"],
    }

    def __init__(self):
        self.objects = set()
        self.mapping = {}

    def addToSelection(self, obj):
        self.objects.add(obj)
        self._selectionChanged(set([obj]), set())

    def removeFromSelection(self, obj):
        self.objects.remove(obj)
        self._selectionChanged(set(), set([obj]))

    def clear(self):
        old = self.objects
        self.objects = set()
        self._selectionChanged(self.objects, old)

    def setSelectionTo(self, obj):
        if obj in self.objects:
            return
        deselected = self.objects
        self.objects = set([obj])
        self._selectionChanged(self.objects, deselected)

    def snapshot(self):
        return frozenset(self.objects)

    def _selectionChanged(self, selected, deselected):
        self.emit("changed", selected, deselected)
        for obj in selected:
            for view in self.mapping[obj]:
                view.select()
        for obj in deselected:
            for view in self.mapping[obj]:
                view.deselect()

    def associateObjects(self, model, view):
        """Associate a view object to its corresponding model object. The view
        object will be notified when the model object is added or removed from
        the selection."""
        if not model in self.mapping:
            self.mapping[model] = []
        self.mapping[model].append(view)

    def dissociateObjects(self, model, view):
        """Remove the association between the model and this view object, so
        that the view object will no longer receive notifications when the
        model object is added to the current selection."""
        self.mapping[model].remove(view)
        if not self.mapping[model]:
            del self.mapping[model]

class Cut(Command):
    undoable = True
    label = _("Cut")
    stockid = gtk.STOCK_CUT
    accelerator = "<Control>X"

    def do(self):
        self.objects = self.app.selection.snapshot()
        self.app.copySelectionToClipboard()
        self.app.deleteObjects(self.objects)

    def undo(self):
        self.app.restoreObjects(self.objects)
        self.app.setSelectionTo(self.objects)

    def is_valid(self):
        return len(self.app.selection) > 0

class Clipboard(object):

    pass

class Copy(Command):
    undoable = False
    label = _("Copy")
    stockid = gtk.STOCK_COPY
    accelerator = "<Control>C"

    def do(self):
        self.app.copySelection()

    def is_valid(self):
        return len(self.app.selection) > 0

class Paste(Command):
    undoable = True
    label = _("Paste")
    stockid = gtk.STOCK_PASTE
    accelerator = "<Control>V"

    def do(self):
        self.objects = self.app.createDataFromClipboard()
        self.restoreObjects(self.objects)

    def undo(self):
        self.app.deleteObjects(self.objects)

    def redo(self):
        self.restoreObjects(self.objects)

    def is_valid(self):
        return not self.app.clipboard.empty()

class Delete(Command):
    undoable = True
    label = _("Delete")
    stockid = gtk.STOCK_DELETE
    accelerator = "Delete"

    def do(self):
        self.objects = self.app.selection.snapshot()
        self.app.deleteObjects(self.objects)

    def undo(self):
        self.app.restoreObjects(self.objects)
        self.app.setSelectionTo(self.objects)

    def redo(self):
        self.app.deleteObjects(self.objects)

if __name__ == '__main__':
    Application().run()
    os.unlink(Application.__configpath__)
