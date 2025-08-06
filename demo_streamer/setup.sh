#!/bin/bash

echo "🚀 Starting Virtual Streamer System Setup..."

# Create virtual environment
echo "📦 Creating Python virtual environment..."
python -m venv venv

# Activate virtual environment
echo "⚡ Activating virtual environment..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install requirements
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating output directories..."
mkdir -p outputs/audio
mkdir -p outputs/videos
mkdir -p static

# Create environment file template
echo "🔑 Creating environment file template..."
cat > .env << EOF
# API Keys (replace with your actual keys)
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Database URL (SQLite default)
DATABASE_URL=sqlite:///./virtual_streamer.db

# Server settings
HOST=0.0.0.0
PORT=8000
EOF

echo "✅ Setup completed!"
echo ""
echo "🔧 Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. Ensure MuseTalk is set up in ../MuseTalk/"
echo "3. Run: python main.py"
echo "4. Open: http://localhost:8000"
echo ""
echo "📖 For detailed instructions, see README.md"
