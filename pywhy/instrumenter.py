"""
Fixed AST-based source code instrumenter for Python Whyline.
This version properly handles AST contexts and node transformation.
"""
from enum import Enum
import json
import ast
import sys
from typing import Dict, Any, List
from dataclasses import dataclass, field
import copy


@dataclass
class InstrumentationInfo:
    """Static metadata about where instrumentation code was inserted during AST transformation.
    
    Created at compile/instrumentation time to track what instrumentation points were added.
    Contains location information but no runtime execution data.
    """
    event_id: int
    line_no: int
    col_offset: int
    filename: str
    event_type: str
    description: str = ""


class ContextFixer(ast.NodeTransformer):
    """Fix AST contexts to ensure proper Load/Store usage"""
    
    def visit_Name(self, node):
        # When we copy nodes for tracing, we need to ensure they have Load context
        if hasattr(node, 'ctx') and isinstance(node.ctx, ast.Store):
            # Create a new node with Load context for expressions
            new_node = ast.Name(id=node.id, ctx=ast.Load())
            return ast.copy_location(new_node, node)
        return node
    
    def visit_Attribute(self, node):
        # Same for attributes
        self.generic_visit(node)
        if hasattr(node, 'ctx') and isinstance(node.ctx, ast.Store):
            new_node = ast.Attribute(
                value=node.value,
                attr=node.attr,
                ctx=ast.Load()
            )
            return ast.copy_location(new_node, node)
        return node
    
    def visit_Subscript(self, node):
        # Same for subscripts
        self.generic_visit(node)
        if hasattr(node, 'ctx') and isinstance(node.ctx, ast.Store):
            new_node = ast.Subscript(
                value=node.value,
                slice=node.slice,
                ctx=ast.Load()
            )
            return ast.copy_location(new_node, node)
        return node


class WhylineInstrumenter(ast.NodeTransformer):
    """Fixed AST transformer that properly handles contexts"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.event_id = 0
        self.instrumentation_points: List[InstrumentationInfo] = []
        self.context_fixer = ContextFixer()
        
    def get_next_event_id(self) -> int:
        """Get next unique event ID"""
        self.event_id += 1
        return self.event_id
    
    def create_tracer_call(self, event_type: str, node: ast.AST, 
                          extra_args: List[ast.expr] = None) -> ast.Call:
        """Create a call to the tracer's record_event method"""
        event_id = self.get_next_event_id()
        
        # Record instrumentation point
        self.instrumentation_points.append(InstrumentationInfo(
            event_id=event_id,
            line_no=getattr(node, 'lineno', 0),
            col_offset=getattr(node, 'col_offset', 0),
            filename=self.filename,
            event_type=event_type
        ))
        
        args = [
            ast.Constant(value=event_id),
            ast.Constant(value=self.filename),
            ast.Constant(value=getattr(node, 'lineno', 0)),
            ast.Constant(value=event_type)
        ]
        
        if extra_args:
            args.extend(extra_args)
        
        call = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='_whyline_tracer', ctx=ast.Load()),
                attr='record_event',
                ctx=ast.Load()
            ),
            args=args,
            keywords=[]
        )
        
        return ast.copy_location(call, node)
    
    def safe_copy_for_expression(self, node: ast.AST) -> ast.AST:
        """Safely copy a node for use in expressions with proper context"""
        copied = copy.deepcopy(node)
        fixed = self.context_fixer.visit(copied)
        return fixed
    
    def visit_Module(self, node: ast.Module) -> ast.Module:
        """Add tracer import to the module"""
        self.generic_visit(node)
        
        # Add import for the tracer
        import_stmt = ast.ImportFrom(
            module='pywhy.tracer',
            names=[ast.alias(name='get_tracer', asname=None)],
            level=0,
            lineno=1,
            col_offset=0
        )
        
        # Add tracer assignment
        tracer_assign = ast.Assign(
            targets=[ast.Name(id='_whyline_tracer', ctx=ast.Store())],
            value=ast.Call(
                func=ast.Name(id='get_tracer', ctx=ast.Load()),
                args=[],
                keywords=[]
            ),
            lineno=1,
            col_offset=0
        )
        
        # Insert at the beginning
        node.body.insert(0, tracer_assign)
        node.body.insert(0, import_stmt)
        
        return node
    
    def visit_Assign(self, node: ast.Assign) -> List[ast.stmt]:
        """Instrument variable assignments"""
        # First, transform children
        self.generic_visit(node)
        
        instrumented_stmts = []
        
        # Keep the original assignment
        instrumented_stmts.append(node)
        
        # Add tracing for each target
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Simple variable assignment: x = value
                
                # Create tracer call arguments
                args = [
                    ast.Constant(value='var_name'),
                    ast.Constant(value=target.id),
                    ast.Constant(value='value'),
                    ast.Name(id=target.id, ctx=ast.Load())  # Fresh node with Load context
                ]
                
                tracer_call = self.create_tracer_call('assign', node, args)
                instrumented_stmts.append(ast.Expr(value=tracer_call))
                
            elif isinstance(target, ast.Attribute):
                # Attribute assignment: obj.attr = value
                
                # Safely copy the object reference for the tracer call
                obj_ref = self.safe_copy_for_expression(target.value)
                
                args = [
                    ast.Constant(value='obj_attr'),
                    ast.Constant(value=target.attr),
                    ast.Constant(value='obj'),
                    obj_ref,
                    ast.Constant(value='value'),
                    self.safe_copy_for_expression(node.value)
                ]
                
                tracer_call = self.create_tracer_call('attr_assign', node, args)
                instrumented_stmts.append(ast.Expr(value=tracer_call))
                
            elif isinstance(target, ast.Subscript):
                # Subscript assignment: arr[index] = value or arr[start:end] = value
                
                container_ref = self.safe_copy_for_expression(target.value)
                value_ref = self.safe_copy_for_expression(node.value)
                
                # Handle different types of subscripts
                if isinstance(target.slice, ast.Slice):
                    # Slice assignment: arr[start:end] = value
                    args = [
                        ast.Constant(value='container'),
                        container_ref,
                        ast.Constant(value='slice_type'),
                        ast.Constant(value='slice'),
                        ast.Constant(value='lower'),
                        target.slice.lower if target.slice.lower else ast.Constant(value=None),
                        ast.Constant(value='upper'),
                        target.slice.upper if target.slice.upper else ast.Constant(value=None),
                        ast.Constant(value='step'),
                        target.slice.step if target.slice.step else ast.Constant(value=None),
                        ast.Constant(value='value'),
                        value_ref
                    ]
                    tracer_call = self.create_tracer_call('slice_assign', node, args)
                else:
                    # Simple subscript assignment: arr[index] = value
                    index_ref = self.safe_copy_for_expression(target.slice)
                    args = [
                        ast.Constant(value='container'),
                        container_ref,
                        ast.Constant(value='index'),
                        index_ref,
                        ast.Constant(value='value'),
                        value_ref
                    ]
                    tracer_call = self.create_tracer_call('subscript_assign', node, args)
                
                instrumented_stmts.append(ast.Expr(value=tracer_call))
        
        return instrumented_stmts
    
    def visit_AugAssign(self, node: ast.AugAssign) -> List[ast.stmt]:
        """Instrument augmented assignments (+=, -=, etc.)"""
        # First, transform children
        self.generic_visit(node)
        
        instrumented_stmts = []
        
        # Keep the original assignment
        instrumented_stmts.append(node)
        
        # Add tracing for the target
        if isinstance(node.target, ast.Name):
            # Simple variable: x += value
            
            args = [
                ast.Constant(value='var_name'),
                ast.Constant(value=node.target.id),
                ast.Constant(value='value'),
                ast.Name(id=node.target.id, ctx=ast.Load())  # Value after assignment
            ]
            
            tracer_call = self.create_tracer_call('aug_assign', node, args)
            instrumented_stmts.append(ast.Expr(value=tracer_call))
            
        elif isinstance(node.target, ast.Attribute):
            # Attribute assignment: obj.attr += value
            
            obj_ref = self.safe_copy_for_expression(node.target.value)
            
            args = [
                ast.Constant(value='obj_attr'),
                ast.Constant(value=node.target.attr),
                ast.Constant(value='obj'),
                obj_ref,
                ast.Constant(value='value'),
                self.safe_copy_for_expression(node.target)
            ]
            
            tracer_call = self.create_tracer_call('aug_assign', node, args)
            instrumented_stmts.append(ast.Expr(value=tracer_call))
            
        elif isinstance(node.target, ast.Subscript):
            # Subscript assignment: arr[index] += value
            
            container_ref = self.safe_copy_for_expression(node.target.value)
            index_ref = self.safe_copy_for_expression(node.target.slice)
            
            args = [
                ast.Constant(value='container'),
                container_ref,
                ast.Constant(value='index'),
                index_ref,
                ast.Constant(value='value'),
                self.safe_copy_for_expression(node.target)
            ]
            
            tracer_call = self.create_tracer_call('aug_assign', node, args)
            instrumented_stmts.append(ast.Expr(value=tracer_call))
        
        return instrumented_stmts
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Instrument function definitions"""
        # Transform function body first
        self.generic_visit(node)
        
        # Create argument list for tracing
        arg_names = [ast.Name(id=arg.arg, ctx=ast.Load()) for arg in node.args.args]
        
        args = [
            ast.Constant(value='func_name'),
            ast.Constant(value=node.name),
            ast.Constant(value='args'),
            ast.List(elts=arg_names, ctx=ast.Load())
        ]
        
        # Add function entry tracing
        entry_tracer = self.create_tracer_call('function_entry', node, args)
        
        # Insert at the beginning of function body
        node.body.insert(0, ast.Expr(value=entry_tracer))
        
        return node
    
    def visit_Return(self, node: ast.Return) -> List[ast.stmt]:
        """Instrument return statements"""
        self.generic_visit(node)
        
        # Handle return value
        if node.value is not None:
            return_value = self.safe_copy_for_expression(node.value)
        else:
            return_value = ast.Constant(value=None)
        
        args = [
            ast.Constant(value='value'),
            return_value
        ]
        
        # Add return tracing
        tracer_call = self.create_tracer_call('return', node, args)
        
        return [ast.Expr(value=tracer_call), node]
    
    def visit_If(self, node: ast.If) -> ast.If:
        """Instrument if statements"""
        # Transform children first
        self.generic_visit(node)
        
        # Add condition tracing
        condition_copy = self.safe_copy_for_expression(node.test)
        
        condition_args = [
            ast.Constant(value='test'),
            condition_copy
        ]
        
        condition_tracer = self.create_tracer_call('condition', node, condition_args)
        
        # Add branch tracing to if body
        if_args = [
            ast.Constant(value='taken'),
            ast.Constant(value='if')
        ]
        
        if_tracer = self.create_tracer_call('branch', node, if_args)
        node.body.insert(0, ast.Expr(value=if_tracer))
        
        # Add branch tracing to else body
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # elif case - will be handled by recursive visit
                pass
            else:
                # else case
                else_args = [
                    ast.Constant(value='taken'),
                    ast.Constant(value='else')
                ]
                
                else_tracer = self.create_tracer_call('branch', node, else_args)
                node.orelse.insert(0, ast.Expr(value=else_tracer))
        
        return node
    
    def visit_For(self, node: ast.For) -> ast.For:
        """Instrument for loops"""
        self.generic_visit(node)
        
        # Get target variable name
        if isinstance(node.target, ast.Name):
            target_name = node.target.id
            target_ref = ast.Name(id=target_name, ctx=ast.Load())
        else:
            target_name = str(node.target)
            target_ref = ast.Constant(value=target_name)
        
        args = [
            ast.Constant(value='target'),
            ast.Constant(value=target_name),
            ast.Constant(value='iter_value'),
            target_ref
        ]
        
        # Add loop iteration tracing
        loop_tracer = self.create_tracer_call('loop_iteration', node, args)
        node.body.insert(0, ast.Expr(value=loop_tracer))
        
        return node
    
    def visit_While(self, node: ast.While) -> ast.While:
        """Instrument while loops"""
        self.generic_visit(node)
        
        # Copy the test condition
        test_copy = self.safe_copy_for_expression(node.test)
        
        args = [
            ast.Constant(value='test'),
            test_copy
        ]
        
        # Add while condition tracing
        while_tracer = self.create_tracer_call('while_condition', node, args)
        node.body.insert(0, ast.Expr(value=while_tracer))
        
        return node
    
    def visit_Call(self, node: ast.Call) -> ast.Call:
        """Instrument function calls (basic version)"""
        self.generic_visit(node)
        
        # For now, just return the node as-is
        # Advanced call instrumentation would require more complex transformation
        return node


def instrument_code(source_code: str, filename: str = "<string>") -> str:
    """Instrument Python source code with Whyline tracing"""
    
    # Parse the source code
    try:
        tree = ast.parse(source_code, filename=filename)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in source code: {e}")
    
    # Transform the AST
    instrumenter = WhylineInstrumenter(filename)
    instrumented_tree = instrumenter.visit(tree)
    
    # Fix missing line numbers and column offsets
    ast.fix_missing_locations(instrumented_tree)
    
    # Convert back to source code
    try:
        return ast.unparse(instrumented_tree)
    except Exception as e:
        raise ValueError(f"Failed to unparse instrumented AST: {e}")
    
def exec_instrumented(source_code: str, globals_dict: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute instrumented Python code"""
    
    if globals_dict is None:
        globals_dict = {}
    
    # Add the tracer to globals
    from .tracer import get_tracer
    globals_dict['_whyline_tracer'] = get_tracer()
    
    # Add built-ins
    import builtins
    globals_dict['__builtins__'] = builtins
    
    # Set __name__ to __main__ to ensure if __name__ == "__main__" blocks execute
    globals_dict['__name__'] = '__main__'
    
    # Set __file__ to avoid NameError if the code references it
    globals_dict['__file__'] = '<string>'
    
    # Handle __name__ == "__main__" guards by replacing them with if True:
    code_to_run = source_code
    if 'if __name__ == "__main__":' in code_to_run:
        code_to_run = code_to_run.replace('if __name__ == "__main__":', 'if True:')
        print("(Modified __name__ check to run main code)")
 

    try:
        if sys.version_info < (3, 9):
            raise RuntimeError("AST-based instrumentation requires Python 3.9 or higher.")
            
        # Use string-based approach for Python 3.9+
        instrumented_code = instrument_code(code_to_run, "<string>")
        exec(instrumented_code, globals_dict)
                
    except Exception as e:
        print(f"Error during instrumentation: {e}")
        print("Falling back to original code execution...")
        exec(code_to_run, globals_dict, globals_dict)
    
    return globals_dict

def instrument_file(source_file: str, output_file: str = None) -> str:
    """Instrument a Python file with Whyline tracing"""
    
    with open(source_file, 'r') as f:
        source_code = f.read()
    
    try:
        instrumented_code = instrument_code(source_code, source_file)
        
        if output_file:
            with open(output_file, 'w') as f:
                if isinstance(instrumented_code, str):
                    f.write(instrumented_code)
                else:
                    f.write("# Compiled code object - cannot write to file\n")
                    f.write(f"# Original file: {source_file}\n")
        
        return instrumented_code
        
    except Exception as e:
        print(f"Error instrumenting file {source_file}: {e}")
        return source_code


class EventType(Enum):
    """Types of trace events"""
    ASSIGN = "assign"
    ATTR_ASSIGN = "attr_assign"  
    SUBSCRIPT_ASSIGN = "subscript_assign"
    SLICE_ASSIGN = "slice_assign"
    AUG_ASSIGN = "aug_assign"
    FUNCTION_ENTRY = "function_entry"
    RETURN = "return"
    CONDITION = "condition"
    BRANCH = "branch"
    LOOP_ITERATION = "loop_iteration"
    WHILE_CONDITION = "while_condition"
    CALL = "call"


@dataclass
class TraceEvent:
    """Runtime data captured when instrumented code executes.
    
    Created at runtime when instrumented code runs to store actual execution traces
    with variable values, function arguments, and other dynamic execution data.
    """
    event_id: int
    filename: str
    line_no: int
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'event_id': self.event_id,
            'filename': self.filename,
            'line_no': self.line_no,
            'event_type': self.event_type,
            'data': self.data
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


