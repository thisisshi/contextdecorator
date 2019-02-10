import sys

from contextlib import ContextDecorator

class Decorator(ContextDecorator):
    def __init__(self, print_args):
        self.print_args = print_args
    
    def __call__(self, f):
        def call(*args, **kwargs):
            print('do something before')
            if self.print_args:
                f(**kwargs)
            else:
                f('')
            print('do something after')
        return call

    def __enter__(self):
        print('hello %s' % self.print_args)
        return self

    def __exit__(self, *exc):
        print('goodbye %s' % self.print_args)


with Decorator(int(sys.argv[1])) as DecoratorInstance:
    @DecoratorInstance
    def print_hiya(arg1):
        print('hiya' + arg1)

    print_hiya(arg1=sys.argv[1])
    print_hiya(arg1=sys.argv[1])
