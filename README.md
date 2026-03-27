# RTSP VLM Analyzer for Raspberry Pi 5 with Hailo-10H

A complete system for analyzing camera frames using Hailo's Vision Language Model (VLM) on Raspberry Pi 5 with Hailo-10H AI HAT+2.

## Features

### On Raspberry Pi (Analyzer):
- **RTSP Camera Processing**: Connect to RTSP cameras on your local network **with authentication support**
- **HTTP Frame Receiver**: Accept frames from other devices via HTTP
- **Motion Detection**: Automatically analyze frames when motion is detected
- **Configurable Analysis**: Choose between description, Q&A, or custom prompts
- **Results Logging**: Save analysis results as JSON with optional image saving
- **Real-time Processing**: Leverages Hailo-10H NPU for fast VLM inference
- **Simulation Mode**: Test without Hailo hardware

### On Other Devices (Sender):
- **Multiple Sources**: Capture from RTSP cameras (with auth), webcams, screenshots, or files
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
- Optional: `mss` library for screen capture (`pip install mss`)

## Installation

1. **On Raspberry Pi:**
```bash
# Clone the repository
git clone https://github.com/opivankristovi/Hailo-10h_RTSP_VLM
cd Hailo-10h_RTSP_VLM

# Run setup script
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Test Hailo installation
python -c "import hailo_platform; print('Hailo SDK OK')"
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

**With authentication:**
```bash
python rtsp_vlm_analyzer.py --rtsp rtsp://192.168.1.100:554/stream \
  --rtsp-user admin --rtsp-pass password
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

**Test without Hailo hardware (simulation mode):**
```bash
python rtsp_vlm_analyzer.py --rtsp rtsp://192.168.1.100:554/stream --simulate
```

### 2. HTTP Server Mode (Receive Frames from Network)

Start HTTP server on port 8080:
```bash
python rtsp_vlm_analyzer.py --http-port 8080
```

The server will be available at `http://<raspberry_pi_ip>:8080`

### 3. Send Frames from Other Devices

From another computer on the network:

**Send frames from RTSP camera:**
```bash
python frame_sender.py --analyzer http://192.168.1.50:8080 \
  --rtsp rtsp://192.168.1.101:554/stream \
  --question "What objects are in the frame?"
```

**With authentication:**
```bash
python frame_sender.py --analyzer http://192.168.1.50:8080 \
  --rtsp rtsp://192.168.1.101:554/stream \
  --rtsp-user admin --rtsp-pass password \
  --question "Is there anyone in the room?"
```

**Send frames from webcam:**
```bash
python frame_sender.py --analyzer http://192.168.1.50:8080 \
  --webcam 0 \
  --interval 10  # Send every 10 seconds
```

**Send single image:**
```bash
python frame_sender.py --analyzer http://192.168.1.50:8080 \
  --image path/to/image.jpg \
  --question "Describe this image in detail"
```

**Send screenshots:**
```bash
python frame_sender.py --analyzer http://192.168.1.50:8080 \
  --screen \
  --interval 30  # Send screenshot every 30 seconds
```

**Send without motion detection (time-based only):**
```bash
python frame_sender.py --analyzer http://192.168.1.50:8080 \
  --rtsp rtsp://192.168.1.101:554/stream \
  --no-motion \
  --interval 60  # Send every 60 seconds
```

## Configuration Options

### RTSP VLM Analyzer (`rtsp_vlm_analyzer.py`):

**Source Options:**
- `--rtsp URL`: RTSP camera URL
- `--rtsp-user USERNAME`: RTSP username
- `--rtsp-pass PASSWORD`: RTSP password
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

**Testing Options:**
- `--simulate`: Run in simulation mode (no Hailo hardware required)

### Frame Sender (`frame_sender.py`):

**Required:**
- `--analyzer URL`: VLM analyzer URL (e.g., http://192.168.1.50:8080)

**Source (choose one):**
- `--rtsp URL`: RTSP camera URL
- `--webcam ID`: Webcam device ID (0, 1, etc.)
- `--screen`: Capture screenshots
- `--image PATH`: Single image file
- `--video PATH`: Video file

**RTSP Authentication:**
- `--rtsp-user USERNAME`: RTSP username
- `--rtsp-pass PASSWORD`: RTSP password

**Analysis Options:**
- `--question TEXT`: Question to ask about frames
- `--prompt-type TYPE`: "describe", "qa", or "custom" (default: "describe")
- `--interval SECONDS`: Send interval (default: 10)
- `--no-motion`: Disable motion detection (RTSP only)

## Example Scenarios

### Scenario 1: Home Security Monitor with Authentication
```bash
# On Raspberry Pi (connected to security camera)
python rtsp_vlm_analyzer.py \
  --rtsp rtsp://security_cam:554/h264 \
  --rtsp-user admin \
  --rtsp-pass securepassword \
  --motion-threshold 0.05 \
  --default-question "Is there a person or vehicle in the frame?" \
  --save-frames \
  --results-dir ./security_logs
```

### Scenario 2: Multi-Camera Factory Monitoring
```bash
# On Raspberry Pi (central analyzer)
python rtsp_vlm_analyzer.py --http-port 9090 --results-dir ./factory_monitoring

# On Machine 1 (production line camera with auth)
python frame_sender.py --analyzer http://raspberry_pi:9090 \
  --rtsp rtsp://prod_line_cam:554/stream \
  --rtsp-user operator --rtsp-pass factory123 \
  --question "Are workers wearing safety gear?" \
  --interval 60

# On Machine 2 (quality control camera)
python frame_sender.py --analyzer http://raspberry_pi:9090 \
  --rtsp rtsp://qc_cam:554/stream \
  --question "Are there any defects in the products?" \
  --motion
```

### Scenario 3: Wildlife Camera Trap
```bash
# On Raspberry Pi with camera in field
python rtsp_vlm_analyzer.py \
  --rtsp rtsp://trail_cam:554/main \
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

## RTSP Authentication Support

The system supports RTSP authentication in two formats:

### 1. URL with embedded credentials:
```
rtsp://username:password@camera_ip:554/stream
```

### 2. Separate arguments (more secure):
```bash
# Analyzer
python rtsp_vlm_analyzer.py --rtsp rtsp://camera_ip:554/stream --rtsp-user admin --rtsp-pass password

# Frame sender
python frame_sender.py --analyzer http://raspberry_pi:8080 --rtsp rtsp://camera_ip:554/stream --rtsp-user admin --rtsp-pass password
```

**Security Note:** For production use, consider:
- Using environment variables for passwords
- Setting file permissions on scripts
- Using `.netrc` files for credential storage
- Implementing proper secret management

## Performance Notes

- **Hailo-10H Inference**: ~1-2 seconds per analysis (depending on prompt complexity)
- **Frame Resolution**: Automatically resized to 336x336 for VLM input
- **Network Latency**: HTTP frame transfer adds minimal overhead
- **Memory Usage**: VLM model uses ~2GB RAM on Hailo-10H
- **Concurrent Analysis**: Single inference at a time (queue-based processing)

## Troubleshooting

### Common Issues:

1. **RTSP connection failed:**
   - Verify camera URL and credentials
   - Test with VLC: `vlc rtsp://username:password@camera_ip:554/stream`
   - Check network connectivity: `ping camera_ip`
   - Try different OpenCV backends (FFMPEG, GStreamer)

2. **Authentication errors:**
   - Check username/password are correct
   - Some cameras require URL-encoded special characters
   - Try both authentication methods (embedded vs separate args)

3. **VLM model not found:**
   - Check Hailo Model Zoo installation
   - Models auto-download on first run from Hailo servers
   - Manual download: Get HEF file from Hailo Developer Zone

4. **HTTP server not accessible:**
   - Check Raspberry Pi firewall: `sudo ufw allow 8080`
   - Verify IP address: `hostname -I`
   - Test locally: `curl http://127.0.0.1:8080`

5. **Slow inference:**
   - Ensure HailoRT is properly installed
   - Check Hailo-10H is detected: `hailortcli fw-control identify`
   - Reduce `max_generated_tokens` in code for faster responses

### Testing:

Run the test suite to verify installation:
```bash
python test_vlm_system.py
```

Test without Hailo hardware:
```bash
python rtsp_vlm_analyzer.py --rtsp rtsp://test_camera:554/stream --simulate --verbose
```

## Security Considerations

1. **Network Security:**
   - Use separate VLAN for camera network
   - Change default RTSP camera passwords
   - Consider VPN for remote access
   - Use HTTPS for analyzer communication (future enhancement)

2. **Credential Management:**
   - Never hardcode passwords in scripts
   - Use environment variables: `export RTSP_PASS="password"`
   - Consider using `.netrc` or credential managers
   - Set strict file permissions: `chmod 600 config_with_passwords.yaml`

3. **HTTP Server:**
   - Runs on specified port only
   - No authentication (add if needed for production)
   - Limit to local network in firewall
   - Consider adding basic auth or API tokens

4. **Data Privacy:**
   - Analysis results stored locally
   - Frames only saved if `--save-frames` enabled
   - Consider encryption for sensitive applications
   - Regular cleanup of stored frames

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
- Integrate with Home Assistant or other smart home systems

## License

MIT License - See LICENSE file for details.

## Support

- **GitHub Issues**: https://github.com/opivankristovi/Hailo-10h_RTSP_VLM/issues
- **Hailo Community Forum**: https://community.hailo.ai/
- **Raspberry Pi Forums**: https://forums.raspberrypi.com/
- **OpenCV Documentation**: https://docs.opencv.org/

## Acknowledgments

- Hailo AI for the Hailo-10H NPU and VLM models
- Raspberry Pi Foundation for Raspberry Pi 5
- OpenCV community for computer vision libraries
- All open-source contributors

## Repository

**GitHub:** https://github.com/opivankristovi/Hailo-10h_RTSP_VLM

**Features:**
- Complete RTSP VLM analyzer with authentication
- Frame sender for multiple sources
- Simulation mode for testing
- Comprehensive documentation
- Production-ready with error handling
- MIT licensed for open-source use