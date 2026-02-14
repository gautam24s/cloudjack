from abc import ABC, abstractmethod


class SecretManagerBlueprint(ABC):

    @abstractmethod
    def get_secret(self, name: str) -> str:
        pass

    @abstractmethod
    def create_secret(self, name: str, value: str):
        pass

    @abstractmethod
    def update_secret(self, name: str, value: str):
        pass

    @abstractmethod
    def delete_secret(self, name: str):
        pass
