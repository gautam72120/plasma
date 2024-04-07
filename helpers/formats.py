from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta


class Plural:
    def __init__(self, value):
        self.value = value

    def __format__(self, format_spec):
        singular, _, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"

        if abs(self.value) != 1:
            return f"{self.value} {plural}"
        return f"{self.value} {singular}"


def human_join(seq, *, delimiter=", ", final="or"):
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    elems = delimiter.join(map(str, seq[:-1]))
    return f"{elems} {final} {seq[-1]}"


def human_timedelta(dt, *, source=None, accuracy=3, brief=False, suffix=True):
    now = source or datetime.now(timezone.utc)

    if isinstance(dt, timedelta):
        dt = now + dt

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Microsecond free zone
    dt = dt.replace(microsecond=0)
    now = now.replace(microsecond=0)

    if dt > now:
        delta = relativedelta(dt, now)
        affix = ""
    else:
        delta = relativedelta(now, dt)
        affix = " ago" if suffix else ""

    attrs = [
        ("year", "y"),
        ("month", "mo"),
        ("day", "d"),
        ("hour", "h"),
        ("minute", "m"),
        ("second", "s"),
    ]

    output = []
    for attr, brief_attr in attrs:
        value = getattr(delta, attr + "s")
        if not value:
            continue

        if attr == "day":
            weeks = delta.weeks
            if weeks:
                value -= weeks * 7
                if brief:
                    output.append(f"{weeks}w")
                else:
                    output.append(format(Plural(weeks), "week"))

        if value <= 0:
            continue

        if brief:
            output.append(f"{attr}{brief_attr}")
        else:
            output.append(format(Plural(value), attr))

    if accuracy:
        output = output[:accuracy]

    if len(output) == 0:
        return "now"

    time = (
        " ".join(output) + affix if brief else human_join(output, final="and") + affix
    )
    return f"`{time}`"
