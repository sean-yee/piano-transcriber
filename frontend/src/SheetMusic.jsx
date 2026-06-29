import React, { useEffect, useRef } from 'react';

export default function SheetMusic({ xmlData }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!xmlData || !containerRef.current) return;

    // Function to initialize and render the sheet music
    const renderSheetMusic = () => {
      if (!window.opensheetmusicdisplay) return;

      // Clear out the container before rendering a new one
      containerRef.current.innerHTML = '';

      const osmd = new window.opensheetmusicdisplay.OpenSheetMusicDisplay(containerRef.current, {
        autoResize: true,
        backend: "svg", // Explicitly use SVG so notes scale smoothly
        drawTitle: false, // Hide the title to keep the UI clean
      });

      osmd.load(xmlData).then(() => {
        // Slightly zoom out to give the measures extra breathing room
        osmd.zoom = 0.9; 
        osmd.render();
      }).catch((error) => {
        console.error("Oops! Something went wrong drawing the sheet music:", error);
      });
    };

    // Load the library dynamically to completely avoid build errors
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

  return (
    <div 
      ref={containerRef} 
      style={{ 
        width: '100%', 
        maxWidth: '100%', // Prevents the div from expanding past boundaries
        minHeight: '400px', 
        marginTop: '20px', 
        backgroundColor: 'white', 
        borderRadius: '8px',
        overflowX: 'auto', // Adds a horizontal scrollbar if the music overflows
        overflowY: 'hidden'
      }} 
    />
  );
}