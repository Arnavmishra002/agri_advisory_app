#!/usr/bin/env python3
"""
Comprehensive Code Documentation Generator for Krishimitra AI
Automatically generates documentation for all modules and functions
"""

import os
import ast
import inspect
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import re


class CodeDocumentationGenerator:
    """Generates comprehensive documentation for Python code"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.documentation = {
            'project_info': {},
            'modules': {},
            'classes': {},
            'functions': {},
            'api_endpoints': {},
            'database_models': {},
            'services': {},
            'generated_at': datetime.now().isoformat()
        }
    
    def generate_all_documentation(self) -> Dict[str, Any]:
        """Generate comprehensive documentation for the entire project"""
        print("📚 Generating comprehensive code documentation...")
        
        # Project information
        self._extract_project_info()
        
        # Scan all Python files
        python_files = self._find_python_files()
        
        for file_path in python_files:
            self._analyze_file(file_path)
        
        # Generate API documentation
        self._generate_api_documentation()
        
        # Generate database model documentation
        self._generate_model_documentation()
        
        # Generate service documentation
        self._generate_service_documentation()
        
        print(f"✅ Documentation generated for {len(python_files)} files")
        return self.documentation
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project"""
        python_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', 'node_modules']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def _extract_project_info(self):
        """Extract project information from README and setup files"""
        readme_path = self.project_root / 'README.md'
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract project name
                name_match = re.search(r'# (.+)', content)
                if name_match:
                    self.documentation['project_info']['name'] = name_match.group(1)
                
                # Extract description
                desc_match = re.search(r'## 🌾 Overview\n\n(.+?)\n\n', content, re.DOTALL)
                if desc_match:
                    self.documentation['project_info']['description'] = desc_match.group(1).strip()
        
        # Extract from requirements
        requirements_path = self.project_root / 'requirements.txt'
        if requirements_path.exists():
            with open(requirements_path, 'r') as f:
                dependencies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                self.documentation['project_info']['dependencies'] = dependencies
    
    def _analyze_file(self, file_path: Path):
        """Analyze a Python file and extract documentation"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Get relative path for module name
            rel_path = file_path.relative_to(self.project_root)
            module_name = str(rel_path).replace('/', '.').replace('\\', '.').replace('.py', '')
            
            file_doc = {
                'path': str(rel_path),
                'module_name': module_name,
                'classes': {},
                'functions': {},
                'imports': [],
                'docstring': ast.get_docstring(tree)
            }
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        file_doc['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        file_doc['imports'].append(f"{module}.{alias.name}")
            
            # Extract classes and functions
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    class_doc = self._extract_class_info(node, module_name)
                    file_doc['classes'][node.name] = class_doc
                    self.documentation['classes'][f"{module_name}.{node.name}"] = class_doc
                
                elif isinstance(node, ast.FunctionDef):
                    func_doc = self._extract_function_info(node, module_name)
                    file_doc['functions'][node.name] = func_doc
                    self.documentation['functions'][f"{module_name}.{node.name}"] = func_doc
            
            self.documentation['modules'][module_name] = file_doc
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def _extract_class_info(self, node: ast.ClassDef, module_name: str) -> Dict[str, Any]:
        """Extract information about a class"""
        class_doc = {
            'name': node.name,
            'module': module_name,
            'docstring': ast.get_docstring(node),
            'methods': {},
            'attributes': [],
            'inheritance': [base.id for base in node.bases if isinstance(base, ast.Name)],
            'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]
        }
        
        # Extract methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_doc = self._extract_function_info(item, module_name, node.name)
                class_doc['methods'][item.name] = method_doc
        
        return class_doc
    
    def _extract_function_info(self, node: ast.FunctionDef, module_name: str, class_name: str = None) -> Dict[str, Any]:
        """Extract information about a function"""
        func_doc = {
            'name': node.name,
            'module': module_name,
            'class': class_name,
            'docstring': ast.get_docstring(node),
            'parameters': [],
            'return_annotation': None,
            'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list],
            'is_async': isinstance(node, ast.AsyncFunctionDef)
        }
        
        # Extract parameters
        for arg in node.args.args:
            param_info = {
                'name': arg.arg,
                'annotation': ast.unparse(arg.annotation) if arg.annotation else None,
                'default': None
            }
            func_doc['parameters'].append(param_info)
        
        # Extract default values
        defaults_start = len(node.args.args) - len(node.args.defaults)
        for i, default in enumerate(node.args.defaults):
            param_index = defaults_start + i
            if param_index < len(func_doc['parameters']):
                func_doc['parameters'][param_index]['default'] = ast.unparse(default)
        
        # Extract return annotation
        if node.returns:
            func_doc['return_annotation'] = ast.unparse(node.returns)
        
        return func_doc
    
    def _generate_api_documentation(self):
        """Generate API endpoint documentation"""
        api_doc = {
            'endpoints': {},
            'authentication': {},
            'response_formats': {}
        }
        
        # Analyze API views
        api_files = [
            'advisory/api/views.py',
            'advisory/api/urls.py',
            'core/urls.py'
        ]
        
        for api_file in api_files:
            file_path = self.project_root / api_file
            if file_path.exists():
                self._analyze_api_file(file_path, api_doc)
        
        self.documentation['api_endpoints'] = api_doc
    
    def _analyze_api_file(self, file_path: Path, api_doc: Dict[str, Any]):
        """Analyze API file for endpoints"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract URL patterns
            url_patterns = re.findall(r"path\('([^']+)',\s*([^,]+)", content)
            
            for pattern, view in url_patterns:
                endpoint_doc = {
                    'pattern': pattern,
                    'view': view.strip(),
                    'methods': ['GET'],  # Default, would need more analysis
                    'description': '',
                    'parameters': [],
                    'responses': {}
                }
                
                # Try to extract more information from the view
                if 'ViewSet' in view:
                    endpoint_doc['methods'] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
                
                api_doc['endpoints'][pattern] = endpoint_doc
        
        except Exception as e:
            print(f"Error analyzing API file {file_path}: {e}")
    
    def _generate_model_documentation(self):
        """Generate database model documentation"""
        model_doc = {
            'models': {},
            'relationships': {},
            'fields': {}
        }
        
        models_file = self.project_root / 'advisory/models.py'
        if models_file.exists():
            self._analyze_models_file(models_file, model_doc)
        
        self.documentation['database_models'] = model_doc
    
    def _analyze_models_file(self, file_path: Path, model_doc: Dict[str, Any]):
        """Analyze models file for database models"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name.endswith('Model'):
                    model_info = {
                        'name': node.name,
                        'docstring': ast.get_docstring(node),
                        'fields': {},
                        'relationships': [],
                        'meta': {}
                    }
                    
                    # Extract fields
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    field_name = target.id
                                    field_info = {
                                        'name': field_name,
                                        'type': ast.unparse(item.value) if hasattr(item, 'value') else 'Unknown'
                                    }
                                    model_info['fields'][field_name] = field_info
                    
                    model_doc['models'][node.name] = model_info
        
        except Exception as e:
            print(f"Error analyzing models file {file_path}: {e}")
    
    def _generate_service_documentation(self):
        """Generate service documentation"""
        service_doc = {
            'services': {},
            'dependencies': {},
            'interfaces': {}
        }
        
        services_dir = self.project_root / 'advisory/services'
        if services_dir.exists():
            for service_file in services_dir.glob('*.py'):
                if service_file.name != '__init__.py':
                    self._analyze_service_file(service_file, service_doc)
        
        self.documentation['services'] = service_doc
    
    def _analyze_service_file(self, file_path: Path, service_doc: Dict[str, Any]):
        """Analyze service file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and 'Service' in node.name:
                    service_info = {
                        'name': node.name,
                        'file': str(file_path.relative_to(self.project_root)),
                        'docstring': ast.get_docstring(node),
                        'methods': {},
                        'dependencies': []
                    }
                    
                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = self._extract_function_info(item, str(file_path.stem))
                            service_info['methods'][item.name] = method_info
                    
                    service_doc['services'][node.name] = service_info
        
        except Exception as e:
            print(f"Error analyzing service file {file_path}: {e}")
    
    def generate_markdown_documentation(self, output_file: str = 'CODE_DOCUMENTATION.md') -> str:
        """Generate markdown documentation"""
        output_path = self.project_root / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 📚 Krishimitra AI - Code Documentation\n\n")
            f.write(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            
            # Project overview
            f.write("## 🌾 Project Overview\n\n")
            project_info = self.documentation['project_info']
            f.write(f"**Name:** {project_info.get('name', 'Krishimitra AI')}\n\n")
            f.write(f"**Description:** {project_info.get('description', 'Agricultural Advisory System')}\n\n")
            
            # Architecture overview
            f.write("## 🏗️ Architecture Overview\n\n")
            f.write("### Core Components\n\n")
            f.write("- **Django Backend**: REST API with Django REST Framework\n")
            f.write("- **AI Services**: Multiple AI integrations (Ollama, Google AI)\n")
            f.write("- **Government APIs**: Real-time data from Indian government sources\n")
            f.write("- **Database Models**: User management, crop data, chat history\n")
            f.write("- **Performance Optimization**: Caching, query optimization, monitoring\n\n")
            
            # Modules documentation
            f.write("## 📦 Modules\n\n")
            for module_name, module_info in self.documentation['modules'].items():
                f.write(f"### {module_name}\n\n")
                if module_info['docstring']:
                    f.write(f"{module_info['docstring']}\n\n")
                
                # Classes
                if module_info['classes']:
                    f.write("**Classes:**\n")
                    for class_name, class_info in module_info['classes'].items():
                        f.write(f"- `{class_name}`: {class_info['docstring'] or 'No description'}\n")
                    f.write("\n")
                
                # Functions
                if module_info['functions']:
                    f.write("**Functions:**\n")
                    for func_name, func_info in module_info['functions'].items():
                        f.write(f"- `{func_name}`: {func_info['docstring'] or 'No description'}\n")
                    f.write("\n")
            
            # API Documentation
            f.write("## 🌐 API Endpoints\n\n")
            api_endpoints = self.documentation['api_endpoints']
            if api_endpoints['endpoints']:
                f.write("| Endpoint | Methods | Description |\n")
                f.write("|----------|---------|-------------|\n")
                
                for pattern, endpoint_info in api_endpoints['endpoints'].items():
                    methods = ', '.join(endpoint_info['methods'])
                    description = endpoint_info['description'] or 'No description'
                    f.write(f"| `{pattern}` | {methods} | {description} |\n")
                f.write("\n")
            
            # Database Models
            f.write("## 🗄️ Database Models\n\n")
            models = self.documentation['database_models']['models']
            if models:
                for model_name, model_info in models.items():
                    f.write(f"### {model_name}\n\n")
                    if model_info['docstring']:
                        f.write(f"{model_info['docstring']}\n\n")
                    
                    if model_info['fields']:
                        f.write("**Fields:**\n")
                        for field_name, field_info in model_info['fields'].items():
                            f.write(f"- `{field_name}`: {field_info['type']}\n")
                        f.write("\n")
            
            # Services
            f.write("## ⚙️ Services\n\n")
            services = self.documentation['services']['services']
            if services:
                for service_name, service_info in services.items():
                    f.write(f"### {service_name}\n\n")
                    if service_info['docstring']:
                        f.write(f"{service_info['docstring']}\n\n")
                    
                    if service_info['methods']:
                        f.write("**Methods:**\n")
                        for method_name, method_info in service_info['methods'].items():
                            f.write(f"- `{method_name}`: {method_info['docstring'] or 'No description'}\n")
                        f.write("\n")
            
            # Development Guidelines
            f.write("## 🛠️ Development Guidelines\n\n")
            f.write("### Code Style\n")
            f.write("- Follow PEP 8 guidelines\n")
            f.write("- Use type hints for function parameters and return values\n")
            f.write("- Write comprehensive docstrings for all functions and classes\n")
            f.write("- Use meaningful variable and function names\n\n")
            
            f.write("### Testing\n")
            f.write("- Write unit tests for all functions\n")
            f.write("- Use pytest for test execution\n")
            f.write("- Maintain test coverage above 80%\n")
            f.write("- Test both success and error cases\n\n")
            
            f.write("### Performance\n")
            f.write("- Use caching for expensive operations\n")
            f.write("- Optimize database queries with select_related and prefetch_related\n")
            f.write("- Monitor API response times\n")
            f.write("- Use async operations for I/O bound tasks\n\n")
            
            # Dependencies
            f.write("## 📋 Dependencies\n\n")
            dependencies = project_info.get('dependencies', [])
            if dependencies:
                f.write("### Core Dependencies\n\n")
                for dep in dependencies[:10]:  # Show first 10
                    f.write(f"- {dep}\n")
                f.write("\n")
            
            f.write("---\n\n")
            f.write("*This documentation is automatically generated. Please update docstrings in the code for better documentation.*\n")
        
        return str(output_path)
    
    def generate_json_documentation(self, output_file: str = 'code_documentation.json') -> str:
        """Generate JSON documentation"""
        output_path = self.project_root / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.documentation, f, indent=2, ensure_ascii=False)
        
        return str(output_path)


def generate_project_documentation(project_root: str = '.') -> Tuple[str, str]:
    """Generate comprehensive project documentation"""
    generator = CodeDocumentationGenerator(project_root)
    
    # Generate documentation
    documentation = generator.generate_all_documentation()
    
    # Generate output files
    markdown_file = generator.generate_markdown_documentation()
    json_file = generator.generate_json_documentation()
    
    return markdown_file, json_file


if __name__ == '__main__':
    markdown_file, json_file = generate_project_documentation()
    print(f"📄 Markdown documentation: {markdown_file}")
    print(f"📄 JSON documentation: {json_file}")







