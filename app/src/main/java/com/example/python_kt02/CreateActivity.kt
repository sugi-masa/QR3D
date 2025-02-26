package com.example.python_kt02

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Bundle
import android.os.Environment
import android.util.Base64
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.*
import com.chaquo.python.android.AndroidPlatform
import com.example.python_kt02.R
import java.io.File
import java.io.FileOutputStream

class CreateActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.create_layout)

        //レイアウト
        val button2: Button = findViewById(R.id.button2d)
        val button3: Button = findViewById(R.id.button3d)
        val radioGroup: RadioGroup = findViewById(R.id.radioGroup)
        val radioButton4: RadioButton = findViewById(R.id.radioButton4)
        val imageView: ImageView = findViewById(R.id.image_view)
        val textView: EditText = findViewById(R.id.edit_text_view)

        // Pythonコードを実行する前にPython.start()の呼び出しが必要
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
        val py = Python.getInstance() //Pythonのインスタンスを取得
        val module = py.getModule("encode") //encode.pyのモジュールを取得

        radioButton4.isChecked = true // 初期状態ではレベルHを選択
        var eccLevel = 4

        radioGroup.setOnCheckedChangeListener { _, checkedId ->
            when (checkedId) {
                R.id.radioButton1 -> eccLevel = 1
                R.id.radioButton2 -> eccLevel = 2
                R.id.radioButton3 -> eccLevel = 3
                R.id.radioButton4 -> eccLevel = 4
            }
        }
        //ボタンを押したときの処理
        button2.setOnClickListener {
            val inputText = textView.text.toString()

            // Pythonスクリプトを呼び出して結果を取得
            val result = module.callAttr("generate_qr_code", inputText, eccLevel)

            // Base64エンコードされた文字列をデコードしてBitmapに変換
            val imgBase64 = result.toJava(String::class.java)

            val imgBytes = Base64.decode(imgBase64, Base64.DEFAULT)
            val bitmap: Bitmap = BitmapFactory.decodeByteArray(imgBytes, 0, imgBytes.size)

            // 画像を内部ストレージに保存
            //saveImageToInternalStorage(bitmap)

            // 画像を表示する処理
            imageView.setImageBitmap(bitmap)
        }

        //ボタンを押したときの処理
        button3.setOnClickListener {
            val inputText = textView.text.toString()

            // Pythonスクリプトを呼び出して結果を取得
            val result = module.callAttr("encode", inputText, eccLevel)

            // Base64エンコードされた文字列をデコードしてBitmapに変換
            val imgBase64 = result.toJava(String::class.java)

            val imgBytes = Base64.decode(imgBase64, Base64.DEFAULT)
            val bitmap: Bitmap = BitmapFactory.decodeByteArray(imgBytes, 0, imgBytes.size)

            // 画像を内部ストレージに保存
            //saveImageToInternalStorage(bitmap)

            // 画像を表示する処理
            imageView.setImageBitmap(bitmap)
        }

        fun saveImageToInternalStorage(bitmap: Bitmap) {
            val directory = getExternalFilesDir(Environment.DIRECTORY_PICTURES)
            val fileName = "qr_code_image.png"
            val file = File(directory, fileName)

            try {
                val fileOutputStream = FileOutputStream(file)
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, fileOutputStream)
                fileOutputStream.flush()
                fileOutputStream.close()

                val imagePath = file.absolutePath
                Toast.makeText(this, "画像が保存されました。 パス: $imagePath", Toast.LENGTH_LONG).show()
            } catch (e: Exception) {
                e.printStackTrace()
                Toast.makeText(this, "画像の保存中にエラーが発生しました。", Toast.LENGTH_SHORT).show()
            }
        }
    }
}