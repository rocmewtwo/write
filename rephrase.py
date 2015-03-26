import word2vec

model = word2vec.load('gdex.numbered.txt.bin')

def thesauru(word):
    thesauru_list=[]
    if word == '_':
        return ['_']
    else:
        if word in model.vocab:
            indexes, metrics = model.cosine(word)
            if word in ['a','an', 'the']:
                return ['a','an', 'the']
            else:
                for i in indexes:
                    thesauru_list.append(model.vocab[i])
                thesauru_list.append(word)
                return thesauru_list
        else:
            return ['_']
