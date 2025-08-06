# 🎯 Virtual Streamer - Avatar Management Guide

## ✨ Tính năng mới đã được cải thiện

### 1. **Dropdown chọn Avatar có sẵn**

- Hiển thị danh sách tất cả video avatar trong thư mục `static/avatars/`
- Hiển thị tên file và dung lượng
- Tự động cập nhật khi có avatar mới

### 2. **Upload Avatar mới**

- Upload trực tiếp qua giao diện web
- Validation file type (chỉ chấp nhận video)
- Giới hạn dung lượng 100MB
- Auto-preview sau khi upload

### 3. **Preview Video Real-time**

- Xem trước video avatar ngay trong form
- Hiển thị thông tin file (tên, dung lượng)
- Hỗ trợ cả avatar local và URL

### 4. **Validation nâng cao**

- Kiểm tra đường dẫn file hợp lệ
- Validate định dạng video
- Thông báo lỗi chi tiết

### 5. **File Browser**

- Nút "Duyệt" để cập nhật danh sách avatar
- Tự động reload khi có thay đổi

### 6. **API Endpoints mới**

- `GET /api/avatars` - Lấy danh sách avatar
- `POST /api/avatars/upload` - Upload avatar mới

### 7. **UI/UX cải thiện**

- Giao diện 2 cột: chọn avatar + preview
- Icon và button trực quan
- Responsive design

### 8. **Documentation**

- README chi tiết trong thư mục avatars
- Hướng dẫn setup và troubleshooting

## 🚀 Cách sử dụng

### Bước 1: Chuẩn bị Avatar

1. Chuẩn bị video avatar (MP4, AVI, MOV)
2. Đảm bảo video có người nói rõ ràng
3. Thời lượng 10-30 giây

### Bước 2: Thêm Avatar

**Option A: Upload qua Web**:

1. Vào Admin Dashboard
2. Tạo phiên live mới
3. Nhấn "Upload Video Mới"
4. Chọn file và upload

**Option B: Copy trực tiếp**:

1. Copy file vào `static/avatars/`
2. Nhấn "Duyệt" để cập nhật

### Bước 3: Tạo phiên live

1. Chọn avatar từ dropdown HOẶC
2. Nhập đường dẫn thủ công
3. Xem preview để kiểm tra
4. Chọn sản phẩm và tạo session

## 🔧 Troubleshooting

**Q: Không thấy avatar trong dropdown?**:

```plain
- Kiểm tra file có trong thư mục static/avatars/
- Nhấn nút "Duyệt" để refresh
- Đảm bảo file có định dạng hỗ trợ (.mp4, .avi, .mov)
```

**Q: Upload thất bại?**:

```plain
- Kiểm tra dung lượng file < 100MB
- Đảm bảo là file video hợp lệ
- Thử lại với file khác
```

**Q: Preview không hiển thị?**:

```plain
- Kiểm tra đường dẫn file chính xác
- Browser phải hỗ trợ định dạng video
- Refresh trang và thử lại
```

## 📁 Cấu trúc thư mục

```plain
static/
├── avatars/
│   ├── README.md              # Hướng dẫn chi tiết
│   ├── sample_avatar.mp4      # Avatar mẫu (nếu có)
│   └── ...                    # Các avatar khác
├── admin.html                 # Giao diện admin đã cải thiện
├── admin.js                   # JavaScript với avatar functions
└── ...
```

## 🎉 Demo workflow

1. **Start server**: `python main.py`
2. **Open admin**: [http://localhost:8000/admin]
3. **Create session**: Nhấn "Tạo phiên live mới"
4. **Select avatar**: Chọn từ dropdown hoặc upload mới
5. **Preview**: Xem video preview ngay lập tức
6. **Create**: Hoàn tất tạo session với avatar đã chọn

Bây giờ bạn có một hệ thống quản lý avatar hoàn chỉnh và user-friendly! 🎊
