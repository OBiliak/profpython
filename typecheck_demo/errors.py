"""Type-checking experiment of laboratory work 4: three intentional type errors."""

from car_catalog.domain.models import Car
from car_catalog.domain.repositories import InMemoryRepository
from car_catalog.domain.value_objects import Mileage, Money

# Error 1: a str value is assigned to a variable of type int.
vehicle_id: int = "1"


# Error 2: the function must return int but returns str.
def count_vehicles() -> int:
    """Return the number of vehicles."""
    return "100"


# Error 3: an object of another type is added to Repository[Car].
repository: InMemoryRepository[Car] = InMemoryRepository()
repository.add(Car(1, "Toyota", "Corolla", 2018, Money(520_000), Mileage(85_000)))
repository.add(Money(520_000))
