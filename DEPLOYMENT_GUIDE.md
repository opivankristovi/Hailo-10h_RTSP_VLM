# Deployment Guide

## Quick Deployment Checklist

### ✅ Step 1: Repository Setup
```bash
# Clone the repository
git clone https://github.com/opivankristovi/Hailo-10h_RTSP_VLM
cd Hailo-10h_RTSP_VLM

# Verify files
ls -la
```

### ✅ Step 2: Raspberry Pi Setup
```bash
# Run setup script
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Test Hailo installation
python -c "import hailo_platform; print('Hailo SDK OK')"
```

### ✅ Step 3: Test Basic Functionality
```bash
# Run test suite
python test_vlm_system.py

# Expected output: All tests should pass
```

### ✅ Step 4: Configure Your Cameras
1. **Find camera RTSP URL**: Usually `rtsp://<camera_ip>:554/stream`
2. **Test with VLC**: `vlc rtsp://camera_ip:554/stream`
3. **Note credentials**: username/password if required

### ✅ Step 5: Deploy Analyzer
```bash
# Simple deployment (motion detection)
python rtsp_vlm_analyzer.py --rtsp rtsp://camera_ip:554/stream

# Advanced deployment (with HTTP server)
python rtsp_vlm_analyzer.py \
  --rtsp rtsp://camera_ip:554/stream \
  --http-port 8080 \
  --results-dir /var/log/vlm-analyzer \
  --save-frames \
  --verbose
```

### ✅ Step 6: Deploy Frame Senders (Optional)
```bash
# On other devices
python frame_sender.py \
  --analyzer http://raspberry_pi_ip:8080 \
  --rtsp rtsp://other_camera_ip:554/stream \
  --question "What's happening?" \
  --interval 60
```

## Production Deployment

### Systemd Service (Recommended)
Create `/etc/systemd/system/vlm-analyzer.service`:
```ini
[Unit]
Description=Hailo VLM Analyzer Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Hailo-10h_RTSP_VLM
Environment="PATH=/home/pi/Hailo-10h_RTSP_VLM/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/pi/Hailo-10h_RTSP_VLM/venv/bin/python rtsp_vlm_analyzer.py \
  --rtsp rtsp://camera_ip:554/stream \
  --http-port 8080 \
  --results-dir /var/log/vlm-analyzer \
  --save-frames \
  --log-level INFO
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

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

### Log Monitoring
```bash
# View logs
sudo journalctl -u vlm-analyzer -f

# Check results
ls -la /var/log/vlm-analyzer/
tail -f /var/log/vlm-analyzer/vlm_analyzer.log
```

## Network Configuration

### Firewall Rules
```bash
# Allow RTSP (if camera is on different subnet)
sudo ufw allow from 192.168.1.0/24 to any port 554

# Allow HTTP server
sudo ufw allow 8080/tcp

# Enable firewall
sudo ufw enable
```

### Static IP (Recommended)
Edit `/etc/dhcpcd.conf`:
```bash
interface eth0
static ip_address=192.168.1.50/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

## Performance Optimization

### Hailo-10H Tuning
```bash
# Check Hailo device status
hailortcli fw-control identify

# Monitor temperature
hailortcli fw-control get-temperature

# Set performance mode (if available)
hailortcli fw-control set-performance-mode high
```

### Raspberry Pi Optimization
```bash
# Overclock (if needed)
# Edit /boot/config.txt
# over_voltage=2
# arm_freq=2000
# gpu_freq=750

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
sudo systemctl disable cups

# Increase swap (for memory-intensive operations)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## Monitoring & Maintenance

### Health Check Script
Create `health_check.sh`:
```bash
#!/bin/bash
# Health check for VLM analyzer

# Check service status
if ! systemctl is-active --quiet vlm-analyzer; then
    echo "Service not running"
    systemctl restart vlm-analyzer
fi

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    echo "Disk space critical: $DISK_USAGE%"
    # Clean old results
    find /var/log/vlm-analyzer -name "*.json" -mtime +7 -delete
    find /var/log/vlm-analyzer -name "*.jpg" -mtime +3 -delete
fi

# Check Hailo device
if ! hailortcli fw-control identify >/dev/null 2>&1; then
    echo "Hailo device not detected"
fi

# Check network connectivity
if ! ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
    echo "Network connectivity issue"
fi
```

### Cron Job for Maintenance
```bash
# Edit crontab
crontab -e

# Add these lines:
# Daily health check at 2 AM
0 2 * * * /home/pi/Hailo-10h_RTSP_VLM/health_check.sh >> /var/log/vlm-health.log

# Weekly cleanup on Sunday at 3 AM
0 3 * * 0 find /var/log/vlm-analyzer -name "*.json" -mtime +30 -delete
0 3 * * 0 find /var/log/vlm-analyzer -name "*.jpg" -mtime +7 -delete

# Restart service weekly to prevent memory leaks
0 4 * * 0 systemctl restart vlm-analyzer
```

## Troubleshooting

### Common Issues & Solutions

#### 1. "VLM model not found"
```bash
# Check model path
ls -la /usr/share/hailo-ollama/models/blob/

# Download manually (if auto-download fails)
# Get from Hailo Developer Zone
sudo cp Qwen2-VL-2B-Instruct.hef /usr/share/hailo-ollama/models/blob/
```

#### 2. "RTSP connection failed"
```bash
# Test with ffmpeg
ffmpeg -i rtsp://camera_ip:554/stream -f null -

# Check credentials
# URL format: rtsp://username:password@camera_ip:554/stream

# Check network
ping camera_ip
```

#### 3. "HTTP server not accessible"
```bash
# Check firewall
sudo ufw status

# Check service is running
netstat -tlnp | grep 8080

# Test locally
curl http://127.0.0.1:8080
```

#### 4. "Slow inference"
```bash
# Check Hailo device
hailortcli fw-control identify

# Reduce token count in code
# Edit rtsp_vlm_analyzer.py: max_generated_tokens=100

# Check CPU temperature
vcgencmd measure_temp
```

#### 5. "Memory issues"
```bash
# Check memory usage
free -h

# Increase swap
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## Backup & Recovery

### Backup Configuration
```bash
# Create backup script
cat > backup_vlm.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/pi/backups/vlm-analyzer"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration
cp /etc/systemd/system/vlm-analyzer.service $BACKUP_DIR/vlm-analyzer.service.$DATE

# Backup results (last 7 days)
find /var/log/vlm-analyzer -name "*.json" -mtime -7 -exec cp {} $BACKUP_DIR/ \;

# Backup logs
cp /var/log/vlm-analyzer/vlm_analyzer.log $BACKUP_DIR/vlm_analyzer.log.$DATE

# Create archive
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz $BACKUP_DIR/*.$DATE

echo "Backup created: $BACKUP_DIR/backup_$DATE.tar.gz"
EOF

chmod +x backup_vlm.sh
```

### Recovery
```bash
# Restore from backup
tar -xzf backup_20240327_120000.tar.gz

# Restore service file
sudo cp vlm-analyzer.service.20240327_120000 /etc/systemd/system/vlm-analyzer.service
sudo systemctl daemon-reload
sudo systemctl restart vlm-analyzer
```

## Scaling for Multiple Cameras

### Option 1: Multiple Services
```bash
# Create separate service files
sudo cp /etc/systemd/system/vlm-analyzer.service /etc/systemd/system/vlm-analyzer-camera1.service
sudo cp /etc/systemd/system/vlm-analyzer.service /etc/systemd/system/vlm-analyzer-camera2.service

# Edit each with different RTSP URL and ports
# camera1: --rtsp rtsp://camera1:554/stream --http-port 8081
# camera2: --rtsp rtsp://camera2:554/stream --http-port 8082

# Start all services
sudo systemctl start vlm-analyzer-camera1
sudo systemctl start vlm-analyzer-camera2
```

### Option 2: Single Service with Multiple Threads
Modify `rtsp_vlm_analyzer.py` to handle multiple RTSP streams in parallel.

## Security Considerations

### 1. Change Default Passwords
```bash
# Raspberry Pi
passwd

# Camera admin passwords
# Change via camera web interface
```

### 2. Network Segmentation
```bash
# Use separate VLAN for cameras
# Edit /etc/dhcpcd.conf for multiple interfaces
```

### 3. Regular Updates
```bash
# System updates
sudo apt update
sudo apt upgrade -y

# Python package updates
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### 4. Access Control
```bash
# Restrict SSH
sudo nano /etc/ssh/sshd_config
# PermitRootLogin no
# PasswordAuthentication no (use keys)

# Restrict HTTP server to local network
# In rtsp_vlm_analyzer.py, bind to specific IP
```

## Support & Resources

### Documentation
- **Project README**: Detailed usage instructions
- **GitHub Wiki**: Additional documentation (if enabled)
- **Example Usage**: `examples/example_usage.md`

### Community Support
- **GitHub Issues**: Bug reports and feature requests
- **Hailo Community Forum**: https://community.hailo.ai/
- **Raspberry Pi Forums**: https://forums.raspberrypi.com/

### Monitoring Tools
```bash
# System monitoring
htop
nmon

# Network monitoring
iftop
nethogs

# Log monitoring
journalctl -f -u vlm-analyzer
tail -f /var/log/vlm-analyzer/vlm_analyzer.log
```

## Next Steps After Deployment

1. **Monitor for 24 hours** to ensure stability
2. **Review analysis results** for accuracy
3. **Adjust motion thresholds** based on environment
4. **Set up alerts** for critical detections
5. **Implement backup strategy** for results
6. **Consider scaling** to additional cameras
7. **Explore integrations** with other systems (Home Assistant, etc.)

Remember to regularly check the GitHub repository for updates and security patches.