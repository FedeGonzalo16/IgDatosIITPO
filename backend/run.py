from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from src.routes.student_routes import student_bp
from src.routes.academic_routes import academic_bp
from src.routes.grading_routes import grading_bp
from src.routes.reports_routes import reports_bp
from src.routes.professor_routes import professor_bp
from src.routes.trajectory_routes import trajectory_bp

app = Flask(__name__)
# Evitar redirecciones por trailing slash (causan "Redirect not allowed for preflight" en CORS)
app.url_map.strict_slashes = False
# CORS explícito: preflight OPTIONS debe recibir 200 con headers, no redirect
CORS(
    app,
    origins=["http://localhost:3000"],
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    supports_credentials=True,
)

# Registros
app.register_blueprint(student_bp, url_prefix='/api/v1/estudiantes')
app.register_blueprint(academic_bp, url_prefix='/api/v1/academic')
app.register_blueprint(grading_bp, url_prefix='/api/v1/calificaciones')
app.register_blueprint(reports_bp, url_prefix='/api/v1/reportes')
app.register_blueprint(professor_bp, url_prefix='/api/v1/profesores')
app.register_blueprint(trajectory_bp, url_prefix='/api/v1/trayectoria')

# Swagger / OpenAPI documentation - disponible en http://localhost:5000/apidocs
from src.swagger_template import SWAGGER_TEMPLATE
Swagger(app, template=SWAGGER_TEMPLATE)

if __name__ == '__main__':
    print("Sistema EduGrade Iniciado en puerto 5000")
    print("Documentación Swagger: http://localhost:5000/apidocs")
    app.run(host='0.0.0.0', port=5000, debug=True)