import sys
import os
import math
from pathlib import Path
from tqdm import tqdm
from PIL import Image
import pyocr
import pyocr.builders
import numpy as np
import cv2
import ocr_db


def imread_jp(image_full_path):
    # cv2::imereadは日本語を含むパスを読めない
    # https://github.com/opencv/opencv/issues/4292
    # https://stackoverflow.com/questions/11552926/how-to-read-raw-png-from-an-array-in-python-opencv
    with open(image_full_path, 'rb') as img_stream:
        file_bytes = np.asarray(bytearray(img_stream.read()), dtype=np.uint8)
        img_data_ndarray = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
        return img_data_ndarray


def get_image(path):
    img = imread_jp(path)
    # ハフ変換による直線検出
    # http://labs.eecs.tottori-u.ac.jp/sd/Member/oyamada/OpenCV/html/py_tutorials/py_imgproc/py_houghlines/py_houghlines.html
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray,50,150,apertureSize = 3)
    # 時間がかかる、斜め線も抽出される
    #lines = cv2.HoughLines(edges,1,np.pi/180,200)
    minLineLength = 150
    maxLineGap = 20
    lines = cv2.HoughLinesP(edges,1,np.pi/180,100,minLineLength,maxLineGap)

    degs = np.array([])
    if not lines is None:
       for line in lines:
           for x1, y1, x2, y2 in line:
               # 角度を取得
               degs = np.append(degs, math.degrees(math.atan2(y2-y1,x2-x1)))
               #cv2.line(img,(x1,y1),(x2,y2),(0,0,255),2)

    #cv2.imshow('image',img)
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()
    #sys.exit(1)

    # 画像の回転
    if degs.shape[0] > 0:
        # はずれ値の影響を受けないように中央値にしておく。
        angle = np.median(degs)
        height = img.shape[0]
        width = img.shape[1]  
        center = (int(width/2), int(height/2))
        scale = 1.0
        trans = cv2.getRotationMatrix2D(center, angle , scale)
        img = cv2.warpAffine(img, trans, (width,height) ,borderValue=(255, 255, 255))

    # ノイズ除去
    img = cv2.fastNlMeansDenoisingColored(img,None,10,10,7,21)

    #cv2.imshow('image',img)
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()
    #with open(path + '.tmp', mode='wb') as fp:
    #    fp.write(img.tobytes())

    return Image.fromarray(img)


def analyze_image(tool, image_path):
    image = get_image(image_path)
    res = tool.image_to_string(
        image,
        lang='jpn',
        builder=pyocr.builders.TextBuilder()
    )
    return res

def get_tool():
    # 1.インストール済みのTesseractのパスを通す
    # https://gammasoft.jp/blog/ocr-by-python/#tesseract
    path_tesseract = "C:\\Program Files\\Tesseract-OCR"
    if path_tesseract not in os.environ["PATH"].split(os.pathsep):
        os.environ["PATH"] += os.pathsep + path_tesseract

    # https://gitlab.gnome.org/World/OpenPaperwork/pyocr
    tools = pyocr.get_available_tools()
    if len(tools) == 0:
        print("No OCR tool found")
        raise
    return tools[0]


def main(db_path):
    db = ocr_db.OcrDb()
    db.connect(db_path)

    tool = get_tool()
    images = db.get_images()
    for image in tqdm(images):
        if db.get_text(image.id) is None:
            text = analyze_image(tool, image.image_path)
            db.update_text(image.id, text)


if __name__ == '__main__':
    main(sys.argv[1])
