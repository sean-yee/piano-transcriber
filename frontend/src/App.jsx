import React, { useState, useEffect, useRef } from 'react';

// --- MAIN APP COMPONENT ---
export default function App() {
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState('advanced');
  const [keySignature, setKeySignature] = useState('auto');
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
    formData.append('mode', mode);
    formData.append('key_signature', keySignature);

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

          {/* Step 2: Complexity */}
          <div className="space-y-4">
            <label className="flex items-center gap-3 text-lg font-bold text-white">
              <span className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-800 text-blue-400 text-sm">2</span>
              Select Complexity
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Beginner Card */}
              <div 
                onClick={() => setMode('beginner')}
                className={`relative flex cursor-pointer rounded-2xl border p-5 transition-all duration-200 ${
                  mode === 'beginner' 
                    ? 'bg-blue-900/20 border-blue-500' 
                    : 'border-slate-700 bg-transparent hover:border-slate-500'
                }`}
              >
                <div className="flex w-full items-center justify-between">
                  <div>
                    <p className={`font-bold text-lg ${mode === 'beginner' ? 'text-blue-400' : 'text-white'}`}>Beginner</p>
                    <p className="text-sm text-slate-400 mt-1">Filters out fast 16th notes for easy reading.</p>
                  </div>
                  {mode === 'beginner' && (
                    <div className="w-6 h-6 rounded bg-[#5bb974] flex items-center justify-center shadow-sm flex-shrink-0 ml-3">
                      <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </div>
              </div>

              {/* Advanced Card */}
              <div 
                onClick={() => setMode('advanced')}
                className={`relative flex cursor-pointer rounded-2xl border p-5 transition-all duration-200 ${
                  mode === 'advanced' 
                    ? 'bg-blue-900/20 border-blue-500' 
                    : 'border-slate-700 bg-transparent hover:border-slate-500'
                }`}
              >
                <div className="flex w-full items-center justify-between">
                  <div>
                    <p className={`font-bold text-lg ${mode === 'advanced' ? 'text-blue-400' : 'text-white'}`}>Advanced</p>
                    <p className="text-sm text-slate-400 mt-1">Exact, intricate rhythms and syncopation.</p>
                  </div>
                  {mode === 'advanced' && (
                    <div className="w-6 h-6 rounded bg-[#5bb974] flex items-center justify-center shadow-sm flex-shrink-0 ml-3">
                      <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </div>
              </div>
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
          <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 pt-4 pb-20">
            <SheetMusic xmlData={xmlData} />
          </div>
        )}

      </div>
    </div>
  );
}

// --- SHEET MUSIC VIEWER COMPONENT ---
function SheetMusic({ xmlData }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!xmlData || !containerRef.current) return;

    const renderSheetMusic = () => {
      if (!window.opensheetmusicdisplay) return;
      containerRef.current.innerHTML = '';

      const osmd = new window.opensheetmusicdisplay.OpenSheetMusicDisplay(containerRef.current, {
        autoResize: true,
        backend: "svg", 
        drawTitle: false, 
      });

      osmd.load(xmlData).then(() => {
        osmd.zoom = 0.9; 
        osmd.render();
      }).catch((error) => {
        console.error("Oops! Something went wrong drawing the sheet music:", error);
      });
    };

    if (window.opensheetmusicdisplay) {
      renderSheetMusic();
    } else {
      const scriptId = 'osmd-script';
      let script = document.getElementById(scriptId);

      if (!script) {
        script = document.createElement('script');
        script.id = scriptId;
        script.src = "https://unpkg.com/opensheetmusicdisplay@1.8.8/build/opensheetmusicdisplay.min.js";
        script.async = true;
        document.body.appendChild(script);
      }

      script.addEventListener('load', renderSheetMusic);

      return () => {
        script.removeEventListener('load', renderSheetMusic);
      };
    }

    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, [xmlData]);

  const handleDownload = () => {
    if (!xmlData) return;
    const blob = new Blob([xmlData], { type: 'application/vnd.recordare.musicxml+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = "AI_Transcription.musicxml"; 
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    window.print(); 
  };

  return (
    <div className="w-full bg-white rounded-3xl shadow-[0_0_40px_rgba(0,0,0,0.3)] border border-slate-700 overflow-hidden">
      <div className="flex flex-col sm:flex-row items-center justify-between px-8 py-5 bg-slate-100 border-b border-slate-300 gap-4">
        <h3 className="font-extrabold text-slate-800 text-xl flex items-center gap-2">
          🎼 Your Sheet Music
        </h3>
        <div className="flex gap-3 w-full sm:w-auto">
          <button 
            onClick={handlePrint}
            className="flex-1 sm:flex-none px-5 py-2.5 text-sm font-bold text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors shadow-sm flex items-center justify-center gap-2"
          >
            🖨️ Print
          </button>
          <button 
            onClick={handleDownload}
            className="flex-1 sm:flex-none px-5 py-2.5 text-sm font-bold text-white bg-blue-600 rounded-xl hover:bg-blue-700 transition-colors shadow-sm flex items-center justify-center gap-2"
          >
            ⬇️ Download XML
          </button>
        </div>
      </div>

      <div 
        ref={containerRef} 
        style={{ 
          width: '100%', 
          maxWidth: '100%', 
          minHeight: '400px', 
          backgroundColor: 'white', 
          overflowX: 'auto', 
          overflowY: 'hidden',
          padding: '40px'
        }} 
      />
    </div>
  );
}