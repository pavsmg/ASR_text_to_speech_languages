from flask import Flask, request, jsonify
import os
import wave
import vosk
import json
from flask_cors import CORS
import librosa
import librosa.display
import matplotlib.pyplot as plt
import io
import base64
import subprocess
import numpy as np
import tempfile

# Inicializar Flask
app = Flask(__name__)
CORS(app)

# Rutas de los modelos por idioma
MODEL_PATHS = {
    "es": r"modelos/vosk-model-es-0.42",
    "en": r"modelos/vosk-model-en-us-0.22",
    "tr": r"modelos/vosk-model-small-tr-0.3"
}

# Variable global para el modelo cargado
_model = None


def check_ffmpeg():
    """Verifica que FFmpeg esté instalado."""
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("FFmpeg está instalado.")
    except FileNotFoundError:
        raise EnvironmentError("FFmpeg no está instalado. Por favor instálalo antes de usar esta aplicación.")


check_ffmpeg()


def get_vosk_model(language):
    """Carga dinámicamente el modelo de Vosk según el idioma seleccionado."""
    global _model
    model_path = MODEL_PATHS.get(language)

    if not model_path:
        raise ValueError(f"Modelo no encontrado para el idioma {language}")

    if _model is None or _model[0] != language:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo no encontrado en {model_path}")
        print(f"Cargando modelo Vosk para el idioma '{language}'...")
        _model = (language, vosk.Model(model_path))
        print("Modelo Vosk cargado correctamente.")
    
    return _model[1]


def preprocess_audio(audio_path):
    """Convierte un archivo de audio a formato WAV mono 16kHz."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        processed_path = temp_file.name

    try:
        command = [
            "ffmpeg", "-i", audio_path,
            "-ac", "1", "-ar", "16000",  # Convertir a mono y 16kHz
            processed_path, "-y"  # Sobrescribir si existe
        ]
        subprocess.run(command, check=True, stderr=subprocess.PIPE)
        print(f"Audio preprocesado guardado en {processed_path}.")
        return processed_path
    except subprocess.CalledProcessError as e:
        print(f"Error al preprocesar el audio: {e.stderr.decode()}")
        raise


def generate_spectrogram(audio_path):
    """Genera un espectrograma del archivo de audio."""
    print(f"Generando espectrograma para {audio_path}...")
    try:
        y, sr = librosa.load(audio_path, sr=None)
        if len(y) == 0:
            raise ValueError("El archivo de audio está vacío.")
        
        # Generar el espectrograma
        S = librosa.feature.melspectrogram(y=y, sr=sr)
        S_dB = librosa.power_to_db(S, ref=np.max)

        # Crear la figura del espectrograma
        plt.figure(figsize=(10, 4))
        librosa.display.specshow(S_dB, sr=sr, x_axis='time', y_axis='mel', cmap='magma')
        plt.colorbar(format='%+2.0f dB')
        plt.title('Espectrograma')
        plt.tight_layout()

        # Guardar el espectrograma como una imagen en memoria
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        print("Espectrograma generado correctamente.")
        spectrogram_base64 = base64.b64encode(buf.read()).decode('utf-8')
        return spectrogram_base64
    except Exception as e:
        print(f"Error al generar el espectrograma: {e}")
        raise


@app.route("/recognize", methods=["POST"])
def recognize():
    """Endpoint para procesar audio y reconocer palabras."""
    temp_audio_path = None
    processed_audio_path = None

    try:
        # Validar archivo de audio
        if "audio" not in request.files:
            print("Error: No se proporcionó un archivo de audio.")
            return jsonify({"error": "No se proporcionó un archivo de audio."}), 400

        # Obtener idioma
        language = request.form.get("language", "en")  # Idioma predeterminado

        audio_file = request.files["audio"]
        temp_audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        audio_file.save(temp_audio_path)
        print(f"Archivo de audio recibido y guardado temporalmente en {temp_audio_path}.")

        # Validar tamaño del archivo
        file_size = os.path.getsize(temp_audio_path)
        print(f"Tamaño del archivo: {file_size} bytes.")
        if file_size == 0:
            print("Error: El archivo está vacío.")
            return jsonify({"error": "El archivo está vacío."}), 400

        # Preprocesar el archivo
        processed_audio_path = preprocess_audio(temp_audio_path)

        # Generar espectrograma
        spectrogram_base64 = generate_spectrogram(processed_audio_path)

        # Procesar el audio con Vosk
        with wave.open(processed_audio_path, "rb") as wf:
            print(f"Propiedades del audio: Canales={wf.getnchannels()}, Frecuencia={wf.getframerate()}, Ancho={wf.getsampwidth()} bytes")
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
                print("Error: Formato de audio no compatible.")
                return jsonify({"error": "El audio debe estar en formato WAV mono 16kHz."}), 400

            recognizer = vosk.KaldiRecognizer(get_vosk_model(language), wf.getframerate())
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    print(f"Resultado parcial: {result}")
                    results.append(result.get("text", ""))

            final_result = json.loads(recognizer.FinalResult())
            print(f"Resultado final: {final_result}")
            results.append(final_result.get("text", ""))

        return jsonify({
            "text": " ".join(results).strip(),
            "spectrogram": spectrogram_base64
        }), 200
    except Exception as e:
        print(f"Error general: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        # Eliminar archivos temporales
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            print(f"Archivo temporal {temp_audio_path} eliminado.")
        if processed_audio_path and os.path.exists(processed_audio_path):
            os.remove(processed_audio_path)
            print(f"Archivo temporal {processed_audio_path} eliminado.")


# Iniciar el servidor
if __name__ == "__main__":
    app.run(debug=True)
