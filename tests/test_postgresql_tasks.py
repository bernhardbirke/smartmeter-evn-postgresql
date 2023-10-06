import pytest
from src.smartmeter.postgresql_tasks import PostgresTasks


# create instance postgrestasks of Class PostgresTasks
@pytest.fixture
def postgrestasks():
    return PostgresTasks()


# Caution: creates an entry in specified postgresql database
def t_insert_smartmeter(postgrestasks):
    id = postgrestasks.insert_smartmeter(
        1234.1339491293948, 45.2, 0.023, 2.39, 230, 240.3, 222.23, 50, 51.4, 49.3, 0.56
    )
    assert isinstance(id, int) and id > 0
