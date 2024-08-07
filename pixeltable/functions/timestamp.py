"""
Pixeltable [UDFs](https://pixeltable.readme.io/docs/user-defined-functions-udfs) for `TimestampType`.

Usage example:
```python
import pixeltable as pxt

t = pxt.get_table(...)
t.select(t.timestamp_col.year, t.timestamp_col.weekday()).collect()
```
"""

from datetime import datetime
from typing import Optional

import pixeltable.func as func
from pixeltable.utils.code import local_public_names


@func.udf
def year(self: datetime) -> int:
    """
    Between [`MINYEAR`](https://docs.python.org/3/library/datetime.html#datetime.MINYEAR) and
    [`MAXYEAR`](https://docs.python.org/3/library/datetime.html#datetime.MAXYEAR) inclusive.

    Equivalent to [`datetime.year`](https://docs.python.org/3/library/datetime.html#datetime.datetime.year).
    """
    return self.year


@func.udf
def month(self: datetime) -> int:
    """
    Between 1 and 12 inclusive.

    Equivalent to [`datetime.month`](https://docs.python.org/3/library/datetime.html#datetime.datetime.month).
    """
    return self.month


@func.udf
def day(self: datetime) -> int:
    """
    Between 1 and the number of days in the given month of the given year.

    Equivalent to [`datetime.day`](https://docs.python.org/3/library/datetime.html#datetime.datetime.day).
    """
    return self.day


@func.udf
def hour(self: datetime) -> int:
    """
    Between 0 and 23 inclusive.

    Equivalent to [`datetime.hour`](https://docs.python.org/3/library/datetime.html#datetime.datetime.hour).
    """
    return self.hour


@func.udf
def minute(self: datetime) -> int:
    """
    Between 0 and 59 inclusive.

    Equivalent to [`datetime.minute`](https://docs.python.org/3/library/datetime.html#datetime.datetime.minute).
    """
    return self.minute


@func.udf
def second(self: datetime) -> int:
    """
    Between 0 and 59 inclusive.

    Equivalent to [`datetime.second`](https://docs.python.org/3/library/datetime.html#datetime.datetime.second).
    """
    return self.second


@func.udf
def microsecond(self: datetime) -> int:
    """
    Between 0 and 999999 inclusive.

    Equivalent to [`datetime.microsecond`](https://docs.python.org/3/library/datetime.html#datetime.datetime.microsecond).
    """
    return self.microsecond


@func.udf
def weekday(self: datetime) -> int:
    """
    Between 0 (Monday) and 6 (Sunday) inclusive.

    Equivalent to [`datetime.weekday()`](https://docs.python.org/3/library/datetime.html#datetime.datetime.weekday).
    """
    return self.weekday()

@func.udf
def isoweekday(self: datetime) -> int:
    """
    Return the day of the week as an integer, where Monday is 1 and Sunday is 7.

    Equivalent to [`datetime.isoweekday()`](https://docs.python.org/3/library/datetime.html#datetime.datetime.isoweekday).
    """
    return self.isoweekday()


@func.udf
def isocalendar(self: datetime) -> dict:
    """
    Return a dictionary with three entries: `'year'`, `'week'`, and `'weekday'`.

    Equivalent to
    [`datetime.isocalendar()`](https://docs.python.org/3/library/datetime.html#datetime.datetime.isocalendar).
    """
    iso_year, iso_week, iso_weekday = self.isocalendar()
    return {'year': iso_year, 'week': iso_week, 'weekday': iso_weekday}


@func.udf
def isoformat(self: datetime, sep: str = 'T', timespec: str = 'auto') -> str:
    """
    Return a string representing the date and time in ISO 8601 format.

    Equivalent to [`datetime.isoformat()`](https://docs.python.org/3/library/datetime.html#datetime.datetime.isoformat).

    Args:
        sep: Separator between date and time.
        timespec: The number of additional terms in the output. See the [`datetime.isoformat()`](https://docs.python.org/3/library/datetime.html#datetime.datetime.isoformat) documentation for more details.
    """
    return self.isoformat(sep=sep, timespec=timespec)


@func.udf
def strftime(self: datetime, format: str) -> str:
    """
    Return a string representing the date and time, controlled by an explicit format string.

    Equivalent to [`datetime.strftime()`](https://docs.python.org/3/library/datetime.html#datetime.datetime.strftime).

    Args:
        format: The format string to control the output. For a complete list of formatting directives, see [`strftime()` and `strptime()` Behavior](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior).
    """
    return self.strftime(format)


# @func.udf
# def date(self: datetime) -> datetime:
#     """
#     Return the date part of the datetime.
#
#     Equivalent to [`datetime.date()`](https://docs.python.org/3/library/datetime.html#datetime.datetime.date).
#     """
#     d = self.date()
#     return datetime(d.year, d.month, d.day)
#
#
# @func.udf
# def time(self: datetime) -> datetime:
#     """
#     Return the time part of the datetime, with microseconds set to 0.
#
#     Equivalent to [`datetime.time()`](https://docs.python.org/3/library/datetime.html#datetime.datetime.time).
#     """
#     t = self.time()
#     return datetime(1, 1, 1, t.hour, t.minute, t.second, t.microsecond)


@func.udf
def replace(
        self: datetime, year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None,
        hour: Optional[int] = None, minute: Optional[int] = None, second: Optional[int] = None,
        microsecond: Optional[int] = None) -> datetime:
    """
    Return a datetime with the same attributes, except for those attributes given new values by whichever keyword
    arguments are specified.

    Equivalent to [`datetime.replace()`](https://docs.python.org/3/library/datetime.html#datetime.datetime.replace).
    """
    kwargs = {k: v for k, v in locals().items() if k != 'self' and v is not None}
    return self.replace(**kwargs)


@func.udf
def toordinal(self: datetime) -> int:
    """
    Return the proleptic Gregorian ordinal of the date, where January 1 of year 1 has ordinal 1.

    Equivalent to [`datetime.toordinal()`](https://docs.python.org/3/library/datetime.html#datetime.datetime.toordinal).
    """
    return self.toordinal()


@func.udf
def posix_timestamp(self: datetime) -> float:
    """
    Return POSIX timestamp corresponding to the datetime instance.

    Equivalent to [`datetime.timestamp()`](https://docs.python.org/3/library/datetime.html#datetime.datetime.timestamp).
    """
    return self.timestamp()


__all__ = local_public_names(__name__)


def __dir__():
    return __all__
