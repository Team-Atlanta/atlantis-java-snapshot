"""
Grammarinator Wrapper

A generic wrapper for generating content using grammarinator without spawning a new process each time.
This wrapper maintains multiple GeneratorTool instances throughout the process
lifecycle for efficient generation of content from any grammarinator-based generator.
"""

import argparse
import json
import random
import threading
from os.path import abspath, exists

from grammarinator.runtime import RuleSize
from grammarinator.tool import DefaultGeneratorFactory, DefaultPopulation, GeneratorTool


class GrammarinatorWrapper:
    """
    A wrapper that maintains multiple GeneratorTool instances throughout
    the lifecycle of the process, with separate instances registered by name.
    """
    _generator_tools = {}
    _counters = {}
    _lock = threading.Lock()
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GrammarinatorWrapper, cls).__new__(cls)
        return cls._instance

    def register(self, name, generator_class, args=None, rule=None, depth=20):
        """
        Register a new generator tool with the specified name.
        
        Args:
            name (str): Name to register the generator under
            generator_class: The generator class to use
            args: Optional list of command-line style arguments
            rule (str): Optional rule name to start generation from
            depth (int): Maximum recursion depth during generation
            
        Returns:
            bool: True if registration was successful, False if name already exists
        """
        with self._lock:
            if name in self._generator_tools:
                return False
            
            processed_args = self._parse_args(args, generator_class, rule, depth)
            generator_tool = self._create_generator_tool(processed_args)
            
            self._generator_tools[name] = generator_tool
            self._counters[name] = 0
            return True
    
    def get_registered(self, name):
        """Get a registered generator by name, or None if not found."""
        with self._lock:
            if name not in self._generator_tools:
                return None
            return self._generator_tools[name]
    
    def is_registered(self, name):
        """Check if a generator name is registered."""
        with self._lock:
            return name in self._generator_tools

    def _parse_args(self, args=None, generator_class=None, rule=None, depth=20):
        """
        Parse command line arguments or use provided args.
        
        Args:
            args: Optional list of command-line style arguments
            generator_class: The generator class to use if not using arg parsing
            rule: Optional rule name to start generation from
            depth: Maximum recursion depth during generation
            
        Returns:
            Parsed arguments object
        """
        # Create parser similar to grammarinator-generate
        parser = argparse.ArgumentParser(prog='grammarinator-wrapper', description='Grammarinator Generic Wrapper')
        
        # Generator settings
        parser.add_argument('generator', metavar='NAME',
                            help='Reference to the generator (in package.module.class format).')
        parser.add_argument('-r', '--rule', metavar='NAME',
                            help='Name of the rule to start generation from.')
        parser.add_argument('-m', '--model', metavar='NAME', default='grammarinator.runtime.DefaultModel',
                            help='Reference to the decision model (default: %(default)s).')
        parser.add_argument('-l', '--listener', metavar='NAME', action='append', default=[],
                            help='Reference to a listener.')
        parser.add_argument('-t', '--transformer', metavar='NAME', action='append', default=[],
                            help='Reference to a transformer to postprocess the generated tree.')
        parser.add_argument('-s', '--serializer', metavar='NAME',
                            help='Reference to a seralizer.')
        parser.add_argument('-d', '--max-depth', default=20, type=int, metavar='NUM',
                            help='Maximum recursion depth during generation (default: %(default)d).')
        parser.add_argument('--max-tokens', default=RuleSize.max.tokens, type=int, metavar='NUM',
                            help='Maximum token number during generation.')
        parser.add_argument('-w', '--weights', metavar='FILE',
                            help='JSON file defining custom weights for alternatives.')
        
        # Evolutionary settings
        parser.add_argument('--population', metavar='DIR',
                            help='Directory of grammarinator tree pool.')
        parser.add_argument('--no-generate', dest='generate', default=True, action='store_false',
                            help='Disable test generation from grammar.')
        parser.add_argument('--no-mutate', dest='mutate', default=True, action='store_false',
                            help='Disable test generation by mutation.')
        parser.add_argument('--no-recombine', dest='recombine', default=True, action='store_false',
                            help='Disable test generation by recombination.')
        parser.add_argument('--no-grammar-violations', dest='unrestricted', default=True, action='store_false',
                            help='Disable applying grammar-violating mutators (enabled by default)')
        parser.add_argument('--keep-trees', default=False, action='store_true',
                            help='Keep generated tests for further mutations/recombinations.')
        parser.add_argument('--tree-format', metavar='NAME', choices=['pickle', 'json', 'flatbuffers'], default='pickle',
                            help='Format of the saved trees (choices: pickle, json, flatbuffers, default: pickle)')
        parser.add_argument('--tree-extension', default='grtp', metavar='EXT',
                            help='Tree file extension (default: %(default)s).')
        parser.add_argument('--tree-codec', default='grammarinator.tool.tree_codec.PickleTreeCodec',
                            help='Tree file codec (default: %(default)s).')
        
        # Output settings
        parser.add_argument('-o', '--out', metavar='FILE', default='',
                            help='Output file name pattern.')
        parser.add_argument('--encoding', default='utf-8',
                            help='Output file encoding (default: %(default)s).')
        parser.add_argument('--encoding-errors', default='strict',
                            help='Encoding error handling scheme (default: %(default)s).')
        parser.add_argument('--dry-run', default=False, action='store_true',
                            help='Generate tests without writing them.')
        
        # Parse the arguments
        parsed_args = parser.parse_args(args)
        return self._process_args(parsed_args)

    def _process_args(self, args):
        """Process and prepare args for the generator tool."""
        # Import objects
        from inators.imp import import_object
        from grammarinator.tool import PickleTreeCodec, JsonTreeCodec, FlatBuffersTreeCodec

        if isinstance(args.generator, str):
            args.generator = import_object(args.generator)
            
        if isinstance(args.model, str):
            args.model = import_object(args.model)
        
        # Handle listeners
        if args.listener:
            listeners = []
            for listener in args.listener:
                listeners.append(import_object(listener))
            args.listener = listeners
        
        # Handle transformers
        if args.transformer:
            transformers = []
            for transformer in args.transformer:
                transformers.append(import_object(transformer))
            args.transformer = transformers
        
        # Handle serializer
        if args.serializer:
            args.serializer = import_object(args.serializer)
            
        # Handle weights
        if args.weights:
            if not exists(args.weights):
                raise ValueError('Custom weights should point to an existing JSON file.')
            
            with open(args.weights, 'r') as f:
                weights = {}
                for rule, alts in json.load(f).items():
                    for alternation_idx, alternatives in alts.items():
                        for alternative_idx, w in alternatives.items():
                            weights[(rule, int(alternation_idx), int(alternative_idx))] = w
                args.weights = weights
        
        # Process tree format argument
        tree_formats = {
            'pickle': {'extension': 'grtp', 'codec_class': PickleTreeCodec},
            'json': {'extension': 'grtj', 'codec_class': JsonTreeCodec},
            'flatbuffers': {'extension': 'grtf', 'codec_class': FlatBuffersTreeCodec},
        }
        tree_format = tree_formats[args.tree_format]
        args.tree_extension = tree_format['extension']
        args.tree_codec = tree_format['codec_class']()
        
        # Handle population
        if args.population:
            args.population = abspath(args.population)
        
        return args

    def _create_generator_tool(self, args):
        """
        Create a generator tool with the processed arguments.
        
        Args:
            args: Processed arguments
            
        Returns:
            GeneratorTool: Initialized generator tool
        """
        # Create the generator factory
        generator_factory = DefaultGeneratorFactory(
            args.generator,
            model_class=args.model,
            weights=getattr(args, 'weights', None),
            listener_classes=args.listener
        )
        
        # Create population if needed
        population = None
        if args.population:
            population = DefaultPopulation(
                args.population,
                args.tree_extension,
                args.tree_codec
            )
        
        # Create the generator tool
        generator_tool = GeneratorTool(
            generator_factory=generator_factory,
            rule=args.rule,
            out_format=args.out,
            limit=RuleSize(depth=args.max_depth, tokens=args.max_tokens),
            population=population,
            generate=args.generate,
            mutate=args.mutate,
            recombine=args.recombine,
            unrestricted=args.unrestricted,
            keep_trees=args.keep_trees,
            transformers=args.transformer,
            serializer=args.serializer,
            cleanup=False,
            encoding=args.encoding,
            errors=args.encoding_errors,
            dry_run=True  # Always use dry_run=True and handle output manually
        )
        
        # Enter the context
        generator_tool.__enter__()
        
        return generator_tool

    def generate(self, name, random_seed=None):
        """
        Generate content using a registered generator.
        
        Args:
            name (str): Name of the registered generator to use
            random_seed (int, optional): Random seed for reproducible generation
            
        Returns:
            bytes: The generated content as bytes
            
        Raises:
            KeyError: If the specified generator name is not registered
        """
        generator_tool = self.get_registered(name)
        if generator_tool is None:
            raise KeyError(f"Generator '{name}' is not registered")
        
        # Increment the counter for this generator
        with self._lock:
            index = self._counters[name]
            self._counters[name] += 1
        
        # Set random seed if provided
        if random_seed is not None:
            original_seed_state = random.getstate()
            random.seed(random_seed + index)
        
        try:
            # Create the content tree
            root = generator_tool.create()
            
            # Convert the tree to bytes
            return str(root).encode('utf-8')
        finally:
            # Restore random state if we set a seed
            if random_seed is not None:
                random.setstate(original_seed_state)

    def __del__(self):
        """Clean up resources when the instance is garbage collected."""
        for name, tool in self._generator_tools.items():
            if tool is not None:
                try:
                    tool.__exit__(None, None, None)
                except:
                    pass
        self._generator_tools.clear()


# Global instance of the wrapper
_wrapper = GrammarinatorWrapper()


def get_wrapper():
    """Get or create the wrapper instance."""
    global _wrapper
    return _wrapper


def register_generator(name, generator_class, args=None, rule=None, depth=20):
    """
    Register a new generator with the specified name.
    
    Args:
        name (str): Name to register the generator under
        generator_class: The generator class to use
        args: Optional list of command-line style arguments
        rule (str): Optional rule name to start generation from
        depth (int): Maximum recursion depth during generation
        
    Returns:
        bool: True if registration was successful, False if name already exists
    """
    return get_wrapper().register(name, generator_class, args, rule, depth)


def generate_content(name):
    """
    Generate content using a registered generator.
    
    Args:
        name (str): Name of the registered generator to use
        
    Returns:
        bytes: The generated content as bytes
    """
    return get_wrapper().generate(name)
