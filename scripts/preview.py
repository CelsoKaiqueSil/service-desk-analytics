"""Render a reproducible analytical preview, not a native Excel or Power BI screenshot."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from service_desk_analytics.pipeline import load_tickets, calculate_kpis

ROOT = Path(__file__).resolve().parents[1]
frame = load_tickets(ROOT / 'data/tickets.csv')
kpis = calculate_kpis(frame)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
fig = plt.figure(figsize=(13, 7.5), facecolor='#f6f8f9')
fig.text(.05, .94, 'Service Desk Analytics', fontsize=24, weight='bold', color='#173631')
fig.text(.05, .89, 'Amostra sintetica | 01 a 06 jul 2026 | tempos em horas corridas UTC', color='#52636b')
for x, title, value in zip([.05, .29, .53, .77], ['Chamados unicos', 'Resolvidos', 'SLA elegivel', 'Backlog snapshot'], [str(kpis['opened']), str(kpis['resolved']), f"{kpis['sla_met_percent']:.1f}%", str(kpis['backlog'])]):
    fig.text(x, .80, title, color='#52636b')
    fig.text(x, .72, value, fontsize=29, weight='bold', color='#147e57')
ax = fig.add_axes([.18, .18, .29, .42], facecolor='#f6f8f9')
counts = frame.groupby('category').size().sort_values()
ax.barh(counts.index, counts, color=['#147e57', '#008aab', '#d39a29', '#73828d'])
ax.set_title('Volume por categoria', loc='left', pad=16)
ax.set_xlabel('Chamados')
ax.set_xlim(0, counts.max()+1)
for i, v in enumerate(counts): ax.text(v+.06, i, str(v), va='center')
ax = fig.add_axes([.60, .18, .34, .42], facecolor='#f6f8f9')
values = [kpis['response_mean_hours'], kpis['response_median_hours'], kpis['response_p90_hours']]
ax.bar(['Media', 'Mediana', 'P90'], values, color=['#008aab', '#147e57', '#d39a29'])
ax.set_title('Primeira resposta', loc='left', pad=16)
ax.set_ylabel('Horas corridas')
for i, v in enumerate(values): ax.text(i, v+.05, f'{v:.2f} h', ha='center')
fig.text(.05, .06, 'Previa Python dos indicadores. Nao e captura do Power BI nem dado de cliente.', fontsize=10, color='#52636b')
output = ROOT / 'docs/images/preview.png'
output.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(output, dpi=140)
plt.close(fig)
