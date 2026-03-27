#!/bin/bash
# Setup script for Hailo-10h_RTSP_VLM project
# Run this on Raspberry Pi 5 with Hailo-10H AI HAT+2

set -e

echo "========================================="
echo "Hailo-10h_RTSP_VLM Project Setup"
echo "========================================="

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi with Hailo-10H"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python version
echo "Checking Python version..."
python3 --version

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for Hailo dependencies
echo "Checking Hailo dependencies..."
if ! python3 -c "import hailo_platform" 2>/dev/null; then
    echo "Warning: hailo_platform not found in Python path"
    echo "Please install Hailo SDK from: https://hailo.ai/developer-zone/"
    echo ""
    echo "Typical installation steps:"
    echo "1. Download HailoRT from Developer Zone"
    echo "2. Install: sudo dpkg -i hailo_rt_*.deb"
    echo "3. Install Python bindings: pip install hailo-platform"
fi

# Check for VLM model
echo "Checking for VLM model..."
MODEL_PATH="/usr/share/hailo-ollama/models/blob/Qwen2-VL-2B-Instruct.hef"
if [ ! -f "$MODEL_PATH" ]; then
    echo "VLM model not found at: $MODEL_PATH"
    echo "The model will be auto-downloaded on first run, or you can:"
    echo "1. Download from Hailo Developer Zone"
    echo "2. Place in: /usr/share/hailo-ollama/models/blob/"
fi

# Make scripts executable
echo "Making scripts executable..."
chmod +x rtsp_vlm_analyzer.py frame_sender.py test_vlm_system.py

# Create results directory
echo "Creating results directory..."
mkdir -p results

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "To activate virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "To test the system:"
echo "  python test_vlm_system.py"
echo ""
echo "To run RTSP analyzer:"
echo "  python rtsp_vlm_analyzer.py --rtsp rtsp://camera_ip:554/stream"
echo ""
echo "To run HTTP server for network frames:"
echo "  python rtsp_vlm_analyzer.py --http-port 8080"
echo ""
echo "Documentation: See README.md for detailed instructions"