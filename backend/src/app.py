from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
import secrets
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Configurar CORS
CORS(app, origins=[
    'http://localhost:3000',
    'https://*.railway.app',
    os.environ.get('FRONTEND_URL', 'http://localhost:3000')
])

# Configurar aplicação
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(16)

# Configurar banco de dados
if os.environ.get('DATABASE_URL'):
    # Railway PostgreSQL
    database_url = os.environ.get('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Desenvolvimento local
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expresso_itaporanga.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelos do banco de dados
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    perfil = db.Column(db.String(20), default='operador')
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

class Entrega(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo_rastreamento = db.Column(db.String(20), unique=True, nullable=False)
    
    # Dados do remetente
    remetente_nome = db.Column(db.String(100), nullable=False)
    remetente_endereco = db.Column(db.Text, nullable=False)
    remetente_cidade = db.Column(db.String(100), nullable=False)
    
    # Dados do destinatário
    destinatario_nome = db.Column(db.String(100), nullable=False)
    destinatario_endereco = db.Column(db.Text, nullable=False)
    destinatario_cidade = db.Column(db.String(100), nullable=False)
    
    # Dados da mercadoria
    tipo_produto = db.Column(db.String(50), nullable=False)
    peso = db.Column(db.Float)
    valor_declarado = db.Column(db.Float)
    observacoes = db.Column(db.Text)
    
    # Status e controle
    status = db.Column(db.String(20), default='pendente')
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))

# Rotas do site institucional
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

@app.route('/servicos')
def servicos():
    return render_template('servicos.html')

@app.route('/contato')
def contato():
    return render_template('contato.html')

@app.route('/contato', methods=['POST'])
def processar_contato():
    try:
        # Coletar dados do formulário
        nome = request.form.get('nome')
        email = request.form.get('email')
        telefone = request.form.get('telefone', '')
        assunto = request.form.get('assunto')
        mensagem = request.form.get('mensagem')
        
        # Criar email
        email_corpo = f"""
        Nova mensagem recebida através do site da Expresso Itaporanga:
        
        Nome: {nome}
        Email: {email}
        Telefone: {telefone}
        Assunto: {assunto}
        
        Mensagem:
        {mensagem}
        
        ---
        Mensagem enviada automaticamente pelo site da Expresso Itaporanga
        """
        
        # Simular envio de email (em produção, configurar SMTP real)
        print("=" * 50)
        print("NOVO EMAIL RECEBIDO")
        print("=" * 50)
        print(f"Para: comercial@expressoitaporanga.com.br")
        print(f"Assunto: Nova mensagem do site - {assunto}")
        print(email_corpo)
        print("=" * 50)
        
        # Retornar sucesso
        return jsonify({
            'success': True, 
            'message': 'Mensagem enviada com sucesso! Entraremos em contato em breve.'
        })
        
    except Exception as e:
        print(f"Erro ao processar contato: {e}")
        return jsonify({
            'success': False, 
            'message': 'Erro ao enviar mensagem. Tente novamente.'
        }), 500

# Rotas do sistema de gestão
@app.route('/gestao')
def gestao_login():
    return render_template('gestao/login.html')

@app.route('/gestao/login', methods=['POST'])
def login():
    try:
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        username = sanitize_input(request.form.get('username'))
        password = request.form.get('password')
        
        # Validar entrada
        is_valid, error_msg = validate_login_input(username, password)
        if not is_valid:
            record_login_attempt(ip_address)
            flash(error_msg, 'error')
            return redirect(url_for('gestao_login'))
        
        usuario = Usuario.query.filter_by(username=username, ativo=True).first()
        
        if usuario and check_password_hash(usuario.password_hash, password):
            session['user_id'] = usuario.id
            session['username'] = usuario.username
            session['perfil'] = usuario.perfil
            session['login_time'] = datetime.now().isoformat()
            session.permanent = True
            
            # Log de login bem-sucedido
            app.logger.info(f"Login bem-sucedido para usuário: {username} de IP: {ip_address}")
            
            return redirect(url_for('dashboard'))
        else:
            # Registrar tentativa falhada
            record_login_attempt(ip_address)
            app.logger.warning(f"Tentativa de login falhada para usuário: {username} de IP: {ip_address}")
            
            flash('Usuário ou senha inválidos', 'error')
            return redirect(url_for('gestao_login'))
    except Exception as e:
        app.logger.error(f"Erro no login: {e}")
        flash('Erro interno do servidor', 'error')
        return redirect(url_for('gestao_login'))

@app.route('/gestao/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/gestao/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('gestao_login'))
    
    # Estatísticas
    total_entregas = Entrega.query.count()
    pendentes = Entrega.query.filter_by(status='pendente').count()
    em_transito = Entrega.query.filter_by(status='em_transito').count()
    entregues = Entrega.query.filter_by(status='entregue').count()
    
    stats = {
        'total': total_entregas,
        'pendentes': pendentes,
        'em_transito': em_transito,
        'entregues': entregues
    }
    
    return render_template('gestao/dashboard.html', stats=stats)

@app.route('/gestao/entregas')
def listar_entregas():
    if 'user_id' not in session:
        return redirect(url_for('gestao_login'))
    
    entregas = Entrega.query.order_by(Entrega.data_criacao.desc()).all()
    return render_template('gestao/entregas.html', entregas=entregas)

@app.route('/gestao/nova-entrega')
def nova_entrega():
    if 'user_id' not in session:
        return redirect(url_for('gestao_login'))
    
    return render_template('gestao/nova_entrega.html')

@app.route('/gestao/criar-entrega', methods=['POST'])
def criar_entrega():
    if 'user_id' not in session:
        return redirect(url_for('gestao_login'))
    
    # Gerar código de rastreamento
    import random
    import string
    codigo = 'EI' + ''.join(random.choices(string.digits, k=8))
    
    entrega = Entrega(
        codigo_rastreamento=codigo,
        remetente_nome=request.form['remetente_nome'],
        remetente_endereco=request.form['remetente_endereco'],
        remetente_cidade=request.form['remetente_cidade'],
        destinatario_nome=request.form['destinatario_nome'],
        destinatario_endereco=request.form['destinatario_endereco'],
        destinatario_cidade=request.form['destinatario_cidade'],
        tipo_produto=request.form['tipo_produto'],
        peso=float(request.form['peso']) if request.form['peso'] else None,
        valor_declarado=float(request.form['valor_declarado']) if request.form['valor_declarado'] else None,
        observacoes=request.form.get('observacoes', ''),
        usuario_id=session['user_id']
    )
    
    db.session.add(entrega)
    db.session.commit()
    
    flash(f'Entrega criada com sucesso! Código: {codigo}', 'success')
    return redirect(url_for('listar_entregas'))

@app.route('/gestao/relatorios')
def relatorios():
    if 'user_id' not in session:
        return redirect(url_for('gestao_login'))
    
    # Dados para relatórios
    total_entregas = Entrega.query.count()
    pendentes = Entrega.query.filter_by(status='pendente').count()
    em_transito = Entrega.query.filter_by(status='em_transito').count()
    entregues = Entrega.query.filter_by(status='entregue').count()
    devolvidas = Entrega.query.filter_by(status='devolvida').count()
    
    # Taxa de sucesso
    taxa_sucesso = (entregues / total_entregas * 100) if total_entregas > 0 else 0
    
    dados = {
        'total': total_entregas,
        'pendentes': pendentes,
        'em_transito': em_transito,
        'entregues': entregues,
        'devolvidas': devolvidas,
        'taxa_sucesso': round(taxa_sucesso, 1)
    }
    
    return render_template('gestao/relatorios.html', dados=dados)

@app.route('/rastreamento')
def rastreamento():
    return render_template('rastreamento.html')

@app.route('/api/rastrear/<codigo>')
def api_rastrear(codigo):
    entrega = Entrega.query.filter_by(codigo_rastreamento=codigo).first()
    if entrega:
        return jsonify({
            'encontrado': True,
            'codigo': entrega.codigo_rastreamento,
            'status': entrega.status,
            'destinatario': entrega.destinatario_nome,
            'cidade_destino': entrega.destinatario_cidade,
            'data_criacao': entrega.data_criacao.strftime('%d/%m/%Y %H:%M')
        })
    else:
        return jsonify({'encontrado': False})

def init_db():
    """Inicializar banco de dados"""
    try:
        db.create_all()
        
        # Criar usuário admin se não existir
        admin = Usuario.query.filter_by(username='admin').first()
        if not admin:
            admin = Usuario(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                perfil='admin',
                ativo=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Usuário admin criado com sucesso!")
        else:
            print("Usuário admin já existe")
    except Exception as e:
        print(f"Erro ao inicializar banco: {e}")

# Inicializar banco sempre que a aplicação for carregada
with app.app_context():
    init_db()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


# ============================================================================
# API REST ENDPOINTS
# ============================================================================

from flask import jsonify

# API: Listar todas as entregas
@app.route('/api/entregas', methods=['GET'])
def api_entregas():
    try:
        entregas = Entrega.query.all()
        entregas_list = []
        
        for entrega in entregas:
            entregas_list.append({
                'id': entrega.id,
                'codigo_rastreamento': entrega.codigo_rastreamento,
                'remetente_nome': entrega.remetente_nome,
                'remetente_cidade': entrega.remetente_cidade,
                'destinatario_nome': entrega.destinatario_nome,
                'destinatario_cidade': entrega.destinatario_cidade,
                'tipo_produto': entrega.tipo_produto,
                'peso': entrega.peso,
                'valor_declarado': entrega.valor_declarado,
                'status': entrega.status,
                'data_criacao': entrega.data_criacao.isoformat() if entrega.data_criacao else None,
                'data_atualizacao': entrega.data_atualizacao.isoformat() if entrega.data_atualizacao else None
            })
        
        return jsonify({
            'success': True,
            'data': entregas_list,
            'total': len(entregas_list)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API: Buscar entrega por código de rastreamento
@app.route('/api/entregas/<codigo_rastreamento>', methods=['GET'])
def api_entrega_por_codigo(codigo_rastreamento):
    try:
        entrega = Entrega.query.filter_by(codigo_rastreamento=codigo_rastreamento).first()
        
        if not entrega:
            return jsonify({
                'success': False,
                'error': 'Entrega não encontrada'
            }), 404
        
        entrega_data = {
            'id': entrega.id,
            'codigo_rastreamento': entrega.codigo_rastreamento,
            'remetente_nome': entrega.remetente_nome,
            'remetente_endereco': entrega.remetente_endereco,
            'remetente_cidade': entrega.remetente_cidade,
            'destinatario_nome': entrega.destinatario_nome,
            'destinatario_endereco': entrega.destinatario_endereco,
            'destinatario_cidade': entrega.destinatario_cidade,
            'tipo_produto': entrega.tipo_produto,
            'peso': entrega.peso,
            'valor_declarado': entrega.valor_declarado,
            'observacoes': entrega.observacoes,
            'status': entrega.status,
            'data_criacao': entrega.data_criacao.isoformat() if entrega.data_criacao else None,
            'data_atualizacao': entrega.data_atualizacao.isoformat() if entrega.data_atualizacao else None
        }
        
        return jsonify({
            'success': True,
            'data': entrega_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API: Criar nova entrega
@app.route('/api/entregas', methods=['POST'])
def api_criar_entrega():
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        required_fields = ['remetente_nome', 'remetente_endereco', 'remetente_cidade',
                          'destinatario_nome', 'destinatario_endereco', 'destinatario_cidade',
                          'tipo_produto']
        
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório: {field}'
                }), 400
        
        # Gerar código de rastreamento único
        import random
        import string
        codigo = 'EI' + ''.join(random.choices(string.digits, k=10))
        
        # Verificar se código já existe
        while Entrega.query.filter_by(codigo_rastreamento=codigo).first():
            codigo = 'EI' + ''.join(random.choices(string.digits, k=10))
        
        # Criar nova entrega
        nova_entrega = Entrega(
            codigo_rastreamento=codigo,
            remetente_nome=data['remetente_nome'],
            remetente_endereco=data['remetente_endereco'],
            remetente_cidade=data['remetente_cidade'],
            destinatario_nome=data['destinatario_nome'],
            destinatario_endereco=data['destinatario_endereco'],
            destinatario_cidade=data['destinatario_cidade'],
            tipo_produto=data['tipo_produto'],
            peso=data.get('peso'),
            valor_declarado=data.get('valor_declarado'),
            observacoes=data.get('observacoes', ''),
            status='pendente'
        )
        
        db.session.add(nova_entrega)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'id': nova_entrega.id,
                'codigo_rastreamento': nova_entrega.codigo_rastreamento,
                'status': nova_entrega.status
            },
            'message': 'Entrega criada com sucesso'
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API: Atualizar status da entrega
@app.route('/api/entregas/<codigo_rastreamento>/status', methods=['PUT'])
def api_atualizar_status(codigo_rastreamento):
    try:
        data = request.get_json()
        novo_status = data.get('status')
        
        if not novo_status:
            return jsonify({
                'success': False,
                'error': 'Status é obrigatório'
            }), 400
        
        # Validar status
        status_validos = ['pendente', 'coletado', 'em_transito', 'entregue', 'cancelado']
        if novo_status not in status_validos:
            return jsonify({
                'success': False,
                'error': f'Status inválido. Valores aceitos: {", ".join(status_validos)}'
            }), 400
        
        entrega = Entrega.query.filter_by(codigo_rastreamento=codigo_rastreamento).first()
        
        if not entrega:
            return jsonify({
                'success': False,
                'error': 'Entrega não encontrada'
            }), 404
        
        entrega.status = novo_status
        entrega.data_atualizacao = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'codigo_rastreamento': entrega.codigo_rastreamento,
                'status': entrega.status,
                'data_atualizacao': entrega.data_atualizacao.isoformat()
            },
            'message': 'Status atualizado com sucesso'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API: Estatísticas gerais
@app.route('/api/estatisticas', methods=['GET'])
def api_estatisticas():
    try:
        total_entregas = Entrega.query.count()
        entregas_pendentes = Entrega.query.filter_by(status='pendente').count()
        entregas_em_transito = Entrega.query.filter_by(status='em_transito').count()
        entregas_entregues = Entrega.query.filter_by(status='entregue').count()
        entregas_canceladas = Entrega.query.filter_by(status='cancelado').count()
        
        # Calcular taxa de sucesso
        if total_entregas > 0:
            taxa_sucesso = round((entregas_entregues / total_entregas) * 100, 2)
        else:
            taxa_sucesso = 0
        
        # Entregas por cidade (top 5)
        from sqlalchemy import func
        cidades_destino = db.session.query(
            Entrega.destinatario_cidade,
            func.count(Entrega.id).label('total')
        ).group_by(Entrega.destinatario_cidade).order_by(func.count(Entrega.id).desc()).limit(5).all()
        
        estatisticas = {
            'total_entregas': total_entregas,
            'entregas_por_status': {
                'pendente': entregas_pendentes,
                'em_transito': entregas_em_transito,
                'entregue': entregas_entregues,
                'cancelado': entregas_canceladas
            },
            'taxa_sucesso': taxa_sucesso,
            'top_cidades_destino': [
                {'cidade': cidade[0], 'total': cidade[1]} 
                for cidade in cidades_destino
            ]
        }
        
        return jsonify({
            'success': True,
            'data': estatisticas
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# API: Processar formulário de contato via AJAX
@app.route('/api/contato', methods=['POST'])
def api_processar_contato():
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        required_fields = ['nome', 'email', 'assunto', 'mensagem']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo obrigatório: {field}'
                }), 400
        
        # Simular processamento do email
        # Em produção, aqui seria implementado o envio real do email
        
        return jsonify({
            'success': True,
            'message': 'Mensagem enviada com sucesso! Entraremos em contato em breve.'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor'
        }), 500

# API: Documentação da API
@app.route('/api/docs', methods=['GET'])
def api_documentacao():
    docs = {
        'title': 'API Expresso Itaporanga',
        'version': '1.0.0',
        'description': 'API REST para gestão de entregas e rastreamento logístico',
        'endpoints': {
            'GET /api/entregas': 'Listar todas as entregas',
            'GET /api/entregas/<codigo>': 'Buscar entrega por código de rastreamento',
            'POST /api/entregas': 'Criar nova entrega',
            'PUT /api/entregas/<codigo>/status': 'Atualizar status da entrega',
            'GET /api/estatisticas': 'Obter estatísticas gerais',
            'POST /api/contato': 'Processar formulário de contato',
            'GET /api/docs': 'Esta documentação'
        },
        'status_validos': ['pendente', 'coletado', 'em_transito', 'entregue', 'cancelado'],
        'exemplo_entrega': {
            'remetente_nome': 'João Silva',
            'remetente_endereco': 'Rua A, 123',
            'remetente_cidade': 'São Paulo/SP',
            'destinatario_nome': 'Maria Santos',
            'destinatario_endereco': 'Rua B, 456',
            'destinatario_cidade': 'Itaporanga/PB',
            'tipo_produto': 'Documentos',
            'peso': 0.5,
            'valor_declarado': 100.00,
            'observacoes': 'Entrega urgente'
        }
    }
    
    return jsonify(docs)

# Rota para análise de dados
@app.route('/gestao/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('gestao_login'))
    return render_template('gestao/analytics.html')


# ============================================================================
# MELHORIAS DE SEGURANÇA
# ============================================================================

# Configurações de segurança
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS apenas
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Previne XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Previne CSRF
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # Timeout de sessão

# Headers de segurança
@app.after_request
def add_security_headers(response):
    # Previne clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Previne MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Força HTTPS
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Previne XSS
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'"
    )
    
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response

# Rate limiting básico (em memória)
from collections import defaultdict

login_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

def is_rate_limited(ip_address):
    """Verifica se o IP está bloqueado por muitas tentativas de login"""
    now = datetime.now()
    attempts = login_attempts[ip_address]
    
    # Remove tentativas antigas
    attempts[:] = [attempt for attempt in attempts if now - attempt < LOCKOUT_DURATION]
    
    return len(attempts) >= MAX_LOGIN_ATTEMPTS

def record_login_attempt(ip_address):
    """Registra uma tentativa de login"""
    login_attempts[ip_address].append(datetime.now())

# Middleware de segurança para rotas de gestão
@app.before_request
def security_middleware():
    # Rate limiting para login
    if request.endpoint == 'login' and request.method == 'POST':
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if is_rate_limited(ip_address):
            flash('Muitas tentativas de login. Tente novamente em 15 minutos.', 'error')
            return redirect(url_for('gestao_login'))
    
    # Verificar sessão para rotas protegidas
    protected_routes = ['dashboard', 'listar_entregas', 'nova_entrega', 'relatorios', 'analytics']
    if request.endpoint in protected_routes:
        if 'user_id' not in session:
            return redirect(url_for('gestao_login'))
        
        # Verificar se a sessão não expirou
        if 'login_time' in session:
            login_time = datetime.fromisoformat(session['login_time'])
            if datetime.now() - login_time > timedelta(hours=2):
                session.clear()
                flash('Sessão expirada. Faça login novamente.', 'info')
                return redirect(url_for('gestao_login'))

# Função para sanitizar entrada do usuário
import html
import re

def sanitize_input(text):
    """Sanitiza entrada do usuário para prevenir XSS"""
    if not text:
        return text
    
    # Remove tags HTML
    text = html.escape(text)
    
    # Remove caracteres perigosos
    text = re.sub(r'[<>"\']', '', text)
    
    return text.strip()

# Validação de entrada mais rigorosa
def validate_login_input(username, password):
    """Valida entrada de login"""
    if not username or not password:
        return False, "Usuário e senha são obrigatórios"
    
    if len(username) > 50 or len(password) > 100:
        return False, "Credenciais inválidas"
    
    # Verifica caracteres permitidos
    if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
        return False, "Usuário contém caracteres inválidos"
    
    return True, ""

# ============================================================================
# FIM DAS MELHORIAS DE SEGURANÇA
# ============================================================================
