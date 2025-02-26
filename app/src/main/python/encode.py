import cv2
import numpy as np
import qrcode
import base64
from reedsolo import RSCodec
import base64

np.set_printoptions(threshold=np.inf)
def generate_qr_code(input_text,ecc_level):
    #誤り訂正レベルの決定
    ecc_rate = [qrcode.constants.ERROR_CORRECT_L,qrcode.constants.ERROR_CORRECT_M,
                 qrcode.constants.ERROR_CORRECT_Q,qrcode.constants.ERROR_CORRECT_H]
    # QRコードを生成
    qr = qrcode.QRCode(
        version=1,
        error_correction=ecc_rate[ecc_level - 1],
        box_size=10,
        border=4,
    )
    qr.add_data(input_text)
    qr.make(fit=True)
    # QRコードのデータをPIL Imageに変換
    qr_image = qr.make_image(fill_color="black", back_color="white")
    # PIL ImageをNumpy配列に変換
    qr_data = np.array(qr_image)

    # QRコードのサイズを取得
    size = qr_data.shape[0]

    # QRコードのデータを指定されたサイズに変換
    qr_data = qr_data.reshape((size, size)).astype(np.uint8) * 255

    # OpenCVを使用して画像を生成
    qr_image_cv2 = cv2.resize(qr_data, (300, 300), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite("image.png",qr_image_cv2)
    # 画像をBase64エンコードして文字列として返却
    _, img_buffer = cv2.imencode(".png", qr_image_cv2)
    img_base64 = base64.b64encode(img_buffer.tobytes()).decode("utf-8")

    return img_base64

#リードソロモン
def reed_solomon(input_text,correction_bits):
    # インスタンスを作成
    rs = RSCodec(correction_bits)  #エラー訂正のための冗長ビットの数

    # 文字列をバイト列に変換して符号化
    encoded_bytes = rs.encode(input_text.encode('utf-8'))
    # バイトをビットに変換
    bits = ''.join(format(byte, '08b') for byte in encoded_bytes)

    #冗長ビットの数を示す6bitを追加
    correction_bits_num = bin(correction_bits)[2:] #冗長ビットの数をbitに変換
    correction_bits_num = correction_bits_num.zfill(16) #必要な桁数に0をパディング
    bits = correction_bits_num + bits #bit列の先頭に追加
    return bits

#verを判別し、文字列をビットに変換
def string_to_bit(input_text,ecc_level):
    #誤り訂正レベルの決定
    ecc_rate = [0.07,0.15,0.25,0.3]

    #ver判別
    length_str = len(input_text) * 8
    for ver in range(1,40):
        length_bits = ((17 + 4 * ver) ** 2 - 192) * 3 - 16
        #8の倍数に変換
        length_bits -= length_bits % 8
        if length_str < length_bits * (1 - 2*ecc_rate[ecc_level - 1]):
            break

    #冗長ビットの数
    correction_bits = int((length_bits - length_str) / 8)
    bits = reed_solomon(input_text,correction_bits)
    return ver,bits

#三次元コードへの変換
def covert(ver,bits):
    size = 17 + 4 * ver
    img=np.ones((size,size,3))
    #ファインダパターン
    img[:8,:8] = -1     #左上
    img[:8,-8:] = -1    #右上
    img[-8:,:8] = -1    #左下

    n=0
    for x in range(size-1,-1,-1):
        for y in range(size-1,-1,-1):
            for color in range(3):
                if img[x,y,color] != -1:
                    img[x,y,color]=bits[n]
                    n+=1
                    if n == len(bits):
                        break
            if n == len(bits):
                break
        if n == len(bits):
            break

    #ファインダパターン
    img[:8,:8] = 1     #左上
    img[:7,:7] = 0
    img[1:6,1:6] = 1
    img[2:5,2:5] = 0
    img[:8,-8:] = 1    #右上
    img[:7,-7:] = 0
    img[1:6,-6:-1] = 1
    img[2:5,-5:-2] = 0
    img[-8:,:8] = 1    #左下
    img[-7:,:7] = 0
    img[-6:-1,1:6] = 1
    img[-5:-2,2:5] = 0

    img[6,0] = [0,0,1]     #赤
    img[6,6] = [1,0,1]     #桃
    img[0,6] = [1,0,0]     #青
    img[5,1] = [1,1,0]     #水
    img[5,5] = [0,1,0]     #緑
    img[1,5] = [0,1,1]     #黄

    img[0,-7] = [0,0,1]    #赤
    img[6,-7] = [1,0,1]    #桃
    img[6,-1] = [1,0,0]    #青
    img[1,-6] = [1,1,0]    #水
    img[5,-6] = [0,1,0]    #緑
    img[5,-2] = [0,1,1]    #黄

    img[-1,6] = [0,0,1]    #赤
    img[-7,6] = [1,0,1]    #桃
    img[-7,0] = [1,0,0]    #青
    img[-2,5] = [1,1,0]    #水
    img[-6,5] = [0,1,0]    #緑
    img[-6,1] = [0,1,1]    #黄
    return img,size

#三次元コードの画像生成
def create(img,size,border):
    bbox=np.array([[border,border],[border,border]])
    height=size+bbox[0,0]+bbox[0,1]
    width=size+bbox[1,0]+bbox[1,1]
    img2=np.ones((height,width,3))

    for y in range(size):
        for x in range(size):
            for color in range(3):
                img2[x + bbox[0,0],y + bbox[1,0],color] = img[x,y,color]

        # QRコードのサイズを取得
    size = img2.shape[0]
    # QRコードのデータを指定されたサイズに変換
    img2 = img2.reshape((size, size, 3)).astype(np.uint8) * 255
    # OpenCVを使用して画像を生成
    img2 = cv2.resize(img2, (300, 300), interpolation=cv2.INTER_NEAREST)
    return img2

def encode(input_text,level):
    ver,bits = string_to_bit(input_text,level)
    img,size = covert(ver,bits)
    img = create(img,size,4)
    # 画像をBase64エンコードして文字列として返却
    _, img_buffer = cv2.imencode(".png", img)
    img_base64 = base64.b64encode(img_buffer.tobytes()).decode("utf-8")
    return img_base64