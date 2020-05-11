from __future__ import print_function
import sys
import pickle
import io
import os.path
import time
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from apiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
from tqdm import tqdm
import ocr_db


SCOPES = [
    'https://www.googleapis.com/auth/drive'
]

def authenticate(client_secret_json_path):
    """QuickStartで行った認証処理と同じ認証処理を行う
    https://developers.google.com/drive/api/v3/quickstart/python
    """
    creds = None
    
    token_path = '{}/token.pickle'.format(os.path.dirname(__file__))
    # ファイルtoken.pickleはユーザーのアクセストークンと更新トークンを格納し、
    # 認証フローが初めて完了すると自動的に作成されます。
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    # 有効な資格情報がない場合は、ユーザーにログインさせます。
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # ユーザーにブラウザーで認証URLを開くように指示し、ユーザーのURLを自動的に開こうとします。
            # ローカルWebサーバーを起動して、認証応答をリッスンします。
            # 認証が完了すると、認証サーバーはユーザーのブラウザーをローカルWebサーバーにリダイレクトします。
            # Webサーバーは、応答とシャットダウンから認証コードを取得します。その後、コードはトークンと交換されます
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_json_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # 次回実行のために「google.oauth2.credentials.Credentials」をシリアライズ化して保存します。
        # https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.credentials.html
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    return creds


def run_ocr(service_drive, path):
    # PNGをGoogleドキュメントとしてUploadします.
    # https://developers.google.com/drive/api/v3/manage-uploads#python
    name = os.path.splitext(os.path.basename(path))[0]
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.document'
    }
    media = MediaFileUpload(path,
                            mimetype='image/png',
                            resumable=True)
    file = service_drive.files().create(body=file_metadata,
                                    media_body=media,
                                    fields='id').execute()
    file_id = file.get('id')

    # Download
    request = service_drive.files().export_media(fileId=file_id, mimeType='text/plain')
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    service_drive.files().delete(fileId=file_id).execute()
    return fh.getvalue().decode('utf-8')



def main(argvs):
    """メイン処理"""
    argvs = sys.argv
    argc = len(argvs)
    if argc != 3:
        print("Usage #python %s [DBのパス] [認証用JSONのパス]" % argvs[0])
        exit()
    db_path = argvs[1]
    client_secret_json_path = argvs[2]

    creds = authenticate(client_secret_json_path)

    service_drive = build('drive', 'v3', credentials=creds)

    db = ocr_db.OcrDb()
    db.connect(db_path)

    images = db.get_images()
    for image in tqdm(images):
        if db.get_text(image.id) is None:
            text = run_ocr(service_drive, image.image_path)
            db.update_text(image.id, text)

if __name__ == '__main__':
    main(sys.argv)
