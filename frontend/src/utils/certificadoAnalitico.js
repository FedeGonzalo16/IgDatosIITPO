/**
 * Lógica unificada para generar y descargar el certificado analítico.
 * Usado desde Mi Perfil (dashboard) y desde la página Perfil (/student/subjects).
 */

/**
 * Obtiene el certificado analítico del backend y descarga un archivo .txt.
 * @param {Object} reportService - Servicio API (reportService.getCertificadoAnalitico)
 * @param {string} studentId - ID del estudiante
 * @param {Object} user - Objeto usuario (para nombre de archivo: legajo)
 * @param {Function} setLoading - (opcional) setState para loading, se llama con true/false
 * @returns {Promise<boolean>} - true si se descargó, false si hubo error
 */
export async function descargarCertificadoAnalitico(reportService, studentId, user, setLoading) {
  if (!studentId) {
    alert('No se pudo identificar al estudiante.');
    return false;
  }
  if (setLoading) setLoading(true);
  try {
    const res = await reportService.getCertificadoAnalitico(studentId, {
      guardar_snapshot: true,
    });
    const data = res.data;
    if (data?.error) {
      alert(data.error);
      return false;
    }
    const lines = [
      'CERTIFICADO ANALÍTICO',
      '========================',
      '',
      `Estudiante: ${data.estudiante?.nombre ?? ''} ${data.estudiante?.apellido ?? ''}`,
      `Legajo: ${data.estudiante?.legajo ?? 'N/A'}`,
      `Email: ${data.estudiante?.email ?? 'N/A'}`,
      '',
      `Promedio histórico: ${data.promedio_historico ?? 'N/A'}`,
      `Avance carrera: ${data.porcentaje_avance != null ? data.porcentaje_avance + '%' : 'N/A'}`,
      `Materias aprobadas: ${data.cantidad_aprobadas ?? 0}`,
      '',
      '--- Materias aprobadas ---',
      ...(data.materias_aprobadas || []).map(m => `  ${m.nombre || m.codigo || ''} - Nota: ${m.nota_final ?? 'N/A'}`),
      '',
      `Emitido: ${new Date().toLocaleString('es-AR')}`,
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `certificado_analitico_${user?.legajo || studentId}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    return true;
  } catch (err) {
    console.error('Error descargando analítico:', err);
    alert('Error al generar el certificado: ' + (err.response?.data?.error || err.message));
    return false;
  } finally {
    if (setLoading) setLoading(false);
  }
}
