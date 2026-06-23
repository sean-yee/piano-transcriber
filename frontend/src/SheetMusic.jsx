import React, { useEffect, useRef } from 'react';
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';

export default function SheetMusic({ xmlData }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!xmlData || !containerRef.current) return;

    // Initialize the rendering engine inside our div
    const osmd = new OpenSheetMusicDisplay(containerRef.current, {
      autoResize: true,
      drawTitle: false, // We hide the title to keep the UI clean
    });

    // Load the XML string from our backend and draw it!
    osmd.load(xmlData).then(() => {
      osmd.render();
    });

    // Cleanup function so we don't draw multiple copies on top of each other
    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, [xmlData]);

  return <div ref={containerRef} style={{ width: '100%', minHeight: '400px', marginTop: '20px', backgroundColor: 'white', borderRadius: '8px' }} />;
}