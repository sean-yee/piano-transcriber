# --- IMPORTS ---
import os
import pandas as pd # Used to build and save the final massive data spreadsheet (CSV)
from music21 import converter, note, chord # Used to read and dissect the MIDI files

# --- MAIN EXTRACTION ENGINE ---
def extract_features_from_midi(midi_folder, output_csv):
    print(f"🔍 Scanning folder: {midi_folder}...")
    
    # This empty list will eventually hold thousands of rows of data, one for every single note processed
    all_data = []
    
    # Loop through every file inside the target folder
    for filename in os.listdir(midi_folder):
        if filename.endswith(".mid") or filename.endswith(".midi"):
            filepath = os.path.join(midi_folder, filename)
            print(f"🎵 Processing: {filename}")
            
            try:
                # Load the MIDI file into music21 so we can analyze it programmatically
                score = converter.parse(filepath)
                
                # Filter out any weird, empty instrument tracks (like a silent drum track)
                valid_parts = [p for p in score.parts if len(p.recurse().notes) > 0]
                
                if len(valid_parts) == 0:
                    continue
                    
                # --- HAND ASSIGNMENT LOGIC ---
                # We need to tag every note as "Right Hand" (1) or "Left Hand" (0) so the AI has an answer key.
                is_one_handed = len(valid_parts) == 1
                right_hand_ids = set()
                left_hand_ids = set()
                
                if not is_one_handed:
                    # If the MIDI file has 2 distinct tracks, we assume Track 0 is the Right Hand and Track 1 is the Left Hand.
                    # We store the unique memory 'id' of every note so we can tag them later.
                    right_hand_ids = set(id(n) for n in valid_parts[0].recurse().notes)
                    left_hand_ids = set(id(n) for n in valid_parts[1].recurse().notes)
                else:
                    # EDGE CASE: If the MIDI file only has 1 track, we have to guess which hand it is.
                    # We average all the pitches together. If the average is high (> 55), we assume it's a Right Hand training song.
                    all_pitches = [p.midi for n in valid_parts[0].flatten().notes for p in (n.pitches if getattr(n, 'isChord', False) else [n.pitch])]
                    if all_pitches and sum(all_pitches)/len(all_pitches) > 55:
                        right_hand_ids = set(id(n) for n in valid_parts[0].recurse().notes)
                    else:
                        left_hand_ids = set(id(n) for n in valid_parts[0].recurse().notes)

                # Flatten the score so it's just one continuous timeline of notes, regardless of tracks
                flat_score = score.flatten().notes
                
                # --- FEATURE ENGINEERING ---
                # This is the most important part of the file. We don't just tell the AI "This is a C4". 
                # We tell the AI the *context* of the note so it can recognize patterns.
                for el in flat_score:
                    # Look at the exact timestamp of this note, and grab ALL other notes playing at this exact millisecond
                    concurrent = flat_score.getElementsByOffset(
                        el.offset, mustBeginInSpan=False, mustFinishInSpan=False
                    )
                    
                    active_pitches = []
                    for c in concurrent:
                        if isinstance(c, note.Note):
                            active_pitches.append(c.pitch.midi)
                        elif isinstance(c, chord.Chord):
                            active_pitches.extend([p.midi for p in c.pitches])
                            
                    if not active_pitches:
                        continue
                        
                    # Calculate the harmonic context of this exact moment in the song
                    max_p = max(active_pitches)
                    min_p = min(active_pitches)
                    c_count = len(active_pitches) # How many keys are currently being pressed down?
                    
                    # If it's a single note...
                    if isinstance(el, note.Note):
                        # Check our IDs to see if this is a Right (1) or Left (0) hand note
                        hand_label = 1 if id(el) in right_hand_ids else (0 if id(el) in left_hand_ids else None)
                        
                        if hand_label is not None:
                            # Calculate how far away this note is from the highest and lowest notes currently playing
                            dist_high = max_p - el.pitch.midi
                            dist_low = el.pitch.midi - min_p
                            
                            # Add this perfectly formatted row of data to our master list
                            all_data.append([el.pitch.midi, float(el.quarterLength), c_count, dist_high, dist_low, hand_label])
                            
                    # If it's a chord...
                    elif isinstance(el, chord.Chord):
                        hand_label = 1 if id(el) in right_hand_ids else (0 if id(el) in left_hand_ids else None)
                        
                        if hand_label is not None:
                            # Break the chord apart and create a separate row of data for EVERY single pitch inside it
                            for p in el.pitches:
                                dist_high = max_p - p.midi
                                dist_low = p.midi - min_p
                                all_data.append([p.midi, float(el.quarterLength), c_count, dist_high, dist_low, hand_label])
                                
            except Exception as e:
                # If a specific MIDI file is corrupted, print the error but keep processing the rest of the folder
                print(f"   ❌ Error processing {filename}: {e}")

    # --- SAVE THE DATA ---
    # Convert our massive python list into a Pandas DataFrame (a virtual spreadsheet)
    # The columns map exactly to the 5 features + 1 label we extracted above
    df = pd.DataFrame(all_data, columns=['Pitch', 'Duration', 'Concurrent_Notes', 'Dist_To_Highest', 'Dist_To_Lowest', 'Hand_Label'])
    
    # Save it to the hard drive as a CSV file so `train_model.py` can load it later
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Success! Created {output_csv} with {len(df)} rows of data!")

# --- EXECUTION BLOCK ---
# This block only runs if you execute this file directly (e.g., `python build_dataset.py`)
if __name__ == "__main__":
    # Ensure the target folder actually exists so the script doesn't crash immediately
    if not os.path.exists('midi_data'):
        os.makedirs('midi_data')
    else:
        # Fire the engine!
        extract_features_from_midi('midi_data', 'massive_training_data.csv')