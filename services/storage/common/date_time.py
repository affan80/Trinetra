from dateutil import parser


def parse_date(date_text):
    """
    Parses a date string into an ISO formatted string.
    """
    if not date_text:
        return None

    try:
        parsed_date = parser.parse(str(date_text))
        return parsed_date.isoformat()
    except Exception:
        return None
