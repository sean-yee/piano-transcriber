import os
import base64
import copy
import numpy as np
import joblib
import traceback  
import librosa
import pretty_midi
import uuid # NEW: For generating unique task IDs
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks # NEW: BackgroundTasks added
from fastapi.middleware.cors import CORSMiddleware
from piano_transcription_inference import PianoTranscription, sample_rate
from music21 import converter, stream, clef, instrument, note, chord, tempo, meter, key as m21_key
from sklearn.ensemble import RandomForestClassifier
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- APP INITIALIZATION ---
app = FastAPI()

origins = [
    "https://main.d3k4cqc4hd4mc0.amplifyapp.com",
    "https://pianopilotai.com",
    "http://localhost:5173",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GLOBAL TASK TRACKER ---
# This dictionary holds the live progress of every active user
active_tasks = {}

# --- MODEL LOADING ---
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

# --- THE BACKGROUND WORKER ---
# This function does all the heavy lifting in the background while React polls for status
def process_audio_background(task_id: str, temp_file_path: str, base_name: str, temp_midi_path: str, temp_xml_path: str, complexity: int, key_signature: str, volume_threshold: int, polyphony_limit: int, smoothness: int, hand_bias: int, preview_only: bool):
    try:
        active_tasks[task_id]["status"] = "processing"
        active_tasks[task_id]["message"] = "Loading audio and detecting BPM..."
        active_tasks[task_id]["progress"] = 5

        # --- AUDIO PROCESSING ---
        audio, _ = librosa.load(temp_file_path, sr=sample_rate, mono=True)
        
        if preview_only:
            max_samples = 60 * sample_rate
            audio = audio[:max_samples]
            print("Preview Mode: Audio truncated to 60 seconds for BPM detection.")
        
        detected_tempo, _ = librosa.beat.beat_track(y=audio, sr=sample_rate)
        detected_bpm = float(detected_tempo[0]) if isinstance(detected_tempo, np.ndarray) else float(detected_tempo)
        detected_bpm = round(detected_bpm) 
        if detected_bpm == 0:
            detected_bpm = 120
            
        print(f"Task {task_id} - Detected Tempo: {detected_bpm} BPM")

        active_tasks[task_id]["message"] = "Slicing audio into chunks..."
        active_tasks[task_id]["progress"] = 10
        
        audio_segment = AudioSegment.from_file(temp_file_path)
        
        if preview_only:
            audio_segment = audio_segment[:60000]
            
        chunk_length_ms = 30000  
        chunks = [audio_segment[i:i + chunk_length_ms] for i in range(0, len(audio_segment), chunk_length_ms)]
        midi_paths = [None] * len(chunks)
        
        def process_chunk(index, chunk_data):
            c_wav = f"{base_name}_chunk_{index}.wav"
            c_mid = f"{base_name}_chunk_{index}.mid"
            chunk_data.export(c_wav, format="wav")
            c_array, _ = librosa.load(c_wav, sr=sample_rate, mono=True)
            transcriptor.transcribe(c_array, c_mid)
            os.remove(c_wav) 
            return index, c_mid

        active_tasks[task_id]["message"] = "Running ByteDance AI on CPU cores..."
        
        # --- THE PROGRESS LOOP ---
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_chunk = {executor.submit(process_chunk, i, chunk): i for i, chunk in enumerate(chunks)}
            
            completed = 0
            total_chunks = len(chunks)
            
            for future in as_completed(future_to_chunk):
                idx, completed_mid_path = future.result()
                midi_paths[idx] = completed_mid_path
                completed += 1
                
                # Math for the progress bar (reserving 10% to 70% for the AI transcription phase)
                ai_progress = int((completed / total_chunks) * 60) 
                current_progress = 10 + ai_progress
                
                active_tasks[task_id]["progress"] = current_progress
                active_tasks[task_id]["message"] = f"Transcribing audio ({completed}/{total_chunks} chunks)..."
                print(f"✅ Task {task_id}: Finished chunk {idx + 1}/{total_chunks}")
            
        # --- STITCHING THE MIDI ---
        active_tasks[task_id]["message"] = "Stitching chunks and building MIDI..."
        active_tasks[task_id]["progress"] = 75

        merged_midi = pretty_midi.PrettyMIDI()
        piano_program = pretty_midi.instrument_name_to_program('Acoustic Grand Piano')
        merged_piano = pretty_midi.Instrument(program=piano_program)
        
        for i, m_path in enumerate(midi_paths):
            offset_sec = i * (chunk_length_ms / 1000.0) 
            pm = pretty_midi.PrettyMIDI(m_path)
            
            for inst in pm.instruments:
                for n in inst.notes:
                    n.start += offset_sec
                    n.end += offset_sec
                    merged_piano.notes.append(n)
                for cc in inst.control_changes:
                    cc.time += offset_sec
                    merged_piano.control_changes.append(cc)
                    
            os.remove(m_path) 
            
        merged_midi.instruments.append(merged_piano)
        merged_midi.write(temp_midi_path) 
        
        # --- MUSIC21 PARSING & FILTERING ---
        active_tasks[task_id]["message"] = "Cleaning up ghost notes and chords..."
        active_tasks[task_id]["progress"] = 80

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
            note_velocity = el.volume.velocity if (hasattr(el, 'volume') and el.volume.velocity is not None) else 64
            if note_velocity < volume_threshold or el.quarterLength < 0.0625:
                elements_to_remove.append(el)
            elif el.quarterLength > max_note_length:
                el.quarterLength = max_note_length
                
        for el in elements_to_remove:
            flat_stream.remove(el)

        for el in list(flat_stream.notes):
            if getattr(el, 'isChord', False) and len(el.pitches) > polyphony_limit:
                sorted_pitches = sorted(el.pitches, key=lambda p: p.midi)
                if polyphony_limit == 1:
                    kept_pitches = [sorted_pitches[-1]]
                else:
                    kept_pitches = [sorted_pitches[0]] + sorted_pitches[-(polyphony_limit-1):]
                
                if len(kept_pitches) == 1:
                    new_el = note.Note(kept_pitches[0])
                else:
                    new_el = chord.Chord(kept_pitches)
                    
                new_el.quarterLength = el.quarterLength
                new_el.offset = el.offset
                if hasattr(el, 'volume') and el.volume.velocity is not None:
                    new_el.volume.velocity = el.volume.velocity
                flat_stream.replace(el, new_el)

        flat_right = stream.Part()
        flat_left = stream.Part()
        
        flat_right.insert(0, tempo.MetronomeMark(number=detected_bpm))
        flat_right.insert(0, meter.TimeSignature('4/4'))
        flat_left.insert(0, tempo.MetronomeMark(number=detected_bpm))
        flat_left.insert(0, meter.TimeSignature('4/4'))

        if key_signature.lower() == 'auto':
            best_key = flat_stream.analyze('key')
            flat_right.insert(0, best_key)
            flat_left.insert(0, best_key)
        else:
            user_key = m21_key.Key(key_signature)
            flat_right.insert(0, user_key)
            flat_left.insert(0, user_key)
        
        active_tasks[task_id]["message"] = "Running Machine Learning hand splitter..."
        active_tasks[task_id]["progress"] = 85

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
            rh_threshold = 0.5 - (hand_bias / 100.0)

            if isinstance(el, note.Note):
                if c_count == 1 and el.pitch.midi > 48:
                    flat_right.insert(el.offset, copy.deepcopy(el))
                else:
                    dist_high = max_p - el.pitch.midi
                    dist_low = el.pitch.midi - min_p
                    features = np.array([[el.pitch.midi, float(el.quarterLength), c_count, dist_high, dist_low]])
                    probs = hand_classifier.predict_proba(features)[0]
                    rh_confidence = probs[1] 
                    if rh_confidence >= rh_threshold:
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
                    probs = hand_classifier.predict_proba(features)[0]
                    rh_confidence = probs[1]
                    if rh_confidence >= rh_threshold:
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

        active_tasks[task_id]["message"] = "Quantizing rhythms and building sheet music..."
        active_tasks[task_id]["progress"] = 90

        def sequence_hand(hand_stream):
            if complexity == 4: 
                grid_resolution = 16.0  
                collision_push = 0.0625  
                standard_durations = [0.0625, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
                fallback_dur = 0.0625
            elif complexity == 1: 
                grid_resolution = 2.0  
                collision_push = 0.5   
                standard_durations = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
                fallback_dur = 0.5
            elif complexity == 2: 
                grid_resolution = 4.0  
                collision_push = 0.25  
                standard_durations = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
                fallback_dur = 0.25
            else: 
                grid_resolution = 8.0  
                collision_push = 0.125  
                standard_durations = [0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
                fallback_dur = 0.125

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

            if smoothness > 0:
                max_gap_to_fill = (smoothness / 100.0) * 0.5 
                final_notes = list(hand_stream.notes)
                final_notes.sort(key=lambda x: x.offset)
                for i in range(len(final_notes) - 1):
                    current_note = final_notes[i]
                    next_note = final_notes[i+1]
                    current_end = current_note.offset + current_note.quarterLength
                    gap = next_note.offset - current_end
                    if 0 < gap <= max_gap_to_fill:
                        current_note.quarterLength += gap

        sequence_hand(flat_right)
        sequence_hand(flat_left)

        end_time = max(flat_right.highestTime, flat_left.highestTime)
        flat_right.insert(end_time, note.Rest(quarterLength=1.0))
        flat_left.insert(end_time, note.Rest(quarterLength=1.0))

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
        
        active_tasks[task_id]["message"] = "Rendering final XML files..."
        active_tasks[task_id]["progress"] = 98

        grand_staff.write("musicxml", fp=temp_xml_path, makeNotation=True)
        
        with open(temp_xml_path, "r") as f:
            xml_string = f.read()
            
        with open(temp_midi_path, "rb") as f:
            midi_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        # --- THE FINISH LINE ---
        # Save the completed data into the global dictionary for React to pull
        active_tasks[task_id]["status"] = "complete"
        active_tasks[task_id]["progress"] = 100
        active_tasks[task_id]["message"] = "Masterpiece finished!"
        active_tasks[task_id]["xml_data"] = xml_string
        active_tasks[task_id]["midi_data"] = midi_base64

        print(f"🎉 Task {task_id} successfully completed!")
        
    except Exception as e:
        print(f"\n❌ TRANSCRIPTION ERROR for task {task_id}:")
        traceback.print_exc() 
        active_tasks[task_id]["status"] = "error"
        active_tasks[task_id]["message"] = str(e)
        
    finally:
        # Server Housekeeping
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_midi_path):
            os.remove(temp_midi_path)
        if os.path.exists(temp_xml_path):
            os.remove(temp_xml_path)


# --- API ENDPOINTS ---
@app.get("/")
def home():
    return {"message": "Piano Transcriber API is running!"}

# NEW ENDPOINT: React hits this to check the live progress
@app.get("/status/{task_id}")
def get_task_status(task_id: str):
    task = active_tasks.get(task_id)
    if not task:
        return {"status": "error", "message": "Task not found or expired."}
    
    # Send back everything EXCEPT the massive file data unless it's completely finished
    if task["status"] != "complete":
        return {
            "status": task["status"],
            "progress": task["progress"],
            "message": task["message"]
        }
    
    return task

# UPDATED ENDPOINT: The Greeter
@app.post("/transcribe")
async def transcribe_audio(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    complexity: int = Form(2),
    key_signature: str = Form("auto"),
    volume_threshold: int = Form(30),
    polyphony_limit: int = Form(6),
    smoothness: int = Form(50),
    hand_bias: int = Form(0),
    preview_only: bool = Form(False) 
):
    # 1. Generate a unique ID for this job
    task_id = str(uuid.uuid4())
    
    # 2. Put them in the system at 0%
    active_tasks[task_id] = {
        "status": "starting",
        "progress": 0,
        "message": "Uploading file to server...",
        "xml_data": None,
        "midi_data": None
    }
    
    # 3. Save the file temporarily right now
    temp_file_path = f"temp_{task_id}_{file.filename}"
    base_name, _ = os.path.splitext(temp_file_path)
    temp_midi_path = f"{base_name}.mid"
    temp_xml_path = f"{base_name}.xml"
    
    with open(temp_file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    # 4. Tell FastAPI to run the massive engine function in the background
    background_tasks.add_task(
        process_audio_background, 
        task_id, temp_file_path, base_name, temp_midi_path, temp_xml_path, 
        complexity, key_signature, volume_threshold, polyphony_limit, smoothness, hand_bias, preview_only
    )
    
    # 5. Instantly return the Pager ID to React!
    return {"status": "success", "task_id": task_id}