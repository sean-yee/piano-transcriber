import os
import base64
import copy
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from basic_pitch.inference import predict
from music21 import converter, stream, clef, instrument, note, chord

app = FastAPI()

# Allow your React app (running on localhost:5173) to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Piano Transcriber API is running!"}

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # 1. Save the uploaded file temporarily
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        # 2. Run Spotify's Basic Pitch with noise cleaning parameters
        model_output, midi_data, note_events = predict(
            temp_file_path,
            minimum_note_length=120.0,
            multiple_pitch_bends=False
        )
        
        temp_midi_path = temp_file_path.replace(os.path.splitext(temp_file_path)[1], ".mid")
        midi_data.write(temp_midi_path)
        
        # 3. Convert MIDI to MusicXML using music21
        # Parse the MIDI cleanly first. Let music21 handle the initial measure layout.
        parsed_score = converter.parse(
            temp_midi_path, 
            quantizePost=True, 
            quarterLengthDivisors=(4,)
        )
        
        ai_part = parsed_score.parts[0]
        
        right_hand = stream.Part()
        right_hand.id = 'RightHand'
        right_hand.insert(0, instrument.Piano())
        right_hand.insert(0, clef.TrebleClef())
        
        left_hand = stream.Part()
        left_hand.id = 'LeftHand'
        left_hand.insert(0, instrument.Piano())
        # Remove the text labels from the left hand part so they don't double up
        left_hand.partName = ''
        left_hand.partAbbreviation = ''
        left_hand.insert(0, clef.BassClef())
        
        # --- THE GRAND STAFF SPLIT FIX ---
        for m in ai_part.getElementsByClass('Measure'):
            m_right = stream.Measure(number=m.number)
            m_left = stream.Measure(number=m.number)
            
            # Duplicate structural elements (Time/Key Signatures) from the surface
            for el in m.elements:
                if el.classes[0] in ['TimeSignature', 'KeySignature']:
                    m_right.insert(el.offset, copy.deepcopy(el))
                    m_left.insert(el.offset, copy.deepcopy(el))

            # THE FIX: Use .flatten().notes to smash open any hidden 'Voice' folders!
            for el in m.flatten().notes:
                if isinstance(el, note.Note):
                    # MIDI note 60 is Middle C
                    if el.pitch.midi >= 60:
                        m_right.insert(el.offset, copy.deepcopy(el))
                    else:
                        m_left.insert(el.offset, copy.deepcopy(el))
                        
                elif isinstance(el, chord.Chord):
                    # Split chords between hands based on Middle C
                    right_pitches = [p for p in el.pitches if p.midi >= 60]
                    left_pitches = [p for p in el.pitches if p.midi < 60]
                    
                    if right_pitches:
                        c_right = chord.Chord(right_pitches)
                        c_right.quarterLength = el.quarterLength
                        m_right.insert(el.offset, c_right)
                    if left_pitches:
                        c_left = chord.Chord(left_pitches)
                        c_left.quarterLength = el.quarterLength
                        m_left.insert(el.offset, c_left)
            
            # Fill the mathematical gaps with rests
            m_right.makeRests(fillGaps=True, inPlace=True)
            m_left.makeRests(fillGaps=True, inPlace=True)
            
            right_hand.append(m_right)
            left_hand.append(m_left)
            
        # Build the final Score
        grand_staff = stream.Score()
        grand_staff.insert(0, right_hand)
        grand_staff.insert(0, left_hand)
        
        temp_xml_path = temp_file_path.replace(os.path.splitext(temp_file_path)[1], ".xml")
        grand_staff.write("musicxml", temp_xml_path)
        
        # 4. Read the XML as a string to send to React
        with open(temp_xml_path, "r") as f:
            xml_string = f.read()
            
        # 5. Read MIDI file as Base64 for the interactive web player
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
        # Clean up ALL temp files so the server doesn't get bloated
        for ext in ["", ".mid", ".xml"]:
            path = temp_file_path.replace(os.path.splitext(temp_file_path)[1], ext)
            if os.path.exists(path):
                os.remove(path)