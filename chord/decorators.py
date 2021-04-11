from time import sleep


def execute_periodically(period: int):
    def decorator(func):
        def wrapper(*args, **kwargs):
            while True:
                sleep(period)
                func(*args, **kwargs)
        return wrapper
    return decorator
