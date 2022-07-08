import multiprocessing
from unittest.mock import Mock

from _pytest.junitxml import _NodeReporter, LogXML
from contextvars import ContextVar
import xml.etree.ElementTree as ET

from pytest_mp.plugin import synchronization


node_reporters_lock = ContextVar("Lock")


def _finalize(self):
    data = self.to_xml()
    self.__dict__.clear()
    self.to_xml = lambda: data
    with node_reporters_lock.get():
        synchronization['node_reporters'].append(data)
_NodeReporter.finalize = _finalize


class MPLogXML(LogXML):

    def __init__(self, logfile, prefix, suite_name="pytest", manager=None):
        LogXML.__init__(self, logfile, prefix, suite_name)
        self.stats = manager.dict()
        self.stats['error'] = 0
        self.stats['passed'] = 0
        self.stats['failure'] = 0
        self.stats['skipped'] = 0
        node_reporters_lock.set(multiprocessing.Lock())

    def pytest_sessionfinish(self) -> None:
        self.node_reporters_ordered = list(map(lambda data: Mock(**{"to_xml.return_value": data}), synchronization['node_reporters']))
        super().pytest_sessionfinish()
