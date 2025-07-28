"""
Fixed AST-based source code instrumenter for Python Whyline.
This version properly handles AST contexts and node transformation.
"""
from .events import EventType, TraceEvent
import ast
import sys
from typing import Dict, Any, List
from dataclasses import dataclass, field
import copy
from .tracer import get_tracer
import builtins

@dataclass
class InstrumentationInfo:
    """Static metadata about where instrumentation code was inserted during AST transformation.
    
    Created at compile/instrumentation time to track what instrumentation points were added.
    Contains location information but no runtime execution data.
    """
    event_id: int
    lineno: int
    col_offset: int
    filename: str
    event_type: str
    description: str = ""


class VariableCollector(ast.NodeVisitor):
    """Collect variable names read in an expression"""
    
    def __init__(self):
        self.variables = set()
    
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.variables.add(node.id)
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        # For obj.attr, we want to track 'obj' as a read variable
        self.visit(node.value)
    
    def visit_Subscript(self, node):
        # For arr[index], we want to track both 'arr' and 'index' variables
        self.visit(node.value)
        self.visit(node.slice)
    
    @classmethod
    def get_read_variables(cls, node: ast.AST) -> list:
        """Get list of variables read in an expression"""
        collector = cls()
        collector.visit(node)
        return sorted(list(collector.variables))


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
    
    def create_tracer_call(self, event_type: EventType, node: ast.AST, 
                          extra_args: List[ast.expr] = None) -> ast.Call:
        """Create a call to the tracer's record_event method"""
        event_id = self.get_next_event_id()
        
        # Record instrumentation point
        self.instrumentation_points.append(InstrumentationInfo(
            event_id=event_id,
            lineno=getattr(node, 'lineno', 0),
            col_offset=getattr(node, 'col_offset', 0),
            filename=self.filename,
            event_type=event_type
        ))
        
        args = [
            ast.Constant(value=event_id),
            ast.Constant(value=self.filename),
            ast.Constant(value=getattr(node, 'lineno', 0)),
            ast.Constant(value=event_type.value)  # Convert EventType enum to string
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
    
    def add_deps_to_args(self, node: ast.AST, args: List[ast.expr]) -> List[ast.expr]:
        """Add variable dependencies to tracer call arguments"""
        deps = VariableCollector.get_read_variables(node)
        
        if deps:
            args.extend([
                ast.Constant(value='deps'),
                ast.List(elts=[ast.Constant(value=var) for var in deps], ctx=ast.Load())
            ])
        
        return args
    

    # === AST Node Visitors ===
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
                
                # Add variable dependencies from the assignment value
                args = self.add_deps_to_args(node.value, args)
                
                tracer_call = self.create_tracer_call(EventType.ASSIGN, node, args)
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
                
                # Add variable dependencies from both object reference and assignment value
                deps_from_obj = VariableCollector.get_read_variables(target.value)
                deps_from_value = VariableCollector.get_read_variables(node.value)
                all_deps = sorted(list(set(deps_from_obj + deps_from_value)))
                
                if all_deps:
                    args.extend([
                        ast.Constant(value='deps'),
                        ast.List(elts=[ast.Constant(value=var) for var in all_deps], ctx=ast.Load())
                    ])
                
                tracer_call = self.create_tracer_call(EventType.ATTR_ASSIGN, node, args)
                instrumented_stmts.append(ast.Expr(value=tracer_call))
                
            elif isinstance(target, ast.Subscript):
                # Subscript assignment: arr[index] = value or arr[start:end] = value
                
                container_ref = self.safe_copy_for_expression(target.value)
                value_ref = self.safe_copy_for_expression(node.value)
                
                # Collect dependencies from all parts
                deps_from_container = VariableCollector.get_read_variables(target.value)
                deps_from_value = VariableCollector.get_read_variables(node.value)
                
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
                    
                    # Add slice bounds dependencies
                    deps_from_slice = []
                    if target.slice.lower:
                        deps_from_slice.extend(VariableCollector.get_read_variables(target.slice.lower))
                    if target.slice.upper:
                        deps_from_slice.extend(VariableCollector.get_read_variables(target.slice.upper))
                    if target.slice.step:
                        deps_from_slice.extend(VariableCollector.get_read_variables(target.slice.step))
                    
                    all_deps = sorted(list(set(deps_from_container + deps_from_value + deps_from_slice)))
                    
                    tracer_call = self.create_tracer_call(EventType.SLICE_ASSIGN, node, args)
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
                    
                    deps_from_index = VariableCollector.get_read_variables(target.slice)
                    all_deps = sorted(list(set(deps_from_container + deps_from_value + deps_from_index)))
                    
                    tracer_call = self.create_tracer_call(EventType.SUBSCRIPT_ASSIGN, node, args)
                
                # Add dependencies to args
                if all_deps:
                    args.extend([
                        ast.Constant(value='deps'),
                        ast.List(elts=[ast.Constant(value=var) for var in all_deps], ctx=ast.Load())
                    ])

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
            
            # Add dependencies: both the target variable (being read) and the value expression
            deps_from_target = [node.target.id]  # The target variable is read in augmented assignment
            deps_from_value = VariableCollector.get_read_variables(node.value)
            all_deps = sorted(list(set(deps_from_target + deps_from_value)))
            
            if all_deps:
                args.extend([
                    ast.Constant(value='deps'),
                    ast.List(elts=[ast.Constant(value=var) for var in all_deps], ctx=ast.Load())
                ])

            tracer_call = self.create_tracer_call(EventType.AUG_ASSIGN, node, args)
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
            
            # Add dependencies from object, target attribute, and value
            deps_from_obj = VariableCollector.get_read_variables(node.target.value)
            deps_from_target = VariableCollector.get_read_variables(node.target)  # obj.attr is read
            deps_from_value = VariableCollector.get_read_variables(node.value)
            all_deps = sorted(list(set(deps_from_obj + deps_from_target + deps_from_value)))
            
            if all_deps:
                args.extend([
                    ast.Constant(value='deps'),
                    ast.List(elts=[ast.Constant(value=var) for var in all_deps], ctx=ast.Load())
                ])

            tracer_call = self.create_tracer_call(EventType.AUG_ASSIGN, node, args)
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
            
            # Add dependencies from container, index, target subscript, and value
            deps_from_container = VariableCollector.get_read_variables(node.target.value)
            deps_from_index = VariableCollector.get_read_variables(node.target.slice)
            deps_from_target = VariableCollector.get_read_variables(node.target)  # arr[index] is read
            deps_from_value = VariableCollector.get_read_variables(node.value)
            all_deps = sorted(list(set(deps_from_container + deps_from_index + deps_from_target + deps_from_value)))
            
            if all_deps:
                args.extend([
                    ast.Constant(value='deps'),
                    ast.List(elts=[ast.Constant(value=var) for var in all_deps], ctx=ast.Load())
                ])
            
            tracer_call = self.create_tracer_call(EventType.AUG_ASSIGN, node, args)
            instrumented_stmts.append(ast.Expr(value=tracer_call))
        
        return instrumented_stmts
    
    ### Function Instrumentation ###
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
        entry_tracer = self.create_tracer_call(EventType.FUNCTION_ENTRY, node, args)
        
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
        tracer_call = self.create_tracer_call(EventType.RETURN, node, args)
        
        return [ast.Expr(value=tracer_call), node]
   
    def visit_Call(self, node: ast.Call) -> ast.Call:
        """Instrument function calls (basic version)"""
        self.generic_visit(node)
        
        return node 
    
    ### Control Flow ###
    def visit_If(self, node: ast.If) -> List[ast.stmt]:
        """Instrument if statements with integrated condition and branch logic"""
        # Transform children first
        self.generic_visit(node)
        
        # Get condition as string for debugging
        condition_str = ast.unparse(node.test) if hasattr(ast, 'unparse') else str(node.test)
        condition_copy = self.safe_copy_for_expression(node.test)
        
        # Track variable reads in the condition BEFORE the if statement
        instrumented_stmts = []
        
        # Add branch tracing to if body (if condition is true)
        if_args = [
            ast.Constant(value='condition'),
            ast.Constant(value=condition_str),
            ast.Constant(value='result'),
            condition_copy,
            ast.Constant(value='decision'),
            ast.Constant(value='if_block')
        ]
        
        # Add dependencies from the condition
        if_args = self.add_deps_to_args(node.test, if_args)
        
        if_tracer = self.create_tracer_call(EventType.BRANCH, node, if_args)
        node.body.insert(0, ast.Expr(value=if_tracer))
        
        # Handle else/skip cases
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # elif case - add branch event for when this condition is false and goes to elif
                elif_args = [
                    ast.Constant(value='condition'),
                    ast.Constant(value=condition_str),
                    ast.Constant(value='result'),
                    condition_copy,
                    ast.Constant(value='decision'),
                    ast.Constant(value='elif_block')
                ]
                
                # Add dependencies from the condition
                elif_args = self.add_deps_to_args(node.test, elif_args)
                
                elif_tracer = self.create_tracer_call(EventType.BRANCH, node, elif_args)
                node.orelse.insert(0, ast.Expr(value=elif_tracer))
            else:
                # explicit else case (condition is false, else block taken)
                else_args = [
                    ast.Constant(value='condition'),
                    ast.Constant(value=condition_str),
                    ast.Constant(value='result'),
                    condition_copy,
                    ast.Constant(value='decision'),
                    ast.Constant(value='else_block')
                ]
                
                # Add dependencies from the condition
                else_args = self.add_deps_to_args(node.test, else_args)
                
                else_tracer = self.create_tracer_call(EventType.BRANCH, node, else_args)
                node.orelse.insert(0, ast.Expr(value=else_tracer))
        else:
            # No else block - create skip branch for when condition is false
            skip_args = [
                ast.Constant(value='condition'),
                ast.Constant(value=condition_str),
                ast.Constant(value='result'),
                condition_copy,
                ast.Constant(value='decision'),
                ast.Constant(value='skip_block')
            ]
            
            # Add dependencies from the condition
            skip_args = self.add_deps_to_args(node.test, skip_args)
            
            skip_tracer = self.create_tracer_call(EventType.BRANCH, node, skip_args)
            node.orelse = [ast.Expr(value=skip_tracer)]
        
        # Add the instrumented if statement
        instrumented_stmts.append(node)
        return instrumented_stmts
    
    ### Loop Instrumentation ###
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
        loop_tracer = self.create_tracer_call(EventType.LOOP_ITERATION, node, args)
        node.body.insert(0, ast.Expr(value=loop_tracer))
        
        return node
    
    def visit_While(self, node: ast.While) -> ast.While:
        """Instrument while loops"""
        self.generic_visit(node)
        
        # Copy the test condition
        test_copy = self.safe_copy_for_expression(node.test)
        
        # Get condition as string for debugging
        condition_str = ast.unparse(node.test) if hasattr(ast, 'unparse') else str(node.test)
        
        args = [
            ast.Constant(value='condition'),
            ast.Constant(value=condition_str),
            ast.Constant(value='result'),
            test_copy
        ]
        
        # Add dependencies from the condition
        args = self.add_deps_to_args(node.test, args)
        
        # Add while condition tracing
        while_tracer = self.create_tracer_call(EventType.WHILE_CONDITION, node, args)
        node.body.insert(0, ast.Expr(value=while_tracer))
        
        return node
    

# Helper function to instrument code
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
    globals_dict['_whyline_tracer'] = get_tracer()
    
    # Add built-ins
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






