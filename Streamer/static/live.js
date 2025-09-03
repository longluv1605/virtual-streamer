// Get session ID from URL
const sessionId = window.location.pathname.split("/").pop();

// API Base URL
const API_BASE = "/api";

// WebSocket connection
let ws = null;

// Global variables
let currentSession = null;
let sessionProducts = [];
let currentProductIndex = 0;
let comments = [];
let isAdmin = false; // In real app, this would be determined by authentication
let waitDuration = 0;

let liveConfig = null;

// ==== KHỞI TẠO ====
// Hiện modal ngay khi vào trang, chưa khởi động websocket/session vội
document.addEventListener("DOMContentLoaded", function () {
    showLiveSetupModal({
        onSubmit: (cfg) => {
            // Lưu lại để chỗ khác dùng
            liveConfig = cfg;

            // initWebSocket(); // nếu cần truyền cfg
            // loadSession(); // hoặc startLive(liveConfig) tuỳ flow của bạn
        },
    });
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
        setTimeout(initWebSocket, 3000);
    };
}

// Session functions
async function loadSession() {
    try {
        const [sessionRes, productsRes] = await Promise.all([
            fetch(`${API_BASE}/sessions/${sessionId}`),
            fetch(`${API_BASE}/sessions/${sessionId}/products`),
        ]);

        if (!sessionRes.ok) {
            throw new Error("Session not found");
        }

        currentSession = await sessionRes.json();
        console.log("Loaded session:", currentSession);
        sessionProducts = await productsRes.json();
        console.log("Loaded products:", sessionProducts);
        waitDuration = currentSession.wait_duration * 1000;

        if (currentSession.status === "live") {
            console.log("Starting live....");
            updateSessionInfo();
            initProductStreaming();
        }
    } catch (error) {
        console.error("Error loading session:", error);
        showNotification("error", "Không tìm thấy phiên live");
    }
}

// WebRTC
async function startWebRTC(sessionId, fps=25) {
    if (window._webrtcStarted) return;
    const pc = new RTCPeerConnection();

    const videoEl = document.getElementById("videoPlayer");

    pc.ontrack = (e) => {
        if (e.track.kind === "video") {
            const ms = videoEl.srcObject || new MediaStream();
            ms.addTrack(e.track);
            videoEl.srcObject = ms;
        }
    };

    console.log(`[${Date.now()}] Starting WebRTC with transceivers...`);

    // Add transceivers to indicate we want to receive video only
    // This is crucial - without this, createOffer() won't include media lines
    pc.addTransceiver("video", { direction: "recvonly" });

    console.log(
        "Created transceivers, PC transceivers count:",
        pc.getTransceivers().length
    );

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    console.log("Sending WebRTC offer:");
    console.log("- Session ID:", sessionId);
    console.log("- Type:", offer.type);
    console.log("- SDP length:", offer.sdp?.length);

    const res = await fetch("/api/webrtc/offer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            session_id: sessionId,
            sdp: offer.sdp,
            type: offer.type,
            fps: fps,
        }),
    });
    if (!res.ok) {
        console.error("Offer failed");
        return;
    }
    const answer = await res.json();
    await pc.setRemoteDescription(answer);

    window._webrtcStarted = true;
    window._pc = pc;
}

// ------------------------------------------------------------
// New product streaming classes and functions
// ------------------------------------------------------------
// AudioPlayer is a simplified audio controller that manages a product
// audio element at a time. It exposes basic playback controls and
// properties used by the synchronization logic. When a new product
// starts streaming, the existing audio is replaced entirely.
class AudioPlayer {
    constructor() {
        this.audio = null;
        this.autoStarted = false;
    }
    async load(url) {
        try {
            // Destroy previous audio if any
            if (this.audio) {
                this.audio.pause();
                this.audio.src = "";
                this.audio = null;
                this.autoStarted = false;
            }
            const absoluteUrl = url.startsWith("/")
                ? `${window.location.origin}${url}`
                : url;
            const audio = new Audio(absoluteUrl);
            audio.preload = "auto";
            audio.autoplay = false;
            audio.muted = false;
            audio.loop = false;
            // Wait until audio is ready to play through
            await new Promise((resolve, reject) => {
                audio.addEventListener("canplaythrough", () => resolve(true), {
                    once: true,
                });
                audio.addEventListener("error", (e) => reject(e), {
                    once: true,
                });
            });
            this.audio = audio;
            return true;
        } catch (err) {
            console.error("AudioPlayer load error", err);
            return false;
        }
    }
    play() {
        if (!this.audio) return;
        this.audio.play().catch((e) => console.warn("Audio play failed", e));
    }
    pause() {
        if (!this.audio) return;
        this.audio.pause();
    }
    get currentTime() {
        return this.audio ? this.audio.currentTime : 0;
    }
    get paused() {
        return this.audio ? this.audio.paused : true;
    }
}

// VideoAudioSync synchronizes a audio file with the video stream
// based on frame presentation times. It uses requestVideoFrameCallback when
// available to obtain the number of frames presented so far. Audio only
// begins after the first video frame is displayed, and it pauses if it
// runs ahead of the video by more than the configurable threshold.
class VideoAudioSync {
    constructor(videoEl, audioPlayer, fps, threshold = 0.2) {
        this.videoEl = videoEl;
        this.audioPlayer = audioPlayer;
        this.fps = fps;
        this.threshold = threshold;
        this.presentedFrames = 0;
        this.baselineFrames = null; // will be set on first frame
        this.active = false;
        this.syncInterval = null;
    }
    start() {
        if (this.active) return;
        this.active = true;
        this.setupFrameCallback();
        this.syncInterval = setInterval(() => this.performSync(), 100);
    }
    setupFrameCallback() {
        if (
            !this.videoEl ||
            typeof this.videoEl.requestVideoFrameCallback !== "function"
        ) {
            return;
        }
        const cb = (now, metadata) => {
            if (!this.active) return;
            this.presentedFrames = metadata.presentedFrames || 0;
            if (this.baselineFrames === null && this.presentedFrames > 0) {
                this.baselineFrames = this.presentedFrames;
            }
            this.videoEl.requestVideoFrameCallback(cb);
        };
        this.videoEl.requestVideoFrameCallback(cb);
    }
    performSync() {
        // Wait until audio is loaded
        if (!this.audioPlayer || !this.audioPlayer.audio) return;

        const relativeFrames = this.presentedFrames - this.baselineFrames;
        const videoTime = relativeFrames / this.fps;

        if (this.presentedFrames % 50 == 0) {
            console.log("==================================");
            console.log("Base frame = ", this.baselineFrames);
            console.log("Presented frame = ", this.presentedFrames);
            console.log("Relative frame = ", relativeFrames);
            console.log("Video time = ", videoTime);
        }
        // Condition 1: start audio after first frame has been displayed
        if (!this.audioPlayer.autoStarted && this.presentedFrames > 0) {
            console.log("Starting Sync...");
            this.audioPlayer.autoStarted = true;
            this.audioPlayer.play();
            return;
        }

        // Skip if not started yet
        if (!this.audioPlayer.autoStarted) return;
        const audioTime = this.audioPlayer.currentTime;

        // Condition 2: Pause audio if it runs ahead of video beyond threshold
        if (audioTime > videoTime + this.threshold) {
            if (!this.audioPlayer.paused) this.audioPlayer.pause();
        } else if (audioTime <= videoTime && this.audioPlayer.paused) {
            this.audioPlayer.play();
        }
    }
    stop() {
        this.active = false;
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
        }
    }
}

// Global variables for product streaming
let audioPlayer = null;
let syncController = null;
let productStatusInterval = null;

// Initialize product streaming by starting the first product automatically
function initProductStreaming() {
    if (!sessionProducts || sessionProducts.length === 0) {
        console.warn("No products available for streaming");
        return;
    }
    currentProductIndex = 0;
    const firstProduct = sessionProducts[0];
    const firstId = firstProduct.id || firstProduct.product_id;
    if (firstId) {
        startProductStream(firstId);
    } else {
        console.warn("First product does not have a valid id");
    }
}

// Start streaming for a specific product by calling the new backend API.
// This function handles starting WebRTC (if needed), loading audio, and
// initializing synchronization. It also begins polling the status API to
// detect when the server finishes generating frames for the current product.
async function startProductStream(productId) {
    if (!productId) {
        console.warn("startProductStream: productId is required");
        return;
    }
    try {
        product = sessionProducts[currentProductIndex];
        // Update current product info
        updateCurrentProductInfo(product);
        // Update next product preview
        updateNextProductInfo(currentProductIndex + 1);

        // Trigger backend to start generating frames for this product
        const url = `/api/webrtc/realtime/start?session_id=${sessionId}&product_id=${productId}`;
        const res = await fetch(url, { method: "POST" });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            console.error("Failed to start product stream", err);
            return;
        }
        const data = await res.json();
        const audioUrl = data.audio_url;
        const fps = data.fps || currentSession?.fps || 25;
        // Start WebRTC connection if not already started
        if (!window._webrtcStarted) {
            // Indicate that we are using product streaming so startWebRTC
            await startWebRTC(sessionId, fps);
        }
        // Load the audio file into our audio player
        if (!audioPlayer) audioPlayer = new AudioPlayer();
        const audioLoaded = await audioPlayer.load(audioUrl);
        if (!audioLoaded) {
            console.error("Could not load audio for product", productId);
        }
        // Stop any existing sync controller and start a new one
        if (syncController) {
            syncController.stop();
            syncController = null;
        }
        const videoEl = document.getElementById("videoPlayer");
        syncController = new VideoAudioSync(videoEl, audioPlayer, fps);
        syncController.start();

        // Poll the backend status periodically to detect when generation ends
        if (productStatusInterval) {
            clearInterval(productStatusInterval);
        }
        productStatusInterval = setInterval(async () => {
            await pollGenerationStatus();
        }, 1000);
    } catch (err) {
        console.error("startProductStream error", err);
    }
}

// Check backend generation status to know when the current product has finished.
// When generation completes, this function advances to the next product
// automatically. If there are no more products, it stops polling.
async function pollGenerationStatus() {
    try {
        const res = await fetch(`/api/webrtc/realtime/status/${sessionId}`);
        if (!res.ok) return;
        const data = await res.json();

        // If the server is not generating, the current product has finished
        if (data && data.is_generating === false) {
            if (productStatusInterval) {
                clearInterval(productStatusInterval);
                productStatusInterval = null;
            }

            // Stop current sync controller
            if (syncController) {
                syncController.stop();
                syncController = null;
            }

            // Advance to next product
            currentProductIndex++;
            if (
                sessionProducts &&
                currentProductIndex < sessionProducts.length
            ) {
                const nextProduct = sessionProducts[currentProductIndex];
                // product object may have id or product_id field
                const nextId =
                    nextProduct.id || nextProduct.product_id || nextProduct._id;
                if (nextId) {
                    await new Promise((r) => setTimeout(r, waitDuration));
                    startProductStream(nextId);
                }
            } else {
                console.log("All products streamed");
            }
        }
    } catch (err) {
        console.error("pollGenerationStatus error", err);
    }
}

function updateCurrentProductInfo(streamProduct) {
    const product = streamProduct.product;
    const container = document.getElementById("currentProductInfo");

    document.getElementById("currentProductName").textContent = product.name;
    document.getElementById("currentProductDescription").textContent =
        product.description || "Không có mô tả";
    document.getElementById("currentProductPrice").textContent =
        formatPrice(product.price) + " VNĐ";
    document.getElementById(
        "currentProductStock"
    ).textContent = `${product.stock_quantity} còn lại`;

    if (product.image_url) {
        document.getElementById("currentProductImage").src = product.image_url;
        document.getElementById("currentProductImage").style.display = "block";
    } else {
        document.getElementById("currentProductImage").style.display = "none";
    }

    container.style.display = "block";
}

function updateNextProductInfo(nextIndex) {
    const container = document.getElementById("nextProductInfo");

    if (nextIndex >= sessionProducts.length) {
        container.style.display = "none";
        return;
    }

    const nextProduct = sessionProducts[nextIndex].product;

    document.getElementById("nextProductName").textContent = nextProduct.name;
    document.getElementById("nextProductPrice").textContent =
        formatPrice(nextProduct.price) + " VNĐ";

    if (nextProduct.image_url) {
        document.getElementById("nextProductImage").src = nextProduct.image_url;
    } else {
        document.getElementById("nextProductImage").src =
            'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60" viewBox="0 0 60 60"><rect width="60" height="60" fill="%23ddd"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%23999">No Image</text></svg>';
    }

    container.style.display = "block";
}

// Utility functions
function formatPrice(price) {
    return new Intl.NumberFormat("vi-VN").format(price);
}

function updateSessionInfo() {
    document.getElementById("sessionTitle").textContent = currentSession.title;

    const statusIndicator = document.getElementById("statusIndicator");
    const statusText = document.getElementById("statusText");

    statusIndicator.className = "status-indicator";

    switch (currentSession.status) {
        case "preparing":
            statusIndicator.classList.add("status-preparing");
            statusText.textContent = "Đang chuẩn bị";
            break;
        case "ready":
            statusIndicator.classList.add("status-ready");
            statusText.textContent = "Sẵn sàng";
            break;
        case "live":
            statusIndicator.classList.add("status-live");
            statusText.textContent = "ĐANG LIVE";
            break;
        case "completed":
            statusIndicator.classList.add("status-ready");
            statusText.textContent = "Đã hoàn thành";
            break;
        default:
            statusText.textContent = currentSession.status;
    }
}


/////////////////////////////////////// Hủy setup
document.getElementById("liveSetupModal").addEventListener("shown.bs.modal", function () {
    const cancelBtn = document.querySelector("#liveSetupModal .btn-outline-secondary");
    if (cancelBtn) {
        cancelBtn.onclick = function () {
            window.location.href = "/sessions"; // hoặc window.close() nếu là popup
        };
    }
});

// ==== HÀM HIỆN & XỬ LÝ MODAL ====
function showLiveSetupModal({ onSubmit }) {
    const modalEl = document.getElementById("liveSetupModal");
    const form = document.getElementById("liveSetupForm");
    const platform = document.getElementById("platformSelect");
    const liveId = document.getElementById("liveIdInput");

    const modal = new bootstrap.Modal(modalEl, {
        backdrop: "static",
        keyboard: false,
    });

    // Fetch platforms and render options
    fetchPlatforms().then(platforms => {
        platform.innerHTML = '<option value="">-- Chọn nền tảng --</option>';
        platforms.forEach(p => {
            const opt = document.createElement("option");
            opt.value = p;
            opt.textContent = p.charAt(0).toUpperCase() + p.slice(1);
            platform.appendChild(opt);
        });
        modal.show();
    });

    // Xóa trạng thái invalid khi user chỉnh
    platform.addEventListener("change", () =>
        platform.classList.remove("is-invalid")
    );
    liveId.addEventListener("input", () =>
        liveId.classList.remove("is-invalid")
    );

    // Check configuration
    checkLiveConfig(modal, onSubmit, form, platform, liveId);
}

// Lấy các nền tảng hiện có
async function fetchPlatforms() {
    try {
        const res = await fetch("/api/chat/platforms");
        if (!res.ok) return [];
        const data = await res.json();
        return data.platforms || [];
    } catch {
        return [];
    }
}

// Check input
function checkLiveConfig(modal, onSubmit, form, platform, liveId) {
    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        let ok = true;

        if (!platform.value) {
            platform.classList.add("is-invalid");
            ok = false;
        }
        if (!liveId.value.trim()) {
            liveId.classList.add("is-invalid");
            ok = false;
        }
        if (!ok) return;

        const cfg = {
            platform: platform.value,
            live_id: liveId.value.trim(),
        };

        // Chờ validate trả về kết quả
        platform = cfg.platform.charAt(0).toUpperCase() + cfg.platform.slice(1);
        showLoading(`Đang kết nối tới nền tảng ${platform}...`);
        const valid = await startLiveChat(cfg);
        hideLoading();
        if (!valid) return;

        // Đóng modal trước khi bắt đầu live
        modal.hide();
        startChatPolling()

        // Callback để khởi động websocket/session sau khi pass validate
        if (typeof onSubmit === "function") onSubmit(cfg);
    });
}

// Kết nối vào nền tảng
async function startLiveChat(config) {
    const res = await fetch("/api/chat/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
    });
    if (!res.ok) {
        const err = await res.json();
        showNotification("error", err.detail || "Không thể bắt đầu phiên live.");
        return false;
    }
    showNotification("info", "Bắt đầu phiên live thành công!");
    return true;
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

// Live chat
let displayedComments = [];

function renderComment(comment) {
    const time = new Date(comment.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
    return `
        <div class="chat-message mb-2">
            <strong class="text-primary">${comment.author}</strong>
            <span class="text-muted ms-2" style="font-size:0.85em">${time}</span>
            <div>${comment.message}</div>
        </div>
    `;
}

function appendChatMessages(comments) {
    const chatMessages = document.getElementById("chatMessages");
    // Lọc các comment mới chưa hiển thị
    const newComments = comments.filter(c => !displayedComments.some(dc => dc.id === c.id));
    if (newComments.length > 0) {
        chatMessages.innerHTML += newComments.map(renderComment).join("");
        displayedComments = displayedComments.concat(newComments);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Poll comment sau khi kết nối thành công
let chatPolling = null;
function startChatPolling() {
    if (chatPolling) return;
    chatPolling = setInterval(async () => {
        const res = await fetch("/api/chat/comments");
        if (res.ok) {
            const data = await res.json();
            appendChatMessages(data.comments || []);
        }
    }, 2000);
}