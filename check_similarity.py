import sys
import os
import re
import json
from tqdm import tqdm
from janome.tokenizer import Tokenizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import ocr_db


def stems(doc):
    result = []
    t = Tokenizer()
    tokens = t.tokenize(doc['text'])
    for token in tokens:
        result.append(token.surface.strip())
    return result

def check_duplicate(lst, item):
    for chk_item in lst:
        if (chk_item['pdf_path1'] == item['pdf_path2'] and
           chk_item['page_num1'] == item['page_num2'] and
           chk_item['pdf_path2'] == item['pdf_path1'] and
           chk_item['page_num2'] == item['page_num1']):
           return True
    return False


def main(db_path, pdf_path_string, output_path):
    result = []
    db = ocr_db.OcrDb()
    db.connect(db_path)
    vectorizer = TfidfVectorizer(analyzer=stems)
    t = Tokenizer()
    texts = db.get_pdf_texts(pdf_path_string)
    documents = []
    for rec in texts:
        documents.append({
            'pdf_path' : rec[0],
            'page_num' : rec[1],
            'text' : rec[2],
        })
    print('fit_transform...')
    tfidf_matrix = vectorizer.fit_transform(documents)
    print('cosine_similarity...')
    for ix in tqdm(range(len(documents))):
        similarities = cosine_similarity(tfidf_matrix[ix], tfidf_matrix)
        for similarity in similarities:
            for ix2 in range(len(similarity)):
                if ix2 == ix:
                    continue
                if similarity[ix2] <= 0.8:
                    continue
                item = {
                    'pdf_path1' : documents[ix]['pdf_path'],
                    'page_num1' : documents[ix]['page_num'],
                    'pdf_path2' : documents[ix2]['pdf_path'],
                    'page_num2' : documents[ix2]['page_num'],
                    'similarity' : similarity[ix2]
                }
                if check_duplicate(result, item):
                    continue
                result.append(item)

    with open(output_path, mode='w', encoding='utf8') as fp:
        json.dump(result, fp, sort_keys=True, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
