import cv2
import numpy as np
from scipy.stats import mode
import base64
from io import BytesIO
from PIL import Image
from reedsolo import RSCodec

np.set_printoptions(threshold=np.inf)

#三次元コードの画像生成
def create(img3d,size3d):
    pixel=10

    bbox=np.array([[4,4],[4,4]])
    height=size3d+bbox[0,0]+bbox[0,1]
    width=size3d+bbox[1,0]+bbox[1,1]
    img3d = 1 - img3d
    img=np.full((height*pixel,width*pixel,3),255, dtype=np.uint8)

    for y in range(size3d):
        for x in range(size3d):
            y1=bbox[0,0]+y
            y2=y1+1
            x1=bbox[1,0]+x
            x2=x1+1
            b=255-img3d[y,x,0]*255
            g=255-img3d[y,x,1]*255
            r=255-img3d[y,x,2]*255
            y1*=pixel
            y2*=pixel
            x1*=pixel
            x2*=pixel
            cv2.rectangle(img, (x1, y1), (x2, y2), (b,g,r), thickness=-1)
    return img

#パターン判別
def pattern_detection(image):
    pattern = np.zeros((3,7))
    pattern[:,1:6] = 255
    pattern[:,2:5] = 0

    re_image = np.zeros((3,7))
    for rows in range(2,5):
        for cols in range(7):
            sub_region = image[rows * (image.shape[0] // 7):(rows + 1) * (image.shape[0] // 7),
                         cols * (image.shape[1] // 7):(cols + 1) * (image.shape[1] // 7)]
            re_image[rows - 2,cols],_ = mode(sub_region.flatten())

    comparison = np.array_equal(pattern, re_image)
    return comparison

#ver判別
def version_detection(image):
    # グレースケール変換
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # しきい値処理
    _, image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # 行数と列数の取得
    img_rows = len(image)
    img_cols = len(image[0])

    # バージョンの判別
    for ver in range(1,41):
        if ver == 41:return False
        size = 17 + 4 * ver
        rows = int(img_rows * 7 / size)
        cols = int(img_cols * 7 / size)
        pattern = image[:rows, :cols]
        if pattern_detection(pattern) == False:
            continue
        pattern = image[:rows, -cols:]
        if pattern_detection(pattern) == False:
            continue
        pattern = image[-rows:, :cols]
        if pattern_detection(pattern) == False:
            continue
        break
    return ver

#detect
def detect(image):
    #画像サイズの設定
    img_size=300
    pts = np.float32([[0,0], [img_size,0],
                      [img_size,img_size], [0,img_size]])
    #QRコードの検出
    retval, points = cv2.QRCodeDetector().detect(image)
    if retval:
        mat = cv2.getPerspectiveTransform(points, pts)
        dst = cv2.warpPerspective(image, mat, (img_size, img_size))
        ver = version_detection(dst)
        return dst,ver
    else:return None

#base64decode
def base64decode(base64_string):
    # Base64デコード
    decoded_data = base64.b64decode(base64_string)
    # バイトデータを画像に変換
    image = Image.open(BytesIO(decoded_data))
    # PIL ImageをNumpy配列に変換
    image = np.array(image)
    return image

#サイズ計測
def qr_size(data):
    length = 0
    max_length = 0
    n = 0#連続した値の長さ
    for row in data:
        for col in row:
            if col == 0:
                length += 1
            else:
                if max_length < length:
                    max_length = length
                length = 0

    # 7 : size = max_length : 300 より求める(四捨五入)
    size = round((7 * 300) / max_length)
    return size

#二値化
def binarization(img,size):
    #配列サイズの成形
    formatted_img = np.zeros((size,size,3))
    for x in range(size):
        for y in range(size):
            for color in range(3):
                # sizexsizeのブロックごとに最頻値を計算し、新しい配列に代入
                x_s = int(300 * x / size)
                x_e = int(300 * (x + 1) / size)
                y_s = int(300 * y / size)
                y_e = int(300 * (y + 1) / size)
                block = img[x_s : x_e, y_s : y_e, color]
                formatted_img[x, y, color] = mode(block.flatten())[0][0]

    #色見本パターン
    sample = np.zeros((8,3,3)) #8色　4パターン　BGR
    sample[0] = [formatted_img[0,6],formatted_img[6,-1],formatted_img[-7,0]] #青
    sample[1] = [formatted_img[5,5],formatted_img[5,-6],formatted_img[-6,5]] #緑
    sample[2] = [formatted_img[6,0],formatted_img[0,-7],formatted_img[-1,6]] #赤
    sample[3] = [formatted_img[1,5],formatted_img[5,-2],formatted_img[-6,1]] #黄
    sample[4] = [formatted_img[6,6],formatted_img[6,-7],formatted_img[-7,6]] #桃
    sample[5] = [formatted_img[5,1],formatted_img[1,-6],formatted_img[-2,5]] #水
    sample[6] = [formatted_img[3,3],formatted_img[3,-4],formatted_img[-4,3]] #黒
    sample[7] = [formatted_img[1,1],formatted_img[1,-2],formatted_img[-2,1]] #白 
    sample_mean = (sample[:,1] + sample[:,2]) / 2

    binary_sample = [[1,0,0],[0,1,0],[0,0,1],[0,1,1],[1,0,1],[1,1,0],[0,0,0],[1,1,1]]
    binary_image = formatted_img

    for x in range(size):
        for y in range(size):
            if x < size / 2:
                if y < size / 2:
                    abs_diff_sum = np.sum(np.abs(sample[:,0] - formatted_img[x,y]), axis=1)
                else:
                    abs_diff_sum = np.sum(np.abs(sample[:,1] - formatted_img[x,y]), axis=1)
            else:
                if y < size / 2:
                    abs_diff_sum = np.sum(np.abs(sample[:,2] - formatted_img[x,y]), axis=1)
                else:
                    abs_diff_sum = np.sum(np.abs(sample_mean - formatted_img[x,y]), axis=1)

            # 最も近い行のインデックスを取得
            near = np.argmin(abs_diff_sum)
            binary_image[x,y] = binary_sample[near]

    # 3次元配列を画像に変換
    create(formatted_img,len(formatted_img))

    return binary_image

#リードソロモンデコード
def reed_solomon_decode(bits):
    #冗長ビット数の取得
    correction_bits = bits[:16]
    correction_bits_num = int(correction_bits, 2)
    # インスタンスを作成
    rs = RSCodec(correction_bits_num)
    integer_value = int(bits[16:],2)
    byte_data = integer_value.to_bytes((integer_value.bit_length() + 7) // 8, byteorder='big')
    # デコード
    decoded_data, errors, data_type = rs.decode(byte_data)
    return decoded_data

#3Dデータからbit列に変換
def convert(img,size):
    #ファインダパターン
    img[:8,:8] = -1     #左上
    img[:8,-8:] = -1    #右上
    img[-8:,:8] = -1    #左下

    bits = ""
    for x in range(size-1,-1,-1):
        for y in range(size-1,-1,-1):
            for color in range(3):
                if img[x,y,color] != -1:
                    bits += str(int(img[x,y,color]))

    bits = bits[:-1*(len(bits)%8)]
    decoded_data = reed_solomon_decode(bits)

    # UTF-8エンコーディングを使用してバイト列を文字列に変換
    string_data = decoded_data.decode('utf-8')
    return string_data

def decode(base64_string):
    img = base64decode(base64_string)
    if img is None:return None
    img,ver = detect(img)
    if img is None:return None
    size = 17 + 4 * ver
    binary_img = binarization(img,size)
    string_data = convert(binary_img,size)
    return string_data