// 전역 변수로 API_BASE 선언 (이미 있으면 유지)
if (typeof API_BASE === 'undefined') {
    var isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    window.API_BASE = isLocal ? "http://127.0.0.1:8000" : "";
}

console.log("LOG_VER_CHECK_0509_01");

window.renderTacticalDisplay = async function(fileName) {
    try {
        const response = await fetch(`${window.API_BASE}/logs/${fileName}`);
        const logDataText = await response.text();
        if (logDataText.includes("waiting") || !logDataText.trim()) return; 
        renderAll(logDataText); 
    } catch (error) { console.error("D3 통신 에러:", error); }
};

window.loadHistoryFile = async function(fileName) {
    try {
        const response = await fetch(`${window.API_BASE}/logs/${fileName}`);
        const logDataText = await response.text();
        gridInit = false; window.dash1State = null; window.dash3State = null; window.dash4State = null;
        renderAll(logDataText);
        
        document.querySelectorAll('.log-btn').forEach(btn => btn.classList.remove('active'));
        const activeBtn = document.getElementById(`btn-${fileName}`);
        if(activeBtn) activeBtn.classList.add('active');

        const lines = logDataText.trim().split('\n').filter(l => l);
        const history = lines.map(l => JSON.parse(l));
        const latest = history[history.length - 1];
        if (typeof window.syncControlPanel === 'function') {
            window.syncControlPanel(latest, fileName);
        }
    } catch (error) { console.error("VOD 로드 에러:", error); }
};

window.refreshLogList = async function() {
    try {
        const res = await fetch(`${window.API_BASE}/api/logs`);
        const data = await res.json();
        const container = document.getElementById('file-list');
        if(!container) return;
        container.innerHTML = "";
        
        let mySessions = JSON.parse(localStorage.getItem("my_mm_sessions") || "{}");
        
        data.files.forEach(file => {
            if (!mySessions[file]) return; 
            
            const btn = document.createElement('button');
            btn.className = `log-btn`;
            btn.id = `btn-${file}`;
            let displayTime = file.replace('sim_log_', '').split('_');
            btn.innerText = displayTime.length >= 2 ? `${displayTime[0]}_${displayTime[1]}` : file;
            btn.onclick = () => window.loadHistoryFile(file);
            container.appendChild(btn);
        });
    } catch (e) { console.error("파일 목록 로드 실패", e); }
};

const safeJoin = (v) => Array.isArray(v) ? v.join("") : (v || "-");

// Entropy와 Minimax 포맷 완벽 호환 파서 (평탄화 로직 제거 버전)
function parseSplit(item) {
    // 항목이 없거나 배열이 아니면 즉시 unknown 반환
    if (!item || !Array.isArray(item)) return {type: 'unknown', s:'-', b:'-', c:'-'};
    
    // 1. 피드백 기반 포맷: [[S, B], count] -> Python의 counts.items() 결과
    // 예: [[1, 1], 25]
    if (Array.isArray(item[0]) && item.length >= 2) {
        return { 
            type: 'feedback', 
            s: item[0][0], 
            b: item[0][1], 
            c: item[1] 
        };
    }

    // 2. 레이블 기반 포맷 (기존 Minimax 호환용)
    if (typeof item[0] === 'string') {
        return { type: 'label', label: item[0], c: item[1] };
    }
    
    return { type: 'unknown', s:'-', b:'-', c:'-'};
}

let gridInit = false, prevHistoryLength = 0;

function renderAll(text) {
    const lines = text.trim().split('\n').filter(l => l);
    if (!lines.length) return;
    const history = lines.map(l => JSON.parse(l));
    const latest = history[history.length - 1];

    let lastHeatmap = null;
    let lastEval = null;
    for (let i = history.length - 1; i >= 0; i--) {
        if (!lastHeatmap && history[i].dashboard_1_heatmap) lastHeatmap = history[i].dashboard_1_heatmap;
        if (!lastEval && history[i].dashboard_3_evaluation) lastEval = history[i].dashboard_3_evaluation;
    }
    if (lastHeatmap) latest.dashboard_1_heatmap = lastHeatmap;
    if (lastEval) latest.dashboard_3_evaluation = lastEval;

    const remains = Number(latest.dashboard_2_trend?.remaining_count || 1);
    const currentTurn = Number(latest.turn || 1);
    const statusVal = latest.status || "processing";

    let displayStatus = statusVal;
    if (remains <= 1 && statusVal !== "lose") displayStatus = "win";
    else if (currentTurn >= 9 && statusVal !== "win") displayStatus = "lose";
    if (statusVal === "lose") displayStatus = "lose"; 

    const elSolver = document.getElementById('m-solver'); if (elSolver) elSolver.innerText = latest.solver_name || "Unknown";
    const elTurn = document.getElementById('m-turn'); if (elTurn) elTurn.innerText = currentTurn;
    const elRemains = document.getElementById('m-remains'); if (elRemains) elRemains.innerText = remains;
    const elGuess = document.getElementById('m-guess'); if (elGuess) elGuess.innerText = latest.best_guess ? `[${safeJoin(latest.best_guess)}]` : "-";
    
    const stCard = document.getElementById('m-status');
    if (stCard) {
        if (displayStatus === "win") { stCard.innerText = "🎯 TARGET HIT"; stCard.style.color = "#F59E0B"; }
        else if (displayStatus === "lose") { stCard.innerText = "💀 GAME OVER"; stCard.style.color = "#F43F5E"; }
        else { stCard.innerText = "PROCESSING ⏳"; stCard.style.color = "#38BDF8"; }
    }

    if (history.length < prevHistoryLength || currentTurn === 1) { 
        gridInit = false; window.dash1State = null; window.dash3State = null; window.dash4State = null;
    }
    prevHistoryLength = history.length;

    try { renderDash1(latest, displayStatus); } catch(e) {}
    try { renderDash2(history); } catch(e) {}
    try { renderDash3(latest, displayStatus); } catch(e) {}
    try { renderDash4(latest, displayStatus); } catch(e) {}
}

function renderDash1(data, status) {
    const probs = data.dashboard_1_heatmap?.probabilities;
    if (!probs) return;
    
    const digitsCount = probs.length; // 3, 4, 5 동적 할당
    // 5자리 이상을 대비한 여유 색상 추가
    const colors = ["#F43F5E", "#38BDF8", "#10B981", "#F59E0B", "#A855F7", "#EAB308"];
    
    const container = document.getElementById('dash1');
    if (!container) return;

    // 자릿수 변경 감지 시 DOM 새로 그리기
    if (container.children.length !== digitsCount) {
        container.innerHTML = "";
        for (let i = 0; i < digitsCount; i++) {
            const div = document.createElement('div');
            div.className = 'chamber';
            div.id = `ch${i}`;
            container.appendChild(div);
        }
        window.dash1State = null; // 상태 초기화
    }

    if (!window.dash1State) {
        window.dash1State = { turn: -1, chambers: Array.from({length: digitsCount}, () => ({})) };
    }
    
    const isNewTurn = window.dash1State.turn !== data.turn;
    window.dash1State.turn = data.turn;
    
    probs.forEach((posProbs, i) => {
        let ch = window.dash1State.chambers[i];
        const c = document.getElementById(`ch${i}`); 
        if (!c) return; 
        const w = c.clientWidth, h = c.clientHeight;
        if (w === 0 || h === 0) return;
        
        // 챔버 초기 세팅
        if (!ch.initialized) {
            c.innerHTML = `<div style="position:absolute; top:4px; left:6px; font-size:0.55rem; color:#475569; z-index:5;">POS ${i+1}</div>`;
            const svg = d3.select(c).append("svg").attr("width", "100%").attr("height", "100%");
            const defs = svg.append("defs");
            ch.clipNewId = `clip-new-ch${i}`; ch.clipOldId = `clip-old-ch${i}`;
            defs.append("clipPath").attr("id", ch.clipNewId).append("rect").attr("class", "rect-new").attr("x", 0).attr("y", 0).attr("width", w).attr("height", 0);
            defs.append("clipPath").attr("id", ch.clipOldId).append("rect").attr("class", "rect-old").attr("x", 0).attr("y", 0).attr("width", w).attr("height", h);
            ch.x = d3.scaleLinear().domain([0, 1]).range([i===0?25:10, w-10]);
            ch.y = d3.scalePoint().domain(d3.range(10)).range([15, h-15]);
            if (i === 0) svg.append("g").attr("transform", "translate(22,0)").call(d3.axisLeft(ch.y).tickSize(2));
            const gOld = svg.append("g").attr("clip-path", `url(#${ch.clipOldId})`);
            
            // 색상을 순환해서 사용 (colors[i % colors.length])
            const chamberColor = colors[i % colors.length];
            ch.pathOld = gOld.append("path").attr("fill", "none").attr("stroke-width", 2).attr("filter", "drop-shadow(0 0 3px currentColor)").attr("stroke", chamberColor);
            ch.laserOld = gOld.append("line").attr("stroke-width", 1.5).attr("stroke-dasharray", "3,3").attr("filter", "drop-shadow(0 0 4px #FFF)").attr("stroke", "#FFF").style("display", "none");
            const gNew = svg.append("g").attr("clip-path", `url(#${ch.clipNewId})`);
            ch.pathNew = gNew.append("path").attr("fill", "none").attr("stroke-width", 2).attr("filter", "drop-shadow(0 0 3px currentColor)").attr("stroke", chamberColor);
            ch.laserNew = gNew.append("line").attr("stroke-width", 1.5).attr("stroke-dasharray", "3,3").attr("filter", "drop-shadow(0 0 4px #FFF)").attr("stroke", "#FFF").style("display", "none");
            ch.scanner = d3.select(c).append("div").style("position", "absolute").style("width", "100%").style("height", "2px").style("background", "rgba(56, 189, 248, 0.8)").style("box-shadow", "0 0 15px #38BDF8, 0 0 5px #FFF").style("pointer-events", "none").style("top", "0px").style("opacity", 0);
            ch.svg = svg; ch.w = w; ch.h = h; ch.initialized = true;
        }
        
        // 애니메이션 및 렌더링
        if (isNewTurn) {
            if (!('currProbs' in ch)) { ch.currProbs = posProbs; ch.currGuess = data.best_guess ? data.best_guess[i] : null; }
            ch.prevProbs = ch.currProbs; ch.prevGuess = ch.currGuess; ch.currProbs = posProbs; ch.currGuess = data.best_guess ? data.best_guess[i] : null;
            const lineGen = d3.line().curve(d3.curveMonotoneY).x(d => ch.x(d.prob)).y(d => ch.y(d.digit));
            ch.pathOld.datum(d3.range(10).map(d=>({digit:d, prob:ch.prevProbs[d]}))).attr("d", lineGen).style("opacity", 1);
            ch.pathNew.datum(d3.range(10).map(d=>({digit:d, prob:ch.currProbs[d]}))).attr("d", lineGen);
            if (ch.prevGuess !== null) { ch.laserOld.attr("x1", 0).attr("x2", ch.w).attr("y1", ch.y(ch.prevGuess)).attr("y2", ch.y(ch.prevGuess)).style("display", "block").style("opacity", 1); } 
            else ch.laserOld.style("display", "none");
            if (ch.currGuess !== null) { ch.laserNew.attr("x1", 0).attr("x2", ch.w).attr("y1", ch.y(ch.currGuess)).attr("y2", ch.y(ch.currGuess)).style("display", "block"); } 
            else ch.laserNew.style("display", "none");
            ch.svg.select(".rect-new").interrupt().attr("y", 0).attr("height", 0);
            ch.svg.select(".rect-old").interrupt().attr("y", 0).attr("height", ch.h);
            ch.scanner.interrupt().style("top", "0px").style("opacity", 1).style("display", "block");
            const scanTime = 800, delay = i * 150; 
            ch.svg.select(".rect-new").transition().delay(delay).duration(scanTime).ease(d3.easeLinear).attr("height", ch.h);
            ch.svg.select(".rect-old").transition().delay(delay).duration(scanTime).ease(d3.easeLinear).attr("y", ch.h).attr("height", 0);
            ch.scanner.transition().delay(delay).duration(scanTime).ease(d3.easeLinear).style("top", `${ch.h}px`).transition().duration(200).style("opacity", 0).on("end", () => { ch.scanner.style("display", "none"); });
            ch.pathOld.transition().delay(delay).duration(scanTime * 1.5).ease(d3.easeCubicOut).style("opacity", 0.25);
            if (ch.prevGuess !== null) ch.laserOld.transition().delay(delay).duration(scanTime * 1.5).ease(d3.easeCubicOut).style("opacity", 0.25);
        } else if (status === 'win' || status === 'lose') {
             ch.svg.select(".rect-new").interrupt().attr("y", 0).attr("height", ch.h);
             ch.svg.select(".rect-old").interrupt().attr("y", ch.h).attr("height", 0);
             ch.scanner.interrupt().style("opacity", 0).style("display", "none");
        }
    });
}

function renderDash2(history) {
    const container = document.getElementById('dash2');
    if (!container) return;
    const w = container.clientWidth, h = container.clientHeight;
    if(w === 0 || h === 0) return;
    
    const DIVIDER = 1.5; 
    const trueMaxRemains = Number(history[0].dashboard_2_trend?.remaining_count || 1);
    const trueCurrentRemains = Number(history[history.length - 1].dashboard_2_trend?.remaining_count || 1);
    const TARGET_PIXELS = Math.floor(trueMaxRemains / DIVIDER); 
    const ratio = w / h;
    const GRID_ROWS = Math.max(1, Math.ceil(Math.sqrt(TARGET_PIXELS / ratio)));
    const GRID_COLS = Math.max(1, Math.ceil(TARGET_PIXELS / GRID_ROWS));
    const DRAW_PIXELS = GRID_ROWS * GRID_COLS; 
    const rectW = w / GRID_COLS, rectH = h / GRID_ROWS;
    
    if (!gridInit) {
        d3.select("#dash2").selectAll("*").remove(); 
        const svg = d3.select("#dash2").append("svg").attr("width", "100%").attr("height", "100%").attr("viewBox", `0 0 ${w} ${h}`);
        const gridGroup = svg.append("g").attr("class", "pixel-grid");
        const rectData = Array.from({length: DRAW_PIXELS}, (_, i) => i);
        gridGroup.selectAll(".shatter-rect").data(rectData).enter().append("rect")
            .attr("class", "shatter-rect")
            .attr("x", d => (d % GRID_COLS) * rectW).attr("y", d => Math.floor(d / GRID_COLS) * rectH)
            .attr("width", Math.max(0.5, rectW)).attr("height", Math.max(0.5, rectH))
            .attr("fill", "rgba(56, 189, 248, 0.4)").attr("stroke", "#030509").attr("stroke-width", 0.5).attr("data-active", "true");
        svg.append("g").attr("class", "line-layer");
        gridInit = true; 
    }
    
    d3.selectAll(".shatter-rect[data-active='false']").interrupt().style("opacity", 0).style("display", "none");
    const activeNodes = d3.selectAll(".shatter-rect[data-active='true']").nodes();
    const visualSurviveRatio = trueCurrentRemains / trueMaxRemains;
    const visualTargetVisible = Math.floor(visualSurviveRatio * DRAW_PIXELS);
    let toShatter = activeNodes.length - visualTargetVisible;
    
    if (toShatter > 0) {
        d3.shuffle(activeNodes);
        for (let i = 0; i < toShatter; i++) {
            const node = d3.select(activeNodes[i]).attr("data-active", "false");
            const startX = +node.attr("x"), startY = +node.attr("y");
            const spreadX = (Math.random() - 0.5) * 400, targetX = Math.max(0, Math.min(w - rectW, startX + spreadX)); 
            const jumpY = startY - (50 + Math.random() * 100), fallY = h - rectH + 3; 
            const totalTime = 1200 + Math.random() * 1000, jumpTime = totalTime * 0.3, fallTime = totalTime * 0.7; 
            node.attr("fill", "#FFF");
            node.transition("moveX").duration(totalTime).ease(d3.easeQuadOut).attr("x", targetX);
            node.transition("shrink").duration(jumpTime).attr("width", Math.max(1, rectW * 0.5)).attr("height", Math.max(1, rectH * 0.5));
            node.transition("moveY").duration(jumpTime).ease(d3.easeCubicOut).attr("y", jumpY).transition().duration(fallTime).ease(d3.easeBounceOut).attr("y", fallY).transition().duration(400).style("opacity", 0).remove();
        }
    }
    
    const svg = d3.select("#dash2 svg");
    const lineLayer = svg.select(".line-layer");
    lineLayer.selectAll("*").remove();
    
    // 턴 중복 제거: 동일한 턴에 processing과 win 로그가 겹칠 때 수직선이 그려지는 현상 방지
    const chartData = Object.values(history.reduce((acc, curr) => {
        if(Number(curr.turn) >= 1) acc[curr.turn] = curr; // 나중에 들어온 최종 결과로 덮어씌움
        return acc;
    }, {}));

    const maxTurn = Math.max(d3.max(chartData, d=>Number(d.turn)) || 2, 2);
    const x = d3.scaleLinear().domain([1, maxTurn]).range([15, w-15]);
    const y = d3.scaleLinear().domain([0, trueMaxRemains]).range([h-30, 15]);
    const lineGen = d3.line().x(d => x(Number(d.turn))).y(d => y(Number(d.dashboard_2_trend?.remaining_count || 0))).curve(d3.curveLinear);
    
    lineLayer.append("path").datum(chartData).attr("fill", "none").attr("stroke", "#FFF").attr("stroke-width", 2.5).attr("filter", "drop-shadow(0 0 5px #FFF)").attr("d", lineGen);
    lineLayer.selectAll("circle").data(chartData).enter().append("circle").attr("cx", d=>x(Number(d.turn))).attr("cy", d=>y(Number(d.dashboard_2_trend?.remaining_count || 0))).attr("r", 4).attr("fill", "#38BDF8");
}

function renderDash3(data, status) {
    if (!window.dash3State) window.dash3State = { turn: -1, status: '' };
    const container = document.getElementById("dash3");
    if (!container) return;
    
    window.dash3State.turn = data.turn; 
    window.dash3State.status = status;
    
    let topPicks = data.dashboard_3_evaluation?.top_guesses || [];
    if (topPicks.length === 0 && data.best_guess) topPicks = [{ guess: data.best_guess, score: 100 }];
    
    // 승리 시 연출
    if(status === 'win' || Number(data.dashboard_2_trend?.remaining_count) <= 1) {
        if (data.best_guess) {
            container.innerHTML = `<div style="display:flex; align-items:center; gap:10px; font-size:0.75rem; margin-bottom:2px;">
                <div class="matrix-text" style="color:#10B981; font-weight:bold; width:55px; text-align:right;" data-val="[${safeJoin(data.best_guess)}]">[####]</div>
                <div style="flex:1; height:8px; background:#0A0F1C; border:1px solid #1E293B;"><div style="width: 100%; height:100%; background: linear-gradient(90deg, #059669, #10B981); box-shadow: 0 0 10px #10B981;"></div></div>
                <div style="color:#10B981; width:45px; font-size:0.7rem; text-align:right;">FINAL</div>
            </div>`;
            runMatrixEffect(); return;
        }
    }

    // 최적화: 브라우저 렉 방지를 위해 최대 100개까지만 렌더링
    const MAX_RENDER = 100;
    const renderPicks = topPicks.slice(0, MAX_RENDER);
    const maxS = d3.max(renderPicks, d => d.score) || 1;
    
    // 상단에 총 남은 후보 수 표시
    let htmlStr = `<div style="font-size:0.65rem; color:#38BDF8; margin-bottom:8px; text-align:right; border-bottom:1px solid #1E293B; padding-bottom:4px;">[ TOTAL CANDIDATES : ${topPicks.length} ]</div>`;
    
    renderPicks.forEach(p => {
        htmlStr += `<div style="display:flex; align-items:center; gap:10px; font-size:0.75rem; margin-bottom:4px;">
            <div class="matrix-text" style="color:#38BDF8; font-weight:bold; width:55px; text-align:right;" data-val="[${safeJoin(p.guess)}]">[####]</div>
            <div style="flex:1; height:8px; background:#0A0F1C; border:1px solid #1E293B;"><div style="height:100%; width: ${(p.score/maxS)*100}%; background: linear-gradient(90deg, #0284C7, #38BDF8); transition: width 0.4s ease;"></div></div>
            <div style="color:#94A3B8; width:45px; font-size:0.7rem; text-align:right;">${p.score.toFixed(2)}</div>
        </div>`;
    });
    
    // 100개가 넘어갈 경우 하단에 생략된 개수 표시
    if (topPicks.length > MAX_RENDER) {
        htmlStr += `<div style="text-align:center; font-size:0.65rem; color:#64748B; margin-top:8px; margin-bottom:10px;">... AND ${topPicks.length - MAX_RENDER} MORE ...</div>`;
    }

    container.innerHTML = htmlStr;
    runMatrixEffect();
}

function runMatrixEffect() {
    const elements = document.querySelectorAll('.matrix-text');
    elements.forEach(el => {
        const finalVal = el.getAttribute('data-val');
        let cycles = 0;
        const interval = setInterval(() => {
            el.innerText = '[' + Array.from({length:4}, () => Math.floor(Math.random()*10)).join('') + ']';
            cycles++;
            if(cycles > 8) { clearInterval(interval); el.innerText = finalVal; }
        }, 40);
    });
}

function renderDash4(data, status) {
    const container = document.getElementById("dash4"); 
    if (!container) return;
    const evalData = data.dashboard_3_evaluation || {};
    const isEnded = (status === 'win' || status === 'lose');
    const vsHTML = `<div class="vs-text ${isEnded ? 'static-vs' : 'pulse-vs'}">VS</div>`;
    
    // 현재 사용 중인 메트릭 확인 (Entropy vs Minimax 구분용)
    const metricName = evalData.metric_name || "";
    const isMinimax = metricName.toLowerCase().includes("minimax");

    if(evalData.expected_splits && evalData.expected_splits.length > 0) {
        // [핵심] 첫 번째 요소를 명시적으로 전달
        const sp = parseSplit(evalData.expected_splits[0]);
        const wcInfo = evalData.worst_split_comparison || {};
        const wcGuess = wcInfo.guess || ['-','-','-','-'];
        
        // [핵심] wcInfo.splits 배열의 첫 번째 요소를 전달하도록 수정
        const wc = parseSplit(wcInfo.splits ? wcInfo.splits[0] : null);
        
        // 솔버 유형에 따른 동적 레이블 설정
        const labelBest = isMinimax ? "최악 피드백시" : "최악 피드백시"; // 엔트로피/미니맥스 둘 다 '최악' 기준은 동일함
        const labelNode = isMinimax ? "최대 잔여 노드" : "생존 노드";

        let bestDesc = `<div>${labelBest}: ${sp.s}S ${sp.b}B</div><div>➔ ${labelNode}: <span class="highlight">${sp.c}</span></div>`;
        let worstDesc = `<div>동일 피드백: ${wc.s}S ${wc.b}B</div><div>➔ ${labelNode}: <span class="highlight">${wc.c}</span></div>`;

        container.innerHTML = `
            <div class="split-box best-box slide-in-left">
                <span style="color:#10B981">TARGET ADOPTED</span>
                <div class="highlight">[${safeJoin(data.best_guess)}]</div>
                ${bestDesc}
            </div>
            ${vsHTML}
            <div class="split-box worst-box slide-in-right">
                <span style="color:#F43F5E">WORST CASE</span>
                <div class="highlight">[${safeJoin(wcGuess)}]</div>
                ${worstDesc}
            </div>`;
    } else if (evalData.top_guesses && evalData.top_guesses.length >= 2) {
        const best = evalData.top_guesses[0], worst = evalData.top_guesses[evalData.top_guesses.length-1];
        container.innerHTML = `<div class="split-box best-box slide-in-left"><span style="color:#10B981">BEST FREQ</span><div class="highlight">[${safeJoin(best.guess)}]</div><div>가중치: ${best.score.toFixed(2)}</div></div>
            ${vsHTML}
            <div class="split-box worst-box slide-in-right"><span style="color:#F43F5E">COMPETITOR</span><div class="highlight">[${safeJoin(worst.guess)}]</div><div>가중치: ${worst.score.toFixed(2)}</div></div>`;
    } else {
        container.innerHTML = "<div style='width:100%; text-align:center; color:#64748B; padding-top:20px;'>[데이터 수집 중]</div>"; 
    }
}