import React from 'react';

export default function InfoModal({ onClose }) {
  return (
    // Backdrop (darkens the rest of the screen)
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      
      {/* Modal Container */}
      <div className="bg-neutral-900 border border-neutral-700 rounded-3xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto custom-scrollbar">
        
        {/* Header */}
        <div className="sticky top-0 bg-neutral-900/95 backdrop-blur-md border-b border-neutral-800 px-8 py-5 flex items-center justify-between z-10">
          <h2 className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-teal-600">
            About Pianopilot
          </h2>
          <button 
            onClick={onClose}
            className="text-neutral-400 hover:text-white transition-colors"
          >
            <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content (This wrapper has p-8 which aligns everything nicely!) */}
        <div className="p-8 space-y-8 text-neutral-300">
          
          <section className="space-y-3">
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              <span>🚀</span> What is this?
            </h3>
            <p className="leading-relaxed">
              Pianopilot is an AI-powered transcription tool built to bridge the gap between playing by ear and reading sheet music. It uses machine learning to listen to raw piano audio, detect the pitches and rhythms, and automatically generate playable, exportable sheet music.
            </p>
          </section>

          <section className="space-y-3">
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              <span>📖</span> How to get the best results
            </h3>
            <ul className="list-disc pl-5 space-y-2 leading-relaxed text-neutral-400">
              <li><strong className="text-neutral-200">Keep it clean:</strong> The AI works best with solo piano. Background noise, vocals, or heavy drums will confuse the model.</li>
              <li><strong className="text-neutral-200">Watch the pedal:</strong> Heavy sustain pedal blends notes together, making it harder for the AI to tell when a note stops and starts.</li>
              <li><strong className="text-neutral-200">Use the sliders:</strong> Adjust volume sensitivity, note complexity, smoothness, chord complexity, and hand splits to customize the music to your liking!</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              <span>⚠️</span> Current Limitations
            </h3>
            <ul className="list-disc pl-5 space-y-2 leading-relaxed text-neutral-400">
              <li><strong className="text-neutral-200">Wait Times & File Limits:</strong> Audio-to-MIDI machine learning is computationally heavy! Because of this, uploads are currently capped at <strong>2.4MB</strong>, and generations can take up to <strong>15 minutes</strong> to finish processing.</li>
              <li><strong className="text-neutral-200">Complex Rhythms:</strong> The AI snaps notes to a strict grid, meaning it can struggle with extreme tempos, heavy rubato, or swing rhythms.</li>
              <li><strong className="text-neutral-200">Hand Splitting:</strong> The model occasionally guesses the wrong hand placement for middle-C notes (use the Hand Split Bias slider to help correct this).</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              <span>✨</span> The Roadmap
            </h3>
            <p className="leading-relaxed">
              This is just version 1.0! Future updates will include:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-neutral-400">
              <li>Advanced rhythm detection for swing and rubato playing.</li>
              <li>Support for MP4 video uploads.</li>
              <li>Cloud accounts to save your transcription history.</li>
              <li>Better AI separation of left-hand vs. right-hand logic.</li>
            </ul>
          </section>

          {/* I moved this section INSIDE the padded wrapper! */}
          <section className="space-y-3 pt-6 border-t border-neutral-800">
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              <span>💌</span> Feedback & Support
            </h3>
            <p className="leading-relaxed text-neutral-400">
              Find a bug? Have a feature request? I'd love to hear from you! 
              Shoot us an email at:{' '}
              <a 
                href="mailto:pianopilotai@gmail.com" 
                className="text-teal-400 hover:text-teal-300 font-bold underline decoration-teal-400/30 underline-offset-4 transition-colors"
              >
                pianopilotai@gmail.com
              </a>
            </p>
          </section>

        </div> {/* <-- The missing closing tag is safely down here now! */}

        {/* Footer */}
        <div className="border-t border-neutral-800 p-6 flex justify-end">
          <button 
            onClick={onClose}
            className="px-8 py-3 bg-neutral-800 hover:bg-neutral-700 text-white font-bold rounded-xl transition-colors"
          >
            Got it!
          </button>
        </div>

      </div>
    </div>
  );
}