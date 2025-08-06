# Virtual Streamer System

Hệ thống livestream bán hàng tự động với AI Virtual Human sử dụng MuseTalk.

## Tính năng chính

### 🤖 AI Virtual Human

- Sử dụng MuseTalk để tạo video lip-sync chân thực
- Virtual human có thể nói về sản phẩm một cách tự nhiên
- Hỗ trợ nhiều avatar và giọng nói khác nhau

### 🧠 LLM Script Generation

- Tự động tạo script bán hàng bằng OpenAI/Gemini
- Tối ưu hóa nội dung cho từng sản phẩm
- Template script có thể tùy chỉnh

### 📹 Real-time Streaming

- Livestream trực tiếp với chat tương tác
- Q&A real-time với khán giả
- Điều khiển admin trong thời gian thực

### 💾 Quản lý sản phẩm

- Hệ thống database hoàn chỉnh
- Quản lý hình ảnh, giá cả, kho hàng
- Phân loại sản phẩm theo danh mục

### 🎤 Text-to-Speech

- Chuyển đổi script thành giọng nói tự nhiên
- Hỗ trợ nhiều giọng và ngôn ngữ
- Chất lượng audio cao

### ⚙️ Admin Dashboard

- Giao diện quản trị trực quan
- Theo dõi thống kê real-time
- Điều khiển phiên live dễ dàng

## Cách hoạt động

1. **Thêm sản phẩm**: Admin thêm sản phẩm vào database với thông tin chi tiết
2. **Tạo phiên live**: Chọn sản phẩm, LLM tạo script, TTS chuyển thành audio
3. **Xử lý MuseTalk**: Tạo video lip-sync từ audio và avatar
4. **Livestream**: Virtual human giới thiệu sản phẩm với tương tác real-time

## Cài đặt

### Yêu cầu hệ thống

- Python 3.10+
- CUDA (khuyến nghị cho GPU acceleration)
- FFmpeg
- Git

### Cài đặt dependencies

1. Clone repository:

    ```bash
    git clone <repository-url>
    cd virtual-streamer
    ```

2. Cài đặt Python dependencies:

    ```bash
    cd demo_streamer
    pip install -r requirements.txt
    ```

3. Thiết lập MuseTalk:

    ```bash
    cd ../MuseTalk
    pip install -r requirements.txt
    # Download models theo hướng dẫn MuseTalk README
    ```

4. Thiết lập FFmpeg:

- Windows: Download và thêm vào PATH
- Linux: `sudo apt install ffmpeg`

### Cấu hình

1. Tạo file `.env` trong thư mục `demo_streamer`:

    ```env
    OPENAI_API_KEY=your_openai_api_key
    GEMINI_API_KEY=your_gemini_api_key
    ```

2. Cập nhật đường dẫn MuseTalk trong `services.py` nếu cần

## Chạy ứng dụng

1. Khởi động backend API:

    ```bash
    cd demo_streamer
    python main.py
    ```

2. Truy cập giao diện:

- Homepage: [http://localhost:8000]
- Admin Dashboard: [http://localhost:8000/admin]
- Live Session: [http://localhost:8000/live/{session_id}]

## API Documentation

API documentation có sẵn tại: [http://localhost:8000/docs]

### Endpoints chính

- `POST /api/products/` - Tạo sản phẩm mới
- `GET /api/products/` - Lấy danh sách sản phẩm
- `POST /api/sessions/` - Tạo phiên live
- `POST /api/sessions/{id}/prepare` - Chuẩn bị phiên live
- `POST /api/sessions/{id}/start` - Bắt đầu live
- `POST /api/sessions/{id}/comments` - Thêm comment
- `WebSocket /ws` - Real-time updates

## Kiến trúc hệ thống

```plain
demo_streamer/
├── main.py              # FastAPI application
├── models.py            # Database models
├── database.py          # Database services
├── services.py          # LLM, TTS, MuseTalk services
├── static/              # Frontend files
│   ├── index.html       # Homepage
│   ├── admin.html       # Admin dashboard
│   ├── live.html        # Live session view
│   ├── admin.js         # Admin functionality
│   └── live.js          # Live session functionality
├── outputs/             # Generated content
│   ├── audio/           # TTS audio files
│   └── videos/          # MuseTalk video files
└── requirements.txt     # Python dependencies
```

## Workflow

### Tạo phiên live

1. Admin chọn sản phẩm từ database
2. LLM (OpenAI/Gemini) tạo script cho từng sản phẩm
3. TTS chuyển script thành audio
4. MuseTalk tạo video lip-sync từ audio + avatar
5. Phiên live sẵn sàng

### Trong lúc live

1. Video sản phẩm được phát tuần tự
2. Giữa các sản phẩm có khoảng trống cho Q&A
3. Admin có thể trả lời câu hỏi real-time
4. Chat tương tác với khán giả

## Tùy chỉnh

### Thêm LLM provider mới

1. Implement trong `LLMService` class
2. Thêm logic xử lý API calls
3. Update configuration

### Thêm TTS provider

1. Extend `TTSService` class
2. Implement conversion method
3. Update audio processing pipeline

### Tùy chỉnh giao diện

1. Modify HTML templates trong `static/`
2. Update CSS styles
3. Extend JavaScript functionality

## Troubleshooting

### MuseTalk issues

- Đảm bảo models đã được download
- Kiểm tra đường dẫn FFmpeg
- Verify CUDA installation cho GPU

### API errors

- Kiểm tra API keys trong .env
- Verify network connectivity
- Check logs trong console

### Database issues

- SQLite database tự động tạo
- Check file permissions
- Verify schema với models.py

## Performance Tips

1. **GPU Acceleration**: Sử dụng CUDA cho MuseTalk
2. **Caching**: Cache generated content
3. **Async Processing**: Sử dụng background tasks
4. **CDN**: Serve static assets từ CDN
5. **Database Optimization**: Index quan trọng columns

## Security

1. **API Keys**: Bảo mật trong environment variables
2. **Input Validation**: Validate tất cả user inputs
3. **Rate Limiting**: Implement cho API endpoints
4. **CORS**: Configure cho production
5. **HTTPS**: Sử dụng SSL trong production

## Deployment

### Docker

```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### Production checklist

- [ ] Environment variables configured
- [ ] Database backup strategy
- [ ] SSL certificates
- [ ] CDN for static assets
- [ ] Monitoring và logging
- [ ] Error handling
- [ ] Rate limiting
- [ ] Security headers

## Contributing

1. Fork repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

MIT License - xem LICENSE file để biết chi tiết.

## Support

Để được hỗ trợ:

1. Check documentation
2. Search existing issues
3. Create new issue với:
    - Mô tả chi tiết vấn đề
    - Steps to reproduce
    - Environment information
    - Error logs

---

## Demo Features

Hệ thống demo bao gồm:

✅ **Hoàn thành:**

- Database models và API
- Admin dashboard hoàn chỉnh
- Live session interface
- Real-time chat và WebSocket
- LLM script generation
- TTS integration
- MuseTalk integration
- Responsive UI

🚧 **Đang phát triển:**

- Advanced analytics
- Multi-language support
- Mobile app
- Advanced streaming features

📋 **Kế hoạch:**

- AI voice cloning
- Advanced personalization
- E-commerce integration
- Payment processing
- Advanced reporting
