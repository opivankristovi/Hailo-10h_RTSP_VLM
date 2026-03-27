#!/usr/bin/env python3
"""
RTSP VLM Analyzer - Clean working version with authentication
"""

import argparse
import cv2
import numpy as np
import time
import json
import logging
import sys
import os
from datetime import datetime
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def build_rtsp_url(rtsp_url, username=None, password=None):
    """Build RTSP URL with authentication"""
    if not rtsp_url.startswith("rtsp://"):
        return rtsp_url
        
    if username and password:
        parsed = urlparse(rtsp_url)
        auth_string = f"{username}:{password}"
        new_netloc = f"{auth_string}@{parsed.netloc}"
        new_url = f"rtsp://{new_netloc}{parsed.path}"
        if parsed.query:
            new_url += f"?{parsed.query}"
        return new_url
    return rtsp_url

class RTSPCamera:
    """Simple RTSP camera handler with authentication"""
    
    def __init__(self, rtsp_url, username=None, password=None):
        self.rtsp_url = rtsp_url
        self.username = username
        self.password = password
        self.cap = None
        
    def connect(self):
        """Connect to RTSP stream"""
        full_url = build_rtsp_url(self.rtsp_url, self.username, self.password)
        logger.info(f"Connecting to RTSP: {full_url}")
        
        # Try different backends
        backends = [cv2.CAP_FFMPEG, cv2.CAP_GSTREAMER, cv2.CAP_ANY]
        
        for backend in backends:
            try:
                self.cap = cv2.VideoCapture(full_url, backend)
                if self.cap and self.cap.isOpened():
                    logger.info(f"Connected using backend: {backend}")
                    return True
            except:
                continue
        
        logger.error("Failed to connect to RTSP stream")
        return False
    
    def get_frame(self):
        """Get a frame from the camera"""
        if not self.cap or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None
    
    def get_stream_info(self):
        """Get stream information"""
        if not self.cap:
            return None
        
        info = {
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": self.cap.get(cv2.CAP_PROP_FPS)
        }
        return info
    
    def disconnect(self):
        """Disconnect from camera"""
        if self.cap:
            self.cap.release()
            self.cap = None

class VLMSimulator:
    """Simulate VLM analysis for testing"""
    
    def __init__(self):
        self.analysis_count = 0
    
    def analyze(self, frame, question=None):
        """Simulate VLM analysis"""
        self.analysis_count += 1
        
        # Simulate processing time
        time.sleep(1.5)
        
        # Generate response based on question
        if question:
            if "person" in question.lower():
                response = "I detect one person in the frame."
            elif "color" in question.lower():
                response = "The image has various colors with good contrast."
            elif "object" in question.lower():
                response = "There are several objects visible in the scene."
            else:
                response = "The image shows a scene with good visibility."
        else:
            response = "This is a simulated analysis of the image."
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "question": question or "Describe this image",
            "response": response,
            "inference_time": 1.5,
            "frame_size": f"{frame.shape[1]}x{frame.shape[0]}",
            "analysis_number": self.analysis_count
        }

def main():
    parser = argparse.ArgumentParser(
        description="RTSP VLM Analyzer with Authentication Support"
    )
    
    parser.add_argument("--rtsp", required=True, help="RTSP camera URL")
    parser.add_argument("--rtsp-user", help="RTSP username")
    parser.add_argument("--rtsp-pass", help="RTSP password")
    parser.add_argument("--question", default="What do you see in this image?", help="Question for analysis")
    parser.add_argument("--interval", type=int, default=10, help="Analysis interval in seconds")
    parser.add_argument("--output-dir", default="./results", help="Output directory for results")
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("RTSP VLM ANALYZER")
    print("="*60)
    print(f"Camera: {args.rtsp}")
    if args.rtsp_user:
        print(f"Username: {args.rtsp_user}")
    print(f"Question: {args.question}")
    print(f"Interval: {args.interval} seconds")
    print(f"Output: {args.output_dir}")
    print("="*60)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize camera
    camera = RTSPCamera(args.rtsp, args.rtsp_user, args.rtsp_pass)
    
    if not camera.connect():
        print("\n✗ Failed to connect to camera")
        return
    
    # Get stream info
    info = camera.get_stream_info()
    if info:
        print(f"\n✓ Camera connected: {info['width']}x{info['height']} @ {info['fps']:.1f} FPS")
    
    # Initialize VLM simulator
    vlm = VLMSimulator()
    
    print("\nStarting analysis loop...")
    print("Press Ctrl+C to stop\n")
    
    try:
        analysis_count = 0
        last_analysis = 0
        
        while True:
            current_time = time.time()
            
            # Check if it's time for analysis
            if current_time - last_analysis >= args.interval:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Capturing frame...")
                
                # Get frame
                frame = camera.get_frame()
                if frame is None:
                    print("  ✗ Failed to capture frame")
                    time.sleep(1)
                    continue
                
                print(f"  ✓ Frame captured: {frame.shape[1]}x{frame.shape[0]}")
                
                # Analyze frame
                print(f"  Analyzing with VLM...")
                result = vlm.analyze(frame, args.question)
                
                # Save frame
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                frame_file = os.path.join(args.output_dir, f"frame_{timestamp}.jpg")
                cv2.imwrite(frame_file, frame)
                
                # Save result
                result_file = os.path.join(args.output_dir, f"analysis_{timestamp}.json")
                with open(result_file, 'w') as f:
                    json.dump(result, f, indent=2)
                
                print(f"  ✓ Analysis complete: {result['response'][:50]}...")
                print(f"  ✓ Files saved: {os.path.basename(frame_file)}, {os.path.basename(result_file)}")
                
                analysis_count += 1
                last_analysis = current_time
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\nStopping analyzer...")
    finally:
        camera.disconnect()
        print(f"\n✓ Analyzer stopped")
        print(f"  Total analyses: {analysis_count}")
        print(f"  Results saved in: {args.output_dir}")
        print("="*60)

if __name__ == "__main__":
    main()