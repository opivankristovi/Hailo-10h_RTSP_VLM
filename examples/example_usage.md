# Example Usage Scenarios

## Scenario 1: Home Security Monitor

### Raspberry Pi (connected to security camera):
```bash
# Analyze security camera feed with motion detection
python rtsp_vlm_analyzer.py \
  --rtsp rtsp://security_cam:554/h264 \
  --motion-threshold 0.05 \
  --default-question "Is there a person or vehicle in the frame?" \
  --save-frames \
  --results-dir ./security_logs \
  --verbose
```

### Expected Output:
```
2026-03-27 14:30:45 - VLMProcessor - INFO - Motion detected - analyzing frame
2026-03-27 14:30:46 - VLMProcessor - INFO - VLM analysis completed in 1.23s

============================================================
ANALYSIS RESULT - 2026-03-27T14:30:45.123456
============================================================
Source: rtsp://security_cam:554/h264
Question: Is there a person or vehicle in the frame?
Inference time: 1.23s
------------------------------------------------------------
RESPONSE:
Yes, there is one person visible in the frame. They appear to be walking...
============================================================
```

## Scenario 2: Wildlife Camera Trap

### Raspberry Pi in field with battery/solar:
```bash
# Analyze trail camera with sensitive motion detection
python rtsp_vlm_analyzer.py \
  --rtsp rtsp://trail_cam:554/main \
  --motion-threshold 0.02 \
  --default-question "What animals are visible and what are they doing?" \
  --save-frames \
  --results-dir ./wildlife_observations \
  --interval 300  # Also analyze every 5 minutes
```

## Scenario 3: Factory Quality Control

### Central Raspberry Pi (analyzer):
```bash
# Start HTTP server to receive frames from multiple cameras
python rtsp_vlm_analyzer.py \
  --http-port 9090 \
  --results-dir ./factory_qc \
  --prompt-type qa
```

### Production Line Camera (sender device):
```bash
# Send frames from production line camera
python frame_sender.py \
  --analyzer http://192.168.1.50:9090 \
  --rtsp rtsp://prod_line_cam:554/stream \
  --question "Are workers wearing safety helmets?" \
  --interval 60  # Send every minute
```

### Quality Control Camera (sender device):
```bash
# Send frames from QC camera
python frame_sender.py \
  --analyzer http://192.168.1.50:9090 \
  --rtsp rtsp://qc_cam:554/stream \
  --question "Are there any visible defects in the products?" \
  --motion  # Send only when motion detected
```

## Scenario 4: Retail Store Analytics

### Raspberry Pi with overhead camera:
```bash
# Analyze customer behavior
python rtsp_vlm_analyzer.py \
  --rtsp rtsp://overhead_cam:554/stream \
  --default-question "How many people are in the store and what are they doing?" \
  --interval 300  # Analyze every 5 minutes
  --results-dir ./store_analytics
```

## Scenario 5: Smart Home Assistant

### Raspberry Pi with indoor camera:
```bash
# Home monitoring with different questions based on time
python rtsp_vlm_analyzer.py \
  --rtsp rtsp://living_room_cam:554/stream \
  --interval 600  # Every 10 minutes
  --results-dir ./home_monitor

# Custom script to change questions based on time
#!/bin/bash
HOUR=$(date +%H)

if [ $HOUR -ge 6 ] && [ $HOUR -lt 12 ]; then
  QUESTION="Is anyone having breakfast in the kitchen?"
elif [ $HOUR -ge 12 ] && [ $HOUR -lt 18 ]; then
  QUESTION="Are the kids doing their homework?"
elif [ $HOUR -ge 18 ] && [ $HOUR -lt 22 ]; then
  QUESTION="Is the family watching TV together?"
else
  QUESTION="Is everything quiet and normal?"
fi

python rtsp_vlm_analyzer.py \
  --rtsp rtsp://living_room_cam:554/stream \
  --default-question "$QUESTION" \
  --interval 600
```

## Scenario 6: Multi-Camera Surveillance

### Using systemd service (on Raspberry Pi):

Create `/etc/systemd/system/vlm-analyzer.service`:
```ini
[Unit]
Description=Hailo VLM Analyzer Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Hailo-10h_RTSP_VLM
ExecStart=/home/pi/Hailo-10h_RTSP_VLM/venv/bin/python rtsp_vlm_analyzer.py \
  --rtsp rtsp://camera1:554/stream \
  --http-port 8080 \
  --results-dir /var/log/vlm-analyzer \
  --save-frames
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vlm-analyzer
sudo systemctl start vlm-analyzer
sudo systemctl status vlm-analyzer
```

## Scenario 7: Integration with Home Assistant

### Custom component to send frames:

Create `home_assistant_sender.py`:
```python
import requests
import cv2
import time
from datetime import datetime

class HomeAssistantVLM:
    def __init__(self, analyzer_url):
        self.analyzer_url = analyzer_url
    
    def capture_and_analyze(self, camera_entity, question):
        """Capture from Home Assistant camera and send to VLM"""
        # Get camera snapshot (example using REST API)
        snapshot_url = f"http://homeassistant:8123/api/camera_proxy/{camera_entity}"
        headers = {"Authorization": "Bearer YOUR_TOKEN"}
        
        response = requests.get(snapshot_url, headers=headers)
        if response.status_code == 200:
            # Send to VLM analyzer
            vlm_response = requests.post(
                f"{self.analyzer_url}/frame?question={question}",
                data=response.content,
                headers={'Content-Type': 'image/jpeg'}
            )
            return vlm_response.json()
        return None

# Usage in automation
def motion_detected_automation():
    vlm = HomeAssistantVLM("http://raspberry_pi:8080")
    result = vlm.capture_and_analyze(
        "camera.front_door",
        "Who is at the front door?"
    )
    if result and "person" in result.get("response", "").lower():
        # Trigger alert
        pass
```

## Scenario 8: Edge AI Pipeline

### Combine with other Hailo models:

Create `multi_model_pipeline.py`:
```python
import cv2
from hailo_platform import VDevice
from hailo_platform.genai import VLM
import numpy as np

class MultiModelPipeline:
    def __init__(self, vlm_model_path, detection_model_path):
        self.vdevice = VDevice.create()
        self.vlm = VLM(self.vdevice, vlm_model_path)
        # Load other models (object detection, face recognition, etc.)
        # self.detector = Detector(self.vdevice, detection_model_path)
    
    def analyze_frame(self, frame):
        # Step 1: Object detection
        # objects = self.detector.detect(frame)
        
        # Step 2: If interesting objects detected, use VLM
        # if objects and self.is_interesting(objects):
        prompt = [{
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": "Describe the main objects and their activities"}
            ]
        }]
        
        response = self.vlm.generate_all(
            prompt=prompt,
            frames=[self.preprocess_frame(frame)],
            max_generated_tokens=150
        )
        
        return {
            # "objects": objects,
            "description": response
        }
    
    def preprocess_frame(self, frame):
        # Resize and convert for VLM
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return cv2.resize(frame_rgb, (336, 336))
```

## Troubleshooting Examples

### Test connectivity:
```bash
# Test RTSP stream
ffmpeg -i rtsp://camera_ip:554/stream -f null -

# Test HTTP server
curl http://raspberry_pi:8080

# Test frame sending
python frame_sender.py --analyzer http://raspberry_pi:8080 --image test.jpg
```

### Monitor performance:
```bash
# Check Hailo device
hailortcli fw-control identify

# Monitor CPU/GPU usage
htop
nvidia-smi  # If using GPU alongside

# Check logs
tail -f vlm_analyzer.log
```

These examples show the flexibility of the system for various real-world applications. The modular design allows easy adaptation to specific use cases.