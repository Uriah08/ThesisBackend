from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

import cv2
import os
import shutil
import numpy as np
from django.conf import settings

from .yolo_cnn.inference import detection_model, classification_model

from datetime import datetime
import uuid

class ScanView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def detect_and_classify(self, image, model_name='MODEL8'):
        det_model = detection_model()
        cls_model = classification_model(model_name)
        
        original = image.copy()
        results = det_model(image, conf=0.25, verbose=False)

        detections = []
        dry_count = 0
        undried_count = 0
        reject_count = 0

        COLORS = {
            'DRY': (0, 255, 0),
            'UNDRIED': (0, 165, 255),
            'REJECT': (0, 0, 255)
        }

        # ── Step 1: collect all reject boxes with confidence >= 0.30 ──
        reject_boxes = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])
            class_name = det_model.names[int(box.cls[0])]
            if class_name.lower() == 'reject' and confidence >= 0.30:
                reject_boxes.append((x1, y1, x2, y2, confidence))

        # ── Step 2: helper to check if a fish box overlaps a reject box ──
        def is_overlapping(box, threshold=0.3):
            bx1, by1, bx2, by2 = box
            for rx1, ry1, rx2, ry2, _ in reject_boxes:
                ix1, iy1 = max(bx1, rx1), max(by1, ry1)
                ix2, iy2 = min(bx2, rx2), min(by2, ry2)
                if ix2 <= ix1 or iy2 <= iy1:
                    continue
                intersection = (ix2 - ix1) * (iy2 - iy1)
                box_area = (bx2 - bx1) * (by2 - by1)
                if box_area > 0 and intersection / box_area >= threshold:
                    return True
            return False

        # ── Step 3: draw reject boxes first ──
        for rx1, ry1, rx2, ry2, conf in reject_boxes:
            label = 'REJECT'
            conf_pct = conf * 100
            color = COLORS['REJECT']
            reject_count += 1

            cv2.rectangle(original, (rx1, ry1), (rx2, ry2), color, 3)
            label_text = f"{label} {conf_pct:.1f}%"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(original, (rx1, ry1 - th - 10), (rx1 + tw + 10, ry1), color, -1)
            cv2.putText(original, label_text, (rx1 + 5, ry1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            detections.append({
                'class': 'reject',
                'label': label,
                'confidence': conf_pct,
                'bbox': [rx1, ry1, rx2, ry2]
            })

        # ── Step 4: process fish boxes, skip if overlapping a reject ──
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])
            class_name = det_model.names[int(box.cls[0])]

            if class_name.lower() != 'fish':
                continue

            # skip this fish if it overlaps a reject box
            if is_overlapping((x1, y1, x2, y2)):
                continue

            crop = original[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            cls_results = cls_model(crop, verbose=False)
            probs = cls_results[0].probs
            top1_idx = probs.top1
            top1_conf = float(probs.top1conf)
            predicted_class = cls_model.names[top1_idx]
            
            if top1_conf < 0.60:
                continue

            if predicted_class == 'UNDRIED':
                label = 'UNDRIED'
                undried_count += 1
            else:
                label = 'DRY'
                dry_count += 1

            conf_pct = top1_conf * 100
            color = COLORS[label]

            cv2.rectangle(original, (x1, y1), (x2, y2), color, 3)
            label_text = f"{label} {conf_pct:.1f}%"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(original, (x1, y1 - th - 10), (x1 + tw + 10, y1), color, -1)
            cv2.putText(original, label_text, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            detections.append({
                'class': class_name,
                'label': label,
                'confidence': conf_pct,
                'bbox': [x1, y1, x2, y2]
            })

        return original, detections, dry_count, undried_count, reject_count

    def post(self, request):
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({"detail": "No image uploaded"}, status=400)

        model_name = request.data.get('model', 'MODEL8')

        temp_path = "temp.jpg"
        with open(temp_path, "wb+") as f:
            for chunk in image_file.chunks():
                f.write(chunk)

        image = cv2.imread(temp_path)

        annotated_image, detections, dry_count, undried_count, reject_count = self.detect_and_classify(image, model_name)

        user_id = str(request.user.id) if request.user.is_authenticated else "default"
        user_folder = os.path.join(settings.MEDIA_ROOT, "scanned", user_id)

        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)

        os.makedirs(user_folder, exist_ok=True)

        filename = f"{uuid.uuid4().hex[:6]}.jpg"
        save_path = os.path.join(user_folder, filename)
        cv2.imwrite(save_path, annotated_image)

        image_url = request.build_absolute_uri(
            settings.MEDIA_URL + f"scanned/{user_id}/{filename}?t={datetime.now().timestamp()}"
        )

        return Response({
            'image_url': image_url,
            'detections': detections,
            'dry_count': dry_count,
            'undried_count': undried_count,
            'reject_count': reject_count,
            'total': dry_count + undried_count + reject_count
        })
        
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.parsers import MultiPartParser, FormParser
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.authentication import TokenAuthentication

# import cv2
# import os
# import shutil
# import numpy as np
# from django.conf import settings

# from .yolo_cnn.inference import detection_model, classification_model

# from datetime import datetime
# import uuid

# class ScanView(APIView):
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]
#     parser_classes = [MultiPartParser, FormParser]

#     def detect_and_classify(self, image, model_name='MODEL8'):
#         det_model = detection_model()
#         cls_model = classification_model(model_name)
        
#         original = image.copy()
#         results = det_model(image, conf=0.25, verbose=False)

#         detections = []
#         dry_count = 0
#         undried_count = 0
#         reject_count = 0

#         COLORS = {
#             'DRY': (0, 255, 0),
#             'UNDRIED': (0, 165, 255),
#             'REJECT': (0, 0, 255)
#         }

#         for box in results[0].boxes:
#             x1, y1, x2, y2 = map(int, box.xyxy[0])
#             confidence = float(box.conf[0])
#             class_name = det_model.names[int(box.cls[0])]

#             if class_name.lower() == 'fish':
#                 crop = original[y1:y2, x1:x2]
#                 if crop.size == 0:
#                     continue
                
#                 cls_results = cls_model(crop, verbose=False)
                
#                 probs = cls_results[0].probs
#                 top1_idx = probs.top1
#                 top1_conf = float(probs.top1conf)
                
#                 predicted_class = cls_model.names[top1_idx]
                
#                 if predicted_class == 'UNDRIED':
#                     label = 'UNDRIED'
#                     conf_pct = top1_conf * 100
#                     color = COLORS['UNDRIED']
#                     undried_count += 1
#                 else:
#                     label = 'DRY'
#                     conf_pct = top1_conf * 100
#                     color = COLORS['DRY']
#                     dry_count += 1

#             elif class_name.lower() == 'reject':
#                 label = 'REJECT'
#                 conf_pct = float(confidence * 100)
#                 color = COLORS['REJECT']
#                 reject_count += 1
#             else:
#                 continue

#             cv2.rectangle(original, (x1, y1), (x2, y2), color, 3)
#             label_text = f"{label} {conf_pct:.1f}%"
#             (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
#             cv2.rectangle(original, (x1, y1-th-10), (x1+tw+10, y1), color, -1)
#             cv2.putText(original, label_text, (x1+5, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

#             detections.append({
#                 'class': class_name,
#                 'label': label,
#                 'confidence': conf_pct,
#                 'bbox': [x1, y1, x2, y2]
#             })

#         return original, detections, dry_count, undried_count, reject_count

#     def post(self, request):
#         image_file = request.FILES.get('image')
#         if not image_file:
#             return Response({"detail": "No image uploaded"}, status=400)

#         model_name = request.data.get('model', 'MODEL8')

#         temp_path = "temp.jpg"
#         with open(temp_path, "wb+") as f:
#             for chunk in image_file.chunks():
#                 f.write(chunk)

#         image = cv2.imread(temp_path)

#         annotated_image, detections, dry_count, undried_count, reject_count = self.detect_and_classify(image, model_name)

#         user_id = str(request.user.id) if request.user.is_authenticated else "default"
#         user_folder = os.path.join(settings.MEDIA_ROOT, "scanned", user_id)

#         if os.path.exists(user_folder):
#             shutil.rmtree(user_folder)

#         os.makedirs(user_folder, exist_ok=True)

#         filename = f"{uuid.uuid4().hex[:6]}.jpg"
#         save_path = os.path.join(user_folder, filename)
#         cv2.imwrite(save_path, annotated_image)

#         image_url = request.build_absolute_uri(
#             settings.MEDIA_URL + f"scanned/{user_id}/{filename}?t={datetime.now().timestamp()}"
#         )

#         return Response({
#             'image_url': image_url,
#             'detections': detections,
#             'dry_count': dry_count,
#             'undried_count': undried_count,
#             'reject_count': reject_count,
#             'total': dry_count + undried_count + reject_count
#         })