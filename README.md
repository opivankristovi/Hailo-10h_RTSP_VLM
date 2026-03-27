# RTSP VLM Analyzer for Raspberry Pi 5 with Hailo-10H

A complete system for analyzing camera frames using Hailo's Vision Language Model (VLM) on Raspberry Pi 5 with Hailo-10H AI HAT+2.

## Features

### On Raspberry Pi (Analyzer):
- **RTSP Camera Processing**: Connect to RTSP cameras on your local network
- **HTTP Frame Receiver**: Accept frames from other devices via HTTP
- **Motion Detection**: Automatically analyze frames when motion is detected
- **Configurable Analysis**: Choose between description, Q&A, or custom prompts
- **Results Logging**: Save analysis results as JSON with optional image saving
- **Real-time Processing**: Leverages Hailo-10H NPU for fast VLM inference

### On Other Devices (Sender):
- **Multiple Sources**: Capture from RTSP cameras, webcams, screenshots, or files
- **Network Integration**: Send frames to Raspberry Pi over LAN
- **Flexible Scheduling**: Time-based or motion-triggered capture
- **Custom Questions**: Send frames with specific questions for analysis

## System Architecture

```
[Camera Sources] -> [Frame Sender] -> [Network] -> [Raspberry Pi 5]
      RTSP        (other devices)      (LAN)      (Hailo-10H VLM)
    Webcam                                                 ↓
    Screen                                           [VLM Analyzer]
    Files                                                 ↓
                                                   [Analysis Results]
```

## Prerequisites

### Raspberry Pi 5 with Hailo-10H:
- Raspberry Pi 5 8GB with AI HAT+2
- HailoRT SDK installed (v5.2.0+)
- Hailo Model Zoo GenAI installed
- Python 3.10+ with OpenCV, NumPy
- VLM model (Qwen2-VL-2B-Instruct) - auto-downloaded on first run

### Other Devices (optional):
- Python 3.8+
- OpenCV, requests library
- Network access to Raspberry Pi

## Installation

1. **On Raspberry Pi:**
```bash
# Clone or copy the scripts
git clone <repository-url>  # or copy the .py files

# Install Python dependencies
pip install opencv-python numpy requests

# Test Hailo VLM is working
python -m hailo_apps.python.gen_ai_apps.simple_vlm_chat.simple_vlm_chat
```

2. **On Other Devices (optional):**
```bash
pip install opencv-python numpy requests mss
```

## Usage

### 1. Basic RTSP Analysis on Raspberry Pi

Analyze frames from an RTSP camera with motion detection:
```bash
python rtsp_vlm_analyzer.py --rtsp rtsp://192.168.1.100:554/stream
```

Analyze every 30 seconds (disable motion detection):
```bash
python rtsp_vlm_analyzer.py --rtsp rtsp://192.168.1.100:554/stream --interval 30 --no-motion
```

With custom question and save frames:
```bash
python rtsp_vlm_analyzer.py --rtsp rtsp://192.168.1.100:554/stream \
  --default-question "How many people are visible?" \
  --save-frames \
  --results-dir ./camera_analysis
```

### 2. HTTP Server Mode (Receive Frames from Network)

Start HTTP server on port 8080:
```bash
python rtsp_vlm_analyzer.py --http-port 8080
```

The server will be available at `http://<raspberry_pi_ip>:8080`

### 3. Send Frames from Other Devices

From another computer on the network:

Send frames from RTSP camera:
```bash
python frame_sender.py --analyzer http://192.168.1.50:8080 \
  --rtsp rtsp://192.168.1.101:554/stream \
  --question "What objects are in the frame?"
```

Send frames from webcam:
```bash
python frame_sender.py --analyzer http://192.168.1.50:8080 \
  --webcam 0 \
  --interval 10  # Send every 10 seconds
```

Send single image:
```bash
python frame_sender.py --analyzer http://192.168.1.50:8080 \
  --image path/to/image.jpg \
  --question "Describe this image in detail"
```

Send screenshots:
```bash
python frame_sender.py --analyzer http://192.168.1.50:8080 \
  --screen \
  --interval 30  # Send screenshot every 30 seconds
```

## Configuration Options

### RTSP VLM Analyzer (`rtsp_vlm_analyzer.py`):

**Source Options:**
- `--rtsp URL`: RTSP camera URL
- `--http-port PORT`: HTTP server port (default: 8080)

**Analysis Options:**
- `--interval SECONDS`: Analysis interval (default: 10)
- `--no-motion`: Disable motion detection
- `--motion-threshold VALUE`: Motion sensitivity (0.0-1.0, default: 0.1)
- `--default-question TEXT`: Default question for analysis
- `--prompt-type TYPE`: "describe", "qa", or "custom" (default: "describe")

**Model Options:**
- `--model PATH`: Path to VLM HEF model file
- `--model-name NAME`: VLM model name (default: "qwen2-vl-2b-instruct")

**Output Options:**
- `--results-dir PATH`: Directory for results (default: "./results")
- `--save-frames`: Save analyzed frames as images
- `--verbose`: Enable detailed logging

### Frame Sender (`frame_sender.py`):

**Required:**
- `--analyzer URL`: VLM analyzer URL (e.g., http://192.168.1.50:8080)

**Source (choose one):**
- `--rtsp URL`: RTSP camera URL
- `--webcam ID`: Webcam device ID (0, 1, etc.)
- `--screen`: Capture screenshots
- `--image PATH`: Single image file
- `--video PATH`: Video file

**Analysis Options:**
- `--question TEXT`: Question to ask about frames
- `--prompt-type TYPE`: "describe", "qa", or "custom" (default: "describe")
- `--interval SECONDS`: Capture interval (default: 10)
- `--motion`: Enable motion detection (RTSP only)

## Example Scenarios

### Scenario 1: Home Security Monitor
```bash
# On Raspberry Pi (connected to security camera)
python rtsp_vlm_analyzer.py --rtsp rtsp://security_cam:554/h264 \
  --motion-threshold 0.05 \
  --default-question "Is there a person or vehicle in the frame?" \
  --save-frames \
  --results-dir ./security_logs
```

### Scenario 2: Multi-Camera Factory Monitoring
```bash
# On Raspberry Pi (central analyzer)
python rtsp_vlm_analyzer.py --http-port 8080 --results-dir ./factory_monitoring

# On Machine 1 (production line camera)
python frame_sender.py --analyzer http://raspberry_pi:8080 \
  --rtsp rtsp://prod_line_cam:554/stream \
  --question "Are workers wearing safety gear?" \
  --interval 60

# On Machine 2 (quality control camera)
python frame_sender.py --analyzer http://raspberry_pi:8080 \
  --rtsp rtsp://qc_cam:554/stream \
  --question "Are there any defects in the products?" \
  --motion
```

### Scenario 3: Wildlife Camera Trap
```bash
# On Raspberry Pi with camera in field
python rtsp_vlm_analyzer.py --rtsp rtsp://trail_cam:554/main \
  --motion-threshold 0.02 \
  --default-question "What animals are visible and what are they doing?" \
  --save-frames \
  --results-dir ./wildlife_observations
```

## Output Format

Analysis results are saved as JSON files in the results directory:

```json
{
  "success": true,
  "timestamp": "2026-03-27T14:30:45.123456",
  "prompt_type": "describe",
  "question": "How many people in the image?",
  "response": "There are two people in the image. One is sitting at a desk...",
  "inference_time": 1.23,
  "frame_size": "640x480",
  "total_inferences": 42,
  "source": "rtsp",
  "source_url": "rtsp://192.168.1.100:554/stream",
  "frame_number": 125,
  "motion_detected": true
}
```

## Performance Notes

- **Hailo-10H Inference**: ~1-2 seconds per analysis (depending on prompt complexity)
- **Frame Resolution**: Automatically resized to 336x336 for VLM input
- **Network Latency**: HTTP frame transfer adds minimal overhead
- **Memory Usage**: VLM model uses ~2GB RAM on Hailo-10H
- **Concurrent Analysis**: Single inference at a time (queue-based processing)

## Troubleshooting

### Common Issues:

1. **VLM model not found:**
   - Check Hailo Model Zoo installation
   - Models auto-download on first run from Hailo servers
   - Manual download: Get HEF file from Hailo Developer Zone

2. **RTSP connection failed:**
   - Verify camera URL and credentials
   - Test with VLC: `vlc rtsp://camera_ip:554/stream`
   - Check network connectivity

3. **HTTP server not accessible:**
   - Check Raspberry Pi firewall: `sudo ufw allow 8080`
   - Verify IP address: `hostname -I`
   - Test locally: `curl http://127.0.0.1:8080`

4. **Slow inference:**
   - Ensure HailoRT is properly installed
   - Check Hailo-10H is detected: `hailortcli fw-control identify`
   - Reduce `max_generated_tokens` in code for faster responses

### Testing:

Run the test suite to verify installation:
```bash
python test_vlm_system.py
```

## Security Considerations

1. **Network Security:**
   - Use separate VLAN for camera network
   - Change default RTSP camera passwords
   - Consider VPN for remote access

2. **HTTP Server:**
   - Runs on specified port only
   - No authentication (add if needed for production)
   - Limit to local network in firewall

3. **Data Privacy:**
   - Analysis results stored locally
   - Frames only saved if `--save-frames` enabled
   - Consider encryption for sensitive applications

## Extending the System

### Custom Prompts:
Modify the prompt templates in `VLMProcessor` class for specialized tasks.

### Additional Sources:
Add new capture methods to `FrameCapture` or `frame_sender.py`.

### Integration:
- Connect to MQTT for IoT integration
- Add database storage for results
- Implement web dashboard for monitoring
- Add alerting system for specific detections

## License

MIT License - See LICENSE file for details.

## Support

- Hailo Community Forum: https://community.hailo.ai/
- Raspberry Pi Forums: https://forums.raspberrypi.com/
- OpenCV Documentation: https://docs.opencv.org/

## Acknowledgments

- Hailo AI for the Hailo-10H NPU and VLM models
- Raspberry Pi Foundation for Raspberry Pi 5
- OpenCV community for computer vision libraries