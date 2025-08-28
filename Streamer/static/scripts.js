// API Base URL
const API_BASE = "/api";

// WebSocket connection
let ws = null;

// Global data
let templates = [];

// Initialize app
document.addEventListener("DOMContentLoaded", function () {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // initWebSocket();
    loadTemplates();
    displayTemplates();
});

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
