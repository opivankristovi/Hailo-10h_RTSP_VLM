            }
        }
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """Handle POST requests with image frames"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Parse query parameters
            parsed = urlparse(self.path)
            query_params = parse_qs(parsed.query)
            
            # Convert bytes to numpy array
            nparr = np.frombuffer(post_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Get metadata from query params
                metadata = {
                    "source_ip": self.client_address[0],
                    "timestamp": datetime.now().isoformat(),
                    "size": f"{frame.shape[1]}x{frame.shape[0]}",
                    "question": query_params.get('question', [None])[0],
                    "prompt_type": query_params.get('type', ['describe'])[0]
                }
                
                # Put frame and metadata in queue
                self.frame_queue.put((frame, metadata))
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"status": "received", "frame_size": metadata["size"]}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"error": "Failed to decode image"}
                self.wfile.write(json.dumps(response).encode())
                
        except Exception as e:
            logger.error(f"HTTP handler error: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"HTTP {format % args}")

class RTSPVLMAnalyzer:
    """Main analyzer class"""
    
    def __init__(self, config):
        self.config = config
        self.vlm_processor = None
        self.frame_capture = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.http_server = None
        self.http_thread = None
        self.analysis_thread = None
        self.running = False
        self.results_dir = Path(config.get("results_dir", "./results"))
        self.results_dir.mkdir(exist_ok=True)
        
    def start(self):
        """Start the analyzer"""
        logger.info("Starting RTSP VLM Analyzer")
        
        # Initialize VLM
        self.vlm_processor = VLMProcessor(
            hef_path=self.config.get("hef_path"),
            model_name=self.config.get("model_name", "qwen2-vl-2b-instruct")
        )
        
        if not self.vlm_processor.initialize():
            logger.error("Failed to initialize VLM processor")
            return False
        
        # Start frame capture if RTSP source specified
        if self.config.get("rtsp_url"):
            self.frame_capture = FrameCapture(
                source_type="rtsp",
                source_url=self.config["rtsp_url"],
                username=self.config.get("rtsp_username"),
                password=self.config.get("rtsp_password"),
                motion_threshold=self.config.get("motion_threshold", 0.1)
            )
            
            if not self.frame_capture.start():
                logger.error("Failed to start frame capture")
                # Don't return False here - we might still have HTTP server
        
        # Start HTTP server for network frames
        if self.config.get("http_port"):
            self._start_http_server(self.config["http_port"])
        
        # Start analysis thread
        self.running = True
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        
        logger.info("RTSP VLM Analyzer started successfully")
        return True
    
    def _start_http_server(self, port):
        """Start HTTP server for receiving frames"""
        def handler_factory(queue):
            return lambda *args, **kwargs: FrameReceiverHTTPHandler(queue, *args, **kwargs)
        
        try:
            server_address = ('', port)
            self.http_server = HTTPServer(
                server_address, 
                handler_factory(self.frame_queue)
            )
            
            self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
            self.http_thread.start()
            logger.info(f"HTTP server started on port {port}")
            
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
    
    def _analysis_loop(self):
        """Main analysis loop"""
        logger.info("Analysis loop started")
        
        last_analysis_time = 0
        analysis_interval = self.config.get("analysis_interval", 10)  # seconds
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check for frames from HTTP queue
                try:
                    frame, metadata = self.frame_queue.get_nowait()
                    logger.info(f"Processing frame from {metadata['source_ip']}")
                    
                    # Determine prompt type
                    prompt_type = metadata.get("prompt_type", "describe")
                    question = metadata.get("question")
                    
                    # Analyze frame
                    result = self.vlm_processor.analyze_frame(
                        frame, 
                        prompt_type=prompt_type,
                        custom_question=question
                    )
                    
                    # Add metadata
                    result.update(metadata)
                    
                    # Save result
                    self._save_result(result, frame)
                    
                    self.frame_queue.task_done()
                    
                except queue.Empty:
                    pass
                
                # Check for frames from RTSP capture
                if self.frame_capture and self.frame_capture.running:
                    frame = self.frame_capture.get_frame()
                    
                    if frame is not None:
                        # Check if we should analyze this frame
                        should_analyze = False
                        
                        if self.config.get("analyze_on_motion", True):
                            # Check for motion
                            if self.frame_capture.detect_motion(frame):
                                logger.info("Motion detected - analyzing frame")
                                should_analyze = True
                        
                        elif current_time - last_analysis_time >= analysis_interval:
                            # Time-based analysis
                            should_analyze = True
                        
                        if should_analyze:
                            # Analyze frame
                            result = self.vlm_processor.analyze_frame(
                                frame,
                                prompt_type=self.config.get("default_prompt", "describe"),
                                custom_question=self.config.get("default_question")
                            )
                            
                            # Add metadata
                            result.update({
                                "source": "rtsp",
                                "source_url": self.config["rtsp_url"],
                                "frame_number": self.frame_capture.frame_count
                            })
                            
                            # Save result
                            self._save_result(result, frame)
                            
                            last_analysis_time = current_time
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}", exc_info=True)
                time.sleep(1)
    
    def _save_result(self, result, frame):
        """Save analysis result and optionally the frame"""
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_base = f"analysis_{timestamp}"
            
            # Save result as JSON
            result_file = self.results_dir / f"{filename_base}.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"Result saved to {result_file}")
            
            # Save frame if configured
            if self.config.get("save_frames", False):
                frame_file = self.results_dir / f"{filename_base}.jpg"
                cv2.imwrite(str(frame_file), frame)
                logger.info(f"Frame saved to {frame_file}")
            
            # Print result to console
            print("\n" + "="*60)
            print(f"ANALYSIS RESULT - {result['timestamp']}")
            print("="*60)
            print(f"Source: {result.get('source', 'unknown')}")
            print(f"Question: {result.get('question', 'Describe image')}")
            print(f"Inference time: {result.get('inference_time', 0):.2f}s")
            print("-"*60)
            print("RESPONSE:")
            print(result.get('response', 'No response'))
            print("="*60 + "\n")
            
        except Exception as e:
            logger.error(f"Failed to save result: {e}")
    
    def stop(self):
        """Stop the analyzer"""
        logger.info("Stopping RTSP VLM Analyzer")
        self.running = False
        
        # Stop frame capture
        if self.frame_capture:
            self.frame_capture.stop()
        
        # Stop HTTP server
        if self.http_server:
            self.http_server.shutdown()
        
        # Wait for threads
        if self.analysis_thread:
            self.analysis_thread.join(timeout=2)
        
        if self.http_thread:
            self.http_thread.join(timeout=2)
        
        # Cleanup VLM
        if self.vlm_processor:
            self.vlm_processor.cleanup()
        
        logger.info("RTSP VLM Analyzer stopped")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="RTSP Camera VLM Analyzer for Raspberry Pi 5 with Hailo-10H",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze RTSP stream with motion detection
  python rtsp_vlm_analyzer.py --rtsp rtsp://192.168.1.100:554/stream
  
  # Analyze RTSP stream with authentication
  python rtsp_vlm_analyzer.py --rtsp rtsp://192.168.1.100:554/stream --rtsp-user admin --rtsp-pass password
  
  # Analyze RTSP stream every 30 seconds
  python rtsp_vlm_analyzer.py --rtsp rtsp://192.168.1.100:554/stream --interval 30 --no-motion
  
  # Start HTTP server on port 8080 for network frames
  python rtsp_vlm_analyzer.py --http-port 8080
  
  # Use custom VLM model
  python rtsp_vlm_analyzer.py --rtsp rtsp://192.168.1.100:554/stream --model /path/to/model.hef
  
  # Save analyzed frames
  python rtsp_vlm_analyzer.py --rtsp rtsp://192.168.1.100:554/stream --save-frames
  
  # Test without Hailo hardware (simulation mode)
  python rtsp_vlm_analyzer.py --rtsp rtsp://192.168.1.100:554/stream --simulate
        """
    )
    
    # Source options
    source_group = parser.add_argument_group('Source Options')
    source_group.add_argument("--rtsp", type=str, help="RTSP camera URL (e.g., rtsp://192.168.1.100:554/stream)")
    source_group.add_argument("--rtsp-user", type=str, help="RTSP username")
    source_group.add_argument("--rtsp-pass", type=str, help="RTSP password")
    source_group.add_argument("--http-port", type=int, default=8080, help="HTTP server port for network frames (default: 8080)")
    
    # Analysis options
    analysis_group = parser.add_argument_group('Analysis Options')
    analysis_group.add_argument("--interval", type=int, default=10, help="Analysis interval in seconds (default: 10)")
    analysis_group.add_argument("--no-motion", action="store_true", help="Disable motion detection")
    analysis_group.add_argument("--motion-threshold", type=float, default=0.1, help="Motion detection threshold (0.0-1.0, default: 0.1)")
    analysis_group.add_argument("--default-question", type=str, help="Default question for analysis")
    analysis_group.add_argument("--prompt-type", choices=["describe", "qa", "custom"], default="describe", help="Default prompt type")
    
    # Model options
    model_group = parser.add_argument_group('Model Options')
    model_group.add_argument("--model", type=str, help="Path to VLM HEF model file")
    model_group.add_argument("--model-name", type=str, default="qwen2-vl-2b-instruct", help="VLM model name (default: qwen2-vl-2b-instruct)")
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument("--results-dir", type=str, default="./results", help="Directory for saving results (default: ./results)")
    output_group.add_argument("--save-frames", action="store_true", help="Save analyzed frames as images")
    output_group.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    # Testing options
    testing_group = parser.add_argument_group('Testing Options')
    testing_group.add_argument("--simulate", action="store_true", help="Run in simulation mode (no Hailo hardware required)")
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if not args.rtsp and args.http_port <= 0:
        parser.error("At least one source (--rtsp or --http-port) must be specified")
    
    # Create config
    config = {
        "rtsp_url": args.rtsp,
        "rtsp_username": args.rtsp_user,
        "rtsp_password": args.rtsp_pass,
        "http_port": args.http_port,
        "analysis_interval": args.interval,
        "analyze_on_motion": not args.no_motion,
        "motion_threshold": args.motion_threshold,
        "default_prompt": args.prompt_type,
        "default_question": args.default_question,
        "hef_path": args.model,
        "model_name": args.model_name,
        "results_dir": args.results_dir,
        "save_frames": args.save_frames
    }
    
    # Override HAILO_AVAILABLE if simulation mode
    if args.simulate:
        global HAILO_AVAILABLE
        HAILO_AVAILABLE = False
        logger.info("Running in simulation mode (no Hailo hardware required)")
    
    # Create and start analyzer
    analyzer = RTSPVLMAnalyzer(config)
    
    try:
        if analyzer.start():
            print("\n" + "="*60)
            print("RTSP VLM ANALYZER RUNNING")
            print("="*60)
            if config["rtsp_url"]:
                print(f"RTSP Source: {config['rtsp_url']}")
                if config["rtsp_username"]:
                    print(f"RTSP Username: {config['rtsp_username']}")
            if config["http_port"] > 0:
                print(f"HTTP Server: http://<raspberry_ip>:{config['http_port']}/frame")
            print(f"Results Directory: {config['results_dir']}")
            print(f"Default Prompt: {config['default_prompt']}")
            if config["default_question"]:
                print(f"Default Question: {config['default_question']}")
            if not HAILO_AVAILABLE:
                print(f"Mode: SIMULATION (no Hailo hardware)")
            print("="*60)
            print("Press Ctrl+C to stop\n")
            
            # Keep main thread alive
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        analyzer.stop()

if __name__ == "__main__":
    main()