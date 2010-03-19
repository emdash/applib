import gobject
from pymodel.basemodel import BaseModel, property
import time

class Clock(BaseModel):

    time = property(0)

    def __init__(self, interval=40):
        gobject.timeout_add(interval, self.updateTime)

    def updateTime(self):
        self.time = time.time()
        return True
