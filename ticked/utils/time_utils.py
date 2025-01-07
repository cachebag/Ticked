def convert_to_12hour(time_24: str) -> str:
    """Convert 24-hour time string (HH:MM) to 12-hour format with AM/PM."""
    try:
        hour, minute = map(int, time_24.split(':'))
        period = "AM" if hour < 12 else "PM"
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour -= 12
        return f"{hour}:{minute:02d} {period}"
    except:
        return time_24

def convert_to_24hour(time_12: str) -> str:
    """Convert 12-hour time string (H:MM AM/PM) to 24-hour format."""
    try:
        time, period = time_12.rsplit(' ', 1)
        hour, minute = map(int, time.split(':'))
        if period == "PM" and hour < 12:
            hour += 12
        elif period == "AM" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"
    except:
        return time_12

def generate_time_options():
    """Generate time options for every 30 minutes in 12-hour format."""
    options = []
    
    for hour in range(24):
        for minute in [0, 30]:
            # Create 24-hour format for value
            time_24 = f"{hour:02d}:{minute:02d}"
            # Convert to 12-hour format for display
            time_12 = convert_to_12hour(time_24)
            # Use 24h format as value, 12h format as display text
            options.append((time_12, time_24))
            
    return options
