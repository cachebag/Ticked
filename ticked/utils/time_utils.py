def convert_to_12hour(time_24: str) -> str:
    try:
        if time_24 == "23:59":
            return "11:59 PM"
        if time_24 == "00:00":
            return "12:00 AM"

        hour, minute = map(int, time_24.split(":"))
        period = "AM" if hour < 12 else "PM"
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour -= 12
        return f"{hour}:{minute:02d} {period}"
    except:
        return time_24


def convert_to_24hour(time_12: str) -> str:
    try:
        if time_12 == "11:59 PM":
            return "23:59"
        if time_12 == "12:00 AM":
            return "00:00"

        time, period = time_12.rsplit(" ", 1)
        hour, minute = map(int, time.split(":"))
        if period == "PM" and hour < 12:
            hour += 12
        elif period == "AM" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"
    except:
        return time_12


def generate_time_options():
    options = []

    options.append(("12:00 AM", "00:00"))

    for hour in range(24):
        for minute in [0, 30]:
            if hour == 0 and minute == 0:
                continue

            time_24 = f"{hour:02d}:{minute:02d}"
            time_12 = convert_to_12hour(time_24)
            options.append((time_12, time_24))

    options.append(("11:59 PM", "23:59"))

    return options
