// --- IMPORTS ---
import React, { useState, useEffect, useRef } from 'react';
// Import the custom component that actually handles drawing the sheet music and playing audio
import SheetMusic from './SheetMusic.jsx';

// --- MAIN APP COMPONENT ---
// This is the "Command Center". It holds all the user's settings and talks to the Python backend.
export default function App() {
  
  // --- STATE MANAGEMENT (THE SLIDERS & KNOBS) ---
  const [file, setFile] = useState(null); 
  const [complexity, setComplexity] = useState(2); 
  const [keySignature, setKeySignature] = useState('auto'); 
  const [volumeThreshold, setVolumeThreshold] = useState(30); 
  const [polyphonyLimit, setPolyphonyLimit] = useState(6); 
  const [smoothness, setSmoothness] = useState(50); 
  const [handBias, setHandBias] = useState(0); 
  
  // --- UI STATE (LOADING & ERRORS) ---
  const [isLoading, setIsLoading] = useState(false); 
  const [xmlData, setXmlData] = useState(null); 
  const [error, setError] = useState(null); 

  // --- EVENT HANDLERS ---
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      
      const MAX_FILE_SIZE = 2621440; 
      
      if (selectedFile.size > MAX_FILE_SIZE) {
        alert("This file is a bit too large! To keep our AI running smoothly, please upload a song under 2.5MB.");
        e.target.value = null; 
        return; 
      }

      setFile(selectedFile); 
      setError(null); 
    }
  };

  const handleTranscribe = async () => {
    if (!file) {
      setError("Please select an audio file first!");
      return;
    }

    setIsLoading(true);
    setError(null);
    setXmlData(null); 

    const formData = new FormData();
    formData.append('file', file);
    formData.append('complexity', complexity);
    formData.append('key_signature', keySignature);
    formData.append('volume_threshold', volumeThreshold);
    formData.append('polyphony_limit', polyphonyLimit);
    formData.append('smoothness', smoothness);
    formData.append('hand_bias', handBias);

    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://api.pianopilotai.com';

      const response = await fetch(`${API_BASE_URL}/transcribe`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server responded with a ${response.status} error.`);
      }

      const data = await response.json();
      
      if (data.status === 'error') {
        throw new Error(data.message);
      }

      setXmlData(data.xml_data);
      
    } catch (err) {
      console.error(err);
      setError(err.message || "An error occurred during transcription.");
    } finally {
      setIsLoading(false);
    }
  };

  // --- COMPONENT UI (JSX) ---
  return (
    // Updated background to neutral-950 and selection color to amber
    <div className="min-h-screen bg-neutral-950 text-neutral-200 p-6 md:p-12 font-sans selection:bg-teal-700 selection:text-neutral-900 print:bg-white print:text-black print:p-0">
      
      <div className="max-w-3xl mx-auto space-y-10 print:hidden">
        
        {/* --- HEADER SECTION --- */}
        {/* Removed 'space-y-4' to kill the gap between the logo and the subtitle */}
        <div className="text-center pt-4 flex flex-col items-center">
          
          {/* THE MASSIVE LOGO */}
          {/* Changed width to 100% of its container (w-full), set a massive max-width, and removed the bottom margin (mb-0) */}
          <img 
            src="/logo.png" 
            alt="Pianopilot Logo" 
            className="w-full max-w-screen-xl h-auto drop-shadow-2xl mb-0 object-contain"
          />
          
          <p className="text-lg text-neutral-400 max-w-2xl mx-auto mt-2">
            Upload your piano audio and instantly generate clean, playable sheet music.
          </p>
        </div>

        {/* --- MAIN CONTROL PANEL (THE SLIDERS) --- */}
        {/* Updated panel background to a warm charcoal (neutral-900) */}
        <div className="bg-neutral-900 p-8 md:p-10 rounded-[2rem] shadow-2xl border border-neutral-800 space-y-10">
          
          {/* STEP 1: File Upload */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-neutral-800 text-teal-600 text-sm">1</span>
              Upload Audio (.mp3, .wav)
            </label>
            <div className="w-full">
              <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-neutral-700 border-dashed rounded-2xl cursor-pointer bg-neutral-800/30 hover:bg-neutral-800/60 hover:border-neutral-500 transition-all group">
                <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
                  <span className="text-4xl mb-3 grayscale opacity-80 group-hover:scale-110 group-hover:-translate-y-1 transition-all duration-300">🎵</span>
                  <p className="text-sm font-medium text-neutral-300">
                    {file ? <span className="text-teal-600 font-bold">{file.name}</span> : "Click to upload or drag and drop"}
                  </p>
                </div>
                <input type="file" className="hidden" accept="audio/*" onChange={handleFileChange} />
              </label>
            </div>
          </div>

          {/* STEP 2: Complexity (Quantization) */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-neutral-800 text-teal-600 text-sm">2</span>
              Sheet Music Complexity (Grid Snap)
            </label>
            
            <div className="bg-neutral-800/30 border border-neutral-800 p-6 rounded-2xl space-y-8">
              <input 
                type="range" 
                min="1" 
                max="4" 
                step="1"
                value={complexity} 
                onChange={(e) => setComplexity(parseInt(e.target.value))}
                className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-teal-700"
              />
              
              <div className="flex justify-between text-center">
                <div className={`flex flex-col w-1/4 ${complexity === 1 ? 'text-teal-600 font-bold scale-110 transition-all' : 'text-neutral-500'}`}>
                  <span>Beginner</span>
                  <span className="text-xs mt-1">8th Notes</span>
                </div>
                <div className={`flex flex-col w-1/4 ${complexity === 2 ? 'text-teal-600 font-bold scale-110 transition-all' : 'text-neutral-500'}`}>
                  <span>Intermediate</span>
                  <span className="text-xs mt-1">16th Notes</span>
                </div>
                <div className={`flex flex-col w-1/4 ${complexity === 3 ? 'text-teal-600 font-bold scale-110 transition-all' : 'text-neutral-500'}`}>
                  <span>Advanced</span>
                  <span className="text-xs mt-1">32nd Notes</span>
                </div>
                <div className={`flex flex-col w-1/4 ${complexity === 4 ? 'text-red-400 font-bold scale-110 transition-all' : 'text-neutral-500'}`}>
                  <span>Exact (Raw)</span>
                  <span className="text-xs mt-1">No Snapping</span>
                </div>
              </div>
            </div>
          </div>

          {/* STEP 2.5: Volume Sensitivity (Ghost Note Filter) */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-neutral-800 text-teal-600 text-sm">🎚️</span>
              Ghost Note Filter (Volume Sensitivity)
            </label>
            
            <div className="bg-neutral-800/30 border border-neutral-800 p-6 rounded-2xl space-y-6">
              <div className="flex justify-between items-center text-sm font-medium">
                <span className="text-neutral-400">Pick up every whisper</span>
                <span className="text-teal-600 font-bold bg-teal-900/20 px-3 py-1 rounded-full border border-teal-900/50">
                  Threshold: {volumeThreshold}
                </span>
                <span className="text-neutral-400">Loud notes only</span>
              </div>
              
              <input 
                type="range" 
                min="0" 
                max="100" 
                value={volumeThreshold} 
                onChange={(e) => setVolumeThreshold(e.target.value)}
                className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-teal-700"
              />
              
              <p className="text-sm text-neutral-500 text-center">
                Filters out accidental key touches and microphone echoes. If your sheet music looks too cluttered, turn this up!
              </p>
            </div>
          </div>

          {/* STEP 2.75: Polyphony Limit (Chord Simplifier) */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-neutral-800 text-teal-600 text-sm">🎹</span>
              Chord Simplifier (Max Notes at Once)
            </label>
            
            <div className="bg-neutral-800/30 border border-neutral-800 p-6 rounded-2xl space-y-6">
              <div className="flex justify-between items-center text-sm font-medium">
                <span className="text-neutral-400">Single Notes</span>
                <span className="text-teal-600 font-bold bg-teal-900/20 px-3 py-1 rounded-full border border-teal-900/50">
                  Max: {polyphonyLimit} notes
                </span>
                <span className="text-neutral-400">10-Note Chords</span>
              </div>
              
              <input 
                type="range" 
                min="1" 
                max="10" 
                value={polyphonyLimit} 
                onChange={(e) => setPolyphonyLimit(e.target.value)}
                className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-teal-700"
              />
              
              <p className="text-sm text-neutral-500 text-center">
                Prevents the AI from writing impossible 7-note chords by only keeping the loudest notes being played at any given moment.
              </p>
            </div>
          </div>

          {/* STEP 2.8: Smoothness (Legato/Rest Filter) */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-neutral-800 text-teal-600 text-sm">🌊</span>
              Smoothness (Fill Tiny Rests)
            </label>
            
            <div className="bg-neutral-800/30 border border-neutral-800 p-6 rounded-2xl space-y-6">
              <div className="flex justify-between items-center text-sm font-medium">
                <span className="text-neutral-400">Choppy (Exact)</span>
                <span className="text-teal-600 font-bold bg-teal-900/20 px-3 py-1 rounded-full border border-teal-900/50">
                  Smoothness: {smoothness}%
                </span>
                <span className="text-neutral-400">Connected (Legato)</span>
              </div>
              
              <input 
                type="range" 
                min="0" 
                max="100" 
                value={smoothness} 
                onChange={(e) => setSmoothness(e.target.value)}
                className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-teal-700"
              />
              
              <p className="text-sm text-neutral-500 text-center">
                Extends notes to fill awkward tiny gaps. High smoothness removes choppy rests and connects chords together beautifully.
              </p>
            </div>
          </div>

          {/* STEP 2.9: Hand Split Bias (ML Override) */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-neutral-800 text-teal-600 text-sm">🧠</span>
              Hand Split Bias (AI Override)
            </label>
            
            <div className="bg-neutral-800/30 border border-neutral-800 p-6 rounded-2xl space-y-6">
              <div className="flex justify-between items-center text-sm font-medium">
                <span className="text-neutral-400">Force Left Hand (Bass)</span>
                <span className={`font-bold px-3 py-1 rounded-full ${handBias < 0 ? 'bg-purple-900/30 text-purple-400' : handBias > 0 ? 'bg-orange-900/30 text-orange-400' : 'bg-neutral-700/50 text-neutral-300'}`}>
                  {handBias == 0 ? "AI Default (50/50)" : handBias > 0 ? `+${handBias} Right Hand` : `${handBias} Left Hand`}
                </span>
                <span className="text-neutral-400">Force Right Hand (Treble)</span>
              </div>
              
              <input 
                type="range" 
                min="-50" 
                max="50" 
                value={handBias} 
                onChange={(e) => setHandBias(e.target.value)}
                className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-teal-700"
              />
              
              <p className="text-sm text-neutral-500 text-center">
                If the AI is putting too many bass notes in the top staff, slide this to the left to force them down!
              </p>
            </div>
          </div>

          {/* STEP 3: Key Signature */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-neutral-800 text-teal-600 text-sm">3</span>
              Key Signature (Scale)
            </label>
            <div className="relative">
              <select 
                value={keySignature} 
                onChange={(e) => setKeySignature(e.target.value)}
                className="w-full appearance-none p-4 text-base font-medium text-neutral-200 border border-neutral-700 rounded-2xl bg-neutral-800/50 hover:bg-neutral-700/50 focus:ring-2 focus:ring-teal-700 focus:border-teal-700 transition-colors cursor-pointer outline-none shadow-sm"
              >
                <option value="auto">✨ Auto-Detect (AI Picks Best)</option>
                <option value="C">C Major / A Minor</option>
                <option value="G">G Major / E Minor</option>
                <option value="D">D Major / B Minor</option>
                <option value="A">A Major / F# Minor</option>
                <option value="E">E Major / C# Minor</option>
                <option value="B">B Major / G# Minor</option>
                <option value="F#">F# Major / D# Minor</option>
                <option value="F">F Major / D Minor</option>
                <option value="Bb">Bb Major / G Minor</option>
                <option value="Eb">Eb Major / C Minor</option>
                <option value="Ab">Ab Major / F Minor</option>
                <option value="Db">Db Major / Bb Minor</option>
                <option value="Gb">Gb Major / Eb Minor</option>
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-5 text-neutral-400">
                ▼
              </div>
            </div>
          </div>

          {/* --- GENERATE BUTTON & ERROR DISPLAY --- */}
          <div className="mt-8 flex flex-col items-center pt-2">
            
            {error && (
              <div className="mb-6 p-4 w-full text-sm text-red-400 bg-red-950/50 border border-red-900/50 rounded-xl text-center font-medium">
                {error}
              </div>
            )}
            
            <button
              onClick={handleTranscribe}
              disabled={isLoading || !file}
              className={`w-full md:w-auto px-10 py-4 rounded-2xl text-neutral-900 font-extrabold text-lg shadow-lg transition-all duration-300 ${
                isLoading || !file 
                  ? 'bg-neutral-800 text-neutral-500 cursor-not-allowed border border-neutral-700 shadow-none' 
                  : 'bg-gradient-to-r from-teal-600 to-yellow-500 hover:from-teal-400 hover:to-yellow-400 hover:shadow-teal-700/25 transform hover:-translate-y-1'
              }`}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-3">
                  <svg className="animate-spin h-5 w-5 text-neutral-900" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Transcribing...
                </span>
              ) : (
                '✨ Generate Sheet Music'
              )}
            </button>
          </div>
        </div>
      </div>

      {xmlData && (
        <div className="max-w-6xl mx-auto w-full animate-in fade-in duration-700 pt-10 pb-20 px-4 md:px-0 print:p-0 print:pt-0">
          <SheetMusic xmlData={xmlData} />
        </div>
      )}

    </div>
  );
}