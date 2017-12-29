from multiprocessing import Queue
from typing import List

import numpy as np
from spacy.tokens import Token

from ml_common import MLModelWorker, MLModelScheduler
from nlp_common import Pos, CapitalizationMode


class PoSCapitalizationMode(object):
    def __init__(self, pos: Pos, mode: CapitalizationMode):
        self.pos = pos
        self.mode = mode

    def __repr__(self):
        return str(self.pos).split(".")[1] + "_" + str(self.mode).split(".")[1]

    def to_embedding(self) -> int:
        return self.pos.value * len(CapitalizationMode) + self.mode.value

    @staticmethod
    def from_embedding(embedding: int):
        pos_part = int(embedding / len(CapitalizationMode))
        mode_part = int(embedding % len(CapitalizationMode))
        return PoSCapitalizationMode(Pos(pos_part), CapitalizationMode(mode_part))


class StructureFeatureAnalyzer(object):
    NUM_FEATURES = len(Pos) * len(CapitalizationMode)

    @staticmethod
    def analyze(token: Token, mode: CapitalizationMode):
        pos = Pos.from_token(token)
        mode = PoSCapitalizationMode(pos, mode)
        return mode.to_embedding()


class StructureModel(object):
    SEQUENCE_LENGTH = 16

    def __init__(self, use_gpu: bool = False):
        import tensorflow as tf
        from keras.models import Sequential
        from keras.layers import Dense, Embedding
        from keras.layers import LSTM
        from keras.backend import set_session

        latent_dim = StructureModel.SEQUENCE_LENGTH * 8

        model = Sequential()
        model.add(
            Embedding(StructureFeatureAnalyzer.NUM_FEATURES, StructureFeatureAnalyzer.NUM_FEATURES,
                      input_length=StructureModel.SEQUENCE_LENGTH))
        model.add(LSTM(latent_dim, dropout=0.2, return_sequences=True))
        model.add(LSTM(latent_dim, dropout=0.2, return_sequences=False))
        model.add(Dense(StructureFeatureAnalyzer.NUM_FEATURES, activation='softmax'))
        model.summary()
        model.compile(loss='categorical_crossentropy', optimizer='adam')
        self.model = model

        if use_gpu:
            config = tf.ConfigProto()
            config.gpu_options.allow_growth = True
            set_session(tf.Session(config=config))

    def train(self, data, labels, epochs=1):
        self.model.fit(data, labels, epochs=epochs, batch_size=64)

    def predict(self) -> List[PoSCapitalizationMode]:
        from keras.preprocessing.sequence import pad_sequences

        predictions = []

        # Start the sequence with NONE / NONE
        sequence = [[0]]

        num_sentences = np.random.randint(1, 5)
        eos_count = 0

        while eos_count < num_sentences:
            padded_sequence = pad_sequences(sequence, maxlen=StructureModel.SEQUENCE_LENGTH, padding='post')

            prediction = self.model.predict(padded_sequence, batch_size=1)
            index = np.random.choice(range(0, StructureFeatureAnalyzer.NUM_FEATURES),
                                     p=prediction[0])

            if PoSCapitalizationMode.from_embedding(index).pos == Pos.EOS:
                eos_count += 1

            predictions.append(index)
            sequence[0].append(index)
            sequence[0] = sequence[0][-StructureModel.SEQUENCE_LENGTH:]

        modes = []
        for embedding_idx, embedding in enumerate(predictions):
            mode = PoSCapitalizationMode.from_embedding(embedding)
            modes.append(mode)
        return modes

    def load(self, path):
        self.model.load_weights(path)

    def save(self, path):
        self.model.save_weights(path)


class StructureModelWorker(MLModelWorker):
    def __init__(self, read_queue: Queue, write_queue: Queue, use_gpu: bool = False):
        MLModelWorker.__init__(self, name='SentenceStructureModelWorker', read_queue=read_queue, write_queue=write_queue,
                               use_gpu=use_gpu)

    def run(self):
        self._model = StructureModel(use_gpu=self._use_gpu)
        MLModelWorker.run(self)

    def predict(self, *data) -> List[PoSCapitalizationMode]:
        return self._model.predict()

    def train(self, *data):
        return self._model.train(data=data[0][0], labels=data[0][1], epochs=data[0][2])

    def save(self, *data):
        return self._model.save(path=data[0][0])

    def load(self, *data):
        return self._model.load(path=data[0][0])


class StructureModelScheduler(MLModelScheduler):
    def __init__(self, use_gpu: bool = False):
        MLModelScheduler.__init__(self)
        self._worker = StructureModelWorker(read_queue=self._write_queue, write_queue=self._read_queue,
                                            use_gpu=use_gpu)

    def predict(self):
        return self._predict()

    def train(self, data, labels, epochs=1):
        return self._train(data, labels, epochs)

    def save(self, path):
        return self._save(path)

    def load(self, path):
        return self._load(path)
