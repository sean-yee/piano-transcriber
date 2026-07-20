🎹 AI-Powered Piano Transcriber

A full-stack machine learning web application that transcribes raw polyphonic piano audio (.mp3, .wav) into dynamic, visually rendered, and playable sheet music.

This project combines deep learning audio transcription with a custom-trained Random Forest classifier to intelligently separate notes into left and right hands, process complex rhythms, and generate accurate sheet music on the fly.

✨ Features

Audio-to-Sheet Music: Upload piano audio and instantly view the generated Grand Staff sheet music.

Intelligent Hand Separation: Uses a custom Machine Learning model trained on 50,000+ notes to dynamically split chords and melodies into Left Hand (Bass Clef) and Right Hand (Treble Clef) parts.

Adaptive Complexity Modes:

Beginner: Quantizes rhythms to clean 8th notes, filtering out fast, micro-timed ghost notes for easy reading.

Advanced: Captures intricate rhythms, syncopation, and fast 16th-note pickups for exact accuracy.

Auto-Detect Key Signature: Utilizes AI harmonic analysis to find the statistically perfect key signature (Scale), reducing unnecessary sharp/flat accidentals.

Interactive UI: A premium, dark-mode frontend built with React and Tailwind CSS v4.

Export Options: Print directly to PDF or download the raw MusicXML file to edit in software like MuseScore or Finale.

🛠️ Tech Stack

Frontend:

React (Vite)

Tailwind CSS v4

OpenSheetMusicDisplay (OSMD) for MusicXML rendering

Backend & Machine Learning:

Python & FastAPI

ByteDance Piano Transcription Model (Deep Learning Audio-to-MIDI)

Scikit-Learn (Random Forest Classifier for hand-splitting)

Librosa & Music21 (Audio signal processing and music theory logic)

Pandas & Joblib

🧠 How It Works (The Pipeline)

Audio Ingestion: The React frontend sends the audio file to the FastAPI backend. Librosa processes the tempo (BPM) and audio waves.

Deep Learning Transcription: The ByteDance neural network maps the audio frequencies to raw MIDI pitches and timestamps.

ML Hand Splitting: Our custom hand_classifier.pkl evaluates every single note's pitch, duration, and distance from concurrent chords to predict whether it was played by the left or right hand.

Algorithmic Sequencer: Based on the user's selected mode (Beginner/Advanced), a custom collision-resolver nudges mathematically overlapping notes into clean grid slots (8th or 16th notes).

Sheet Music Generation: Music21 calculates the Key Signature, applies dynamic Clefs (e.g., Treble 8va or Bass 8vb if the notes go too high/low), and packages it all into a MusicXML string.

Frontend Rendering: OpenSheetMusicDisplay renders the XML string into beautiful SVG sheet music right in the browser!

🚀 Local Setup & Installation

To run this project locally, you will need two terminal windows open—one for the Python backend and one for the React frontend.

1. Backend Setup (FastAPI)

Navigate to the root directory (where main.py is located):

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install backend dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload


The backend will run at http://localhost:8000

2. Frontend Setup (React/Vite)

Open a second terminal and navigate to your frontend folder:

cd frontend

# Install Node modules
npm install

# Start the frontend development server
npm run dev


The frontend will run at http://localhost:5173 (or similar, check your terminal).

🔮 Future Improvements

Add support for more instruments beyond solo piano.

Implement a live-playback feature that highlights notes on the sheet music as the original audio plays.

Allow users to manually adjust the tempo or time signature before generating.

📄 License

This project is open-source and available under the MIT License. Feel free to fork, modify, and improve it!
