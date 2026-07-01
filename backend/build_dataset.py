import os
import pandas as pd
from music21 import converter, instrument, note, chord

def extract_features_from_midi(midi_folder, output_csv):
    print(f"🔍 Scanning folder: {midi_folder}...")
    
    all_data = []
    
    # Loop through every MIDI file in your folder
    for filename in os.listdir(midi_folder):
        if filename.endswith(".mid") or filename.endswith(".midi"):
            filepath = os.path.join(midi_folder, filename)
            print(f"🎵 Processing: {filename}")
            
            try:
                # Load the MIDI file using music21
                score = converter.parse(filepath)
                parts = instrument.partitionByInstrument(score)
                
                # We need a piano song that has at least two parts (Left and Right hand tracks)
                if not parts or len(parts.parts) < 2:
                    print(f"   ⏭️ Skipping {filename}: Couldn't find 2 separate hand tracks.")
                    continue
                
                # Usually, Part 0 is the Right Hand (Treble) and Part 1 is the Left Hand (Bass)
                right_hand_notes = parts.parts[0].recurse().notes
                left_hand_notes = parts.parts[1].recurse().notes
                
                # Process Right Hand (Label = 1)
                all_data.extend(process_notes(right_hand_notes, hand_label=1))
                
                # Process Left Hand (Label = 0)
                all_data.extend(process_notes(left_hand_notes, hand_label=0))
                
            except Exception as e:
                print(f"   ❌ Error processing {filename}: {e}")

    # Convert our massive list into a Pandas DataFrame
    df = pd.DataFrame(all_data, columns=[
        'Pitch', 'Duration', 'Concurrent_Notes', 
        'Dist_To_Highest', 'Dist_To_Lowest', 'Hand_Label'
    ])
    
    # Save it to a CSV file!
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Success! Created {output_csv} with {len(df)} rows of data!")

def process_notes(music21_notes, hand_label):
    """Helper function to turn music21 notes into our ML features"""
    extracted_data = []
    
    # Group notes by their exact start time so we can calculate "Concurrent Notes"
    # This is a slightly simplified version to get you started!
    for element in music21_notes:
        notes_in_group = []
        
        # If it's a chord, break it into individual notes
        if isinstance(element, chord.Chord):
            notes_in_group = [n for n in element.notes]
        # If it's a single note, just put it in a list
        elif isinstance(element, note.Note):
            notes_in_group = [element]
            
        if not notes_in_group:
            continue
            
        # Figure out the highest and lowest pitches at this exact moment
        pitches = [n.pitch.midi for n in notes_in_group]
        highest_pitch = max(pitches)
        lowest_pitch = min(pitches)
        concurrent_count = len(pitches)
        
        # Calculate features for every single note
        for n in notes_in_group:
            pitch_val = n.pitch.midi
            duration_val = float(n.quarterLength)
            
            # Here is our feature engineering!
            dist_highest = highest_pitch - pitch_val
            dist_lowest = pitch_val - lowest_pitch
            
            extracted_data.append([
                pitch_val, 
                duration_val, 
                concurrent_count, 
                dist_highest, 
                dist_lowest, 
                hand_label
            ])
            
    return extracted_data

if __name__ == "__main__":
    # Create a folder named 'midi_data' and put your downloaded MIDI files in it!
    if not os.path.exists('midi_data'):
        os.makedirs('midi_data')
        print("📁 Created a new folder called 'midi_data'. Put your downloaded MIDI files in there and run this again!")
    else:
        extract_features_from_midi('midi_data', 'massive_training_data.csv')