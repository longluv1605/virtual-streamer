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

// Q&A Management Variables
let unansweredQuestions = [];
let pendingQuestions = []; // Questions waiting to be auto-answered
let isPlayingAnswerVideo = false; // Flag to prevent multiple answer videos

// Initialize app
document.addEventListener("DOMContentLoaded", function () {
    initWebSocket();
    loadSession();
    loadComments();

    // Set up chat form
    document.getElementById("chatForm").addEventListener("submit", sendMessage);

    // Auto-scroll chat
    setInterval(scrollChatToBottom, 100000);

    // Check if admin (for demo purposes, always show admin panel)
    isAdmin = true;
    if (isAdmin) {
        document.getElementById("adminPanel").style.display = "block";
    }
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
        sessionProducts = await productsRes.json();

        updateSessionInfo();
        updateProgressBar();

        if (currentSession.status === "live") {
            if (!currentSession.for_stream) startLiveSession();
            else ensureRealtimeAndWebRTC();
        }
    } catch (error) {
        console.error("Error loading session:", error);
        showNotification("error", "Không tìm thấy phiên live");
    }
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

    // Update admin buttons
    // updateAdminButtons();
}

function updateProgressBar() {
    if (sessionProducts.length === 0) return;

    const progressContainer = document.getElementById("progressContainer");
    const progressBar = document.getElementById("progressBar");
    const progressText = document.getElementById("progressText");

    progressContainer.style.display = "block";

    const progress = ((currentProductIndex + 1) / sessionProducts.length) * 100;
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `${currentProductIndex + 1}/${
        sessionProducts.length
    }`;
}

// function updateAdminButtons() {
//     // const startBtn = document.getElementById("startSessionBtn");
//     // const pauseBtn = document.getElementById("pauseSessionBtn");
//     // const stopBtn = document.getElementById("stopSessionBtn");

//     switch (currentSession.status) {
//         case "ready":
//             startBtn.style.display = "block";
//             pauseBtn.style.display = "none";
//             stopBtn.style.display = "none";
//             break;
//         case "live":
//             startBtn.style.display = "none";
//             pauseBtn.style.display = "block";
//             stopBtn.style.display = "block";
//             break;
//         default:
//             startBtn.style.display = "none";
//             pauseBtn.style.display = "none";
//             stopBtn.style.display = "none";
//     }
// }

// Live session functions
function startLiveSession() {
    if (sessionProducts.length === 0) return;

    // Show first product
    showProduct(0);
}

function showProduct(index) {
    if (index >= sessionProducts.length) {
        // End of session
        endSession();
        return;
    }

    currentProductIndex = index;
    const product = sessionProducts[index];

    // Update current product info
    updateCurrentProductInfo(product);

    // Update next product preview
    updateNextProductInfo(index + 1);

    // Play product video
    playProductVideo(product);

    // Update progress
    updateProgressBar();
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

function playProductVideo(streamProduct) {
    const videoPlayer = document.getElementById("videoPlayer");

    if (streamProduct.video_path) {
        // video_path already contains the full path like "outputs/videos/filename.mp4"
        // so we just need to add leading slash to make it absolute
        videoPlayer.src = `/${streamProduct.video_path}`;
        videoPlayer.load();
        videoPlayer.play();

        // Auto-advance to next product when video ends
        videoPlayer.onended = function () {
            console.log(
                "Product video ended, checking for pending questions..."
            );
            console.log(`Pending questions count: ${pendingQuestions.length}`);

            // Auto-answer any pending questions before moving to next product
            // autoAnswerPendingQuestions();

            setTimeout(() => {
                nextProduct();
            }, 2000); // 2 second gap between products
        };
    } else {
        // Fallback if no video
        videoPlayer.src = "";
        showNotification("warning", "Video chưa sẵn sàng cho sản phẩm này");
    }
}

function nextProduct() {
    showProduct(currentProductIndex + 1);
}

// Play answer video on main video player
function playAnswerVideo(videoPath) {
    // Check if already playing an answer video
    if (isPlayingAnswerVideo) {
        console.log("Already playing an answer video, skipping new request");
        showNotification(
            "warning",
            "Đang phát video trả lời khác, vui lòng đợi..."
        );
        return;
    }

    const videoPlayer = document.getElementById("videoPlayer");

    // Store current product video info to resume later
    const currentSrc = videoPlayer.src;
    const currentTime = videoPlayer.currentTime;
    const wasPlaying = !videoPlayer.paused;

    // Set flag to prevent multiple answer videos
    isPlayingAnswerVideo = true;

    // Show notification
    showNotification("info", "Đang phát video trả lời câu hỏi...");

    // Play answer video
    videoPlayer.src = `/${videoPath}`;
    videoPlayer.load();
    videoPlayer.play();

    // When answer video ends, resume product video
    videoPlayer.onended = function () {
        console.log("Answer video ended, resuming product video");

        // Clear the flag
        isPlayingAnswerVideo = false;

        // Resume product video
        if (currentSrc) {
            videoPlayer.src = currentSrc;
            videoPlayer.load();
            videoPlayer.currentTime = currentTime;

            if (wasPlaying) {
                videoPlayer.play();
            }

            // Restore original onended handler for product video
            restoreProductVideoHandler();
        }

        showNotification("success", "Đã trả lời xong câu hỏi!");
    };
}

function restoreProductVideoHandler() {
    const videoPlayer = document.getElementById("videoPlayer");

    // Restore original product video end handler
    videoPlayer.onended = function () {
        console.log("Product video ended, checking for pending questions...");
        console.log(`Pending questions count: ${pendingQuestions.length}`);

        // Auto-answer any pending questions before moving to next product
        // autoAnswerPendingQuestions();

        setTimeout(() => {
            nextProduct();
        }, 2000); // 2 second gap between products
    };
}

// Auto-answer questions when product video ends
async function autoAnswerPendingQuestions() {
    if (pendingQuestions.length === 0) return;

    // Don't auto-answer if already playing an answer video
    if (isPlayingAnswerVideo) {
        console.log("Already playing answer video, deferring auto-answer");
        return;
    }

    console.log(`Auto-answering ${pendingQuestions.length} pending questions`);

    // Process only the first pending question to avoid conflicts
    const question = pendingQuestions[0];

    try {
        const response = await fetch(
            `${API_BASE}/sessions/${sessionId}/comments/auto-answer-question/${question.id}`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
            }
        );

        if (response.ok) {
            console.log(
                `Auto-answering question ${question.id}: ${question.message}`
            );
            showNotification(
                "info",
                `Đang tự động trả lời câu hỏi: "${question.message.substring(
                    0,
                    50
                )}..."`
            );

            // Remove the processed question from pending list
            pendingQuestions = pendingQuestions.filter(
                (q) => q.id !== question.id
            );
        } else {
            console.error(`Failed to auto-answer question ${question.id}`);
        }
    } catch (error) {
        console.error(`Error auto-answering question ${question.id}:`, error);
    }
}

function endSession() {
    showNotification("info", "Phiên live đã kết thúc");
    document.getElementById("currentProductInfo").style.display = "none";
    document.getElementById("nextProductInfo").style.display = "none";

    // Show thank you message
    const videoPlayer = document.getElementById("videoPlayer");
    videoPlayer.src = "";
    videoPlayer.poster =
        'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600"><rect width="800" height="600" fill="%23000"/><text x="400" y="300" text-anchor="middle" dy=".3em" fill="%23fff" font-size="40">Cảm ơn bạn đã theo dõi!</text></svg>';
}

// Chat functions
async function loadComments() {
    try {
        const response = await fetch(
            `${API_BASE}/sessions/${sessionId}/comments`
        );
        comments = await response.json();
        displayComments();
    } catch (error) {
        console.error("Error loading comments:", error);
    }
}

function displayComments() {
    const container = document.getElementById("chatMessages");
    comments.reverse();
    const html = comments
        .map(
            (comment) => `
        <div class="message ${comment.is_question ? "question" : ""}">
            <strong>${comment.username}:</strong> ${comment.message}
            <br><small class="text-muted">${formatTime(
                comment.timestamp
            )}</small>
            ${
                comment.is_question
                    ? `<br><small class="text-warning"><i class="fas fa-question-circle"></i> Câu hỏi</small>
                       ${
                           comment.answered && comment.answer_video_path
                               ? `<br><div class="answer-video mt-2">
                              <small class="text-success"><i class="fas fa-check-circle"></i> Đã trả lời:</small>
                              <br><small class="text-info">Video đã được chiếu trên màn hình chính</small>
                            </div>`
                               : comment.answered
                               ? '<br><small class="text-success"><i class="fas fa-check-circle"></i> Đã trả lời</small>'
                               : ""
                       }`
                    : ""
            }
        </div>
    `
        )
        .join("");

    container.innerHTML = html;
    scrollChatToBottom();
}

function addMessageToChat(comment) {
    const container = document.getElementById("chatMessages");

    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${comment.is_question ? "question" : ""}`;
    messageDiv.innerHTML = `
        <strong>${comment.username}:</strong> ${comment.message}
        <br><small class="text-muted">${formatTime(comment.timestamp)}</small>
        ${
            comment.is_question
                ? `<br><small class="text-warning"><i class="fas fa-question-circle"></i> Câu hỏi</small>
                   ${
                       comment.answered && comment.answer_video_path
                           ? `<br>
                                <div class="answer-video mt-2">
                                    <small class="text-success"><i class="fas fa-check-circle"></i> Đã trả lời:</small>
                                    
                                </div>`
                           : comment.answered
                           ? '<br><small class="text-success"><i class="fas fa-check-circle"></i> Đã trả lời</small>'
                           : ""
                   }`
                : ""
        }
    `;

    container.appendChild(messageDiv);
    scrollChatToBottom();

    // Add to comments array
    comments.push(comment);
}

async function sendMessage(event) {
    event.preventDefault();

    const username = document.getElementById("usernameInput").value.trim();
    const message = document.getElementById("messageInput").value.trim();
    const isQuestion = document.getElementById("isQuestionCheck").checked;

    if (!username || !message) {
        showNotification("warning", "Vui lòng nhập tên và tin nhắn");
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE}/sessions/${sessionId}/comments`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    username: username,
                    message: message,
                    is_question: isQuestion,
                }),
            }
        );

        if (response.ok) {
            document.getElementById("messageInput").value = "";
            document.getElementById("isQuestionCheck").checked = false;
        } else {
            throw new Error("Failed to send message");
        }
    } catch (error) {
        console.error("Error sending message:", error);
        showNotification("error", "Lỗi gửi tin nhắn");
    }
}

function scrollChatToBottom() {
    const container = document.getElementById("chatMessages");
    container.scrollTop = container.scrollHeight;
}

// Admin functions
async function startSession() {
    try {
        const response = await fetch(
            `${API_BASE}/sessions/${sessionId}/start`,
            {
                method: "POST",
            }
        );

        if (response.ok) {
            loadSession();
        } else {
            throw new Error("Failed to start session");
        }
    } catch (error) {
        console.error("Error starting session:", error);
        showNotification("error", "Lỗi bắt đầu phiên live");
    }
}

async function stopSession() {
    try {
        const response = await fetch(`${API_BASE}/sessions/${sessionId}/stop`, {
            method: "POST",
        });

        if (response.ok) {
            loadSession();
        } else {
            throw new Error("Failed to stop session");
        }
    } catch (error) {
        console.error("Error stopping session:", error);
        showNotification("error", "Lỗi dừng phiên live");
    }
}

function pauseSession() {
    const videoPlayer = document.getElementById("videoPlayer");
    if (videoPlayer.paused) {
        videoPlayer.play();
        document.getElementById("pauseSessionBtn").innerHTML =
            '<i class="fas fa-pause"></i> Tạm dừng';
    } else {
        videoPlayer.pause();
        document.getElementById("pauseSessionBtn").innerHTML =
            '<i class="fas fa-play"></i> Tiếp tục';
    }
}

async function showQuestions() {
    try {
        const response = await fetch(
            `${API_BASE}/sessions/${sessionId}/comments/questions`
        );
        const questions = await response.json();

        const container = document.getElementById("questionsList");

        if (questions.length === 0) {
            container.innerHTML =
                '<p class="text-muted">Không có câu hỏi nào chưa trả lời</p>';
        } else {
            const html = questions
                .map(
                    (question) => `
                <div class="card bg-secondary mb-3">
                    <div class="card-body">
                        <h6 class="card-title">${question.username}</h6>
                        <p class="card-text">${question.message}</p>
                        <small class="text-muted">${formatTime(
                            question.timestamp
                        )}</small>
                        <div class="mt-2">
                            <button class="btn btn-success btn-sm" onclick="markAnswered(${
                                question.id
                            })">
                                <i class="fas fa-check"></i> Đã trả lời
                            </button>
                        </div>
                    </div>
                </div>
            `
                )
                .join("");
            container.innerHTML = html;
        }

        new bootstrap.Modal(document.getElementById("questionsModal")).show();
    } catch (error) {
        console.error("Error loading questions:", error);
        showNotification("error", "Lỗi tải câu hỏi");
    }
}

async function markAnswered(commentId) {
    try {
        const response = await fetch(
            `${API_BASE}/sessions/${sessionId}/comments/${commentId}/answer`,
            {
                method: "PUT",
            }
        );

        if (response.ok) {
            showNotification("success", "Đã đánh dấu câu hỏi đã trả lời");
            // Refresh questions list
            showQuestions();
        } else {
            throw new Error("Failed to mark as answered");
        }
    } catch (error) {
        console.error("Error marking as answered:", error);
        showNotification("error", "Lỗi đánh dấu câu hỏi");
    }
}

// Utility functions
function formatPrice(price) {
    return new Intl.NumberFormat("vi-VN").format(price);
}

function formatTime(dateString) {
    return new Date(dateString).toLocaleTimeString("vi-VN");
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
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// Q&A Management Functions
async function loadUnansweredQuestions() {
    try {
        const response = await fetch(
            `${API_BASE}/sessions/${sessionId}/comments/questions/unanswered`
        );
        if (response.ok) {
            unansweredQuestions = await response.json();
            updateQuestionPanel();
        }
    } catch (error) {
        console.error("Error loading unanswered questions:", error);
    }
}

function updateQuestionPanel() {
    const questionCount = document.getElementById("questionCount");
    const questionsContainer = document.getElementById("unansweredQuestions");

    if (!questionCount || !questionsContainer) return;

    questionCount.textContent = unansweredQuestions.length;

    if (unansweredQuestions.length === 0) {
        questionsContainer.innerHTML =
            '<p class="text-muted small mb-0">Chưa có câu hỏi nào</p>';
        return;
    }

    questionsContainer.innerHTML = unansweredQuestions
        .map(
            (question) => `
        <div class="border rounded p-2 mb-2 bg-secondary">
            <div class="d-flex justify-content-between align-items-start mb-1">
                <strong class="text-warning small">${question.username}</strong>
                <small class="text-muted">${formatTime(
                    question.timestamp
                )}</small>
            </div>
            <p class="mb-2 small">${question.message}</p>
            <button class="btn btn-sm btn-primary" onclick="answerQuestion(${
                question.id
            })">
                <i class="fas fa-reply"></i> Trả lời
            </button>
        </div>
    `
        )
        .join("");
}

async function answerQuestion(commentId) {
    // Check if already processing an answer video
    if (isPlayingAnswerVideo) {
        showNotification(
            "warning",
            "Đang phát video trả lời khác, vui lòng đợi..."
        );
        return;
    }

    if (!confirm("Tạo video trả lời cho câu hỏi này?")) return;

    try {
        showNotification("info", "Đang tạo video trả lời...");

        const response = await fetch(
            `${API_BASE}/sessions/${sessionId}/comments/answer-question/${commentId}`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
            }
        );

        if (response.ok) {
            showNotification("success", "Đã bắt đầu tạo video trả lời!");
            // Remove from unanswered list
            unansweredQuestions = unansweredQuestions.filter(
                (q) => q.id !== commentId
            );
            // Remove from pending list as well
            pendingQuestions = pendingQuestions.filter(
                (q) => q.id !== commentId
            );
            updateQuestionPanel();

            // Note: Video will automatically play on main player when ready via WebSocket
        } else {
            const error = await response.json();
            showNotification(
                "error",
                error.detail || "Không thể tạo video trả lời"
            );
        }
    } catch (error) {
        console.error("Error answering question:", error);
        showNotification("error", "Lỗi khi tạo video trả lời");
    }
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
    });
}

// Enhanced WebSocket message handling for Q&A
function handleWebSocketMessage(data) {
    switch (data.type) {
        case "new_comment":
            if (data.session_id == sessionId) {
                addMessageToChat(data.comment);
                // If it's a question, add to unanswered list and pending list for auto-answer
                if (data.comment.is_question && !data.comment.answered) {
                    const questionData = {
                        id: data.comment.id,
                        username: data.comment.username,
                        message: data.comment.message,
                        timestamp: data.comment.timestamp,
                        session_id: data.comment.session_id,
                    };

                    unansweredQuestions.push(questionData);

                    // Also add to pending questions for auto-answer when video ends
                    pendingQuestions.push(questionData);

                    updateQuestionPanel();

                    console.log(
                        `New question added to pending list: "${data.comment.message}"`
                    );
                }
            }
            break;
        case "question_processing":
            if (data.session_id == sessionId) {
                showNotification("info", data.message);
            }
            break;
        case "question_answered":
            if (data.session_id == sessionId) {
                showNotification("success", data.message);

                // Only play answer video if not already playing one
                if (data.video_path && !isPlayingAnswerVideo) {
                    playAnswerVideo(data.video_path);
                    console.log(
                        "Playing answer video on main player:",
                        data.video_path
                    );
                } else if (data.video_path && isPlayingAnswerVideo) {
                    console.log(
                        "Answer video ready but already playing another, queuing for later"
                    );
                    showNotification(
                        "info",
                        "Video trả lời đã sẵn sàng, sẽ phát sau khi video hiện tại kết thúc"
                    );
                }

                // Reload comments to show answer video in chat as well
                loadComments();
                loadUnansweredQuestions(); // Refresh the list

                // Remove from pending questions if it was auto-answered
                if (data.comment_id) {
                    pendingQuestions = pendingQuestions.filter(
                        (q) => q.id !== data.comment_id
                    );
                    console.log(
                        `Question ${data.comment_id} removed from pending list`
                    );
                }
            }
            break;
        case "question_error":
            if (data.session_id == sessionId) {
                showNotification("error", data.message);
            }
            break;
        case "session_started":
            if (data.session_id == sessionId) {
                loadSession();
                showNotification("success", "Phiên live đã bắt đầu!");
                // Show Q&A panel when session starts
                if (isAdmin) {
                    document.getElementById("qaPanel").style.display = "block";
                    loadUnansweredQuestions();
                    // Refresh questions every 30 seconds
                    setInterval(loadUnansweredQuestions, 30000);
                }
            }
            break;
        // case "session_stopped":
        //     if (data.session_id == sessionId) {
        //         loadSession();
        //         showNotification("info", "Phiên live đã kết thúc");
        //         // Hide Q&A panel when session stops
        //         document.getElementById("qaPanel").style.display = "none";
        //     }
        //     break;
    }
}

async function startWebRTC(sessionId, fps = 25) {
    if (window._webrtcStarted) return;
    const pc = new RTCPeerConnection();

    const videoEl = document.getElementById("videoPlayer");
    pc.ontrack = (e) => {
        if (e.track.kind === "video") {
            const ms = videoEl.srcObject || new MediaStream();
            ms.addTrack(e.track);
            videoEl.srcObject = ms;
        }
        // else if (e.track.kind === "audio") {
        //     // Nếu backend sau này thêm audio track
        //     let audioEl = document.getElementById("remoteAudio");
        //     if (!audioEl) {
        //         audioEl = document.createElement("audio");
        //         audioEl.id = "remoteAudio";
        //         audioEl.autoplay = true;
        //         document.body.appendChild(audioEl);
        //     }
        //     const msA = audioEl.srcObject || new MediaStream();
        //     msA.addTrack(e.track);
        //     audioEl.srcObject = msA;
        // }
    };

    console.log(`[${Date.now()}] Starting WebRTC with transceivers...`);
    
    // Add transceivers to indicate we want to receive video and audio
    // This is crucial - without this, createOffer() won't include media lines
    pc.addTransceiver("video", { direction: "recvonly" });
    pc.addTransceiver("audio", { direction: "recvonly" });

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
    console.log("- SDP content:", offer.sdp);

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

async function ensureRealtimeAndWebRTC() {
    if (window._webrtcStarted) {
        console.log("WebRTC started...");
        return;
    }
    try {
        // Khởi động realtime producer (chỉ cần nếu chưa chạy)
        await fetch(`/api/webrtc/realtime/start?session_id=${sessionId}`, {
            method: "POST",
        });
        console.log("Fetched /api/webrtc/realtime/start...");
    } catch (e) {
        console.warn("Realtime start failed (có thể đã chạy):", e);
    }
    const fps = currentSession?.fps || 25;
    await startWebRTC(sessionId, fps);
}
