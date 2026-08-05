// --- IMPORTS ---
import React, { useEffect, useRef, useState } from 'react';
// OpenSheetMusicDisplay (OSMD) is the engine that converts XML data into visual sheet music (SVG)
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';
// AudioPlayer hooks into OSMD and uses Tone.js to actually play the notes out loud
import AudioPlayer from 'osmd-audio-player';

export default function SheetMusic({ xmlData }) {
  // --- REFS ---
  // Refs store data that persists across renders WITHOUT triggering a UI update.
  // We use them here to hold onto the actual HTML div and the heavy JavaScript classes.
  const containerRef = useRef(null); // Points to the empty <div> where the sheet music will be drawn
  const osmdRef = useRef(null); // Holds the actual OSMD rendering engine instance
  const audioPlayerRef = useRef(null); // Holds the Tone.js audio engine instance
  
  // --- STATE ---
  // State variables trigger UI updates (like changing a button from Play to Pause)
  const [isReady, setIsReady] = useState(false); // True when the music has fully finished drawing
  const [isPlaying, setIsPlaying] = useState(false); // Tracks if the audio is currently running
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0); // The value for the frontend UI dropdown
  const [baseBpm, setBaseBpm] = useState(120); // The original tempo of the song (used for Sledgehammer math)

  // --- MAIN INITIALIZATION HOOK ---
  // This useEffect runs every single time the `xmlData` prop changes (i.e., when you generate a new song)
  useEffect(() => {
    // Safety check: Don't do anything if we don't have XML data or a valid HTML container
    if (!xmlData || !containerRef.current) return;

    // Reset everything for the new song
    setIsReady(false);
    setIsPlaying(false);
    containerRef.current.innerHTML = ''; // Wipe the old sheet music off the screen

    // 1. Initialize the Visual Engine (OSMD)
    osmdRef.current = new OpenSheetMusicDisplay(containerRef.current, {
      autoResize: true, // Redraw if the user resizes their browser window
      backend: "svg", // Render as crisp vector graphics
      drawTitle: false, // Hide the default ugly title text
      followCursor: true, // Tell the engine to scroll the page as the song plays
      cursorsOptions: [{ type: 0, color: "#ef4444", alpha: 0.6, size: 4 }] // Configure our custom red cursor
    });

    // Initialize the Audio Engine
    audioPlayerRef.current = new AudioPlayer();

    // 2. Async Loading Function
    // We have to wait for OSMD to finish calculating the layout before we can attach the audio
    const loadMusic = async () => {
      try {
        // Step A: Parse the XML and physically draw the SVG onto the screen
        await osmdRef.current.load(xmlData);
        osmdRef.current.zoom = 0.9; // Scale it down slightly so it fits nicely
        osmdRef.current.render();

        // Step B: Hook the audio engine into the newly drawn sheet music
        await audioPlayerRef.current.loadScore(osmdRef.current);

        // Step C: Snatch the original base BPM out of the audio engine so our speed math works later!
        if (audioPlayerRef.current.playbackSettings && audioPlayerRef.current.playbackSettings.bpm) {
          setBaseBpm(audioPlayerRef.current.playbackSettings.bpm);
        }

        // Step D: Show the red tracking cursor and force it to snap to the very first note
        osmdRef.current.cursor.show();
        osmdRef.current.cursor.update();

        // Step E: The CSS Scalpel
        // OSMD's default cursor is a bit clunky. We reach directly into the DOM to style it 
        // without breaking OSMD's internal X/Y coordinate tracking math.
        if (osmdRef.current.cursor.cursorElement) {
          const cursorStyle = osmdRef.current.cursor.cursorElement.style;
          
          cursorStyle.setProperty('width', '4px', 'important');
          cursorStyle.setProperty('height', '108px', 'important'); // Make it tall enough to span the grand staff
          cursorStyle.setProperty('background-color', '#ef4444', 'important');
          cursorStyle.setProperty('z-index', '9999', 'important'); // Keep it on top of the notes
          cursorStyle.setProperty('opacity', '0.6', 'important');
        }

        // Everything is loaded and styled. Unlock the UI buttons!
        setIsReady(true);
      } catch (error) {
        console.error("Oops! Something went wrong drawing the sheet music:", error);
      }
    };

    // Actually trigger the load function we just defined
    loadMusic();

    // 3. Cleanup Function
    // When the component unmounts (or a new song loads), we MUST kill the old audio engine 
    // otherwise the old song will keep playing invisibly in the background!
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

  // --- AUDIO CONTROLS ---

  // THE BPM SLEDGEHAMMER: Because osmd-audio-player ignores standard playbackRate, 
  // we manually calculate a new BPM and force-feed it to the internal playbackSettings.
  const handleSpeedChange = (e) => {
    const newSpeed = parseFloat(e.target.value);
    setPlaybackSpeed(newSpeed); // Update the React dropdown UI
    
    if (audioPlayerRef.current) {
      // Math: Original BPM (e.g., 100) * 0.5x speed = 50 Target BPM
      const targetBpm = Math.round(baseBpm * newSpeed);
      
      // Attempt Method 1: The official setter
      if (typeof audioPlayerRef.current.setBpm === 'function') {
        audioPlayerRef.current.setBpm(targetBpm);
      } 
      // Attempt Method 2: Brutally mutate the internal settings object
      else if (audioPlayerRef.current.playbackSettings) {
        audioPlayerRef.current.playbackSettings.bpm = targetBpm;
      }
      
      // If the song is actively playing, quickly pause and play it to force Tone.js to sync the new tempo
      if (isPlaying) {
        audioPlayerRef.current.pause();
        setTimeout(() => {
          audioPlayerRef.current.play();
        }, 50); 
      }
    }
  };

  // Toggles the audio engine between Play and Pause states
  const togglePlay = () => {
    if (!audioPlayerRef.current || !isReady) return;
    if (isPlaying) {
      audioPlayerRef.current.pause();
    } else {
      audioPlayerRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  // Completely halts the audio engine and resets the visual cursor back to Measure 1
  const stopPlay = () => {
    if (!audioPlayerRef.current || !isReady) return;
    audioPlayerRef.current.stop();
    setIsPlaying(false);
    
    if (osmdRef.current && osmdRef.current.cursor) {
      osmdRef.current.cursor.reset(); 
    }
  };

  // --- EXPORT CONTROLS ---

  // Triggers the browser's native print dialog, allowing users to "Save as PDF"
  const handleDownloadPDF = () => {
    window.print(); 
  };


  // --- COMPONENT UI (JSX) ---
  return (
    <div className="w-full bg-white rounded-3xl shadow-[0_0_40px_rgba(0,0,0,0.3)] border border-slate-700 overflow-hidden">
      
      {/* 1. THE TOOLBAR */}
      {/* Contains the title and all action buttons (Play, Stop, Speed, Download) */}
      <div className="flex flex-col sm:flex-row items-center justify-between px-8 py-5 bg-slate-100 border-b border-slate-300 gap-4">
        <h3 className="font-extrabold text-slate-800 text-xl flex items-center gap-2">
          🎼 Your Sheet Music
        </h3>
        
        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
          {/* Audio Playback Controls */}
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

            {/* Practice Mode Speed Controller */}
            <div className="flex items-center gap-2 ml-2 bg-white px-3 py-1.5 border border-slate-300 rounded-xl shadow-sm">
              <span className="text-sm font-bold text-slate-500">🏎️ Speed:</span>
              <select
                value={playbackSpeed}
                onChange={handleSpeedChange}
                disabled={!isReady}
                className="bg-transparent text-sm font-bold text-slate-700 outline-none cursor-pointer disabled:text-slate-400 disabled:cursor-not-allowed"
              >
                <option value="0.5">0.5x (Half)</option>
                <option value="0.75">0.75x (Slow)</option>
                <option value="1">1.0x (Normal)</option>
                <option value="1.25">1.25x (Fast)</option>
                <option value="1.5">1.5x (Faster)</option>
                <option value="2">2.0x (Double)</option>
              </select>
            </div>
          </div>

          {/* Export Controls */}
          <button onClick={handleDownloadPDF} className="flex-1 sm:flex-none px-5 py-2 text-sm font-bold text-white bg-blue-600 rounded-xl hover:bg-blue-700 transition-colors shadow-sm flex items-center justify-center gap-2">
            ⬇️ Download PDF
          </button>
        </div>
      </div>

      {/* 2. THE SHEET MUSIC CANVAS */}
      {/* This outer wrapper handles horizontal scrolling if OSMD draws a massive 1200px wide line of music.
        The inner buffer div enforces padding/whitespace and centers the music on large screens. 
      */}
      <div className="w-full overflow-x-auto overflow-y-hidden custom-scrollbar bg-white">
        <div className="min-w-[800px] max-w-7xl mx-auto px-8 md:px-16 py-10">
          
          {/* This is the crucial empty container! We pass its reference (containerRef) 
            to OSMD on line 28, and OSMD physically injects the SVG tags directly into this space.
          */}
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