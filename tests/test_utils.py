import pytest
from app.utils import eth_to_greg, greg_to_eth, is_leap_eth, is_valid_eth_date

def test_is_leap_eth():
    assert is_leap_eth(2011) == True
    assert is_leap_eth(2012) == False
    assert is_leap_eth(2015) == True
    assert is_leap_eth(2016) == False

def test_is_valid_eth_date():
    # Valid dates
    assert is_valid_eth_date(1, 1, 2016)[0] == True
    assert is_valid_eth_date(30, 12, 2016)[0] == True
    assert is_valid_eth_date(5, 13, 2016)[0] == True  # 2016 is not leap, but 2015 was. 
    # Wait, is_leap_eth(2015) returns True. So Pagume in 2015 has 6 days.
    assert is_valid_eth_date(6, 13, 2015)[0] == True
    assert is_valid_eth_date(6, 13, 2016)[0] == False
    
    # Invalid dates
    assert is_valid_eth_date(31, 1, 2016)[0] == False
    assert is_valid_eth_date(1, 14, 2016)[0] == False
    assert is_valid_eth_date(1, 1, 10000)[0] == False

def test_eth_to_greg_conversions():
    # Known test cases
    # Meskerem 1, 2016 EC -> Sept 12, 2023 GC (Since 2015 was leap)
    assert eth_to_greg(1, 1, 2016) == (12, 9, 2023)
    
    # Meskerem 1, 2015 EC -> Sept 11, 2022 GC
    assert eth_to_greg(1, 1, 2015) == (11, 9, 2022)
    
    # Pagume 6, 2015 EC -> Sept 11, 2023 GC
    assert eth_to_greg(6, 13, 2015) == (11, 9, 2023)
    
    # January 1, 2024 GC -> Tahsas 22, 2016 EC
    # Let's test greg_to_eth for this
    assert greg_to_eth(1, 1, 2024) == (22, 4, 2016)

def test_greg_to_eth_conversions():
    # Sept 11, 2023 GC -> Pagume 6, 2015 EC
    assert greg_to_eth(11, 9, 2023) == (6, 13, 2015)
    
    # Sept 12, 2023 GC -> Meskerem 1, 2016 EC
    assert greg_to_eth(12, 9, 2023) == (1, 1, 2016)
    
    # Jan 1, 2024 GC -> Tahsas 22, 2016 EC
    assert greg_to_eth(1, 1, 2024) == (22, 4, 2016)
