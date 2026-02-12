from flask import Flask
from src.routes.student_routes import student_bp
from src.routes.academic_routes import academic_bp
from src.routes.grading_routes import grading_bp
from src.routes.reports_routes import reports_bp

app = Flask(__name__)

# Registros
app.register_blueprint(student_bp, url_prefix='/api/v1/estudiantes')
app.register_blueprint(academic_bp, url_prefix='/api/v1/academic')
app.register_blueprint(grading_bp, url_prefix='/api/v1/calificaciones')
app.register_blueprint(reports_bp, url_prefix='/api/v1/reportes')

if __name__ == '__main__':
    print("Sistema EduGrade Iniciado en puerto 5000")
    app.run(host='0.0.0.0', port=5000, debug=True)