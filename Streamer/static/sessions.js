// API Base URL
const API_BASE = "/api";

// WebSocket connection
let ws = null;

// Global data
let products = [];
let sessions = [];
let templates = [];
let availableAvatars = [];

// Initialize app
document.addEventListener("DOMContentLoaded", function () {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    initWebSocket();
    loadSessions();
    loadAvatars();
});

// WebSocket functions
function initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onopen = function () {
        console.log("WebSocket connected");
    };

    ws.onmessage = function (event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onclose = function () {
        console.log("WebSocket disconnected");
        // Reconnect after 3 seconds
        setTimeout(initWebSocket, 3000);
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case "session_ready":
            showNotification(
                "success",
                `Phiên live ${data.session_id} đã sẵn sàng!`
            );
            loadSessions();
            hideLoading();
            break;
        case "session_error":
            showNotification(
                "error",
                `Lỗi xử lý phiên live ${data.session_id}`
            );
            loadSessions();
            hideLoading();
            break;
        case "session_started":
            showNotification(
                "info",
                `Phiên live ${data.session_id} đã bắt đầu`
            );
            loadSessions();
            break;
        case "session_stopped":
            showNotification(
                "info",
                `Phiên live ${data.session_id} đã kết thúc`
            );
            loadSessions();
            break;
        case "new_comment":
            // Handle new comments if needed
            break;
    }
}

// Session functions
async function loadSessions() {
    try {
        const response = await fetch(`${API_BASE}/sessions`);
        sessions = await response.json();
        displaySessions();
    } catch (error) {
        console.error("Error loading sessions:", error);
        showNotification("error", "Lỗi tải danh sách phiên live");
    }
}

function displaySessions() {
    const container = document.getElementById("sessions-list");

    if (sessions.length === 0) {
        container.innerHTML =
            '<p class="text-muted">Chưa có phiên live nào</p>';
        return;
    }
    sessions.reverse();
    const html = sessions
        .map(
            (session) => `
        <div class="card session-card mb-3">
            <div class="card-body">
                <div class="row">
                    <div class="col-md-8">
                        <h5 class="card-title">${session.title}</h5>
                        <p class="card-text">${
                            session.description || "Không có mô tả"
                        }</p>
                        <p class="card-text">
                            <small class="text-muted">Tạo: ${formatDate(
                                session.created_at
                            )}</small>
                        </p>
                        ${getStreamingInfo(session)}
                    </div>
                    <div class="col-md-4 text-end">
                        <span class="badge ${getStatusBadgeClass(
                            session.status
                        )} status-badge mb-2">
                            ${getStatusText(session.status)}
                        </span><br>
                        ${getSessionActions(session)}
                    </div>
                </div>
            </div>
        </div>
    `
        )
        .join("");

    container.innerHTML = html;
}

function getSessionActions(session) {
    switch (session.status) {
        case "preparing":
            return `
                <button class="btn btn-sm btn-warning mb-1" onclick="prepareSession(${session.id})">
                    <i class="fas fa-cog"></i> Chuẩn bị
                </button><br>
            `;
        case "ready":
            return `
                <button class="btn btn-sm btn-success mb-1" onclick="startSession(${session.id})">
                    <i class="fas fa-play"></i> Bắt đầu
                </button><br>
            `;
        case "live":
            return `
                <button class="btn btn-sm btn-danger mb-1" onclick="stopSession(${session.id})">
                    <i class="fas fa-stop"></i> Dừng
                </button><br>
                <a href="/live/${session.id}" class="btn btn-sm btn-outline-info mb-1" target="_blank">
                    <i class="fas fa-external-link-alt"></i> Live
                </a>
            `;
        default:
            return "";
    }
}

async function showCreateSessionModal() {
    document.getElementById("createSessionForm").reset();

    // Reset streaming settings to default values
    // document.getElementById("enableStreaming").checked = false;
    document.getElementById("waitTime").value = 10;
    document.getElementById("fps").value = 25;
    document.getElementById("batchSize").value = 4;

    // Show modal first
    const modal = new bootstrap.Modal(
        document.getElementById("createSessionModal")
    );
    modal.show();

    // Initialize tooltips for the modal
    setTimeout(() => {
        var tooltipTriggerList = [].slice.call(
            document.querySelectorAll(
                '#createSessionModal [data-bs-toggle="tooltip"]'
            )
        );
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }, 100);

    // Then load data asynchronously
    try {
        console.log("Starting to load product selection...");
        await loadProductSelection();
        console.log("Product selection loaded successfully");
        await loadAvatarSelection();
    } catch (error) {
        console.error("Error in showCreateSessionModal:", error);
    }
}

async function loadProductSelection() {
    const container = document.getElementById("productSelection");

    try {
        console.log("Fetching products from API...");
        // Fetch products directly from API
        const response = await fetch(`${API_BASE}/products`);
        console.log("API response status:", response.status);

        const productsData = await response.json();
        console.log("API response data:", productsData);

        // Extract products array from paginated response
        const products = Array.isArray(productsData.items)
            ? productsData.items
            : Array.isArray(productsData)
            ? productsData
            : [];

        console.log("Extracted products array:", products);
        console.log("Products count:", products.length);

        if (products.length === 0) {
            container.innerHTML =
                '<p class="text-muted">Chưa có sản phẩm nào. <a href="/products" target="_blank">Thêm sản phẩm mới</a></p>';
            return;
        }

        console.log("Generating HTML for products...");
        const html = products
            .map(
                (product) => `
            <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" value="${
                    product.id
                }" id="product_${product.id}">
                <label class="form-check-label" for="product_${product.id}">
                    <strong>${product.name}</strong><br>
                    <small class="text-muted">${formatPrice(
                        product.price
                    )} VNĐ - ${product.stock_quantity} trong kho</small>
                </label>
            </div>
        `
            )
            .join("");

        console.log("Setting innerHTML, HTML length:", html.length);
        container.innerHTML = html;
        console.log("Product selection HTML updated successfully");
    } catch (error) {
        console.error("Error loading products for selection:", error);
        container.innerHTML =
            '<p class="text-danger">Lỗi tải danh sách sản phẩm. <a href="/products" target="_blank">Quản lý sản phẩm</a></p>';
    }
}

async function createSession() {
    const selectedProducts = Array.from(
        document.querySelectorAll("#productSelection input:checked")
    ).map((cb) => parseInt(cb.value));

    if (selectedProducts.length === 0) {
        showNotification("warning", "Vui lòng chọn ít nhất một sản phẩm");
        return;
    }

    // Get avatar path from selection
    let avatarPath = null;
    const avatarSelect = document.getElementById("avatarSelect");

    if (avatarSelect.value) {
        // Avatar selected from dropdown - use the path directly
        avatarPath = avatarSelect.value;
        console.log("Using selected avatar path:", avatarPath);
    } else if (avatarPathInput) {
        // Manual path entered
        avatarPath = avatarPathInput;
        console.log("Using manual avatar path:", avatarPath);
    } else {
        showNotification("warning", "Vui lòng chọn avatar hoặc nhập đường dẫn");
        return;
    }

    // Get streaming settings with validation
    const enableStreaming = true;
    const waitTime = Math.max(
        1,
        Math.min(60, parseInt(document.getElementById("waitTime").value) || 10)
    );
    const fps = Math.max(
        1,
        Math.min(60, parseInt(document.getElementById("fps").value) || 25)
    );
    const batchSize = Math.max(
        1,
        Math.min(32, parseInt(document.getElementById("batchSize").value) || 4)
    );

    // Validate streaming settings
    if (waitTime < 1 || waitTime > 60) {
        showNotification("warning", "Thời gian chờ phải từ 1-60 giây");
        return;
    }

    if (fps < 1 || fps > 60) {
        showNotification("warning", "FPS phải từ 1-60");
        return;
    }

    if (batchSize < 1 || batchSize > 32) {
        showNotification("warning", "Batch size phải từ 1-32");
        return;
    }

    const formData = {
        title: document.getElementById("sessionTitle").value,
        description: document.getElementById("sessionDescription").value,
        avatar_path: avatarPath, // Use avatar_path instead of avatar_id
        product_ids: selectedProducts,
        // New streaming settings - use backend field names
        for_stream: enableStreaming,
        wait_duration: waitTime,
        fps: fps,
        batch_size: batchSize,
    };

    console.log("Creating session with data:", formData);

    try {
        const response = await fetch(`${API_BASE}/sessions`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(formData),
        });

        if (response.ok) {
            showNotification("success", "Tạo phiên live thành công");
            bootstrap.Modal.getInstance(
                document.getElementById("createSessionModal")
            ).hide();
            loadSessions();
        } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Failed to create session");
        }
    } catch (error) {
        console.error("Error creating session:", error);
        showNotification("error", `Lỗi tạo phiên live: ${error.message}`);
    }
}

async function prepareSession(sessionId) {
    showLoading(
        "Đang chuẩn bị phiên live... Vui lòng chờ (có thể mất vài phút)"
    );

    try {
        const response = await fetch(
            `${API_BASE}/sessions/${sessionId}/prepare`,
            {
                method: "POST",
            }
        );

        if (response.ok) {
            showNotification("info", "Bắt đầu chuẩn bị phiên live");
            loadSessions();
        } else {
            throw new Error("Failed to prepare session");
        }
    } catch (error) {
        console.error("Error preparing session:", error);
        showNotification("error", "Lỗi chuẩn bị phiên live");
        hideLoading();
    }
}

async function startSession(sessionId) {
    try {
        const response = await fetch(
            `${API_BASE}/sessions/${sessionId}/start`,
            {
                method: "POST",
            }
        );

        if (response.ok) {
            showNotification("success", "Phiên live đã bắt đầu");
            loadSessions();
            window.location.href = `/live/${sessionId}`;
        } else {
            throw new Error("Failed to start session");
        }
    } catch (error) {
        console.error("Error starting session:", error);
        showNotification("error", "Lỗi bắt đầu phiên live");
    }
}

async function stopSession(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/sessions/${sessionId}/stop`, {
            method: "POST",
        });

        if (response.ok) {
            showNotification("success", "Phiên live đã dừng");
            loadSessions();
        } else {
            throw new Error("Failed to stop session");
        }
    } catch (error) {
        console.error("Error stopping session:", error);
        showNotification("error", "Lỗi dừng phiên live");
    }
}

// Utility functions
function formatPrice(price) {
    return new Intl.NumberFormat("vi-VN").format(price);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleString("vi-VN");
}

function getStatusBadgeClass(status) {
    const classes = {
        preparing: "bg-secondary",
        processing: "bg-warning",
        ready: "bg-info",
        live: "bg-success",
        completed: "bg-primary",
        error: "bg-danger",
    };
    return classes[status] || "bg-secondary";
}

function getStatusText(status) {
    const texts = {
        preparing: "Chuẩn bị",
        processing: "Đang xử lý",
        ready: "Sẵn sàng",
        live: "Đang live",
        completed: "Hoàn thành",
        error: "Lỗi",
    };
    return texts[status] || status;
}

function getStreamingInfo(session) {
    if (!session || typeof session !== "object") {
        return "";
    }

    const streamingBadge = session.for_stream
        ? '<span class="badge bg-success me-1"><i class="fas fa-broadcast-tower"></i> Streaming</span>'
        : '<span class="badge bg-secondary me-1"><i class="fas fa-pause"></i> Không stream</span>';

    const fps = session.fps || session.stream_fps || 25;
    const batchSize = session.batch_size || 4;
    const waitTime = session.wait_duration || 10;

    return `
        <div class="mt-2">
            ${streamingBadge}
            <span class="badge bg-info me-1">${fps} FPS</span>
            <span class="badge bg-warning me-1">Batch: ${batchSize}</span>
            <span class="badge bg-light text-dark">Chờ: ${waitTime}s</span>
        </div>
    `;
}

function showNotification(type, message) {
    // Create notification element
    const notification = document.createElement("div");
    notification.className = `alert alert-${
        type === "error" ? "danger" : type
    } alert-dismissible fade show position-fixed`;
    notification.style.cssText =
        "top: 20px; right: 20px; z-index: 9999; min-width: 300px;";
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

function showLoading(message = "Đang xử lý...") {
    document.getElementById("loadingMessage").textContent = message;
    new bootstrap.Modal(document.getElementById("loadingModal")).show();
}

function hideLoading() {
    const modal = bootstrap.Modal.getInstance(
        document.getElementById("loadingModal")
    );
    if (modal) {
        modal.hide();
    }
}

async function loadAvatars() {
    try {
        const response = await fetch(`${API_BASE}/avatars`);
        availableAvatars = await response.json();
        console.log("Loaded avatars:", availableAvatars);
    } catch (error) {
        console.error("Error loading avatars:", error);
        availableAvatars = [];
    }
}

function loadAvatarSelection() {
    const select = document.getElementById("avatarSelect");

    // Reset: giữ đúng 1 placeholder
    select.innerHTML = '<option value="">-- Chọn avatar có sẵn --</option>';

    // Không có avatar nào
    if (!Array.isArray(availableAvatars) || availableAvatars.length === 0) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Không có avatar nào";
        option.disabled = true;
        select.appendChild(option);
        return;
    }

    // Tạo option cho tất cả avatar (không group)
    const frag = document.createDocumentFragment();

    availableAvatars.forEach((avatar) => {
        // Bỏ icon thư mục/hình/video ở đầu tên (nếu có)
        const cleanName = (avatar.name || "").replace(/^[📁🎬🖼️]\s*/, "");
        const label = `${cleanName}`;

        const option = document.createElement("option");
        option.value = avatar.video_path;
        option.textContent = label;

        frag.appendChild(option);
    });

    select.appendChild(frag);
}

function selectAvatar() {
    const select = document.getElementById("avatarSelect");
    // const input = document.getElementById("avatarVideo");
    const selectedPath = select.value;

    if (selectedPath) {
        // input.value = selectedPath;
        showVideoPreview(selectedPath);

        // Show helpful message for MuseTalk avatars
        const selectedAvatar = availableAvatars.find(
            (a) => a.video_path === selectedPath
        );
        if (selectedAvatar) {
            showNotification(
                "info",
                `Đã chọn avatar từ MuseTalk: ${selectedAvatar.name}`
            );
        }
    } else {
        hideVideoPreview();
    }
}

function showVideoPreview(videoPath) {
    const preview = document.getElementById("avatarPreview");
    const video = document.getElementById("previewVideo");
    const info = document.getElementById("videoInfo");

    if (!preview || !video || !info) {
        console.warn("Preview elements not found");
        return;
    }

    // Regular video preview
    video.src = videoPath;
    video.style.display = "block";
    if (document.getElementById("musetalkPreview")) {
        document.getElementById("musetalkPreview").style.display = "none";
    }

    // Find avatar info
    const avatar = availableAvatars.find((a) => a.path === videoPath);
    if (avatar) {
        info.textContent = `${avatar.name} (${formatFileSize(avatar.size)})`;
    } else {
        info.textContent = "Video preview";
    }
    preview.style.display = "block";
}

function hideVideoPreview() {
    const preview = document.getElementById("avatarPreview");
    if (preview) {
        preview.style.display = "none";
    }
}
