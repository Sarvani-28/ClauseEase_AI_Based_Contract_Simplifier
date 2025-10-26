// Results page JavaScript for Flask templates
document.addEventListener('DOMContentLoaded', () => {
    // Data is passed from template via script tags
    if (typeof chartData !== 'undefined' && typeof statsData !== 'undefined') {
        createCharts();
    }
});

function displayResults() {
    if (!processedResults) return;
    
    document.getElementById('doc-filename').textContent = currentFilename;
    document.getElementById('file-count').textContent = '1 file processed successfully';
    
    document.getElementById('clause-count').textContent = processedResults.clause_count || 0;
    document.getElementById('terms-count').textContent = processedResults.legal_terms?.length || 0;
    document.getElementById('word-count').textContent = (processedResults.word_count || 0).toLocaleString();
    
    const simplifiedCount = processedResults.clauses?.filter(c => 
        c.simplified && c.simplified !== c.cleaned_text
    ).length || 0;
    document.getElementById('simplified-count').textContent = simplifiedCount;
    
    document.getElementById('clauses-subtitle').textContent = 
        `${processedResults.clause_count || 0} clauses found in the document`;
    document.getElementById('terms-subtitle').textContent = 
        `${processedResults.legal_terms?.length || 0} legal terms identified in the document`;
    document.getElementById('simplified-subtitle').textContent = 
        `Plain language version of your contract`;
    
    displayClauses();
    displayLegalTerms();
    displaySimplifiedText();
}

function displayClauses() {
    const clausesList = document.getElementById('clauses-list');
    
    if (!processedResults.clauses || processedResults.clauses.length === 0) {
        clausesList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <p>No clauses found in this document.</p>
            </div>
        `;
        return;
    }
    
    clausesList.innerHTML = processedResults.clauses.map(clause => `
        <div class="clause-card">
            <div class="clause-header-row">
                <div class="clause-title">Clause ${clause.index}</div>
                <span class="clause-type-badge">${clause.type || 'General'}</span>
            </div>
            <div class="clause-original">${escapeHtml(clause.cleaned_text)}</div>
        </div>
    `).join('');
}

function displayLegalTerms() {
    const termsList = document.getElementById('terms-list');
    
    if (!processedResults.legal_terms || processedResults.legal_terms.length === 0) {
        termsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚖️</div>
                <p>No legal terms found in this document.</p>
            </div>
        `;
        return;
    }
    
    termsList.innerHTML = `
        <div class="terms-grid">
            ${processedResults.legal_terms.map(term => `
                <div class="term-card">
                    <div class="term-name">${escapeHtml(term.term)}</div>
                    <span class="term-category">${escapeHtml(term.category || 'Legal Term')}</span>
                    ${term.definition ? `<div class="term-definition">${escapeHtml(term.definition)}</div>` : ''}
                </div>
            `).join('')}
        </div>
    `;
}

function displaySimplifiedText() {
    const simplifiedList = document.getElementById('simplified-list');
    
    if (!processedResults.clauses || processedResults.clauses.length === 0) {
        simplifiedList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">✨</div>
                <p>No simplified text available.</p>
            </div>
        `;
        return;
    }
    
    simplifiedList.innerHTML = processedResults.clauses.map(clause => `
        <div class="simplified-card">
            <div class="simplified-card-header">Clause ${clause.index}</div>
            <div class="simplified-text">${escapeHtml(clause.simplified || clause.cleaned_text)}</div>
        </div>
    `).join('');
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`${tabName}-content`).classList.add('active');
}

function displayReadabilityMetrics() {
    if (!processedResults) return;
    displayComparisonView();
}

function displayComparisonView() {
    if (!processedResults) return;
    
    const original = processedResults.original_readability || {};
    const simplified = processedResults.simplified_readability || {};
    
    document.getElementById('original-word-count').textContent = `${original.word_count || 0} words`;
    document.getElementById('original-sentence-count').textContent = `${original.sentence_count || 0} sentences`;
    document.getElementById('simplified-word-count').textContent = `${simplified.word_count || 0} words`;
    document.getElementById('simplified-sentence-count').textContent = `${simplified.sentence_count || 0} sentences`;
    
    const originalDisplay = document.getElementById('original-text-display');
    const originalText = processedResults.raw_text || 'No text available';
    const formattedOriginal = formatOriginalText(originalText);
    originalDisplay.innerHTML = highlightLegalTerms(formattedOriginal);
    
    const simplifiedDisplay = document.getElementById('simplified-text-display');
    if (processedResults.clauses && processedResults.clauses.length > 0) {
        const simplifiedText = processedResults.clauses.map(c => c.simplified).join(' ');
        const formattedSimplified = formatTextWithParagraphs(simplifiedText);
        simplifiedDisplay.innerHTML = formattedSimplified;
    } else {
        simplifiedDisplay.innerHTML = '<p style="color: #64748b; font-style: italic;">No simplified text available</p>';
    }
}

function formatOriginalText(text) {
    if (!text) return '<p style="color: #64748b;">No text available</p>';

    const normalized = text.replace(/\r\n/g, '\n');
    let paragraphs = normalized.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);

    if (paragraphs.length === 0) {
        paragraphs = normalized.split(/\n/).map(p => p.trim()).filter(Boolean);
    }

    if (paragraphs.length === 0) {
        paragraphs = [normalized.replace(/\s+/g, ' ').trim()];
    }

    return paragraphs
        .map(p => `<p style="margin-bottom: 18px; line-height: 1.9; text-align: justify; color: #1e293b;">${p}</p>`)
        .join('');
}

function formatTextWithParagraphs(text) {
    if (!text) return '<p style="color: #64748b;">No text available</p>';
    
    text = text.replace(/\s+/g, ' ').trim();
    const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
    
    let paragraphs = [];
    let currentParagraph = [];
    
    sentences.forEach((sentence, index) => {
        const trimmedSentence = sentence.trim();
        if (trimmedSentence) {
            currentParagraph.push(trimmedSentence);
            
            if ((index + 1) % 2 === 0 || index === sentences.length - 1) {
                if (currentParagraph.length > 0) {
                    paragraphs.push(currentParagraph.join(' '));
                    currentParagraph = [];
                }
            }
        }
    });
    
    if (paragraphs.length === 0) {
        paragraphs = [text];
    }
    
    return paragraphs
        .map(p => `<p style="margin-bottom: 18px; line-height: 1.9; text-align: justify; color: #1e293b;">${p}</p>`)
        .join('');
}

function formatTextAsNumberedList(text) {
    if (!text) return '<p style="color: #64748b;">No text available</p>';
    
    text = text.replace(/\s+/g, ' ').trim();
    const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
    
    if (sentences.length === 0) {
        return '<p style="color: #64748b;">No text available</p>';
    }
    
    let html = '<ol style="padding-left: 24px; margin: 0;">';
    
    sentences.forEach((sentence, index) => {
        const trimmedSentence = sentence.trim();
        if (trimmedSentence) {
            html += `
                <li style="
                    margin-bottom: 20px;
                    line-height: 1.9;
                    text-align: justify;
                    color: #1e293b;
                    padding-left: 8px;
                    font-size: 15px;
                ">
                    ${trimmedSentence}
                </li>
            `;
        }
    });
    
    html += '</ol>';
    return html;
}

function highlightLegalTerms(text) {
    if (!processedResults.legal_terms || processedResults.legal_terms.length === 0) {
        return text;
    }
    
    let highlightedText = text;
    processedResults.legal_terms.forEach(term => {
        const regex = new RegExp(`\\b${term.term}\\b`, 'gi');
        highlightedText = highlightedText.replace(regex, 
            `<span class="highlight-legal" title="${term.explanation || ''}">${term.term}</span>`
        );
    });
    
    return highlightedText;
}

let readabilityChart = null;
let statsChart = null;

function createCharts() {
    // Create placeholder charts - in a full implementation, you would use Chart.js
    const clauseTypeCanvas = document.getElementById('clauseTypeChart');
    if (clauseTypeCanvas) {
        const container = clauseTypeCanvas.parentElement;
        container.innerHTML = '<p style="color: #64748b; text-align: center; padding: 2rem;">Charts will be implemented with Chart.js</p>';
    }
    
    const statsCanvas = document.getElementById('statsChart');
    if (statsCanvas) {
        const container = statsCanvas.parentElement;
        container.innerHTML = '<p style="color: #64748b; text-align: center; padding: 2rem;">Charts will be implemented with Chart.js</p>';
    }
}

// Additional functionality can be added here as needed

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateDownloadButtonState() {
    const downloadBtn = document.getElementById('download-btn');
    if (!downloadBtn) return;

    if (currentDocumentId) {
        downloadBtn.disabled = false;
        downloadBtn.title = 'Download this report as JSON';
    } else {
        downloadBtn.disabled = true;
        downloadBtn.title = 'Download available after saving a document';
    }
}

async function downloadCurrentReport() {
    if (!currentDocumentId) {
        alert('Document reference not available. Please open the report from history.');
        return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
        alert('Session expired. Please login again.');
        window.location.href = '../auth/index.html#login';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/history/${currentDocumentId}/download`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Unable to download report');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const disposition = response.headers.get('Content-Disposition') || '';
        const matches = disposition.match(/filename="?([^";]+)"?/);
        const fallback = currentFilename ? `${currentFilename.replace(/\.[^/.]+$/, '')}-report.json` : `contract-report-${currentDocumentId}.json`;
        link.download = matches && matches[1] ? matches[1] : fallback;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Download error:', error);
        alert('Unable to download the report. Please try again later.');
    }
}
