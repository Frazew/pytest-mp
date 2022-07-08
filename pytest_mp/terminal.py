from _pytest.terminal import TerminalReporter
import multiprocessing


# Taken from pytest/_pytest/terminal.py
# and made process safe by avoiding use of `setdefault()`
# Thanks to pytest-concurrent for approach

# Also includes pytest-instafail functionality
# :copyright: (c) 2013-2016 by Janne Vanhala.
# since it isn't compatible w/ MPTerminalReporter


class MPTerminalReporter(TerminalReporter):

    def __init__(self, reporter, manager):
        TerminalReporter.__init__(self, reporter.config)
        self._tw = reporter._tw
        self.manager = manager
        self.stats = dict()
        self.stat_keys = ['passed', 'failed', 'error', 'skipped', 'warnings', 'xpassed', 'xfailed', '']
        for key in self.stat_keys:
            self.stats[key] = manager.list()
        self.stats_lock = multiprocessing.Lock()
        self._progress_items_reported_proxy = manager.Value('i', 0)
        self.progress_lock = multiprocessing.Lock()

    def pytest_collectreport(self, report):
        # Show errors occurred during the collection instantly.
        TerminalReporter.pytest_collectreport(self, report)
        if self.config.option.instafail:
            if report.failed:
                if self.isatty:
                    self.rewrite('')  # erase the "collecting"/"collected" message
                self.print_failure(report)

    def summary_failures(self):
        if not self.config.option.instafail:
            TerminalReporter.summary_failures(self)

    def summary_errors(self):
        if not self.config.option.instafail:
            TerminalReporter.summary_errors(self)

    def pytest_runtest_logstart(self, nodeid, location):
        pass

    def pytest_runtest_logreport(self, report):
        with self.progress_lock:
            # following example here https://github.com/pytest-dev/pytest/blob/03ef54670662def8422ec983969b81250d543433/src/_pytest/terminal.py#L387
            res = self.config.hook.pytest_report_teststatus(report=report, config=self.config)
            cat, letter, word = res

            # This helps make TerminalReporter process-safe.
            with self.stats_lock:
                if cat in self.stat_keys:
                    self.stats[cat].append(report)
                else:  # not expected and going to be dropped.  TODO: fix this.
                    cat_list = self.stats.get(cat, [])
                    cat_list.append(report)
                    self.stats[cat] = cat_list

            self._tests_ran = True
            if not letter and not word:
                # probably passed setup/teardown
                return

            # This helps make TerminalReporter process-safe.
            with self.stats_lock:
                self._progress_items_reported_proxy.value += 1

            return super().pytest_runtest_logreport(report)

    def print_failure(self, report):
        if self.config.option.tbstyle != "no":
            if self.config.option.tbstyle == "line":
                line = self._getcrashline(report)
                self.write_line(line)
            else:
                msg = self._getfailureheadline(report)
                if not hasattr(report, 'when'):
                    msg = "ERROR collecting " + msg
                elif report.when == "setup":
                    msg = "ERROR at setup of " + msg
                elif report.when == "teardown":
                    msg = "ERROR at teardown of " + msg
                self.write_sep("_", msg)
                if not self.config.getvalue("usepdb"):
                    self._outrep_summary(report)

    def _get_progress_information_message(self):
        collected = self._session.testscollected
        if collected:
            progress = self._progress_items_reported_proxy.value * 100 // collected
            return ' [{:3d}%]'.format(progress)
        return ' [100%]'
