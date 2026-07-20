import os
import pandas as pd
from music21 import converter, note, chord

def extract_features_from_midi(midi_folder, output_csv):
    print(f"🔍 Scanning folder: {midi_folder}...")
    all_data = []
    
    for filename in os.listdir(midi_folder):
        if filename.endswith(".mid") or filename.endswith(".midi"):
            filepath = os.path.join(midi_folder, filename)
            print(f"🎵 Processing: {filename}")
            
            try:
                score = converter.parse(filepath)
                valid_parts = [p for p in score.parts if len(p.recurse().notes) > 0]
                
                if len(valid_parts) == 0:
                    continue
                    
                # If it's a 2-handed song, split by track. If 1-handed, we'll assign it automatically!
                is_one_handed = len(valid_parts) == 1
                right_hand_ids = set()
                left_hand_ids = set()
                
                if not is_one_handed:
                    right_hand_ids = set(id(n) for n in valid_parts[0].recurse().notes)
                    left_hand_ids = set(id(n) for n in valid_parts[1].recurse().notes)
                else:
                    # For 1-handed training songs, decide if it's treble or bass based on pitch
                    all_pitches = [p.midi for n in valid_parts[0].flatten().notes for p in (n.pitches if getattr(n, 'isChord', False) else [n.pitch])]
                    if all_pitches and sum(all_pitches)/len(all_pitches) > 55:
                        right_hand_ids = set(id(n) for n in valid_parts[0].recurse().notes)
                    else:
                        left_hand_ids = set(id(n) for n in valid_parts[0].recurse().notes)

                flat_score = score.flatten().notes
                
                for el in flat_score:
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
                        
                    max_p = max(active_pitches)
                    min_p = min(active_pitches)
                    c_count = len(active_pitches)
                    
                    if isinstance(el, note.Note):
                        hand_label = 1 if id(el) in right_hand_ids else (0 if id(el) in left_hand_ids else None)
                        if hand_label is not None:
                            dist_high = max_p - el.pitch.midi
                            dist_low = el.pitch.midi - min_p
                            all_data.append([el.pitch.midi, float(el.quarterLength), c_count, dist_high, dist_low, hand_label])
                            
                    elif isinstance(el, chord.Chord):
                        hand_label = 1 if id(el) in right_hand_ids else (0 if id(el) in left_hand_ids else None)
                        if hand_label is not None:
                            for p in el.pitches:
                                dist_high = max_p - p.midi
                                dist_low = p.midi - min_p
                                all_data.append([p.midi, float(el.quarterLength), c_count, dist_high, dist_low, hand_label])
                                
            except Exception as e:
                print(f"   ❌ Error processing {filename}: {e}")

    # Back to the original 5 features + label
    df = pd.DataFrame(all_data, columns=['Pitch', 'Duration', 'Concurrent_Notes', 'Dist_To_Highest', 'Dist_To_Lowest', 'Hand_Label'])
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Success! Created {output_csv} with {len(df)} rows of data!")

if __name__ == "__main__":
    if not os.path.exists('midi_data'):
        os.makedirs('midi_data')
    else:
        extract_features_from_midi('midi_data', 'massive_training_data.csv')