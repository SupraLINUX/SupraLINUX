#!/usr/bin/python3
from __future__ import annotations
import hashlib
from pathlib import Path

PATH = Path('debian/libkf6holidays6.symbols')
BASE_SHA256 = 'b0be25ddbc4c7abeb121bb0d3c3ca053d33e2a9fa88695bea210c50d56c256cd'
RESULT_SHA256 = 'fac03d2f96ccec7b6cbcfd30d59cee86496d3a0f6b5ad02d3392496b61e7c135'

HEBREW_DATE = [
    '_ZN9KHolidays10HebrewDate10fromHebrewEiii@Base',
    '_ZN9KHolidays10HebrewDate11fromSecularEiii@Base',
    '_ZN9KHolidays10HebrewDateC1ERKNS_16HebrewDateResultE@Base',
    '_ZN9KHolidays10HebrewDateC2ERKNS_16HebrewDateResultE@Base',
    '_ZN9KHolidays10HebrewDateD1Ev@Base',
    '_ZN9KHolidays10HebrewDateD2Ev@Base',
]
HEBREW_CONVERTER = [
    '_ZN9KHolidays15HebrewConverter12short_kislevEi@Base',
    '_ZN9KHolidays15HebrewConverter13long_cheshvanEi@Base',
    '_ZN9KHolidays15HebrewConverter13qdateToHebrewERK5QDate@Base',
    '_ZN9KHolidays15HebrewConverter17gregorianToHebrewEiii@Base',
    '_ZN9KHolidays15HebrewConverter17hebrewToGregorianEiii@Base',
    '_ZN9KHolidays15HebrewConverter18hebrew_leap_year_pEi@Base',
    '_ZN9KHolidays15HebrewConverter18hebrew_year_lengthEi@Base',
    '_ZN9KHolidays15HebrewConverter19hebrew_elapsed_daysEi@Base',
    '_ZN9KHolidays15HebrewConverter19hebrew_month_lengthEii@Base',
    '_ZN9KHolidays15HebrewConverter20absolute_from_hebrewEiii@Base',
    '_ZN9KHolidays15HebrewConverter20hebrew_elapsed_days2Ei@Base',
    '_ZN9KHolidays15HebrewConverter20hebrew_from_absoluteElPiS1_S1_@Base',
    '_ZN9KHolidays15HebrewConverter20secular_month_lengthEii@Base',
    '_ZN9KHolidays15HebrewConverter21gregorian_leap_year_pEi@Base',
    '_ZN9KHolidays15HebrewConverter21hebrew_months_in_yearEi@Base',
    '_ZN9KHolidays15HebrewConverter23absolute_from_gregorianEiii@Base',
    '_ZN9KHolidays15HebrewConverter23gregorian_from_absoluteElPiS1_S1_@Base',
    '_ZN9KHolidays15HebrewConverter25hebrewToSecularConversionEiiiPNS_16HebrewDateResultE@Base',
    '_ZN9KHolidays15HebrewConverter25secularToHebrewConversionEiiiPNS_16HebrewDateResultE@Base',
    '_ZN9KHolidays15HebrewConverter9finish_upEliiiiPNS_16HebrewDateResultE@Base',
]
HEBREW_GETTERS = [
    '_ZNK9KHolidays10HebrewDate15hebrewDayNumberEv@Base',
    '_ZNK9KHolidays10HebrewDate17hebrewMonthLengthEv@Base',
    '_ZNK9KHolidays10HebrewDate18isOnHebrewLeapYearEv@Base',
    '_ZNK9KHolidays10HebrewDate18secularMonthLengthEv@Base',
    '_ZNK9KHolidays10HebrewDate19isOnSecularLeapYearEv@Base',
    '_ZNK9KHolidays10HebrewDate3dayEv@Base',
    '_ZNK9KHolidays10HebrewDate4kviaEv@Base',
    '_ZNK9KHolidays10HebrewDate4yearEv@Base',
    '_ZNK9KHolidays10HebrewDate5monthEv@Base',
    '_ZNK9KHolidays10HebrewDate9dayOfWeekEv@Base',
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lines(symbols: list[str]) -> list[str]:
    return [f' {symbol} 6.30.0' for symbol in symbols]

raw = PATH.read_bytes()
if digest(raw) != BASE_SHA256:
    raise SystemExit(f'unexpected KHolidays symbols baseline: {digest(raw)}')

out: list[str] = []
date_anchor = converter_anchor = getter_anchor = False
for line in raw.decode().splitlines():
    out.append(line)
    if line == '* Build-Depends-Package: libkf6holidays-dev':
        out += lines(HEBREW_DATE)
        date_anchor = True
    elif line.lstrip().split(' ', 1)[0] == '_ZN9KHolidays13HolidayRegionaSERKS0_@Base':
        out += lines(HEBREW_CONVERTER)
        converter_anchor = True
    elif line.lstrip().split(' ', 1)[0] == '_ZN9KHolidays9SunEventsaSERKS0_@Base':
        out += lines(HEBREW_GETTERS)
        getter_anchor = True

if not (date_anchor and converter_anchor and getter_anchor):
    raise SystemExit('KHolidays 6.28 symbols anchors did not match expected baseline')
result = ('\n'.join(out) + '\n').encode()
if digest(result) != RESULT_SHA256:
    raise SystemExit(f'unexpected reviewed KHolidays symbols result: {digest(result)}')
PATH.write_bytes(result)
print(digest(result))
