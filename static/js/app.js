// --- Application State ---
let username = "Fanatic_99";
let userTeam = "neutral";
let activeStand = "neutral";
let socket = null;
let aiSocket = null;
let currentOver = 17.2;

// --- DOM References ---
const chatMessages = document.getElementById("chat-messages");
const messageInput = document.getElementById("chat-message-input");
const scoreText = document.getElementById("score-text");
const oversText = document.getElementById("overs-text");
const strikerText = document.getElementById("striker-text");
const bowlerText = document.getElementById("bowler-text");
const recentBallsList = document.getElementById("recent-balls-list");
const threadsList = document.getElementById("threads-list");
const duggyMessages = document.getElementById("duggy-messages");
const duggyInput = document.getElementById("duggy-query-input");
const moderatorLogs = document.getElementById("moderator-logs");

// DRS references
const drsOverlay = document.getElementById("drs-overlay-container");
const drsTimerText = document.getElementById("drs-timer-text");
const drsAppealDesc = document.getElementById("drs-appeal-desc");
const drsBarOut = document.getElementById("drs-bar-out");
const drsBarNotOut = document.getElementById("drs-bar-notout");

// --- Profile Modal Setup ---
function selectProfileTeam(team) {
    document.querySelectorAll(".team-select-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelector(`.team-select-btn.${team}`).classList.add("active");
    userTeam = team;
}

function saveProfile() {
    const inputName = document.getElementById("username-input").value.strip ? 
                      document.getElementById("username-input").value.strip() : 
                      document.getElementById("username-input").value.trim();
    if (inputName) {
        username = inputName;
    }
    document.getElementById("profile-modal").style.display = "none";
    
    // Automatically match stand to favorite team or default to neutral
    activeStand = userTeam;
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.getElementById(`tab-${activeStand}`).classList.add("active");
    
    initStadiumMap();
    connectWebSocket(activeStand);
    connectAIWebSocket();
}

// --- WebSocket Management ---
function connectWebSocket(standId) {
    if (socket) {
        socket.close();
    }
    
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    socket = new WebSocket(`${protocol}//${host}/ws/chat/${standId}`);
    
    socket.onopen = () => {
        console.log(`WebSocket connected to stand: ${standId}`);
        // Clear chat container
        chatMessages.innerHTML = "";
        appendSystemMessage(`Joined the ${standId.toUpperCase()} Stand chatroom.`);
    };
    
    socket.onmessage = (event) => {
        const data = jsonParse(event.data);
        if (!data) return;
        
        switch (data.type) {
            case "init":
                // Load scorecard
                updateScorecardUI(data.scorecard);
                // Load threads
                renderThreads(data.threads);
                // Load DRS if active
                handleDRSState(data.drs);
                // Load moderator logs
                renderModeratorLogs(data.moderator_logs);
                if (data.fan_counts) {
                    updateFanCounts(data.fan_counts);
                }
                if (data.fantasy_teams) {
                    updateFantasyUI(data.fantasy_teams);
                }
                if (data.debate) {
                    updateDebateUI(data.debate);
                }
                break;
                
            case "message":
                appendChatMessage(data.message);
                break;
                
            case "scorecard":
                updateScorecardUI(data.scorecard);
                break;
                
            case "new_thread":
                appendThreadCard(data.thread, true);
                break;
                
            case "drs_trigger":
                triggerDRSView(data.drs);
                break;
                
            case "drs_tick":
                drsTimerText.innerText = `${data.time_remaining}s`;
                break;
                
            case "drs_vote_update":
                updateDRSMeter(data.votes_out, data.votes_not_out);
                break;
                
            case "drs_resolved":
                resolveDRSView(data.drs, data.thread);
                break;
                
            case "moderator_log":
                appendModeratorLog(data.log);
                break;
                
            case "fan_counts":
                updateFanCounts(data.counts);
                break;

            case "fantasy_update":
                updateFantasyUI(data.teams);
                break;

            case "debate_updated":
                updateDebateUI(data.debate);
                break;

            case "debate_resolved":
                updateDebateUI(data.debate);
                break;
        }
    };
    
    socket.onclose = () => {
        console.log("WebSocket disconnected.");
    };
}

function switchStand(standId) {
    activeStand = standId;
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.getElementById(`tab-${standId}`).classList.add("active");
    updateStadiumActiveHighlight(standId);
    connectWebSocket(standId);
}

// --- Chat Functions ---
function sendChatMessage() {
    const text = messageInput.value.trim();
    if (!text || !socket) return;
    
    socket.send(JSON.stringify({
        sender: username,
        message: text,
        team: userTeam
    }));
    
    messageInput.value = "";
}

function handleChatSubmit(event) {
    if (event.key === "Enter") {
        sendChatMessage();
    }
}

function appendChatMessage(msg) {
    const isMe = msg.sender === username;
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble team-${msg.team} ${isMe ? 'me' : ''}`;
    
    bubble.innerHTML = `
        <span class="sender">${msg.sender}</span>
        <span class="msg-text">${escapeHTML(msg.message)}</span>
        <span class="timestamp">${msg.timestamp}</span>
    `;
    
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendSystemMessage(text) {
    const container = document.createElement("div");
    container.style.textAlign = "center";
    container.style.fontSize = "11px";
    container.style.color = "var(--text-muted)";
    container.style.margin = "8px 0";
    container.innerText = text;
    chatMessages.appendChild(container);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// --- Scorecard UI Updates ---
function updateScorecardUI(scoreData) {
    scoreText.innerText = `${scoreData.runs}/${scoreData.wickets}`;
    oversText.innerText = `(${scoreData.overs} Overs)`;
    strikerText.innerText = scoreData.batsman_striker;
    bowlerText.innerText = scoreData.bowler_active;
    currentOver = parseFloat(scoreData.overs);
    
    // Excitement bars
    document.getElementById("pulse-csk").style.width = `${scoreData.excitement_csk}%`;
    document.getElementById("pulse-csk").innerText = `${scoreData.excitement_csk}%`;
    document.getElementById("pulse-mi").style.width = `${scoreData.excitement_mi}%`;
    document.getElementById("pulse-mi").innerText = `${scoreData.excitement_mi}%`;
    
    // Ball tray
    recentBallsList.innerHTML = "";
    scoreData.recent_balls.forEach(ball => {
        const ballSpan = document.createElement("span");
        ballSpan.className = "ball";
        if (ball === "W") {
            ballSpan.classList.add("runs-w");
        } else if (ball === "4") {
            ballSpan.classList.add("runs-4");
        } else if (ball === "6") {
            ballSpan.classList.add("runs-6");
        }
        ballSpan.innerText = ball;
        recentBallsList.appendChild(ballSpan);
    });
}

// --- Event Threads Rendering ---
function renderThreads(threads) {
    threadsList.innerHTML = "";
    if (threads.length === 0) {
        threadsList.innerHTML = `<p class="no-logs">No match threads created yet.</p>`;
        return;
    }
    threads.forEach(thread => appendThreadCard(thread, false));
}

function appendThreadCard(thread, isNew = false) {
    // Remove "no threads" placeholder if it exists
    const placeholder = threadsList.querySelector(".no-logs");
    if (placeholder) {
        threadsList.innerHTML = "";
    }
    
    const card = document.createElement("div");
    card.className = "thread-card";
    
    // Highlight class based on type
    if (thread.event_type === "wicket") {
        card.classList.add("highlight-wicket");
    } else if (thread.event_type === "boundary") {
        card.classList.add("highlight-boundary");
    } else if (thread.event_type.startsWith("drs")) {
        card.classList.add("highlight-drs");
    }
    
    card.innerHTML = `
        <div class="thread-meta">
            <span class="over-badge">Over ${thread.over}</span>
            <span>${thread.timestamp}</span>
        </div>
        <h4>${escapeHTML(thread.title)}</h4>
        <p>${escapeHTML(thread.description)}</p>
    `;
    
    if (isNew) {
        threadsList.insertBefore(card, threadsList.firstChild);
        card.style.animation = "glow-pulse 2s ease";
    } else {
        threadsList.appendChild(card);
    }
}

// --- DRS UI Panel Management ---
function handleDRSState(drs) {
    if (drs.is_active) {
        triggerDRSView(drs);
        updateDRSMeter(drs.votes_out, drs.votes_not_out);
    } else {
        drsOverlay.classList.add("hidden");
    }
}

function triggerDRSView(drs) {
    drsAppealDesc.innerHTML = `Over ${drs.over}: LBW appeal on <strong>${drs.batsman}</strong> bowler by <strong>${drs.bowler}</strong>. The match is paused for third umpire review. Crowd votes are locked in 15 seconds!`;
    drsTimerText.innerText = `${drs.time_remaining}s`;
    
    // Reset buttons
    document.querySelectorAll(".drs-vote-btn").forEach(btn => {
        btn.disabled = false;
        btn.style.opacity = "1";
    });
    
    updateDRSMeter(0, 0);
    drsOverlay.classList.remove("hidden");
}

function updateDRSMeter(outVotes, notOutVotes) {
    const total = outVotes + notOutVotes;
    if (total === 0) {
        drsBarOut.style.width = "50%";
        drsBarOut.innerText = "OUT (50%)";
        drsBarNotOut.style.width = "50%";
        drsBarNotOut.innerText = "NOT OUT (50%)";
        return;
    }
    
    const outPct = Math.round((outVotes / total) * 100);
    const notOutPct = 100 - outPct;
    
    drsBarOut.style.width = `${outPct}%`;
    drsBarOut.innerText = `OUT (${outPct}%)`;
    drsBarNotOut.style.width = `${notOutPct}%`;
    drsBarNotOut.innerText = `NOT OUT (${notOutPct}%)`;
}

function voteDRS(vote) {
    // Disable buttons
    document.querySelectorAll(".drs-vote-btn").forEach(btn => {
        btn.disabled = true;
        btn.style.opacity = "0.5";
    });
    
    fetch("/api/drs/vote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ vote: vote })
    })
    .then(res => res.json())
    .catch(err => console.error("Error casting DRS vote:", err));
}

function resolveDRSView(drs, thread) {
    // Flash the official verdict on the screen shortly before hiding
    const verdictColor = drs.official_verdict === "OUT" ? "var(--accent-red)" : "var(--primary-green)";
    drsAppealDesc.innerHTML = `<span style="font-size: 16px; font-weight: 700; color: ${verdictColor}">OFFICIAL VERDICT: ${drs.official_verdict}</span>`;
    
    setTimeout(() => {
        drsOverlay.classList.add("hidden");
        // Inject thread
        appendThreadCard(thread, true);
    }, 2000);
}

// --- Duggy Chatbot (System A) ---
function connectAIWebSocket() {
    if (aiSocket) {
        aiSocket.close();
    }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    // Create a unique dummy user_id for the isolated connection
    const userId = username + "_" + Math.floor(Math.random() * 1000);
    aiSocket = new WebSocket(`${protocol}//${host}/ws/chat/ai/${userId}`);
    
    aiSocket.onopen = () => {
        console.log("Duggy AI WebSocket connected.");
        document.querySelector(".duggy-input-bar input").placeholder = "Ask Duggy a question...";
    };
    
    let currentBotMessageBubble = null;
    let currentTextBuffer = "";

    aiSocket.onmessage = (event) => {
        const textChunk = event.data;
        
        // Check for completion signal
        if (textChunk === "[DONE]") {
            currentBotMessageBubble = null;
            return;
        }

        // Remove typing indicator if present
        document.querySelector(".typing-indicator")?.remove();

        // Create new bubble if it's the start of a response
        if (!currentBotMessageBubble) {
            const bubble = document.createElement("div");
            bubble.className = `duggy-msg bot`;
            bubble.innerHTML = `<div class="text content-area"></div>`;
            duggyMessages.appendChild(bubble);
            currentBotMessageBubble = bubble.querySelector(".content-area");
            currentTextBuffer = "";
        }

        currentTextBuffer += textChunk;
        currentBotMessageBubble.innerHTML = formatDuggyResponse(currentTextBuffer);
        duggyMessages.scrollTop = duggyMessages.scrollHeight;
    };
    
    aiSocket.onclose = () => {
        console.log("Duggy AI WebSocket disconnected. Attempting to reconnect in 5s...");
        setTimeout(connectAIWebSocket, 5000);
    };
}

function submitDuggyQuery() {
    const text = duggyInput.value.trim();
    if (!text) return;
    
    if (!aiSocket || aiSocket.readyState !== WebSocket.OPEN) {
        alert("Duggy is currently offline. Please wait for reconnection.");
        return;
    }
    
    appendDuggyMessage("user", text);
    duggyInput.value = "";
    
    // Add typing indicator
    const typingBubble = document.createElement("div");
    typingBubble.className = "duggy-msg bot typing-indicator";
    typingBubble.innerHTML = `<div class="text"><i class="fa-solid fa-circle-notch fa-spin"></i> Duggy is thinking...</div>`;
    duggyMessages.appendChild(typingBubble);
    duggyMessages.scrollTop = duggyMessages.scrollHeight;
    
    // Send over WebSocket
    aiSocket.send(JSON.stringify({ query: text }));
}

function quickQuery(queryText) {
    duggyInput.value = queryText;
    submitDuggyQuery();
}

function handleDuggySubmit(event) {
    if (event.key === "Enter") {
        submitDuggyQuery();
    }
}

function appendDuggyMessage(sender, text) {
    const bubble = document.createElement("div");
    bubble.className = `duggy-msg ${sender}`;
    bubble.innerHTML = `<div class="text content-area">${formatDuggyResponse(text)}</div>`;
    duggyMessages.appendChild(bubble);
    duggyMessages.scrollTop = duggyMessages.scrollHeight;
}

// Format markdown bold/bullet indicators in Duggy bot responses
function formatDuggyResponse(text) {
    let formatted = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/- (.*?)\n/g, '• $1<br>')
        .replace(/\n/g, '<br>');
    return formatted;
}

// --- Live Match Simulator Panel ---
function simulateBall(runs, eventType, description) {
    // Generate next over value
    let nextOver = parseFloat((currentOver + 0.1).toFixed(1));
    if (Math.round((nextOver % 1) * 10) >= 6) {
        nextOver = Math.round(nextOver) + 0.0;
    }
    
    // Choose typical batsman / bowler based on simulator
    const batsmen = ["MS Dhoni", "Ruturaj Gaikwad", "Ravindra Jadeja"];
    const bowlers = ["Jasprit Bumrah", "Hardik Pandya", "Gerald Coetzee"];
    
    const randomBatsman = batsmen[Math.floor(Math.random() * batsmen.length)];
    const randomBowler = bowlers[Math.floor(Math.random() * bowlers.length)];
    
    const payload = {
        over: nextOver.toFixed(1),
        runs: runs,
        event_type: eventType,
        batsman: randomBatsman,
        bowler: randomBowler,
        description: description
    };
    
    fetch("/api/match/ball", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        console.log("Simulated ball event:", payload);
    })
    .catch(err => console.error("Error simulating ball:", err));
}

// --- Moderation Logs Panel ---
function renderModeratorLogs(logs) {
    moderatorLogs.innerHTML = "";
    if (logs.length === 0) {
        moderatorLogs.innerHTML = `<p class="no-logs">No toxic comments blocked yet. Try sending bad words in chat to test the filter.</p>`;
        return;
    }
    logs.forEach(log => appendModeratorLog(log));
}

function appendModeratorLog(log) {
    // Remove placeholder
    const placeholder = moderatorLogs.querySelector(".no-logs");
    if (placeholder) {
        moderatorLogs.innerHTML = "";
    }
    
    const entry = document.createElement("div");
    entry.className = "log-entry";
    entry.innerHTML = `
        <div class="log-meta">
            <span>BLOCKED SENDER: ${escapeHTML(log.sender)}</span>
            <span>${log.timestamp}</span>
        </div>
        <div class="log-text">"${escapeHTML(log.original_message)}"</div>
        <div class="log-reason"><i class="fa-solid fa-triangle-exclamation"></i> Reason: ${escapeHTML(log.reason)}</div>
    `;
    
    moderatorLogs.insertBefore(entry, moderatorLogs.firstChild);
}

// --- Virtual Stadium Map Controls ---
function initStadiumMap() {
    const sectors = {
        csk: document.getElementById("stadium-sector-csk"),
        mi: document.getElementById("stadium-sector-mi"),
        neutral: document.getElementById("stadium-sector-neutral")
    };
    
    const tooltip = document.getElementById("stadium-tooltip");
    
    // Highlight the active sector initially
    updateStadiumActiveHighlight(activeStand);

    Object.keys(sectors).forEach(key => {
        const sector = sectors[key];
        if (!sector) return;
        
        sector.addEventListener("mouseenter", (e) => {
            const counts = window.fanCounts || { csk: 12, mi: 8, neutral: 5 };
            const count = counts[key];
            const name = key.toUpperCase() + " STAND";
            if (tooltip) {
                tooltip.innerText = `${name} (${count} active fans)`;
                tooltip.classList.add("visible");
            }
        });
        
        sector.addEventListener("mouseleave", () => {
            if (tooltip) tooltip.classList.remove("visible");
        });
    });
}

function updateStadiumActiveHighlight(standId) {
    document.querySelectorAll(".stadium-sector").forEach(el => el.classList.remove("active"));
    const activeEl = document.getElementById(`stadium-sector-${standId}`);
    if (activeEl) {
        activeEl.classList.add("active");
    }
}

function updateFanCounts(counts) {
    if (!counts) return;
    
    // Update individual stand buttons
    const cskBtn = document.getElementById("tab-csk");
    const miBtn = document.getElementById("tab-mi");
    const neutralBtn = document.getElementById("tab-neutral");
    
    if (cskBtn) cskBtn.innerHTML = `<i class="fa-solid fa-flag csk-color"></i> CSK Stand (${counts.csk})`;
    if (miBtn) miBtn.innerHTML = `<i class="fa-solid fa-flag mi-color"></i> MI Stand (${counts.mi})`;
    if (neutralBtn) neutralBtn.innerHTML = `<i class="fa-solid fa-comments"></i> Neutral Stand (${counts.neutral})`;
    
    // Save counts on window so hover handler can read them
    window.fanCounts = counts;
    
    // Update total count in header
    const total = (counts.csk || 0) + (counts.mi || 0) + (counts.neutral || 0);
    const totalText = document.getElementById("fan-total-text");
    if (totalText) {
        totalText.innerText = `${total} fans active`;
    }
}

// --- Helper Functions ---
function escapeHTML(str) {
    if (!str) return "";
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

function jsonParse(str) {
    try {
        return JSON.parse(str);
    } catch (e) {
        console.error("JSON Parse Error:", e);
        return null;
    }
}

// --- Live Fantasy League Battle Widget ---
let currentFantasyTeams = null;

function updateFantasyUI(teams) {
    if (!teams) return;
    currentFantasyTeams = teams;
    
    const userTotal = document.getElementById("user-total-pts");
    const challengerTotal = document.getElementById("challenger-total-pts");
    const userList = document.getElementById("user-players-list");
    const challengerList = document.getElementById("challenger-players-list");
    
    if (userTotal) userTotal.innerText = `${teams.user_team.total_points} pts`;
    if (challengerTotal) challengerTotal.innerText = `${teams.challenger_team.total_points} pts`;
    
    if (userList) {
        userList.innerHTML = "";
        Object.entries(teams.user_team.players).forEach(([name, details]) => {
            const isCaptain = name === teams.user_team.captain;
            const item = document.createElement("div");
            item.className = "fantasy-player-item";
            item.innerHTML = `
                <span class="player-name">
                    ${isCaptain ? '<i class="fa-solid fa-star"></i>' : ''}
                    ${escapeHTML(name)}
                </span>
                <span class="player-role">${escapeHTML(details.role)}</span>
                <span class="player-pts">${details.points}</span>
            `;
            userList.appendChild(item);
        });
    }
    
    if (challengerList) {
        challengerList.innerHTML = "";
        Object.entries(teams.challenger_team.players).forEach(([name, details]) => {
            const isCaptain = name === teams.challenger_team.captain;
            const item = document.createElement("div");
            item.className = "fantasy-player-item";
            item.innerHTML = `
                <span class="player-name">
                    ${isCaptain ? '<i class="fa-solid fa-star"></i>' : ''}
                    ${escapeHTML(name)}
                </span>
                <span class="player-role">${escapeHTML(details.role)}</span>
                <span class="player-pts">${details.points}</span>
            `;
            challengerList.appendChild(item);
        });
    }
}

function shareFantasyCard(cardType) {
    if (!socket || !currentFantasyTeams) return;
    
    const teamName = currentFantasyTeams.user_team.name;
    const captain = currentFantasyTeams.user_team.captain;
    const totalPoints = currentFantasyTeams.user_team.total_points;
    
    socket.send(JSON.stringify({
        type: "share_fantasy_card",
        card_type: cardType,
        team_name: teamName,
        captain: captain,
        total_points: totalPoints,
        sender: username,
        team: userTeam
    }));
}

// --- Collapsible Cards Controller ---
function toggleCollapsible(bodyId, iconId) {
    const body = document.getElementById(bodyId);
    const icon = document.getElementById(iconId);
    if (body) {
        body.classList.toggle("collapsed");
        if (icon) {
            if (body.classList.contains("collapsed")) {
                icon.className = "fa-solid fa-chevron-down toggle-icon";
            } else {
                icon.className = "fa-solid fa-chevron-up toggle-icon";
                if (bodyId === "replay-body") {
                    setTimeout(drawInitialPitch, 50);
                }
            }
        }
    }
}

// --- Audio Dugout Space Controls ---
let isSpeakRequested = false;
let isAudioMuted = false;

function toggleSpeakRequest() {
    const speakBtn = document.getElementById("audio-speak-btn");
    const muteBtn = document.getElementById("audio-mute-btn");
    const waves = document.getElementById("audio-waves");
    
    if (!speakBtn) return;
    
    isSpeakRequested = !isSpeakRequested;
    if (isSpeakRequested) {
        speakBtn.innerHTML = `<i class="fa-solid fa-microphone"></i> Speaking`;
        speakBtn.classList.add("active");
        if (muteBtn) muteBtn.classList.remove("hidden");
        if (waves) waves.classList.add("speaking");
        appendSystemMessage("You are now a speaker in the Audio Dugout.");
    } else {
        speakBtn.innerHTML = `<i class="fa-solid fa-hand"></i> Request to Speak`;
        speakBtn.classList.remove("active");
        if (muteBtn) muteBtn.classList.add("hidden");
        if (waves) waves.classList.remove("speaking");
        isAudioMuted = false;
        if (muteBtn) {
            muteBtn.classList.remove("active");
            muteBtn.innerHTML = `<i class="fa-solid fa-microphone-slash"></i> Mute`;
        }
        appendSystemMessage("You returned to the listener section.");
    }
}

function toggleMuteAudio() {
    const muteBtn = document.getElementById("audio-mute-btn");
    const waves = document.getElementById("audio-waves");
    if (!muteBtn) return;
    
    isAudioMuted = !isAudioMuted;
    if (isAudioMuted) {
        muteBtn.innerHTML = `<i class="fa-solid fa-microphone"></i> Unmute`;
        muteBtn.classList.add("active");
        if (waves) waves.classList.remove("speaking");
    } else {
        muteBtn.innerHTML = `<i class="fa-solid fa-microphone-slash"></i> Mute`;
        muteBtn.classList.remove("active");
        if (waves) waves.classList.add("speaking");
    }
}

function toggleAudioDugoutPanel(visible) {
    const panel = document.getElementById("audio-dugout-panel");
    if (panel) {
        if (visible) {
            panel.classList.remove("hidden");
        } else {
            panel.classList.add("hidden");
            // Reset state
            if (isSpeakRequested) {
                toggleSpeakRequest();
            }
        }
    }
}

// Show audio space panel on load & draw initial pitch
window.addEventListener("DOMContentLoaded", () => {
    setTimeout(() => {
        toggleAudioDugoutPanel(true);
    }, 1500);
    
    // Draw the 3D replay pitch immediately so the canvas isn't blank
    setTimeout(drawInitialPitch, 100);
    
    // --- Canvas Drag-to-Rotate Interaction ---
    const replayCanvas = document.getElementById("replay-canvas");
    if (replayCanvas) {
        let isDragging = false;
        let dragStartX = 0;
        
        replayCanvas.style.cursor = "grab";
        
        replayCanvas.addEventListener("mousedown", (e) => {
            isDragging = true;
            dragStartX = e.clientX;
            replayCanvas.style.cursor = "grabbing";
        });
        
        replayCanvas.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            const deltaX = e.clientX - dragStartX;
            // If dragged more than 60px horizontally, switch angle
            if (Math.abs(deltaX) > 60) {
                const angleSelect = document.getElementById("replay-angle");
                if (deltaX > 0 && replayAngle === "side") {
                    replayAngle = "behind";
                    if (angleSelect) angleSelect.value = "behind";
                } else if (deltaX < 0 && replayAngle === "behind") {
                    replayAngle = "side";
                    if (angleSelect) angleSelect.value = "side";
                }
                drawInitialPitch();
                dragStartX = e.clientX;
            }
        });
        
        replayCanvas.addEventListener("mouseup", () => {
            isDragging = false;
            replayCanvas.style.cursor = "grab";
        });
        
        replayCanvas.addEventListener("mouseleave", () => {
            isDragging = false;
            replayCanvas.style.cursor = "grab";
        });
        
        // Touch support for mobile
        replayCanvas.addEventListener("touchstart", (e) => {
            isDragging = true;
            dragStartX = e.touches[0].clientX;
        }, { passive: true });
        
        replayCanvas.addEventListener("touchmove", (e) => {
            if (!isDragging) return;
            const deltaX = e.touches[0].clientX - dragStartX;
            if (Math.abs(deltaX) > 60) {
                const angleSelect = document.getElementById("replay-angle");
                if (deltaX > 0 && replayAngle === "side") {
                    replayAngle = "behind";
                    if (angleSelect) angleSelect.value = "behind";
                } else if (deltaX < 0 && replayAngle === "behind") {
                    replayAngle = "side";
                    if (angleSelect) angleSelect.value = "side";
                }
                drawInitialPitch();
                dragStartX = e.touches[0].clientX;
            }
        }, { passive: true });
        
        replayCanvas.addEventListener("touchend", () => {
            isDragging = false;
        });
    }
});

// --- AI Debate Arena ---
function submitDebate(team) {
    const input = document.getElementById(`debate-input-${team}`);
    if (!input || !input.value.trim() || !socket) return;
    
    socket.send(JSON.stringify({
        type: "submit_debate_argument",
        team: team,
        argument: input.value.trim()
    }));
    
    input.value = "";
    // Show spinner in debate status box
    const statusBox = document.getElementById("debate-status-box");
    if (statusBox) {
        statusBox.innerHTML = `
            <div class="debate-loading">
                <i class="fa-solid fa-circle-notch fa-spin text-yellow"></i>
                Argument submitted! Waiting for the other side to argue...
            </div>
        `;
    }
}

function resetDebate() {
    if (!socket) return;
    socket.send(JSON.stringify({
        type: "reset_debate"
    }));
}

function updateDebateUI(debate) {
    const statusBox = document.getElementById("debate-status-box");
    if (!statusBox) return;
    
    if (debate.status === "waiting") {
        if (debate.csk_statement || debate.mi_statement) {
            const side = debate.csk_statement ? "CSK" : "MI";
            statusBox.innerHTML = `
                <div class="debate-loading">
                    <i class="fa-solid fa-circle-notch fa-spin text-yellow"></i>
                    ${side} argument is locked in! Awaiting challenger response...
                </div>
            `;
        } else {
            statusBox.innerHTML = `
                <div class="debate-placeholder-text">Waiting for both statements to begin the duel...</div>
            `;
        }
    } else if (debate.status === "judging") {
        statusBox.innerHTML = `
            <div class="debate-loading">
                <i class="fa-solid fa-scale-balanced fa-beat text-yellow"></i>
                Both arguments received! AI Referee is verifying statistics and logic...
            </div>
        `;
    } else if (debate.status === "finished" && debate.result) {
        const res = debate.result;
        statusBox.innerHTML = `
            <div class="debate-verdict">
                <div class="debate-verdict-header">
                    <span>🏆 AI Referee Verdict: <strong class="text-green">${res.winner} wins the duel!</strong></span>
                    <div class="debate-scores">
                        <span class="debate-score-badge csk">CSK: ${res.csk_score}/10</span>
                        <span class="debate-score-badge mi">MI: ${res.mi_score}/10</span>
                    </div>
                </div>
                <p class="debate-verdict-recap">${escapeHTML(res.recap)}</p>
                <button class="debate-reset-btn" onclick="resetDebate()"><i class="fa-solid fa-arrow-rotate-left"></i> Reset Arena</button>
            </div>
        `;
    }
}

// --- 3D Ball-Tracker Replay Engine ---
let replaySpeed = 1;
let replayAngle = "side";
let animationId = null;

function changeReplaySpeed() {
    const select = document.getElementById("replay-speed");
    if (select) replaySpeed = parseFloat(select.value);
}

function changeReplayAngle() {
    const select = document.getElementById("replay-angle");
    if (select) {
        replayAngle = select.value;
        drawInitialPitch();
    }
}

function drawInitialPitch() {
    const canvas = document.getElementById("replay-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw Grass background
    ctx.fillStyle = "#0c1511";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    if (replayAngle === "side") {
        // Draw Side Pitch Beige Strip
        ctx.fillStyle = "#a88e74";
        ctx.fillRect(20, 140, canvas.width - 40, 8);
        
        // Creases
        ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(80, 140);
        ctx.lineTo(80, 148);
        ctx.moveTo(310, 140);
        ctx.lineTo(310, 148);
        ctx.stroke();
        
        // Draw Stumps
        ctx.fillStyle = "#e2e8f0";
        ctx.fillRect(310, 95, 2, 45); // Left
        ctx.fillRect(313, 95, 2, 45); // Center
        ctx.fillRect(316, 95, 2, 45); // Right
        ctx.fillStyle = "#ef4444";
        ctx.fillRect(309, 93, 10, 2); // Bail
    } else {
        // Behind Wicket perspective trapezoid
        ctx.fillStyle = "#a88e74";
        ctx.beginPath();
        ctx.moveTo(150, 70);
        ctx.lineTo(226, 70);
        ctx.lineTo(330, 160);
        ctx.lineTo(46, 160);
        ctx.closePath();
        ctx.fill();
        
        // Draw Stumps at far end
        ctx.fillStyle = "#e2e8f0";
        ctx.fillRect(185, 45, 1.5, 25);
        ctx.fillRect(188, 45, 1.5, 25);
        ctx.fillRect(191, 45, 1.5, 25);
        ctx.fillStyle = "#ef4444";
        ctx.fillRect(184, 44, 9, 1.5);
    }
}

function startBallReplay() {
    if (animationId) {
        cancelAnimationFrame(animationId);
    }
    
    const canvas = document.getElementById("replay-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    
    let frame = 0;
    const totalFrames = 100 * (1 / replaySpeed);
    
    function drawFrame() {
        drawInitialPitch();
        frame++;
        
        let ballX = 0;
        let ballY = 0;
        let ballRadius = 5.5;
        const progress = frame / totalFrames;
        
        if (replayAngle === "side") {
            // Parabolic arc release at (60, 90), bounce at (220, 140), finish at (312, 108)
            ballX = 60 + progress * 252;
            if (progress < 0.65) {
                // First arc to bounce
                const p = progress / 0.65;
                ballY = 90 + 50 * p * p - 20 * Math.sin(p * Math.PI);
            } else {
                // Rise after bounce
                const p = (progress - 0.65) / 0.35;
                ballY = 140 - 32 * Math.sin(p * Math.PI / 2);
            }
        } else {
            // Behind wickets: release at bottom (200, 160), bounce at (188, 110), finish at stumps (188, 50)
            // Perspective shrinking radius
            ballRadius = 9 - progress * 5;
            ballX = 188 + (1 - progress) * 12;
            
            if (progress < 0.65) {
                const p = progress / 0.65;
                ballY = 160 - 50 * p + 18 * Math.sin(p * Math.PI);
            } else {
                const p = (progress - 0.65) / 0.35;
                ballY = 110 - 60 * p + 8 * Math.sin(p * Math.PI);
            }
        }
        
        // Draw Ball
        ctx.beginPath();
        ctx.arc(ballX, ballY, ballRadius, 0, 2 * Math.PI);
        ctx.fillStyle = "#f87171";
        ctx.shadowColor = "rgba(239, 68, 68, 0.6)";
        ctx.shadowBlur = 8;
        ctx.fill();
        ctx.shadowBlur = 0; // Reset shadow
        
        // Bail fly off if progress is close to stumps impact
        if (replayAngle === "side" && progress > 0.95) {
            ctx.fillStyle = "#ef4444";
            // Draw flew off bail
            ctx.fillRect(318, 75 - (progress - 0.95)*80, 8, 2);
        }
        
        if (frame < totalFrames) {
            animationId = requestAnimationFrame(drawFrame);
        }
    }
    
    drawFrame();
}
