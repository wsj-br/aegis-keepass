"""Exercise the spec's pure filters without running a PyInstaller build."""

import ast
from pathlib import Path

import pytest


@pytest.fixture
def filters():
    spec = Path(__file__).resolve().parents[2] / 'packaging' / 'aegis-keepass.spec'
    tree = ast.parse(spec.read_text())
    names = {'_DROP_LIB_PREFIXES', '_norm', '_drop_binary'}
    nodes = [node for node in tree.body if
             isinstance(node, ast.Import) and any(a.name == 'os' for a in node.names)
             or isinstance(node, ast.FunctionDef) and node.name in names
             or isinstance(node, ast.Assign) and any(
                 isinstance(target, ast.Name) and target.id in names
                 for target in node.targets)]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(spec), 'exec'), namespace)
    return namespace


@pytest.mark.parametrize('library', [
    'liblcms2.so.2', 'native/liblcms2.so.2.0.16',
    'libwebkit2gtk-4.1.so.0', 'libjavascriptcoregtk-4.1.so.0',
])
def test_host_webkit_dependencies_are_not_bundled(filters, library):
    assert filters['_drop_binary'](library)


@pytest.mark.parametrize('library', [
    'gi/_gi.cpython-313-x86_64-linux-gnu.so',
    'cryptography/hazmat/bindings/_rust.abi3.so', 'libpython3.13.so.1.0',
])
def test_python_extensions_remain_bundled(filters, library):
    assert not filters['_drop_binary'](library)
