"""Build a portable PBIP demonstration from the validated synthetic ticket snapshot."""
from pathlib import Path
import csv
import io
import json
import pandas as pd
from service_desk_analytics.pipeline import load_tickets, calculate_kpis

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'powerbi'
BASE = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def m_source(frame, types):
    stream = io.StringIO()
    frame.to_csv(stream, index=False, quoting=csv.QUOTE_ALL, lineterminator='\n')
    literal = stream.getvalue().replace('"', '""').replace('\n', '#(lf)')
    conversions = ', '.join('{"' + name + '", ' + kind + '}' for name, kind in types.items())
    return f'let Source = Csv.Document(Text.ToBinary("{literal}", TextEncoding.Utf8), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]), Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]), Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)), Typed = Table.TransformColumnTypes(Nulls, {{{conversions}}}, "en-US") in Typed'


def table(name, frame, types):
    mapping = {'type text': 'string', 'Int64.Type': 'int64', 'type number': 'double', 'type date': 'dateTime', 'type logical': 'boolean'}
    return {'name': name, 'columns': [{'name': column, 'dataType': mapping[kind], 'sourceColumn': column,
        'summarizeBy': 'none', **({'formatString': 'yyyy-MM-dd'} if kind == 'type date' else {})} for column, kind in types.items()],
        'partitions': [{'name': name, 'mode': 'import', 'source': {'type': 'm', 'expression': m_source(frame, types)}}]}


def field(table_name, name, measure=False):
    return {'field': {'Measure' if measure else 'Column': {'Expression': {'SourceRef': {'Entity': table_name}}, 'Property': name}},
        'queryRef': table_name + '.' + name}


def visual(page, name, kind, x, y, width, height, roles):
    write(OUT / 'ServiceDesk.Report/definition/pages' / page / 'visuals' / name / 'visual.json', {
        '$schema': BASE + 'visualContainer/2.1.0/schema.json', 'name': name,
        'position': {'x': x, 'y': y, 'z': 0, 'width': width, 'height': height, 'tabOrder': y+x},
        'visual': {'visualType': kind, 'query': {'queryState': {role: {'projections': fields} for role, fields in roles.items()}},
            'drillFilterOtherVisuals': True}})


def main():
    frame = load_tickets(ROOT / 'data/tickets.csv')
    categories = pd.DataFrame({'Category': sorted(frame.category.unique())})
    categories.insert(0, 'CategoryKey', range(1, len(categories)+1))
    owners = pd.DataFrame({'Owner': sorted(frame.owner.unique())})
    owners.insert(0, 'OwnerKey', range(1, len(owners)+1))
    facts = pd.DataFrame({'TicketId': frame.ticket_id, 'OpenedDateKey': frame.opened_at.dt.strftime('%Y%m%d').astype(int),
        'ResolvedDateKey': frame.resolved_at.dt.strftime('%Y%m%d').astype('Int64'),
        'CategoryKey': frame.category.map(dict(zip(categories.Category, categories.CategoryKey))),
        'OwnerKey': frame.owner.map(dict(zip(owners.Owner, owners.OwnerKey))), 'Status': frame.status,
        'ResponseHours': frame.response_hours, 'SolutionHours': frame.solution_hours,
        'SLAEligible': frame.sla_met.notna(), 'SLAMet': frame.sla_met})
    calendar = pd.DataFrame({'Date': pd.date_range('2026-01-01', '2026-12-31')})
    calendar['DateKey'] = calendar.Date.dt.strftime('%Y%m%d').astype(int)
    calendar['YearMonth'] = calendar.Date.dt.strftime('%Y-%m')
    calendar.Date = calendar.Date.dt.strftime('%Y-%m-%d')
    types = {'TicketId': 'type text', 'OpenedDateKey': 'Int64.Type', 'ResolvedDateKey': 'Int64.Type',
        'CategoryKey': 'Int64.Type', 'OwnerKey': 'Int64.Type', 'Status': 'type text',
        'ResponseHours': 'type number', 'SolutionHours': 'type number', 'SLAEligible': 'type logical', 'SLAMet': 'type logical'}
    tables = [table('FactTickets', facts, types), table('DimCategory', categories, {'CategoryKey': 'Int64.Type', 'Category': 'type text'}),
        table('DimOwner', owners, {'OwnerKey': 'Int64.Type', 'Owner': 'type text'}),
        table('DimDate', calendar, {'Date': 'type date', 'DateKey': 'Int64.Type', 'YearMonth': 'type text'})]
    measures = {
        'Chamados': ('COUNTROWS(FactTickets)', '0'),
        'Resolvidos': ('COUNTROWS(FILTER(FactTickets, NOT ISBLANK(FactTickets[SolutionHours])))', '0'),
        'Backlog snapshot': ('CALCULATE([Chamados], FactTickets[Status] IN {"Aberto", "Em andamento"})', '0'),
        'SLA elegiveis': ('CALCULATE([Chamados], FactTickets[SLAEligible] = TRUE())', '0'),
        'SLA cumpridos': ('CALCULATE([Chamados], FactTickets[SLAMet] = TRUE())', '0'),
        'SLA percentual': ('DIVIDE([SLA cumpridos], [SLA elegiveis])', '0.0%'),
        'Resposta media h': ('AVERAGE(FactTickets[ResponseHours])', '0.00'),
        'Resposta mediana h': ('MEDIAN(FactTickets[ResponseHours])', '0.00'),
        'Solucao P90 h': ('PERCENTILEX.INC(FILTER(FactTickets, NOT ISBLANK(FactTickets[SolutionHours])), FactTickets[SolutionHours], 0.9)', '0.00'),
        'Chamados mes anterior': ('CALCULATE([Chamados], DATEADD(DimDate[Date], -1, MONTH))', '0'),
        'Resolvidos por data': ('CALCULATE([Resolvidos], USERELATIONSHIP(FactTickets[ResolvedDateKey], DimDate[DateKey]))', '0'),
    }
    tables[0]['measures'] = [{'name': name, 'expression': expr, 'formatString': fmt} for name, (expr, fmt) in measures.items()]
    tables[3]['dataCategory'] = 'Time'
    tables[3]['columns'][0]['isKey'] = True
    relationships = []
    for key, dimension, active in [('CategoryKey', 'DimCategory', True), ('OwnerKey', 'DimOwner', True),
            ('OpenedDateKey', 'DimDate', True), ('ResolvedDateKey', 'DimDate', False)]:
        relationships.append({'name': 'Fact_' + key, 'fromTable': 'FactTickets', 'fromColumn': key,
            'toTable': dimension, 'toColumn': 'DateKey' if dimension == 'DimDate' else key,
            'crossFilteringBehavior': 'oneDirection', 'isActive': active})
    write(OUT / 'ServiceDesk.SemanticModel/model.bim', {'name': 'ServiceDeskDemo', 'compatibilityLevel': 1600,
        'model': {'culture': 'en-US', 'defaultPowerBIDataSourceVersion': 'powerBI_V3', 'tables': tables, 'relationships': relationships}})
    write(OUT / 'ServiceDesk.SemanticModel/definition.pbism', {'version': '4.0', 'settings': {}})
    write(OUT / 'ServiceDesk.pbip', {'version': '1.0', 'artifacts': [{'report': {'path': 'ServiceDesk.Report'}}], 'settings': {'enableAutoRecovery': True}})
    write(OUT / 'ServiceDesk.Report/definition.pbir', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json',
        'version': '4.0', 'datasetReference': {'byPath': {'path': '../ServiceDesk.SemanticModel'}}})
    write(OUT / 'ServiceDesk.Report/definition/report.json', {'$schema': BASE + 'report/2.1.0/schema.json', 'themeCollection': {}})
    write(OUT / 'ServiceDesk.Report/definition/pages/pages.json', {'$schema': BASE + 'pagesMetadata/1.0.0/schema.json', 'pageOrder': ['Resumo', 'Detalhes'], 'activePageName': 'Resumo'})
    for name in ['Resumo', 'Detalhes']:
        write(OUT / f'ServiceDesk.Report/definition/pages/{name}/page.json', {'$schema': BASE + 'page/2.0.0/schema.json',
            'name': name, 'displayName': name + ' - dados sinteticos', 'displayOption': 'FitToPage', 'width': 1280, 'height': 720})
    for index, measure in enumerate(['Chamados', 'Resolvidos', 'SLA percentual', 'Solucao P90 h']):
        visual('Resumo', 'kpi'+str(index), 'card', 24+index*312, 24, 288, 130, {'Values': [field('FactTickets', measure, True)]})
    visual('Resumo', 'categorias', 'clusteredBarChart', 24, 180, 600, 360,
        {'Category': [field('DimCategory', 'Category')], 'Y': [field('FactTickets', 'Chamados', True)]})
    visual('Resumo', 'resposta', 'clusteredBarChart', 650, 180, 600, 360,
        {'Category': [field('DimOwner', 'Owner')], 'Y': [field('FactTickets', 'Resposta mediana h', True)]})
    visual('Resumo', 'periodo', 'slicer', 24, 570, 600, 110, {'Values': [field('DimDate', 'YearMonth')]})
    visual('Resumo', 'analista', 'slicer', 650, 570, 600, 110, {'Values': [field('DimOwner', 'Owner')]})
    visual('Detalhes', 'chamados', 'tableEx', 24, 24, 1232, 650, {'Values': [field('FactTickets', name) for name in types]})
    for name, data in [('fact_tickets', facts), ('dim_category', categories), ('dim_owner', owners), ('dim_date', calendar)]:
        path = OUT / 'data' / (name+'.csv')
        path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(path, index=False, lineterminator='\n')
    (OUT / 'measures.dax').write_text('\n\n'.join(f'{name} = {expr}' for name, (expr, _) in measures.items())+'\n', encoding='utf-8')
    write(OUT / 'expected_metrics.json', calculate_kpis(frame))
    print('PBIP, model, DAX and synthetic star schema generated. Native Desktop validation is still required.')


if __name__ == '__main__':
    main()
