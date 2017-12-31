from typing import List


class TrainingDataManager(object):
    def new_training_data(self) -> List[str]:
        pass

    def mark_trained(self, data: List):
        pass

    def untrain_all(self):
        pass

    def store(self, data):
        pass
