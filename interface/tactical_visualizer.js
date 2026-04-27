window.renderTacticalDisplay = async function(fileName) {
    try {
        const response = await fetch(`http://127.0.0.1:8000/logs/${fileName}`);
        const logDataText = await response.text();
        if (logDataText.includes("waiting") || !logDataText.trim()) return; 
        renderAll(logDataText); 
    } catch (error) { console.error("D3 통신 에러:", error); }
};

window.loadHistoryFile = async function(fileName) {
    try {
        const response = await fetch(`http://127.0.0.1:8000/logs/${fileName}`);
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
        const res = await fetch('http://127.0.0.1:8000/api/logs');
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

window.refreshLogList();

const safeJoin = (v) => Array.isArray(v) ? v.join("") : (v || "-");
function parseSplit(arr) {
    if (!arr || !Array.isArray(arr) || arr.length === 0) return {s:'-', b:'-', c:'-'};
    let target = (Array.isArray(arr[0]) && Array.isArray(arr[0][0])) ? arr[0] : arr;
    if (Array.isArray(target) && target.length >= 2 && Array.isArray(target[0])) {
        return {s: target[0][0], b: target[0][1], c: target[1]};
    }
    return {s:'-', b:'-', c:'-'};
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

    try { renderDash1(latest, displayStatus); } catch(e) { document.getElementById("dash1").innerHTML = `<div style="color:red; padding:10px;">Dash1 Error: ${e.message}</div>`; }
    try { renderDash2(history); } catch(e) { document.getElementById("dash2").innerHTML = `<div style="color:red; padding:10px;">Dash2 Error: ${e.message}</div>`; }
    try { renderDash3(latest, displayStatus); } catch(e) { document.getElementById("dash3").innerHTML = `<div style="color:red; padding:10px;">Dash3 Error: ${e.message}</div>`; }
    try { renderDash4(latest, displayStatus); } catch(e) { document.getElementById("dash4").innerHTML = `<div style="color:red; padding:10px;">Dash4 Error: ${e.message}</div>`; }
}

function renderDash1(data, status) {
    const probs = data.dashboard_1_heatmap?.probabilities;
    if (!probs) {
        document.getElementById("dash1").innerHTML = "<div style='color:#64748B; width:100%; text-align:center; margin-top:20px;'>해당 솔버는 확률장(Heatmap)을 연산하지 않습니다.</div>";
        return;
    }
    
    const colors = ["#F43F5E", "#38BDF8", "#10B981", "#F59E0B"];
    if (!window.dash1State) window.dash1State = { turn: -1, chambers: [{},{},{},{}] };
    
    const isNewTurn = window.dash1State.turn !== data.turn;
    window.dash1State.turn = data.turn;

    probs.forEach((posProbs, i) => {
        let ch = window.dash1State.chambers[i];
        const c = document.getElementById(`ch${i}`); 
        if (!c) return; 
        
        const w = c.clientWidth, h = c.clientHeight;
        if (w === 0 || h === 0) return;

        if (!ch.initialized) {
            c.innerHTML = '<div style="position:absolute; top:4px; left:6px; font-size:0.55rem; color:#475569; z-index:5;">POS '+(i+1)+'</div>';
            const svg = d3.select(c).append("svg").attr("width", "100%").attr("height", "100%");
            const defs = svg.append("defs");
            
            ch.clipNewId = `clip-new-ch${i}`;
            ch.clipOldId = `clip-old-ch${i}`;
            
            defs.append("clipPath").attr("id", ch.clipNewId).append("rect").attr("class", "rect-new").attr("x", 0).attr("y", 0).attr("width", w).attr("height", 0);
            defs.append("clipPath").attr("id", ch.clipOldId).append("rect").attr("class", "rect-old").attr("x", 0).attr("y", 0).attr("width", w).attr("height", h);
            
            ch.x = d3.scaleLinear().domain([0, 1]).range([i===0?25:10, w-10]);
            ch.y = d3.scalePoint().domain(d3.range(10)).range([15, h-15]);
            if (i === 0) svg.append("g").attr("transform", "translate(22,0)").call(d3.axisLeft(ch.y).tickSize(2));
            
            const gOld = svg.append("g").attr("clip-path", `url(#${ch.clipOldId})`);
            ch.pathOld = gOld.append("path").attr("fill", "none").attr("stroke-width", 2).attr("filter", "drop-shadow(0 0 3px currentColor)").attr("stroke", colors[i]);
            ch.laserOld = gOld.append("line").attr("stroke-width", 1.5).attr("stroke-dasharray", "3,3").attr("filter", "drop-shadow(0 0 4px #FFF)").attr("stroke", "#FFF").style("display", "none");

            const gNew = svg.append("g").attr("clip-path", `url(#${ch.clipNewId})`);
            ch.pathNew = gNew.append("path").attr("fill", "none").attr("stroke-width", 2).attr("filter", "drop-shadow(0 0 3px currentColor)").attr("stroke", colors[i]);
            ch.laserNew = gNew.append("line").attr("stroke-width", 1.5).attr("stroke-dasharray", "3,3").attr("filter", "drop-shadow(0 0 4px #FFF)").attr("stroke", "#FFF").style("display", "none");
            
            ch.scanner = d3.select(c).append("div").style("position", "absolute").style("width", "100%").style("height", "2px").style("background", "rgba(56, 189, 248, 0.8)").style("box-shadow", "0 0 15px #38BDF8, 0 0 5px #FFF").style("pointer-events", "none").style("top", "0px").style("opacity", 0);
            ch.svg = svg; ch.w = w; ch.h = h; ch.initialized = true;
        }

        if (isNewTurn) {
            if (!('currProbs' in ch)) {
                ch.currProbs = posProbs;
                ch.currGuess = data.best_guess ? data.best_guess[i] : null;
            }
            ch.prevProbs = ch.currProbs;
            ch.prevGuess = ch.currGuess;
            ch.currProbs = posProbs;
            ch.currGuess = data.best_guess ? data.best_guess[i] : null;

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
    
    const maxTurn = Math.max(d3.max(history, d=>Number(d.turn)) || 2, 2);
    const x = d3.scaleLinear().domain([1, maxTurn]).range([15, w-15]);
    const y = d3.scaleLinear().domain([0, trueMaxRemains]).range([h-30, 15]);

    const lineGen = d3.line().x(d => x(Number(d.turn))).y(d => y(Number(d.dashboard_2_trend?.remaining_count || 0))).curve(d3.curveLinear);
    
    lineLayer.append("path").datum(history).attr("fill", "none").attr("stroke", "#FFF").attr("stroke-width", 2.5).attr("filter", "drop-shadow(0 0 5px #FFF)").attr("d", lineGen);
    lineLayer.selectAll("circle").data(history).enter().append("circle").attr("cx", d=>x(Number(d.turn))).attr("cy", d=>y(Number(d.dashboard_2_trend?.remaining_count || 0))).attr("r", 4).attr("fill", "#38BDF8");
    lineLayer.raise();
}

function renderDash3(data, status) {
    if (!window.dash3State) window.dash3State = { turn: -1, status: '' };
    if (window.dash3State.turn === data.turn && window.dash3State.status === status) return;
    
    const container = document.getElementById("dash3");
    if (!container) return;
    
    if (window.dash3State.turn === data.turn && status === 'win') {
        const firstRow = container.querySelector('div');
        if (firstRow) firstRow.style.color = '#10B981';
        window.dash3State.status = status;
        return;
    }

    window.dash3State.turn = data.turn;
    window.dash3State.status = status;

    let topPicks = data.dashboard_3_evaluation?.top_guesses || [];
    if (topPicks.length === 0 && data.best_guess) topPicks = [{ guess: data.best_guess, score: 100 }];

    if(status === 'win' || Number(data.dashboard_2_trend?.remaining_count) <= 1) {
        if (data.best_guess) {
            container.innerHTML = `<div style="display:flex; align-items:center; gap:10px; font-size:0.75rem; margin-bottom:2px;">
                <div class="matrix-text" style="color:#10B981; font-weight:bold; width:55px; text-align:right;" data-val="[${safeJoin(data.best_guess)}]">[####]</div>
                <div style="flex:1; height:8px; background:#0A0F1C; border:1px solid #1E293B;"><div style="width: 100%; height:100%; background: linear-gradient(90deg, #059669, #10B981); box-shadow: 0 0 10px #10B981;"></div></div>
                <div style="color:#10B981; width:45px; font-size:0.7rem; text-align:right;">FINAL</div>
            </div>`;
            runMatrixEffect();
            return;
        }
    }

    if(!topPicks.length) { container.innerHTML = "<div style='color:#64748B; text-align:center; padding-top:20px;'>탐색 중...</div>"; return; }
    container.innerHTML = "";
    const maxS = d3.max(topPicks, d => d.score) || 1;
    topPicks.forEach(p => {
        container.innerHTML += `<div style="display:flex; align-items:center; gap:10px; font-size:0.75rem; margin-bottom:2px;">
            <div class="matrix-text" style="color:#38BDF8; font-weight:bold; width:55px; text-align:right;" data-val="[${safeJoin(p.guess)}]">[####]</div>
            <div style="flex:1; height:8px; background:#0A0F1C; border:1px solid #1E293B;"><div style="height:100%; width: ${(p.score/maxS)*100}%; background: linear-gradient(90deg, #0284C7, #38BDF8); transition: width 0.4s ease;"></div></div>
            <div style="color:#94A3B8; width:45px; font-size:0.7rem; text-align:right;">${p.score.toFixed(2)}</div>
        </div>`;
    });
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
    if (!window.dash4State) window.dash4State = { turn: -1, status: '' };
    if (window.dash4State.turn === data.turn && window.dash4State.status === status) return;
    
    const container = document.getElementById("dash4"); 
    if (!container) return;

    if (window.dash4State.turn === data.turn && (status === 'win' || status === 'lose')) {
        const vsText = container.querySelector('.vs-text');
        if (vsText) {
            vsText.classList.remove('pulse-vs');
            vsText.classList.add('static-vs');
        }
        window.dash4State.status = status;
        return;
    }

    window.dash4State.turn = data.turn;
    window.dash4State.status = status;

    const evalData = data.dashboard_3_evaluation || {};
    const isEnded = (status === 'win' || status === 'lose');
    const vsHTML = `<div class="vs-text ${isEnded ? 'static-vs' : 'pulse-vs'}">VS</div>`;

    if(evalData.expected_splits && evalData.expected_splits.length > 0) {
        const sp = parseSplit(evalData.expected_splits[0]);
        const wcInfo = evalData.worst_split_comparison || {};
        const wcGuess = wcInfo.guess || ['-','-','-','-'];
        const wc = parseSplit(wcInfo.splits);
        
        container.innerHTML = `<div class="split-box best-box slide-in-left"><span style="color:#10B981">TARGET ADOPTED</span><div class="highlight">[${safeJoin(data.best_guess)}]</div>
            <div>최악 피드백: ${sp.s}S ${sp.b}B</div><div>➔ 생존 노드: <span class="highlight">${sp.c}</span></div></div>
            ${vsHTML}
            <div class="split-box worst-box slide-in-right"><span style="color:#F43F5E">WORST CASE</span><div class="highlight">[${safeJoin(wcGuess)}]</div>
            <div>동일 피드백: ${wc.s}S ${wc.b}B</div><div>➔ 생존 노드: <span class="highlight">${wc.c}</span></div></div>`;
    } else if (evalData.top_guesses && evalData.top_guesses.length >= 2) {
        const best = evalData.top_guesses[0], worst = evalData.top_guesses[evalData.top_guesses.length-1];
        container.innerHTML = `<div class="split-box best-box slide-in-left"><span style="color:#10B981">BEST FREQ</span><div class="highlight">[${safeJoin(best.guess)}]</div><div>가중치: ${best.score.toFixed(2)}</div></div>
            ${vsHTML}
            <div class="split-box worst-box slide-in-right"><span style="color:#F43F5E">COMPETITOR</span><div class="highlight">[${safeJoin(worst.guess)}]</div><div>가중치: ${worst.score.toFixed(2)}</div></div>`;
    } else {
        container.innerHTML = "<div style='width:100%; text-align:center; color:#64748B; padding-top:20px;'>[데이터 수집 중]</div>"; 
    }
}