import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

def build_and_save_model():
    print("1. Loading dataset...")
    try:
        # This will read your toy dataset for now, but when you build 
        # your massive 50,000 row dataset, you just drop it right here!
        df = pd.read_csv('training_data.csv')
        
        feature_columns = ['Pitch', 'Duration', 'Concurrent_Notes', 'Dist_To_Highest', 'Dist_To_Lowest']
        X_train = df[feature_columns].values
        y_train = df['Hand_Label'].values
        
        print("2. Training Random Forest Model...")
        # We can increase n_estimators to 100 now because we are training offline!
        # This makes the model much more accurate.
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X_train, y_train)
        
        print("3. Exporting trained model...")
        joblib.dump(clf, 'hand_classifier.pkl')
        print("✅ Success! 'hand_classifier.pkl' has been saved.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    build_and_save_model()