import todo
import arrow


def get_timestamp():
    return arrow.now().timestamp


def get_date(timestamp):
    return arrow.Arrow.fromtimestamp(timestamp)


def get_formatted_date(timestamp):
    return get_date(timestamp).format(
        "dddd, Do MMMM YYYY, hh:mm a (ZZZ)"
    )
