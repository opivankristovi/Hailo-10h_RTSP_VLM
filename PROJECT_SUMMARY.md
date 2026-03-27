# Hailo-10h_RTSP_VLM Project Summary

## Project Overview
A complete edge AI system for real-time camera frame analysis using Hailo's Vision Language Model (VLM) on Raspberry Pi 5 with Hailo-10H AI HAT+2 accelerator.

## Repository
**GitHub:** https://github.com/opivankristovi/Hailo-10h_RTSP_VLM

## Project Structure
```
Hailo-10h_RTSP_VLM/
├── rtsp_vlm_analyzer.py     # Main analyzer (runs on Raspberry Pi)
├── frame_sender.py          # Frame sender (runs on other devices)
├── test_vlm_system.py       # Test suite
├── setup.sh                 # Installation script
├── requirements.txt         # Python dependencies
├── README.md               # Comprehensive documentation
├── LICENSE                 # MIT License
├── .gitignore             # Git ignore rules
├── examples/              # Usage examples
│   └── example_usage.md
└── PROJECT_SUMMARY.md     # This file
```

## Key Features

### 1. **Multi-Source Frame Capture**
- Direct RTSP camera connections
- HTTP server for network frame reception
- Support for webcams, screenshots, video files
- Motion detection and time-based triggering

### 2. **Hailo-10H Optimized VLM Inference**
- Uses Qwen2-VL-2B-Instruct model
- Hardware-accelerated on Hailo-10H NPU
- ~1-2 second inference time per frame
- Automatic model downloading

### 3. **Flexible Analysis Modes**
- **Description**: "Describe this image in detail"
- **Q&A**: Answer specific questions about frames
- **Custom**: User-defined prompts
- Configurable parameters (temperature, tokens, etc.)

### 4. **Network Architecture**
```
[Camera Sources] -> [Frame Sender] -> [Network] -> [Raspberry Pi 5]
  RTSP Cameras    (Linux/Windows)     (LAN/WAN)   (Hailo-10H VLM)
  Webcams                                              ↓
  Screenshots                                    [VLM Analyzer]
  Files                                                ↓
                                                [JSON Results + Images]
```

### 5. **Production-Ready Features**
- Proper error handling and logging
- Resource management (VLM cleanup)
- Configurable via command-line arguments
- Results saved as JSON with timestamps
- Optional frame saving for audit trails

## Technical Specifications

### Hardware Requirements
- **Primary**: Raspberry Pi 5 8GB + Hailo-10H AI HAT+2
- **Secondary**: Any device with Python for frame sending
- **Network**: LAN connectivity between devices
- **Storage**: SD card/SSD for results storage

### Software Dependencies
- **Raspberry Pi**: HailoRT SDK v5.2.0+, Python 3.10+, OpenCV, NumPy
- **Other Devices**: Python 3.8+, OpenCV, requests (optional: mss for screenshots)

### Performance Metrics
- **Inference Time**: 1-2 seconds per analysis
- **Frame Rate**: 30 FPS capture, configurable analysis rate
- **Memory**: ~2GB for VLM model on Hailo-10H
- **Network**: Minimal overhead for HTTP frame transfer

## Use Case Scenarios

### 1. **Security & Surveillance**
- Motion-triggered person/vehicle detection
- 24/7 monitoring with alerting
- Multi-camera support via network

### 2. **Industrial Automation**
- Quality control inspection
- Safety compliance monitoring
- Production line analytics

### 3. **Research & Environmental**
- Wildlife observation
- Traffic monitoring
- Retail analytics

### 4. **Smart Home**
- Occupancy detection
- Activity monitoring
- Elderly/child care

## Getting Started

### Quick Start (Raspberry Pi)
```bash
# Clone repository
git clone https://github.com/opivankristovi/Hailo-10h_RTSP_VLM
cd Hailo-10h_RTSP_VLM

# Run setup
./setup.sh

# Test with RTSP camera
python rtsp_vlm_analyzer.py --rtsp rtsp://camera_ip:554/stream
```

### Quick Start (Other Devices)
```bash
# Send frames to Raspberry Pi
python frame_sender.py --analyzer http://raspberry_pi_ip:8080 --image test.jpg
```

## Development Status

### ✅ Complete
- Core analyzer with RTSP and HTTP support
- Frame sender for multiple sources
- Comprehensive error handling
- Results logging and saving
- Test suite
- Documentation

### 🔄 Planned Enhancements
- Web dashboard for monitoring
- MQTT integration for IoT
- Database storage for results
- Alerting system (email, SMS, etc.)
- Docker containerization
- REST API for integration

## Project Value Proposition

### For Developers
- Open-source MIT license
- Well-documented code
- Modular architecture
- Easy to extend and customize

### For Businesses
- Cost-effective edge AI solution
- No cloud dependency (privacy)
- Scalable from single to multi-camera
- Production-ready reliability

### For Researchers
- Real-world VLM deployment example
- Performance benchmarking data
- Edge AI case study
- Extensible for custom applications

## Contributing
The project is open for contributions. Areas of interest:
- Additional camera source integrations
- Performance optimizations
- New VLM model support
- Integration with other AI frameworks

## License
MIT License - Free for commercial and personal use.

## Contact
- **GitHub**: @opivankristovi
- **Repository**: https://github.com/opivankristovi/Hailo-10h_RTSP_VLM
- **Issues**: Use GitHub Issues for bugs and feature requests

## Acknowledgments
- Hailo AI for the Hailo-10H NPU and VLM models
- Raspberry Pi Foundation for Raspberry Pi 5
- OpenCV community for computer vision libraries
- All open-source contributors