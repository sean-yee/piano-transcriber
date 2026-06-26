import os
import base64
import copy
import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from basic_pitch.inference import predict
from music21 import converter, stream, clef, instrument, note, chord
from sklearn.ensemble import RandomForestClassifier

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- THE UPGRADED CLASSIFIER (Feature Engineering) ---
def train_hand_classifier():
    """
    Features: [Pitch, Duration, Concurrent_Notes, Dist_To_Highest, Dist_To_Lowest]
    Labels: 0 (Left Hand), 1 (Right Hand)
    """
    X_train = np.array([
        # Scenario 1: Single notes (standard playing)
        [40, 1.0, 1, 0, 0],  # Low note alone -> Left
        [80, 1.0, 1, 0, 0],  # High note alone -> Right
        
        # Scenario 2: Standard 3-note chord (around Middle C)
        [60, 1.0, 3, 7, 0],  # Bottom of chord -> Left
        [64, 1.0, 3, 3, 4],  # Middle of chord -> Right
        [67, 1.0, 3, 0, 7],  # Top of chord -> Right
        
        # Scenario 3: THE EDGE CASE (Both hands playing very high)
        # 6 notes playing concurrently between pitch 75 and 87
        [75, 1.0, 6, 12, 0], # Absolute lowest of the cluster -> Left
        [79, 1.0, 6, 8, 4],  # Second lowest -> Left
        [81, 1.0, 6, 6, 6],  # Middle-low -> Left
        [84, 1.0, 6, 3, 9],  # Middle-high -> Right
        [86, 1.0, 6, 1, 11], # Upper -> Right
        [87, 1.0, 6, 0, 12]  # Absolute highest -> Right
    ])
    
    y_train = np.array([0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1])
    
    clf = RandomForestClassifier(n_estimators=25, random_state=42)
    clf.fit(X_train, y_train)
    return clf

hand_classifier = train_hand_classifier()

@app.get("/")
def home():
    return {"message": "Piano Transcriber API is running!"}

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        model_output, midi_data, note_events = predict(
            temp_file_path,
            minimum_note_length=120.0,
            multiple_pitch_bends=False,
            onset_threshold=0.6,
            frame_threshold=0.45 
        )
        
        temp_midi_path = temp_file_path.replace(os.path.splitext(temp_file_path)[1], ".mid")
        midi_data.write(temp_midi_path)
        
        parsed_score = converter.parse(
            temp_midi_path, 
            quantizePost=True, 
            quarterLengthDivisors=(4,)
        )
        
        ai_part = parsed_score.parts[0]
        
        # --- NOTE STITCHING FIX ---
        flat_elements = ai_part.flatten().notes.stream()
        for i in range(len(flat_elements) - 1):
            current_el = flat_elements[i]
            next_el = flat_elements[i + 1]
            current_end_time = current_el.offset + current_el.quarterLength
            gap = next_el.offset - current_end_time
            if 0 < gap <= 0.25:
                current_el.quarterLength += gap
                
        right_hand = stream.Part()
        right_hand.id = 'RightHand'
        right_hand.insert(0, instrument.Piano())
        right_hand.insert(0, clef.TrebleClef())
        
        left_hand = stream.Part()
        left_hand.id = 'LeftHand'
        left_hand.insert(0, instrument.Piano())
        left_hand.partName = ''
        left_hand.partAbbreviation = ''
        left_hand.insert(0, clef.BassClef())
        
        # --- NEW: Track current clefs for dynamic octave/clef changes ---
        current_right_clef = 'treble'
        current_left_clef = 'bass'
        
        # --- THE CONTEXTUAL ML SPLIT ---
        for m in ai_part.getElementsByClass('Measure'):
            m_right = stream.Measure(number=m.number)
            m_left = stream.Measure(number=m.number)
            
            r_pitches = []
            l_pitches = []
            
            for el in m.elements:
                if el.classes[0] in ['TimeSignature', 'KeySignature']:
                    m_right.insert(el.offset, copy.deepcopy(el))
                    m_left.insert(el.offset, copy.deepcopy(el))

            flat_measure_notes = m.flatten().notes
            
            for el in flat_measure_notes:
                # 1. Freeze time and find all notes playing at this exact moment
                concurrent = flat_measure_notes.getElementsByOffset(
                    el.offset, 
                    mustBeginInSpan=False, 
                    mustFinishInSpan=False
                )
                
                # 2. Extract all active pitches
                active_pitches = []
                for c in concurrent:
                    if isinstance(c, note.Note):
                        active_pitches.append(c.pitch.midi)
                    elif isinstance(c, chord.Chord):
                        active_pitches.extend([p.midi for p in c.pitches])
                        
                if not active_pitches:
                    continue
                
                # 3. Calculate Contextual Metrics
                max_p = max(active_pitches)
                min_p = min(active_pitches)
                c_count = len(active_pitches)
                
                if isinstance(el, note.Note):
                    dist_high = max_p - el.pitch.midi
                    dist_low = el.pitch.midi - min_p
                    
                    features = np.array([[el.pitch.midi, el.quarterLength, c_count, dist_high, dist_low]])
                    prediction = hand_classifier.predict(features)[0]
                    
                    if prediction == 1:
                        m_right.insert(el.offset, copy.deepcopy(el))
                        r_pitches.append(el.pitch.midi)
                    else:
                        m_left.insert(el.offset, copy.deepcopy(el))
                        l_pitches.append(el.pitch.midi)
                        
                elif isinstance(el, chord.Chord):
                    right_chord_pitches = []
                    left_chord_pitches = []
                    
                    for p in el.pitches:
                        dist_high = max_p - p.midi
                        dist_low = p.midi - min_p
                        features = np.array([[p.midi, el.quarterLength, c_count, dist_high, dist_low]])
                        
                        if hand_classifier.predict(features)[0] == 1:
                            right_chord_pitches.append(p)
                            r_pitches.append(p.midi)
                        else:
                            left_chord_pitches.append(p)
                            l_pitches.append(p.midi)
                    
                    if right_chord_pitches:
                        c_right = chord.Chord(right_chord_pitches)
                        c_right.quarterLength = el.quarterLength
                        m_right.insert(el.offset, c_right)
                    if left_chord_pitches:
                        c_left = chord.Chord(left_chord_pitches)
                        c_left.quarterLength = el.quarterLength
                        m_left.insert(el.offset, c_left)
            
            # --- NEW: Dynamic Clef & Octave Logic ---
            if r_pitches:
                avg_r = sum(r_pitches) / len(r_pitches)
                if avg_r < 50 and current_right_clef != 'bass':
                    m_right.insert(0, clef.BassClef())
                    current_right_clef = 'bass'
                elif avg_r > 84 and current_right_clef != 'treble8va':  # C6 and above
                    m_right.insert(0, clef.Treble8vaClef())
                    current_right_clef = 'treble8va'
                elif 50 <= avg_r <= 84 and current_right_clef != 'treble':
                    m_right.insert(0, clef.TrebleClef())
                    current_right_clef = 'treble'

            if l_pitches:
                avg_l = sum(l_pitches) / len(l_pitches)
                if avg_l > 65 and current_left_clef != 'treble':
                    m_left.insert(0, clef.TrebleClef())
                    current_left_clef = 'treble'
                elif avg_l < 36 and current_left_clef != 'bass8vb':  # C2 and below
                    m_left.insert(0, clef.Bass8vbClef())
                    current_left_clef = 'bass8vb'
                elif 36 <= avg_l <= 65 and current_left_clef != 'bass':
                    m_left.insert(0, clef.BassClef())
                    current_left_clef = 'bass'
            
            m_right.makeRests(fillGaps=True, inPlace=True)
            m_left.makeRests(fillGaps=True, inPlace=True)
            
            right_hand.append(m_right)
            left_hand.append(m_left)
            
        grand_staff = stream.Score()
        grand_staff.insert(0, right_hand)
        grand_staff.insert(0, left_hand)
        
        temp_xml_path = temp_file_path.replace(os.path.splitext(temp_file_path)[1], ".xml")
        grand_staff.write("musicxml", temp_xml_path)
        
        with open(temp_xml_path, "r") as f:
            xml_string = f.read()
            
        with open(temp_midi_path, "rb") as f:
            midi_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        return {
            "status": "success",
            "message": f"Successfully transcribed {file.filename}",
            "xml_data": xml_string,
            "midi_data": midi_base64 
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
    finally:
        for ext in ["", ".mid", ".xml"]:
            path = temp_file_path.replace(os.path.splitext(temp_file_path)[1], ext)
            if os.path.exists(path):
                os.remove(path)