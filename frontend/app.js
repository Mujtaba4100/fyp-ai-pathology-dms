const API_BASE = "http://localhost:8000/api";
let currentFileId = null;

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

    // Show File Preview inside the drop zone
    const previewContainer = document.getElementById('file-preview-container');
    const imagePreview = document.getElementById('uploaded-image-preview');
    const pdfIcon = document.getElementById('pdf-preview-icon');
    const pdfName = document.getElementById('pdf-preview-name');
    
    if (file.type.startsWith('image/')) {
        imagePreview.src = URL.createObjectURL(file);
        imagePreview.style.display = 'block';
        pdfIcon.style.display = 'none';
        previewContainer.style.display = 'flex';
    } else if (file.type === 'application/pdf') {
        pdfName.textContent = file.name;
        pdfIcon.style.display = 'flex';
        imagePreview.style.display = 'none';
        previewContainer.style.display = 'flex';
    } else {
        previewContainer.style.display = 'none';
    }

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
        currentFileId = fileId;
        
        // Read user-selected extraction mode from frontend toggle
        const selectedMode = document.querySelector('input[name="extraction-mode"]:checked').value;
        const useVision = selectedMode === "vision";
        
        let cleanedText = "";
        
        if (!useVision) {
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
            
            cleanedText = cleanData.cleaned_text;
        } else {
            console.log(`[AI Pipeline] Bypassing Standard OCR. Routing directly to Llama-4 Vision API.`);
        }

        // --- STEP 4: HYBRID OCR/VISION EXTRACTION ---
        progressPercent.textContent = "Step 4: Parsing medical data using Hybrid OCR/Vision AI...";
        console.log(`[AI Pipeline] Mode selected: ${selectedMode.toUpperCase()} (force_vision: ${useVision})`);
        
        const extractResponse = await fetch(`${API_BASE}/extract/process-hybrid`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                ...getAuthHeader()
            },
            body: JSON.stringify({ 
                ocr_text: cleanedText, 
                file_id: fileId,
                force_vision: useVision
            })
        });
        if (!extractResponse.ok) throw new Error("Hybrid Extraction failed.");
        const extractData = await extractResponse.json();
        
        if (extractData.status !== "success" || !extractData.data) {
            throw new Error(extractData.message || "AI Extraction failed.");
        }
        
        // Render results on UI
        progressPercent.textContent = "Processing complete! Ready for clinical verification.";
        renderExtractionResults(extractData.data, extractData.method, fileId);
        
        // Hide progress block after a small delay
        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 2000);

    } catch (err) {
        console.error(err);
        progressPercent.textContent = `Error: ${err.message}`;
        alert(`Pipeline Error: ${err.message}`);
    }
}

// Render the structured pathology tables
function renderExtractionResults(data, method, fileId) {
    document.getElementById('extraction-placeholder').style.display = 'none';
    const resultsPanel = document.getElementById('extraction-results');
    resultsPanel.style.display = 'flex';

    // Reset Approve button state for new document
    const btnApprove = document.getElementById('btn-approve');
    if (btnApprove) {
        btnApprove.textContent = "Approve & Save to Database";
        btnApprove.style.backgroundColor = "";
        btnApprove.disabled = false;
    }

    // Set editable header fields
    document.getElementById('patient-name-input').value = data.patient_name || "";
    document.getElementById('test-type-input').value = data.test_type || "";
    document.getElementById('test-date-input').value = data.test_date || "";

    // Set clinical text blocks
    document.getElementById('diagnosis-input').value = data.diagnosis || "";
    document.getElementById('summary-input').value = data.summary || "";

    // Pipeline badge indicator
    const badge = document.getElementById('extraction-pipeline-method');
    if (method === "vision_llm") {
        badge.textContent = "Vision LLM Fallback (Llama-4)";
        badge.style.backgroundColor = "rgba(139, 92, 246, 0.15)";
        badge.style.color = "var(--accent-purple)";
    } else {
        badge.textContent = "OCR Text Extraction (Llama-3)";
        badge.style.backgroundColor = "var(--accent-teal-glass)";
        badge.style.color = "var(--accent-teal)";
    }

    // Render findings table rows as editable input boxes
    const tbody = document.getElementById('findings-body');
    tbody.innerHTML = "";

    if (data.findings && data.findings.length > 0) {
        data.findings.forEach((finding, idx) => {
            const tr = document.createElement('tr');
            
            tr.innerHTML = `
                <td><input type="text" class="findings-input" id="finding-name-${idx}" value="${finding.test_name || ""}"></td>
                <td>
                    <input type="text" class="findings-input" id="finding-val-${idx}" value="${finding.value || ""}" style="width: 70px;">
                    <input type="text" class="findings-input" id="finding-unit-${idx}" value="${finding.unit || ""}" style="width: 50px;">
                </td>
                <td><input type="text" class="findings-input" id="finding-range-${idx}" value="${finding.reference_range || ""}"></td>
                <td style="text-align: center;">
                    <input type="checkbox" class="checkbox-custom" id="finding-abnormal-${idx}" ${finding.is_abnormal ? 'checked' : ''}>
                </td>
            `;
            tbody.appendChild(tr);
        });
        tbody.dataset.count = data.findings.length;
    } else {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-secondary);">No findings values extracted. Click Save to save empty report or add rows manually.</td></tr>`;
        tbody.dataset.count = 0;
    }
}

// Clinician Approval & Submission
async function approveAndSaveReport() {
    if (!currentFileId) {
        alert("Error: No active document loaded.");
        return;
    }

    const btn = document.getElementById('btn-approve');
    const originalText = btn.textContent;
    btn.textContent = "Saving to EMR...";
    btn.disabled = true;
    let saveSuccess = false;

    try {
        const patientName = document.getElementById('patient-name-input').value.trim();
        const testType = document.getElementById('test-type-input').value.trim();
        const testDate = document.getElementById('test-date-input').value.trim();
        const diagnosis = document.getElementById('diagnosis-input').value.trim();
        const summary = document.getElementById('summary-input').value.trim();

        // Read findings rows
        const tbody = document.getElementById('findings-body');
        const count = parseInt(tbody.dataset.count || "0", 10);
        const findings = [];

        for (let idx = 0; idx < count; idx++) {
            const nameEl = document.getElementById(`finding-name-${idx}`);
            if (nameEl) {
                findings.push({
                    test_name: nameEl.value.trim(),
                    value: document.getElementById(`finding-val-${idx}`).value.trim(),
                    unit: document.getElementById(`finding-unit-${idx}`).value.trim(),
                    reference_range: document.getElementById(`finding-range-${idx}`).value.trim(),
                    is_abnormal: document.getElementById(`finding-abnormal-${idx}`).checked
                });
            }
        }

        const payload = {
            file_id: currentFileId,
            patient_name: patientName || null,
            test_type: testType || "Pathology Test",
            test_date: testDate || null,
            diagnosis: diagnosis || null,
            summary: summary,
            findings: findings
        };

        const response = await fetch(`${API_BASE}/extract/approve-save`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...getAuthHeader()
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Failed to save verified report.");
        }

        const resData = await response.json();
        saveSuccess = true;
        alert("🎉 Report Verified & Saved successfully in PostgreSQL EMR and Vector Search database!");
        
    } catch (err) {
        alert(`Verification failed: ${err.message}`);
    } finally {
        if (saveSuccess) {
            btn.textContent = "Saved successfully ✓";
            btn.style.backgroundColor = "var(--success-green)";
            btn.disabled = true;
        } else {
            btn.textContent = originalText;
            btn.disabled = false;
        }
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

// Manually trigger extraction using Llama 4 Vision LLM on the current file
async function forceVisionExtraction() {
    if (!currentFileId) {
        alert("No active document loaded.");
        return;
    }
    
    const progressContainer = document.getElementById('upload-progress');
    const progressFilename = document.getElementById('progress-filename');
    const progressPercent = document.getElementById('progress-percent');
    
    progressContainer.style.display = 'block';
    progressFilename.textContent = "Current Document";
    progressPercent.textContent = "Forcing multimodal visual analysis with Llama-4 Vision LLM...";
    
    try {
        const response = await fetch(`${API_BASE}/extract/process-hybrid`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                ...getAuthHeader()
            },
            body: JSON.stringify({ ocr_text: "", file_id: currentFileId, force_vision: true })
        });
        
        if (!response.ok) throw new Error("Vision extraction request failed.");
        const data = await response.json();
        
        if (data.status !== "success" || !data.data) {
            throw new Error(data.message || "Vision extraction failed.");
        }
        
        renderExtractionResults(data.data, data.method, currentFileId);
        progressPercent.textContent = "Vision extraction complete!";
        
        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 2000);
        
    } catch (err) {
        console.error(err);
        progressPercent.textContent = `Error: ${err.message}`;
        alert(`Vision Extraction Error: ${err.message}`);
    }
}

// Toggle UI layout classes when switching Standard vs Vision mode
function updateModeUI() {
    const selectedMode = document.querySelector('input[name="extraction-mode"]:checked').value;
    const ocrLabel = document.getElementById("mode-ocr-label");
    const visionLabel = document.getElementById("mode-vision-label");
    
    if (selectedMode === "ocr") {
        ocrLabel.classList.add("active");
        visionLabel.classList.remove("active");
    } else {
        visionLabel.classList.add("active");
        ocrLabel.classList.remove("active");
    }
}

// Make sure updateModeUI is global
window.updateModeUI = updateModeUI;
