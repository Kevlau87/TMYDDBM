"""Metric -> US customary conversions, for display only.

TeslaMate stores everything internally in metric (km, km/h, Celsius, bar)
regardless of the display units configured in the TeslaMate app itself --
this is a Tesla API / TeslaMate storage convention, not a user preference.
The SQL/gold layer stays in those native units so it's unambiguous for any
future analysis; conversion happens here, at the point charts/tables are
built, not in the data model.
"""

KM_TO_MI = 0.621371
M_TO_FT = 3.28084
BAR_TO_PSI = 14.5038


def km_to_mi(km):
    return km * KM_TO_MI


def kmh_to_mph(kmh):
    return kmh * KM_TO_MI


def c_to_f(c):
    return c * 9 / 5 + 32


def f_to_c(f):
    return (f - 32) * 5 / 9


def bar_to_psi(bar):
    return bar * BAR_TO_PSI


def m_to_ft(m):
    return m * M_TO_FT


def ft_to_m(ft):
    return ft / M_TO_FT
