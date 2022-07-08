try:
    from pytest_html.html_report import HTMLReport
except ImportError:
    from pytest_html.plugin import HTMLReport


class MPHTMLReport(HTMLReport):

    def __init__(self, logfile, config, manager=None):
        HTMLReport.__init__(self, logfile, config)
        self.reports = manager.dict()
        self._manager = manager

    def pytest_runtest_logreport(self, report):
        if report.nodeid not in self.reports:
            self.reports[report.nodeid] = self._manager.list()
        super().pytest_runtest_logreport(report)
