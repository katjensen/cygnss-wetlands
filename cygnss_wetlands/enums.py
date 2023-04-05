import enum


class ExtendedEnum(enum.Enum):
    @classmethod
    def enumlist(cls):
        return list(map(lambda c: c, cls))

    @classmethod
    def namelist(cls):
        return list(map(lambda c: c.name, cls))

    @classmethod
    def from_str(cls, value: str):
        for k, v in cls.__members__.items():
            if k == value:
                return v
        else:
            raise ValueError(f"'{cls.__name__}' enum not found for '{value}'")


class CygnssProductLevel(ExtendedEnum):
    L1 = 1
    L2 = 2
    L3 = 3
