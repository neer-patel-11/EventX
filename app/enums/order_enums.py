
from enum import Enum as PyEnum

class OrderStatus(PyEnum):
    CANCELLED='cancelled'
    INCOMPLETE='incomplete'
    COMPLETELYFILLED='completelyfilled'
    PARTIALFILLED='partialfilled'

class OrderShareType(PyEnum):
    YES='yes'
    NO='no'

class OrderSide(PyEnum):
    BUY='buy'
    SELL='sell'
    