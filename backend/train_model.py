# --- IMPORTS ---
import pandas as pd # Used to read and manipulate the massive CSV spreadsheet
from sklearn.ensemble import RandomForestClassifier # The actual Machine Learning algorithm ("the brain")
import joblib # A tool used to package and save the trained model into a file

# --- MAIN TRAINING FUNCTION ---
# This script reads the study guide (CSV) created by build_dataset.py,
# looks for mathematical patterns, and learns how to guess Right vs. Left hand.
def build_and_save_model():
    print("1. Loading massive dataset...")
    try:
        # Step 1: Load the Answer Key
        # We read the massive CSV file containing all the extracted notes and their true hand labels
        df = pd.read_csv('massive_training_data.csv')
        print(f"   -> Awesome! Successfully loaded {len(df)} rows of data!")
        
        # Step 2: Separate the "Questions" (Features) from the "Answers" (Labels)
        # The 'Features' (X) are the clues the AI uses: pitch, length, and harmonic context
        feature_columns = ['Pitch', 'Duration', 'Concurrent_Notes', 'Dist_To_Highest', 'Dist_To_Lowest']
        X_train = df[feature_columns].values
        
        # The 'Label' (y) is the actual answer: 1 for Right Hand, 0 for Left Hand
        y_train = df['Hand_Label'].values
        
        # Step 3: Train the Brain
        print("2. Training Random Forest Model (This might take a few seconds now!)...")
        # We spin up a Random Forest (which is essentially 100 decision trees voting on the answer)
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        
        # .fit() is where the actual learning happens. The AI studies X to figure out how to guess y.
        clf.fit(X_train, y_train)
        
        # Step 4: Save the Brain
        print("3. Exporting trained model...")
        # Once trained, we freeze the model's brain state and save it to a .pkl file.
        # Your main.py FastAPI server will load this exact file to make live predictions!
        joblib.dump(clf, 'hand_classifier.pkl')
        print("✅ Success! The upgraded 'hand_classifier.pkl' has been saved.")
        
    except FileNotFoundError:
        # Friendly error if you forgot to run build_dataset.py first
        print("❌ Error: Could not find 'massive_training_data.csv'. Make sure it is in the same folder!")
    except Exception as e:
        # Catch-all for any other unexpected errors (like running out of computer RAM)
        print(f"❌ Error: {e}")

# --- EXECUTION BLOCK ---
# This ensures the training process only starts if you explicitly run this specific file 
# (e.g., by typing `python train_model.py` in your terminal)
if __name__ == "__main__":
    build_and_save_model()