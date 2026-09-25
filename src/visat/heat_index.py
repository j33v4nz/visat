"""NWS (Rothfusz) heat index in Celsius, and its risk band.

Open-Meteo's `apparent_temperature` uses a different "feels like" formula
(Steadman) — show that as "feels like" in the UI, but use this heat index
for the risk band, since it's what KSDMA's own alerts are based on.
"""

from . import config


def heat_index_celsius(temp_c: float, relative_humidity_pct: float) -> float:
    """Rothfusz regression, computed in Fahrenheit then converted back.

    Below 27C (80F) the Rothfusz regression isn't valid, so just return the
    air temperature — there's no meaningful heat-index effect that low.
    """
    if temp_c < 26.7:  # ~80F
        return round(temp_c, 1)

    t = temp_c * 9 / 5 + 32
    r = relative_humidity_pct

    hi_f = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * r
        - 0.22475541 * t * r
        - 0.00683783 * t * t
        - 0.05481717 * r * r
        + 0.00122874 * t * t * r
        + 0.00085282 * t * r * r
        - 0.00000199 * t * t * r * r
    )

    # Low relative-humidity adjustment (r < 13%, 80F <= t <= 112F).
    if r < 13 and 80 <= t <= 112:
        adjustment = ((13 - r) / 4) * ((17 - abs(t - 95)) / 17) ** 0.5
        hi_f -= adjustment

    # High relative-humidity adjustment (r > 85%, 80F <= t <= 87F).
    if r > 85 and 80 <= t <= 87:
        hi_f += ((r - 85) / 10) * ((87 - t) / 5)

    return round((hi_f - 32) * 5 / 9, 1)


def heat_index_band(heat_index_c: float) -> str | None:
    """Which NWS band a heat-index value falls in, or None if below Caution."""
    for band, (low, high) in config.HEAT_INDEX_BANDS_C.items():
        if high is None:
            if heat_index_c >= low:
                return band
        elif low <= heat_index_c < high:
            return band
    return None
