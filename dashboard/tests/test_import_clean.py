"""Import-clean tests for dashboard modules.

Every file in dashboard/components/ and dashboard/pages/ must import
without error. Pages use a _is_streamlit_running() guard so they
won't execute UI code at import time.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest


def _list_modules(package_path: str, package_name: str) -> list[str]:
    """List all module names under a package directory."""
    modules = []
    for importer, modname, ispkg in pkgutil.iter_modules([package_path]):
        full_name = f"{package_name}.{modname}"
        modules.append(full_name)
    return modules


class TestComponentImports:
    """Every file in dashboard/components/ imports without error."""

    @pytest.fixture(scope="class")
    def component_modules(self):
        import dashboard.components
        pkg_path = dashboard.components.__path__[0]
        return _list_modules(pkg_path, "dashboard.components")

    def test_at_least_one_component(self, component_modules):
        assert len(component_modules) >= 5, (
            f"Expected at least 5 component modules, found {len(component_modules)}"
        )

    def test_all_components_import(self, component_modules):
        failures = []
        for mod_name in component_modules:
            try:
                importlib.import_module(mod_name)
            except Exception as exc:
                failures.append(f"{mod_name}: {exc}")
        assert not failures, (
            f"{len(failures)} component(s) failed to import:\n"
            + "\n".join(failures)
        )


class TestPageImports:
    """Every file in dashboard/pages/ imports without error.

    Pages have a _is_streamlit_running() guard that prevents bare
    execution of UI code at import time.
    """

    @pytest.fixture(scope="class")
    def page_modules(self):
        import dashboard.pages
        pkg_path = dashboard.pages.__path__[0]
        return _list_modules(pkg_path, "dashboard.pages")

    def test_at_least_nine_pages(self, page_modules):
        assert len(page_modules) >= 9, (
            f"Expected at least 9 page modules, found {len(page_modules)}"
        )

    def test_all_pages_import(self, page_modules):
        failures = []
        for mod_name in page_modules:
            try:
                importlib.import_module(mod_name)
            except Exception as exc:
                failures.append(f"{mod_name}: {exc}")
        assert not failures, (
            f"{len(failures)} page(s) failed to import:\n"
            + "\n".join(failures)
        )
