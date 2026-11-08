"""NumPy implementation of the catalog analytics: whole arrays instead of Python loops."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from car_catalog.performance.analytics import (
    BRANDS,
    CURRENT_YEAR,
    MONTHS,
    BrandStatistics,
    CarRecord,
    MileageStatistics,
)


@dataclass(frozen=True)
class CatalogArrays:
    """The catalog as columns: one NumPy array for every field (brand as a code 0..9)."""

    car_ids: np.ndarray
    brand_codes: np.ndarray
    years: np.ndarray
    prices: np.ndarray
    mileages: np.ndarray

    @property
    def nbytes(self) -> int:
        """Memory of all arrays in bytes."""
        return sum(
            array.nbytes
            for array in (self.car_ids, self.brand_codes, self.years, self.prices, self.mileages)
        )


def to_arrays(cars: list[CarRecord]) -> CatalogArrays:
    """Convert list[CarRecord] into arrays with compact dtypes."""
    code_of = {brand: code for code, brand in enumerate(BRANDS)}
    return CatalogArrays(
        car_ids=np.array([car.car_id for car in cars], dtype=np.int32),
        brand_codes=np.array([code_of[car.brand] for car in cars], dtype=np.int8),
        years=np.array([car.year for car in cars], dtype=np.int16),
        prices=np.array([car.price for car in cars], dtype=np.float64),
        mileages=np.array([car.mileage for car in cars], dtype=np.int32),
    )


def count_by_brand(arrays: CatalogArrays, brand: str) -> int:
    """Number of cars of a brand: boolean mask + count_nonzero."""
    return int(np.count_nonzero(arrays.brand_codes == BRANDS.index(brand)))


def count_by_years(arrays: CatalogArrays, min_year: int, max_year: int) -> int:
    """Number of cars with min_year <= year <= max_year."""
    mask = (arrays.years >= min_year) & (arrays.years <= max_year)
    return int(np.count_nonzero(mask))


def most_expensive_id(arrays: CatalogArrays) -> int:
    """ID of the most expensive car (argmax gives the first maximum, as the loop)."""
    return int(arrays.car_ids[np.argmax(arrays.prices)])


def lowest_mileage_id(arrays: CatalogArrays) -> int:
    """ID of the car with the lowest mileage."""
    return int(arrays.car_ids[np.argmin(arrays.mileages)])


def average_price(arrays: CatalogArrays) -> float:
    """Average price."""
    return float(arrays.prices.mean())


def mileage_statistics(arrays: CatalogArrays) -> MileageStatistics:
    """Min, max, average and standard deviation of mileage (std of the whole set, ddof=0)."""
    mileages = arrays.mileages
    return MileageStatistics(
        int(mileages.min()), int(mileages.max()), float(mileages.mean()), float(mileages.std())
    )


def manufacturer_statistics(arrays: CatalogArrays) -> dict[str, BrandStatistics]:
    """Statistics of every manufacturer: bincount sums values by brand code."""
    length = len(BRANDS)
    counts = np.bincount(arrays.brand_codes, minlength=length)
    price_sums = np.bincount(arrays.brand_codes, weights=arrays.prices, minlength=length)
    mileage_sums = np.bincount(arrays.brand_codes, weights=arrays.mileages, minlength=length)
    result = {}
    for code, brand in enumerate(BRANDS):
        if counts[code] == 0:
            continue
        result[brand] = BrandStatistics(
            count=int(counts[code]),
            average_price=float(price_sums[code] / counts[code]),
            average_mileage=float(mileage_sums[code] / counts[code]),
            max_price=float(arrays.prices[arrays.brand_codes == code].max()),
        )
    return dict(sorted(result.items()))


def residual_values(arrays: CatalogArrays) -> np.ndarray:
    """Residual values of all cars at once: 120 steps over arrays instead of 120 × N steps.

    The same formula as analytics.residual_value(), but every operation works on the whole array.
    """
    values = arrays.prices.copy()
    ages = CURRENT_YEAR - arrays.years.astype(np.float64)
    mileages = arrays.mileages.astype(np.float64)
    for month in range(1, MONTHS + 1):
        rate = 0.005 + 0.01 * np.sin((month + ages) / 6) ** 2
        wear = mileages * 0.0004 * np.sqrt(month) / MONTHS
        values = values * (1 - rate) - wear
    return np.maximum(values, 0.0)


def catalog_report(arrays: CatalogArrays) -> dict[str, object]:
    """The same report as analytics.catalog_report(), cars are given by ID."""
    return {
        "toyota": count_by_brand(arrays, "Toyota"),
        "years_2019_2022": count_by_years(arrays, 2019, 2022),
        "most_expensive": most_expensive_id(arrays),
        "lowest_mileage": lowest_mileage_id(arrays),
        "average_price": average_price(arrays),
        "mileage": mileage_statistics(arrays),
        "manufacturers": manufacturer_statistics(arrays),
        "average_residual": float(residual_values(arrays).mean()),
    }
