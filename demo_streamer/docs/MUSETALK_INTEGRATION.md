# 🎬 MuseTalk Avatar Integration Guide

## Tính năng mới: Tự động lấy Avatar từ MuseTalk

Hệ thống Virtual Streamer đã được tích hợp với MuseTalk để tự động sử dụng các avatar có sẵn.

## 🚀 Quick Start

### 1. Khởi động hệ thống

```bash
cd demo_streamer
python main.py
```

### 2. Truy cập Admin

- Mở: [http://localhost:8000/admin]
- Nhấn "Tạo phiên live mới"

### 3. Chọn Avatar MuseTalk

- Trong dropdown "Video avatar"
- Chọn mục **"🎬 MuseTalk Videos"**
- Khuyến nghị: `yongen.mp4` hoặc `sun.mp4`

### 4. Tạo session và test

- Chọn sản phẩm để bán
- Nhấn "Tạo phiên live"
- Nhấn "Chuẩn bị" để generate video

## 📋 Avatar có sẵn

### Video Avatars (Best Choice)

- ✅ **yongen.mp4** - Nam, chất lượng cao
- ✅ **sun.mp4** - Nữ, professional
- ✅ **long.mp4** - Video dài, nhiều expressions

### Demo Images (Backup)

- man, musk, monalisa, sit, video1, sun1, sun2

## 🔧 Troubleshooting

**Q: Không thấy MuseTalk avatars?**

```plain
- Đảm bảo thư mục MuseTalk ở ../MuseTalk/
- Kiểm tra file tồn tại trong data/video/
- Nhấn "Duyệt" để refresh danh sách
```

**Q: Avatar path quá dài?**

```plain
- Hệ thống tự động detect đường dẫn
- Chỉ cần chọn từ dropdown
- Không cần nhập thủ công
```

**Q: Video không preview được?**

```plain
- MuseTalk videos sử dụng absolute path
- Preview sẽ hiển thị placeholder icon
- Vẫn hoạt động bình thường khi process
```

## 🎯 Workflow hoàn chỉnh

1. **Setup**: Chọn avatar MuseTalk ✅
2. **Products**: Thêm sản phẩm cần bán ✅
3. **Session**: Tạo phiên live ✅
4. **Prepare**: Generate scripts + audio + video ✅
5. **Go Live**: Bắt đầu livestream ✅

Giờ đây việc tạo Virtual Streamer đã dễ dàng hơn rất nhiều với MuseTalk integration! 🎉
