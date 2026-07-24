import React, { useEffect, useRef, useState } from 'react';
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';
import AudioPlayer from 'osmd-audio-player';

export default function SheetMusic({ xmlData }) {
  const containerRef = useRef(null);
  const osmdRef = useRef(null);
  const audioPlayerRef = useRef(null);
  
  const [isReady, setIsReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    if (!xmlData || !containerRef.current) return;

    setIsReady(false);
    setIsPlaying(false);
    containerRef.current.innerHTML = '';

    // 1. Initialize OSMD with NATIVE cursor settings built-in!
    osmdRef.current = new OpenSheetMusicDisplay(containerRef.current, {
      autoResize: true,
      backend: "svg", 
      drawTitle: false, 
      followCursor: true, // Tell OSMD to track the cursor
      cursorsOptions: [{ type: 0, color: "#ef4444", alpha: 0.6, size: 4 }] // Native Red Cursor!
    });

    audioPlayerRef.current = new AudioPlayer();

    const loadMusic = async () => {
      try {
        // 1. FIRST, actually load and draw the sheet music! (I accidentally deleted this earlier)
        await osmdRef.current.load(xmlData);
        osmdRef.current.zoom = 0.9;
        osmdRef.current.render();

        // 2. THEN load the audio player so it hooks into the drawn music
        await audioPlayerRef.current.loadScore(osmdRef.current);

        // 3. Show the cursor and force it to calculate its starting position
        osmdRef.current.cursor.show();
        osmdRef.current.cursor.update();

        // 4. THE SCALPEL (Adding visual styles without breaking top/left coordinates)
        if (osmdRef.current.cursor.cursorElement) {
          const cursorStyle = osmdRef.current.cursor.cursorElement.style;
          
          cursorStyle.setProperty('width', '4px', 'important');
          cursorStyle.setProperty('height', '108px', 'important');
          cursorStyle.setProperty('background-color', '#ef4444', 'important');
          cursorStyle.setProperty('z-index', '9999', 'important');
          cursorStyle.setProperty('opacity', '0.6', 'important');
        }

        setIsReady(true);
      } catch (error) {
        console.error("Oops! Something went wrong drawing the sheet music:", error);
      }
    };

    loadMusic();

    return () => {
      if (audioPlayerRef.current) {
        try {
          if (audioPlayerRef.current.osmd) {
            audioPlayerRef.current.stop();
          }
        } catch (err) {
          console.warn("Skipped audio cleanup.");
        }
      }
    };
  }, [xmlData]);

  const togglePlay = () => {
    if (!audioPlayerRef.current || !isReady) return;
    if (isPlaying) {
      audioPlayerRef.current.pause();
    } else {
      audioPlayerRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  const stopPlay = () => {
    if (!audioPlayerRef.current || !isReady) return;
    audioPlayerRef.current.stop();
    setIsPlaying(false);
    
    if (osmdRef.current && osmdRef.current.cursor) {
      osmdRef.current.cursor.reset(); 
    }
  };

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
      
      {/* TOOLBAR (Kept exactly as you built it!) */}
      <div className="flex flex-col sm:flex-row items-center justify-between px-8 py-5 bg-slate-100 border-b border-slate-300 gap-4">
        <h3 className="font-extrabold text-slate-800 text-xl flex items-center gap-2">
          🎼 Your Sheet Music
        </h3>
        
        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
          <div className="flex gap-2 mr-2 border-r border-slate-300 pr-4">
            <button 
              onClick={togglePlay}
              disabled={!isReady}
              className={`px-4 py-2 text-sm font-bold rounded-xl transition-colors shadow-sm flex items-center justify-center gap-2 text-white
                ${isReady ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-400 cursor-not-allowed'}`}
            >
              {isPlaying ? "⏸ Pause" : "▶️ Play"}
            </button>
            <button 
              onClick={stopPlay}
              disabled={!isReady}
              className={`px-4 py-2 text-sm font-bold rounded-xl transition-colors shadow-sm flex items-center justify-center gap-2 text-white
                ${isReady ? 'bg-red-600 hover:bg-red-700' : 'bg-gray-400 cursor-not-allowed'}`}
            >
              ⏹ Stop
            </button>
          </div>

          <button onClick={handlePrint} className="flex-1 sm:flex-none px-5 py-2 text-sm font-bold text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors shadow-sm flex items-center justify-center gap-2">
            🖨️ Print
          </button>
          <button onClick={handleDownload} className="flex-1 sm:flex-none px-5 py-2 text-sm font-bold text-white bg-blue-600 rounded-xl hover:bg-blue-700 transition-colors shadow-sm flex items-center justify-center gap-2">
            ⬇️ Download XML
          </button>
        </div>
      </div>

      {/* ✨ THE FIX: A scrollable wrapper, a buffer div, and the OSMD container ✨ */}
      <div className="w-full overflow-x-auto overflow-y-hidden custom-scrollbar bg-white">
        
        {/* The Buffer Div: Enforces the whitespace and centers the music */}
        <div className="min-w-[800px] max-w-7xl mx-auto px-8 md:px-16 py-10">
          
          <div 
            ref={containerRef} 
            style={{ 
              position: 'relative', 
              width: '100%', 
              minHeight: '400px', 
            }} 
          />
          
        </div>
        
      </div>
    </div>
  );
}