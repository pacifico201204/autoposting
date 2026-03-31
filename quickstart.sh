#!/bin/bash
# Quick Start Script for Vibecode Auto

echo "🚀 Vibecode Auto - Beta 1.6"
echo "================================"
echo ""

# Check Python version
echo "📋 Kiểm tra Python..."
python3 --version

# Create logs directory
echo "📁 Tạo thư mục logs..."
mkdir -p logs

# Show recent logs
echo ""
echo "📊 Logs gần đây:"
ls -lh logs/ | tail -5

echo ""
echo "✅ Setup hoàn tất!"
echo ""
echo "🎯 Cách chạy:"
echo "   python3 main.py"
echo ""
echo "📖 Xem logs real-time:"
echo "   tail -f logs/vibecode_*.log"
echo ""
