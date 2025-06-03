// ML Training
async function trainMLModel() {
    const token = localStorage.getItem('token');
    if (!token) {
        alert('❌ Önce giriş yapın!');
        return;
    }
    
    const resultsDiv = document.getElementById('ml-results');
    resultsDiv.innerHTML = '🤖 ML Model eğitiliyor... (30-60 saniye sürebilir)';
    
    try {
        const response = await fetch('http://localhost:8000/ml/train', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            resultsDiv.innerHTML = `
                <h4>✅ ML Model Eğitildi!</h4>
                <p>📊 Matrix: ${data.ml_status?.matrix_shape}</p>
                <p>🎬 Model Hazır: ${data.ml_status?.ml_ready ? 'Evet' : 'Hayır'}</p>
            `;
        } else {
            resultsDiv.innerHTML = `❌ Hata: ${data.message}`;
        }
    } catch (error) {
        resultsDiv.innerHTML = `❌ Network hatası: ${error}`;
    }
}

// ML Önerileri
async function getMLRecommendations() {
    const token = localStorage.getItem('token');
    if (!token) {
        alert('❌ Önce giriş yapın!');
        return;
    }
    
    const resultsDiv = document.getElementById('ml-results');
    resultsDiv.innerHTML = '🎯 ML önerileri getiriliyor...';
    
    try {
        const response = await fetch('http://localhost:8000/ml/recommendations?n_recommendations=10', {
            headers: {'Authorization': `Bearer ${token}`}
        });
        
        const data = await response.json();
        
        if (data.status === 'success' && data.recommendations) {
            let html = '<h4>🤖 ML Önerileri:</h4><div class="recommendations-grid">';
            
            data.recommendations.slice(0, 8).forEach((movie, i) => {
                html += `
                    <div style="border: 1px solid #ddd; margin: 5px; padding: 10px; border-radius: 5px;">
                        <h5>${movie.title}</h5>
                        <p>🎯 Tahmin: ${movie.predicted_rating?.toFixed(2)}/5.0</p>
                        <p>📅 ${movie.release_date}</p>
                        <p>🎭 ${movie.genres?.join(', ')}</p>
                    </div>
                `;
            });
            
            html += '</div>';
            resultsDiv.innerHTML = html;
        } else {
            resultsDiv.innerHTML = `❌ ${data.message || 'ML önerileri alınamadı'}`;
        }
    } catch (error) {
        resultsDiv.innerHTML = `❌ Network hatası: ${error}`;
    }
}

// ML Status
async function checkMLStatus() {
    const resultsDiv = document.getElementById('ml-results');
    resultsDiv.innerHTML = '📊 ML durumu kontrol ediliyor...';
    
    try {
        const response = await fetch('http://localhost:8000/ml/status');
        const data = await response.json();
        
        resultsDiv.innerHTML = `
            <h4>📊 ML Sistem Durumu:</h4>
            <p>🤖 Model Hazır: ${data.ml_system?.ml_ready ? 'Evet ✅' : 'Hayır ❌'}</p>
            <p>🎓 Model Eğitildi: ${data.ml_system?.model_trained ? 'Evet ✅' : 'Hayır ❌'}</p>
            <p>📊 Matrix: ${data.ml_system?.matrix_shape || 'Yok'}</p>
        `;
    } catch (error) {
        resultsDiv.innerHTML = `❌ Network hatası: ${error}`;
    }
}