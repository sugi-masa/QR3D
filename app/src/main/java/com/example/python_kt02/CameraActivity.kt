package com.example.python_kt02

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.os.Bundle
import android.os.Environment
import android.text.method.LinkMovementMethod
import android.util.Base64
import android.util.Log
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import com.example.python_kt02.R
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class CameraActivity : AppCompatActivity() {
    private var cameraExecutor: ExecutorService? = null
    private lateinit var previewView: PreviewView
    private lateinit var textView: TextView

    private var cameraProvider: ProcessCameraProvider? = null
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.d("MyApp", "onCreate()")
        setContentView(R.layout.camera_layout)

        // レイアウトの初期化
        previewView = findViewById(R.id.previewView)
        textView = findViewById(R.id.textView)
//        // ImageCaptureの初期化
//        imageCapture = ImageCapture.Builder().build()

        // カメラ権限の確認とリクエスト
        if (allPermissionsGranted()) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.CAMERA),
                REQUEST_CAMERA_PERMISSION
            )
        }

        // URLがクリックされたときのリスナーを設定
        textView.movementMethod = LinkMovementMethod.getInstance()

        // コピー機能を追加
        textView.setOnLongClickListener {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = ClipData.newPlainText("label", textView.text)
            clipboard.setPrimaryClip(clip)
            Toast.makeText(this, "クリップボードにコピーしました", Toast.LENGTH_SHORT).show()
            true
        }

        cameraExecutor = Executors.newSingleThreadExecutor()
    }

    private fun allPermissionsGranted() =
        ContextCompat.checkSelfPermission(
            this, Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED

    private fun startCamera() {
        Log.d("MyApp", "startCamera()")
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            // Previewの設定
            val preview = Preview.Builder()
                .setTargetRotation(previewView.display.rotation)
                .build()
            preview.setSurfaceProvider(previewView.surfaceProvider)

            val imageAnalysis = ImageAnalysis.Builder()
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor!!, ImageAnalysis.Analyzer { imageProxy ->
                        processImage(imageProxy)
                    })
                }

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this, cameraSelector, preview, imageAnalysis
                )

            } catch (exc: Exception) {
                Log.e("MyApp", "Error starting camera", exc)
            }
        }, ContextCompat.getMainExecutor(this))
        Log.d("MyApp", "startCameraEnd()")
    }

    private fun processImage(imageProxy: ImageProxy) {
        Log.d("MyApp", "processImage()")
        try {
            // 画像処理を行う関数を呼び出す
            val processedString = performImageProcessing(imageProxy)
            Log.d("resultString", processedString)
            if(processedString != "") {
                runOnUiThread {

                    textView = findViewById(R.id.textView)
                    textView.text = processedString
                }
            }
        } catch (e: Exception) {
            Log.e("MyApp", "Error processing image", e)
        } finally {
            // ImageProxyをクローズする
            imageProxy.close()
        }

    }

    private fun performImageProcessing(imageProxy: ImageProxy):String{
        // Pythonコードを実行する前にPython.start()の呼び出しが必要
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
        val py = Python.getInstance() //Pythonのインスタンスを取得
        val module = py.getModule("decode") //decode.pyのモジュールを取得
        var result = ""
        try {
            val base64String = getImageProxyData(imageProxy)
            result = module.callAttr("decode",base64String).toString()
            Log.d("result", "result:$result")
            //writeBase64ToInternalStorage(this, result, "bits.txt")
        } catch (e: Exception) {
            Log.e("MyApp", "Error processing image", e)
        } finally {
            imageProxy.close()
        }
        return result
    }

    private fun getImageProxyData(imageProxy: ImageProxy): String {
        val yBuffer = imageProxy.planes[0].buffer
        val uBuffer = imageProxy.planes[1].buffer
        val vBuffer = imageProxy.planes[2].buffer

        val ySize = yBuffer.remaining()
        val uSize = uBuffer.remaining()
        val vSize = vBuffer.remaining()

        val nv21 = ByteArray(ySize + uSize + vSize)
        yBuffer.get(nv21, 0, ySize)
        uBuffer.get(nv21, ySize, uSize)
        vBuffer.get(nv21, ySize + uSize, vSize)

        val yuvImage = YuvImage(nv21, ImageFormat.NV21, imageProxy.width, imageProxy.height, null)
        val byteArrayOutputStream = ByteArrayOutputStream()
        yuvImage.compressToJpeg(
            Rect(0, 0, yuvImage.width, yuvImage.height),
            100,
            byteArrayOutputStream
        )
        val jpegArray = byteArrayOutputStream.toByteArray()
        val bitmap = BitmapFactory.decodeByteArray(jpegArray, 0, jpegArray.size)
        val pngByteArrayOutputStream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, pngByteArrayOutputStream)
        val pngByteArray = pngByteArrayOutputStream.toByteArray()

        return Base64.encodeToString(pngByteArray, Base64.DEFAULT)
    }

    private fun writeBase64ToInternalStorage(context: Context, base64String: String, fileName: String) {
        // ファイルを生成
        val file = File(context.filesDir, fileName)

        try {
            // FileOutputStreamを使用してファイルに書き込み
            val fos = FileOutputStream(file)
            fos.write(base64String.toByteArray())
            fos.close()

            // ファイルのパスをログに出力
            val filePath = file.absolutePath
            //Logcatに表示
            Log.d("FilePath", filePath)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun bitmapToBase64(bitmap: Bitmap): String {
        val byteArrayOutputStream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, byteArrayOutputStream)
        val byteArray = byteArrayOutputStream.toByteArray()
        return Base64.encodeToString(byteArray, Base64.DEFAULT)
    }

    private fun saveImageToInternalStorage(bitmap: Bitmap?) {
        val directory = getExternalFilesDir(Environment.DIRECTORY_PICTURES)
        val fileName = "qr_code_image.png"
        val file = File(directory, fileName)

        try {
            val fileOutputStream = FileOutputStream(file)
            bitmap?.compress(Bitmap.CompressFormat.PNG, 100, fileOutputStream)
            fileOutputStream.flush()
            fileOutputStream.close()

            val imagePath = file.absolutePath
            Log.d("MyApp", "Success save image$imagePath")
        } catch (e: Exception) {
            e.printStackTrace()
            Log.e("MyApp", "Error save image", e)
        }
    }

    private fun displaySavedImage() {
        Log.d("MyApp", "displaySavedImage()")
        val directory = getExternalFilesDir(Environment.DIRECTORY_PICTURES)
        val fileName = "qr_code_image.png"
        val file = File(directory, fileName)

        if (file.exists()) {
            // ファイルが存在する場合、そのファイルをImageViewに表示
            val bitmap = BitmapFactory.decodeFile(file.absolutePath)
            //capturedImageView.setImageBitmap(bitmap)
            Log.d("MyApp", "Success display saved image")
        } else {
            Log.e("MyApp", "Image file not found")
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraProvider?.unbindAll()
        cameraExecutor?.shutdown()
    }
    companion object {
        private const val TAG = "CameraTestActivity"
        private const val REQUEST_CAMERA_PERMISSION = 10
    }
}
