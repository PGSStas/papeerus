class ExistingNameException(Exception):
    def __init__(self):
        super().__init__("This nickname already exists")
