from abc import ABC, abstractmethod


class BaseModel(ABC):

    @abstractmethod
    def curves(self):
        """Abstract method: class must return its curves"""
        pass

    @abstractmethod
    def price(self):
        "Abstract method: class must expose a price method"
        pass

    @abstractmethod
    def with_curves(self, curves: dict):
        "Abstract method: construct a new model with new curves"
        pass
