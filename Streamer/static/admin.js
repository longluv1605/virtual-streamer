// API Base URL
const API_BASE = "/api";

// WebSocket connection
let ws = null;

// Global data
let products = [];
let sessions = [];
let templates = [];
let availableAvatars = [];
let databaseAvatars = []; // Avatars in database

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
    loadDashboard();
    // loadProducts();
    loadSessions();
    loadTemplates();
    loadAvatars();
    loadDatabaseAvatars(); // Load avatars from database
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

// Tab functions
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll(".tab-content").forEach((tab) => {
        tab.style.display = "none";
    });

    // Remove active class from all nav links
    document.querySelectorAll(".nav-link").forEach((link) => {
        link.classList.remove("active");
    });

    // Show selected tab
    document.getElementById(`${tabName}-tab`).style.display = "block";

    // Add active class to clicked nav link
    event.target.classList.add("active");

    // Load data for specific tabs
    switch (tabName) {
        case "dashboard":
            loadDashboard();
            break;
        case "products":
            loadProducts();
            break;
        case "sessions":
            loadSessions();
            break;
        case "templates":
            loadTemplates();
            break;
    }
}

// Dashboard functions
async function loadDashboard() {
    try {
        // Load summary data
        const [productsRes, sessionsRes, templatesRes] = await Promise.all([
            fetch(`${API_BASE}/products`),
            fetch(`${API_BASE}/sessions`),
            fetch(`${API_BASE}/templates`),
        ]);

        const productsData = await productsRes.json();
        const sessions = await sessionsRes.json();
        const templates = await templatesRes.json();

        console.log("Products response:", productsData);
        console.log("Sessions response:", sessions);

        // Extract products array from paginated response
        const products = Array.isArray(productsData.items)
            ? productsData.items
            : Array.isArray(productsData)
            ? productsData
            : [];

        console.log("Extracted products array:", products);
        console.log("Is products an array?", Array.isArray(products));

        // Update counters
        document.getElementById("total-products").textContent =
            productsData.total || products.length;
        document.getElementById("total-sessions").textContent = sessions.length;
        document.getElementById("live-sessions").textContent = sessions.filter(
            (s) => s.status === "live"
        ).length;
        document.getElementById("total-templates").textContent =
            templates.length;

        // Show recent sessions
        sessions.reverse();
        const recentSessions = sessions.slice(0, 5);
        const recentSessionsHtml = recentSessions
            .map(
                (session) => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <strong>${session.title}</strong><br>
                    <small class="text-muted">${formatDate(
                        session.created_at
                    )}</small>
                </div>
                <span class="badge ${getStatusBadgeClass(
                    session.status
                )}">${getStatusText(session.status)}</span>
            </div>
        `
            )
            .join("");
        document.getElementById("recent-sessions").innerHTML =
            recentSessionsHtml ||
            '<p class="text-muted">Chưa có phiên live nào</p>';

        // Show featured products
        const featuredProducts = products.slice(0, 5);
        const featuredProductsHtml = featuredProducts
            .map(
                (product) => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <strong>${product.name}</strong><br>
                    <small class="text-muted">${formatPrice(
                        product.price
                    )} VNĐ</small>
                </div>
                <span class="badge bg-success">${
                    product.stock_quantity
                } trong kho</span>
            </div>
        `
            )
            .join("");
        document.getElementById("featured-products").innerHTML =
            featuredProductsHtml ||
            '<p class="text-muted">Chưa có sản phẩm nào</p>';
    } catch (error) {
        console.error("Error loading dashboard:", error);
        showNotification("error", "Lỗi tải dashboard");
    }
}

// // Product functions
// async function loadProducts() {
//     try {
//         const response = await fetch(`${API_BASE}/products`);
//         const productsData = await response.json();
//         console.log("Products data in loadProducts:", productsData);
//         // Extract products array from paginated response
//         products = Array.isArray(productsData.items)
//             ? productsData.items
//             : Array.isArray(productsData)
//             ? productsData
//             : [];
//         console.log("Extracted products for global variable:", products);
//         console.log("Is products an array?", Array.isArray(products));
//         displayProducts();
//     } catch (error) {
//         console.error("Error loading products:", error);
//         showNotification("error", "Lỗi tải danh sách sản phẩm");
//     }
// }

// function displayProducts() {
//     const container = document.getElementById("products-list");

//     if (products.length === 0) {
//         container.innerHTML = '<p class="text-muted">Chưa có sản phẩm nào</p>';
//         return;
//     }

//     const html = products
//         .map(
//             (product) => `
//         <div class="card product-card mb-3">
//             <div class="card-body">
//                 <div class="row">
//                     <div class="col-md-2">
//                         ${
//                             product.image_url
//                                 ? `<img src="${product.image_url}" class="img-fluid rounded" alt="${product.name}">`
//                                 : '<div class="bg-light rounded d-flex align-items-center justify-content-center" style="height: 80px;"><i class="fas fa-image text-muted"></i></div>'
//                         }
//                     </div>
//                     <div class="col-md-8">
//                         <h5 class="card-title">${product.name}</h5>
//                         <p class="card-text">${
//                             product.description || "Không có mô tả"
//                         }</p>
//                         <p class="card-text">
//                             <strong>Giá: ${formatPrice(
//                                 product.price
//                             )} VNĐ</strong><br>
//                             <small class="text-muted">Danh mục: ${
//                                 product.category || "Không xác định"
//                             }</small><br>
//                             <small class="text-muted">Kho: ${
//                                 product.stock_quantity
//                             }</small>
//                         </p>
//                     </div>
//                     <div class="col-md-2 text-end">
//                         <span class="badge ${
//                             product.is_active ? "bg-success" : "bg-secondary"
//                         } mb-2">
//                             ${product.is_active ? "Hoạt động" : "Ngưng bán"}
//                         </span><br>
//                         <button class="btn btn-sm btn-outline-primary mb-1" onclick="editProduct(${
//                             product.id
//                         })">
//                             <i class="fas fa-edit"></i>
//                         </button>
//                         <button class="btn btn-sm btn-outline-danger" onclick="deleteProduct(${
//                             product.id
//                         })">
//                             <i class="fas fa-trash"></i>
//                         </button>
//                     </div>
//                 </div>
//             </div>
//         </div>
//     `
//         )
//         .join("");

//     container.innerHTML = html;
// }

function showAddProductModal() {
    document.getElementById("addProductForm").reset();
    new bootstrap.Modal(document.getElementById("addProductModal")).show();
}

async function addProduct() {
    const formData = {
        name: document.getElementById("productName").value,
        description: document.getElementById("productDescription").value,
        price: parseFloat(document.getElementById("productPrice").value),
        category: document.getElementById("productCategory").value,
        stock_quantity: parseInt(document.getElementById("productStock").value),
        image_url: document.getElementById("productImage").value,
    };

    try {
        const response = await fetch(`${API_BASE}/products`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(formData),
        });

        if (response.ok) {
            showNotification("success", "Thêm sản phẩm thành công");
            bootstrap.Modal.getInstance(
                document.getElementById("addProductModal")
            ).hide();
            // loadProducts();
            loadDashboard();
        } else {
            throw new Error("Failed to add product");
        }
    } catch (error) {
        console.error("Error adding product:", error);
        showNotification("error", "Lỗi thêm sản phẩm");
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
        await loadDatabaseAvatarSelection(); // Use database avatars
    } catch (error) {
        console.error("Error in showCreateSessionModal:", error);
    }
}

async function loadProductSelection() {
    const container = document.getElementById("productSelection");
    console.log("loadProductSelection called, container:", container);

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
    const avatarPathInput = document.getElementById("avatarVideo").value.trim();

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
            loadDashboard();
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
            loadDashboard();
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
            loadDashboard();
        } else {
            throw new Error("Failed to stop session");
        }
    } catch (error) {
        console.error("Error stopping session:", error);
        showNotification("error", "Lỗi dừng phiên live");
    }
}

// Template functions
async function loadTemplates() {
    try {
        const response = await fetch(`${API_BASE}/templates`);
        templates = await response.json();
        displayTemplates();
    } catch (error) {
        console.error("Error loading templates:", error);
        showNotification("error", "Lỗi tải danh sách template");
    }
}

function displayTemplates() {
    const container = document.getElementById("templates-list");

    if (templates.length === 0) {
        container.innerHTML = '<p class="text-muted">Chưa có template nào</p>';
        return;
    }

    const html = templates
        .map(
            (template) => `
        <div class="card mb-3">
            <div class="card-body">
                <h5 class="card-title">${template.name}</h5>
                <p class="card-text"><small class="text-muted">Danh mục: ${
                    template.category || "Không xác định"
                }</small></p>
                <div class="card-text">
                    <pre style="white-space: pre-wrap; font-size: 0.9rem;">${
                        template.template
                    }</pre>
                </div>
            </div>
        </div>
    `
        )
        .join("");

    container.innerHTML = html;
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

// Avatar functions
async function loadAvatars() {
    try {
        const response = await fetch(`${API_BASE}/avatars`);
        const data = await response.json();
        availableAvatars = data.avatars;
    } catch (error) {
        console.error("Error loading avatars:", error);
        availableAvatars = [];
    }
}

// Avatar management functions
async function loadDatabaseAvatars() {
    try {
        const response = await fetch(`${API_BASE}/avatars/database`);
        databaseAvatars = await response.json();
        console.log("Database avatars loaded:", databaseAvatars);
    } catch (error) {
        console.error("Error loading database avatars:", error);
        databaseAvatars = [];
    }
}

async function loadDatabaseAvatarSelection() {
    const select = document.getElementById("avatarSelect");

    // Clear existing options except the first one
    select.innerHTML = '<option value="">-- Chọn avatar --</option>';

    try {
        // Load fresh data
        await loadDatabaseAvatars();

        if (databaseAvatars.length === 0) {
            const option = document.createElement("option");
            option.value = "";
            option.textContent =
                "Chưa có avatar trong database. Hãy thêm avatar mới.";
            option.disabled = true;
            select.appendChild(option);
            return;
        }

        databaseAvatars.forEach((avatar) => {
            const option = document.createElement("option");
            option.value = avatar.id; // Use avatar ID instead of path
            option.textContent = `${avatar.name} ${
                avatar.is_prepared ? "Prepared" : "Pending"
            } (ID: ${avatar.id})`;
            if (!avatar.is_prepared) {
                option.style.color = "#6c757d"; // Gray for unprepared
            }
            select.appendChild(option);
        });
    } catch (error) {
        console.error("Error loading avatar selection:", error);
        select.innerHTML = '<option value="">Lỗi tải danh sách avatar</option>';
    }
}

async function createOrSelectAvatar() {
    const avatarPath = document.getElementById("avatarVideo").value.trim();
    if (!avatarPath) {
        showNotification("warning", "Vui lòng nhập đường dẫn avatar");
        return null;
    }

    try {
        // Check if avatar already exists in database
        const existingAvatar = databaseAvatars.find(
            (a) => a.video_path === avatarPath
        );
        if (existingAvatar) {
            console.log("Using existing avatar:", existingAvatar);
            return existingAvatar.id;
        }

        // Create new avatar in database
        const response = await fetch(`${API_BASE}/avatars/database`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                video_path: avatarPath,
                name: `Avatar ${Date.now()}`, // Generate name
                bbox_shift: 0,
            }),
        });

        if (response.ok) {
            const newAvatar = await response.json();
            console.log("Created new avatar:", newAvatar);
            // Refresh avatar list
            await loadDatabaseAvatars();
            return newAvatar.id;
        } else {
            throw new Error("Failed to create avatar");
        }
    } catch (error) {
        console.error("Error creating/selecting avatar:", error);
        showNotification("error", "Lỗi tạo/chọn avatar");
        return null;
    }
}

function loadAvatarSelection() {
    const select = document.getElementById("avatarSelect");

    // Clear existing options except the first one
    select.innerHTML = '<option value="">-- Chọn avatar có sẵn --</option>';

    if (availableAvatars.length === 0) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Không có avatar nào";
        option.disabled = true;
        select.appendChild(option);
        return;
    }

    availableAvatars.forEach((avatar) => {
        const option = document.createElement("option");
        option.value = avatar.path;
        option.textContent = `${avatar.name} (${formatFileSize(avatar.size)})`;
        select.appendChild(option);
    });
}

function selectAvatar() {
    const select = document.getElementById("avatarSelect");
    const input = document.getElementById("avatarVideo");
    const selectedAvatarId = select.value;

    if (selectedAvatarId) {
        // Find the selected avatar in database
        const selectedAvatar = databaseAvatars.find(
            (a) => a.id == selectedAvatarId
        );
        if (selectedAvatar) {
            input.value = selectedAvatar.video_path; // Show path for preview
            showVideoPreview(selectedAvatar.video_path);
        }
    } else {
        input.value = "";
        hideVideoPreview();
    }
}

function browseAvatar() {
    // Reload available avatars first
    loadAvatars().then(() => {
        loadAvatarSelection();
        showNotification("info", "Danh sách avatar đã được cập nhật");
    });
}

async function uploadAvatar() {
    const fileInput = document.getElementById("avatarUpload");
    const file = fileInput.files[0];

    if (!file) {
        return;
    }

    // Validate file type
    const validTypes = [
        "video/mp4",
        "video/avi",
        "video/mov",
        "video/x-msvideo",
        "video/quicktime",
    ];
    if (!validTypes.includes(file.type)) {
        showNotification("error", "Chỉ chấp nhận file video (MP4, AVI, MOV)");
        return;
    }

    // Validate file size (max 100MB)
    const maxSize = 100 * 1024 * 1024; // 100MB
    if (file.size > maxSize) {
        showNotification(
            "error",
            "File quá lớn. Vui lòng chọn file nhỏ hơn 100MB"
        );
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    showLoading("Đang upload avatar...");

    try {
        const response = await fetch(`${API_BASE}/avatars/upload`, {
            method: "POST",
            body: formData,
        });

        if (response.ok) {
            const result = await response.json();
            showNotification("success", "Upload avatar thành công!");

            // Update the input field and preview
            document.getElementById("avatarVideo").value = result.path;
            showVideoPreview(result.path);

            // Reload avatars list
            await loadAvatars();
            loadAvatarSelection();

            // Clear file input
            fileInput.value = "";
        } else {
            const error = await response.json();
            throw new Error(error.detail || "Upload failed");
        }
    } catch (error) {
        console.error("Error uploading avatar:", error);
        showNotification("error", `Lỗi upload: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function showVideoPreview(videoPath) {
    const preview = document.getElementById("avatarPreview");
    const video = document.getElementById("previewVideo");
    const info = document.getElementById("videoInfo");

    video.src = videoPath;

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
    document.getElementById("avatarPreview").style.display = "none";
}

function formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function isValidVideoPath(path) {
    if (!path || typeof path !== "string") {
        return false;
    }

    // Check if it's a valid static path or external URL
    const validExtensions = [".mp4", ".avi", ".mov", ".mkv", ".webm"];
    const lowercasePath = path.toLowerCase();

    // Check if path has valid video extension
    const hasValidExtension = validExtensions.some((ext) =>
        lowercasePath.endsWith(ext)
    );

    if (!hasValidExtension) {
        return false;
    }

    // Check if it's a valid path format
    return (
        path.startsWith("/static/avatars/") ||
        path.startsWith("http://") ||
        path.startsWith("https://") ||
        path.startsWith("./") ||
        path.startsWith("../")
    );
}

// Add event listener for manual input changes
document.addEventListener("DOMContentLoaded", function () {
    // Add event listener after DOM is loaded
    setTimeout(() => {
        const avatarInput = document.getElementById("avatarVideo");
        if (avatarInput) {
            avatarInput.addEventListener("input", function () {
                const path = this.value.trim();
                if (
                    path &&
                    (path.startsWith("/static/") ||
                        path.startsWith("http") ||
                        path.includes("MuseTalk"))
                ) {
                    showVideoPreview(path);
                } else {
                    hideVideoPreview();
                }
            });
        }
    }, 1000);
});

// Avatar functions (MuseTalk Integration)
async function loadAvatars() {
    try {
        const response = await fetch(`${API_BASE}/avatars`);
        const data = await response.json();
        availableAvatars = data.avatars;
        console.log("Loaded avatars:", availableAvatars);
    } catch (error) {
        console.error("Error loading avatars:", error);
        availableAvatars = [];
    }
}

function loadAvatarSelection() {
    const select = document.getElementById("avatarSelect");

    // Clear existing options except the first one
    select.innerHTML = '<option value="">-- Chọn avatar có sẵn --</option>';

    if (availableAvatars.length === 0) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Không có avatar nào";
        option.disabled = true;
        select.appendChild(option);
        return;
    }

    // Group avatars by source
    const groupedAvatars = {
        local: [],
        musetalk_video: [],
        musetalk_demo: [],
    };

    availableAvatars.forEach((avatar) => {
        if (groupedAvatars[avatar.source]) {
            groupedAvatars[avatar.source].push(avatar);
        }
    });

    // Add grouped options
    Object.entries(groupedAvatars).forEach(([source, avatars]) => {
        if (avatars.length > 0) {
            // Add group header
            const optgroup = document.createElement("optgroup");
            optgroup.label = getSourceLabel(source);

            avatars.forEach((avatar) => {
                const option = document.createElement("option");
                option.value = avatar.path;
                option.textContent = `${avatar.name.replace(
                    /^[📁🎬🖼️]\s*/,
                    ""
                )} (${formatFileSize(avatar.size)})`;

                // Add additional info for MuseTalk avatars
                if (avatar.source.startsWith("musetalk")) {
                    option.title = `${
                        avatar.type === "video"
                            ? "Video Avatar"
                            : "Image Avatar"
                    } từ MuseTalk`;
                }

                optgroup.appendChild(option);
            });

            select.appendChild(optgroup);
        }
    });
}

function getSourceLabel(source) {
    const labels = {
        local: "📁 Local Avatars",
        musetalk_video: "🎬 MuseTalk Videos (Khuyến nghị)",
        musetalk_demo: "🖼️ MuseTalk Demo Images",
    };
    return labels[source] || source;
}

function selectAvatar() {
    const select = document.getElementById("avatarSelect");
    const input = document.getElementById("avatarVideo");
    const selectedPath = select.value;

    if (selectedPath) {
        input.value = selectedPath;
        showVideoPreview(selectedPath);

        // Show helpful message for MuseTalk avatars
        const selectedAvatar = availableAvatars.find(
            (a) => a.path === selectedPath
        );
        if (selectedAvatar && selectedAvatar.source.startsWith("musetalk")) {
            showNotification(
                "info",
                `Đã chọn ${
                    selectedAvatar.type === "video" ? "video" : "ảnh"
                } avatar từ MuseTalk: ${selectedAvatar.name}`
            );
        }
    } else {
        hideVideoPreview();
    }
}

function browseAvatar() {
    // Reload available avatars first
    loadAvatars().then(() => {
        loadAvatarSelection();
        showNotification(
            "info",
            "Đã cập nhật danh sách avatar (bao gồm MuseTalk avatars)"
        );
    });
}

async function uploadAvatar() {
    const fileInput = document.getElementById("avatarUpload");
    const file = fileInput.files[0];

    if (!file) {
        return;
    }

    // Validate file type
    const validTypes = [
        "video/mp4",
        "video/avi",
        "video/mov",
        "video/x-msvideo",
        "video/quicktime",
    ];
    if (!validTypes.includes(file.type)) {
        showNotification("error", "Chỉ chấp nhận file video (MP4, AVI, MOV)");
        return;
    }

    // Validate file size (max 100MB)
    const maxSize = 100 * 1024 * 1024; // 100MB
    if (file.size > maxSize) {
        showNotification(
            "error",
            "File quá lớn. Vui lòng chọn file nhỏ hơn 100MB"
        );
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    showLoading("Đang upload avatar...");

    try {
        const response = await fetch(`${API_BASE}/avatars/upload`, {
            method: "POST",
            body: formData,
        });

        if (response.ok) {
            const result = await response.json();
            showNotification("success", "Upload avatar thành công!");

            // Update the input field and preview
            document.getElementById("avatarVideo").value = result.path;
            showVideoPreview(result.path);

            // Reload avatars list
            await loadAvatars();
            loadAvatarSelection();

            // Clear file input
            fileInput.value = "";
        } else {
            const error = await response.json();
            throw new Error(error.detail || "Upload failed");
        }
    } catch (error) {
        console.error("Error uploading avatar:", error);
        showNotification("error", `Lỗi upload: ${error.message}`);
    } finally {
        hideLoading();
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

    // For MuseTalk paths, we might need to handle them differently
    if (videoPath.includes("MuseTalk")) {
        // For MuseTalk files, show path info instead of actual preview
        info.textContent = "MuseTalk Avatar - Preview không khả dụng";
        preview.style.display = "block";
        video.style.display = "none";

        // Create a placeholder div
        if (!document.getElementById("musetalkPreview")) {
            const placeholder = document.createElement("div");
            placeholder.id = "musetalkPreview";
            placeholder.className =
                "bg-light rounded d-flex align-items-center justify-content-center";
            placeholder.style.cssText = "height: 150px; max-width: 100%;";
            placeholder.innerHTML =
                '<i class="fas fa-user-circle fa-3x text-muted"></i><br><small>MuseTalk Avatar</small>';

            video.parentNode.insertBefore(placeholder, video);
        }
        document.getElementById("musetalkPreview").style.display = "flex";
    } else {
        // Regular video preview
        video.src = videoPath;
        video.style.display = "block";
        if (document.getElementById("musetalkPreview")) {
            document.getElementById("musetalkPreview").style.display = "none";
        }

        // Find avatar info
        const avatar = availableAvatars.find((a) => a.path === videoPath);
        if (avatar) {
            info.textContent = `${avatar.name} (${formatFileSize(
                avatar.size
            )})`;
        } else {
            info.textContent = "Video preview";
        }
    }

    preview.style.display = "block";
}

function hideVideoPreview() {
    const preview = document.getElementById("avatarPreview");
    if (preview) {
        preview.style.display = "none";
    }
}
