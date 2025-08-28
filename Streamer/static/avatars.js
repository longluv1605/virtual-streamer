// API base URL
const API_BASE = "/api";

// Store loaded avatars
let avatars = [];

// Initialize page when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
    // Initialize Bootstrap tooltips if any
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Load existing avatars on page load
    loadAvatars();

    // Toggle compress options visibility when compress checkbox changes
    const compressCheckbox = document.getElementById("avatarCompress");
    if (compressCheckbox) {
        compressCheckbox.addEventListener("change", toggleCompressOptions);
    }
});

function loadAvatars() {
    fetch(`${API_BASE}/avatars`)
        .then((response) => response.json())
        .then((data) => {
            avatars = Array.isArray(data) ? data : [];
            displayAvatars();
        })
        .catch((error) => {
            console.error("Error loading avatars:", error);
            showNotification("error", "Lỗi tải danh sách avatar");
        });
}

function displayAvatars() {
    const container = document.getElementById("avatars-list");
    if (!container) return;

    if (!Array.isArray(avatars) || avatars.length === 0) {
        container.innerHTML = '<p class="text-muted">Chưa có avatar nào</p>';
        return;
    }

    const html = avatars
        .map((avatar) => {
            // For preview we use a video tag with object-fit: contain to display the entire frame.
            return `
                <div class="col-md-4 col-sm-6 mb-4">
                    <div class="card h-100 shadow-sm">
                        <div class="ratio ratio-16x9">
                            <video
                                src="${avatar.video_path}"
                                class="card-img-top"
                                muted
                                playsinline
                                preload="metadata"
                                style="object-fit: contain; width: 100%; height: 100%; border-top-left-radius: 0.25rem; border-top-right-radius: 0.25rem; background-color: #ffffffff;"
                            ></video>
                        </div>
                        <div class="card-body text-center">
                            <h5 class="card-title mb-2">${
                                avatar.name || "Avatar"
                            }</h5>
                        </div>
                    </div>
                </div>
            `;
        })
        .join("");

    container.innerHTML = html;
}

function showCreateAvatarModal() {
    const form = document.getElementById("createAvatarForm");
    if (form) {
        form.reset();
    }
    // Hide compress options by default when opening the modal
    const optionsDiv = document.getElementById("compressOptions");
    if (optionsDiv) {
        optionsDiv.style.display = "none";
    }
    const modalEl = document.getElementById("createAvatarModal");
    if (modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
}

async function createAvatar() {
    const createModalEl = document.getElementById("createAvatarModal");
    const createModalInstance = bootstrap.Modal.getInstance(createModalEl);
    // Nếu modal đã được khởi tạo, ẩn nó
    if (createModalInstance) {
        createModalInstance.hide();
    }

    const nameInput = document.getElementById("avatarName");
    const fileInput = document.getElementById("avatarFile");
    const compressInput = document.getElementById("avatarCompress");

    const name = nameInput?.value.trim();
    const file = fileInput?.files[0];
    const compress = compressInput?.checked;

    if (!name) {
        showNotification("warning", "Vui lòng nhập tên avatar");
        return;
    }
    if (!file) {
        showNotification("warning", "Vui lòng chọn video avatar");
        return;
    }

    try {
        // Step 1: upload the video file to server. Show a single loading modal.
        showLoading("Đang upload video avatar...");
        const formData = new FormData();
        formData.append("file", file);
        const uploadResp = await fetch(`${API_BASE}/avatars/upload`, {
            method: "POST",
            body: formData,
        });
        if (!uploadResp.ok) {
            const errorData = await uploadResp.json().catch(() => ({}));
            throw new Error(errorData.detail || "Upload video thất bại");
        }
        const uploadData = await uploadResp.json();
        const videoPath = uploadData.path || uploadData.video_path;
        if (!videoPath) {
            throw new Error("Đường dẫn video không hợp lệ");
        }

        // Step 2: create avatar record in database
        // Update loading message instead of showing a new modal
        const loadingMsgEl = document.getElementById("loadingMessage");
        if (loadingMsgEl) loadingMsgEl.textContent = "Đang tạo avatar...";
        const payload = {
            name: name,
            video_path: videoPath,
        };
        // Optional fields: include compression options if enabled
        if (compress) {
            payload.compress = true;
            // Read compression parameters
            const fpsValue = document.getElementById("compressFPS")?.value;
            const resValue =
                document.getElementById("compressResolution")?.value;
            const bitrateValue =
                document.getElementById("compressBitrate")?.value;
            if (fpsValue) payload.compress_fps = parseInt(fpsValue, 10);
            if (resValue) payload.compress_resolution = parseInt(resValue, 10);
            if (bitrateValue)
                payload.compress_bitrate = parseInt(bitrateValue, 10);
        }

        const createResp = await fetch(`${API_BASE}/avatars`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });
        if (!createResp.ok) {
            const errorData2 = await createResp.json().catch(() => ({}));
            throw new Error(errorData2.detail || "Tạo avatar thất bại");
        }

        // Success
        showNotification("success", "Tạo avatar thành công");
        hideLoading();
        // Hide the modal
        const modalInstance = bootstrap.Modal.getInstance(
            document.getElementById("createAvatarModal")
        );
        if (modalInstance) modalInstance.hide();
        // Refresh avatar list
        loadAvatars();
    } catch (error) {
        console.error("Error creating avatar:", error);
        hideLoading();
        showNotification("error", error.message || "Lỗi tạo avatar");
    }
}

function showNotification(type, message) {
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
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

function showLoading(message = "Đang xử lý...") {
    const msgEl = document.getElementById("loadingMessage");
    if (msgEl) msgEl.textContent = message;
    const modalEl = document.getElementById("loadingModal");
    if (modalEl) new bootstrap.Modal(modalEl).show();
}

function hideLoading() {
    const modalEl = document.getElementById("loadingModal");
    if (!modalEl) return;
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
}

function toggleCompressOptions() {
    const compressCheckbox = document.getElementById("avatarCompress");
    const optionsDiv = document.getElementById("compressOptions");
    if (!compressCheckbox || !optionsDiv) return;
    optionsDiv.style.display = compressCheckbox.checked ? "block" : "none";
}
