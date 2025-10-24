// RugDetector UI - Main Application
// Handles form submission, API calls, and result visualization

// Configuration
const API_BASE_URL = window.location.origin;
const API_ENDPOINT = `${API_BASE_URL}/check`;

// DOM Elements
const form = document.getElementById('analyzerForm');
const loadingState = document.getElementById('loadingState');
const results = document.getElementById('results');
const analyzeBtn = document.getElementById('analyzeBtn');

// Result Elements
const riskScore = document.getElementById('riskScore');
const riskCategory = document.getElementById('riskCategory');
const riskBadge = document.getElementById('riskBadge');
const riskRecommendation = document.getElementById('riskRecommendation');
const confidenceValue = document.getElementById('confidenceValue');
const riskCircle = document.getElementById('riskCircle');
const featuresGrid = document.getElementById('featuresGrid');
const detailAddress = document.getElementById('detailAddress');
const detailBlockchain = document.getElementById('detailBlockchain');
const detailTimestamp = document.getElementById('detailTimestamp');

// State
let currentAnalysis = null;

// Event Listeners
form.addEventListener('submit', handleFormSubmit);

// Handle form submission
async function handleFormSubmit(e) {
    e.preventDefault();

    // Get form values
    const contractAddress = document.getElementById('contractAddress').value.trim();
    const blockchain = document.getElementById('blockchain').value;
    const paymentId = document.getElementById('paymentId').value.trim();

    // Validate contract address
    if (!isValidAddress(contractAddress)) {
        showError('Invalid contract address format. Must be 0x followed by 40 hex characters.');
        return;
    }

    // Show loading state
    showLoading();

    try {
        // Call API
        const analysisResult = await analyzeContract(contractAddress, blockchain, paymentId);

        // Store result
        currentAnalysis = analysisResult;

        // Display results
        displayResults(analysisResult);

    } catch (error) {
        console.error('Analysis error:', error);
        showError(error.message || 'Failed to analyze contract. Please try again.');
        hideLoading();
    }
}

// Call API to analyze contract
async function analyzeContract(contractAddress, blockchain, paymentId) {
    const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            contract_address: contractAddress,
            blockchain: blockchain,
            payment_id: paymentId
        })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `API error: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
        throw new Error(data.error || 'Analysis failed');
    }

    return data.data;
}

// Display analysis results
function displayResults(data) {
    hideLoading();
    results.style.display = 'flex';

    // Scroll to results
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Update risk score
    updateRiskScore(data.riskScore, data.riskCategory);

    // Update risk badge
    updateRiskBadge(data.riskCategory);

    // Update recommendation
    riskRecommendation.textContent = data.recommendation;

    // Update confidence
    confidenceValue.textContent = `${(data.confidence * 100).toFixed(1)}%`;

    // Update features
    displayFeatures(data.features);

    // Update contract details
    detailAddress.textContent = formatAddress(data.contract_address);
    detailBlockchain.textContent = capitalizeFirst(data.blockchain);
    detailTimestamp.textContent = formatTimestamp(data.analysis_timestamp);
}

// Update risk score display
function updateRiskScore(score, category) {
    // Animate score
    animateNumber(riskScore, 0, score, 1000, 2);

    // Update category
    riskCategory.textContent = capitalizeFirst(category);

    // Animate circle
    const circumference = 2 * Math.PI * 85; // radius = 85
    const offset = circumference - (score * circumference);
    riskCircle.style.strokeDashoffset = offset;

    // Update circle color based on risk
    const gradient = document.getElementById('riskGradient');
    const stops = gradient.querySelectorAll('stop');

    if (category === 'low') {
        stops[0].setAttribute('stop-color', '#00ff88');
        stops[1].setAttribute('stop-color', '#00ffff');
    } else if (category === 'medium') {
        stops[0].setAttribute('stop-color', '#ffcc00');
        stops[1].setAttribute('stop-color', '#ff9500');
    } else if (category === 'high') {
        stops[0].setAttribute('stop-color', '#ff3366');
        stops[1].setAttribute('stop-color', '#ff6b9d');
    }
}

// Update risk badge
function updateRiskBadge(category) {
    riskBadge.className = `risk-badge ${category}`;
    riskBadge.querySelector('.badge-text').textContent = capitalizeFirst(category) + ' Risk';
}

// Display features
function displayFeatures(features) {
    featuresGrid.innerHTML = '';

    // Convert features object to array and sort by importance
    const featureArray = Object.entries(features);

    // Create feature categories
    const categories = {
        'ownership': ['hasOwnershipTransfer', 'hasRenounceOwnership', 'ownerBalance', 'ownerVerified', 'ownerBlacklisted'],
        'liquidity': ['hasLiquidityLock', 'liquidityRatio', 'liquidityLockedDays', 'lowLiquidityWarning', 'liquidityValue', 'liquidityChangePercent'],
        'holders': ['holderCount', 'holderConcentration', 'top10HoldersPercent', 'suspiciousHolderPatterns', 'giniCoefficient'],
        'code': ['hasHiddenMint', 'hasPausableTransfers', 'hasBlacklist', 'verifiedContract', 'auditedByFirm'],
        'time': ['contractAge', 'lastActivityDays', 'avgDailyTransactions', 'suspiciousPatterns', 'highFailureRate']
    };

    // Store all features with their categories
    window.featureCategories = categories;
    window.allFeatures = features;

    // Display all features initially
    displayFeaturesByCategory('all');

    // Setup tab listeners
    setupFeatureTabs();
}

// Display features by category
function displayFeaturesByCategory(category) {
    featuresGrid.innerHTML = '';

    if (category === 'all') {
        // Display all features
        Object.entries(window.allFeatures).forEach(([key, value]) => {
            const featureEl = createFeatureElement(key, value);
            featuresGrid.appendChild(featureEl);
        });
    } else {
        // Display features for specific category
        const categoryFeatures = window.featureCategories[category] || [];
        categoryFeatures.forEach(key => {
            if (window.allFeatures.hasOwnProperty(key)) {
                const value = window.allFeatures[key];
                const featureEl = createFeatureElement(key, value);
                featuresGrid.appendChild(featureEl);
            }
        });
    }
}

// Setup feature tab listeners
function setupFeatureTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all tabs
            tabBtns.forEach(b => b.classList.remove('active'));

            // Add active class to clicked tab
            btn.classList.add('active');

            // Get category
            const category = btn.getAttribute('data-category');

            // Display features for this category
            displayFeaturesByCategory(category);
        });
    });
}

// Create feature element
function createFeatureElement(name, value) {
    const div = document.createElement('div');
    div.className = 'feature-item';

    const nameEl = document.createElement('div');
    nameEl.className = 'feature-name';
    nameEl.textContent = formatFeatureName(name);

    const valueEl = document.createElement('div');
    valueEl.className = `feature-value ${typeof value === 'boolean' ? 'boolean' : 'numeric'}`;
    valueEl.textContent = formatFeatureValue(value);

    div.appendChild(nameEl);
    div.appendChild(valueEl);

    return div;
}

// Format feature name (camelCase to Title Case)
function formatFeatureName(name) {
    return name
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
}

// Format feature value
function formatFeatureValue(value) {
    if (typeof value === 'boolean') {
        return value ? '✓ Yes' : '✗ No';
    } else if (typeof value === 'number') {
        if (value < 1 && value > 0) {
            return (value * 100).toFixed(1) + '%';
        } else if (Number.isInteger(value)) {
            return value.toLocaleString();
        } else {
            return value.toFixed(2);
        }
    }
    return String(value);
}

// Show loading state
function showLoading() {
    form.style.display = 'none';
    loadingState.style.display = 'block';
    results.style.display = 'none';
    analyzeBtn.disabled = true;

    // Animate loading steps
    animateLoadingSteps();
}

// Hide loading state
function hideLoading() {
    form.style.display = 'flex';
    loadingState.style.display = 'none';
    analyzeBtn.disabled = false;
}

// Show error message
function showError(message) {
    alert(`Error: ${message}`);
}

// Validate Ethereum address
function isValidAddress(address) {
    return /^0x[a-fA-F0-9]{40}$/.test(address);
}

// Format address (shorten)
function formatAddress(address) {
    if (!address) return 'N/A';
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

// Capitalize first letter
function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// Format timestamp
function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Animate number
function animateNumber(element, start, end, duration, decimals = 0) {
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function (ease out cubic)
        const eased = 1 - Math.pow(1 - progress, 3);

        const current = start + (end - start) * eased;
        element.textContent = current.toFixed(decimals);

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

// Sample contract addresses for quick testing
const sampleAddresses = {
    uniswap: '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f', // Low risk
    test1: '0x1111111111111111111111111111111111111111', // Medium risk
    test2: '0x0000000000000000000000000000000000000000'  // High risk
};

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to submit form
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (form.style.display !== 'none') {
            form.dispatchEvent(new Event('submit'));
        }
    }
});

// Initialize tooltips (if needed)
document.querySelectorAll('[data-tooltip]').forEach(element => {
    element.addEventListener('mouseenter', (e) => {
        const tooltip = e.target.getAttribute('data-tooltip');
        // Add tooltip display logic here
    });
});

// Animate loading steps
function animateLoadingSteps() {
    const steps = [
        'step1', 'step2', 'step3', 'step4', 'step5'
    ];

    // Reset all steps
    steps.forEach(stepId => {
        const step = document.getElementById(stepId);
        if (step) {
            step.classList.remove('active', 'completed');
        }
    });

    // Animate steps sequentially
    let currentStep = 0;
    const stepDuration = 1200; // ms per step

    const interval = setInterval(() => {
        if (currentStep > 0) {
            const prevStep = document.getElementById(steps[currentStep - 1]);
            if (prevStep) {
                prevStep.classList.remove('active');
                prevStep.classList.add('completed');
                prevStep.textContent = prevStep.textContent.replace('⏳', '✅');
            }
        }

        if (currentStep < steps.length) {
            const step = document.getElementById(steps[currentStep]);
            if (step) {
                step.classList.add('active');
            }
            currentStep++;
        } else {
            clearInterval(interval);
        }
    }, stepDuration);

    // Store interval ID to clear it when results are shown
    window.loadingInterval = interval;
}

// Override hideLoading to clear loading animation
const originalHideLoading = hideLoading;
function hideLoading() {
    if (window.loadingInterval) {
        clearInterval(window.loadingInterval);
    }
    form.style.display = 'flex';
    loadingState.style.display = 'none';
    analyzeBtn.disabled = false;
}

console.log('🚀 RugDetector UI initialized');
console.log('API endpoint:', API_ENDPOINT);
