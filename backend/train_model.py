import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

def build_and_save_model():
    print("1. Loading massive dataset...")
    try:
        # --- NEW: Pointing to your newly generated massive dataset! ---
        df = pd.read_csv('massive_training_data.csv')
        print(f"   -> Awesome! Successfully loaded {len(df)} rows of data!")
        
        feature_columns = ['Pitch', 'Duration', 'Concurrent_Notes', 'Dist_To_Highest', 'Dist_To_Lowest']
        X_train = df[feature_columns].values
        y_train = df['Hand_Label'].values
        
        print("2. Training Random Forest Model (This might take a few seconds now!)...")
        # We keep n_estimators at 100, which gives fantastic accuracy on large datasets
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X_train, y_train)
        
        print("3. Exporting trained model...")
        joblib.dump(clf, 'hand_classifier.pkl')
        print("✅ Success! The upgraded 'hand_classifier.pkl' has been saved.")
        
    except FileNotFoundError:
        print("❌ Error: Could not find 'massive_training_data.csv'. Make sure it is in the same folder!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    build_and_save_model()