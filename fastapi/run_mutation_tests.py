#!/usr/bin/env python
"""
Custom mutation testing framework for FastAPI encoders.py
Generates mutants by modifying operators, constants, and logic
"""

import ast
import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
import shutil

class MutationGenerator(ast.NodeTransformer):
    """Generates mutations of Python code by modifying operators, constants, and logic"""
    
    def __init__(self, target_mutation: int = None):
        self.mutation_count = 0
        self.target_mutation = target_mutation
        self.mutations_found = []
        self.current_line = 0
        self.in_docstring = False
        
    def visit(self, node):
        if hasattr(node, 'lineno'):
            self.current_line = node.lineno
        return super().visit(node)
    
    def visit_Constant(self, node):
        """Mutate constants (skip docstrings)"""
        # Skip if this is a docstring (string at beginning of function/module)
        if isinstance(node.value, str):
            return node
            
        # Only count/mutate non-string constants
        self.mutations_found.append(('Constant', self.current_line, repr(node.value)))
        
        if self.target_mutation is None:
            return node
            
        if self.mutation_count == self.target_mutation:
            if isinstance(node.value, bool):
                node.value = not node.value
                return node
            elif isinstance(node.value, int) and not isinstance(node.value, bool):
                node.value = node.value + 1 if node.value != 0 else -1
                return node
            elif isinstance(node.value, float):
                node.value = node.value + 1.0 if node.value != 0.0 else -1.0
                return node
            elif node.value is None:
                node.value = False
                return node
        
        self.mutation_count += 1
        return node
    
    def visit_BinOp(self, node):
        """Mutate binary operators"""
        self.generic_visit(node)
        self.mutations_found.append(('BinOp', self.current_line, type(node.op).__name__))
        
        if self.target_mutation is None:
            return node
            
        if self.mutation_count == self.target_mutation:
            ops = {
                ast.Add: ast.Sub,
                ast.Sub: ast.Add,
                ast.Mult: ast.Div,
                ast.Div: ast.Mult,
                ast.Mod: ast.Add,
                ast.Pow: ast.Mult,
                ast.LShift: ast.RShift,
                ast.RShift: ast.LShift,
                ast.BitOr: ast.BitAnd,
                ast.BitAnd: ast.BitOr,
                ast.BitXor: ast.BitAnd,
                ast.FloorDiv: ast.Div,
            }
            if type(node.op) in ops:
                node.op = ops[type(node.op)]()
                return node
        
        self.mutation_count += 1
        return node
    
    def visit_Compare(self, node):
        """Mutate comparison operators"""
        for i, op in enumerate(node.ops):
            self.mutations_found.append(('Compare', self.current_line, type(op).__name__))
            
            if self.target_mutation is not None and self.mutation_count == self.target_mutation:
                ops = {
                    ast.Eq: ast.NotEq,
                    ast.NotEq: ast.Eq,
                    ast.Lt: ast.Gt,
                    ast.Gt: ast.Lt,
                    ast.LtE: ast.GtE,
                    ast.GtE: ast.LtE,
                    ast.Is: ast.IsNot,
                    ast.IsNot: ast.Is,
                    ast.In: ast.NotIn,
                    ast.NotIn: ast.In,
                }
                if type(op) in ops:
                    node.ops[i] = ops[type(op)]()
                    return node
            
            self.mutation_count += 1
        
        self.generic_visit(node)
        return node
    
    def visit_BoolOp(self, node):
        """Mutate boolean operators"""
        self.generic_visit(node)
        self.mutations_found.append(('BoolOp', self.current_line, type(node.op).__name__))
        
        if self.target_mutation is None:
            return node
            
        if self.mutation_count == self.target_mutation:
            if isinstance(node.op, ast.And):
                node.op = ast.Or()
            elif isinstance(node.op, ast.Or):
                node.op = ast.And()
            return node
        
        self.mutation_count += 1
        return node
    
    def visit_If(self, node):
        """Mutate if conditions - negate boolean test"""
        self.mutations_found.append(('If', self.current_line, 'negate_condition'))
        
        if self.target_mutation is not None and self.mutation_count == self.target_mutation:
            # Negate the condition
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            ast.copy_location(node.test, node)
        
        self.mutation_count += 1
        self.generic_visit(node)
        return node
    
    def visit_Assign(self, node):
        """Mutate assignment operators"""
        for target in node.targets:
            self.mutations_found.append(('Assign', self.current_line, 'value_swap'))
        
        if self.target_mutation is not None and self.mutation_count == self.target_mutation:
            # Negate the assigned value if it's a boolean
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool):
                node.value.value = not node.value.value
                return node
        
        self.mutation_count += 1
        self.generic_visit(node)
        return node
        """Mutate return statements"""
        if node.value is not None:
            self.mutations_found.append(('Return', self.current_line, 'negate_return'))
            
            if self.target_mutation is not None and self.mutation_count == self.target_mutation:
                # Negate the return value if it's a boolean expression
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool):
                    node.value.value = not node.value.value
                else:
                    node.value = ast.UnaryOp(op=ast.Not(), operand=node.value)
                    ast.copy_location(node.value, node)
                return node
            
            self.mutation_count += 1
        
        self.generic_visit(node)
        return node


def count_mutations(source_code: str) -> int:
    """Count total possible mutations"""
    try:
        tree = ast.parse(source_code)
        generator = MutationGenerator(target_mutation=None)
        generator.visit(tree)
        return generator.mutation_count
    except:
        return 0


def generate_mutation(source_code: str, mutation_id: int) -> Tuple[str, bool]:
    """Generate a specific mutation"""
    try:
        tree = ast.parse(source_code)
        generator = MutationGenerator(target_mutation=mutation_id)
        new_tree = generator.visit(tree)
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree), True
    except Exception as e:
        return None, False


def run_tests(test_timeout: int = 60) -> Tuple[bool, str]:
    """Run the test suite"""
    try:
        result = subprocess.run(
            ['python', '-m', 'pytest', 'tests/test_jsonable_encoder.py', '-q', '--tb=no'],
            capture_output=True,
            text=True,
            timeout=test_timeout,
            cwd=os.getcwd()
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Test timeout"
    except Exception as e:
        return False, str(e)


def main():
    # Read the original source
    encoders_path = Path('fastapi/encoders.py')
    if not encoders_path.exists():
        print(f"Error: {encoders_path} not found")
        sys.exit(1)
    
    original_source = encoders_path.read_text()
    
    # Create backup
    backup_path = Path('fastapi/encoders.py.backup')
    backup_path.write_text(original_source)
    print(f"Backup created at {backup_path}")
    
    # Count mutations
    total_mutations = count_mutations(original_source)
    print(f"\nTotal possible mutations found: {total_mutations}")
    
    # Limit to at least 100 mutations
    num_mutations = max(100, total_mutations)
    print(f"Will test {min(num_mutations, total_mutations)} mutations")
    
    # Test report
    report = {
        'timestamp': datetime.now().isoformat(),
        'file': str(encoders_path),
        'total_mutations': total_mutations,
        'mutations_tested': 0,
        'mutations_killed': 0,
        'mutations_survived': 0,
        'errors': 0,
        'mutation_results': []
    }
    
    # Run tests on original
    print("\nRunning tests on original code...")
    original_pass, original_output = run_tests()
    if not original_pass:
        print("WARNING: Tests fail on original code!")
        print(original_output[:500])
    else:
        print("✓ Original code passes all tests")
    
    # Generate and test mutations
    print(f"\nTesting {min(num_mutations, total_mutations)} mutations...")
    
    mutation_id = 0
    while mutation_id < min(num_mutations, total_mutations):
        mutated_source, success = generate_mutation(original_source, mutation_id)
        
        if not success or mutated_source is None:
            mutation_id += 1
            continue
        
        # Only test if mutation is different from original (actual code change)
        if mutated_source == original_source:
            mutation_id += 1
            continue
        
        # Write mutated code
        encoders_path.write_text(mutated_source)
        
        # Run tests
        test_pass, test_output = run_tests()
        
        report['mutations_tested'] += 1
        
        if test_pass:
            # Mutation survived (test passed - bad mutation)
            report['mutations_survived'] += 1
            status = 'SURVIVED'
        else:
            # Mutation killed (test failed - good mutation)
            report['mutations_killed'] += 1
            status = 'KILLED'
        
        report['mutation_results'].append({
            'mutation_id': mutation_id,
            'status': status,
            'test_output_lines': len(test_output.split('\n'))
        })
        
        # Print progress
        if (mutation_id + 1) % 10 == 0:
            killed_rate = (report['mutations_killed'] / report['mutations_tested'] * 100) if report['mutations_tested'] > 0 else 0
            print(f"Progress: {mutation_id + 1}/{min(num_mutations, total_mutations)} | Killed: {killed_rate:.1f}%")
        
        mutation_id += 1
    
    # Restore original
    encoders_path.write_text(original_source)
    print(f"\nOriginal code restored")
    
    # Generate report
    mutation_score = (report['mutations_killed'] / report['mutations_tested'] * 100) if report['mutations_tested'] > 0 else 0
    report['mutation_score'] = mutation_score
    
    # Save JSON report
    report_path = Path('mutation_report.json')
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nJSON report saved to {report_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("MUTATION TESTING REPORT")
    print("="*60)
    print(f"File: {encoders_path}")
    print(f"Total possible mutations: {total_mutations}")
    print(f"Mutations tested: {report['mutations_tested']}")
    print(f"Mutations killed: {report['mutations_killed']}")
    print(f"Mutations survived: {report['mutations_survived']}")
    print(f"Mutation score: {mutation_score:.2f}%")
    print("="*60)
    
    # Generate HTML report
    html_report = generate_html_report(report, mutation_score)
    html_path = Path('mutation_report.html')
    html_path.write_text(html_report)
    print(f"HTML report saved to {html_path}")
    
    return report


def generate_html_report(report: Dict, mutation_score: float) -> str:
    """Generate an HTML report"""
    killed = report['mutations_killed']
    survived = report['mutations_survived']
    total = report['mutations_tested']
    
    killed_pct = (killed / total * 100) if total > 0 else 0
    survived_pct = (survived / total * 100) if total > 0 else 0
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mutation Testing Report - encoders.py</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }}
            .header {{
                background-color: #2c3e50;
                color: white;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .summary {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr 1fr;
                gap: 15px;
                margin-bottom: 20px;
            }}
            .metric {{
                background-color: white;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .metric h3 {{
                margin: 0 0 10px 0;
                color: #666;
                font-size: 0.9em;
                text-transform: uppercase;
            }}
            .metric-value {{
                font-size: 2em;
                font-weight: bold;
                color: #2c3e50;
            }}
            .killed {{
                color: #27ae60;
            }}
            .survived {{
                color: #e74c3c;
            }}
            .score {{
                color: #3498db;
            }}
            .chart {{
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .bar-container {{
                display: flex;
                height: 30px;
                border-radius: 3px;
                overflow: hidden;
                background-color: #ecf0f1;
            }}
            .killed-bar {{
                background-color: #27ae60;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: flex-end;
                padding-right: 10px;
                color: white;
                font-weight: bold;
            }}
            .survived-bar {{
                background-color: #e74c3c;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: flex-end;
                padding-right: 10px;
                color: white;
                font-weight: bold;
            }}
            .details {{
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            footer {{
                margin-top: 30px;
                text-align: center;
                color: #999;
                font-size: 0.9em;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Mutation Testing Report</h1>
            <p>FastAPI encoders.py Mutation Analysis</p>
            <p style="font-size: 0.9em; margin: 10px 0 0 0;">Generated: {report['timestamp']}</p>
        </div>
        
        <div class="summary">
            <div class="metric">
                <h3>Mutations Tested</h3>
                <div class="metric-value">{total}</div>
            </div>
            <div class="metric">
                <h3>Killed</h3>
                <div class="metric-value killed">{killed}</div>
            </div>
            <div class="metric">
                <h3>Survived</h3>
                <div class="metric-value survived">{survived}</div>
            </div>
            <div class="metric">
                <h3>Mutation Score</h3>
                <div class="metric-value score">{mutation_score:.1f}%</div>
            </div>
        </div>
        
        <div class="chart">
            <h3>Mutation Results Distribution</h3>
            <div class="bar-container">
                <div class="killed-bar" style="width: {killed_pct}%">
                    {killed} Killed ({killed_pct:.1f}%)
                </div>
                <div class="survived-bar" style="width: {survived_pct}%">
                    {survived} Survived ({survived_pct:.1f}%)
                </div>
            </div>
        </div>
        
        <div class="details">
            <h3>Details</h3>
            <ul>
                <li><strong>File:</strong> {report['file']}</li>
                <li><strong>Total Possible Mutations:</strong> {report['total_mutations']}</li>
                <li><strong>Mutations Tested:</strong> {report['mutations_tested']}</li>
                <li><strong>Mutation Score:</strong> {mutation_score:.2f}%</li>
            </ul>
            <p>
                A mutation score of 100% means all mutations were killed (caught by tests).
                This indicates strong test coverage. Lower scores suggest areas where test
                coverage could be improved.
            </p>
        </div>
        
        <footer>
            <p>Report generated by Custom Mutation Testing Framework</p>
        </footer>
    </body>
    </html>
    """
    return html


if __name__ == '__main__':
    main()
