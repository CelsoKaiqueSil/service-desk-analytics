import json
from pathlib import Path
import subprocess
import sys
import pandas as pd

ROOT = Path(__file__).parents[1]


def test_powerbi_model_references_and_synthetic_parity():
    subprocess.run([sys.executable, 'scripts/build_powerbi.py'], cwd=ROOT, check=True)
    folder = ROOT / 'powerbi'
    model = json.loads((folder / 'ServiceDesk.SemanticModel/model.bim').read_text(encoding='utf-8'))['model']
    tables = {table['name']: table for table in model['tables']}
    for relationship in model['relationships']:
        for side in ['from', 'to']:
            assert relationship[side+'Column'] in {col['name'] for col in tables[relationship[side+'Table']]['columns']}
    assert sum(rel['isActive'] is False for rel in model['relationships']) == 1
    facts = pd.read_csv(folder / 'data/fact_tickets.csv')
    expected = json.loads((folder / 'expected_metrics.json').read_text())
    assert len(facts) == expected['opened'] == 8
    assert int(facts.SolutionHours.notna().sum()) == expected['resolved'] == 6
    assert round(facts.loc[facts.SLAEligible, 'SLAMet'].mean()*100, 8) == round(expected['sla_met_percent'], 8)
    assert len(list((folder / 'ServiceDesk.Report').rglob('visual.json'))) == 9
