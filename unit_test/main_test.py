import pytest
from scripts import main

def test_main():
    with pytest.raises(AssertionError) as excinfo:
        main.get_connection_info('postgres')

    assert "Expected values: (mt-pg, user, password), Actual values: " in str(excinfo.value)
