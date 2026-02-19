
// ═══════════════════════════════════════════════════════════
// KrishiMitra — IoT/Blockchain Feature (Antigravity Addition)
// Add this <script> block before </body> in index.html
// ═══════════════════════════════════════════════════════════

async function loadIoTData() {
    const location = window.currentLocation || 'Delhi';
    const container = document.getElementById('iot-blockchain-data');
    if (!container) return;

    container.innerHTML = '<div class="text-center p-4"><div class="spinner-border text-success"></div><p class="mt-2">IoT सेंसर डेटा लोड हो रहा है...</p></div>';

    try {
        const resp = await fetch(`/api/iot-blockchain/sensor_data/?location=${encodeURIComponent(location)}`);
        const data = await resp.json();

        const readings = data.readings || {};
        const blockchain = data.blockchain || {};
        const health = data.soil_health_score || {};
        const recs = data.recommendations || [];

        container.innerHTML = `
        <div class="row g-3">
            <div class="col-md-6">
                <div class="card border-success">
                    <div class="card-header bg-success text-white">
                        <i class="fas fa-microchip me-2"></i>IoT सेंसर रीडिंग्स
                        <span class="badge bg-light text-success ms-2">लाइव</span>
                    </div>
                    <div class="card-body">
                        <div class="row g-2">
                            <div class="col-6"><div class="p-2 bg-light rounded text-center">
                                <div class="fw-bold text-primary">${readings.soil_moisture_pct}%</div>
                                <small>मिट्टी नमी</small>
                            </div></div>
                            <div class="col-6"><div class="p-2 bg-light rounded text-center">
                                <div class="fw-bold text-danger">${readings.soil_temperature_c}°C</div>
                                <small>मिट्टी तापमान</small>
                            </div></div>
                            <div class="col-6"><div class="p-2 bg-light rounded text-center">
                                <div class="fw-bold text-warning">${readings.soil_ph}</div>
                                <small>pH मान</small>
                            </div></div>
                            <div class="col-6"><div class="p-2 bg-light rounded text-center">
                                <div class="fw-bold text-success">${health.grade || 'B'}</div>
                                <small>स्वास्थ्य ग्रेड</small>
                            </div></div>
                        </div>
                        <div class="mt-2"><strong>NPK:</strong> N=${readings.npk?.nitrogen_kg_ha} | P=${readings.npk?.phosphorus_kg_ha} | K=${readings.npk?.potassium_kg_ha}</div>
                        <div class="mt-1 text-muted small">सेंसर ID: ${data.sensor_id}</div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card border-primary">
                    <div class="card-header bg-primary text-white">
                        <i class="fab fa-ethereum me-2"></i>ब्लॉकचेन वेरिफिकेशन
                        ${blockchain.verified ? '<span class="badge bg-success ms-2">✓ Verified</span>' : ''}
                    </div>
                    <div class="card-body">
                        <div class="mb-2">
                            <small class="text-muted">Transaction Hash:</small>
                            <code class="d-block text-truncate small">${blockchain.transaction_hash}</code>
                        </div>
                        <div class="mb-2">
                            <small class="text-muted">Block #${blockchain.block_number}</small>
                        </div>
                        <div class="mb-2">
                            <small class="text-muted">Network: ${blockchain.network}</small>
                        </div>
                        <div class="alert alert-success p-2 small mt-2 mb-0">
                            <i class="fas fa-lock me-1"></i>डेटा अपरिवर्तनीय रूप से संग्रहीत है
                        </div>
                    </div>
                </div>
                <div class="card border-warning mt-3">
                    <div class="card-header bg-warning text-dark">
                        <i class="fas fa-seedling me-2"></i>AI सुझाव
                    </div>
                    <div class="card-body p-2">
                        <ul class="list-unstyled mb-0">
                            ${recs.map(r => `<li class="small py-1 border-bottom">${r}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        </div>`;
    } catch (err) {
        container.innerHTML = `<div class="alert alert-warning">IoT डेटा लोड नहीं हो सका: ${err.message}</div>`;
    }
}

// Auto-load when IoT tab is shown
document.addEventListener('DOMContentLoaded', () => {
    const iotTab = document.querySelector('[data-bs-target="#iot-section"], [href="#iot-section"]');
    if (iotTab) {
        iotTab.addEventListener('shown.bs.tab', loadIoTData);
    }
});
