import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import VoiceRecognition from "./pages/VoiceRecognition";


function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<VoiceRecognition />} />
      </Routes>
    </Router>
  );
}

export default App;
