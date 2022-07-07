import time
import sys
import os

from _pytest.junitxml import _NodeReporter, LogXML
import xml.etree.ElementTree as ET
import py

from pytest_mp.plugin import synchronization


# Python 2.X and 3.X compatibility
if sys.version_info[0] < 3:
    from codecs import open
else:
    unichr = chr
    unicode = str
    long = int


# Taken from pytest/_pytest/junitxml.py
# but uses synchronization dict store
# Thanks to pytest-concurrent for approach


class MPNodeReporter(_NodeReporter):

    def finalize(self):
        data = self.to_xml()
        self.__dict__.clear()
        self.to_xml = lambda: py.xml.raw(data)
        with synchronization['node_reporters_lock']:
            synchronization['node_reporters'].append(data)


class MPLogXML(LogXML):

    def __init__(self, logfile, prefix, suite_name="pytest", manager=None):
        LogXML.__init__(self, logfile, prefix, suite_name)
        self.stats = manager.dict()
        self.stats['error'] = 0
        self.stats['passed'] = 0
        self.stats['failure'] = 0
        self.stats['skipped'] = 0
        self.stats_lock = manager.Lock()

    def pytest_sessionfinish(self):
        dirname = os.path.dirname(os.path.abspath(self.logfile))
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        logfile = open(self.logfile, 'w', encoding='utf-8')
        suite_stop_time = time.time()
        suite_time_delta = suite_stop_time - self.suite_start_time

        numtests = (self.stats['passed'] + self.stats['failure'] +  # noqa W504
                    self.stats['skipped'] + self.stats['error'] -  # noqa W504
                    self.cnt_double_fail_tests)
        logfile.write('<?xml version="1.0" encoding="utf-8"?>')

        suite_node = ET.Element(
            "testsuite",
            self._get_global_properties_node(),
            name=self.suite_name,
            errors=self.stats['error'],
            failures=self.stats['failure'],
            skips=self.stats['skipped'],
            tests=numtests,
            time="%.3f" % suite_time_delta
        )

        global_properties = self._get_global_properties_node()
        if global_properties is not None:
            suite_node.append(global_properties)
        for node_reporter in synchronization['node_reporters']:  # Synchronization
            suite_node.append(py.xml.raw(x))

        testsuites = ET.Element("testsuites")
        testsuites.append(suite_node)
        logfile.write(ET.tostring(testsuites, encoding="unicode"))
        logfile.close()

    def add_stats(self, key):
        with self.stats_lock:
            if key in self.stats:
                self.stats[key] += 1

    def node_reporter(self, report):
        nodeid = getattr(report, 'nodeid', report)
        # local hack to handle xdist report order
        slavenode = getattr(report, 'node', None)

        key = nodeid, slavenode
        if key in self.node_reporters:
            return self.node_reporters[key]

        reporter = MPNodeReporter(nodeid, self)

        self.node_reporters[key] = reporter
        return reporter
