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


class AggregationMethod(ExtendedEnum):
    DropInBucket = enum.auto()
    InverseDistance = enum.auto()


class GridType(ExtendedEnum):
    EASE2_G1km = enum.auto()

    EASE2_G3km = enum.auto()
    EASE2_N3km = enum.auto()
    EASE2_S3km = enum.auto()

    EASE2_G3125km = enum.auto()
    EASE2_N3125km = enum.auto()
    EASE2_S3125km = enum.auto()

    EASE2_G625km = enum.auto()
    EASE2_N625km = enum.auto()
    EASE2_S625km = enum.auto()

    EASE2_G9km = enum.auto()
    EASE2_N9km = enum.auto()
    EASE2_S9km = enum.auto()

    EASE2_G125km = enum.auto()
    EASE2_N125km = enum.auto()
    EASE2_S125km = enum.auto()

    EASE_G125km = enum.auto()
    EASE_N125km = enum.auto()
    EASE_S125km = enum.auto()

    EASE2_G25km = enum.auto()
    EASE2_N25km = enum.auto()
    EASE2_S25km = enum.auto()

    EASE_G25km = enum.auto()
    EASE_N25km = enum.auto()
    EASE_S25km = enum.auto()

    EASE2_G36km = enum.auto()
    EASE2_N36km = enum.auto()
    EASE2_S36km = enum.auto()
