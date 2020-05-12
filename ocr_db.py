"""youtubeのメッセージ記録用DB操作."""
from peewee import *
from playhouse.sqlite_ext import *
from statistics import mean, median,variance,stdev
#import logging
#logger = logging.getLogger('peewee')
#logger.setLevel(logging.DEBUG)
#logger.addHandler(logging.StreamHandler())


database_proxy = Proxy()


class Image(Model):
    """画像情報"""
    id = AutoIncrementField()
    pdf_path = CharField()
    page_num = IntegerField()
    image_path = CharField()

    class Meta:
        """Moviesのメタ情報"""
        database = database_proxy
        indexes = (
            # 末尾に,がないとエラーになる
            # 複数指定も可能
            (('pdf_path', 'page_num'), True),
        )


class OcrText(Model):
    """OCRのテキスト情報"""
    id = AutoIncrementField()
    image_id = ForeignKeyField(Image, related_name='image', index=True, null=False, unique=True)
    text = CharField()


    class Meta:
        """Moviesのメタ情報"""
        database = database_proxy


class OcrDb:
    """OCR用のDB操作"""
    database = None

    def connect(self, db_path):
        """SQLiteへの接続"""
        self.database = SqliteDatabase(db_path)
        database_proxy.initialize(self.database)
        self.database.create_tables([Image, OcrText])


    def append_images(self, rows):
        """画像情報を登録する"""
        try:
            with self.database.transaction():
                Image.insert_many(rows).execute()
                self.database.commit()
        except IntegrityError as ex:
            print(ex)
            self.database.rollback()

    def get_images(self):
        """画像情報を全て取得する"""
        return Image.select()


    def get_text(self, image_id):
        rec = OcrText.get_or_none(image_id=image_id)
        if not rec:
            return None
        return rec.text
        

    def update_text(self, image_id, text):
        rec = OcrText.get_or_none(image_id=image_id)
        if rec:
            rec.text = text
            rec.save()
        else:
            rec = OcrText.create(image_id=image_id, text=text)

    def get_pdf_list(self):
        return Image.select(Image.pdf_path).distinct()

    def get_pdf_texts(self, pdf_path):
        rec_image = Image.get_or_none(pdf_path=pdf_path)
        ret = (OcrText.select(Image.pdf_path.alias('pdf_path'), Image.page_num.alias('page_num'), OcrText.text).join(Image, JOIN.LEFT_OUTER).where(Image.pdf_path ** "%{}%".format(pdf_path)))
        return ret.tuples()

