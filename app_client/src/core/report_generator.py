"""
Autonova RMM - Report Generator
Generates professional PDF/HTML reports with operation details and signatures.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional
import asyncio
import base64

# Logo SVG (embedded)
AUTONOVA_LOGO = '''
<svg width="60" height="60" viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="60" height="60" rx="12" fill="url(#gradient)"/>
  <defs>
    <linearGradient id="gradient" x1="0" y1="0" x2="60" y2="60" gradientUnits="userSpaceOnUse">
      <stop stop-color="#6366f1"/>
      <stop offset="1" stop-color="#10b981"/>
    </linearGradient>
  </defs>
  <path d="M30 12L45 25V45H15V25L30 12Z" fill="white" fill-opacity="0.9"/>
  <circle cx="30" cy="32" r="6" fill="#6366f1"/>
</svg>
'''


class ReportGenerator:
    """Generates professional service reports."""
    
    def __init__(self, progress_callback: Callable = None):
        self.progress_callback = progress_callback
        self.operations = []
        self.scan_results = {}
    
    async def log(self, message: str):
        """Send progress message."""
        if self.progress_callback:
            await self.progress_callback({
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "level": "info"
            })
    
    def add_operation(self, operation: Dict[str, Any]):
        """Add an operation to the report."""
        self.operations.append({
            **operation,
            "timestamp": datetime.now().isoformat()
        })
    
    def set_scan_results(self, results: Dict[str, Any]):
        """Set scan results for the report."""
        self.scan_results = results
    
    def generate_html(
        self,
        hostname: str,
        agent_id: str,
        technician: str = "Técnico Autonova",
        client_name: str = "Cliente"
    ) -> str:
        """Generate full HTML report."""
        
        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%H:%M:%S")
        
        # Calculate totals
        total_ops = len(self.operations)
        success_ops = sum(1 for op in self.operations if op.get('success', True))
        failed_ops = total_ops - success_ops
        
        # Get health score
        health_score = self.scan_results.get('score', 0)
        
        # Generate operations table rows
        ops_rows = ""
        for i, op in enumerate(self.operations, 1):
            status_color = "#10b981" if op.get('success', True) else "#ef4444"
            status_text = "✓ Exitoso" if op.get('success', True) else "✗ Fallido"
            op_type = op.get('type', 'Operación')
            op_desc = op.get('description', op.get('message', 'Sin descripción'))
            op_time = op.get('timestamp', '')[:19].replace('T', ' ')
            
            ops_rows += f'''
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #333;">{i}</td>
                <td style="padding: 12px; border-bottom: 1px solid #333;">{op_type}</td>
                <td style="padding: 12px; border-bottom: 1px solid #333;">{op_desc[:80]}</td>
                <td style="padding: 12px; border-bottom: 1px solid #333; color: {status_color};">{status_text}</td>
                <td style="padding: 12px; border-bottom: 1px solid #333; font-size: 12px;">{op_time}</td>
            </tr>
            '''
        
        # Generate issues found section
        issues_html = ""
        issues_found = self.scan_results.get('issues_found', [])
        if issues_found:
            issues_html = '<h3 style="color: #f59e0b; margin-top: 20px;">⚠️ Problemas Detectados</h3><ul>'
            for issue in issues_found[:10]:
                severity_color = {"high": "#ef4444", "medium": "#f59e0b", "low": "#10b981"}.get(issue.get('severity', 'medium'), "#f59e0b")
                issues_html += f'<li style="color: {severity_color}; margin: 8px 0;">{issue.get("message", "")}</li>'
            issues_html += '</ul>'
        
        # Generate threats section
        threats_html = ""
        threats_found = self.scan_results.get('threats_found', [])
        if threats_found:
            threats_html = '<h3 style="color: #ef4444; margin-top: 20px;">🚨 Amenazas Detectadas</h3><ul>'
            for threat in threats_found[:10]:
                threats_html += f'<li style="color: #ef4444; margin: 8px 0;">{threat.get("type", "")}: {threat.get("name", "N/A")}</li>'
            threats_html += '</ul>'
        
        # System info
        sys_info = self.scan_results.get('system_info', {})
        hardware = self.scan_results.get('hardware', {})
        
        html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Reporte de Servicio - Autonova RMM</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', sans-serif;
            background: #0f0f0f;
            color: #e5e5e5;
            padding: 40px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #1a1a1a;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }}
        
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #333;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .logo {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .logo h1 {{
            font-size: 28px;
            background: linear-gradient(135deg, #6366f1, #10b981);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .report-meta {{
            text-align: right;
            color: #888;
        }}
        
        .section {{
            margin: 30px 0;
            padding: 25px;
            background: #252525;
            border-radius: 12px;
            border-left: 4px solid #6366f1;
        }}
        
        .section h2 {{
            color: #6366f1;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        
        .stat-card {{
            background: #1a1a1a;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 32px;
            font-weight: 700;
            color: #10b981;
        }}
        
        .stat-label {{
            color: #888;
            font-size: 14px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        
        th {{
            background: #333;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #10b981;
        }}
        
        .health-score {{
            text-align: center;
            padding: 30px;
        }}
        
        .score-circle {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: linear-gradient(135deg, #6366f1, #10b981);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 42px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        
        .signature-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            margin-top: 40px;
            padding-top: 30px;
            border-top: 2px solid #333;
        }}
        
        .signature-box {{
            padding: 20px;
            background: #252525;
            border-radius: 10px;
        }}
        
        .signature-line {{
            border-bottom: 2px solid #555;
            height: 60px;
            margin: 20px 0 10px 0;
        }}
        
        .footer {{
            margin-top: 40px;
            text-align: center;
            color: #666;
            font-size: 12px;
            padding-top: 20px;
            border-top: 1px solid #333;
        }}
        
        .seal {{
            display: inline-block;
            padding: 15px 30px;
            border: 3px solid #10b981;
            border-radius: 50%;
            color: #10b981;
            font-weight: 700;
            text-transform: uppercase;
            transform: rotate(-5deg);
            margin: 20px;
        }}
        
        @media print {{
            body {{ background: white; color: black; }}
            .container {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">
                {AUTONOVA_LOGO}
                <div>
                    <h1>AUTONOVA RMM</h1>
                    <p style="color: #888;">Reporte de Servicio Técnico</p>
                </div>
            </div>
            <div class="report-meta">
                <p><strong>Fecha:</strong> {date_str}</p>
                <p><strong>Hora:</strong> {time_str}</p>
                <p><strong>ID Reporte:</strong> RPT-{agent_id[:8].upper()}</p>
            </div>
        </div>
        
        <div class="section">
            <h2>📋 Información del Equipo</h2>
            <div class="grid">
                <div><strong>Hostname:</strong> {hostname}</div>
                <div><strong>Sistema:</strong> {sys_info.get('os', 'Windows')} {sys_info.get('os_release', '')}</div>
                <div><strong>Usuario:</strong> {sys_info.get('username', 'N/A')}</div>
                <div><strong>Arquitectura:</strong> {sys_info.get('architecture', 'x64')}</div>
                <div><strong>Procesador:</strong> {sys_info.get('processor', 'N/A')[:30]}...</div>
                <div><strong>ID Agente:</strong> {agent_id}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🏥 Diagnóstico del Sistema</h2>
            <div class="health-score">
                <div class="score-circle">{health_score}</div>
                <p style="color: #888;">Puntuación de Salud</p>
            </div>
            <div class="grid">
                <div class="stat-card">
                    <div class="stat-value">{total_ops}</div>
                    <div class="stat-label">Operaciones Realizadas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #10b981;">{success_ops}</div>
                    <div class="stat-label">Exitosas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #ef4444;">{failed_ops}</div>
                    <div class="stat-label">Con Errores</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(threats_found)}</div>
                    <div class="stat-label">Amenazas Detectadas</div>
                </div>
            </div>
            {issues_html}
            {threats_html}
        </div>
        
        <div class="section">
            <h2>📝 Detalle de Operaciones</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Tipo</th>
                        <th>Descripción</th>
                        <th>Estado</th>
                        <th>Fecha/Hora</th>
                    </tr>
                </thead>
                <tbody>
                    {ops_rows if ops_rows else '<tr><td colspan="5" style="padding: 20px; text-align: center; color: #888;">Sin operaciones registradas</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <div class="section" style="text-align: center;">
            <div class="seal">✓ SERVICIO<br>CERTIFICADO</div>
            <p style="color: #10b981; font-weight: 600; margin-top: 15px;">
                Este equipo ha sido verificado y optimizado por Autonova RMM
            </p>
        </div>
        
        <div class="signature-section">
            <div class="signature-box">
                <h3 style="color: #6366f1;">Técnico Responsable</h3>
                <div class="signature-line"></div>
                <p><strong>{technician}</strong></p>
                <p style="color: #888; font-size: 12px;">Firma y Sello</p>
            </div>
            <div class="signature-box">
                <h3 style="color: #6366f1;">Cliente</h3>
                <div class="signature-line"></div>
                <p><strong>{client_name}</strong></p>
                <p style="color: #888; font-size: 12px;">Firma de Conformidad</p>
            </div>
        </div>
        
        <div class="footer">
            <p>Reporte generado automáticamente por <strong>Autonova RMM v1.0</strong></p>
            <p>© {now.year} Autonova - Todos los derechos reservados</p>
            <p style="margin-top: 10px; color: #555;">
                Este documento certifica que el servicio fue realizado conforme a los estándares de calidad de Autonova.
            </p>
        </div>
    </div>
</body>
</html>
        '''
        
        return html
    
    async def generate_and_save(
        self,
        hostname: str,
        agent_id: str,
        technician: str = "Técnico Autonova"
    ) -> Dict[str, Any]:
        """Generate and save report to file."""
        
        await self.log("Generando reporte profesional...")
        
        html = self.generate_html(hostname, agent_id, technician)
        
        # Save to reports directory
        reports_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'Autonova' / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{hostname}_{timestamp}.html"
        filepath = reports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        await self.log(f"✓ Reporte guardado: {filepath}")
        
        return {
            "success": True,
            "filepath": str(filepath),
            "filename": filename,
            "html": html,
            "operations_count": len(self.operations),
            "timestamp": datetime.now().isoformat()
        }


# Global report instance for the session
_current_report: Optional[ReportGenerator] = None


def get_report_generator(progress_callback: Callable = None) -> ReportGenerator:
    """Get or create report generator for current session."""
    global _current_report
    if _current_report is None:
        _current_report = ReportGenerator(progress_callback)
    else:
        _current_report.progress_callback = progress_callback
    return _current_report


async def generate_report(
    hostname: str,
    agent_id: str,
    command_logs: List[Dict[str, Any]] = None,
    scan_results: Dict[str, Any] = None,
    progress_callback: Callable = None
) -> Dict[str, Any]:
    """
    Generate comprehensive service report.
    
    Args:
        hostname: Computer hostname
        agent_id: Agent identifier
        command_logs: List of executed commands
        scan_results: Results from system scan
        progress_callback: Progress update callback
    """
    report = get_report_generator(progress_callback)
    
    # Add command logs as operations
    if command_logs:
        for log in command_logs:
            report.add_operation({
                "type": log.get('command_type', 'Comando'),
                "description": str(log.get('result', {}))[:100],
                "success": log.get('success', True),
                "timestamp": log.get('timestamp', datetime.now().isoformat())
            })
    
    # Set scan results
    if scan_results:
        report.set_scan_results(scan_results)
    
    return await report.generate_and_save(hostname, agent_id)
