import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

YOLO_DETECTION_PATH = os.path.join(BASE_DIR, 'model', 'yolo', 'yolov8-5.pt')

YOLO_CLASSIFICATION_PATHS = {
    'MODEL6': os.path.join(BASE_DIR, 'model', 'yolocls', 'yolov8-cls-6.pt'),
    'MODEL7': os.path.join(BASE_DIR, 'model', 'yolocls', 'yolov8-cls-7.pt'),
    'MODEL8': os.path.join(BASE_DIR, 'model', 'yolocls', 'yolov8-cls-8.pt'),
}

_detection_model = None
_classification_models = {}

def get_detection_model():
    global _detection_model
    if _detection_model is None:
        from ultralytics import YOLO
        print("Loading YOLO detection model...")
        _detection_model = YOLO(YOLO_DETECTION_PATH)
        print("✓ YOLO detection model loaded")
    return _detection_model

def get_classification_model(model_name='MODEL8'):
    global _classification_models
    if model_name not in _classification_models:
        from ultralytics import YOLO
        path = YOLO_CLASSIFICATION_PATHS.get(model_name)
        if not path:
            raise ValueError(f"Unknown model: {model_name}")
        print(f"Loading classification model {model_name}...")
        _classification_models[model_name] = YOLO(path)
        print(f"✓ {model_name} loaded")
    return _classification_models[model_name]

detection_model = get_detection_model
classification_model = get_classification_model