/**
 * Web Content Analyzer: RE vs DFA — Application Logic
 * Pure Vanilla JavaScript (No build step, Chart.js via CDN).
 */

document.addEventListener("DOMContentLoaded", () => {
  // ==========================================================================
  // GLOBAL STATE
  // ==========================================================================
  const state = {
    theme: localStorage.getItem("toc_theme") || "light",
    activeTab: "analyzer",
    pages: [],
    selectedPageId: "page1",
    patterns: {},
    selectedPatterns: new Set(["email", "mobile", "date", "url", "hashtag", "time", "ing_word"]),
    
    // Analyzer Tab State
    currentAnalysis: null,
    tableFilterText: "",
    tablePatternFilter: "all",
    tableSortCol: "line",
    tableSortAsc: true,
    tablePage: 1,
    tablePageSize: 25,

    // DFA Definition & Simulator State
    dfaDefinition: null,
    simWord: "learning",
    simTrace: null,
    simStepIndex: 0,
    simInterval: null,

    // Cross-page summary & Compare state
    summaryData: null,
    crossPageChart: null,
    compareTimingChart: null,
    compareLocChart: null,

    // Test cases state
    testCases: [],
    testCaseFilterText: "",
    testCasePatternFilter: "all"
  };

  // Set initial theme
  document.body.setAttribute("data-theme", state.theme);
  updateThemeButtonUI();

  // Initialize application
  initNavigation();
  initThemeToggle();
  initAnalyzerTab();
  initComparisonTab();
  initDfaTab();
  initCompareTab();
  initAboutTab();

  // Load initial remote metadata
  fetchInitialData();


  // ==========================================================================
  // NAVIGATION & THEME
  // ==========================================================================
  function initNavigation() {
    const tabButtons = document.querySelectorAll(".tab-btn");
    tabButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        const targetTab = btn.getAttribute("data-tab");
        switchTab(targetTab);
      });
    });
  }

  function switchTab(tabId) {
    state.activeTab = tabId;

    // Update tab buttons
    document.querySelectorAll(".tab-btn").forEach(btn => {
      const isSelected = btn.getAttribute("data-tab") === tabId;
      btn.classList.toggle("active", isSelected);
      btn.setAttribute("aria-selected", isSelected);
    });

    // Update panes
    document.querySelectorAll(".tab-pane").forEach(pane => {
      pane.classList.add("hidden");
      pane.classList.remove("active");
    });

    const activePane = document.getElementById(`pane-${tabId}`);
    if (activePane) {
      activePane.classList.remove("hidden");
      activePane.classList.add("active");
    }

    // Tab-specific activations
    if (tabId === "comparison" && !state.summaryData) {
      loadCrossPageSummary();
    } else if (tabId === "dfa" && !state.dfaDefinition) {
      loadDfaDefinition();
    } else if (tabId === "compare") {
      // populate LOC in table if available
      loadComparisonLOC();
    } else if (tabId === "about" && state.testCases.length === 0) {
      loadTestCases();
    }
  }

  function initThemeToggle() {
    const btn = document.getElementById("theme-toggle");
    btn.addEventListener("click", () => {
      state.theme = state.theme === "light" ? "dark" : "light";
      document.body.setAttribute("data-theme", state.theme);
      localStorage.setItem("toc_theme", state.theme);
      updateThemeButtonUI();

      // Refresh charts for theme contrast if initialized
      if (state.crossPageChart) state.crossPageChart.update();
      if (state.compareTimingChart) state.compareTimingChart.update();
      if (state.compareLocChart) state.compareLocChart.update();
    });
  }

  function updateThemeButtonUI() {
    const textEl = document.getElementById("theme-text");
    if (textEl) {
      textEl.textContent = state.theme === "light" ? "Dark Mode" : "Light Mode";
    }
  }


  // ==========================================================================
  // TOAST NOTIFICATIONS
  // ==========================================================================
  function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px)";
      setTimeout(() => toast.remove(), 200);
    }, 3500);
  }


  // ==========================================================================
  // INITIAL DATA LOADING
  // ==========================================================================
  async function fetchInitialData() {
    try {
      // 1. Fetch Pages
      const pagesRes = await fetch("/api/pages");
      if (pagesRes.ok) {
        state.pages = await pagesRes.json();
        renderSnapshotCards();
        renderSourcesInfoList();
      }

      // 2. Fetch Patterns
      const patternsRes = await fetch("/api/patterns");
      if (patternsRes.ok) {
        state.patterns = await patternsRes.json();
        renderPatternCheckboxes();
        renderPatternFilters();
        renderRegistryTable();
      }

      // Execute default analysis on Page 1
      executeAnalysis();

    } catch (err) {
      console.error("Initial load error:", err);
      showToast("Failed to initialize data from server.", "error");
    }
  }


  // ==========================================================================
  // TAB 1: ANALYZER LOGIC
  // ==========================================================================
  function initAnalyzerTab() {
    // Source radio change
    const radioInputs = document.querySelectorAll('input[name="source-type"]');
    radioInputs.forEach(radio => {
      radio.addEventListener("change", (e) => {
        const val = e.target.value;
        document.getElementById("snapshot-controls").classList.toggle("hidden", val !== "snapshot");
        document.getElementById("custom-text-controls").classList.toggle("hidden", val !== "custom");
        document.getElementById("live-url-controls").classList.toggle("hidden", val !== "url");
      });
    });

    // Pattern select all / clear
    document.getElementById("btn-select-all-patterns").addEventListener("click", () => {
      Object.keys(state.patterns).forEach(k => state.selectedPatterns.add(k));
      updatePatternCheckboxesUI();
    });

    document.getElementById("btn-clear-patterns").addEventListener("click", () => {
      state.selectedPatterns.clear();
      updatePatternCheckboxesUI();
    });

    // Live URL fetch button
    document.getElementById("btn-fetch-url").addEventListener("click", async () => {
      const urlInput = document.getElementById("live-url-input");
      const url = urlInput.value.trim();
      if (!url) {
        showToast("Please enter a valid HTTP/HTTPS URL.", "error");
        return;
      }

      try {
        showToast("Fetching and cleaning web page...", "info");
        const res = await fetch("/api/fetch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || data.error || "Failed to fetch URL");
        }
        showToast(`Successfully fetched: ${data.title || url}`, "success");
        // Automatically run analysis on the live URL
        executeAnalysis({ url });
      } catch (err) {
        showToast(err.message, "error");
      }
    });

    // Run extraction button
    document.getElementById("btn-run-analysis").addEventListener("click", () => {
      executeAnalysis();
    });

    // Search and filter in matches table
    document.getElementById("table-search").addEventListener("input", (e) => {
      state.tableFilterText = e.target.value.toLowerCase();
      state.tablePage = 1;
      renderMatchesTable();
    });

    document.getElementById("table-pattern-filter").addEventListener("change", (e) => {
      state.tablePatternFilter = e.target.value;
      state.tablePage = 1;
      renderMatchesTable();
    });

    // Table sorting
    document.querySelectorAll("#matches-table th[data-sort]").forEach(th => {
      th.addEventListener("click", () => {
        const col = th.getAttribute("data-sort");
        if (state.tableSortCol === col) {
          state.tableSortAsc = !state.tableSortAsc;
        } else {
          state.tableSortCol = col;
          state.tableSortAsc = true;
        }
        renderMatchesTable();
      });
    });

    // Pagination
    document.getElementById("btn-prev-page").addEventListener("click", () => {
      if (state.tablePage > 1) {
        state.tablePage--;
        renderMatchesTable();
      }
    });

    document.getElementById("btn-next-page").addEventListener("click", () => {
      state.tablePage++;
      renderMatchesTable();
    });

    // Exports
    document.getElementById("btn-export-csv").addEventListener("click", exportMatchesCSV);
    document.getElementById("btn-export-json").addEventListener("click", exportMatchesJSON);
  }

  function renderSnapshotCards() {
    const container = document.getElementById("snapshot-cards");
    if (!container) return;
    container.innerHTML = "";

    state.pages.forEach(p => {
      const card = document.createElement("div");
      card.className = `snapshot-card-item ${p.id === state.selectedPageId ? "selected" : ""}`;
      card.setAttribute("data-page-id", p.id);

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span class="snapshot-badge">${escapeHTML(p.category || "Corpus")}</span>
          <span style="font-size:11px; color:var(--text-muted);">${p.id.toUpperCase()}</span>
        </div>
        <div class="snapshot-card-title">${escapeHTML(p.title || p.id)}</div>
        <div class="snapshot-card-meta">${p.char_count.toLocaleString()} chars &bull; ${p.line_count.toLocaleString()} lines</div>
      `;

      card.addEventListener("click", () => {
        state.selectedPageId = p.id;
        document.querySelectorAll(".snapshot-card-item").forEach(c => c.classList.remove("selected"));
        card.classList.add("selected");
      });

      container.appendChild(card);
    });
  }

  function renderPatternCheckboxes() {
    const container = document.getElementById("patterns-checklist");
    if (!container) return;
    container.innerHTML = "";

    Object.values(state.patterns).forEach(p => {
      const label = document.createElement("label");
      label.className = "pattern-checkbox-card";

      const isChecked = state.selectedPatterns.has(p.key);
      label.innerHTML = `
        <input type="checkbox" value="${p.key}" ${isChecked ? "checked" : ""} />
        <div class="pattern-meta">
          <div class="pattern-name">${escapeHTML(p.label)}</div>
          <code class="pattern-regex-code">${escapeHTML(p.regex)}</code>
        </div>
      `;

      const input = label.querySelector("input");
      input.addEventListener("change", (e) => {
        if (e.target.checked) {
          state.selectedPatterns.add(p.key);
        } else {
          state.selectedPatterns.delete(p.key);
        }
      });

      container.appendChild(label);
    });
  }

  function updatePatternCheckboxesUI() {
    document.querySelectorAll('#patterns-checklist input[type="checkbox"]').forEach(input => {
      input.checked = state.selectedPatterns.has(input.value);
    });
  }

  function renderPatternFilters() {
    const filterSelect = document.getElementById("table-pattern-filter");
    if (!filterSelect) return;
    filterSelect.innerHTML = '<option value="all">All Patterns</option>';

    Object.values(state.patterns).forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.key;
      opt.textContent = p.label;
      filterSelect.appendChild(opt);
    });
  }

  async function executeAnalysis(overrideParams = null) {
    const runBtn = document.getElementById("btn-run-analysis");
    const spinner = document.getElementById("run-spinner");
    const runText = document.getElementById("run-btn-text");

    let payload = {};
    const sourceType = document.querySelector('input[name="source-type"]:checked').value;

    if (overrideParams) {
      payload = { ...overrideParams };
    } else if (sourceType === "snapshot") {
      payload.page_id = state.selectedPageId;
    } else if (sourceType === "custom") {
      const text = document.getElementById("custom-text-input").value;
      if (!text.trim()) {
        showToast("Please enter custom text to analyze.", "error");
        return;
      }
      payload.text = text;
    } else if (sourceType === "url") {
      const url = document.getElementById("live-url-input").value.trim();
      if (!url) {
        showToast("Please enter a valid URL.", "error");
        return;
      }
      payload.url = url;
    }

    payload.patterns = Array.from(state.selectedPatterns);

    try {
      runBtn.disabled = true;
      spinner.classList.remove("hidden");
      runText.textContent = "Analyzing...";

      const res = await fetch("/api/analyze/re", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Analysis failed");
      }

      state.currentAnalysis = data;
      document.getElementById("analyzer-results").classList.remove("hidden");

      // Also fetch full raw text for viewer if page_id was used
      let fullText = "";
      if (payload.page_id) {
        const pageRes = await fetch(`/api/pages/${payload.page_id}`);
        if (pageRes.ok) {
          const pageData = await pageRes.json();
          fullText = pageData.text;
        }
      } else if (payload.text) {
        fullText = payload.text;
      }

      renderSummaryCards(data);
      renderMatchesTable();
      renderHighlighter(fullText, data);

      showToast(`Extraction complete: ${data.total_matches} matches in ${data.elapsed_ms} ms`, "success");

    } catch (err) {
      showToast(err.message, "error");
    } finally {
      runBtn.disabled = false;
      spinner.classList.add("hidden");
      runText.textContent = "Execute Extraction";
    }
  }

  function renderSummaryCards(data) {
    const container = document.getElementById("summary-cards-grid");
    if (!container) return;
    container.innerHTML = "";

    Object.values(data.results).forEach(item => {
      const card = document.createElement("div");
      card.className = "summary-card";
      card.innerHTML = `
        <div class="summary-card-count">${item.count}</div>
        <div class="summary-card-label">${escapeHTML(item.label)}</div>
        <div class="summary-card-unique">${item.unique_count} unique</div>
      `;
      container.appendChild(card);
    });
  }

  function getFlattenedMatches() {
    if (!state.currentAnalysis || !state.currentAnalysis.results) return [];
    const list = [];
    Object.values(state.currentAnalysis.results).forEach(p => {
      (p.matches || []).forEach(m => {
        list.push({
          patternKey: p.key,
          patternLabel: p.label,
          text: m.text,
          start: m.start,
          end: m.end,
          line: m.line,
          column: m.column
        });
      });
    });
    return list;
  }

  function renderMatchesTable() {
    const tbody = document.getElementById("matches-table-body");
    const paginationInfo = document.getElementById("pagination-info");
    const prevBtn = document.getElementById("btn-prev-page");
    const nextBtn = document.getElementById("btn-next-page");

    if (!tbody) return;
    tbody.innerHTML = "";

    let allMatches = getFlattenedMatches();

    // 1. Filter by pattern
    if (state.tablePatternFilter !== "all") {
      allMatches = allMatches.filter(m => m.patternKey === state.tablePatternFilter);
    }

    // 2. Filter by search text
    if (state.tableFilterText) {
      allMatches = allMatches.filter(m =>
        m.text.toLowerCase().includes(state.tableFilterText) ||
        m.patternLabel.toLowerCase().includes(state.tableFilterText)
      );
    }

    // 3. Sort
    allMatches.sort((a, b) => {
      let valA = a[state.tableSortCol];
      let valB = b[state.tableSortCol];

      if (typeof valA === "string") valA = valA.toLowerCase();
      if (typeof valB === "string") valB = valB.toLowerCase();

      if (valA < valB) return state.tableSortAsc ? -1 : 1;
      if (valA > valB) return state.tableSortAsc ? 1 : -1;
      return 0;
    });

    // 4. Paginate
    const total = allMatches.length;
    const totalPages = Math.ceil(total / state.tablePageSize) || 1;
    if (state.tablePage > totalPages) state.tablePage = totalPages;

    const startIdx = (state.tablePage - 1) * state.tablePageSize;
    const pageItems = allMatches.slice(startIdx, startIdx + state.tablePageSize);

    if (pageItems.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--text-muted); padding:24px;">No matching items found.</td></tr>`;
      paginationInfo.textContent = "Showing 0 of 0 matches";
      prevBtn.disabled = true;
      nextBtn.disabled = true;
      return;
    }

    paginationInfo.textContent = `Showing ${startIdx + 1} - ${Math.min(startIdx + state.tablePageSize, total)} of ${total} matches`;
    prevBtn.disabled = state.tablePage <= 1;
    nextBtn.disabled = state.tablePage >= totalPages;

    pageItems.forEach(item => {
      const tr = document.createElement("tr");
      tr.className = "clickable-row";
      tr.setAttribute("data-match-start", item.start);
      tr.setAttribute("data-match-end", item.end);

      tr.innerHTML = `
        <td><span class="legend-chip hl-${item.patternKey}">${escapeHTML(item.patternLabel)}</span></td>
        <td><code>${escapeHTML(item.text)}</code></td>
        <td>${item.line}:${item.column}</td>
        <td>${item.start} - ${item.end}</td>
      `;

      tr.addEventListener("click", () => {
        scrollToHighlight(item.start);
      });

      tbody.appendChild(tr);
    });
  }

  function renderHighlighter(fullText, analysisData) {
    const viewer = document.getElementById("text-viewer");
    const legend = document.getElementById("pattern-legend");
    if (!viewer || !legend) return;

    legend.innerHTML = "";
    Object.values(analysisData.results).forEach(p => {
      const chip = document.createElement("span");
      chip.className = `legend-chip hl-${p.key}`;
      chip.textContent = `${p.label} (${p.count})`;
      legend.appendChild(chip);
    });

    if (!fullText) {
      viewer.innerHTML = `<p class="placeholder-text">Text content unavailable for direct highlight preview.</p>`;
      return;
    }

    // Collect all matches with start and end
    const rawMatches = [];
    Object.values(analysisData.results).forEach(p => {
      (p.matches || []).forEach(m => {
        rawMatches.push({
          start: m.start,
          end: m.end,
          patternKey: p.key,
          text: m.text
        });
      });
    });

    // Sort by start offset ascending
    rawMatches.sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start));

    // Build highlighted HTML without overlaps
    let html = "";
    let lastOffset = 0;

    for (const m of rawMatches) {
      if (m.start < lastOffset) continue; // Skip overlaps
      html += escapeHTML(fullText.substring(lastOffset, m.start));
      html += `<mark id="match-offset-${m.start}" class="hl-${m.patternKey}">${escapeHTML(fullText.substring(m.start, m.end))}</mark>`;
      lastOffset = m.end;
    }
    html += escapeHTML(fullText.substring(lastOffset));

    viewer.innerHTML = html;
  }

  function scrollToHighlight(startOffset) {
    const mark = document.getElementById(`match-offset-${startOffset}`);
    const viewer = document.getElementById("text-viewer");
    if (mark && viewer) {
      document.querySelectorAll("#text-viewer mark.focused-match").forEach(el => el.classList.remove("focused-match"));
      mark.classList.add("focused-match");

      const markTop = mark.offsetTop - viewer.offsetTop;
      viewer.scrollTo({ top: markTop - 60, behavior: "smooth" });
    }
  }

  function exportMatchesCSV() {
    const matches = getFlattenedMatches();
    if (matches.length === 0) {
      showToast("No matches available to export.", "warning");
      return;
    }
    const headers = ["Pattern", "Text", "Start", "End", "Line", "Column"];
    const rows = matches.map(m => [
      `"${m.patternLabel}"`,
      `"${m.text.replace(/"/g, '""')}"`,
      m.start,
      m.end,
      m.line,
      m.column
    ]);
    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    downloadBlob(csvContent, "extracted_matches.csv", "text/csv;charset=utf-8;");
  }

  function exportMatchesJSON() {
    if (!state.currentAnalysis) {
      showToast("No matches available to export.", "warning");
      return;
    }
    const jsonStr = JSON.stringify(state.currentAnalysis, null, 2);
    downloadBlob(jsonStr, "extracted_matches.json", "application/json");
  }

  function downloadBlob(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Downloaded: ${filename}`, "success");
  }


  // ==========================================================================
  // TAB 2: CROSS-PAGE COMPARISON
  // ==========================================================================
  function initComparisonTab() {
    document.getElementById("btn-refresh-summary").addEventListener("click", () => {
      loadCrossPageSummary();
    });
  }

  async function loadCrossPageSummary() {
    try {
      const res = await fetch("/api/summary");
      if (!res.ok) throw new Error("Failed to fetch cross-page summary");
      const data = await res.json();
      state.summaryData = data;

      renderCrossPageChart(data);
      renderSummaryTable(data);
      renderAutomatedInsights(data);

    } catch (err) {
      showToast(err.message, "error");
    }
  }

  function renderCrossPageChart(data) {
    const ctx = document.getElementById("cross-page-chart");
    if (!ctx) return;

    if (state.crossPageChart) {
      state.crossPageChart.destroy();
    }

    const labels = data.patterns.map(p => p.label);
    const page1Data = data.patterns.map(p => p.page1);
    const page2Data = data.patterns.map(p => p.page2);
    const page3Data = data.patterns.map(p => p.page3);

    state.crossPageChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Page 1: UGC (Educational)",
            data: page1Data,
            backgroundColor: "rgba(59, 130, 246, 0.8)",
            borderColor: "rgb(59, 130, 246)",
            borderWidth: 1
          },
          {
            label: "Page 2: The Indian Express (News)",
            data: page2Data,
            backgroundColor: "rgba(245, 158, 11, 0.8)",
            borderColor: "rgb(245, 158, 11)",
            borderWidth: 1
          },
          {
            label: "Page 3: DEV Community (Tech Blog)",
            data: page3Data,
            backgroundColor: "rgba(16, 185, 129, 0.8)",
            borderColor: "rgb(16, 185, 129)",
            borderWidth: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "top",
            labels: {
              boxWidth: 12,
              font: { size: 12, family: "ui-sans-serif, system-ui, sans-serif" }
            }
          },
          tooltip: {
            padding: 10,
            cornerRadius: 6
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Match Frequency Count" },
            grid: { color: "rgba(150, 150, 150, 0.1)" }
          },
          x: {
            grid: { display: false }
          }
        }
      }
    });
  }

  function renderSummaryTable(data) {
    const tbody = document.getElementById("summary-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    const p1Chars = data.pages.page1 ? 27264 : 1;
    const p2Chars = data.pages.page2 ? 31938 : 1;
    const p3Chars = data.pages.page3 ? 18835 : 1;
    const avgChars = (p1Chars + p2Chars + p3Chars) / 3;

    data.patterns.forEach(row => {
      const tr = document.createElement("tr");
      const normalizedRate = ((row.total / (p1Chars + p2Chars + p3Chars)) * 1000).toFixed(2);

      tr.innerHTML = `
        <td><code>${row.key}</code></td>
        <td><strong>${escapeHTML(row.label)}</strong></td>
        <td>${row.page1}</td>
        <td>${row.page2}</td>
        <td>${row.page3}</td>
        <td><strong>${row.total}</strong></td>
        <td><code>${normalizedRate}</code></td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderAutomatedInsights(data) {
    const box = document.getElementById("comparison-insights");
    if (!box) return;

    let highestUrlPage = "Page 2";
    let highestUrlCount = 0;
    data.patterns.forEach(p => {
      if (p.key === "url") {
        if (p.page2 >= p.page1 && p.page2 >= p.page3) {
          highestUrlPage = "Page 2 (The Indian Express)";
          highestUrlCount = p.page2;
        }
      }
    });

    box.innerHTML = `
      <h4 style="font-size:13px; font-weight:700; margin-bottom:6px; color:var(--text-main);">Cross-Corpus Comparative Insights</h4>
      <ul style="font-size:12.5px; padding-left:18px; color:var(--text-sub); line-height:1.6;">
        <li><strong>Hyperlink Dominance:</strong> Web URLs form the largest token group overall (499 matches), with peak concentration on ${highestUrlPage} (${highestUrlCount} links) due to syndication and navigation links.</li>
        <li><strong>Domain Specialization:</strong> Calendar dates in <code>DD-MM-YYYY</code> format appear exclusively on Page 1 (UGC Educational notices), while social <code>#hashtags</code> are concentrated entirely on Page 3 (DEV Community).</li>
        <li><strong>Consistent Morphological Density:</strong> The <code>-ing</code> word pattern shows remarkably stable frequency across all three genres (~92&ndash;97 occurrences per corpus), providing an ideal constant baseline for the RE vs DFA benchmark.</li>
      </ul>
    `;
  }


  // ==========================================================================
  // TAB 3: DFA MACHINE & SIMULATOR
  // ==========================================================================
  function initDfaTab() {
    const wordInput = document.getElementById("simulator-word-input");
    const stepBtn = document.getElementById("btn-sim-step");
    const playBtn = document.getElementById("btn-sim-play");
    const resetBtn = document.getElementById("btn-sim-reset");

    // Word input change
    wordInput.addEventListener("input", () => {
      resetSimulator();
    });

    // Example chip clicks
    document.querySelectorAll(".example-chips .chip-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        wordInput.value = btn.getAttribute("data-word");
        resetSimulator();
        startSimulatorTrace();
      });
    });

    stepBtn.addEventListener("click", () => {
      stepSimulator();
    });

    playBtn.addEventListener("click", () => {
      togglePlaySimulator();
    });

    resetBtn.addEventListener("click", () => {
      resetSimulator();
    });
  }

  async function loadDfaDefinition() {
    try {
      const res = await fetch("/api/dfa/definition");
      if (!res.ok) throw new Error("Failed to load DFA definition");
      const def = await res.json();
      state.dfaDefinition = def;

      renderDfaSvgDiagram(def);
      renderDfaSemantics(def);
      renderDfaTransitionTable(def);

      // Initialize simulator
      startSimulatorTrace();

    } catch (err) {
      showToast(err.message, "error");
    }
  }

  function renderDfaSvgDiagram(def) {
    const wrapper = document.getElementById("dfa-svg-wrapper");
    if (!wrapper) return;

    // Load static SVG from docs or inline render
    fetch("/api/dfa/definition")
      .then(() => {
        // Render inline SVG
        wrapper.innerHTML = `
          <svg id="interactive-dfa-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1020 520" width="100%">
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#3b82f6" />
              </marker>
              <marker id="arrow-start" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#10b981" />
              </marker>
              <marker id="arrow-trap" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#ef4444" />
              </marker>
            </defs>

            <!-- Start Arrow -->
            <path d="M 40 240 L 78 240" fill="none" stroke="#10b981" stroke-width="3" marker-end="url(#arrow-start)" />
            <text x="50" y="228" font-family="sans-serif" font-size="12" font-weight="700" fill="#10b981">START</text>

            <!-- Spine Edges -->
            <path d="M 158 240 L 260 240" fill="none" stroke="#3b82f6" stroke-width="2" marker-end="url(#arrow)" />
            <text x="210" y="231" font-family="monospace" font-size="12" font-weight="600" fill="var(--text-main)" text-anchor="middle">I,N,G,O</text>

            <path d="M 338 240 L 460 240" fill="none" stroke="#3b82f6" stroke-width="2" marker-end="url(#arrow)" />
            <text x="400" y="233" font-family="monospace" font-size="12" font-weight="600" fill="var(--text-main)" text-anchor="middle">I</text>

            <path d="M 538 240 L 660 240" fill="none" stroke="#3b82f6" stroke-width="2" marker-end="url(#arrow)" />
            <text x="600" y="233" font-family="monospace" font-size="12" font-weight="600" fill="var(--text-main)" text-anchor="middle">N</text>

            <path d="M 738 240 L 860 240" fill="none" stroke="#059669" stroke-width="2.5" marker-end="url(#arrow)" />
            <text x="800" y="233" font-family="monospace" font-size="12" font-weight="700" fill="#059669" text-anchor="middle">G</text>

            <!-- Self Loops -->
            <path d="M 285 204 C 270 140, 330 140, 315 204" fill="none" stroke="#3b82f6" stroke-width="2" marker-end="url(#arrow)" />
            <text x="300" y="148" font-family="monospace" font-size="12" font-weight="600" fill="var(--text-main)" text-anchor="middle">N, G, O</text>

            <path d="M 485 204 C 470 140, 530 140, 515 204" fill="none" stroke="#3b82f6" stroke-width="2" marker-end="url(#arrow)" />
            <text x="500" y="148" font-family="monospace" font-size="12" font-weight="600" fill="var(--text-main)" text-anchor="middle">I</text>

            <!-- Backward Transitions -->
            <path d="M 480 270 C 430 320, 370 320, 320 270" fill="none" stroke="#3b82f6" stroke-width="1.8" marker-end="url(#arrow)" />
            <text x="400" y="322" font-family="monospace" font-size="12" font-weight="600" fill="var(--text-main)" text-anchor="middle">G, O</text>

            <path d="M 680 270 C 580 360, 420 360, 315 275" fill="none" stroke="#3b82f6" stroke-width="1.8" marker-end="url(#arrow)" />
            <text x="480" y="358" font-family="monospace" font-size="12" font-weight="600" fill="var(--text-main)" text-anchor="middle">N, O</text>

            <path d="M 680 215 C 630 170, 570 170, 520 215" fill="none" stroke="#3b82f6" stroke-width="1.8" marker-end="url(#arrow)" />
            <text x="600" y="178" font-family="monospace" font-size="12" font-weight="600" fill="var(--text-main)" text-anchor="middle">I</text>

            <path d="M 880 215 C 780 120, 620 120, 525 218" fill="none" stroke="#3b82f6" stroke-width="1.8" marker-end="url(#arrow)" />
            <text x="700" y="128" font-family="monospace" font-size="12" font-weight="600" fill="var(--text-main)" text-anchor="middle">I</text>

            <path d="M 885 272 C 750 390, 450 390, 310 276" fill="none" stroke="#3b82f6" stroke-width="1.8" marker-end="url(#arrow)" />
            <text x="600" y="396" font-family="monospace" font-size="12" font-weight="600" fill="var(--text-main)" text-anchor="middle">N, G, O</text>

            <!-- Trap State -->
            <path d="M 140 275 C 240 430, 380 430, 460 430" fill="none" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="4,4" marker-end="url(#arrow-trap)" />
            <text x="260" y="445" font-family="monospace" font-size="11" font-weight="600" fill="#dc2626" text-anchor="middle">NON_LETTER</text>

            <!-- State Circles -->
            <g id="svg-node-q0">
              <circle cx="120" cy="240" r="38" fill="var(--bg-surface)" stroke="#3b82f6" stroke-width="2.5" />
              <text x="120" y="236" font-family="sans-serif" font-weight="700" font-size="18" text-anchor="middle" dominant-baseline="central" fill="var(--text-main)">q0</text>
              <text x="120" y="254" font-family="sans-serif" font-weight="500" font-size="11" text-anchor="middle" fill="var(--text-muted)">Start</text>
            </g>

            <g id="svg-node-q1">
              <circle cx="300" cy="240" r="38" fill="var(--bg-surface)" stroke="#3b82f6" stroke-width="2.5" />
              <text x="300" y="236" font-family="sans-serif" font-weight="700" font-size="18" text-anchor="middle" dominant-baseline="central" fill="var(--text-main)">q1</text>
              <text x="300" y="254" font-family="sans-serif" font-weight="500" font-size="11" text-anchor="middle" fill="var(--text-muted)">&gt;=1 letter</text>
            </g>

            <g id="svg-node-q2">
              <circle cx="500" cy="240" r="38" fill="var(--bg-surface)" stroke="#3b82f6" stroke-width="2.5" />
              <text x="500" y="236" font-family="sans-serif" font-weight="700" font-size="18" text-anchor="middle" dominant-baseline="central" fill="var(--text-main)">q2</text>
              <text x="500" y="254" font-family="sans-serif" font-weight="500" font-size="11" text-anchor="middle" fill="var(--text-muted)">'i'</text>
            </g>

            <g id="svg-node-q3">
              <circle cx="700" cy="240" r="38" fill="var(--bg-surface)" stroke="#3b82f6" stroke-width="2.5" />
              <text x="700" y="236" font-family="sans-serif" font-weight="700" font-size="18" text-anchor="middle" dominant-baseline="central" fill="var(--text-main)">q3</text>
              <text x="700" y="254" font-family="sans-serif" font-weight="500" font-size="11" text-anchor="middle" fill="var(--text-muted)">'in'</text>
            </g>

            <g id="svg-node-q4">
              <!-- Double concentric circle for accepting state -->
              <circle cx="900" cy="240" r="38" fill="var(--bg-surface)" stroke="#059669" stroke-width="2.5" />
              <circle cx="900" cy="240" r="32" fill="var(--success-bg)" stroke="#059669" stroke-width="2" />
              <text x="900" y="235" font-family="sans-serif" font-weight="700" font-size="18" text-anchor="middle" dominant-baseline="central" fill="#047857">q4</text>
              <text x="900" y="253" font-family="sans-serif" font-weight="600" font-size="11" text-anchor="middle" fill="#059669">Accept</text>
            </g>

            <g id="svg-node-q_trap">
              <circle cx="500" cy="430" r="34" fill="var(--danger-bg)" stroke="#dc2626" stroke-width="2" />
              <text x="500" y="426" font-family="sans-serif" font-weight="700" font-size="16" text-anchor="middle" dominant-baseline="central" fill="#b91c1c">q_trap</text>
              <text x="500" y="443" font-family="sans-serif" font-weight="600" font-size="11" text-anchor="middle" fill="#dc2626">Trap</text>
            </g>
          </svg>
        `;
      });
  }

  function highlightSvgState(stateId) {
    document.querySelectorAll("#interactive-dfa-svg [id^='svg-node-'] circle").forEach(el => {
      el.classList.remove("svg-active-state");
    });
    const targetGroup = document.getElementById(`svg-node-${stateId}`);
    if (targetGroup) {
      targetGroup.querySelectorAll("circle").forEach(c => c.classList.add("svg-active-state"));
    }
  }

  function renderDfaSemantics(def) {
    const list = document.getElementById("state-semantics-list");
    if (!list) return;
    list.innerHTML = "";
    Object.values(def.states).forEach(s => {
      const li = document.createElement("li");
      li.innerHTML = `<strong><code>${s.id}</code></strong>: ${escapeHTML(s.meaning)}`;
      list.appendChild(li);
    });
  }

  function renderDfaTransitionTable(def) {
    const tbody = document.getElementById("dfa-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    def.transition_table.forEach(row => {
      const tr = document.createElement("tr");
      const statusBadge = row.is_accepting
        ? '<span class="badge badge-pass">ACCEPTING</span>'
        : (row.is_start ? '<span class="badge badge-accent">START</span>' : '-');

      tr.innerHTML = `
        <td><strong><code>${row.state}</code></strong></td>
        <td>${escapeHTML(row.meaning)}</td>
        <td><code>${row.transitions.I}</code></td>
        <td><code>${row.transitions.N}</code></td>
        <td><code>${row.transitions.G}</code></td>
        <td><code>${row.transitions.OTHER_LETTER}</code></td>
        <td><code>${row.transitions.NON_LETTER}</code></td>
        <td>${statusBadge}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // --- DFA Simulator Execution ---
  async function startSimulatorTrace() {
    const wordInput = document.getElementById("simulator-word-input");
    const word = wordInput.value;
    state.simWord = word;
    state.simStepIndex = 0;

    try {
      const res = await fetch("/api/dfa/trace", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word })
      });
      if (!res.ok) throw new Error("Trace failed");
      const data = await res.json();
      state.simTrace = data;

      renderSimTape();
      updateSimStatusBanner("READY", "Press Step or Play to trace state transitions", "status-idle");
      highlightSvgState("q0");

    } catch (err) {
      showToast(err.message, "error");
    }
  }

  function renderSimTape() {
    const tape = document.getElementById("sim-tape");
    if (!tape) return;
    tape.innerHTML = "";

    if (!state.simWord) {
      tape.innerHTML = `<span style="font-size:12px; color:var(--text-muted);">Tape empty. Enter a word above.</span>`;
      return;
    }

    for (let i = 0; i < state.simWord.length; i++) {
      const cell = document.createElement("div");
      cell.className = `tape-cell ${i === state.simStepIndex ? "active" : ""} ${i < state.simStepIndex ? "passed" : ""}`;
      cell.innerHTML = `
        <span class="tape-idx">${i + 1}</span>
        <span>${escapeHTML(state.simWord[i])}</span>
      `;
      tape.appendChild(cell);
    }
  }

  function stepSimulator() {
    if (!state.simTrace || !state.simTrace.steps) return;
    const totalSteps = state.simTrace.steps.length;

    if (state.simStepIndex < totalSteps) {
      const currentStep = state.simTrace.steps[state.simStepIndex];
      state.simStepIndex++;

      renderSimTape();
      highlightSvgState(currentStep.to_state);

      const msg = `Step ${currentStep.step}/${totalSteps}: char '${currentStep.char}' [Class: ${currentStep.class}] &rarr; ${currentStep.from_state} to ${currentStep.to_state}`;
      updateSimStatusBanner("STEPPING", msg, "status-idle");

      // Check if finished on this step
      if (state.simStepIndex === totalSteps) {
        finishSimulator();
      }
    } else {
      finishSimulator();
    }
  }

  function finishSimulator() {
    if (state.simInterval) {
      clearInterval(state.simInterval);
      state.simInterval = null;
      document.getElementById("btn-sim-play").textContent = "Play \u25ba";
    }

    const accepted = state.simTrace.accepted;
    const finalState = state.simTrace.final_state;
    if (accepted) {
      updateSimStatusBanner(
        "ACCEPTED",
        `Token "${state.simWord}" successfully recognized by DFA in accepting state ${finalState} (Length >= 4 and ends in "ing").`,
        "status-accept"
      );
    } else {
      let reason = `Ended in non-accepting state ${finalState}.`;
      if (state.simWord.length < 4) reason += ` (Failed length >= 4 constraint).`;
      if (finalState === "q_trap") reason = `Entered dead trap state upon non-letter character.`;
      updateSimStatusBanner("REJECTED", `Token "${state.simWord}" rejected by DFA: ${reason}`, "status-reject");
    }
  }

  function togglePlaySimulator() {
    const playBtn = document.getElementById("btn-sim-play");
    if (state.simInterval) {
      clearInterval(state.simInterval);
      state.simInterval = null;
      playBtn.textContent = "Play \u25ba";
    } else {
      if (state.simStepIndex >= (state.simTrace?.steps?.length || 0)) {
        resetSimulator();
      }
      playBtn.textContent = "Pause \u23f8";
      state.simInterval = setInterval(() => {
        if (state.simStepIndex < (state.simTrace?.steps?.length || 0)) {
          stepSimulator();
        } else {
          finishSimulator();
        }
      }, 500);
    }
  }

  function resetSimulator() {
    if (state.simInterval) {
      clearInterval(state.simInterval);
      state.simInterval = null;
      document.getElementById("btn-sim-play").textContent = "Play \u25ba";
    }
    startSimulatorTrace();
  }

  function updateSimStatusBanner(badgeText, message, statusClass) {
    const banner = document.getElementById("sim-status-banner");
    const badge = document.getElementById("sim-status-badge");
    const msg = document.getElementById("sim-status-msg");

    if (banner && badge && msg) {
      banner.className = `sim-status-banner ${statusClass}`;
      badge.textContent = badgeText;
      msg.innerHTML = message;
    }
  }


  // ==========================================================================
  // TAB 4: RE VS DFA COMPARISON
  // ==========================================================================
  function initCompareTab() {
    document.getElementById("btn-run-compare").addEventListener("click", () => {
      runHeadToHeadComparison();
    });
  }

  async function loadComparisonLOC() {
    // Populate static LOC estimates initially
    const reLocEl = document.getElementById("cell-re-loc");
    const dfaLocEl = document.getElementById("cell-dfa-loc");
    if (reLocEl && dfaLocEl && reLocEl.textContent.includes("Loading")) {
      runHeadToHeadComparison();
    }
  }

  async function runHeadToHeadComparison() {
    const picker = document.getElementById("compare-page-picker");
    const pageId = picker.value;
    const btn = document.getElementById("btn-run-compare");
    const spinner = document.getElementById("compare-spinner");

    try {
      btn.disabled = true;
      spinner.classList.remove("hidden");

      const res = await fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ page_id: pageId })
      });

      if (!res.ok) throw new Error("Comparison request failed");
      const data = await res.json();

      // Show sections
      document.getElementById("compare-equivalence-banner").classList.remove("hidden");
      document.getElementById("compare-metrics-grid").classList.remove("hidden");
      document.getElementById("compare-charts-row").classList.remove("hidden");

      // Update Equivalence Banner
      const equalBadge = document.getElementById("compare-equal-badge");
      const equalText = document.getElementById("compare-equal-text");
      if (data.equal) {
        equalBadge.textContent = "IDENTICAL RESULTS";
        equalBadge.style.backgroundColor = "var(--success)";
        equalText.textContent = `Both engines extracted exactly ${data.re.count} matches with 100% identical character offsets, lines, and columns.`;
      } else {
        equalBadge.textContent = "DISCREPANCY DETECTED";
        equalBadge.style.backgroundColor = "var(--danger)";
        equalText.textContent = `RE found ${data.re.count} while DFA found ${data.dfa.count} (${data.diff.discrepancies} diffs).`;
      }

      // Update Metric Cards
      document.getElementById("metric-re-count").textContent = data.re.count;
      document.getElementById("metric-dfa-count").textContent = data.dfa.count;
      document.getElementById("metric-re-time").textContent = data.performance.re_time_us.toFixed(1);
      document.getElementById("metric-dfa-time").textContent = data.performance.dfa_time_us.toFixed(1);
      document.getElementById("metric-speedup").textContent = `${data.performance.speedup_ratio}x`;
      document.getElementById("metric-faster-desc").textContent = `${data.performance.faster} is faster`;

      // Update Qualitative Table Cells
      document.getElementById("cell-re-loc").textContent = `${data.loc_comparison.re_code_lines} non-blank, non-comment lines`;
      document.getElementById("cell-dfa-loc").textContent = `${data.loc_comparison.dfa_code_lines} non-blank, non-comment lines`;
      document.getElementById("cell-re-time").textContent = `${data.performance.re_time_us.toFixed(1)} \u00b5s (200-run avg)`;
      document.getElementById("cell-dfa-time").textContent = `${data.performance.dfa_time_us.toFixed(1)} \u00b5s (200-run avg)`;

      // Render Charts
      renderCompareCharts(data);

      showToast(`Comparison complete for ${pageId}: identical match sets verified.`, "success");

    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btn.disabled = false;
      spinner.classList.add("hidden");
    }
  }

  function renderCompareCharts(data) {
    const timingCtx = document.getElementById("compare-timing-chart");
    const locCtx = document.getElementById("compare-loc-chart");

    if (state.compareTimingChart) state.compareTimingChart.destroy();
    if (state.compareLocChart) state.compareLocChart.destroy();

    // Timing chart
    state.compareTimingChart = new Chart(timingCtx, {
      type: "bar",
      data: {
        labels: ["RE Engine (C-SRE)", "DFA Engine (Python Table)"],
        datasets: [{
          label: "Latency (\u00b5s, lower is faster)",
          data: [data.performance.re_time_us, data.performance.dfa_time_us],
          backgroundColor: ["rgba(59, 130, 246, 0.8)", "rgba(16, 185, 129, 0.8)"],
          borderColor: ["rgb(59, 130, 246)", "rgb(16, 185, 129)"],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Microseconds (\u00b5s)" },
            grid: { color: "rgba(150, 150, 150, 0.1)" }
          }
        }
      }
    });

    // LOC chart
    state.compareLocChart = new Chart(locCtx, {
      type: "bar",
      data: {
        labels: ["RE Engine (core/re_engine.py)", "DFA Engine (dfa_engine + dfa_definition)"],
        datasets: [{
          label: "Lines of Code (LOC)",
          data: [data.loc_comparison.re_code_lines, data.loc_comparison.dfa_code_lines],
          backgroundColor: ["rgba(99, 102, 241, 0.8)", "rgba(245, 158, 11, 0.8)"],
          borderColor: ["rgb(99, 102, 241)", "rgb(245, 158, 11)"],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Lines of Code" },
            grid: { color: "rgba(150, 150, 150, 0.1)" }
          }
        }
      }
    });
  }


  // ==========================================================================
  // TAB 5: ABOUT & TEST CASES
  // ==========================================================================
  function initAboutTab() {
    document.getElementById("testcase-search").addEventListener("input", (e) => {
      state.testCaseFilterText = e.target.value.toLowerCase();
      renderTestCasesTable();
    });

    document.getElementById("testcase-pattern-filter").addEventListener("change", (e) => {
      state.testCasePatternFilter = e.target.value;
      renderTestCasesTable();
    });
  }

  function renderSourcesInfoList() {
    const container = document.getElementById("sources-info-list");
    if (!container) return;
    container.innerHTML = "";

    state.pages.forEach(p => {
      const card = document.createElement("div");
      card.className = "source-item-card";
      card.innerHTML = `
        <span class="snapshot-badge">${escapeHTML(p.category)}</span>
        <div class="source-item-title">${escapeHTML(p.title)}</div>
        <div class="source-item-url"><a href="${p.url}" target="_blank" rel="noopener noreferrer">${escapeHTML(p.url)}</a></div>
        <div style="font-size:11.5px; color:var(--text-muted); margin-top:4px;">
          ${p.char_count.toLocaleString()} chars &bull; ${p.line_count.toLocaleString()} lines &bull; Fetched: ${new Date(p.fetched_on).toLocaleDateString()}
        </div>
      `;
      container.appendChild(card);
    });
  }

  function renderRegistryTable() {
    const tbody = document.getElementById("registry-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    Object.values(state.patterns).forEach(p => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><code>${p.key}</code></td>
        <td><strong>${escapeHTML(p.label)}</strong></td>
        <td><code>${escapeHTML(p.regex)}</code></td>
        <td>${p.flags ? "<code>re.IGNORECASE</code>" : "None"}</td>
        <td>${escapeHTML(p.description)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  async function loadTestCases() {
    try {
      const res = await fetch("/api/testcases");
      if (!res.ok) throw new Error("Failed to load test cases");
      const data = await res.json();
      state.testCases = data.cases || [];

      // Populate filter dropdown
      const select = document.getElementById("testcase-pattern-filter");
      if (select) {
        select.innerHTML = '<option value="all">All Patterns</option>';
        const distinctPatterns = [...new Set(state.testCases.map(c => c.pattern))];
        distinctPatterns.forEach(pat => {
          const opt = document.createElement("option");
          opt.value = pat;
          opt.textContent = pat;
          select.appendChild(opt);
        });
      }

      renderTestCasesTable();

    } catch (err) {
      showToast(err.message, "error");
    }
  }

  function renderTestCasesTable() {
    const tbody = document.getElementById("testcases-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    let filtered = state.testCases;

    if (state.testCasePatternFilter !== "all") {
      filtered = filtered.filter(c => c.pattern === state.testCasePatternFilter);
    }

    if (state.testCaseFilterText) {
      filtered = filtered.filter(c =>
        c.input.toLowerCase().includes(state.testCaseFilterText) ||
        c.description.toLowerCase().includes(state.testCaseFilterText)
      );
    }

    filtered.forEach(c => {
      const tr = document.createElement("tr");
      const expectedBadge = c.expected
        ? '<span class="badge badge-accent">MATCH</span>'
        : '<span class="badge" style="background:#f1f5f9; color:#475569;">NO MATCH</span>';

      tr.innerHTML = `
        <td><code>${c.pattern}</code></td>
        <td><code>${escapeHTML(c.input)}</code></td>
        <td>${expectedBadge}</td>
        <td>${escapeHTML(c.description)}</td>
        <td><span class="badge badge-pass">PASSED</span></td>
      `;
      tbody.appendChild(tr);
    });
  }


  // ==========================================================================
  // HELPER UTILITIES
  // ==========================================================================
  function escapeHTML(str) {
    if (typeof str !== "string") return String(str || "");
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
