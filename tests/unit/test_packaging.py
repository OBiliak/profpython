"""Tests of the package metadata: version, console script and migrations inside the package."""

from importlib.metadata import entry_points, metadata, version

from car_catalog import __version__
from car_catalog.persistence.migrations import MIGRATIONS_DIR


def test_installed_version_is_package_version() -> None:
    assert version("car-catalog") == __version__


def test_metadata() -> None:
    data = metadata("car-catalog")
    assert data["Name"] == "car-catalog"
    assert data["Requires-Python"] == ">=3.11"
    assert data["License-Expression"] == "MIT"


def test_console_script_points_to_main() -> None:
    scripts = entry_points(group="console_scripts", name="car-catalog")
    assert [script.value for script in scripts] == ["car_catalog.main:main"]


def test_migrations_are_inside_the_package() -> None:
    assert MIGRATIONS_DIR.parent.name == "car_catalog"
    assert (MIGRATIONS_DIR / "env.py").is_file()
    assert sorted(path.name for path in (MIGRATIONS_DIR / "versions").glob("*.py")) == [
        "0001_create_car_catalog_tables.py",
        "0002_add_vin_to_cars.py",
    ]
