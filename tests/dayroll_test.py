import pytest
import datetime as dt
from qp.time.dayroll import roll_day, Dayroll

# --- Following ---

def test_following_sat():
    # input saturday 2 May, expect monday 4 May 2026
    assert roll_day(dt.date(2026, 5, 2), dayroll=Dayroll.FOLLOWING) == dt.date(2026, 5, 4)

def test_following_weekday():
    # input monday 4 May, expect monday 4 May 2026
    assert roll_day(dt.date(2026, 5, 4), dayroll=Dayroll.FOLLOWING) == dt.date(2026, 5, 4)

def test_following_hol():
    # input 1 jan 2026 (new years) expect friday 2 jan 2026
    assert roll_day(dt.date(2026,1,1), dayroll=Dayroll.FOLLOWING, currency="USD") == dt.date(2026, 1, 2)

# --- Preceding ---

def test_preceding_sat():
    # input saturday 2 May, expect friday 1 May 2026
    assert roll_day(dt.date(2026, 5, 2), dayroll=Dayroll.PRECEDING) == dt.date(2026, 5, 1)

def test_preceding_weekday():
    # input monday 4 May, expect monday 4 May 2026
    assert roll_day(dt.date(2026, 5, 4), dayroll=Dayroll.PRECEDING) == dt.date(2026, 5, 4)

def test_preceding_hol():
    # input monday 16 feb 2026 (president's day), expect friday 13 feb 2026
    assert roll_day(dt.date(2026, 2, 16), dayroll=Dayroll.PRECEDING, currency="USD") == dt.date(2026, 2, 13)
    
# --- Modified Following ---

def test_modified_following_sat():
    # input saturday 2 May, expect monday 4 May 2026
    assert roll_day(dt.date(2026, 5, 2), dayroll=Dayroll.MODIFIED_FOLLOWING) == dt.date(2026, 5, 4)

def test_modified_following_next_month():
    # input sunday 31 may 2026, expect fri 29 may 2026
    assert roll_day(dt.date(2026, 5, 31), dayroll=Dayroll.MODIFIED_FOLLOWING) == dt.date(2026, 5, 29)
    
    
# --- Modified Preceding ---

def test_modified_preceding_sat():
    # input saturday 2 May, expect friday 1 May 2026
    assert roll_day(dt.date(2026, 5, 2), dayroll=Dayroll.MODIFIED_PRECEDING) == dt.date(2026, 5, 1)

def test_modified_preceding_previous_month():
    # input sunday 1 march 2026, expect monday 2 march 2026
    assert roll_day(dt.date(2026, 3, 1), dayroll=Dayroll.MODIFIED_PRECEDING) == dt.date(2026, 3, 2)


# --- Invalid Dayroll ---

def test_invalid_dayroll():
    with pytest.raises(KeyError):
        roll_day(dt.date(2026, 5, 2), dayroll="invalid")