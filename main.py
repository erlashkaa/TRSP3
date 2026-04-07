import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.security import HTTPBasicCredentials
from fastapi.responses import JSONResponse, HTMLResponse
from dotenv import load_dotenv
import secrets

from database import get_db_connection
from models import User, TodoCreate, TodoUpdate, LoginRequest, Token
from auth import (
    get_password_hash, verify_password, create_access_token, 
    get_current_user_basic, get_current_user_jwt, authenticate_user_basic,
    fake_users_db, UserInDB, compare_strings, security_basic
)
from rbac import (
    Role, get_user_role, require_permission, require_role,
    register_user_with_role, user_roles
)
from todos import router as todos_router
from rate_limiter import rate_limit

load_dotenv()

# Configuration
MODE = os.getenv("MODE", "DEV")
DOCS_USER = os.getenv("DOCS_USER", "admin")
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD", "secret123")

# Create FastAPI app with conditional docs (Задание 6.3)
if MODE == "PROD":
    app = FastAPI(
        title="My API",
        docs_url=None,      # Disable /docs
        redoc_url=None,     # Disable /redoc
        openapi_url=None    # Disable /openapi.json
    )
else:
    app = FastAPI(
        title="My API",
        docs_url=None,      # Disable default docs (we'll use custom)
        redoc_url=None,     # Hide /redoc
        openapi_url="/openapi.json"
    )

# Include routers
app.include_router(todos_router)

# ============ Зелено-белая тема для документации ============

# Зелено-белая тема для всех кнопок
GREEN_WHITE_THEME_CSS = """
<style>
    /* Общие стили страницы */
    body {
        background: #f5f5f5 !important;
    }
    
    /* Основной контент */
    .swagger-ui {
        background: white !important;
    }
    
    /* Заголовки */
    .swagger-ui .info .title {
        color: #2E7D32 !important;
        font-weight: bold !important;
    }
    
    .swagger-ui .info .title small {
        background: #4CAF50 !important;
        color: white !important;
    }
    
    /* Секции с эндпоинтами */
    .swagger-ui .opblock-tag {
        background: #E8F5E9 !important;
        color: #1B5E20 !important;
        border-left: 4px solid #4CAF50 !important;
        font-weight: bold !important;
    }
    
    .swagger-ui .opblock-tag:hover {
        background: #C8E6C9 !important;
    }
    
    /* GET запросы */
    .swagger-ui .opblock.opblock-get {
        background: #F1F8E9 !important;
        border-color: #4CAF50 !important;
    }
    
    .swagger-ui .opblock.opblock-get .opblock-summary-method {
        background: #4CAF50 !important;
        color: white !important;
    }
    
    /* POST запросы */
    .swagger-ui .opblock.opblock-post {
        background: #E8F5E9 !important;
        border-color: #66BB6A !important;
    }
    
    .swagger-ui .opblock.opblock-post .opblock-summary-method {
        background: #66BB6A !important;
        color: white !important;
    }
    
    /* PUT запросы */
    .swagger-ui .opblock.opblock-put {
        background: #F1F8E9 !important;
        border-color: #81C784 !important;
    }
    
    .swagger-ui .opblock.opblock-put .opblock-summary-method {
        background: #81C784 !important;
        color: white !important;
    }
    
    /* DELETE запросы */
    .swagger-ui .opblock.opblock-delete {
        background: #FFF3E0 !important;
        border-color: #EF5350 !important;
    }
    
    .swagger-ui .opblock.opblock-delete .opblock-summary-method {
        background: #EF5350 !important;
        color: white !important;
    }
    
    /* ВСЕ КНОПКИ - зеленые */
    .btn,
    button,
    .execute-wrapper .btn,
    .try-out__btn,
    .cancel,
    .auth-btn-wrapper .btn,
    .btn-group button,
    .modal-btn,
    button[type="submit"],
    a.btn,
    .download-url-button,
    .download-btn,
    .authorize__btn,
    .btn-modal,
    .btn-clear,
    .btn-cancel,
    .btn-execute,
    .operation-sheet button,
    .info .btn,
    .btn-primary,
    .btn-danger,
    .btn-warning,
    .btn-info,
    .btn-success,
    .btn-default,
    .submit {
        background: #4CAF50 !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        padding: 8px 16px !important;
        box-shadow: 0 2px 4px rgba(76, 175, 80, 0.3) !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
    }
    
    /* Эффект при наведении на кнопки */
    .btn:hover,
    button:hover,
    .execute-wrapper .btn:hover,
    .try-out__btn:hover,
    .auth-btn-wrapper .btn:hover,
    .btn-group button:hover,
    button[type="submit"]:hover,
    a.btn:hover {
        background: #388E3C !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4) !important;
    }
    
    /* Эффект при нажатии */
    .btn:active,
    button:active {
        transform: translateY(0px) !important;
    }
    
    /* Кнопка Execute */
    .execute-wrapper .btn {
        background: #2E7D32 !important;
        font-weight: bold !important;
    }
    
    .execute-wrapper .btn:hover {
        background: #1B5E20 !important;
    }
    
    /* Кнопка Try it out */
    .try-out__btn {
        background: #66BB6A !important;
    }
    
    .try-out__btn:hover {
        background: #4CAF50 !important;
    }
    
    /* Кнопка Cancel */
    .cancel {
        background: #9E9E9E !important;
    }
    
    .cancel:hover {
        background: #757575 !important;
    }
    
    /* Кнопка Authorize */
    .auth-btn-wrapper .btn {
        background: #43A047 !important;
    }
    
    .auth-btn-wrapper .btn:hover {
        background: #2E7D32 !important;
    }
    
    /* Запрещаем изменение стилей для отключенных кнопок */
    .btn:disabled,
    button:disabled {
        opacity: 0.5 !important;
        cursor: not-allowed !important;
        transform: none !important;
    }
    
    /* Убираем стандартные рамки */
    button:focus,
    .btn:focus {
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.5) !important;
    }
    
    /* Табы и вкладки */
    .swagger-ui .information-container .info .base-url {
        color: #2E7D32 !important;
    }
    
    /* Скроллбар зеленый */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #4CAF50;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #2E7D32;
    }
    
    /* Схемы ответов */
    .swagger-ui .responses-inner .response-col_status {
        color: #2E7D32 !important;
        font-weight: bold !important;
    }
    
    /* Код в ответах */
    .swagger-ui .highlight-code {
        background: #f5f5f5 !important;
        border-left: 3px solid #4CAF50 !important;
    }
    
    /* Формы ввода */
    .swagger-ui input,
    .swagger-ui textarea,
    .swagger-ui select {
        border-color: #C8E6C9 !important;
    }
    
    .swagger-ui input:focus,
    .swagger-ui textarea:focus,
    .swagger-ui select:focus {
        border-color: #4CAF50 !important;
        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2) !important;
    }
    
    /* Ссылки */
    a {
        color: #2E7D32 !important;
    }
    
    a:hover {
        color: #1B5E20 !important;
    }
    
    /* Бейджи */
    .swagger-ui .scheme-container .schemes .scheme-server {
        background: #E8F5E9 !important;
        color: #2E7D32 !important;
    }
    
    /* Модальные окна */
    .modal-dialog .modal-content {
        border-top: 4px solid #4CAF50 !important;
    }
    
    .modal-dialog .modal-header {
        background: #E8F5E9 !important;
        color: #2E7D32 !important;
    }
    
    /* Сообщения об ошибках */
    .swagger-ui .errors-wrapper {
        background: #FFF3E0 !important;
        border-left: 4px solid #EF5350 !important;
    }
    
    /* Успешные сообщения */
    .swagger-ui .success {
        color: #4CAF50 !important;
    }
</style>
"""

# Custom HTML template with Swagger UI and green-white theme
CUSTOM_DOCS_HTML = f"""
<!DOCTYPE html>
<html>
<head>
    <title>API Documentation - Green Theme</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <link rel="icon" type="image/png" href="https://fastapi.tiangolo.com/img/favicon.png">
    {GREEN_WHITE_THEME_CSS}
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                url: "/openapi.json",
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                deepLinking: true,
                displayOperationId: false,
                filter: true,
                tryItOutEnabled: true,
                persistAuthorization: true,
                defaultModelsExpandDepth: 1,
                defaultModelExpandDepth: 1,
                displayRequestDuration: true,
                docExpansion: "list",
                showExtensions: true,
                showCommonExtensions: true
            }});
            window.ui = ui;
        }};
    </script>
</body>
</html>
"""

# ============ Задание 6.3: Protected Documentation ============

def verify_docs_auth(credentials: HTTPBasicCredentials = Depends(security_basic)):
    """Verify credentials for documentation access (Задание 6.3)"""
    correct_username = compare_strings(credentials.username, DOCS_USER)
    correct_password = compare_strings(credentials.password, DOCS_PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Conditionally protect docs in DEV mode (Задание 6.3)
if MODE == "DEV":
    @app.get("/docs", include_in_schema=False)
    async def get_swagger_docs(username: str = Depends(verify_docs_auth)):
        """Protected Swagger UI endpoint with green-white theme"""
        return HTMLResponse(content=CUSTOM_DOCS_HTML)
    
    @app.get("/openapi.json", include_in_schema=False)
    async def get_openapi(username: str = Depends(verify_docs_auth)):
        """Protected OpenAPI schema endpoint"""
        return app.openapi()

# ============ Задание 6.2: Basic Auth with Password Hashing ============

@app.post("/register", status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=1, time_window_seconds=60, key_prefix="register")
async def register_user(user: User, request: Request):
    """
    Register a new user with hashed password (Задание 6.2, 6.5)
    """
    # Check if user already exists (in fake DB for 6.5 compatibility)
    if user.username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists"
        )
    
    # Also check SQLite DB (Задание 8.1)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username = ?", (user.username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists"
            )
    
    # Hash password
    hashed_password = get_password_hash(user.password)
    
    # Store in fake DB (for tasks 6.2-6.5)
    fake_users_db[user.username] = UserInDB(
        username=user.username,
        hashed_password=hashed_password
    )
    
    # Also store in SQLite (Задание 8.1)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (user.username, hashed_password)
        )
        conn.commit()
    
    # Assign default role for RBAC (Задание 7.1)
    if user.username not in user_roles:
        user_roles[user.username] = Role.USER
    
    return {"message": "New user created"}

@app.get("/login", status_code=status.HTTP_200_OK)
async def login_basic(user: UserInDB = Depends(get_current_user_basic)):
    """
    Basic auth login endpoint (Задание 6.2)
    """
    return {"message": f"Welcome, {user.username}!"}

# ============ Задание 6.4 & 6.5: JWT Authentication ============

@app.post("/login/jwt", response_model=Token)
@rate_limit(max_requests=5, time_window_seconds=60, key_prefix="login")
async def login_jwt(login_data: LoginRequest, request: Request):
    """
    JWT login endpoint (Задание 6.4, 6.5)
    """
    # Find user in fake DB first
    user = None
    if login_data.username in fake_users_db:
        user = fake_users_db[login_data.username]
        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization failed"
            )
    else:
        # Check SQLite DB
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, password FROM users WHERE username = ?", (login_data.username,))
            row = cursor.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            if not verify_password(login_data.password, row["password"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization failed"
                )
    
    # Create JWT token
    access_token = create_access_token(data={"sub": login_data.username})
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/protected_resource")
async def protected_resource(username: str = Depends(get_current_user_jwt)):
    """
    Protected endpoint requiring JWT (Задание 6.4, 6.5)
    """
    return {"message": f"Access granted for user: {username}"}

# ============ Задание 7.1: RBAC ============

# Seed admin user for testing
register_user_with_role("admin", "admin123", Role.ADMIN)
register_user_with_role("guest_user", "guest123", Role.GUEST)

@app.get("/rbac/admin-only")
async def admin_endpoint(username: str = Depends(require_role([Role.ADMIN]))):
    """
    Admin-only endpoint (Задание 7.1)
    """
    return {"message": f"Welcome admin {username}! You have full access."}

@app.get("/rbac/user-resource")
async def user_resource_endpoint(username: str = Depends(require_role([Role.ADMIN, Role.USER]))):
    """
    Resource accessible by admin and user roles (Задание 7.1)
    """
    return {"message": f"Hello {username}! You can read and update resources."}

@app.get("/rbac/guest-resource")
async def guest_endpoint(username: str = Depends(get_current_user_jwt)):
    """
    Guest accessible endpoint (read-only) (Задание 7.1)
    """
    user_role = get_user_role(username)
    return {
        "message": f"Welcome {username} (role: {user_role.value}). You have read-only access.",
        "resources": ["item1", "item2", "item3"]
    }

@app.post("/rbac/create-resource")
async def create_resource_endpoint(
    username: str = Depends(require_permission("create"))
):
    """
    Create resource - requires 'create' permission (admin only)
    """
    return {"message": f"Resource created by {username}"}

@app.put("/rbac/update-resource/{resource_id}")
async def update_resource_endpoint(
    resource_id: int,
    username: str = Depends(require_permission("update"))
):
    """
    Update resource - requires 'update' permission (admin or user)
    """
    return {"message": f"Resource {resource_id} updated by {username}"}

@app.delete("/rbac/delete-resource/{resource_id}")
async def delete_resource_endpoint(
    resource_id: int,
    username: str = Depends(require_permission("delete"))
):
    """
    Delete resource - requires 'delete' permission (admin only)
    """
    return {"message": f"Resource {resource_id} deleted by {username}"}

# ============ Задание 8.1: SQLite Users Table ============

@app.post("/register/sqlite", status_code=status.HTTP_201_CREATED)
async def register_user_sqlite(user: User):
    """
    Register user directly to SQLite (Задание 8.1)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT username FROM users WHERE username = ?", (user.username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists"
            )
        
        # Insert user (password stored in plain text as per Задание 8.1)
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (user.username, user.password)  # Plain text for task 8.1
        )
        conn.commit()
    
    return {"message": "User registered successfully!"}

# ============ Root endpoint ============

@app.get("/")
async def root():
    return {
        "message": "FastAPI Server Running",
        "mode": MODE,
        "endpoints": {
            "auth": ["/register", "/login", "/login/jwt", "/protected_resource"],
            "rbac": ["/rbac/admin-only", "/rbac/user-resource", "/rbac/guest-resource", 
                     "/rbac/create-resource", "/rbac/update-resource/{id}", "/rbac/delete-resource/{id}"],
            "todos": ["/todos (GET, POST)", "/todos/{id} (GET, PUT, DELETE)"],
            "docs": f"/docs (protected in DEV mode)" if MODE == "DEV" else "disabled in PROD"
        }
    }

# ============ Error handlers ============

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers if exc.headers else None
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)