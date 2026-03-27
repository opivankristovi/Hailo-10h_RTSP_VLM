#!/usr/bin/env python3
"""
Frame Sender for RTSP VLM Analyzer

This script captures frames from various sources and sends them to the
Raspberry Pi running the VLM analyzer via HTTP.

Features:
1. Capture from RTSP cameras
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

def capture_rtsp_frames(rtsp_url, frame_queue, stop_event):
    """Capture frames from RTSP stream"""
    print(f"Starting RTSP capture from: {rtsp_url}")
    
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
    
    last_frame = None
    frame_count = 0
    
    while not stop_event.is_set():
        try:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read RTSP frame, reconnecting...")
                time.sleep(1)
                cap.release()
                cap = cv2.VideoCapture(rtsp_url)
                continue
            
            frame_count += 1
            
            # Detect motion
            motion_detected = False
            if last_frame is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                last_gray = cv2.cvtColor(last_frame, cv2.COLOR_BGR2GRAY)
                
                diff = cv2.absdiff(last_gray, gray)
                _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                
                motion_pixels = np.sum(thresh > 0)
                motion_percent = motion_pixels / thresh.size
                
                if motion_percent > 0.05:  # 5% motion threshold
                    motion_detected = True
            
            last_frame = frame.copy()
            
            if motion_detected or frame_count % 30 == 0:  # Send every 30 frames or on motion
                frame_queue.put(("rtsp", frame, {
                    "source": rtsp_url,
                    "frame_number": frame_count,
                    "motion_detected": motion_detected
                }))
            
            time.sleep(0.033)  ~30 FPS
            
        except Exception as e:
            print(f"RTSP capture error: {e}")
            time.sleep(1)
    
    cap.release()
    print("RTSP capture stopped")

def capture_webcam_frames(device_id, frame_queue, stop_event):
    """Capture frames from webcam"""
    print(f"Starting webcam capture from device: {device_id}")
    
    cap = cv2.VideoCapture(device_id)
    
    frame_count = 0
    last_capture_time = 0
    
    while not stop_event.is_set():
        try:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read webcam frame")
                time.sleep(1)
                continue
            
            frame_count += 1
            current_time = time.time()
            
            # Capture every 5 seconds
            if current_time - last_capture_time >= 5:
                frame_queue.put(("webcam", frame, {
                    "device": device_id,
                    "frame_number": frame_count,
                    "timestamp": datetime.now().isoformat()
                }))
                last_capture_time = current_time
            
            time.sleep(0.033)  ~30 FPS
            
        except Exception as e:
            print(f"Webcam capture error: {e}")
            time.sleep(1)
    
    cap.release()
    print("Webcam capture stopped")

def capture_screen(frame_queue, stop_event):
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
        last_capture_time = 0
        
        while not stop_event.is_set():
            try:
                # Capture screen
                screenshot = sct.grab(monitor)
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                frame_count += 1
                current_time = time.time()
                
                # Capture every 10 seconds
                if current_time - last_capture_time >= 10:
                    frame_queue.put(("screen", frame, {
                        "monitor": "primary",
                        "frame_number": frame_count,
                        "timestamp": datetime.now().isoformat()
                    }))
                    last_capture_time = current_time
                
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
        url = f"{analyzer_url}/frame"
        if question:
            url += f"?question={requests.utils.quote(question)}&type={prompt_type}"
        
        # Send POST request
        response = requests.post(
            url,
            data=img_encoded.tobytes(),
            headers={'Content-Type': 'image/jpeg'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Frame sent successfully: {result}")
            return True
        else:
            print(f"Failed to send frame: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending frame: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Frame Sender for VLM Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send frames from RTSP camera
  python frame_sender.py --analyzer http://192.168.1.50:8080 --rtsp rtsp://192.168.1.100:554/stream
  
  # Send frames from webcam with custom question
  python frame_sender.py --analyzer http://192.168.1.50:8080 --webcam 0 --question "What objects are visible?"
  
  # Send screenshots every 30 seconds
  python frame_sender.py --analyzer http://192.168.1.50:8080 --screen --interval 30
  
  # Send single image file
  python frame_sender.py --analyzer http://192.168.1.50:8080 --image path/to/image.jpg
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
    
    # Analysis options
    parser.add_argument("--question", help="Question to ask about the frame")
    parser.add_argument("--prompt-type", choices=["describe", "qa", "custom"], default="describe", help="Prompt type")
    parser.add_argument("--interval", type=int, default=10, help="Capture interval in seconds (for screen/webcam)")
    parser.add_argument("--motion", action="store_true", help="Enable motion detection (RTSP only)")
    
    args = parser.parse_args()
    
    # Create frame queue and stop event
    frame_queue = queue.Queue()
    stop_event = threading.Event()
    
    # Start appropriate capture thread
    capture_thread = None
    
    if args.rtsp:
        capture_thread = threading.Thread(
            target=capture_rtsp_frames,
            args=(args.rtsp, frame_queue, stop_event),
            daemon=True
        )
    elif args.webcam is not None:
        capture_thread = threading.Thread(
            target=capture_webcam_frames,
            args=(args.webcam, frame_queue, stop_event),
            daemon=True
        )
    elif args.screen:
        capture_thread = threading.Thread(
            target=capture_screen,
            args=(frame_queue, stop_event),
            daemon=True
        )
    
    # Start capture thread if needed
    if capture_thread:
        capture_thread.start()
        print(f"Capture started for {args.rtsp or f'webcam {args.webcam}' or 'screen'}")
    
    # Handle single image
    if args.image:
        print(f"Sending single image: {args.image}")
        frame = cv2.imread(args.image)
        if frame is not None:
            send_frame_to_analyzer(
                frame,
                {"source": "image", "filename": args.image},
                args.analyzer,
                args.question,
                args.prompt_type
            )
        else:
            print(f"Failed to load image: {args.image}")
        return
    
    # Handle video file
    if args.video:
        print(f"Processing video file: {args.video}")
        cap = cv2.VideoCapture(args.video)
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Send every 30th frame
            if frame_count % 30 == 0:
                print(f"Sending frame {frame_count} from video")
                send_frame_to_analyzer(
                    frame,
                    {"source": "video", "filename": args.video, "frame_number": frame_count},
                    args.analyzer,
                    args.question,
                    args.prompt_type
                )
                time.sleep(1)  # Don't flood the analyzer
        
        cap.release()
        print("Video processing complete")
        return
    
    # Process frames from queue
    print("Frame sender running. Press Ctrl+C to stop.")
    print(f"Sending to analyzer: {args.analyzer}")
    if args.question:
        print(f"Question: {args.question}")
    
    try:
        while True:
            try:
                # Get frame from queue
                source_type, frame, metadata = frame_queue.get(timeout=1)
                
                print(f"Sending frame from {source_type} (frame {metadata.get('frame_number', 'N/A')})")
                
                # Send to analyzer
                send_frame_to_analyzer(
                    frame,
                    metadata,
                    args.analyzer,
                    args.question,
                    args.prompt_type
                )
                
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
        print("Frame sender stopped")

if __name__ == "__main__":
    main()