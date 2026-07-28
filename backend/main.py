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

# --- APP INITIALIZATION ---
# Create the FastAPI server instance
app = FastAPI()

# Configure CORS so your React frontend (running on a different port) is allowed to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODEL LOADING ---
# 1. The Core AI: ByteDance's Piano Transcription model (converts audio to raw MIDI)
print("Loading ByteDance Piano Transcription model (this may take a moment to download weights on first run)...")
try:
    transcriptor = PianoTranscription(device='cpu') 
    print("✅ Successfully loaded ByteDance Piano Model")
except Exception as e:
    print(f"❌ Error loading ByteDance model: {e}")

# 2. The Hand Splitter: Your custom Machine Learning model that guesses if a note is Left or Right hand
print("Loading Machine Learning model...")
try:
    hand_classifier = joblib.load('hand_classifier.pkl')
    print("✅ Successfully loaded pre-trained hand_classifier.pkl")
except Exception as e:
    print(f"❌ Error loading model: {e}. Falling back to empty model.")
    hand_classifier = RandomForestClassifier()

# --- API ENDPOINTS ---
# A simple health check endpoint to verify the server is running
@app.get("/")
def home():
    return {"message": "Piano Transcriber API is running!"}

# The main engine: This catches the audio file and slider values from the React frontend
@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...), 
    complexity: int = Form(2),
    key_signature: str = Form("auto"),
    volume_threshold: int = Form(30),
    polyphony_limit: int = Form(6),
    smoothness: int = Form(50),
    hand_bias: int = Form(0)
):
    # Set up temporary file paths to store the incoming audio and the generated data
    temp_file_path = f"temp_{file.filename}"
    base_name, _ = os.path.splitext(temp_file_path)
    temp_midi_path = f"{base_name}.mid"
    temp_xml_path = f"{base_name}.xml"
    
    # Save the uploaded audio file to the server's hard drive
    with open(temp_file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        # --- AUDIO PROCESSING ---
        # Load the audio file into memory using librosa so we can analyze it
        audio, _ = librosa.load(temp_file_path, sr=sample_rate, mono=True)
        
        # Calculate the actual tempo (BPM) of the song so we can draw accurate sheet music measures
        print("Detecting BPM...")
        detected_tempo, _ = librosa.beat.beat_track(y=audio, sr=sample_rate)
        detected_bpm = float(detected_tempo[0]) if isinstance(detected_tempo, np.ndarray) else float(detected_tempo)
        detected_bpm = round(detected_bpm) 
        if detected_bpm == 0:
            detected_bpm = 120 # Fallback in case librosa fails to detect a beat
            
        print(f"Detected Tempo: {detected_bpm} BPM")
        print(f"Transcription Mode: {complexity}")
        print(f"Requested Key Signature: {key_signature.upper()}")

        # Run the ByteDance AI to convert the audio array into a raw MIDI file
        transcriptor.transcribe(audio, temp_midi_path)
        
        # --- MUSIC21 PARSING ---
        # Load the raw MIDI file into music21, which allows us to manipulate the notes programmatically
        parsed_score = converter.parse(temp_midi_path)
        ai_part = parsed_score.parts[0]
        
        # Scale the lengths of all the notes to match our detected BPM
        scale_factor = detected_bpm / 120.0
        ai_part.augmentOrDiminish(scale_factor, inPlace=True)
        
        # Flatten the score (remove all measures/bars) so it is just one continuous timeline of notes
        flat_stream = ai_part.flatten()
        
        # Shift the entire song so the very first note starts exactly at timestamp 0.0
        if len(flat_stream.notes) > 0:
            first_note_offset = min(n.offset for n in flat_stream.notes)
            for el in flat_stream.notes:
                el.offset -= first_note_offset
        
        # Strip out any junk formatting the AI might have accidentally added
        for el in list(flat_stream.getElementsByClass(['TimeSignature', 'MetronomeMark', 'KeySignature'])):
            flat_stream.remove(el)
            
        # --- FILTER 1: GHOST NOTES & MAX LENGTH ---
        max_note_length = 8.0 
        elements_to_remove = []
        for el in flat_stream.notes:
            note_velocity = el.volume.velocity if (hasattr(el, 'volume') and el.volume.velocity is not None) else 64
            
            # If a note is quieter than the user's slider OR ridiculously short, tag it for deletion
            if note_velocity < volume_threshold or el.quarterLength < 0.0625:
                elements_to_remove.append(el)
            # Cap endlessly ringing notes to a maximum of 2 whole notes (8.0 beats)
            elif el.quarterLength > max_note_length:
                el.quarterLength = max_note_length
                
        # Actually delete the tagged ghost notes
        for el in elements_to_remove:
            flat_stream.remove(el)

        # --- FILTER 2: THE CHORD SIMPLIFIER (POLYPHONY) ---
        # Search for chords that have more notes playing at once than the user's slider allows
        for el in list(flat_stream.notes):
            if getattr(el, 'isChord', False) and len(el.pitches) > polyphony_limit:
                
                # Sort pitches from bottom (bass) to top (melody)
                sorted_pitches = sorted(el.pitches, key=lambda p: p.midi)
                
                if polyphony_limit == 1:
                    # If limited to 1 note, nuke everything except the highest melody note
                    kept_pitches = [sorted_pitches[-1]]
                else:
                    # Otherwise, keep the crucial bass note, the crucial melody note, and delete the middle overtones
                    kept_pitches = [sorted_pitches[0]] + sorted_pitches[-(polyphony_limit-1):]
                
                # Rebuild the simplified note/chord
                if len(kept_pitches) == 1:
                    new_el = note.Note(kept_pitches[0])
                else:
                    new_el = chord.Chord(kept_pitches)
                    
                # Copy over the timing and volume data from the original giant chord
                new_el.quarterLength = el.quarterLength
                new_el.offset = el.offset
                if hasattr(el, 'volume') and el.volume.velocity is not None:
                    new_el.volume.velocity = el.volume.velocity
                
                # Swap the new clean chord into the timeline, destroying the old messy one
                flat_stream.replace(el, new_el)

        # --- PREPARE HANDS ---
        # Create two empty buckets: one for the Right Hand, one for the Left
        flat_right = stream.Part()
        flat_left = stream.Part()
        
        # Inject the BPM and Time Signature into the beginning of both hands
        flat_right.insert(0, tempo.MetronomeMark(number=detected_bpm))
        flat_right.insert(0, meter.TimeSignature('4/4'))
        flat_left.insert(0, tempo.MetronomeMark(number=detected_bpm))
        flat_left.insert(0, meter.TimeSignature('4/4'))

        # --- KEY SIGNATURE ---
        if key_signature.lower() == 'auto':
            # Let music21 analyze the pitches and mathematically guess the key (e.g., C Major)
            print("Auto-detecting the perfect key signature...")
            best_key = flat_stream.analyze('key')
            print(f"Detected Key: {best_key}")
            flat_right.insert(0, best_key)
            flat_left.insert(0, best_key)
        else:
            # Force the specific key the user chose in the UI dropdown
            user_key = m21_key.Key(key_signature)
            flat_right.insert(0, user_key)
            flat_left.insert(0, user_key)
        
        # --- FILTER 3: MACHINE LEARNING HAND SPLITTER ---
        # Loop through every note and use our Random Forest model to guess which hand played it
        for el in flat_stream.notes:
            # Gather contextual data (how many notes are playing right now, what is the highest/lowest pitch)
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
            
            # Convert the user's Bias Slider into a math threshold
            # E.g., +50 bias lowers the threshold so the Right Hand steals more notes
            rh_threshold = 0.5 - (hand_bias / 100.0)

            # If it's a single note...
            if isinstance(el, note.Note):
                # Basic sanity check: If it's the only note playing and it's high up, just give it to the Right Hand
                if c_count == 1 and el.pitch.midi > 48:
                    flat_right.insert(el.offset, copy.deepcopy(el))
                else:
                    # Feed the contextual data into the ML Model
                    dist_high = max_p - el.pitch.midi
                    dist_low = el.pitch.midi - min_p
                    features = np.array([[el.pitch.midi, float(el.quarterLength), c_count, dist_high, dist_low]])
                    
                    # Ask the ML Model: "How confident are you this is a Right Hand note?"
                    probs = hand_classifier.predict_proba(features)[0]
                    rh_confidence = probs[1] 
                    
                    # Apply our user-adjusted threshold to the AI's confidence
                    if rh_confidence >= rh_threshold:
                        flat_right.insert(el.offset, copy.deepcopy(el))
                    else:
                        flat_left.insert(el.offset, copy.deepcopy(el))
                    
            # If it's a chord...
            elif isinstance(el, chord.Chord):
                r_pitches = []
                l_pitches = []
                # We have to split the chord apart and ask the ML model about EVERY single pitch inside it
                for p in el.pitches:
                    dist_high = max_p - p.midi
                    dist_low = p.midi - min_p
                    features = np.array([[p.midi, float(el.quarterLength), c_count, dist_high, dist_low]])
                    
                    probs = hand_classifier.predict_proba(features)[0]
                    rh_confidence = probs[1]
                    
                    if rh_confidence >= rh_threshold:
                        r_pitches.append(p)
                    else:
                        l_pitches.append(p)
                        
                # Reassemble the pieces into two new chords, one for each hand
                if r_pitches:
                    c_right = chord.Chord(r_pitches)
                    c_right.quarterLength = el.quarterLength
                    flat_right.insert(el.offset, c_right)
                if l_pitches:
                    c_left = chord.Chord(l_pitches)
                    c_left.quarterLength = el.quarterLength
                    flat_left.insert(el.offset, c_left)

        # --- FILTER 4: QUANTIZATION & SMOOTHING (The Core Sequencer) ---
        # This function takes a raw, messy AI timeline and mathematically snaps the notes to a readable grid
        def sequence_hand(hand_stream):
            
            # Map the user's Complexity Slider to actual musical math arrays
            if complexity == 4: # EXACT: No snapping, allows chaotic 64th notes
                grid_resolution = 16.0  
                collision_push = 0.0625  
                standard_durations = [0.0625, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
                fallback_dur = 0.0625
            elif complexity == 1: # BEGINNER: Forces very clean, slow 8th notes
                grid_resolution = 2.0  
                collision_push = 0.5   
                standard_durations = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
                fallback_dur = 0.5
            elif complexity == 2: # INTERMEDIATE: Standard 16th note grid
                grid_resolution = 4.0  
                collision_push = 0.25  
                standard_durations = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
                fallback_dur = 0.25
            else: # ADVANCED: Allows fast 32nd notes and trills
                grid_resolution = 8.0  
                collision_push = 0.125  
                standard_durations = [0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
                fallback_dur = 0.125

            # Group notes that happen at roughly the same time into a single grid slot
            offset_groups = {}
            raw_notes = list(hand_stream.notes)
            raw_notes.sort(key=lambda x: x.offset)
            
            for el in raw_notes:
                # Mathematically snap the note's weird decimal start time (e.g., 1.033) to a clean grid line (1.0)
                clean_off = round(float(el.offset) * grid_resolution) / grid_resolution
                
                # Prevent visual overlaps: If the slot is taken, nudge the note forward slightly
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
                
            # Now actually draw the snapped notes onto the timeline
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
                
                # Remove duplicate pitches within the same chord
                unique_pitches = list(set(pitches))
                unique_pitches.sort(key=lambda p: p.midi)
                
                # Clean up repeated trills
                if len(unique_pitches) > 1 and previous_pitches:
                    filtered_pitches = [p for p in unique_pitches if p.midi not in previous_pitches]
                    if len(filtered_pitches) > 0:
                        unique_pitches = filtered_pitches
                        
                previous_pitches = [p.midi for p in unique_pitches]
                
                # Create the final container object
                if len(unique_pitches) == 1:
                    new_el = note.Note(unique_pitches[0])
                else:
                    new_el = chord.Chord(unique_pitches)
                    
                # Snap the note's DURATION (length) to a readable value
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

            # --- FILTER 5: LEGATO SMOOTHNESS (REST ELIMINATOR) ---
            if smoothness > 0:
                # Convert the 0-100 UI slider into a max stretching tolerance
                max_gap_to_fill = (smoothness / 100.0) * 0.5 
                
                final_notes = list(hand_stream.notes)
                final_notes.sort(key=lambda x: x.offset)
                
                for i in range(len(final_notes) - 1):
                    current_note = final_notes[i]
                    next_note = final_notes[i+1]
                    
                    # Measure the silence between the current note ending and the next note starting
                    current_end = current_note.offset + current_note.quarterLength
                    gap = next_note.offset - current_end
                    
                    # If there's a gap, and it's small enough, stretch the note's tail to fill the silence!
                    if 0 < gap <= max_gap_to_fill:
                        current_note.quarterLength += gap

        # Actually execute the massive sequence function on both hands independently
        sequence_hand(flat_right)
        sequence_hand(flat_left)

        # BUG FIX: Force both hands to have the exact same duration so the rendering engine doesn't crash
        end_time = max(flat_right.highestTime, flat_left.highestTime)
        flat_right.insert(end_time, note.Rest(quarterLength=1.0))
        flat_left.insert(end_time, note.Rest(quarterLength=1.0))

        # Ask music21 to officially calculate where the measure lines (bars) belong based on our tempo
        right_measured = flat_right.makeMeasures()
        left_measured = flat_left.makeMeasures()
        
        # Clean up any leftover messy overlapping notes
        right_clean = right_measured.chordify()
        left_clean = left_measured.chordify()
        
        # --- SCORE CONSTRUCTION ---
        # Build the formal objects required for standard MusicXML formatting
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
        
        # --- DYNAMIC CLEFS ---
        # Right Hand Loop: Evaluate each measure and dynamically swap clefs if the notes get too high or low
        current_right_clef = 'treble'
        for m in right_clean.getElementsByClass('Measure'):
            m_new = copy.deepcopy(m)
            for c in m_new.getElementsByClass('Clef'):
                m_new.remove(c) # Strip out existing clefs
                
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
            m_new.makeRests(fillGaps=True, inPlace=True) # Fill empty space with rests
            right_hand.append(m_new)

        # Left Hand Loop: Evaluate each measure and dynamically swap clefs if the notes get too high or low
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
            
        # Combine both fully processed hands into a single Grand Staff sheet music object
        grand_staff = stream.Score()
        grand_staff.insert(0, right_hand)
        grand_staff.insert(0, left_hand)
        
        # Render the final MusicXML code to a temporary file
        grand_staff.write("musicxml", fp=temp_xml_path, makeNotation=True)
        
        # --- RESPONSE GENERATION ---
        # Read the generated XML code and the Base64 MIDI data so we can send it back to React
        with open(temp_xml_path, "r") as f:
            xml_string = f.read()
            
        with open(temp_midi_path, "rb") as f:
            midi_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        # Ship it!
        return {
            "status": "success",
            "message": f"Successfully transcribed {file.filename}",
            "xml_data": xml_string,
            "midi_data": midi_base64 
        }
        
    except Exception as e:
        # If the math explodes somewhere, catch the error and send a polite message back to the UI
        print("\n❌ TRANSCRIPTION ERROR:")
        traceback.print_exc() 
        error_msg = str(e)
        if not error_msg: 
            error_msg = repr(e) 
        return {"status": "error", "message": error_msg}
        
    finally:
        # Server Housekeeping: Delete the temporary audio, MIDI, and XML files so the hard drive doesn't fill up
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_midi_path):
            os.remove(temp_midi_path)
        if os.path.exists(temp_xml_path):
            os.remove(temp_xml_path)