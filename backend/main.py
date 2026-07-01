import os
import copy
import numpy as np
import pandas as pd
import joblib
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from basic_pitch.inference import predict
from music21 import stream, clef, note, chord, instrument
from sklearn.ensemble import RandomForestClassifier

app = FastAPI()

# Allow your React frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- THE UPGRADED CLASSIFIER (Loading the .pkl file) ---
print("Loading Machine Learning model...")
try:
    # Instead of training from scratch, we instantly load the "saved brain"
    hand_classifier = joblib.load('hand_classifier.pkl')
    print("✅ Successfully loaded pre-trained hand_classifier.pkl")
except Exception as e:
    print(f"❌ Error loading model: {e}. Falling back to empty model.")
    # Fallback to prevent server crash if the .pkl file is missing
    hand_classifier = RandomForestClassifier()

@app.get("/")
def home():
    return {"message": "Piano Transcriber API is running!"}

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # 1. Save uploaded file temporarily to process it
    temp_audio_path = f"temp_{file.filename}"
    with open(temp_audio_path, "wb") as f:
        f.write(await file.read())

    try:
        # 2. Run basic-pitch AI to extract raw MIDI notes from the audio
        print(f"Predicting MIDI for {file.filename}...")
        model_output, midi_data, note_events = predict(temp_audio_path)
        
        # 3. Initialize Music21 Score (Sheet Music)
        score = stream.Score()
        
        part_treble = stream.Part()
        part_treble.insert(0, instrument.Piano())
        part_treble.insert(0, clef.TrebleClef())
        
        part_bass = stream.Part()
        part_bass.insert(0, instrument.Piano())
        part_bass.insert(0, clef.BassClef())

        if not note_events:
            return {"xml_data": ""}

        # 4. Process each note and predict which hand played it
        for n_event in note_events:
            pitch = n_event[2]
            duration = n_event[1] - n_event[0]
            
            # Feature extraction to match our Random Forest training columns
            # (In a highly advanced version, you would calculate concurrent notes dynamically)
            concurrent_notes = 1 
            dist_to_highest = 0
            dist_to_lowest = 0
            
            features = [[pitch, duration, concurrent_notes, dist_to_highest, dist_to_lowest]]
            
            try:
                # Predict: 0 = Left Hand (Bass), 1 = Right Hand (Treble)
                hand_label = hand_classifier.predict(features)[0]
            except:
                # Basic fallback if model isn't fully trained yet
                hand_label = 1 if pitch >= 60 else 0

            # Create the note
            new_note = note.Note(pitch)
            new_note.quarterLength = duration
            
            # Assign to the correct staff based on the ML prediction
            if hand_label == 1:
                part_treble.insert(n_event[0], new_note)
            else:
                part_bass.insert(n_event[0], new_note)
                
        # Combine parts into the final score
        score.insert(0, part_treble)
        score.insert(0, part_bass)
        
        # 5. Export to MusicXML string to send back to React
        xml_file_path = score.write('musicxml')
        with open(xml_file_path, 'r') as f:
            xml_string = f.read()
            
        # Clean up the generated xml file
        if os.path.exists(xml_file_path):
            os.remove(xml_file_path)
            
        return {"xml_data": xml_string}
        
    finally:
        # Always clean up the temporary audio file
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)