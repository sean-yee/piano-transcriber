import React, { useState, useEffect, useRef } from 'react';
import SheetMusic from './SheetMusic.jsx';

// --- MAIN APP COMPONENT ---
export default function App() {
  const [file, setFile] = useState(null);
  const [complexity, setComplexity] = useState(2); // 1=Beginner, 2=Intermediate, 3=Advanced, 4=Exact
  const [keySignature, setKeySignature] = useState('auto');
  const [volumeThreshold, setVolumeThreshold] = useState(30);
  const [polyphonyLimit, setPolyphonyLimit] = useState(6);
  const [smoothness, setSmoothness] = useState(50);
  const [isLoading, setIsLoading] = useState(false);
  const [xmlData, setXmlData] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
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

    try {
      // Ensure this points to your running FastAPI backend
      const response = await fetch('http://localhost:8000/transcribe', {
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

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-200 p-6 md:p-12 font-sans selection:bg-blue-500 selection:text-white">
      <div className="max-w-3xl mx-auto space-y-10">
        
        {/* Header Section */}
        <div className="text-center space-y-4 pt-4">
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight flex items-center justify-center gap-4">
            <span className="text-white">🎹</span> 
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">
              AI Piano Transcriber
            </span>
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto">
            Upload your piano audio and instantly generate clean, playable sheet music.
          </p>
        </div>

        {/* Main Control Panel */}
        <div className="bg-[#111827] p-8 md:p-10 rounded-[2rem] shadow-2xl border border-slate-800 space-y-10">
          
          {/* Step 1: File Upload */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-800 text-blue-400 text-sm">1</span>
              Upload Audio (.mp3, .wav)
            </label>
            <div className="w-full">
              <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-slate-700 border-dashed rounded-2xl cursor-pointer bg-[#151e32]/50 hover:bg-[#151e32] hover:border-slate-500 transition-all group">
                <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
                  <span className="text-4xl mb-3 grayscale opacity-80 group-hover:scale-110 group-hover:-translate-y-1 transition-all duration-300">🎵</span>
                  <p className="text-sm font-medium text-slate-300">
                    {file ? <span className="text-blue-400 font-bold">{file.name}</span> : "Click to upload or drag and drop"}
                  </p>
                </div>
                <input type="file" className="hidden" accept="audio/*" onChange={handleFileChange} />
              </label>
            </div>
          </div>

          {/* Step 2: Complexity (Quantization) */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-800 text-blue-400 text-sm">2</span>
              Sheet Music Complexity (Grid Snap)
            </label>
            
            <div className="bg-slate-800/30 border border-slate-700 p-6 rounded-2xl space-y-8">
              <input 
                type="range" 
                min="1" 
                max="4" 
                step="1"
                value={complexity} 
                onChange={(e) => setComplexity(parseInt(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              
              {/* Dynamic Labels based on slider position */}
              <div className="flex justify-between text-center">
                <div className={`flex flex-col w-1/4 ${complexity === 1 ? 'text-blue-400 font-bold scale-110 transition-all' : 'text-slate-500'}`}>
                  <span>Beginner</span>
                  <span className="text-xs mt-1">8th Notes</span>
                </div>
                <div className={`flex flex-col w-1/4 ${complexity === 2 ? 'text-blue-400 font-bold scale-110 transition-all' : 'text-slate-500'}`}>
                  <span>Intermediate</span>
                  <span className="text-xs mt-1">16th Notes</span>
                </div>
                <div className={`flex flex-col w-1/4 ${complexity === 3 ? 'text-blue-400 font-bold scale-110 transition-all' : 'text-slate-500'}`}>
                  <span>Advanced</span>
                  <span className="text-xs mt-1">32nd Notes</span>
                </div>
                <div className={`flex flex-col w-1/4 ${complexity === 4 ? 'text-red-400 font-bold scale-110 transition-all' : 'text-slate-500'}`}>
                  <span>Exact (Raw)</span>
                  <span className="text-xs mt-1">No Snapping</span>
                </div>
              </div>
            </div>
          </div>

          {/* Step 2.5: Volume Sensitivity (Ghost Note Filter) */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-800 text-blue-400 text-sm">🎚️</span>
              Ghost Note Filter (Volume Sensitivity)
            </label>
            
            <div className="bg-slate-800/30 border border-slate-700 p-6 rounded-2xl space-y-6">
              <div className="flex justify-between items-center text-sm font-medium">
                <span className="text-slate-400">Pick up every whisper</span>
                <span className="text-blue-400 font-bold bg-blue-900/30 px-3 py-1 rounded-full">
                  Threshold: {volumeThreshold}
                </span>
                <span className="text-slate-400">Loud notes only</span>
              </div>
              
              <input 
                type="range" 
                min="0" 
                max="100" 
                value={volumeThreshold} 
                onChange={(e) => setVolumeThreshold(e.target.value)}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              
              <p className="text-sm text-slate-500 text-center">
                Filters out accidental key touches and microphone echoes. If your sheet music looks too cluttered, turn this up!
              </p>
            </div>
          </div>

          {/* Step 2.75: Polyphony Limit (Chord Simplifier) */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-800 text-blue-400 text-sm">🎹</span>
              Chord Simplifier (Max Notes at Once)
            </label>
            
            <div className="bg-slate-800/30 border border-slate-700 p-6 rounded-2xl space-y-6">
              <div className="flex justify-between items-center text-sm font-medium">
                <span className="text-slate-400">Single Notes</span>
                <span className="text-blue-400 font-bold bg-blue-900/30 px-3 py-1 rounded-full">
                  Max: {polyphonyLimit} notes
                </span>
                <span className="text-slate-400">10-Note Chords</span>
              </div>
              
              <input 
                type="range" 
                min="1" 
                max="10" 
                value={polyphonyLimit} 
                onChange={(e) => setPolyphonyLimit(e.target.value)}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              
              <p className="text-sm text-slate-500 text-center">
                Prevents the AI from writing impossible 7-note chords by only keeping the loudest notes being played at any given moment.
              </p>
            </div>
          </div>

          {/* Step 2.8: Smoothness (Legato/Rest Filter) */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-800 text-blue-400 text-sm">🌊</span>
              Smoothness (Fill Tiny Rests)
            </label>
            
            <div className="bg-slate-800/30 border border-slate-700 p-6 rounded-2xl space-y-6">
              <div className="flex justify-between items-center text-sm font-medium">
                <span className="text-slate-400">Choppy (Exact)</span>
                <span className="text-blue-400 font-bold bg-blue-900/30 px-3 py-1 rounded-full">
                  Smoothness: {smoothness}%
                </span>
                <span className="text-slate-400">Connected (Legato)</span>
              </div>
              
              <input 
                type="range" 
                min="0" 
                max="100" 
                value={smoothness} 
                onChange={(e) => setSmoothness(e.target.value)}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              
              <p className="text-sm text-slate-500 text-center">
                Extends notes to fill awkward tiny gaps. High smoothness removes choppy rests and connects chords together beautifully.
              </p>
            </div>
          </div>

          {/* Step 3: Key Signature */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-800 text-blue-400 text-sm">3</span>
              Key Signature (Scale)
            </label>
            <div className="relative">
              <select 
                value={keySignature} 
                onChange={(e) => setKeySignature(e.target.value)}
                className="w-full appearance-none p-4 text-base font-medium text-slate-200 border border-slate-700 rounded-2xl bg-slate-800/50 hover:bg-slate-700/50 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors cursor-pointer outline-none shadow-sm"
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
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-5 text-slate-400">
                ▼
              </div>
            </div>
          </div>

          {/* Action Button & Errors */}
          <div className="mt-8 flex flex-col items-center pt-2">
            {error && (
              <div className="mb-6 p-4 w-full text-sm text-red-400 bg-red-950/50 border border-red-900/50 rounded-xl text-center font-medium">
                {error}
              </div>
            )}
            
            <button
              onClick={handleTranscribe}
              disabled={isLoading || !file}
              className={`w-full md:w-auto px-10 py-4 rounded-2xl text-white font-bold text-lg shadow-lg transition-all duration-300 ${
                isLoading || !file 
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700' 
                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 hover:shadow-blue-500/25 transform hover:-translate-y-1'
              }`}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-3">
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
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

        {/* Sheet Music Display */}
        {xmlData && (
          <div className="animate-in fade-in duration-700 pt-4 pb-20">
            <SheetMusic xmlData={xmlData} />
          </div>
        )}

      </div>
    </div>
  );
}

