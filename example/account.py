from basemodel import property, BaseModel
from observable import ObservableList

# Design the basic account object

class Transaction(BaseModel):

    # Similar to the property() built-in, the pymodel property descriptor
    # creates a dynamic property, however this property automatically emits
    # the appropriate "-changed" signal when the value changes.
    debit = property()
    credit = property()

    # This is a more complex property, which is read-only, and depends on the
    # two other properties (debit and credit). Specifying these properties here
    # means that balanced-changed will automatically be emitted when either
    # debit-changed or credit-changed is emitted.

    @property()
    def balance(self):
        return self.credit - self.debit

    def isDebit(self):
        return self.debit and not self.credit

    def isCredit(self):
        return self.credit and not self.debit

    def __init__(self, debit=float(0), credit=float(0)):
        assert not debit and credit
        if debit:
            self.debit = debit
        else:
            self.credit = credit

class Account(Transaction):

    # An account is a Transaction whose balance is the sum over the list of
    # children. There are many ways we could have defined it, but we do it
    # this way to illustrate the flexibility of the framework.

    # Transactions is a list of child Transaction objects. By declaring it as
    # a ListProperty we are ensuring that transactions-changed will be
    # emitted whenever the list is mutated (children added, or removed).

    transactions = property()

    @property
    def debit(self):
        return sum((t for t in self.transactions if t.isDebit))

    @property
    def credit(self):
        return sum((t for t in self.transactiosn if t.isCredit))

    def addTransaction(self, transaction):
        self.transactions.append(transaction)

    def removeTransaction(self, transaction):
        self.transactions.remove(transaction)

    # Note that we don't need to redefine the balance property, because it can
    # still be expressed as credit - debit, and it will still be recalculated
    # when debit or credit change.

    def __init__(self, transactions):
        Transaction.__init__(self)
        # for ListObserver to work, it must contain an ObservableList instance
        self.transactions = ObservableList(transactions)

class AccountingApplication(object):

    # Property is one of the most flexible convenience objects in
    # the toolkit. It works with any object inheriting from BaseModel, and
    # automatically watches sub-properties of the specified model object.
    
    document = property()

    # In this very simple application, the the init_document method is the
    # only method we need to concern ourselves with. The document property
    # holds the users's content.  The application object watches this object
    # for changes and sets dirty flags as appropraite. Calls to saveDocument
    # and loadDocument assume this object as the root node. The settings
    # property, unused here, manages user preferences in a similar fashion.

    def __init__(self):
        self.document = Account()


def pathToUri(path):
    return "file://" + path

if __name__ == "__main__":

    import cmd

    class UI(cmd.Cmd):

        prompt = "> "

        def preloop(self):
            self.app = AccountingApplication()
            self.account_stack = [self.app.document]

        def do_add(self, line):
            amount = float(line)
            self.account_stack[-1].(amount)

        def do_remove(self, line):
            ref = self.account_stack[-1].find(line)
            if ref:
                self.account_stack[-1].remove(ref)

        def do_subaccount(self, line):
            acct = Account()
            self.account_stack[-1].addTransaction(acct)
            self.account_stack.append(acct)

        def do_close_subaccount(self, line):
            if len(self.account_stack) > 1:
                self.account_stack.pop()

        def do_list(self, line):
            for transaction, depth in self.app.getFullList():
                print (" " * depth) + transaction.balance

        def do_undo(self, line):
            self.app.undo()

        def do_redo(self, line):
            self.app.redo()

        def do_save(self, line):
            self.app.saveDocument(pathToUri(line))

        def do_load(self, line):
            self.app.loadDocument(pathtoUri(line))

        def postcmd(self):
            print self.app.root_account.balance

    ui = UI()
    ui.cmdloop()
