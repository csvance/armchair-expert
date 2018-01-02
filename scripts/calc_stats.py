from config.ml import PREPROCESS_CACHE_DIR
from common.nlp import SpacyPreprocessor
from storage.armchair_expert import SentenceStatsManager


spacy_preprocessor = SpacyPreprocessor()
spacy_preprocessor.load_cache(PREPROCESS_CACHE_DIR)

# Update statistics
sentence_stats_manager = SentenceStatsManager()
docs, _ = spacy_preprocessor.get_preprocessed_data()
for doc in docs:
    sents = 0
    for sent in doc.sents:
        sents += 1
    sentence_stats_manager.log_length(length=sents)

sentence_stats_manager.commit()
