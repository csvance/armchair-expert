from reaction_model import *


def file_to_utf8(path):
    b_data = open(path, 'rb').read()
    utf8_data = b_data.decode('utf-8', 'ignore')
    return str(utf8_data)


if __name__ == '__main__':

    reaction = AOLReactionModelTrainer()

    data_path = 'training/aol-reaction-model/markov_line_utf8.csv'

    # Make sure the file is pure UTF8
    #data = file_to_utf8(data_path)
    #open(data_path, 'w').write(data)

    reaction.train(data_path, epochs=10)
    reaction.print_evaluation(data_path)
    export_dir = reaction.classifier.export_savedmodel("models/aol-reaction-model/", export_fn())
    print("New export_dir: %s" % export_dir)




