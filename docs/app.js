const sampleStories = [
    {
        id: "account_init",
        title: "Account Initialization",
        category: "⭐ CORE: Verification Loop",
        domain: "Banking",
        text: "As a user, I want to initialize my bank account with a starting balance of 100.",
        dafnyBuggy: "class Account {\n  var balance: int\n  constructor() {\n    balance = 100; // Bug: invalid assignment\n  }\n}",
        dafnyFix: "class Account {\n  var balance: int\n  constructor() {\n    balance := 100; // Corrected assignment operator\n  }\n}",
        errors: "test_spec_adk.dfy(4,12): Error: invalid NameSegment\n  |\n4 |     balance = 100; // Bug\n  |             ^",
        summary: "This change initializes the bank account balance field with an initial deposit value of 100 using Dafny verified constructors.",
        gherkin: "Feature: Bank Account\n  Scenario: Initialize\n    Given the initial deposit balance is 100",
        rubyCode: "Given(/^the initial deposit balance is (\\d+)$/) do |balance|\n  @account = Account.new(balance.to_i)\n  # Verification check\n  expect(@account.balance).to eq(100)\nend"
    },
    {
        id: "atm_withdraw",
        title: "ATM Cash Withdrawal",
        category: "⭐ CORE: Dependency Map",
        domain: "Banking",
        text: "As a user, I want to withdraw cash from my bank account, subject to positive balance check.",
        dafnyBuggy: "method Withdraw(amount: int)\n  requires balance >= amount\n{\n  balance = balance - amount; // Bug: invalid assignment\n}",
        dafnyFix: "method Withdraw(amount: int)\n  requires balance >= amount\n  modifies this\n  ensures balance == old(balance) - amount\n{\n  balance := balance - amount;\n}",
        errors: "test_spec_adk.dfy(5,10): Error: invalid NameSegment\n  |\n5 |   balance = balance - amount;\n  |           ^",
        summary: "This change introduces the cash withdrawal operation, enforcing safety preconditions (balance must be >= amount) and updates the balance state securely.",
        gherkin: "Feature: ATM Withdrawal\n  Scenario: Withdraw Cash\n    When the user withdraws 50",
        rubyCode: "When(/^the user withdraws (\\d+)$/) do |amount|\n  @account.withdraw(amount.to_i)\n  # Verification checklist\n  expect(@account.balance).to eq(50)\nend"
    },
    {
        id: "seat_allocation",
        title: "Flight Seat Allocation",
        category: "Booking Domain",
        domain: "Booking",
        text: "As a user, I want to reserve a specific seat on a flight, ensuring the seat is not already allocated.",
        dafnyBuggy: "method AllocateSeat(seatId: int)\n{\n  seats[seatId] = true; // Bug: no occupancy check\n}",
        dafnyFix: "method AllocateSeat(seatId: int)\n  requires seatId >= 0 && seatId < MaxSeats\n  requires !seats[seatId]\n  modifies this\n  ensures seats[seatId]\n{\n  seats[seatId] := true;\n}",
        errors: "test_spec_adk.dfy(3,10): Error: pre-condition violation. Seat occupancy constraint missing.",
        summary: "Enforces seat boundaries and checks seat availability status before marking it as allocated.",
        gherkin: "Feature: Flight Booking\n  Scenario: Reserve Seat\n    Given seat 12B is available\n    When the user reserves seat 12B\n    Then seat 12B should be occupied",
        rubyCode: "Given(/^seat (\\w+) is available$/) do |seat_id|\n  @flight.mark_available(seat_id)\nend\n\nWhen(/^the user reserves seat (\\w+)$/) do |seat_id|\n  @flight.allocate(seat_id)\nend"
    },
    {
        id: "retail_discount",
        title: "Retail Discount Checkout",
        category: "Retail Domain",
        domain: "Retail",
        text: "As a user, I want to apply a coupon code at checkout to reduce my total cart price.",
        dafnyBuggy: "method ApplyCoupon(coupon: Coupon)\n{\n  cart.total = cart.total - coupon.value; // Bug: negative checkout check missing\n}",
        dafnyFix: "method ApplyCoupon(coupon: Coupon)\n  requires cart.total >= coupon.value\n  modifies this\n  ensures cart.total == old(cart.total) - coupon.value\n{\n  cart.total := cart.total - coupon.value;\n}",
        errors: "test_spec_adk.dfy(4,14): Error: post-condition violation. Cart total fell below zero.",
        summary: "Validates checkout totals, ensuring coupon values do not exceed the current cart balance.",
        gherkin: "Feature: Retail Checkout\n  Scenario: Apply Promo\n    Given the cart total is 100\n    When the user applies coupon of 20\n    Then the checkout total should be 80",
        rubyCode: "Given(/^the cart total is (\\d+)$/) do |total|\n  @cart = Cart.new(total.to_i)\nend\n\nWhen(/^the user applies coupon of (\\d+)$/) do |val|\n  @cart.apply_coupon(val.to_i)\nend"
    },
    {
        id: "medical_prescription",
        title: "Prescription Validation",
        category: "Medical Domain",
        domain: "Medical",
        text: "As a user, I want to validate drug dosage levels against FDA maximum limits before authorization.",
        dafnyBuggy: "method Dispense(dose: int)\n{\n  activeDose = dose; // Bug: limit check missing\n}",
        dafnyFix: "method Dispense(dose: int)\n  requires dose > 0 && dose <= MaxFdaDose\n  modifies this\n  ensures activeDose == dose\n{\n  activeDose := dose;\n}",
        errors: "test_spec_adk.dfy(3,14): Error: invariant violation. Dose exceeds FDA safety limit.",
        summary: "Validates pharmaceutical dosage parameters against medical bounds before dispensing stubs.",
        gherkin: "Feature: Pharmacy Dispenser\n  Scenario: Safety Check\n    When doctor prescribes 500mg dosage\n    Then the system should verify and authorize",
        rubyCode: "When(/^doctor prescribes (\\d+)mg dosage$/) do |dosage|\n  @dispenser.prescribe(dosage.to_i)\nend\n\nThen(/^the system should verify and authorize$/) do\n  expect(@dispenser.authorized?).to be_truthy\nend"
    },
    {
        id: "logistics_mileage",
        title: "Logistics Mileage Tracking",
        category: "Logistics Domain",
        domain: "Logistics",
        text: "As a user, I want to track delivery vehicle mileage logs to ensure fuel efficiency compliance.",
        dafnyBuggy: "method LogMileage(dist: int)\n{\n  mileage = mileage + dist; // Bug: invalid assignment\n}",
        dafnyFix: "method LogMileage(dist: int)\n  requires dist > 0\n  modifies this\n  ensures mileage == old(mileage) + dist\n{\n  mileage := mileage + dist;\n}",
        errors: "test_spec_ady.dfy(3,10): Error: pre-condition violation. Distance traveled must be positive.",
        summary: "Accumulates distance logs on vehicle state objects, validating trip parameters.",
        gherkin: "Feature: Mileage Logging\n  Scenario: Record Trip\n    Given starting mileage is 10000\n    When the vehicle travels 150 miles\n    Then the odometer should read 10150",
        rubyCode: "Given(/^starting mileage is (\\d+)$/) do |start_mil|\n  @truck = Vehicle.new(start_mil.to_i)\nend\n\nWhen(/^the vehicle travels (\\d+) miles$/) do |dist|\n  @truck.drive(dist.to_i)\nend"
    },
    {
        id: "smart_home_temp",
        title: "Smart Thermostat Limit",
        category: "Smart Home Domain",
        domain: "Smart Home",
        text: "As a user, I want to regulate house temperature safely within bounds of 15 to 30 degrees.",
        dafnyBuggy: "method SetTemp(t: int)\n{\n  temp = t; // Bug: bound checks missing\n}",
        dafnyFix: "method SetTemp(t: int)\n  requires t >= 15 && t <= 30\n  modifies this\n  ensures temp == t\n{\n  temp := t;\n}",
        errors: "test_spec_adk.dfy(3,10): Error: post-condition violation. Target temperature exceeds safety envelope.",
        summary: "Validates thermostat inputs to keep climate control within safe regulatory bounds.",
        gherkin: "Feature: Smart Thermostat\n  Scenario: Set Bounds\n    Given thermostat is set to 20\n    When temperature is changed to 25\n    Then target temp should be 25",
        rubyCode: "Given(/^thermostat is set to (\\d+)$/) do |temp|\n  @thermostat = Thermostat.new(temp.to_i)\nend\n\nWhen(/^temperature is changed to (\\d+)$/) do |target|\n  @thermostat.set_temperature(target.to_i)\nend"
    }
];

let selectedStory = sampleStories[0];

// Initialize DOM elements
const storyList = document.getElementById("storyList");
const customStory = document.getElementById("customStory");
const runBtn = document.getElementById("runBtn");
const terminalLog = document.getElementById("terminalLog");
const graphViewport = document.getElementById("graphViewport");
const traceContainer = document.getElementById("traceContainer");
const vibeSummary = document.getElementById("vibeSummary");
const consentActions = document.getElementById("consentActions");
const codeEditorBox = document.getElementById("codeEditorBox");
const proposedCodeEditor = document.getElementById("proposedCodeEditor");
const approveBtn = document.getElementById("approveBtn");
const rejectBtn = document.getElementById("rejectBtn");

// Dafny spec elements
const specCard = document.getElementById("specCard");
const specStatus = document.getElementById("specStatus");
const specCodeArea = document.getElementById("specCodeArea");

// Render story selection list
function renderStories() {
    storyList.innerHTML = "";
    sampleStories.forEach(story => {
        const item = document.createElement("div");
        const isCore = story.category.includes("⭐ CORE");
        item.className = "story-item" + (selectedStory.id === story.id ? " active" : "") + (isCore ? " core-story" : "");
        
        item.innerHTML = `
            <div class="story-title">${story.title}</div>
            <div class="story-badge">${story.category}</div>
        `;
        storyList.appendChild(item);
    });
    
    // Bind click events
    Array.from(storyList.children).forEach((child, index) => {
        child.onclick = () => {
            selectedStory = sampleStories[index];
            customStory.value = "";
            codeEditorBox.style.display = "none";
            specCard.style.display = "none";
            renderStories();
        };
    });
}

// Write line to terminal with delay
function writeLog(text, className = "") {
    const span = document.createElement("span");
    span.className = className;
    span.textContent = text;
    terminalLog.appendChild(span);
    terminalLog.scrollTop = terminalLog.scrollHeight;
}

// Render SVG Graph Viewport
function drawGraph(activeNodeId = null, highlightDependents = false) {
    const isWithdraw = selectedStory.id === "atm_withdraw";
    
    // Nodes coordinates
    const nodes = [
        { id: "story", label: "UserStory", title: selectedStory.title, x: 60, y: 70, color: "#3b82f6" },
        { id: "step", label: "GherkinStep", title: selectedStory.gherkin.split('\n')[2] || "Cucumber Step", x: 190, y: 70, color: "#10b981" },
        { id: "ruby", label: "RubyDefinition", title: "Ruby Step Implementation", x: 320, y: 70, color: "#8b5cf6" }
    ];
    
    // If it's the withdrawal story, add dependency node
    if (isWithdraw) {
        nodes.push({ id: "dep_story", label: "DependentStory", title: "Account Initialization (Parent)", x: 60, y: 200, color: "#f59e0b" });
    }

    let edges = [
        { from: "story", to: "step", label: "IMPLEMENTS" },
        { from: "step", to: "ruby", label: "BINDS" }
    ];
    
    if (isWithdraw) {
        edges.push({ from: "story", to: "dep_story", label: "DEPENDS_ON" });
    }

    let svgContent = `<svg class="graph-svg">
        <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="15" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#a1a1aa" />
            </marker>
        </defs>`;

    // Draw Edges
    edges.forEach(edge => {
        const fromNode = nodes.find(n => n.id === edge.from);
        const toNode = nodes.find(n => n.id === edge.to);
        const isHighlighted = highlightDependents && (edge.from === "story" && edge.to === "dep_story");
        const strokeColor = isHighlighted ? "#f59e0b" : "#3f3f46";
        const strokeWidth = isHighlighted ? "3" : "1.5";
        
        svgContent += `<line x1="${fromNode.x}" y1="${fromNode.y}" x2="${toNode.x}" y2="${toNode.y}" 
            stroke="${strokeColor}" stroke-width="${strokeWidth}" marker-end="url(#arrow)" class="graph-edge" />`;
    });

    // Draw Nodes
    nodes.forEach(node => {
        const isActive = activeNodeId === node.id;
        const stroke = isActive ? "#fff" : "transparent";
        const r = isActive ? 22 : 18;
        svgContent += `
            <g class="graph-node" onclick="nodeClick('${node.id}')">
                <circle cx="${node.x}" cy="${node.y}" r="${r}" fill="${node.color}" stroke="${stroke}" stroke-width="2" />
                <text x="${node.x}" y="${node.y + 35}" fill="#f4f4f5" font-size="10" text-anchor="middle" font-weight="600">${node.label}</text>
                <title>${node.title}</title>
            </g>`;
    });

    svgContent += `</svg>`;
    graphViewport.innerHTML = svgContent;
}

// Handle node clicks in Graph
window.nodeClick = function(nodeId) {
    if (nodeId === "story" && selectedStory.id === "atm_withdraw") {
        writeLog("[Graph GQL Query] Running transitive dependents search...", "cyan");
        writeLog("[Impact Map] Transitive dependency detected: ATM Cash Withdrawal depends on Account Initialization.", "yellow");
        drawGraph("story", true);
    } else {
        drawGraph(nodeId, false);
    }
};

// Render OpenTelemetry Traces
function renderTraces(widths = { p1: 0, p2: 0, p3: 0, p4: 0 }) {
    const spans = [
        { id: "parent", label: "run_adk_pipeline", width: 100, color: "rgba(255, 255, 255, 0.1)" },
        { id: "p1", label: "  ├── phase1_autoformalization", width: widths.p1, color: "rgba(59, 130, 246, 0.5)" },
        { id: "p2", label: "  ├── phase2_verification_loop", width: widths.p2, color: "rgba(139, 92, 246, 0.5)" },
        { id: "p3", label: "  ├── phase3_test_generation", width: widths.p3, color: "rgba(16, 185, 129, 0.5)" },
        { id: "p4", label: "  └── phase4_human_in_the_loop_mapping", width: widths.p4, color: "rgba(245, 158, 11, 0.5)" }
    ];

    traceContainer.innerHTML = "";
    spans.forEach(span => {
        traceContainer.innerHTML += `
            <div class="trace-bar">
                <div class="trace-fill" style="width: ${span.width}%; background: ${span.color}"></div>
                <div class="trace-label">${span.label}</div>
                <div class="trace-duration">${span.width > 0 ? (span.width * 20) + "ms" : "Pending"}</div>
            </div>`;
    });
}

// Main execution simulation
async function runPipeline() {
    // Reset state
    terminalLog.innerHTML = "";
    consentActions.style.display = "none";
    codeEditorBox.style.display = "none";
    vibeSummary.textContent = "Processing pipeline...";
    vibeSummary.className = "vibe-summary";
    renderTraces();
    drawGraph();
    
    // Reset and show spec card
    specCard.style.display = "block";
    specStatus.textContent = "PENDING";
    specStatus.className = "spec-badge pending";
    specCodeArea.textContent = "// Running autoformalizer agent...";
    
    const storyText = customStory.value.trim() || selectedStory.text;
    
    writeLog("Starting pipeline execution...", "cyan");
    await sleep(800);
    
    // Phase 1: Autoformalization
    writeLog("============================================================", "yellow");
    writeLog("PHASE 1: AUTOFORMALIZATION (ADK Agent)", "yellow");
    writeLog("============================================================", "yellow");
    writeLog("Generating initial Dafny specification from story requirement...");
    renderTraces({ p1: 95, p2: 0, p3: 0, p4: 0 });
    
    specStatus.textContent = "VERIFYING";
    specStatus.className = "spec-badge verifying";
    specCodeArea.textContent = selectedStory.dafnyBuggy;
    
    await sleep(1500);
    writeLog("Initial specification drafted successfully.");
    
    // Phase 1b: Semantic Critic
    writeLog("\nPHASE 1b: REFLECTIVE SEMANTIC CRITIC", "cyan");
    writeLog("Checking semantic consistency...");
    await sleep(800);
    writeLog("[OK] Semantic validation passed: all constraints are modeled.");
    
    // Phase 2: Verification Loop
    writeLog("\n============================================================", "yellow");
    writeLog("PHASE 2: VERIFICATION LOOP (Dafny Compiler)", "yellow");
    writeLog("============================================================", "yellow");
    renderTraces({ p1: 95, p2: 40, p3: 0, p4: 0 });
    
    if (selectedStory.id === "atm_withdraw") {
        writeLog("[Graph Query] Checking downstream dependencies...");
        writeLog("--- PRE-RECOMPILATION IMPACT MAP ---", "yellow");
        writeLog("Target: atm_withdraw.txt");
        writeLog("  - [Direct Dependent] -> dependent_story.txt (Atm Withdrawal Limit Check)", "red");
        await sleep(1200);
    }
    
    writeLog("Verification Attempt 1/3...");
    await sleep(1000);
    writeLog("FAILED: Verification issues detected:", "red");
    writeLog(selectedStory.errors, "red");
    
    // Update spec status to failed and show logs
    specStatus.textContent = "FAILED (ATTEMPT 1)";
    specStatus.className = "spec-badge failed";
    specCodeArea.textContent = `${selectedStory.dafnyBuggy}\n\n// --- COMPILER ERRORS ---\n${selectedStory.errors}`;
    
    writeLog("\nTriggering ADK self-correction loop...", "yellow");
    writeLog("[Task Breakdown] Generated fix checklist:\n  - [ ] Fix syntax errors or modifier mappings");
    await sleep(1500);
    
    writeLog("Self-correction compiled. Resubmitting to verification compiler...");
    writeLog("Verification Attempt 2/3...");
    renderTraces({ p1: 95, p2: 90, p3: 0, p4: 0 });
    
    specStatus.textContent = "VERIFYING (ATTEMPT 2)";
    specStatus.className = "spec-badge verifying";
    specCodeArea.textContent = selectedStory.dafnyFix;
    
    await sleep(1200);
    writeLog("SUCCESS: Dafny specification verified successfully in attempt 2!", "green");
    writeLog("[Graph] Saved verified specification to graph database.");
    
    // Update spec status to success
    specStatus.textContent = "SUCCESS (VERIFIED)";
    specStatus.className = "spec-badge success";
    
    // Phase 3: Feature Generation
    writeLog("\n============================================================", "yellow");
    writeLog("PHASE 3: BDD GHERKIN TEST GENERATION", "yellow");
    writeLog("============================================================", "yellow");
    renderTraces({ p1: 95, p2: 90, p3: 85, p4: 0 });
    await sleep(1200);
    writeLog("Saving final Gherkin tests to test_output_adk.feature...", "green");
    writeLog(selectedStory.gherkin);
    
    // Phase 4: Consent check
    writeLog("\n============================================================", "yellow");
    writeLog("PHASE 4: HUMAN-IN-THE-LOOP CUCUMBER MAPPING", "yellow");
    writeLog("============================================================", "yellow");
    renderTraces({ p1: 95, p2: 90, p3: 85, p4: 80 });
    await sleep(1000);
    
    writeLog("[!] HUMAN-IN-THE-LOOP CHECKPOINT: Unmapped Gherkin Step Detected!", "yellow");
    writeLog("Invoking 'ruby-step-scaffolder' Agent Skill... (Intercepted by Quorum)");
    await sleep(1000);
    
    // Activate Consent Gate Card UI & load proposed code
    vibeSummary.textContent = selectedStory.summary;
    proposedCodeEditor.value = selectedStory.rubyCode;
    codeEditorBox.style.display = "block";
    consentActions.style.display = "flex";
    document.getElementById("consentCard").scrollIntoView({ behavior: 'smooth' });
}

// Utility Sleep helper
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Handle Consent Decision Actions
approveBtn.onclick = () => {
    const finalCode = proposedCodeEditor.value.trim();
    writeLog("[Quorum] Evaluation decision: Approved=True.", "green");
    writeLog("[Quorum] Writing approved custom code stub to step definitions:\n" + finalCode, "green");
    writeLog("[+] Successfully committed modifications to disk.", "green");
    writeLog("\n[Telemetry] Step Reuse Coverage Score: 100% (1/1 steps mapped)", "cyan");
    writeLog("BDD VERIFICATION PIPELINE COMPLETED SUCCESSFULLY!", "green");
    
    consentActions.style.display = "none";
    codeEditorBox.style.display = "none";
    vibeSummary.textContent = "Code change APPROVED and written to disk successfully.";
    vibeSummary.className = "vibe-summary green-text";
    
    // Render final traces & graph status
    renderTraces({ p1: 95, p2: 90, p3: 85, p4: 100 });
    drawGraph("ruby");
};

rejectBtn.onclick = () => {
    writeLog("[!] [Quorum Reject] Proposed code modification was REJECTED by User.", "red");
    writeLog("ValueError: User rejected code change consensus. Aborting file update.", "red");
    
    consentActions.style.display = "none";
    codeEditorBox.style.display = "none";
    vibeSummary.textContent = "Code change REJECTED. Pipeline execution aborted and files rolled back.";
    vibeSummary.className = "vibe-summary red-text";
    
    renderTraces({ p1: 95, p2: 90, p3: 85, p4: 20 });
};

// Initial Render
renderStories();
drawGraph();
renderTraces();

runBtn.onclick = runPipeline;
