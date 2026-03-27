#!/usr/bin/env python3
"""
Test Script for RTSP VLM Analyzer System

This script demonstrates how to use the VLM analyzer system.
Run this on your Raspberry Pi 5 with Hailo-10H.

Author: ClawBot
Date: 2026-03-27
"""

import subprocess
import time
import os
import sys

def test_rtsp_analyzer():
    """Test 1: Run RTSP analyzer with simulated camera"""
    print("\n" + "="*60)
    print("TEST 1: RTSP Analyzer with Test Pattern")
    print("="*60)
    
    # First, let's create a test RTSP server with a test pattern
    print("Creating test RTSP server...")
    
    # Check if we have ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except:
        print("ffmpeg not found. Install with: sudo apt install ffmpeg")
        return False
    
    # Start test RTSP server in background
    rtsp_cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", "testsrc=size=640x480:rate=30",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-f", "rtsp",
        "rtsp://127.0.0.1:8554/test"
    ]
    
    rtsp_process = subprocess.Popen(
        rtsp_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    time.sleep(2)  # Give server time to start
    
    # Start VLM analyzer
    print("Starting VLM analyzer...")
    analyzer_cmd = [
        sys.executable, "rtsp_vlm_analyzer.py",
        "--rtsp", "rtsp://127.0.0.1:8554/test",
        "--interval", "5",
        "--no-motion",
        "--default-question", "What colors and shapes do you see?",
        "--results-dir", "./test_results",
        "--verbose"
    ]
    
    analyzer_process = subprocess.Popen(
        analyzer_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    print("Analyzer running for 30 seconds...")
    print("Check ./test_results directory for analysis results")
    
    # Let it run for 30 seconds
    time.sleep(30)
    
    # Stop processes
    print("Stopping test...")
    analyzer_process.terminate()
    rtsp_process.terminate()
    
    analyzer_process.wait(timeout=5)
    rtsp_process.wait(timeout=5)
    
    # Check results
    if os.path.exists("./test_results"):
        result_files = list(os.listdir("./test_results"))
        if result_files:
            print(f"✓ Test passed! Found {len(result_files)} analysis results")
            return True
        else:
            print("✗ Test failed: No results generated")
            return False
    else:
        print("✗ Test failed: Results directory not created")
        return False

def test_http_server():
    """Test 2: Test HTTP server for network frames"""
    print("\n" + "="*60)
    print("TEST 2: HTTP Frame Receiver")
    print("="*60)
    
    # Start analyzer with HTTP server only
    print("Starting VLM analyzer with HTTP server...")
    analyzer_cmd = [
        sys.executable, "rtsp_vlm_analyzer.py",
        "--http-port", "9090",
        "--results-dir", "./http_test_results",
        "--verbose"
    ]
    
    analyzer_process = subprocess.Popen(
        analyzer_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    time.sleep(3)  # Give server time to start
    
    # Create a test image
    print("Creating test image...")
    import cv2
    import numpy as np
    
    # Create a simple test image
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(test_image, (100, 100), (300, 300), (0, 255, 0), -1)  # Green rectangle
    cv2.circle(test_image, (400, 200), 50, (255, 0, 0), -1)  # Blue circle
    
    # Save test image
    cv2.imwrite("test_image.jpg", test_image)
    
    # Send test image via HTTP
    print("Sending test image to analyzer...")
    
    # Read image as bytes
    with open("test_image.jpg", "rb") as f:
        image_data = f.read()
    
    # Send HTTP request
    import requests
    try:
        response = requests.post(
            "http://127.0.0.1:9090/frame?question=What shapes and colors are in this image?",
            data=image_data,
            headers={'Content-Type': 'image/jpeg'},
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✓ Image sent successfully: {response.json()}")
        else:
            print(f"✗ Failed to send image: {response.status_code}")
            analyzer_process.terminate()
            return False
        
    except Exception as e:
        print(f"✗ HTTP request failed: {e}")
        analyzer_process.terminate()
        return False
    
    # Wait for processing
    time.sleep(5)
    
    # Stop analyzer
    print("Stopping analyzer...")
    analyzer_process.terminate()
    analyzer_process.wait(timeout=5)
    
    # Check results
    if os.path.exists("./http_test_results"):
        result_files = list(os.listdir("./http_test_results"))
        if result_files:
            print(f"✓ HTTP test passed! Found {len(result_files)} analysis results")
            
            # Show first result
            first_result = os.path.join("./http_test_results", result_files[0])
            if first_result.endswith(".json"):
                import json
                with open(first_result, 'r') as f:
                    result_data = json.load(f)
                print(f"\nSample result:")
                print(f"  Question: {result_data.get('question')}")
                print(f"  Response: {result_data.get('response', '')[:100]}...")
            
            return True
        else:
            print("✗ HTTP test failed: No results generated")
            return False
    else:
        print("✗ HTTP test failed: Results directory not created")
        return False

def test_frame_sender():
    """Test 3: Test frame sender script"""
    print("\n" + "="*60)
    print("TEST 3: Frame Sender Script")
    print("="*60)
    
    print("This test requires two terminals:")
    print("1. Terminal 1: Run VLM analyzer with HTTP server")
    print("2. Terminal 2: Run frame sender")
    print("\nCommands to run:")
    print("Terminal 1: python rtsp_vlm_analyzer.py --http-port 9090 --results-dir ./sender_test")
    print("Terminal 2: python frame_sender.py --analyzer http://127.0.0.1:9090 --image test_image.jpg --question 'Describe this image'")
    
    return True

def main():
    """Run all tests"""
    print("VLM Analyzer System Test Suite")
    print("="*60)
    
    tests_passed = 0
    tests_total = 3
    
    # Run tests
    try:
        if test_rtsp_analyzer():
            tests_passed += 1
        
        if test_http_server():
            tests_passed += 1
        
        if test_frame_sender():
            tests_passed += 1
    
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("✓ All tests passed! Your VLM analyzer system is ready.")
        print("\nNext steps:")
        print("1. Run analyzer on Raspberry Pi:")
        print("   python rtsp_vlm_analyzer.py --rtsp rtsp://your_camera_ip:554/stream")
        print("2. Send frames from another machine:")
        print("   python frame_sender.py --analyzer http://raspberry_ip:8080 --rtsp rtsp://other_camera_ip:554/stream")
    else:
        print("✗ Some tests failed. Check the output above for details.")
    
    # Cleanup
    for dir_path in ["./test_results", "./http_test_results", "./sender_test"]:
        if os.path.exists(dir_path):
            import shutil
            shutil.rmtree(dir_path)
    
    if os.path.exists("test_image.jpg"):
        os.remove("test_image.jpg")

if __name__ == "__main__":
    main()