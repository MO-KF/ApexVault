import cv2
import face_recognition
import os
import numpy as np

FACE_DIR = os.path.join(os.environ.get('APPDATA', 'C:\\'), 'ApexVault', 'faces')
if not os.path.exists(FACE_DIR):
    os.makedirs(FACE_DIR)

def _save_encoding(encoding, file_path):

    np.save(file_path, np.asarray(encoding, dtype=np.float64))

def _load_encoding(file_path):

    if os.path.exists(file_path):
        try:
            encoding = np.load(file_path, allow_pickle=False)
            return encoding if isinstance(encoding, np.ndarray) and encoding.size else None
        except Exception:
            return None
    legacy = os.path.splitext(file_path)[0] + ".pkl"
    if os.path.exists(legacy):
        import pickle
        with open(legacy, "rb") as f:
            encoding = np.asarray(pickle.load(f), dtype=np.float64)
        _save_encoding(encoding, file_path)
        try:
            os.remove(legacy)
        except OSError:
            pass
        return encoding
    return None

def register_face(target_id):

    cap = cv2.VideoCapture(0)
    registered = False
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        
        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        
        cv2.putText(frame, "Press 'S' to Save Face | 'Q' to Cancel", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow(f'Register Face - {target_id}', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s') and face_locations:
            encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            if encodings:
                _save_encoding(encodings[0], os.path.join(FACE_DIR, f"{target_id}.npy"))
                registered = True
                break
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return registered

def verify_face(target_id):

    known_encoding = _load_encoding(os.path.join(FACE_DIR, f"{target_id}.npy"))
    if known_encoding is None:
        return False
        
    cap = cv2.VideoCapture(0)
    match_found = False
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)
            
        cv2.putText(frame, "Looking for you... Press 'Q' to Cancel", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow(f'Face Unlock - {target_id}', frame)
        
        if face_encodings:
            matches = face_recognition.compare_faces([known_encoding], face_encodings[0], tolerance=0.5)
            if matches[0]:
                match_found = True
                break
                
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
    return match_found