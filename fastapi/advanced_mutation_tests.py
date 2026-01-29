#!/usr/bin/env python
"""
Advanced Mutation Testing Framework for FastAPI encoders.py
Generates 100+ mutants with various mutation operators
"""

import ast
import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Tuple, Any
from datetime import datetime
import random
import re

class AdvancedMutationGenerator(ast.NodeTransformer):
    """Advanced mutation operator generator"""
    
    def __init__(self, target_mutation: int = None, mutation_type: str = None):
        self.mutation_count = 0
        self.target_mutation = target_mutation
        self.target_mutation_type = mutation_type
        self.mutations_found = []
        self.current_line = 0
        
    def visit(self, node):
        if hasattr(node, 'lineno'):
            self.current_line = node.lineno
        return super().visit(node)
    
    def record_mutation(self, mutation_type: str, description: str = ""):
        """Record a potential mutation point"""
        self.mutations_found.append({
            'type': mutation_type,
            'line': self.current_line,
            'description': description
        })
    
    def apply_mutation_if_match(self, mutation_type: str):
        """Apply mutation if this is the target"""
        if self.target_mutation is not None and self.mutation_count == self.target_mutation:
            if self.target_mutation_type is None or self.target_mutation_type == mutation_type:
                return True
        return False
    
    def visit_Constant(self, node):
        """Mutate constants"""
        if isinstance(node.value, str):
            self.generic_visit(node)
            return node
        
        if isinstance(node.value, bool):
            self.record_mutation('BoolConstant', f"bool {node.value}")
            if self.apply_mutation_if_match('BoolConstant'):
                node.value = not node.value
                self.mutation_count += 1
                return node
            self.mutation_count += 1
        
        elif isinstance(node.value, int) and not isinstance(node.value, bool):
            self.record_mutation('IntConstant', f"int {node.value}")
            if self.apply_mutation_if_match('IntConstant'):
                node.value = node.value + 1 if node.value != 0 else -1
                self.mutation_count += 1
                return node
            self.mutation_count += 1
        
        elif isinstance(node.value, float):
            self.record_mutation('FloatConstant', f"float {node.value}")
            if self.apply_mutation_if_match('FloatConstant'):
                node.value = node.value + 1.0 if node.value != 0.0 else -1.0
                self.mutation_count += 1
                return node
            self.mutation_count += 1
        
        elif node.value is None:
            self.record_mutation('NoneConstant', "None")
            if self.apply_mutation_if_match('NoneConstant'):
                node.value = False
                self.mutation_count += 1
                return node
            self.mutation_count += 1
        
        self.generic_visit(node)
        return node
    
    def visit_BinOp(self, node):
        """Mutate binary operators"""
        self.generic_visit(node)
        op_name = type(node.op).__name__
        self.record_mutation('BinOp', op_name)
        
        if self.apply_mutation_if_match('BinOp'):
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
                self.mutation_count += 1
                return node
        
        self.mutation_count += 1
        return node
    
    def visit_Compare(self, node):
        """Mutate comparison operators"""
        for i, op in enumerate(node.ops):
            op_name = type(op).__name__
            self.record_mutation('Compare', op_name)
            
            if self.apply_mutation_if_match('Compare'):
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
                    self.mutation_count += 1
                    return node
            
            self.mutation_count += 1
        
        self.generic_visit(node)
        return node
    
    def visit_BoolOp(self, node):
        """Mutate boolean operators"""
        self.generic_visit(node)
        op_name = type(node.op).__name__
        self.record_mutation('BoolOp', op_name)
        
        if self.apply_mutation_if_match('BoolOp'):
            if isinstance(node.op, ast.And):
                node.op = ast.Or()
            elif isinstance(node.op, ast.Or):
                node.op = ast.And()
            self.mutation_count += 1
            return node
        
        self.mutation_count += 1
        return node
    
    def visit_If(self, node):
        """Mutate if conditions"""
        self.record_mutation('IfNegate', 'negate_condition')
        
        if self.apply_mutation_if_match('IfNegate'):
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            ast.copy_location(node.test, node)
            self.mutation_count += 1
            self.generic_visit(node)
            return node
        
        self.mutation_count += 1
        self.generic_visit(node)
        return node
    
    def visit_While(self, node):
        """Mutate while conditions"""
        self.record_mutation('WhileNegate', 'negate_condition')
        
        if self.apply_mutation_if_match('WhileNegate'):
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            ast.copy_location(node.test, node)
            self.mutation_count += 1
            self.generic_visit(node)
            return node
        
        self.mutation_count += 1
        self.generic_visit(node)
        return node
    
    def visit_Return(self, node):
        """Mutate return statements"""
        if node.value is not None:
            self.record_mutation('ReturnNegate', 'negate_return')
            
            if self.apply_mutation_if_match('ReturnNegate'):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool):
                    node.value.value = not node.value.value
                else:
                    node.value = ast.UnaryOp(op=ast.Not(), operand=node.value)
                    ast.copy_location(node.value, node)
                self.mutation_count += 1
                self.generic_visit(node)
                return node
            
            self.mutation_count += 1
        
        self.generic_visit(node)
        return node
    
    def visit_Assign(self, node):
        """Mutate assignments"""
        for target in node.targets:
            self.record_mutation('AssignValue', 'value_swap')
        
        if self.apply_mutation_if_match('AssignValue'):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool):
                node.value.value = not node.value.value
                self.mutation_count += 1
                self.generic_visit(node)
                return node
        
        self.mutation_count += 1
        self.generic_visit(node)
        return node
    
    def visit_UnaryOp(self, node):
        """Mutate unary operators"""
        self.generic_visit(node)
        op_name = type(node.op).__name__
        self.record_mutation('UnaryOp', op_name)
        
        if self.apply_mutation_if_match('UnaryOp'):
            if isinstance(node.op, ast.Not):
                # Remove the not operator
                return node.operand
            elif isinstance(node.op, ast.USub):
                node.op = ast.UAdd()
                self.mutation_count += 1
                return node
            elif isinstance(node.op, ast.UAdd):
                node.op = ast.USub()
                self.mutation_count += 1
                return node
        
        self.mutation_count += 1
        return node
    
    def visit_Call(self, node):
        """Mutate function calls - remove calls or replace with None"""
        if hasattr(node.func, 'attr'):
            attr_name = node.func.attr
            self.record_mutation('CallRemove', f'call_to_{attr_name}')
            
            if self.apply_mutation_if_match('CallRemove'):
                # Replace call with None
                self.mutation_count += 1
                return ast.Constant(value=None)
            
            self.mutation_count += 1
        
        self.generic_visit(node)
        return node
    
    def visit_For(self, node):
        """Mutate for loop iterations"""
        self.record_mutation('ForLoopNegate', 'negate_loop')
        
        if self.apply_mutation_if_match('ForLoopNegate'):
            # Wrap the body in a negated condition (simplified)
            self.mutation_count += 1
        else:
            self.mutation_count += 1
        
        self.generic_visit(node)
        return node
    
    def visit_BinOp_AugAssign(self, node):
        """Mutate augmented assignments (+=, -=, etc)"""
        if hasattr(node, 'op'):
            op_name = type(node.op).__name__
            self.record_mutation('AugAssign', op_name)
            
            if self.apply_mutation_if_match('AugAssign'):
                ops = {
                    ast.Add: ast.Sub,
                    ast.Sub: ast.Add,
                    ast.Mult: ast.Div,
                    ast.Div: ast.Mult,
                }
                if type(node.op) in ops:
                    node.op = ops[type(node.op)]()
                    self.mutation_count += 1
                    return node
            
            self.mutation_count += 1
        
        self.generic_visit(node)
        return node


def count_mutations(source_code: str) -> Tuple[int, List[Dict]]:
    """Count total possible mutations"""
    try:
        tree = ast.parse(source_code)
        generator = AdvancedMutationGenerator(target_mutation=None)
        generator.visit(tree)
        return generator.mutation_count, generator.mutations_found
    except:
        return 0, []


def generate_mutation(source_code: str, mutation_id: int) -> Tuple[str, bool]:
    """Generate a specific mutation"""
    try:
        tree = ast.parse(source_code)
        generator = AdvancedMutationGenerator(target_mutation=mutation_id)
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
    total_mutations, mutation_list = count_mutations(original_source)
    print(f"\nTotal possible mutations found: {total_mutations}")
    print(f"Mutation types found:")
    
    # Group by type
    type_counts = {}
    for mut in mutation_list:
        mut_type = mut['type']
        type_counts[mut_type] = type_counts.get(mut_type, 0) + 1
    
    for mut_type, count in sorted(type_counts.items()):
        print(f"  - {mut_type}: {count}")
    
    # Limit to at least 100 mutations or all available
    num_mutations_to_test = max(100, total_mutations)
    if total_mutations < 100:
        print(f"\nWarning: Only {total_mutations} mutations available, need at least 100")
        num_mutations_to_test = total_mutations
    
    print(f"Will test {num_mutations_to_test} mutations")
    
    # Test report
    report = {
        'timestamp': datetime.now().isoformat(),
        'file': str(encoders_path),
        'total_mutations': total_mutations,
        'mutations_tested': 0,
        'mutations_killed': 0,
        'mutations_survived': 0,
        'errors': 0,
        'mutation_results': [],
        'mutation_types': type_counts
    }
    
    # Run tests on original
    print("\nRunning tests on original code...")
    original_pass, original_output = run_tests()
    if not original_pass:
        print("WARNING: Tests fail on original code!")
        print(original_output[:500])
    else:
        print(f"✓ Original code passes all tests")
    
    # Generate and test mutations
    print(f"\nTesting mutations...")
    
    mutation_id = 0
    tested_count = 0
    
    while mutation_id < total_mutations and tested_count < num_mutations_to_test:
        mutated_source, success = generate_mutation(original_source, mutation_id)
        
        if not success or mutated_source is None:
            mutation_id += 1
            continue
        
        # Only test if mutation is different from original
        if mutated_source == original_source:
            mutation_id += 1
            continue
        
        # Write mutated code
        encoders_path.write_text(mutated_source)
        
        # Run tests
        test_pass, test_output = run_tests()
        
        report['mutations_tested'] += 1
        tested_count += 1
        
        if test_pass:
            # Mutation survived
            report['mutations_survived'] += 1
            status = 'SURVIVED'
        else:
            # Mutation killed
            report['mutations_killed'] += 1
            status = 'KILLED'
        
        report['mutation_results'].append({
            'mutation_id': mutation_id,
            'status': status,
        })
        
        # Print progress
        if tested_count % 10 == 0:
            killed_rate = (report['mutations_killed'] / report['mutations_tested'] * 100)
            print(f"Progress: {tested_count}/{num_mutations_to_test} | Killed: {killed_rate:.1f}%")
        
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
    print(f"JSON report saved to {report_path}")
    
    # Print summary
    print("\n" + "="*70)
    print("MUTATION TESTING REPORT - encoders.py")
    print("="*70)
    print(f"File: {encoders_path}")
    print(f"Total possible mutations: {total_mutations}")
    print(f"Mutations tested: {report['mutations_tested']}")
    print(f"Mutations killed: {report['mutations_killed']}")
    print(f"Mutations survived: {report['mutations_survived']}")
    print(f"Mutation score: {mutation_score:.2f}%")
    print("="*70)
    
    # Generate HTML report
    html_report = generate_html_report(report, mutation_score, type_counts)
    html_path = Path('mutation_report.html')
    html_path.write_text(html_report, encoding='utf-8')
    print(f"HTML report saved to {html_path}")
    
    return report


def generate_html_report(report: Dict, mutation_score: float, type_counts: Dict[str, int]) -> str:
    """Generate an HTML report"""
    killed = report['mutations_killed']
    survived = report['mutations_survived']
    total = report['mutations_tested']
    
    killed_pct = (killed / total * 100) if total > 0 else 0
    survived_pct = (survived / total * 100) if total > 0 else 0
    
    # Generate type breakdown
    type_breakdown = ""
    for mut_type, count in sorted(type_counts.items()):
        type_breakdown += f"<li><strong>{mut_type}:</strong> {count} mutation points</li>\n"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mutation Testing Report - encoders.py</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            .header {{
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                color: white;
                padding: 40px;
                border-radius: 10px;
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }}
            .header h1 {{
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            .header p {{
                font-size: 1.1em;
                opacity: 0.9;
            }}
            .header .timestamp {{
                font-size: 0.9em;
                margin-top: 15px;
                opacity: 0.7;
            }}
            .summary {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .metric {{
                background-color: white;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                text-align: center;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }}
            .metric:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            }}
            .metric h3 {{
                margin: 0 0 15px 0;
                color: #7f8c8d;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .metric-value {{
                font-size: 2.5em;
                font-weight: bold;
                color: #2c3e50;
            }}
            .metric-value.killed {{
                color: #27ae60;
            }}
            .metric-value.survived {{
                color: #e74c3c;
            }}
            .metric-value.score {{
                color: #3498db;
            }}
            .chart {{
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }}
            .chart h3 {{
                margin-bottom: 20px;
                color: #2c3e50;
            }}
            .bar-container {{
                display: flex;
                height: 40px;
                border-radius: 5px;
                overflow: hidden;
                background-color: #ecf0f1;
                margin-bottom: 20px;
            }}
            .killed-bar {{
                background-color: #27ae60;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
            }}
            .survived-bar {{
                background-color: #e74c3c;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
            }}
            .details {{
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }}
            .details h3 {{
                margin-bottom: 15px;
                color: #2c3e50;
            }}
            .details ul {{
                list-style: none;
                padding-left: 0;
            }}
            .details li {{
                padding: 10px 0;
                color: #34495e;
                border-bottom: 1px solid #ecf0f1;
            }}
            .details li:last-child {{
                border-bottom: none;
            }}
            .details strong {{
                color: #2c3e50;
            }}
            .mutation-types {{
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }}
            .mutation-types h3 {{
                margin-bottom: 20px;
                color: #2c3e50;
            }}
            .mutation-types ul {{
                list-style: none;
                padding-left: 0;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
            }}
            .mutation-types li {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #3498db;
                color: #34495e;
            }}
            .interpretation {{
                background-color: #ecf7ff;
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid #3498db;
                margin-bottom: 30px;
            }}
            .interpretation h4 {{
                color: #2c3e50;
                margin-bottom: 10px;
            }}
            footer {{
                text-align: center;
                color: white;
                font-size: 0.9em;
                margin-top: 30px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🧬 Mutation Testing Report</h1>
                <p>FastAPI encoders.py Mutation Analysis</p>
                <div class="timestamp">Generated: {report['timestamp']}</div>
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
            
            <div class="interpretation">
                <h4>📊 What Does This Mean?</h4>
                <p>
                    The mutation score ({mutation_score:.1f}%) represents the percentage of mutations that were caught by the test suite. 
                    A score of 100% indicates excellent test coverage - all injected mutations were detected. 
                    Scores below 80% suggest areas where test coverage could be improved to catch edge cases.
                </p>
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
            
            <div class="mutation-types">
                <h3>Mutation Types Tested</h3>
                <ul>
                    {type_breakdown}
                </ul>
            </div>
            
            <div class="details">
                <h3>📋 Detailed Information</h3>
                <ul>
                    <li><strong>File Analyzed:</strong> {report['file']}</li>
                    <li><strong>Total Possible Mutations:</strong> {report['total_mutations']}</li>
                    <li><strong>Mutations Tested:</strong> {report['mutations_tested']}</li>
                    <li><strong>Mutations Killed:</strong> {report['mutations_killed']}</li>
                    <li><strong>Mutations Survived:</strong> {report['mutations_survived']}</li>
                    <li><strong>Mutation Score:</strong> {mutation_score:.2f}%</li>
                </ul>
            </div>
            
            <footer>
                <p>🔬 Report generated by Advanced Mutation Testing Framework</p>
                <p>Testing FastAPI encoders.py functionality</p>
            </footer>
        </div>
    </body>
    </html>
    """
    return html


if __name__ == '__main__':
    main()
