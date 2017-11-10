from reaction_model import AOLReactionModel

def file_to_utf8(path):
    b_data = open(path, 'rb').read()
    utf8_data = b_data.decode('utf-8', 'ignore')
    return str(utf8_data)

if __name__ == '__main__':
    reaction = AOLReactionModel()

    data_path = 'training/aol-reaction-model/markov_line_utf8.csv'
    reaction.train(data_path, epochs=100)
    reaction.print_evaluation(data_path)

    classify = ['roflcopter', 'wat', 'lol', 'haha', 'llooolololo', 'oh hi mark', 'llllll', 'oooooo', 'wwwwtttt']
    for idx, is_aol_speak in enumerate(reaction.classify_data(classify)):
        print("%s - %s" % (is_aol_speak, classify[idx]))
