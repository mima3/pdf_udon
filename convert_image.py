import sys
import os
from pathlib import Path
import fitz
from tqdm import tqdm
import ocr_db


def main(db_path):
    db = ocr_db.OcrDb()
    db.connect(db_path)

    input_folder = Path('data').glob("*.pdf")
    for path in tqdm(list(input_folder)):
        result = []
        name = os.path.splitext(os.path.basename(path))[0]
        doc = fitz.open(path)
        for page in doc:
            pix = page.getPixmap()
            image_path = 'image/{}_{}.png'.format(name, page.number)
            pix.writePNG(image_path)
            rec = {
                'image_path' : str(image_path),
                'page_num' : page.number,
                'pdf_path' : str(path)
            }
            result.append(rec)
        # 多すぎるとエラーになる.
        db.append_images(result)

if __name__ == '__main__':
    main(sys.argv[1])
