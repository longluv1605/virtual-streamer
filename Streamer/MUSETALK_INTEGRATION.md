# MuseTalk WebRTC Integration

Tích hợp MuseTalk vào hệ thống WebRTC streaming của Virtual Streamer.

## Architecture

### Model Loading Optimization

-   Singleton pattern để load models một lần khi khởi động server
-   Thread-safe initialization với threading.Lock()
-   Graceful fallback về demo mode nếu initialization thất bại

### Avatar Data Management

-   Sử dụng Avatar class có sẵn từ MuseTalk repository
-   Cache avatar data trong memory sau khi prepare
-   Disk persistence cho avatar data đã process

### WebRTC Integration

-   Queue-based streaming với video và audio queues
-   Sử dụng logic inference có sẵn từ MuseTalk
-   Extension method cho Avatar class để support WebRTC

## Files Modified

**src/services/musetalk.py**

-   MuseTalkRealtimeService class với Singleton pattern
-   initialize_models(): Load models một lần
-   prepare_avatar(): Wrapper cho Avatar.prepare_material()
-   generate_frames_for_webrtc(): Wrapper cho Avatar.inference_for_webrtc()

**src/services/avatar_webrtc_extension.py**

-   Extension method inference_for_webrtc cho Avatar class
-   Monkey patch để thêm method vào Avatar class có sẵn
-   Reuse toàn bộ logic từ MuseTalk scripts

**src/services/stream.py**

-   Tích hợp MuseTalk vào start_realtime_session()
-   Auto-detect và fallback về demo mode
-   prepare_avatar_for_realtime() helper function

**src/api/webrtc.py**

-   /realtime/start với avatar_id và audio_path parameters
-   /avatar/prepare endpoint
-   /avatar/initialize endpoint để manual init models
-   /musetalk/status endpoint

**static/live.js**

-   Auto-detect MuseTalk status
-   Pass avatar parameters khi start realtime session

**main.py**

-   Auto-initialize MuseTalk models khi startup
-   Error handling và fallback

## API Endpoints

### GET /api/webrtc/musetalk/status

Check MuseTalk service status

```json
{
    "initialized": true,
    "current_avatar": "yongen",
    "loaded_avatars": ["yongen", "sun"]
}
```

### POST /api/webrtc/avatar/initialize

Initialize MuseTalk models manually

```json
{ "status": "success" }
```

### POST /api/webrtc/avatar/prepare

Prepare avatar cho realtime streaming

```bash
POST /api/webrtc/avatar/prepare?avatar_id=yongen&video_path=../MuseTalk/data/video/yongen.mp4
```

### POST /api/webrtc/realtime/start

Start realtime session với MuseTalk support

```bash
POST /api/webrtc/realtime/start?session_id=test&avatar_id=yongen&audio_path=../MuseTalk/data/audio/yongen.wav
```

## Usage

### 1. Start Server

```bash
cd Streamer
python main.py
```

Server tự động initialize MuseTalk models nếu có thể.

### 2. Prepare Avatar (via API)

```bash
# Initialize models nếu chưa được init
curl -X POST "http://localhost:8000/api/webrtc/avatar/initialize"

# Prepare avatar
curl -X POST "http://localhost:8000/api/webrtc/avatar/prepare?avatar_id=yongen&video_path=../MuseTalk/data/video/yongen.mp4"
```

### 3. Start WebRTC Streaming

Frontend sẽ tự động:

1. Check MuseTalk status
2. Sử dụng MuseTalk nếu ready
3. Fallback về demo mode nếu không

## Technical Details

### Code Reuse Strategy

-   Không implement lại logic đã có trong MuseTalk
-   Sử dụng Avatar class có sẵn từ scripts/realtime_inference_synced.py
-   Extension method để thêm WebRTC support vào Avatar class
-   Wrapper functions trong MuseTalkRealtimeService

### Performance Optimizations

-   Models load một lần khi startup server (~10-30 giây)
-   Avatar preparation (~1-5 phút) và cache trong memory
-   Realtime generation ~25 FPS trên modern GPU
-   Memory usage ~4-8GB VRAM cho MuseTalk models

### Error Handling

-   Graceful fallback về demo mode
-   Comprehensive error logging
-   API status endpoints để debug
-   Timeout handling cho queue operations
