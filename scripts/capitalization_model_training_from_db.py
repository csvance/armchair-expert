from capitalization_model import *
from ml_common import DatabaseLinesDataFetcher
from markov_schema import *
from ml_common import create_spacy_instance
from pos_tree_model import PosTreeModel
import json


data_cache_path = 'training/data.json'
label_cache_path = 'training/labels.json'

capitalization_model = CapitalizationModel(use_gpu=CONFIG_USE_GPU)

cached_data_loaded = False

try:
    data = json.loads(open(data_cache_path, 'r').read())
    labels = json.loads(open(label_cache_path, 'r').read())
    cached_data_loaded = True
except FileNotFoundError:
    pass

if not cached_data_loaded:
    nlp = create_spacy_instance()

    session = Session()

    line_fetcher = DatabaseLinesDataFetcher(session=session)
    lines = line_fetcher.get_data()

    data = []
    labels = []

    num_lines = len(lines)

    for line_idx, line in enumerate(lines):
        doc = nlp(line)
        print("%f%%: %s" % (100 * float(line_idx) / float(num_lines), line))

        for sent in doc.sents:
            for token_idx, token in enumerate(sent):

                custom_pos = PosTreeModel.custom_pos_from_word(token.text, is_emoji=token._.is_emoji)
                pos = custom_pos if custom_pos is not None else token.pos_

                # Get features and classification labels
                word_features = CapitalizationFeatureAnalyzer.analyze(token.text, pos, word_position=token_idx)
                word_label = CapitalizationFeatureAnalyzer.label(token.text)

                data.append(word_features)
                labels.append(word_label)

    open(data_cache_path,'w').write(json.dumps(data))
    open(label_cache_path,'w').write(json.dumps(labels))

# Conver to numpy arrays
data = np.array(data)
labels = np.array(labels)

capitalization_model.train(data, labels, epochs=1)
capitalization_model.save(CONFIG_CAPITALIZATION_MODEL_PATH)