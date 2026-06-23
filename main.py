import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from basic_pitch.inference import predict

app = FastAPI()

# Allow your future React app (running on localhost:5173) to talk to this API
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
        # 2. Run Spotify's Basic Pitch
        _, midi_data, _ = predict(temp_file_path)
        
        temp_midi_path = temp_file_path.replace(os.path.splitext(temp_file_path)[1], ".mid")
        midi_data.write(temp_midi_path)
        
        # 3. Convert MIDI to MusicXML using music21
        from music21 import converter
        
        # Parse the raw AI MIDI
        parsed_midi = converter.parse(temp_midi_path)
        
        # --- THE BULLETPROOF QUANTIZE FIX ---
        # Instead of inPlace=True, we explicitly overwrite the variable
        # with a brand new, strictly quantized Stream.
        parsed_midi = parsed_midi.quantize([4, 8, 16])
        # ------------------------------------
        
        temp_xml_path = temp_file_path.replace(os.path.splitext(temp_file_path)[1], ".xml")
        parsed_midi.write("musicxml", temp_xml_path)
        
        # 4. NEW: Read the XML as a string to send to React
        with open(temp_xml_path, "r") as f:
            xml_string = f.read()
        
        return {
            "status": "success",
            "message": f"Successfully transcribed {file.filename}",
            "xml_data": xml_string # Send the raw XML string!
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
    finally:
        # Clean up ALL temp files
        for ext in ["", ".mid", ".xml"]:
            path = temp_file_path.replace(os.path.splitext(temp_file_path)[1], ext)
            if os.path.exists(path):
                os.remove(path)