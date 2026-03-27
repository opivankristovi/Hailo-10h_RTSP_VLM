#!/usr/bin/env python3
"""
Frame Sender for RTSP VLM Analyzer

This script captures frames from various sources and sends them to the
Raspberry Pi running the VLM analyzer via HTTP.

Features:
1. Capture from RTSP cameras (with authentication)
2. Capture from USB/webcam
3. Capture from video files
4. Capture from screen/screenshot
5. Send with custom questions/prompts
6. Automatic capture on motion detection

Author: ClawBot
Date: 2026-03-27
"""

import argparse
import cv2
import numpy as np
import time
import requests
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import threading
import queue
from urllib.parse import urlparse

def build_rtsp_url(rtsp_url, username=None, password=None):
    """Build RTSP URL with authentication if provided"""
    if not rtsp_url.startswith("rtsp://"):
        return rtsp_url
        
    if username and password:
        # Parse the URL to insert credentials
        parsed = urlparse(rtsp_url)
        auth_string = f"{username}:{password}"
        new_netloc = f"{auth_string}@{parsed.netloc}"
        new_url = f"rtsp://{new_netloc}{parsed.path}"
        if parsed.query:
            new_url += f"?{parsed.query}"
        return new_url
    return rtsp_url

def capture_rtsp_frames(rtsp_url, username, password, frame_queue, stop_event, motion_detection=True, send_interval=30):
    """Capture frames from RTSP stream"""
    full_url = build_rtsp_url(rtsp_url, username, password)
    print(f"Starting RTSP capture from: {full_url}")
    
    # Try different OpenCV backends
    backends = [
        cv2.CAP_FFMPEG,
        cv2.CAP_GSTREAMER,
        cv2.CAP_ANY
    ]
    
    cap = None
    for backend in backends:
        cap = cv2.VideoCapture(full_url, backend)
        if cap and cap.isOpened():
            print(f"Connected using backend: {backend}")
            break
    
    if not cap or not cap.isOpened():
        print(f"Failed to open RTSP stream: {full_url}")
        return
    
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
    
    last_frame = None
    frame_count = 0
    last_sent_time = 0
    
    while not stop_event.is_set():
        try:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read RTSP frame, reconnecting...")
                time.sleep(1)
                cap.release()
                # Try to reconnect
                for backend in backends:
                    cap = cv2.VideoCapture(full_url, backend)
                    if cap and cap.isOpened():
                        print(f"Reconnected using backend: {backend}")
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        break
                if not cap or not cap.isOpened():
                    print("Failed to reconnect")
                    break
                continue
            
            frame_count += 1
            current_time = time.time()
            
            # Detect motion if enabled
            motion_detected = False
            if motion_detection and last_frame is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                last_gray = cv2.cvtColor(last_frame, cv2.COLOR_BGR2GRAY)
                
                diff = cv2.absdiff(last_gray, gray)
                _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                
                motion_pixels = np.sum(thresh > 0)
                motion_percent = motion_pixels / thresh.size
                
                if motion_percent > 0.05:  # 5% motion threshold
                    motion_detected = True
            
            last_frame = frame.copy()
            
            # Send frame on motion or at interval
            should_send = False
            if motion_detection and motion_detected:
                should_send = True
                print(f"Motion detected - sending frame {frame_count}")
            elif current_time - last_sent_time >= send_interval:
                should_send = True
                print(f"Interval reached - sending frame {frame_count}")
            
            if should_send:
                frame_queue.put(("rtsp", frame, {
                    "source": rtsp_url,
                    "frame_number": frame_count,
                    "motion_detected": motion_detected,
                    "timestamp": datetime.now().isoformat()
                }))
                last_sent_time = current_time
            
            time.sleep(0.033)  # ~30 FPS
            
        except Exception as e:
            print(f"RTSP capture error: {e}")
            time.sleep(1)
    
    if cap:
        cap.release()
    print("RTSP capture stopped")

def capture_webcam_frames(device_id, frame_queue, stop_event, send_interval=10):
    """Capture frames from webcam"""
    print(f"Starting webcam capture from device: {device_id}")
    
    cap = cv2.VideoCapture(device_id)
    
    frame_count = 0
    last_sent_time = 0
    
    while not stop_event.is_set():
        try:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read webcam frame")
                time.sleep(1)
                continue
            
            frame_count += 1
            current_time = time.time()
            
            # Send at interval
            if current_time - last_sent_time >= send_interval:
                frame_queue.put(("webcam", frame, {
                    "device": device_id,
                    "frame_number": frame_count,
                    "timestamp": datetime.now().isoformat()
                }))
                last_sent_time = current_time
                print(f"Sent webcam frame {frame_count}")
            
            time.sleep(0.033)  # ~30 FPS
            
        except Exception as e:
            print(f"Webcam capture error: {e}")
            time.sleep(1)
    
    cap.release()
    print("Webcam capture stopped")

def capture_screen(frame_queue, stop_event, send_interval=10):
    """Capture screenshots (requires mss library)"""
    try:
        from mss import mss
    except ImportError:
        print("Install mss library: pip install mss")
        return
    
    print("Starting screen capture")
    
    with mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        
        frame_count = 0
        last_sent_time = 0
        
        while not stop_event.is_set():
            try:
                # Capture screen
                screenshot = sct.grab(monitor)
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                frame_count += 1
                current_time = time.time()
                
                # Send at interval
                if current_time - last_sent_time >= send_interval:
                    frame_queue.put(("screen", frame, {
                        "monitor": "primary",
                        "frame_number": frame_count,
                        "timestamp": datetime.now().isoformat()
                    }))
                    last_sent_time = current_time
                    print(f"Sent screenshot {frame_count}")
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                print(f"Screen capture error: {e}")
                time.sleep(1)
    
    print("Screen capture stopped")

def send_frame_to_analyzer(frame, metadata, analyzer_url, question=None, prompt_type="describe"):
    """Send frame to VLM analyzer"""
    try:
        # Encode frame as JPEG
        _, img_encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        
        # Prepare URL with query parameters
        url = f"{analyzer_url.rstrip('/')}/frame"
        params = []
        if question:
            params.append(f"question={requests.utils.quote(question)}")
        if prompt_type:
            params.append(f"type={prompt_type}")
        
        if params:
            url += "?" + "&".join(params)
        
        # Send POST request
        response = requests.post(
            url,
            data=img_encoded.tobytes(),
            headers={'Content-Type': 'image/jpeg'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Frame sent successfully: {result.get('status', 'OK')}")
            return True
        else:
            print(f"✗ Failed to send frame: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"✗ Connection error: Cannot connect to {analyzer_url}")
        return False
    except Exception as e:
        print(f"✗ Error sending frame: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Frame Sender for VLM Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send frames from RTSP camera
  python frame_sender.py --analyzer http://192.168.1.50:8080 --rtsp rtsp://192.168.1.100:554/stream
  
  # Send frames from RTSP camera with authentication
  python frame_sender.py --analyzer http://192.168.1.50:8080 --rtsp rtsp://192.168.1.100:554/stream --rtsp-user admin --rtsp-pass password
  
  # Send frames from webcam with custom question
  python frame_sender.py --analyzer http://192.168.1.50:8080 --webcam 0 --question "What objects are visible?"
  
  # Send screenshots every 30 seconds
  python frame_sender.py --analyzer http://192.168.1.50:8080 --screen --interval 30
  
  # Send single image file
  python frame_sender.py --analyzer http://192.168.1.50:8080 --image path/to/image.jpg
  
  # Send without motion detection (time-based only)
  python frame_sender.py --analyzer http://192.168.1.50:8080 --rtsp rtsp://192.168.1.100:554/stream --no-motion --interval 60
        """
    )
    
    # Destination
    parser.add_argument("--analyzer", required=True, help="URL of VLM analyzer (e.g., http://192.168.1.50:8080)")
    
    # Source options (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--rtsp", help="RTSP camera URL")
    source_group.add_argument("--webcam", type=int, help="Webcam device ID (0, 1, etc.)")
    source_group.add_argument("--screen", action="store_true", help="Capture screenshots")
    source_group.add_argument("--image", help="Single image file to send")
    source_group.add_argument("--video", help="Video file to process")
    
    # RTSP authentication
    parser.add_argument("--rtsp-user", type=str, help="RTSP username")
    parser.add_argument("--rtsp-pass", type=str, help="RTSP password")
    
    # Analysis options
    parser.add_argument("--question", help="Question to ask about the frame")
    parser.add_argument("--prompt-type", choices=["describe", "qa", "custom"], default="describe", help="Prompt type")
    parser.add_argument("--interval", type=int, default=10, help="Send interval in seconds (default: 10)")
    parser.add_argument("--no-motion", action="store_true", help="Disable motion detection (RTSP only)")
    
    args = parser.parse_args()
    
    # Create frame queue and stop event
    frame_queue = queue.Queue()
    stop_event = threading.Event()
    
    # Start appropriate capture thread
    capture_thread = None
    
    if args.rtsp:
        capture_thread = threading.Thread(
            target=capture_rtsp_frames,
            args=(args.rtsp, args.rtsp_user, args.rtsp_pass, frame_queue, stop_event, not args.no_motion, args.interval),
            daemon=True
        )
    elif args.webcam is not None:
        capture_thread = threading.Thread(
            target=capture_webcam_frames,
            args=(args.webcam, frame_queue, stop_event, args.interval),
            daemon=True
        )
    elif args.screen:
        capture_thread = threading.Thread(
            target=capture_screen,
            args=(frame_queue, stop_event, args.interval),
            daemon=True
        )
    
    # Start capture thread if needed
    if capture_thread:
        capture_thread.start()
        source_desc = args.rtsp or f"webcam {args.webcam}" or "screen"
        print(f"Capture started for {source_desc}")
        if args.rtsp and (args.rtsp_user or args.rtsp_pass):
            print(f"Using authentication: {args.rtsp_user or 'N/A'}")
    
    # Handle single image
    if args.image:
        print(f"Sending single image: {args.image}")
        frame = cv2.imread(args.image)
        if frame is not None:
            success = send_frame_to_analyzer(
                frame,
                {"source": "image", "filename": args.image},
                args.analyzer,
                args.question,
                args.prompt_type
            )
            if success:
                print("✓ Image sent successfully")
            else:
                print("✗ Failed to send image")
        else:
            print(f"✗ Failed to load image: {args.image}")
        return
    
    # Handle video file
    if args.video:
        print(f"Processing video file: {args.video}")
        cap = cv2.VideoCapture(args.video)
        frame_count = 0
        sent_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Send every 30th frame or at 10-second intervals
            if frame_count % 30 == 0:
                print(f"Sending frame {frame_count} from video")
                success = send_frame_to_analyzer(
                    frame,
                    {"source": "video", "filename": args.video, "frame_number": frame_count},
                    args.analyzer,
                    args.question,
                    args.prompt_type
                )
                if success:
                    sent_count += 1
                time.sleep(1)  # Don't flood the analyzer
        
        cap.release()
        print(f"Video processing complete. Sent {sent_count} frames.")
        return
    
    # Process frames from queue
    print("\n" + "="*60)
    print("FRAME SENDER RUNNING")
    print("="*60)
    print(f"Analyzer: {args.analyzer}")
    if args.question:
        print(f"Question: {args.question}")
    print(f"Prompt Type: {args.prompt_type}")
    print(f"Send Interval: {args.interval} seconds")
    if args.rtsp:
        print(f"Motion Detection: {'Enabled' if not args.no_motion else 'Disabled'}")
    print("="*60)
    print("Press Ctrl+C to stop\n")
    
    sent_count = 0
    error_count = 0
    
    try:
        while True:
            try:
                # Get frame from queue
                source_type, frame, metadata = frame_queue.get(timeout=1)
                
                print(f"Sending frame from {source_type} (frame {metadata.get('frame_number', 'N/A')})")
                
                # Send to analyzer
                success = send_frame_to_analyzer(
                    frame,
                    metadata,
                    args.analyzer,
                    args.question,
                    args.prompt_type
                )
                
                if success:
                    sent_count += 1
                else:
                    error_count += 1
                
                frame_queue.task_done()
                
            except queue.Empty:
                # No frames in queue, continue
                pass
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping frame sender...")
    finally:
        stop_event.set()
        if capture_thread:
            capture_thread.join(timeout=2)
        
        print("\n" + "="*60)
        print("FRAME SENDER STOPPED")
        print("="*60)
        print(f"Frames sent successfully: {sent_count}")
        print(f"Failed sends: {error_count}")
        print("="*60)

if __name__ == "__main__":
    main()