from messages import *
from ml_common import *
from ml_common import create_spacy_instance

if __name__ == '__main__':

    path = "training/markov_training_files"
    nlp = create_spacy_instance()

    pos_tree_model = PosTreeModel(path=CONFIG_POS_TREE_CONFIG_PATH, nlp=nlp, people=CONFIG_DISCORD_MEMBERS)

    training_data_fetcher = DirectoryUnstructuredDataFetcher(path)

    for line in training_data_fetcher.get_data():
        print(line)
        pos_tree_model.process_text(line)

    pos_tree_model.update_probabilities()
    pos_tree_model.save()

    print("All Done!")
