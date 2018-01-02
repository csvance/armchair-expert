from storage.armchair_expert import InputTextStatManager
from storage.twitter import TwitterTrainingDataManager
from common.nlp import create_nlp_instance, SpacyPreprocessor

nlp = create_nlp_instance()

spacy_preprocessor = SpacyPreprocessor()
for message in TwitterTrainingDataManager().all_training_data():
    spacy_preprocessor.preprocess(nlp(message[0].decode()))

# Update statistics
sentence_stats_manager = InputTextStatManager()
docs, _ = spacy_preprocessor.get_preprocessed_data()
for doc in docs:
    sents = 0
    for sent in doc.sents:
        sents += 1
    sentence_stats_manager.log_length(length=sents)

sentence_stats_manager.commit()
