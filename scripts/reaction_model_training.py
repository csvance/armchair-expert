from reaction_model import *


if __name__ == '__main__':

    reaction = AOLReactionModelTrainer()

    data_path = 'training/aol-reaction-model/markov_line_utf8.csv'

    reaction.train(data_path, epochs=10)
    reaction.print_evaluation(data_path)
    export_dir = reaction.classifier.export_savedmodel("models/aol-reaction-model/", export_fn())
    print("New export_dir: %s" % export_dir)




