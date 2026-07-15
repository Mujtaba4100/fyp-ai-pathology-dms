const API_BASE = "http://localhost:8000/api";

// Authentication helpers
function getAuthHeader() {
    const token = localStorage.getItem("emr_auth_token");
    return token ? { "Authorization": `Bearer ${token}` } : {};
}

// Session check on page load
document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("emr_auth_token");
    if (token) {
        showDashboard();
    } else {
        showLogin();
    }
});

function showLogin() {
    document.getElementById("login-overlay").style.display = "flex";
    document.getElementById("main-dashboard").style.display = "none";
}

function showDashboard() {
    document.getElementById("login-overlay").style.display = "none";
    document.getElementById("main-dashboard").style.display = "flex";
}

async function submitLogin() {
    const userField = document.getElementById("login-username");
    const passField = document.getElementById("login-password");
    
    const username = userField.value.trim();
    const password = passField.value.trim();
    
    if (!username || !password) {
        alert("Please enter both username and password.");
        return;
    }
    await executeLogin(username, password);
}

async function quickLogin() {
    await executeLogin("admin", "admin123");
}

async function executeLogin(username, password) {
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Invalid login credentials.");
        }
        
        const data = await response.json();
        localStorage.setItem("emr_auth_token", data.access_token);
        showDashboard();
        
    } catch (err) {
        alert(`Authentication failed: ${err.message}`);
    }
}

function logoutUser() {
    localStorage.removeItem("emr_auth_token");
    showLogin();
}

// 1. Tab switching logic
function switchTab(tabName) {
    // Switch Sidebar items active state
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');

    // Switch panels visibility
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById(`tab-${tabName}`).classList.add('active');
}

// 2. File Ingestion & Pipeline automation
function triggerFileInput() {
    document.getElementById('file-input').click();
}

// Bind file selection change event
document.getElementById('file-input').addEventListener('change', function(e) {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

// Drag & Drop event bindings
const dropZone = document.getElementById('drop-zone');
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files[0]);
    }
});

// Resolution validation helper for low-res images
function validateImageResolution(file) {
    return new Promise((resolve) => {
        if (!file.type.startsWith("image/")) {
            resolve(true);
            return;
        }
        
        const img = new Image();
        img.src = URL.createObjectURL(file);
        
        img.onload = function() {
            URL.revokeObjectURL(img.src);
            if (this.width < 1000) {
                const proceed = confirm(
                    `⚠️ WARNING: Low Resolution Image\n\n` +
                    `The selected image is only ${this.width}x${this.height} pixels (less than 1000px wide).\n` +
                    `Low resolution can lead to OCR character recognition errors.\n\n` +
                    `We recommend uploading a scan or photo of at least 1500px wide.\n\n` +
                    `Do you want to proceed anyway?`
                );
                resolve(proceed);
            } else {
                resolve(true);
            }
        };
        
        img.onerror = function() {
            URL.revokeObjectURL(img.src);
            resolve(true);
        };
    });
}

// Complete automated extraction pipeline
async function handleFileUpload(file) {
    // Perform client-side quality check
    const proceed = await validateImageResolution(file);
    if (!proceed) return;

    const progressContainer = document.getElementById('upload-progress');
    const progressFilename = document.getElementById('progress-filename');
    const progressPercent = document.getElementById('progress-percent');
    
    const extractionPlaceholder = document.getElementById('extraction-placeholder');
    const extractionResults = document.getElementById('extraction-results');
    
    // Reset UI state
    progressContainer.style.display = 'block';
    progressFilename.textContent = file.name;
    progressPercent.textContent = "Step 1: Ingesting file...";
    
    extractionPlaceholder.style.display = 'flex';
    extractionResults.style.display = 'none';

    try {
        // --- STEP 1: UPLOAD FILE ---
        const formData = new FormData();
        formData.append("file", file);
        
        const uploadResponse = await fetch(`${API_BASE}/upload/`, {
            method: "POST",
            headers: { ...getAuthHeader() },
            body: formData
        });
        
        if (!uploadResponse.ok) throw new Error("Upload failed. Check server logs.");
        const uploadData = await uploadResponse.json();
        
        if (uploadData.status !== "success" || !uploadData.file_id) {
            throw new Error(uploadData.message || "Ingestion rejected by server.");
        }
        
        const fileId = uploadData.file_id;
        
        // --- STEP 2: RUN OCR ---
        progressPercent.textContent = "Step 2: Processing OCR (Reading document)...";
        const ocrResponse = await fetch(`${API_BASE}/ocr/process/${fileId}`, {
            method: "POST",
            headers: { ...getAuthHeader() }
        });
        if (!ocrResponse.ok) throw new Error("OCR Processing failed.");
        const ocrData = await ocrResponse.json();
        
        if (ocrData.status !== "success") {
            throw new Error(ocrData.error_message || "OCR extraction failed.");
        }
        
        const rawText = ocrData.extracted_text;

        // --- STEP 3: CLEAN TEXT ---
        progressPercent.textContent = "Step 3: Cleaning & normalizing medical terms...";
        const cleanResponse = await fetch(`${API_BASE}/clean/text`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: rawText })
        });
        if (!cleanResponse.ok) throw new Error("Text cleaning failed.");
        const cleanData = await cleanResponse.json();
        
        if (cleanData.status !== "success") {
            throw new Error(cleanData.message || "Text cleaning failed.");
        }
        
        const cleanedText = cleanData.cleaned_text;

        // --- STEP 4: EXTRACT MEDICAL DATA (Groq LLM) ---
        progressPercent.textContent = "Step 4: Extracting pathology data using AI (Groq Llama-3)...";
        const extractResponse = await fetch(`${API_BASE}/extract/medical-data`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cleaned_text: cleanedText, file_id: fileId })
        });
        if (!extractResponse.ok) throw new Error("LLM Extraction failed.");
        const extractData = await extractResponse.json();
        
        if (extractData.status !== "success" || !extractData.data) {
            throw new Error(extractData.message || "AI Extraction failed.");
        }
        
        const medicalData = extractData.data;

        // --- STEP 5: GENERATE & SAVE EMBEDDINGS (Local) ---
        progressPercent.textContent = "Step 5: Generating search index embeddings (local Sentence-Transformer)...";
        const embedResponse = await fetch(`${API_BASE}/embeddings/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: cleanedText, file_id: fileId })
        });
        
        // Render results on UI
        progressPercent.textContent = "Processing complete!";
        renderExtractionResults(medicalData);
        
        // Hide progress block after a small delay
        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 3000);

    } catch (err) {
        console.error(err);
        progressPercent.textContent = `Error: ${err.message}`;
        alert(`Pipeline Error: ${err.message}`);
    }
}

// Render the structured pathology tables
function renderExtractionResults(data) {
    document.getElementById('extraction-placeholder').style.display = 'none';
    const resultsPanel = document.getElementById('extraction-results');
    resultsPanel.style.display = 'flex';

    // Set header fields
    document.getElementById('patient-name').textContent = data.patient_name || "Not Found";
    document.getElementById('test-type').textContent = data.test_type || "Not Found";
    document.getElementById('test-date').textContent = data.test_date || "Not Found";

    // Set clinical blocks
    document.getElementById('diagnosis-text').textContent = data.diagnosis || "No primary diagnosis extracted.";
    document.getElementById('summary-text').textContent = data.summary || "No summary provided.";

    // Render findings table rows
    const tbody = document.getElementById('findings-body');
    tbody.innerHTML = "";

    if (data.findings && data.findings.length > 0) {
        data.findings.forEach(finding => {
            const tr = document.createElement('tr');
            
            const badgeClass = finding.is_abnormal ? "status-badge abnormal" : "status-badge normal";
            const badgeLabel = finding.is_abnormal ? "Abnormal" : "Normal";
            
            tr.innerHTML = `
                <td><strong>${finding.test_name || "-"}</strong></td>
                <td>${finding.value || "-"} ${finding.unit || ""}</td>
                <td><code>${finding.reference_range || "-"}</code></td>
                <td><span class="${badgeClass}">${badgeLabel}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } else {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-secondary);">No findings values extracted.</td></tr>`;
    }
}

// 3. Search implementation (Semantic / Keyword)
async function performSearch(type) {
    const queryInput = document.getElementById('search-input');
    const query = queryInput.value.trim();
    
    if (!query) {
        alert("Please enter a search query.");
        return;
    }

    const loadingBlock = document.getElementById('search-loading');
    const resultsContainer = document.getElementById('search-results');

    // Reset list state
    loadingBlock.style.display = 'flex';
    resultsContainer.innerHTML = "";

    try {
        const endpoint = type === 'semantic' ? `${API_BASE}/search/semantic` : `${API_BASE}/search/keyword`;
        const bodyObj = type === 'semantic' ? { query: query, top_k: 5 } : { keyword: query, top_k: 5 };

        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(bodyObj)
        });

        if (!response.ok) throw new Error("Search request failed.");
        const data = await response.json();
        
        loadingBlock.style.display = 'none';

        if (data.status === "success" && data.results && data.results.length > 0) {
            renderSearchResults(data.results, type);
        } else {
            resultsContainer.innerHTML = `
                <div class="search-empty-state">
                    <span>No matching medical documents found.</span>
                </div>
            `;
        }

    } catch (err) {
        console.error(err);
        loadingBlock.style.display = 'none';
        resultsContainer.innerHTML = `
            <div class="search-empty-state" style="color: var(--error-red);">
                <span>Error: ${err.message}</span>
            </div>
        `;
    }
}

// Dynamically render search cards
function renderSearchResults(results, type) {
    const resultsContainer = document.getElementById('search-results');
    resultsContainer.innerHTML = "";

    results.forEach(res => {
        const card = document.createElement('div');
        card.className = "search-result-card";
        
        const headerBadge = type === 'semantic' 
            ? `<span class="result-score-badge">Similarity: ${(res.similarity_score * 100).toFixed(1)}%</span>` 
            : `<span class="result-score-badge" style="background-color: rgba(59, 130, 246, 0.15); color: #60a5fa;">Keyword Match</span>`;

        card.innerHTML = `
            <div class="result-card-header">
                <span class="result-title">${res.patient_name || "Unknown Patient"}</span>
                ${headerBadge}
            </div>
            <div class="result-card-meta">
                <span><strong>Test:</strong> ${res.test_type || "Unknown"}</span>
                <span><strong>Doc ID:</strong> <code>${res.document_id}</code></span>
            </div>
            <div class="result-diag-block">
                <strong>Diagnosis:</strong> ${res.diagnosis || "No primary diagnosis extracted."}
            </div>
        `;
        resultsContainer.appendChild(card);
    });
}

// 4. RAG Chatbot Implementation
let chatHistory = [];

async function sendChatMessage() {
    const chatInput = document.getElementById('chat-input');
    const question = chatInput.value.trim();
    
    if (!question) return;

    // Render User Message bubble
    const messagesContainer = document.getElementById('chat-messages');
    renderBubble(messagesContainer, "user", question);
    
    // Clear input
    chatInput.value = "";
    
    // Render bot typing loading bubble
    const typingBubble = renderTypingIndicator(messagesContainer);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
        const response = await fetch(`${API_BASE}/chat/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question: question,
                conversation_history: chatHistory
            })
        });

        // Remove typing indicator
        typingBubble.remove();

        if (!response.ok) throw new Error("Q&A assistant request failed.");
        const data = await response.json();
        
        if (data.status === "success" && data.answer) {
            renderBubble(messagesContainer, "bot", data.answer);
            
            // Update local memory history
            chatHistory.push({ role: "user", content: question });
            chatHistory.push({ role: "assistant", content: data.answer });
            
            // Limit history context to last 6 messages
            if (chatHistory.length > 10) chatHistory = chatHistory.slice(-10);
        } else {
            renderBubble(messagesContainer, "bot", data.message || "Sorry, I encountered an issue processing that query.");
        }

    } catch (err) {
        console.error(err);
        typingBubble.remove();
        renderBubble(messagesContainer, "bot", `Error: ${err.message}`);
    }

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Render message bubbles
function renderBubble(container, role, text) {
    const bubble = document.createElement('div');
    bubble.className = role === 'user' ? "message message-user" : "message message-bot";
    
    const avatar = role === 'user' ? "👨‍⚕️" : "🤖";
    
    bubble.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <p>${text.replace(/\n/g, '<br>')}</p>
        </div>
    `;
    container.appendChild(bubble);
}

// Render typing animation
function renderTypingIndicator(container) {
    const bubble = document.createElement('div');
    bubble.className = "message message-bot typing";
    bubble.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="dot-pulse"></div>
            <div class="dot-pulse"></div>
            <div class="dot-pulse"></div>
        </div>
    `;
    container.appendChild(bubble);
    return bubble;
}
