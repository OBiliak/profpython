"""Type-checking experiment of laboratory work 4: the three type errors are fixed."""

from car_catalog.domain.models import Car
from car_catalog.domain.repositories import InMemoryRepository
from car_catalog.domain.value_objects import Mileage, Money

# Fix 1: the variable of type int gets an int value.
vehicle_id: int = 1


# Fix 2: the function returns int as declared.
def count_vehicles() -> int:
    """Return the number of vehicles."""
    return 100


# Fix 3: only Car objects are added to Repository[Car].
repository: InMemoryRepository[Car] = InMemoryRepository()
repository.add(Car(1, "Toyota", "Corolla", 2018, Money(520_000), Mileage(85_000)))
repository.add(Car(2, "Toyota", "RAV4", 2021, Money(1_150_000), Mileage(32_000)))

if __name__ == "__main__":
    print(f"vehicle_id={vehicle_id}, count_vehicles()={count_vehicles()}")
    print(f"У репозиторії {len(repository)} автомобілі")
