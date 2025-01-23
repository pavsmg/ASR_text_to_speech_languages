import React, { useState } from "react";
import Header from "../components/Header";
import Sidebar from "../components/Sidebar";
import Footer from "../components/Footer";
import { useNavigate } from "react-router-dom";

function VoiceRecognition() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [response, setResponse] = useState("Aquí aparecerán las palabras reconocidas.");
  const [spectrogram, setSpectrogram] = useState(null);
  const [selectedLanguage, setSelectedLanguage] = useState("");
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [audioChunks, setAudioChunks] = useState([]);

  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev);

  const startRecording = async () => {
    if (!selectedLanguage) {
      alert("Por favor selecciona un idioma antes de grabar.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (event) => {
        chunks.push(event.data);
      };

      recorder.onstop = async () => {
        setAudioChunks(chunks);
        const audioBlob = new Blob(chunks, { type: "audio/wav" });
        const formData = new FormData();
        formData.append("audio", audioBlob);
        formData.append("language", selectedLanguage);

        try {
          const response = await fetch("http://127.0.0.1:5000/recognize", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            throw new Error("Error al comunicarse con el servidor.");
          }

          const result = await response.json();
          setResponse(result.text || "No se reconocieron palabras.");
          setSpectrogram(result.spectrogram || null);
        } catch (error) {
          console.error("Error en la solicitud:", error);
          setResponse("Ocurrió un error al procesar el audio.");
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      setResponse("Grabación en curso...");
    } catch (error) {
      console.error("Error al iniciar la grabación:", error);
      setResponse("No se pudo iniciar la grabación.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
      setResponse("Procesando audio...");
    }
  };

  const cancelRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
      setResponse("Grabación cancelada.");
    }
  };

  return (
    <div className="bg-white min-h-screen flex flex-col relative">
      <Header />
      <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />

      <main className="flex-1 flex flex-col lg:flex-row items-center justify-between gap-8 p-6">
        <div className="bg-gray-100 p-6 rounded-lg shadow-lg w-full lg:w-3/4">
          <h3 className="text-blue-800 text-center font-bold mb-4">Espectrograma</h3>
          {spectrogram ? (
            <img
              src={`data:image/png;base64,${spectrogram}`}
              alt="Espectrograma del audio"
              className="w-full h-auto rounded-md"
            />
          ) : (
            <p className="text-center text-gray-500">
              {response === "Procesando audio..."
                ? "Generando espectrograma..."
                : "El espectrograma aparecerá aquí."}
            </p>
          )}
        </div>

        <div className="bg-white p-4 rounded-lg shadow-xl border border-gray-300">
          <h3 className="text-blue-600 font-bold text-center mb-4 text-lg">
            Seleccionar idioma
          </h3>
          <select
            value={selectedLanguage}
            onChange={(e) => setSelectedLanguage(e.target.value)}
            className="block w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-400"
            aria-label="Seleccionar idioma"
          >
            <option value="">-- Selecciona un idioma --</option>
            <option value="es">Español</option>
            <option value="en">English</option>
            <option value="tr">Türkce</option>
          </select>
        </div>

        <div className="bg-gradient-to-br from-blue-600 to-blue-800 text-white p-6 rounded-lg shadow-lg w-full lg:w-1/4">
          <div className="flex flex-col gap-4">
            <button
              onClick={startRecording}
              className={`py-2 px-4 rounded-md font-semibold transition ${
                isRecording || !selectedLanguage
                  ? "bg-gray-400 cursor-not-allowed"
                  : "bg-white text-blue-800 hover:bg-gray-100"
              }`}
              disabled={isRecording || !selectedLanguage}
            >
              Iniciar Grabación
            </button>
            <button
              onClick={stopRecording}
              className={`py-2 px-4 rounded-md font-semibold transition ${
                isRecording
                  ? "bg-red-600 text-white hover:bg-red-700"
                  : "bg-gray-400 cursor-not-allowed"
              }`}
              disabled={!isRecording}
            >
              Detener
            </button>
            <button
              onClick={cancelRecording}
              className={`py-2 px-4 rounded-md font-semibold transition border ${
                isRecording
                  ? "border-red-600 text-red-600 hover:bg-red-600 hover:text-white"
                  : "border-gray-400 text-gray-400 cursor-not-allowed"
              }`}
              disabled={!isRecording}
            >
              Cancelar
            </button>
          </div>
          <div className="mt-4 bg-gray-100 p-6 rounded-lg shadow-lg text-center">
            <h3 className="text-blue-800 font-bold text-lg">Resultado</h3>
            <p
              className={`mt-2 text-lg font-bold ${
                response === "No se reconocieron palabras."
                  ? "text-red-600 animate-pulse"
                  : "bg-gradient-to-r from-green-400 via-blue-500 to-purple-600 bg-clip-text text-transparent animate-fade-in"
              }`}
            >
              {response}
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}

export default VoiceRecognition;
