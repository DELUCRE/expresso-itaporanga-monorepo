/**
 * Configuração da API do Expresso Itaporanga
 */

// URL base da API (será definida via variável de ambiente)
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:5000' 
    : 'https://expresso-backend-production.railway.app'; // Substitua pela URL real do backend

/**
 * Configuração padrão para requisições
 */
const API_CONFIG = {
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
};

/**
 * Função para fazer requisições à API
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
        ...API_CONFIG,
        ...options,
        headers: {
            ...API_CONFIG.headers,
            ...options.headers
        }
    };

    try {
        const response = await fetch(url, config);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        } else {
            return await response.text();
        }
    } catch (error) {
        console.error('Erro na requisição à API:', error);
        throw error;
    }
}

/**
 * Funções específicas da API
 */

// Rastreamento de entregas
async function rastrearEntrega(codigo) {
    try {
        const data = await apiRequest(`/api/rastrear/${codigo}`);
        return data;
    } catch (error) {
        return { 
            encontrado: false, 
            erro: 'Erro ao consultar rastreamento. Tente novamente.' 
        };
    }
}

// Enviar formulário de contato
async function enviarContato(formData) {
    try {
        const data = await apiRequest('/contato', {
            method: 'POST',
            body: formData
        });
        return data;
    } catch (error) {
        return { 
            success: false, 
            message: 'Erro ao enviar mensagem. Tente novamente.' 
        };
    }
}

// Obter estatísticas (para dashboard público, se necessário)
async function obterEstatisticas() {
    try {
        const data = await apiRequest('/api/estatisticas');
        return data;
    } catch (error) {
        return { 
            success: false, 
            data: null 
        };
    }
}

/**
 * Funções utilitárias
 */

// Mostrar mensagem de erro
function mostrarErro(mensagem) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-error';
    alertDiv.textContent = mensagem;
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
        z-index: 9999;
        max-width: 300px;
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Mostrar mensagem de sucesso
function mostrarSucesso(mensagem) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success';
    alertDiv.textContent = mensagem;
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
        z-index: 9999;
        max-width: 300px;
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

/**
 * Inicialização quando o DOM estiver carregado
 */
document.addEventListener('DOMContentLoaded', function() {
    // Configurar formulário de rastreamento
    const formRastreamento = document.querySelector('#form-rastreamento');
    if (formRastreamento) {
        formRastreamento.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const codigo = document.querySelector('#codigo-rastreamento').value.trim();
            if (!codigo) {
                mostrarErro('Por favor, digite o código de rastreamento.');
                return;
            }
            
            const resultado = await rastrearEntrega(codigo);
            
            const resultadoDiv = document.querySelector('#resultado-rastreamento');
            if (resultadoDiv) {
                if (resultado.encontrado) {
                    resultadoDiv.innerHTML = `
                        <div class="rastreamento-sucesso">
                            <h3>Entrega Encontrada!</h3>
                            <p><strong>Código:</strong> ${resultado.codigo}</p>
                            <p><strong>Status:</strong> ${resultado.status}</p>
                            <p><strong>Destinatário:</strong> ${resultado.destinatario}</p>
                            <p><strong>Cidade:</strong> ${resultado.cidade_destino}</p>
                            <p><strong>Data:</strong> ${resultado.data_criacao}</p>
                        </div>
                    `;
                } else {
                    resultadoDiv.innerHTML = `
                        <div class="rastreamento-erro">
                            <h3>Entrega não encontrada</h3>
                            <p>Verifique o código e tente novamente.</p>
                        </div>
                    `;
                }
            }
        });
    }
    
    // Configurar formulário de contato
    const formContato = document.querySelector('#contact-form');
    if (formContato) {
        formContato.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(formContato);
            const resultado = await enviarContato(formData);
            
            if (resultado.success) {
                mostrarSucesso(resultado.message);
                formContato.reset();
            } else {
                mostrarErro(resultado.message);
            }
        });
    }
});
