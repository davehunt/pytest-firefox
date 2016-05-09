# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys

from firefox_puppeteer import Puppeteer
from firefox_puppeteer.ui.browser.window import BrowserWindow
from marionette_driver.marionette import Marionette
import pytest

PY3 = sys.version_info[0] == 3


@pytest.fixture
def firefox(marionette, puppeteer):
    firefox = puppeteer.windows.current
    with marionette.using_context(marionette.CONTEXT_CHROME):
        firefox.focus()
    marionette.set_context(marionette.CONTEXT_CONTENT)
    return firefox


@pytest.yield_fixture
def marionette(request):
    marionette = Marionette(bin=request.config.getoption('firefox_path'))
    marionette.start_session()
    request.node._marionette = marionette
    yield marionette
    marionette.cleanup()


@pytest.fixture
def puppeteer(marionette):
    puppeteer = Puppeteer()
    puppeteer.marionette = marionette
    return puppeteer


@pytest.mark.hookwrapper
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    summary = []
    extra = getattr(report, 'extra', [])
    marionette = getattr(item, '_marionette', None)
    xfail = hasattr(report, 'wasxfail')
    if marionette is not None:
        if (report.skipped and xfail) or (report.failed and not xfail):
            exclude = item.config.getini('selenium_exclude_debug').lower()
            if 'url' not in exclude:
                _gather_url(item, report, marionette, summary, extra)
            if 'screenshot' not in exclude:
                _gather_screenshot(item, report, marionette, summary, extra)
            if 'html' not in exclude:
                _gather_html(item, report, marionette, summary, extra)
            if 'logs' not in exclude:
                _gather_logs(item, report, marionette, summary, extra)
    if summary:
        report.sections.append(('pytest-firefox', '\n'.join(summary)))
    report.extra = extra


def _gather_url(item, report, marionette, summary, extra):
    try:
        with marionette.using_context(marionette.CONTEXT_CHROME):
            url = marionette.get_url()
    except Exception as e:
        summary.append('WARNING: Failed to gather URL: {}'.format(e))
        return
    pytest_html = item.config.pluginmanager.getplugin('html')
    if pytest_html is not None:
        # add url to the html report
        extra.append(pytest_html.extras.url(url))
    summary.append('URL: {0}'.format(url))


def _gather_screenshot(item, report, marionette, summary, extra):
    try:
        with marionette.using_context(marionette.CONTEXT_CHROME):
            screenshot = marionette.screenshot()
    except Exception as e:
        summary.append('WARNING: Failed to gather screenshot: {}'.format(e))
        return
    pytest_html = item.config.pluginmanager.getplugin('html')
    if pytest_html is not None:
        # add screenshot to the html report
        extra.append(pytest_html.extras.image(screenshot, 'Screenshot'))


def _gather_html(item, report, marionette, summary, extra):
    try:
        with marionette.using_context(marionette.CONTEXT_CHROME):
            html = marionette.page_source
        if not PY3:
            html = html.encode('utf-8')
    except Exception as e:
        summary.append('WARNING: Failed to gather HTML: {}'.format(e))
        return
    pytest_html = item.config.pluginmanager.getplugin('html')
    if pytest_html is not None:
        # add page source to the html report
        extra.append(pytest_html.extras.text(html, 'HTML'))


def _gather_logs(item, report, driver, summary, extra):
    try:
        logs = driver.get_logs()
    except Exception as e:
        summary.append('WARNING: Failed to gather logs: {}'.format(e))
        return
    pytest_html = item.config.pluginmanager.getplugin('html')
    if logs and pytest_html is not None:
        extra.append(pytest_html.extras.text('\n'.join(logs), 'Log'))
