import os
import base64
import copy
import numpy as np
import joblib
import traceback  
import librosa    
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from piano_transcription_inference import PianoTranscription, sample_rate
from music21 import converter, stream, clef, instrument, note, chord, tempo, meter, key as m21_key
from sklearn.ensemble import RandomForestClassifier

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading ByteDance Piano Transcription model (this may take a moment to download weights on first run)...")
try:
    transcriptor = PianoTranscription(device='cpu') 
    print("✅ Successfully loaded ByteDance Piano Model")
except Exception as e:
    print(f"❌ Error loading ByteDance model: {e}")

print("Loading Machine Learning model...")
try:
    hand_classifier = joblib.load('hand_classifier.pkl')
    print("✅ Successfully loaded pre-trained hand_classifier.pkl")
except Exception as e:
    print(f"❌ Error loading model: {e}. Falling back to empty model.")
    hand_classifier = RandomForestClassifier()

@app.get("/")
def home():
    return {"message": "Piano Transcriber API is running!"}

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...), 
    mode: str = Form("advanced"),
    key_signature: str = Form("auto")
):
    temp_file_path = f"temp_{file.filename}"
    base_name, _ = os.path.splitext(temp_file_path)
    temp_midi_path = f"{base_name}.mid"
    temp_xml_path = f"{base_name}.xml"
    
    with open(temp_file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        audio, _ = librosa.load(temp_file_path, sr=sample_rate, mono=True)
        
        print("Detecting BPM...")
        detected_tempo, _ = librosa.beat.beat_track(y=audio, sr=sample_rate)
        detected_bpm = float(detected_tempo[0]) if isinstance(detected_tempo, np.ndarray) else float(detected_tempo)
        detected_bpm = round(detected_bpm) 
        if detected_bpm == 0:
            detected_bpm = 120
        print(f"Detected Tempo: {detected_bpm} BPM")
        print(f"Transcription Mode: {mode.upper()}")
        print(f"Requested Key Signature: {key_signature.upper()}")

        transcriptor.transcribe(audio, temp_midi_path)
        
        parsed_score = converter.parse(temp_midi_path)
        ai_part = parsed_score.parts[0]
        
        scale_factor = detected_bpm / 120.0
        ai_part.augmentOrDiminish(scale_factor, inPlace=True)
        
        flat_stream = ai_part.flatten()
        
        if len(flat_stream.notes) > 0:
            first_note_offset = min(n.offset for n in flat_stream.notes)
            for el in flat_stream.notes:
                el.offset -= first_note_offset
        
        for el in list(flat_stream.getElementsByClass(['TimeSignature', 'MetronomeMark', 'KeySignature'])):
            flat_stream.remove(el)
            
        max_note_length = 8.0 
        elements_to_remove = []
        for el in flat_stream.notes:
            if el.quarterLength < 0.125:
                elements_to_remove.append(el)
            elif el.quarterLength > max_note_length:
                el.quarterLength = max_note_length
        for el in elements_to_remove:
            flat_stream.remove(el)
            
        flat_right = stream.Part()
        flat_left = stream.Part()
        
        # Insert Tempo and Time Signature
        flat_right.insert(0, tempo.MetronomeMark(number=detected_bpm))
        flat_right.insert(0, meter.TimeSignature('4/4'))
        flat_left.insert(0, tempo.MetronomeMark(number=detected_bpm))
        flat_left.insert(0, meter.TimeSignature('4/4'))

        # --- AUTO-DETECT OR APPLY CUSTOM KEY SIGNATURE ---
        if key_signature.lower() == 'auto':
            # Let music21's AI analyze the notes and calculate the statistically most likely key!
            print("Auto-detecting the perfect key signature...")
            best_key = flat_stream.analyze('key')
            print(f"Detected Key: {best_key}")
            flat_right.insert(0, best_key)
            flat_left.insert(0, best_key)
        else:
            # Apply the user's explicit choice
            user_key = m21_key.Key(key_signature)
            flat_right.insert(0, user_key)
            flat_left.insert(0, user_key)
        
        for el in flat_stream.notes:
            concurrent = flat_stream.getElementsByOffset(el.offset, mustBeginInSpan=False, mustFinishInSpan=False)
            active_pitches = []
            for c in concurrent.notes:
                if isinstance(c, note.Note):
                    active_pitches.append(c.pitch.midi)
                elif isinstance(c, chord.Chord):
                    active_pitches.extend([p.midi for p in c.pitches])
                    
            if not active_pitches:
                continue
                
            c_count = len(active_pitches)
            max_p = max(active_pitches)
            min_p = min(active_pitches)
            
            if isinstance(el, note.Note):
                if c_count == 1 and el.pitch.midi > 48:
                    flat_right.insert(el.offset, copy.deepcopy(el))
                else:
                    dist_high = max_p - el.pitch.midi
                    dist_low = el.pitch.midi - min_p
                    features = np.array([[el.pitch.midi, float(el.quarterLength), c_count, dist_high, dist_low]])
                    
                    if hand_classifier.predict(features)[0] == 1:
                        flat_right.insert(el.offset, copy.deepcopy(el))
                    else:
                        flat_left.insert(el.offset, copy.deepcopy(el))
                    
            elif isinstance(el, chord.Chord):
                r_pitches = []
                l_pitches = []
                for p in el.pitches:
                    dist_high = max_p - p.midi
                    dist_low = p.midi - min_p
                    features = np.array([[p.midi, float(el.quarterLength), c_count, dist_high, dist_low]])
                    if hand_classifier.predict(features)[0] == 1:
                        r_pitches.append(p)
                    else:
                        l_pitches.append(p)
                        
                if r_pitches:
                    c_right = chord.Chord(r_pitches)
                    c_right.quarterLength = el.quarterLength
                    flat_right.insert(el.offset, c_right)
                if l_pitches:
                    c_left = chord.Chord(l_pitches)
                    c_left.quarterLength = el.quarterLength
                    flat_left.insert(el.offset, c_left)

        def sequence_hand(hand_stream):
            if mode.lower() == "beginner":
                grid_resolution = 2.0  
                collision_push = 0.5   
                standard_durations = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
                fallback_dur = 0.5
            else:
                grid_resolution = 4.0  
                collision_push = 0.25  
                standard_durations = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
                fallback_dur = 0.25

            offset_groups = {}
            raw_notes = list(hand_stream.notes)
            raw_notes.sort(key=lambda x: x.offset)
            
            for el in raw_notes:
                clean_off = round(float(el.offset) * grid_resolution) / grid_resolution
                
                while clean_off in offset_groups:
                    existing_el = offset_groups[clean_off][0]
                    if abs(float(el.offset) - float(existing_el.offset)) < 0.15:
                        break 
                    else:
                        clean_off += collision_push 
                        
                if clean_off not in offset_groups:
                    offset_groups[clean_off] = []
                offset_groups[clean_off].append(el)
                hand_stream.remove(el) 
                
            sorted_offsets = sorted(list(offset_groups.keys()))
            previous_pitches = []
            
            for i in range(len(sorted_offsets)):
                current_offset = sorted_offsets[i]
                elements = offset_groups[current_offset]
                
                pitches = []
                for el in elements:
                    if isinstance(el, note.Note):
                        pitches.append(el.pitch)
                    elif isinstance(el, chord.Chord):
                        pitches.extend(el.pitches)
                
                unique_pitches = list(set(pitches))
                unique_pitches.sort(key=lambda p: p.midi)
                
                if len(unique_pitches) > 1 and previous_pitches:
                    filtered_pitches = [p for p in unique_pitches if p.midi not in previous_pitches]
                    if len(filtered_pitches) > 0:
                        unique_pitches = filtered_pitches
                        
                previous_pitches = [p.midi for p in unique_pitches]
                
                if len(unique_pitches) == 1:
                    new_el = note.Note(unique_pitches[0])
                else:
                    new_el = chord.Chord(unique_pitches)
                    
                requested_dur = max(float(e.quarterLength) for e in elements)
                
                absolute_max = requested_dur
                if i < len(sorted_offsets) - 1:
                    max_allowed_by_next = sorted_offsets[i + 1] - current_offset
                    absolute_max = min(absolute_max, max_allowed_by_next)
                
                valid_lengths = [d for d in standard_durations if d <= absolute_max + 0.01]
                
                if not valid_lengths:
                    final_dur = fallback_dur 
                else:
                    final_dur = min(valid_lengths, key=lambda x: abs(x - requested_dur))
                
                new_el.quarterLength = final_dur
                hand_stream.insert(current_offset, new_el)

        sequence_hand(flat_right)
        sequence_hand(flat_left)

        right_measured = flat_right.makeMeasures()
        left_measured = flat_left.makeMeasures()
        
        right_clean = right_measured.chordify()
        left_clean = left_measured.chordify()
        
        right_hand = stream.Part()
        right_hand.id = 'RightHand'
        rh_inst = instrument.Piano()
        rh_inst.instrumentName = 'Piano'
        rh_inst.instrumentAbbreviation = ' ' 
        right_hand.insert(0, rh_inst)
        right_hand.partName = 'Piano'
        right_hand.partAbbreviation = ' '
        right_hand.insert(0, clef.TrebleClef())
        
        left_hand = stream.Part()
        left_hand.id = 'LeftHand'
        lh_inst = instrument.Piano()
        lh_inst.instrumentName = ' ' 
        lh_inst.instrumentAbbreviation = ' '
        left_hand.insert(0, lh_inst)
        left_hand.partName = ' '
        left_hand.partAbbreviation = ' '
        left_hand.insert(0, clef.BassClef())
        
        current_right_clef = 'treble'
        for m in right_clean.getElementsByClass('Measure'):
            m_new = copy.deepcopy(m)
            for c in m_new.getElementsByClass('Clef'):
                m_new.remove(c)
                
            pitches = [p.midi for n in m_new.notes for p in n.pitches]
            if pitches:
                avg_r = sum(pitches) / len(pitches)
                if avg_r < 50 and current_right_clef != 'bass':
                    m_new.insert(0, clef.BassClef())
                    current_right_clef = 'bass'
                elif avg_r > 84 and current_right_clef != 'treble8va':  
                    m_new.insert(0, clef.Treble8vaClef())
                    current_right_clef = 'treble8va'
                elif 50 <= avg_r <= 84 and current_right_clef != 'treble':
                    m_new.insert(0, clef.TrebleClef())
                    current_right_clef = 'treble'
            m_new.makeRests(fillGaps=True, inPlace=True)
            right_hand.append(m_new)

        current_left_clef = 'bass'
        for m in left_clean.getElementsByClass('Measure'):
            m_new = copy.deepcopy(m)
            for c in m_new.getElementsByClass('Clef'):
                m_new.remove(c)
                
            pitches = [p.midi for n in m_new.notes for p in n.pitches]
            if pitches:
                avg_l = sum(pitches) / len(pitches)
                if avg_l > 65 and current_left_clef != 'treble':
                    m_new.insert(0, clef.TrebleClef())
                    current_left_clef = 'treble'
                elif avg_l < 36 and current_left_clef != 'bass8vb':  
                    m_new.insert(0, clef.Bass8vbClef())
                    current_left_clef = 'bass8vb'
                elif 36 <= avg_l <= 65 and current_left_clef != 'bass':
                    m_new.insert(0, clef.BassClef())
                    current_left_clef = 'bass'
            m_new.makeRests(fillGaps=True, inPlace=True)
            left_hand.append(m_new)
            
        grand_staff = stream.Score()
        grand_staff.insert(0, right_hand)
        grand_staff.insert(0, left_hand)
        
        grand_staff.write("musicxml", fp=temp_xml_path, makeNotation=True)
        
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
        print("\n❌ TRANSCRIPTION ERROR:")
        traceback.print_exc() 
        error_msg = str(e)
        if not error_msg: 
            error_msg = repr(e) 
        return {"status": "error", "message": error_msg}
        
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_midi_path):
            os.remove(temp_midi_path)
        if os.path.exists(temp_xml_path):
            os.remove(temp_xml_path)