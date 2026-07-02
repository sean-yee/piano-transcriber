import os
import pandas as pd
from music21 import converter, instrument, note, chord

def extract_features_from_midi(midi_folder, output_csv):
    print(f"🔍 Scanning folder: {midi_folder}...")
    all_data = []
    
    for filename in os.listdir(midi_folder):
        if filename.endswith(".mid") or filename.endswith(".midi"):
            filepath = os.path.join(midi_folder, filename)
            print(f"🎵 Processing: {filename}")
            
            try:
                score = converter.parse(filepath)
                
                # --- NEW: Get raw tracks that actually contain notes ---
                # (This ignores empty metadata tracks and stops music21 from merging identical instruments)
                valid_parts = [p for p in score.parts if len(p.recurse().notes) > 0]
                
                if len(valid_parts) < 2:
                    print(f"   ⏭️ Skipping {filename}: Couldn't find 2 separate hand tracks.")
                    continue
                
                # 1. Secretly tag the notes by their original hand BEFORE we mix them up
                right_hand_ids = set(id(n) for n in valid_parts[0].recurse().notes)
                left_hand_ids = set(id(n) for n in valid_parts[1].recurse().notes)
                
                # 2. Smash all the notes together (exactly like main.py does with audio!)
                flat_score = score.flatten().notes
                
                # 3. Group them by their exact start time
                for el in flat_score:
                    concurrent = flat_score.getElementsByOffset(
                        el.offset, 
                        mustBeginInSpan=False, 
                        mustFinishInSpan=False
                    )
                    
                    active_pitches = []
                    for c in concurrent:
                        if isinstance(c, note.Note):
                            active_pitches.append(c.pitch.midi)
                        elif isinstance(c, chord.Chord):
                            active_pitches.extend([p.midi for p in c.pitches])
                            
                    if not active_pitches:
                        continue
                        
                    max_p = max(active_pitches)
                    min_p = min(active_pitches)
                    c_count = len(active_pitches)
                    
                    if isinstance(el, note.Note):
                        # Figure out which hand originally played this note
                        if id(el) in right_hand_ids:
                            hand_label = 1
                        elif id(el) in left_hand_ids:
                            hand_label = 0
                        else:
                            continue # Skip if we don't know
                            
                        # Calculate features across the ENTIRE piano at this exact moment
                        dist_high = max_p - el.pitch.midi
                        dist_low = el.pitch.midi - min_p
                        all_data.append([el.pitch.midi, float(el.quarterLength), c_count, dist_high, dist_low, hand_label])
                        
                    elif isinstance(el, chord.Chord):
                        if id(el) in right_hand_ids:
                            hand_label = 1
                        elif id(el) in left_hand_ids:
                            hand_label = 0
                        else:
                            continue
                            
                        for p in el.pitches:
                            dist_high = max_p - p.midi
                            dist_low = p.midi - min_p
                            all_data.append([p.midi, float(el.quarterLength), c_count, dist_high, dist_low, hand_label])
                            
            except Exception as e:
                print(f"   ❌ Error processing {filename}: {e}")

    df = pd.DataFrame(all_data, columns=[
        'Pitch', 'Duration', 'Concurrent_Notes', 
        'Dist_To_Highest', 'Dist_To_Lowest', 'Hand_Label'
    ])
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Success! Created {output_csv} with {len(df)} perfectly matched rows of data!")

if __name__ == "__main__":
    if not os.path.exists('midi_data'):
        os.makedirs('midi_data')
    else:
        extract_features_from_midi('midi_data', 'massive_training_data.csv')